import numpy as np


class ResourcePool:
    """
    Three-resource pool (water, food, electricity) — data-driven (Phase 5).

    Supply:
      - Loaded from monthly arrays in config (60 rows = 5 cities × 12 months)
      - Indexed by model.current_step % 12 (monthly cycle)
      - Water reduced by FHTC gap (unconnected households get 0 piped water)

    Allocation order:
      1. PDS food: extreme_poor and bpl_poor get guaranteed PDS kg first
      2. Market allocation: proportional by demand for remaining supply
      3. Gruha Jyothi: electricity cost = 0 if allocated ≤ 200 kWh

    Interaction effects (applied after allocation):
      - water_deficit → food_utilization reduction (coeff from config)
      - electricity_deficit → water_pumping reduction (coeff from config)
      - food_deficit → direct trust reduction (applied to agent.trust)
    """

    def __init__(self, config):
        self.config = config
        supply = config["supply_monthly"]

        # 12-month supply arrays
        self._water_arr = supply["water_lpd_hh"]    # L/HH/day
        self._food_arr  = supply["food_kg_hh"]       # kg/HH/month (PDS)
        self._elec_arr  = supply["elec_kwh_hh"]      # kWh/HH/month

        # Interaction coefficients
        ix = config.get("resource_interactions", {})
        self.c_water_food = ix.get("water_deficit_on_food_utilization", 0.715)
        self.c_elec_water = ix.get("electricity_deficit_on_water_pumping", 0.458)
        self.c_food_trust = ix.get("food_deficit_on_trust_drop_rate", 0.638)

        # FHTC: fraction of HH without tap connection
        gap_pct = config.get("water_access_gap_pct", 0.0)
        self.water_coverage = max(0.0, 1.0 - gap_pct / 100.0)

        # State for current step
        self.water_supply = 0.0
        self.food_supply  = 0.0
        self.elec_supply  = 0.0

        # Expose total_supply for StabilityAnalyzer (use water as primary resource)
        self.total_supply = 0.0

    # ------------------------------------------------------------------
    # Monthly supply update (call before allocation each step)
    # ------------------------------------------------------------------
    def update_monthly_supply(self, month_index: int, shock_multipliers: dict = None):
        """
        Set supply levels for the current month.

        Args:
            month_index: 0=Jan … 11=Dec
            shock_multipliers: dict with keys 'water', 'food', 'elec'
                               each a float multiplier (1.0 = no shock)
        """
        m = month_index % 12
        sm = shock_multipliers or {}

        self.water_supply = self._water_arr[m] * sm.get("water", 1.0) * self.water_coverage
        self.food_supply  = self._food_arr[m]  * sm.get("food", 1.0)
        self.elec_supply  = self._elec_arr[m]  * sm.get("elec", 1.0)

        # Expose water supply as legacy total_supply
        self.total_supply = self.water_supply

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------
    def allocate(self, agents):
        """
        Allocate water, food, and electricity to all agents.

        Food allocation: PDS priority → then market proportional
        Water allocation: proportional by demand (water coverage already applied)
        Electricity allocation: proportional by demand
        """
        n = len(agents)
        if n == 0:
            return

        # --- FOOD ---
        self._allocate_food(agents)

        # --- WATER ---
        self._allocate_proportional(
            agents,
            demand_attr="water_demand",
            alloc_attr="water_allocated",
            total_supply=self.water_supply * n,  # per-HH → total for all agents
        )

        # --- ELECTRICITY ---
        self._allocate_proportional(
            agents,
            demand_attr="elec_demand",
            alloc_attr="elec_allocated",
            total_supply=self.elec_supply * n,
        )

        # --- INTERACTION EFFECTS ---
        self._apply_interactions(agents)

    def _allocate_food(self, agents):
        """
        Food allocation in two tiers:
          1. PDS tier: poor agents get min(pds_supply, pds_demand) guaranteed
          2. Market tier: remaining demand filled proportionally
        """
        pds_supply_per_agent = self.food_supply   # per HH from monthly array

        # Tier 1: PDS allocation for eligible agents
        anna_bhagya_cfg  = self.config.get("anna_bhagya",  {})
        eligible_groups  = anna_bhagya_cfg.get("eligible_groups", ["extreme_poor", "bpl_poor"])
        rice_kg_pp       = anna_bhagya_cfg.get("rice_kg_pp_pm", 5)
        hh_size          = self.config.get("avg_household_size", 4.0)
        anna_bhagya_kg   = rice_kg_pp * hh_size   # guaranteed kg/HH/month

        for agent in agents:
            d = self.config["demand_by_group"].get(agent.income_group, {})
            pds_need = d.get("food_pds_kg", 0.0)

            if agent.income_group in eligible_groups:
                # PDS supply; Anna Bhagya guarantees additional rice floor
                pds_alloc = min(pds_supply_per_agent, pds_need)
                if agent.eligible_anna_bhagya:
                    pds_alloc = max(pds_alloc, min(anna_bhagya_kg, pds_need))
                agent.food_allocated = pds_alloc
            else:
                agent.food_allocated = 0.0  # non-poor: market only

        # Tier 2: Market allocation for remaining demand
        # (food_supply here represents PDS only; market is additional)
        # Market adds up to remaining demand
        for agent in agents:
            d = self.config["demand_by_group"].get(agent.income_group, {})
            market_need = d.get("food_market_kg", agent.food_demand - agent.food_allocated)
            market_need = max(0.0, market_need)

            # Market is assumed available but reduced under shock (shock multiplier already applied)
            # Simple assumption: market supply = market_need (elastic supply)
            # except when food_supply shock reduces availability
            market_factor = min(self.food_supply / max(0.001, d.get("food_pds_kg", 1.0)), 1.0)
            agent.food_allocated += market_need * market_factor

            agent.food_allocated = max(0.0, agent.food_allocated)

    def _allocate_proportional(self, agents, demand_attr, alloc_attr, total_supply):
        """Proportional allocation under scarcity; full allocation if surplus."""
        total_demand = sum(getattr(a, demand_attr) for a in agents)

        if total_demand <= 0:
            for agent in agents:
                setattr(agent, alloc_attr, 0.0)
            return

        if total_demand <= total_supply:
            # Surplus: everyone gets their full demand
            for agent in agents:
                setattr(agent, alloc_attr, getattr(agent, demand_attr))
        else:
            # Scarcity: proportional rationing
            ratio = total_supply / total_demand
            for agent in agents:
                setattr(agent, alloc_attr, getattr(agent, demand_attr) * ratio)

    # ------------------------------------------------------------------
    # Resource interaction effects
    # ------------------------------------------------------------------
    def _apply_interactions(self, agents):
        """
        Apply coupling coefficients after primary allocation.

        1. Electricity deficit → reduce water allocation (pumping capacity)
        2. Water deficit → reduce food utilization (cooking, hygiene)
        3. Food deficit → reduce trust directly (hunger → unrest)
        """
        for agent in agents:
            # --- 1. Electricity → Water ---
            if agent.elec_demand > 0:
                elec_sat = min(agent.elec_allocated / agent.elec_demand, 1.0)
                elec_deficit = max(0.0, 1.0 - elec_sat)
                water_reduction = elec_deficit * self.c_elec_water
                agent.water_allocated = max(0.0, agent.water_allocated * (1.0 - water_reduction))

            # --- 2. Water → Food utilization ---
            if agent.water_demand > 0:
                water_sat = min(agent.water_allocated / agent.water_demand, 1.0)
                water_deficit = max(0.0, 1.0 - water_sat)
                food_reduction = water_deficit * self.c_water_food
                agent.food_allocated = max(0.0, agent.food_allocated * (1.0 - food_reduction))

            # --- 3. Food → Trust ---
            if agent.food_demand > 0:
                food_sat = min(agent.food_allocated / agent.food_demand, 1.0)
                food_deficit = max(0.0, 1.0 - food_sat)
                trust_drop = food_deficit * self.c_food_trust * 0.1  # scale to monthly delta
                agent.trust = max(0.0, agent.trust - trust_drop)

            # Update legacy allocated (water proxy)
            agent.allocated = agent.water_allocated