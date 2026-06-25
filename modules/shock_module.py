"""
modules/shock_module.py — Phase 5 (data-driven)

City-specific shocks with:
  - Month-based triggers (not step-based)
  - Gradual recovery curves (not sudden reset)
  - Multi-resource shocks (water + food + electricity + trust simultaneously)
  - Economic shock: reduces agent income directly
"""


class ShockModule:
    """
    Injects city-specific external shocks with gradual recovery curves.

    Shock types (from shock_parameters.json):
      "flood"           — water, food, trust reduction; triggered Jul-Sep
      "drought"         — water, food, trust reduction; triggered Mar-May
      "economic_crisis" — income, demand, trust reduction; persistent

    Recovery: each shock has a `recovery_curve` list. Month 0 of shock applies
    curve[0] as the supply multiplier. Each subsequent month advances through
    the curve until 1.0 (full recovery).
    """

    def __init__(self, config):
        self.config   = config
        self.shock_cfg = config.get("shock", {})

        # Active shock tracking: {shock_type: months_active}
        self._active_shocks = {}

        # Track which shocks have already fired trust reduction (fire once)
        self._trust_shocked = set()

        # Economic shock: applied to agents directly
        self._eco_shock_active = False
        self._eco_month_index  = 0

    def get_current_multipliers(self, month_index: int) -> dict:
        """
        Compute supply multipliers (water, food, elec) for the current month.
        Called by urban_model.step() before ResourcePool.update_monthly_supply().

        Returns dict: {"water": float, "food": float, "elec": float}
        """
        multipliers = {"water": 1.0, "food": 1.0, "elec": 1.0}

        month = (month_index % 12) + 1  # 1=Jan, ..., 12=Dec

        for shock_type in ["flood", "drought"]:
            s = self.shock_cfg.get(shock_type, {})
            if not s or s.get("disabled", False):
                continue

            trigger_months = s.get("trigger_months", [])

            if month in trigger_months:
                # Shock triggers this month
                if shock_type not in self._active_shocks:
                    self._active_shocks[shock_type] = 0  # month 0 of shock

            if shock_type in self._active_shocks:
                idx = self._active_shocks[shock_type]
                curve = s.get("recovery_curve", [0.7, 0.85, 1.0])

                if idx < len(curve):
                    recovery_mult = curve[idx]
                    # Apply recovery multiplier to base reduction
                    water_red = s.get("water_supply_reduction", 0.0)
                    food_red  = s.get("food_supply_reduction",  0.0)

                    # Effective reduction at this point in recovery
                    eff_water = water_red * (1.0 - recovery_mult)
                    eff_food  = food_red  * (1.0 - recovery_mult)

                    multipliers["water"] *= (1.0 - eff_water)
                    multipliers["food"]  *= (1.0 - eff_food)
                    # Electricity less affected by flood/drought
                    multipliers["elec"]  *= max(0.85, 1.0 - eff_water * 0.3)

                    # Advance recovery index
                    self._active_shocks[shock_type] = idx + 1

                    # Check if shock fully recovered
                    if self._active_shocks[shock_type] >= len(curve):
                        # Only remove if we're past the trigger window
                        if month not in trigger_months:
                            del self._active_shocks[shock_type]
                else:
                    # Past curve length — fully recovered
                    if shock_type in self._active_shocks:
                        del self._active_shocks[shock_type]

        return multipliers

    def apply_trust_shock(self, model, month_index: int):
        """
        Apply trust reduction ONCE on the first month a shock triggers.
        Not repeated every month of the trigger window.
        """
        month = (month_index % 12) + 1

        for shock_type in ["flood", "drought"]:
            s = self.shock_cfg.get(shock_type, {})
            if not s or s.get("disabled", False):
                continue
            key = f"{shock_type}_{month_index // 12}"  # unique per year
            if month in s.get("trigger_months", []) and key not in self._trust_shocked:
                trust_red = s.get("trust_reduction", 0.0)
                for agent in model.agents_list:
                    agent.trust = max(0.0, agent.trust - trust_red)
                self._trust_shocked.add(key)

    def apply_economic_shock(self, model, month_index: int):
        """
        Economic shock: reduces agent income and demand capacity.
        Gradual recovery via recovery_curve.
        """
        s = self.shock_cfg.get("economic_crisis", {})
        if not s or s.get("disabled", False):
            return

        curve = s.get("recovery_curve", [0.85, 0.90, 0.95, 1.0])
        income_red   = s.get("income_reduction_pct", 15) / 100.0
        trust_red    = s.get("trust_reduction", 0.20)
        total_months = s.get("persistence_months", 6)
        month = (month_index % 12) + 1

        # Economic shock: assume it starts in month 4 (post-budget shock scenario)
        eco_trigger = [4, 5, 6, 7, 8, 9]  # can be parameterized later

        if month == eco_trigger[0] and not self._eco_shock_active:
            self._eco_shock_active = True
            self._eco_month_index  = 0
            # Store original income as baseline BEFORE any reduction
            for agent in model.agents_list:
                agent._original_income = agent.income
            # Apply immediate trust shock
            for agent in model.agents_list:
                agent.trust = max(0.0, agent.trust - trust_red)

        if self._eco_shock_active:
            idx = self._eco_month_index
            if idx < len(curve):
                recovery_mult = curve[idx]
                # FIX: Apply relative to ORIGINAL income, not current income
                # Each month the recovery curve moves toward 1.0, so effective
                # reduction shrinks. income_at_month = original * (1 - eff_red)
                eff_income_red = income_red * (1.0 - recovery_mult)
                for agent in model.agents_list:
                    # Restore to original then apply current-month reduction
                    original = getattr(agent, "_original_income", agent.income)
                    agent.income = max(0.0, original * (1.0 - eff_income_red))
                self._eco_month_index += 1
                if self._eco_month_index >= total_months:
                    # Restore incomes to original at end of shock
                    for agent in model.agents_list:
                        original = getattr(agent, "_original_income", agent.income)
                        agent.income = original
                    self._eco_shock_active = False

    def apply(self, model):
        """
        Legacy single-call interface. Now called from urban_model.step()
        to apply trust and economic shock effects (supply multipliers are
        handled separately via get_current_multipliers()).
        """
        month_index = model.current_step
        self.apply_trust_shock(model, month_index)
        self.apply_economic_shock(model, month_index)

    @property
    def active_shock_names(self) -> list:
        """Return names of currently active shocks (for logging/dashboard)."""
        names = list(self._active_shocks.keys())
        if self._eco_shock_active:
            names.append("economic_crisis")
        return names
