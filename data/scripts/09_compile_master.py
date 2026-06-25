"""
Step 9: Compile Master Config — One JSON Per City for ABM Ingestion
-------------------------------------------------------------------
Input : All Phase 1–3 processed outputs
Output: data/processed/model_config_by_city.json

This is the single config file that UrbanStabilityModel reads.
"""
import pathlib
import pandas as pd
import numpy as np
import json

PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

# -----------------------------------------------------------------------
# Load all processed files
# -----------------------------------------------------------------------
demo_df      = pd.read_csv(PROCESSED / "city_demographics.csv")
income_df    = pd.read_csv(PROCESSED / "income_distribution.csv")
ration_df    = pd.read_csv(PROCESSED / "agent_class_proportions.csv")
water_df     = pd.read_csv(PROCESSED / "water_supply_monthly.csv")
elec_df      = pd.read_csv(PROCESSED / "electricity_supply_monthly.csv")
food_df      = pd.read_csv(PROCESSED / "food_ration_supply.csv")
demand_df    = pd.read_csv(PROCESSED / "demand_calibration.csv")

with open(PROCESSED / "resource_interaction_matrix.json") as f:
    interactions = json.load(f)

CITIES = ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi-Dharwad", "Belagavi"]

# -----------------------------------------------------------------------
# Load policy and shock parameters from Phase 4 extraction
# -----------------------------------------------------------------------
with open(PROCESSED / "policy_parameters.json") as f:
    _policy_full = json.load(f)

# Flatten policy params for ABM config (only the key ABM-relevant fields)
POLICY_PARAMS = {
    "water_norm_lpcd": _policy_full["water_norm"]["standard_lpcd"],
    "fhtc_water_access_gap": _policy_full["fhtc_coverage"]["water_access_gap_pct"],
    "anna_bhagya": {
        "eligible": _policy_full["anna_bhagya"]["eligible"],
        "rice_kg_per_person_per_month": _policy_full["anna_bhagya"]["rice_kg_per_person_per_month"],
        "source": _policy_full["anna_bhagya"]["source"],
    },
    "gruha_jyothi": {
        "free_units_per_month": _policy_full["gruha_jyothi"]["free_units_per_month"],
        "eligible": _policy_full["gruha_jyothi"]["eligible"],
        "source": _policy_full["gruha_jyothi"]["source"],
    },
    "gruha_lakshmi": {
        "transfer_rs_per_month": _policy_full["gruha_lakshmi"]["transfer_rs_per_month"],
        "eligible": _policy_full["gruha_lakshmi"]["eligible"],
        "source": _policy_full["gruha_lakshmi"]["source"],
    },
    "dm_response": {
        "relief_duration_months": _policy_full["dm_response"]["relief_duration_months"],
        "restoration_priority": _policy_full["dm_response"]["restoration_priority"],
        "source": _policy_full["dm_response"]["source"],
    },
}

with open(PROCESSED / "shock_parameters.json") as f:
    _shock_full = json.load(f)

# Build city-specific shock params (no longer uniform)
def get_city_shock(city):
    """Extract city-specific shock magnitudes + recovery curves."""
    city_shocks = {}
    for shock_type in ["flood", "drought", "economic_crisis"]:
        if shock_type not in _shock_full:
            continue
        s = _shock_full[shock_type]

        # Get city-specific parameters
        if "city_parameters" in s and city in s["city_parameters"]:
            params = {k: v for k, v in s["city_parameters"][city].items()
                      if k != "rationale"}
        else:
            # Fallback to first city's params
            continue

        # Get city-specific recovery curve
        if "recovery_curve" in s and city in s["recovery_curve"]:
            params["recovery_curve"] = s["recovery_curve"][city]

        # Add trigger months and source
        if "trigger_months" in s:
            params["trigger_months"] = s["trigger_months"]
        params["source"] = s.get("source", "")

        city_shocks[shock_type] = params
    return city_shocks

# Trust mechanics (same for all cities — behavioural model)
TRUST_MECHANICS = _shock_full.get("trust_mechanics", {})

