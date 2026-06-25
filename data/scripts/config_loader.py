"""
config_loader.py
----------------
Loads model_config_by_city.json and returns a model-ready config dict
for a given city. This is the bridge between the data pipeline (Phases 1-4)
and the simulation engine (Phase 5).

Usage:
    from data.scripts.config_loader import load_city_config
    cfg = load_city_config("Bengaluru")
    model = UrbanStabilityModel(config=cfg)
"""
import json
import pathlib

_DEFAULT_JSON = pathlib.Path(
    pathlib.Path(__file__).parent.parent / "processed" / "model_config_by_city.json"
)

CITIES = ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi-Dharwad", "Belagavi"]


def load_city_config(city: str, json_path=None) -> dict:
    """
    Load and flatten the data-driven config for a specific city.

    Returns a dict with all keys the simulation engine needs:
      - demographics, agent_groups, supply_monthly, demand_by_group,
        resource_interactions, policy, shock, trust_mechanics
    """
    path = pathlib.Path(json_path) if json_path else _DEFAULT_JSON
    with open(path, encoding="utf-8") as f:
        all_configs = json.load(f)

    if city not in all_configs:
        raise ValueError(f"City '{city}' not found. Available: {list(all_configs.keys())}")

    raw = all_configs[city]

    # -----------------------------------------------------------------------
    # Build agent group specs: list of (group_name, fraction, lognorm params)
    # Used by UrbanAgent to draw income + assign group
    # -----------------------------------------------------------------------
    agent_groups = []
    for group_name, gdata in raw["agent_groups"].items():
        agent_groups.append({
            "name":               group_name,
            "fraction":           gdata["fraction"],
            "lognorm_mean":       gdata["lognorm_mean"],
            "lognorm_sigma":      gdata["lognorm_sigma"],
            "annual_income_mean": gdata["annual_income_mean"],
        })

    # -----------------------------------------------------------------------
    # Supply: 12-month arrays indexed by month (0=Jan, 11=Dec)
    # -----------------------------------------------------------------------
    supply = raw["supply_monthly"]
    supply_monthly = {
        "water_lpd_hh":   supply["water_per_hh_lpd"],        # litres/HH/day
        "food_kg_hh":     supply["food_per_hh_kg"],          # kg/HH/month (PDS)
        "elec_kwh_hh":    supply["electricity_per_hh_kwh"],  # kWh/HH/month
        "water_mld":      supply["water_mld"],
        "water_seasonal": supply["water_seasonal_mult"],
    }

    # -----------------------------------------------------------------------
    # Demand: per-group calibrated values
    # -----------------------------------------------------------------------
    demand_by_group = {}
    for grp, ddata in raw["demand_by_group"].items():
        demand_by_group[grp] = {
            "food_total_kg":    ddata["food_demand_kg_hh"],
            "food_pds_kg":      ddata["pds_food_kg_hh"],
            "food_market_kg":   ddata["market_food_kg_hh"],
            "pds_share":        ddata["pds_share"],
            "elec_kwh":         ddata["electricity_demand_kwh_hh"],
            "water_lpd":        ddata["water_demand_lpd_hh"],
        }

    # -----------------------------------------------------------------------
    # Resource interaction coefficients
    # -----------------------------------------------------------------------
    interactions = raw.get("resource_interactions", {})

    # -----------------------------------------------------------------------
    # Policy (with FHTC city-specific gap)
    # -----------------------------------------------------------------------
    policy = raw["policy"]
    fhtc_gap = policy.get("fhtc_water_access_gap", {})
    water_access_gap = fhtc_gap.get(city, 0.0) if isinstance(fhtc_gap, dict) else 0.0

    # -----------------------------------------------------------------------
    # Shock: city-specific parameters
    # -----------------------------------------------------------------------
    shock = raw.get("shock", {})

    # -----------------------------------------------------------------------
    # Trust mechanics (ABM behavioural model)
    # -----------------------------------------------------------------------
    trust_mechanics = raw.get("trust_mechanics", {})

    # -----------------------------------------------------------------------
    # Assemble final config dict
    # -----------------------------------------------------------------------
    config = {
        # Identity
        "city":                city,

        # Simulation control
        "num_agents":          raw.get("num_agents", 500),
        "num_steps":           12,          # 1 year = 12 monthly steps
        "random_seed":         42,
        "timestep":            "month",

        # Demographics
        "population":          raw["population"],
        "households":          raw["households"],
        "avg_household_size":  raw["avg_household_size"],
        "literacy_rate":       raw["literacy_rate"],

        # Agent income groups (data-driven, not synthetic)
        "agent_groups":        agent_groups,

        # Resource supply (monthly arrays)
        "supply_monthly":      supply_monthly,

        # Resource demand (per income group)
        "demand_by_group":     demand_by_group,

        # Resource coupling (interaction coefficients)
        "resource_interactions": interactions,
        "water_access_gap_pct": water_access_gap,

        # Policy schemes
        "anna_bhagya": {
            "enabled": True,
            "rice_kg_pp_pm":   policy["anna_bhagya"]["rice_kg_per_person_per_month"],
            "eligible_groups": ["extreme_poor", "bpl_poor"],
        },
        "gruha_jyothi": {
            "enabled": True,
            "free_units_kwh":  policy["gruha_jyothi"]["free_units_per_month"],
        },
        "gruha_lakshmi": {
            "enabled": True,
            "transfer_rs_pm":  policy["gruha_lakshmi"]["transfer_rs_per_month"],
            "eligible_groups": ["extreme_poor", "bpl_poor"],
        },
        "dm_response": {
            "relief_duration_months": policy["dm_response"]["relief_duration_months"],
        },
        "water_norm_lpcd": policy["water_norm_lpcd"],

        # Legacy policy dict (keeps old PolicyEngine compatible)
        "policy": {
            "pricing_multiplier": {"enabled": False, "value": 1.0},
            "subsidy":            {"enabled": False, "rate": 0.0, "threshold_percentile": 30},
            "consumption_cap":    {"enabled": False, "cap_value": 9999},
        },

        # Shock (city-specific from Phase 4)
        "shock": shock,

        # Trust mechanics (from Phase 4)
        "trust_mechanics": trust_mechanics,
        "trust_initial":   trust_mechanics.get("definition", {}).get("initial_value", 0.7),
        "trust_weight_personal": 0.8,   # alpha for social influence blend

        # USI weights
        "usi_weights":           [0.25, 0.25, 0.25, 0.25],
        "collapse_threshold":    0.2,
        "collapse_consecutive_steps": 3,
        "oscillation_window":    5,

        # Network
        "network_type": "erdos_renyi",
        "avg_degree":   8,

        # Electricity growth
        "electricity_growth_rate_monthly": raw.get("electricity_growth_rate_monthly", 0.005),
    }

    return config


def get_all_city_configs(json_path=None) -> dict:
    """Return config dicts for all 5 cities."""
    return {city: load_city_config(city, json_path) for city in CITIES}


if __name__ == "__main__":
    # Quick test
    for city in CITIES:
        cfg = load_city_config(city)
        ag = cfg["agent_groups"]
        s  = cfg["supply_monthly"]
        print(f"\n{city}:")
        print(f"  Agents: {cfg['num_agents']}, HH: {cfg['households']:,}")
        print(f"  Groups: {[g['name'] for g in ag]}")
        print(f"  Water Jan: {s['water_lpd_hh'][0]:.0f} L/HH/day")
        print(f"  Food Jan:  {s['food_kg_hh'][0]:.1f} kg/HH/month (PDS)")
        print(f"  Elec Jan:  {s['elec_kwh_hh'][0]:.0f} kWh/HH/month")
        shk = cfg["shock"]
        if "flood" in shk:
            print(f"  Flood water reduction: {shk['flood']['water_supply_reduction']}")
            print(f"  Flood recovery curve:  {shk['flood']['recovery_curve']}")
    print("\nconfig_loader OK")
