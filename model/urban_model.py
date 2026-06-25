"""
model/urban_model.py — Phase 5 (data-driven)

UrbanStabilityModel now:
  - Loads config from model_config_by_city.json via config_loader
  - Creates agents with group-specific income/demand from HCES calibration
  - Uses 3-resource pool (water, food, electricity) with monthly arrays
  - Applies city-specific shocks with gradual recovery curves
  - Implements Anna Bhagya, Gruha Jyothi, Gruha Lakshmi policies
  - Records full USI + sub-components per monthly step
"""
from mesa import Model
from mesa.datacollection import DataCollector
import numpy as np

from model.resource_pool import ResourcePool
from agents.urban_agent import UrbanAgent
from modules.interaction_network import create_interaction_network
from modules.stability_analyzer import StabilityAnalyzer
from modules.shock_module import ShockModule
from model.policy_engine import PolicyEngine


class UrbanStabilityModel(Model):

    def __init__(self, config: dict):
        super().__init__()

        self.config = config
        np.random.seed(config.get("random_seed", 42))

        self.city         = config.get("city", "Unknown")
        self.num_agents   = config.get("num_agents", 500)
        self.current_step = 0
        self.running      = True

        # ------------------------------------------------------------------
        # Create agents by income group proportions
        # ------------------------------------------------------------------
        self.agents_list = []
        groups = config["agent_groups"]  # list of {name, fraction, lognorm_*}

        # Assign agents to groups by exact fraction
        counts = self._group_counts(groups, self.num_agents)

        for group_cfg, count in zip(groups, counts):
            for _ in range(count):
                agent = UrbanAgent(self, income_group=group_cfg["name"])
                self.agents_list.append(agent)

        # Shuffle to mix groups in the list
        rng = np.random.default_rng(config.get("random_seed", 42))
        rng.shuffle(self.agents_list)

        # ------------------------------------------------------------------
        # Resource Pool (3 resources)
        # ------------------------------------------------------------------
        self.resource_pool = ResourcePool(config)

        # ------------------------------------------------------------------
        # Policy Engine
        # ------------------------------------------------------------------
        self.policy_engine = PolicyEngine(config, self.agents_list)

        # ------------------------------------------------------------------
        # Interaction Network
        # ------------------------------------------------------------------
        self.network = create_interaction_network(
            self.num_agents,
            config.get("avg_degree", 8),
            seed=config.get("random_seed", 42)
        )

        # ------------------------------------------------------------------
        # Stability Analyzer
        # ------------------------------------------------------------------
        self.stability_analyzer = StabilityAnalyzer(config)

        # ------------------------------------------------------------------
        # Shock Module
        # ------------------------------------------------------------------
        self.shock_module = ShockModule(config)

        # ------------------------------------------------------------------
        # Metrics
        # ------------------------------------------------------------------
        self.current_usi  = 0.0
        self.current_gini = 0.0
        self.current_S_R  = 0.0
        self.current_C    = 0.0
        self.current_S_I  = 0.0
        self.current_S_O  = 0.0
        self._collapse_streak = 0

        # ------------------------------------------------------------------
        # Data Collector
        # ------------------------------------------------------------------
        self.datacollector = DataCollector(
            model_reporters={
                "Step":           lambda m: m.current_step,
                "Month":          lambda m: (m.current_step % 12) + 1,
                "USI":            lambda m: m.current_usi,
                "Gini":           lambda m: m.current_gini,
                "Average_Trust":  lambda m: m.current_C,
                "S_R":            lambda m: m.current_S_R,
                "S_I":            lambda m: m.current_S_I,
                "S_O":            lambda m: m.current_S_O,
                "Water_Supply":   lambda m: m.resource_pool.water_supply,
                "Food_Supply":    lambda m: m.resource_pool.food_supply,
                "Elec_Supply":    lambda m: m.resource_pool.elec_supply,
                "Total_Demand":   lambda m: sum(a.water_demand for a in m.agents_list),
                "Total_Supply":   lambda m: m.resource_pool.total_supply,
                "Active_Shocks":  lambda m: str(m.shock_module.active_shock_names),
                "Cooperating_Pct": lambda m: float(
                    sum(1 for a in m.agents_list if a.cooperating) / max(1, len(m.agents_list))
                ),
            }
        )

    # ------------------------------------------------------------------
    # MAIN SIMULATION STEP
    # ------------------------------------------------------------------
    def step(self):
        if not self.running:
            return

        month_index = self.current_step

        # 1. GET SHOCK MULTIPLIERS for this month (from recovery curves)
        shock_multipliers = self.shock_module.get_current_multipliers(month_index)
        shock_active = any(v < 1.0 for v in shock_multipliers.values())

        # 2. UPDATE MONTHLY SUPPLY (seasonal + shock)
        self.resource_pool.update_monthly_supply(month_index, shock_multipliers)

        # 3. POLICY: compute subsidy eligibility (legacy no-op in Phase 5)
        self.policy_engine.compute_subsidy_eligibility()

        # 4. AGENTS compute demand (model-level control — no agent.step() to avoid duplication)
        for agent in self.agents_list:
            agent.compute_demand()

        # 5. RESOURCE ALLOCATION (3 pools + interaction effects)
        self.resource_pool.allocate(self.agents_list)

        # 6. POLICY: post-allocation adjustments (Gruha Jyothi, DM response)
        self.policy_engine.apply_policies(
            self.agents_list,
            self.resource_pool,
            shock_active=shock_active
        )

        # 7. SHOCK: apply trust reduction + economic shock
        self.shock_module.apply(self)

        # 8. AGENTS update trust (satisfaction + social influence)
        for agent in self.agents_list:
            agent.update_trust()

        # 9. COMPUTE STABILITY METRICS
        (
            self.current_usi,
            self.current_gini,
            self.current_S_R,
            self.current_C,
            self.current_S_I,
            self.current_S_O
        ) = self.stability_analyzer.compute_usi(
            self.agents_list,
            self.resource_pool.total_supply
        )

        # 10. COLLAPSE DETECTION
        threshold   = self.config.get("collapse_threshold", 0.2)
        consecutive = self.config.get("collapse_consecutive_steps", 3)

        if self.current_usi < threshold:
            self._collapse_streak += 1
        else:
            self._collapse_streak = 0

        if self._collapse_streak >= consecutive:
            print(f"[{self.city}] COLLAPSE at step {self.current_step} "
                  f"(USI={self.current_usi:.3f} < {threshold} for {consecutive} steps)")
            self.running = False

        # 11. COLLECT DATA
        self.datacollector.collect(self)

        # 12. ADVANCE TIME
        self.current_step += 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _group_counts(groups: list, total: int) -> list:
        """Distribute total agents across groups by fraction (integer rounding)."""
        fracs   = [g["fraction"] for g in groups]
        total_f = sum(fracs)
        counts  = [int(round(f / total_f * total)) for f in fracs]
        # Correct rounding error
        diff = total - sum(counts)
        if diff != 0:
            counts[0] += diff
        return counts

    def get_summary(self) -> dict:
        """Return end-of-run summary dict."""
        return {
            "city":          self.city,
            "steps_run":     self.current_step,
            "final_usi":     round(self.current_usi, 4),
            "final_gini":    round(self.current_gini, 4),
            "final_trust":   round(self.current_C, 4),
            "final_S_R":     round(self.current_S_R, 4),
            "collapse":      not self.running,
            "active_shocks": self.shock_module.active_shock_names,
        }