# -----------------------------------------------------------------------
# Build config per city
# -----------------------------------------------------------------------
config = {}
for city in CITIES:
    # Demographics
    demo_row = demo_df[demo_df["city"] == city].iloc[0]

    # Income groups
    city_income = income_df[income_df["city"] == city]
    agent_groups = {}
    for _, ig in city_income.iterrows():
        agent_groups[ig["income_group"]] = {
            "fraction":      float(ig["group_fraction"]),
            "lognorm_mean":  float(ig["lognorm_mean"]),
            "lognorm_sigma": float(ig["lognorm_sigma"]),
            "annual_income_mean": float(ig["annual_income_mean"]),
        }

    # Monthly supply arrays (12 values)
    city_water = water_df[water_df["city"] == city].sort_values("month")
    city_elec  = elec_df[elec_df["city"] == city].sort_values("month")
    city_food  = food_df[food_df["city"] == city].sort_values("month")

    supply_monthly = {
        "water_mld":              city_water["effective_mld"].tolist(),
        "water_per_hh_lpd":       city_water["water_per_hh_lpd"].tolist(),
        "water_seasonal_mult":    city_water["seasonal_multiplier"].tolist(),
        "electricity_mu":         city_elec["monthly_mu"].tolist(),
        "electricity_per_hh_kwh": city_elec["electricity_per_hh_kwh"].tolist(),
        "food_total_kg":          city_food["total_food_kg"].tolist(),
        "food_per_hh_kg":         city_food["food_per_hh_kg"].tolist(),
    }

    # Demand calibration per group (now includes PDS decomposition)
    city_demand = demand_df[demand_df["city"] == city]
    demand_by_group = {}
    for _, d in city_demand.iterrows():
        demand_by_group[d["income_group"]] = {
            "food_demand_kg_hh":       float(d["food_demand_kg_hh"]),
            "pds_food_kg_hh":          float(d.get("pds_food_kg_hh", 0)),
            "market_food_kg_hh":       float(d.get("market_food_kg_hh", 0)),
            "pds_share":               float(d.get("pds_share", 0.3)),
            "electricity_demand_kwh_hh": float(d["electricity_demand_kwh_hh"]),
            "water_demand_lpd_hh":     float(d["water_demand_lpd_hh"]),
        }

    # Resource interactions (same for all cities — state-level)
    res_interactions = {
        k: v["coefficient"] for k, v in interactions.items()
        if k != "metadata" and isinstance(v, dict) and "coefficient" in v
    }

    # Electricity growth
    growth_rate = float(city_elec["monthly_growth_rate"].iloc[0]) if "monthly_growth_rate" in city_elec.columns else 0.005

    config[city] = {
        "num_agents": 500,
        "timestep": "month",
        "population": int(demo_row["population"]),
        "households": int(demo_row["households"]),
        "avg_household_size": float(demo_row["avg_household_size"]),
        "literacy_rate": float(demo_row["literacy_rate"]),
        "agent_groups": agent_groups,
        "supply_monthly": supply_monthly,
        "demand_by_group": demand_by_group,
        "resource_interactions": res_interactions,
        "electricity_growth_rate_monthly": growth_rate,
        "policy": POLICY_PARAMS,
        "shock": get_city_shock(city),           # FIX 1: city-specific
        "trust_mechanics": TRUST_MECHANICS,      # FIX 3: formal trust definition
        "food_supply_note": "food_per_hh_kg is PDS ration only (~25-60% of total for poor, ~10% for non-poor). Market supply fills the remainder.",
    }

    print(f"  {city}: {len(agent_groups)} groups, 12-month supply, {len(demand_by_group)} demand profiles")

out_path = PROCESSED / "model_config_by_city.json"
with open(out_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"\nSaved: {out_path}")

# -----------------------------------------------------------------------
# Verification: city-specific shocks + recovery curves + trust
# -----------------------------------------------------------------------
print("\n--- CITY-SPECIFIC SHOCK COMPARISON ---")
print(f"  {'City':20s} | {'Flood Water':12s} | {'Drought Water':14s} | {'Econ Income':12s} | {'Flood Recovery':20s}")
print(f"  {'':20s} | {'Reduction':12s} | {'Reduction':14s} | {'Reduction':12s} | {'Curve':20s}")
print(f"  {'-'*20} | {'-'*12} | {'-'*14} | {'-'*12} | {'-'*20}")
for city in CITIES:
    s = config[city]["shock"]
    fw = s.get("flood",{}).get("water_supply_reduction", "N/A")
    dw = s.get("drought",{}).get("water_supply_reduction", "N/A")
    ei = s.get("economic_crisis",{}).get("income_reduction_pct", "N/A")
    rc = s.get("flood",{}).get("recovery_curve", [])
    print(f"  {city:20s} | {str(fw):12s} | {str(dw):14s} | {str(ei):12s} | {str(rc)}")

print("\n--- TRUST MECHANICS ---")
tm = config["Bengaluru"].get("trust_mechanics", {})
if "system_effects" in tm:
    for effect, rule in tm["system_effects"].items():
        print(f"  {effect}: threshold={rule.get('threshold','?')}, rule={rule.get('rule','?')[:60]}")

print("\nStep 9 complete (v2: city-specific shocks + recovery curves + trust mechanics).")

