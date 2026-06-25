from mesa import Agent
import numpy as np


class UrbanAgent(Agent):
    """
    Urban household agent — data-driven (Phase 5).

    Each agent belongs to one income group (extreme_poor / bpl_poor / non_poor).
    Income is drawn from the group's HCES-calibrated lognormal distribution.
    Demand is split across 3 resources (water, food, electricity).
    Trust mechanics follow the formal definition from trust_mechanics config.
    """

    def __init__(self, model, income_group: str):
        super().__init__(model)

        self.income_group = income_group

        # Lognormal income from group-calibrated params
        g = self._group_cfg()
        self.income = np.random.lognormal(
            mean=g["lognorm_mean"],
            sigma=g["lognorm_sigma"]
        )

        # Annual income reference (for policy eligibility)
        self.annual_income_mean = g["annual_income_mean"]

        # Trust — start from config initial value with small uniform noise
        trust_init = model.config.get("trust_initial", 0.7)
        self.trust = float(np.clip(
            np.random.normal(trust_init, 0.05), 0.1, 1.0
        ))

        # --- Resource demand (per HH per month) ---
        self.food_demand  = 0.0
        self.water_demand = 0.0
        self.elec_demand  = 0.0

        # --- Resource allocation received ---
        self.food_allocated  = 0.0
        self.water_allocated = 0.0
        self.elec_allocated  = 0.0

        # Legacy single-resource fields (kept for StabilityAnalyzer compatibility)
        self.demand    = 0.0
        self.allocated = 0.0

        # Cooperation flag
        self.cooperating = True

        # --- Policy eligibility (set once at init by PolicyEngine, never changed) ---
        self.eligible_anna_bhagya   = False   # BPL/AAY group
        self.eligible_gruha_jyothi  = False   # all domestic consumers
        self.eligible_gruha_lakshmi = False   # female-headed HH (50% of poor)

        # --- Per-step policy benefit flags (reset each step by PolicyEngine) ---
        # True = agent actually received the benefit THIS month
        self.benefit_anna_bhagya   = False
        self.benefit_gruha_jyothi  = False
        self.benefit_gruha_lakshmi = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _group_cfg(self):
        """Return this agent's group config dict."""
        for g in self.model.config["agent_groups"]:
            if g["name"] == self.income_group:
                return g
        raise KeyError(f"Group '{self.income_group}' not in agent_groups")

    def _demand_cfg(self):
        """Return this agent's demand calibration dict."""
        return self.model.config["demand_by_group"][self.income_group]

    # ------------------------------------------------------------------
    # Demand computation
    # ------------------------------------------------------------------
    def compute_demand(self):
        """
        Set demand for water, food, electricity from calibrated per-HH values.
        Adjusts for:
          - Trust < 0.5: demand escalation (panic hoarding, up to +20%)
          - Gruha Lakshmi: income supplement raises non-poor-equivalent demand
          - Economic shock: income reduction applied to food/elec demand
        """
        d = self._demand_cfg()

        # Base calibrated demands
        food_base  = d["food_total_kg"]
        water_base = d["water_lpd"]
        elec_base  = d["elec_kwh"]

        # FIX 3: Demand escalation when trust < 0.5 (panic buying)
        tm = self.model.config.get("trust_mechanics", {})
        escalation_threshold = 0.5
        if tm:
            de = tm.get("system_effects", {}).get("demand_escalation", {})
            escalation_threshold = de.get("threshold", 0.5)

        if self.trust < escalation_threshold:
            escalation = 1.0 + 0.2 * (escalation_threshold - self.trust)
            food_base  *= escalation
            elec_base  *= escalation   # not water — people don't hoard water in pipes

        if self.eligible_gruha_lakshmi:
            supplement_rs = self.model.config["gruha_lakshmi"]["transfer_rs_pm"]
            # ≈ 5% demand boost per ₹2000/month (modest — most goes to savings)
            boost = 1 + (supplement_rs / 40000)
            food_base *= boost

        self.food_demand  = max(0.0, food_base)
        self.water_demand = max(0.0, water_base)
        self.elec_demand  = max(0.0, elec_base)

        # Legacy combined demand for StabilityAnalyzer (normalised 0-1 scale)
        # Water dominates physical demand — use as proxy
        self.demand = self.water_demand

    # ------------------------------------------------------------------
    # Trust update
    # ------------------------------------------------------------------
    def update_trust(self):
        """
        Trust update using data-driven trust mechanics:

        1. Resource satisfaction: compare received vs demanded (threshold 0.8)
        2. Policy benefit: +0.03 if received any policy benefit this step
        3. Shock event: handled externally by ShockModule
        4. Social influence: 0.2 × mean(neighbour trust)
        5. Natural recovery: +0.01 per stable month (no shock)

        Thresholds:
          < 0.5 → policy_effectiveness drops
          < 0.4 → cooperation collapses
          < 0.3 → protest risk
        """
        if self.food_demand == 0 and self.water_demand == 0:
            return

        # --- 1. Resource satisfaction ---
        # Use combined satisfaction across all 3 resources (weighted)
        sat_food  = min(self.food_allocated  / self.food_demand,  1.0) if self.food_demand  > 0 else 1.0
        sat_water = min(self.water_allocated / self.water_demand, 1.0) if self.water_demand > 0 else 1.0
        sat_elec  = min(self.elec_allocated  / self.elec_demand,  1.0) if self.elec_demand  > 0 else 1.0

        # Weighted: food and water more critical than electricity
        satisfaction = 0.4 * sat_food + 0.4 * sat_water + 0.2 * sat_elec

        if satisfaction >= 0.8:
            trust_delta = +0.02   # adequate supply → slow trust build
        else:
            trust_delta = -0.05 * (1.0 - satisfaction / 0.8)  # shortfall erodes trust

        # --- 2. Policy benefit (uses benefit_ flags set by PolicyEngine this step) ---
        policy_bonus = 0.0
        if self.benefit_anna_bhagya:
            policy_bonus += 0.03
        if self.benefit_gruha_jyothi:
            policy_bonus += 0.02
        if self.benefit_gruha_lakshmi:
            policy_bonus += 0.02
        # Scale policy bonus by trust (low trust → less aware of/accessing benefits)
        eff = min(self.trust / 0.5, 1.0)  # policy effectiveness
        trust_delta += policy_bonus * eff

        # --- 4. Social influence (0.2 × mean neighbour trust) ---
        network = self.model.network
        agent_index = self.model.agents_list.index(self)
        alpha = self.model.config.get("trust_weight_personal", 0.8)

        if agent_index in network:
            neighbours = list(network.neighbors(agent_index))
            if neighbours:
                mean_nbr = float(np.mean([
                    self.model.agents_list[n].trust
                    for n in neighbours if n < len(self.model.agents_list)
                ]))
            else:
                mean_nbr = self.trust
        else:
            mean_nbr = self.trust

        # Blend: personal experience + social influence
        personal = max(0.0, min(1.0, self.trust + trust_delta))
        self.trust = alpha * personal + (1 - alpha) * mean_nbr

        # --- Cooperation state from trust thresholds ---
        self.cooperating = self.trust >= 0.4

        # Clamp
        self.trust = float(np.clip(self.trust, 0.0, 1.0))

        # Update composite consumption score for Gini calculation.
        # Use normalized satisfaction per resource (allocation / demand),
        # weighted equally. This makes Gini shock-sensitive and policy-responsive.
        def _ratio(alloc, demand):
            return alloc / demand if demand > 0 else 1.0

        self.allocated = (
            0.40 * _ratio(self.food_allocated,  self.food_demand)
            + 0.40 * _ratio(self.water_allocated, self.water_demand)
            + 0.20 * _ratio(self.elec_allocated,  self.elec_demand)
        )

    # ------------------------------------------------------------------
    # Mesa step — NO-OP (model loop controls sequencing explicitly)
    # ------------------------------------------------------------------
    def step(self):
        """
        Intentional no-op. The model step() calls compute_demand(),
        resource_pool.allocate(), policy_engine.apply_policies(), and
        update_trust() in the correct order. Calling agent.step()
        would cause double computation.
        """
        pass