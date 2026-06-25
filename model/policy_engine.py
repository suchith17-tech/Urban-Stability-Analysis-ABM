"""
model/policy_engine.py — Phase 5 (data-driven)

Implements three Karnataka government schemes:
  - Anna Bhagya: free rice for BPL/AAY agents
  - Gruha Jyothi: free electricity ≤ 200 kWh/month
  - Gruha Lakshmi: ₹2000/month to eligible women-headed HH agents
  - DM Response: emergency supply release during active shocks
  - Policy effectiveness scaling by trust level
"""
import numpy as np


class PolicyEngine:
    """
    Manages and applies all scheme-based policy mechanisms.
    Called once per step before and after resource allocation.
    """

    def __init__(self, config, agents_list):
        self.config      = config
        self.agents_list = agents_list

        # Anna Bhagya config
        self.ab_cfg  = config.get("anna_bhagya",  {"enabled": False})
        # Gruha Jyothi config
        self.gj_cfg  = config.get("gruha_jyothi", {"enabled": False})
        # Gruha Lakshmi config
        self.gl_cfg  = config.get("gruha_lakshmi",{"enabled": False})
        # DM Response config
        self.dm_cfg  = config.get("dm_response",  {"relief_duration_months": 3})

        # Assign policy eligibility at init (deterministic)
        self._assign_eligibility()

    # ------------------------------------------------------------------
    # Eligibility assignment (once at model init)
    # ------------------------------------------------------------------
    def _assign_eligibility(self):
        """
        Assign scheme eligibility to agents based on income group.
        Gruha Lakshmi: 50% of eligible group agents (proxy for female HoH).
        """
        ab_groups = self.ab_cfg.get("eligible_groups", ["extreme_poor", "bpl_poor"])
        gl_groups = self.gl_cfg.get("eligible_groups", ["extreme_poor", "bpl_poor"])

        for agent in self.agents_list:
            # Anna Bhagya — eligibility: BPL/AAY group
            agent.eligible_anna_bhagya = (
                self.ab_cfg.get("enabled", False)
                and agent.income_group in ab_groups
            )

            # Gruha Jyothi — eligibility: ALL domestic consumers
            agent.eligible_gruha_jyothi = self.gj_cfg.get("enabled", False)

            # Gruha Lakshmi — eligibility: ~50% of poor HH (proxy for female HoH)
            agent.eligible_gruha_lakshmi = (
                self.gl_cfg.get("enabled", False)
                and agent.income_group in gl_groups
                and np.random.random() < 0.50    # ≈50% female HoH in Karnataka
            )

    # ------------------------------------------------------------------
    # Pre-allocation: subsidy eligibility (legacy interface)
    # ------------------------------------------------------------------
    def compute_subsidy_eligibility(self):
        """Legacy method — no-op in Phase 5. Eligibility set at init."""
        pass

    # ------------------------------------------------------------------
    # Post-allocation: apply policy adjustments
    # ------------------------------------------------------------------
    def apply_policies(self, agents, resource_pool, shock_active: bool = False):
        """
        Apply all post-allocation policy adjustments per step.

        Step 1: Reset all benefit flags (benefit_ = False for everyone)
        Step 2: Evaluate each scheme and set benefit_ = True if agent
                is eligible AND the benefit condition is met this step.
        Step 3: DM Response emergency boost (if shock active)
        """
        gj_threshold = self.gj_cfg.get("free_units_kwh", 200)

        for agent in agents:
            # Reset per-step benefit flags
            agent.benefit_anna_bhagya   = False
            agent.benefit_gruha_jyothi  = False
            agent.benefit_gruha_lakshmi = False

            # Anna Bhagya: eligible + received PDS food allocation this step
            if agent.eligible_anna_bhagya and agent.food_allocated > 0:
                agent.benefit_anna_bhagya = True

            # Gruha Jyothi: eligible + actually consumed ≤ 200 kWh this step
            # Eligibility (eligible_gruha_jyothi) is never touched here
            if agent.eligible_gruha_jyothi and agent.elec_allocated <= gj_threshold:
                agent.benefit_gruha_jyothi = True

            # Gruha Lakshmi: eligible → always receives transfer (DBT, not usage-based)
            if agent.eligible_gruha_lakshmi:
                agent.benefit_gruha_lakshmi = True

        # --- DM Response: emergency supply release ---
        if shock_active:
            dm_boost = 0.15   # 15% emergency supply supplement
            # Apply boost to water and food proportionally
            for agent in agents:
                agent.water_allocated = min(
                    agent.water_demand,
                    agent.water_allocated * (1 + dm_boost)
                )
                agent.food_allocated = min(
                    agent.food_demand,
                    agent.food_allocated * (1 + dm_boost * 0.5)
                )

    # ------------------------------------------------------------------
    # Effective price (legacy interface compatibility)
    # ------------------------------------------------------------------
    def apply_pricing(self, base_price, agent):
        """Legacy: returns base price (scheme pricing not used in Phase 5)."""
        return base_price

    def apply_consumption_cap(self, agents):
        """Legacy: no-op in Phase 5 (caps handled per-resource in ResourcePool)."""
        pass