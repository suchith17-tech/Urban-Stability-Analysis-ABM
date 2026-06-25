import numpy as np


class StabilityAnalyzer:
    """
    Computes the Urban Stability Index (USI) from 4 sub-components.

    USI(t) = w1*S_R + w2*C + w3*S_I + w4*S_O

    Components:
        S_R : Resource Sufficiency  = min(total_allocation / total_demand, 1)
                                      → 1 when supply meets demand, <1 under scarcity
        C   : Cooperation Ratio     = mean(trust) across all agents
        S_I : Inequality Stability  = 1 - Gini(allocations)
        S_O : Oscillation Stability = 1 / (1 + var(USI_history[-W:]))

    Note: S_R and S_I now measure independent dimensions — sufficiency vs. distribution
    equity — whereas the previous variance-based S_R was a second inequality proxy.
    """

    def __init__(self, config):
        self.weights = config.get("usi_weights", [0.25, 0.25, 0.25, 0.25])
        self.oscillation_window = config.get("oscillation_window", 5)
        self.usi_history = []  # rolling history for S_O

    # ------------------------------------------------------------------
    # 3.2  Resource Sufficiency  (replaces old variance-based S_R)
    # ------------------------------------------------------------------
    def compute_S_R(self, agents, total_supply):
        """
        S_R = Weighted composite resource sufficiency across all 3 resources.

        Formula:
            S_R = 0.4 * (total_food_alloc / total_food_demand)
                + 0.4 * (total_water_alloc / total_water_demand)
                + 0.2 * (total_elec_alloc  / total_elec_demand)

        Weights match the Gini composite (food & water equally critical,
        electricity secondary) — ensures S_R and S_I measure consistent
        dimensions of the same multi-resource system.

        Range: [0, 1]  — 1 = all demands fully met across all resources
        """
        def _ratio(alloc_attr, demand_attr):
            total_demand = sum(getattr(a, demand_attr) for a in agents)
            if total_demand == 0:
                return 1.0
            total_alloc = sum(getattr(a, alloc_attr) for a in agents)
            return min(total_alloc / total_demand, 1.0)

        food_ratio  = _ratio("food_allocated",  "food_demand")
        water_ratio = _ratio("water_allocated", "water_demand")
        elec_ratio  = _ratio("elec_allocated",  "elec_demand")

        return float(0.4 * food_ratio + 0.4 * water_ratio + 0.2 * elec_ratio)


    # ------------------------------------------------------------------
    # 3.3  Cooperation Ratio
    # ------------------------------------------------------------------
    def compute_C(self, agents):
        """C = mean trust across all agents. Range: [0, 1]"""
        return float(np.mean([a.trust for a in agents]))

    # ------------------------------------------------------------------
    # 3.1 / 3.4  Gini & Inequality Stability
    # ------------------------------------------------------------------
    def compute_gini(self, agents):
        """
        Gini coefficient over agent composite consumption-satisfaction scores.

        Each agent's `allocated` = weighted satisfaction ratio:
            0.40 * (food_allocated / food_demand)
          + 0.40 * (water_allocated / water_demand)
          + 0.20 * (elec_allocated  / elec_demand)

        Range [0, 1]:
          0 = perfect equality (all agents equally satisfied)
          1 = extreme inequality (some fully satisfied, others starved)

        Responds dynamically to:
          - Shocks  → supply drops → poor under-served → Gini rises
          - Policies → PDS floor + income transfers → Gini falls
        """
        values = sorted([a.allocated for a in agents])
        n = len(values)
        if n == 0:
            return 0.0

        cumulative = 0.0
        weighted_sum = 0.0
        for i, v in enumerate(values):
            weighted_sum += (i + 1) * v
            cumulative += v

        if cumulative == 0:
            return 0.0

        return (2 * weighted_sum) / (n * cumulative) - (n + 1) / n

    def compute_S_I(self, gini):
        """S_I = 1 - Gini. Range: [0, 1] (1 = perfect equality)"""
        return max(0.0, 1.0 - gini)

    # ------------------------------------------------------------------
    # 3.5  Oscillation Stability
    # ------------------------------------------------------------------
    def compute_S_O(self):
        """
        S_O = 1 / (1 + var(USI_history[-W:])).
        Uses last W USI values. Range: (0, 1].
        On first W steps, window is smaller — stabilizes as history grows.
        """
        window = self.usi_history[-self.oscillation_window:]
        if len(window) < 2:
            return 1.0  # no oscillation yet
        return 1.0 / (1.0 + np.var(window))

    # ------------------------------------------------------------------
    # 3.6  USI Composite
    # ------------------------------------------------------------------
    def compute_usi(self, agents, total_supply):
        """
        Compute full USI and all sub-components for the current step.

        Args:
            agents       : list of UrbanAgent instances
            total_supply : current ResourcePool.total_supply (used for S_R)

        Returns: (usi, gini, S_R, C, S_I, S_O)
        """
        w1, w2, w3, w4 = self.weights

        S_R  = self.compute_S_R(agents, total_supply)
        C    = self.compute_C(agents)
        gini = self.compute_gini(agents)
        S_I  = self.compute_S_I(gini)
        S_O  = self.compute_S_O()

        usi = w1 * S_R + w2 * C + w3 * S_I + w4 * S_O

        # Clamp to [0, 1]
        usi = max(0.0, min(1.0, usi))

        # Store in history for next step's S_O
        self.usi_history.append(usi)

        return usi, gini, S_R, C, S_I, S_O
