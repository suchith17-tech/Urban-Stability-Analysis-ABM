"""
11_run_experiments.py — Phase 6: Experiment Execution
======================================================
Runs 6 structured scenarios for all 5 Karnataka cities (24 months each).
Results are saved to results/experiments/<scenario>/<city>.csv

SCENARIOS
---------
  exp1_baseline        : No shocks, policies ON  (control group)
  exp2_flood           : Flood shock ON, policies ON
  exp3_drought         : Drought shock ON, policies ON
  exp4_economic        : Economic shock ON, policies ON
  exp5a_shock_nopolicy : All shocks ON, policies OFF
  exp5b_shock_policy   : All shocks ON, policies ON
  exp6_combined        : All shocks ON, policies ON, 24 months (stress test)

HOW SHOCKS ARE TOGGLED
-----------------------
The shock config contains 3 sub-dicts: "flood", "drought", "economic_crisis".
We selectively inject a "disabled" key to suppress individual shock types.
The ShockModule checks this key when iterating.

HOW POLICIES ARE TOGGLED
--------------------------
Each policy sub-dict (anna_bhagya, gruha_jyothi, gruha_lakshmi) has an
"enabled" key. We set it to False to turn a policy off.
PolicyEngine._assign_eligibility() reads this at model init time.
"""

import sys
import copy
import pathlib
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from data.scripts.config_loader import load_city_config, CITIES
from model.urban_model import UrbanStabilityModel

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
NUM_STEPS   = 24          # 2 full years for strong recovery visibility
RESULTS_DIR = pathlib.Path("results/experiments")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS: config overrides
# ─────────────────────────────────────────────────────────────────────────────

def _disable_all_shocks(cfg: dict) -> dict:
    """Mark all shock types as disabled."""
    for shock_type in ("flood", "drought", "economic_crisis"):
        if shock_type in cfg["shock"]:
            cfg["shock"][shock_type]["disabled"] = True
    return cfg


def _enable_only_shock(cfg: dict, shock_type: str) -> dict:
    """Enable only one shock type; disable the rest."""
    for stype in ("flood", "drought", "economic_crisis"):
        if stype in cfg["shock"]:
            cfg["shock"][stype]["disabled"] = (stype != shock_type)
    return cfg


def _enable_all_shocks(cfg: dict) -> dict:
    """Enable all shock types (remove disabled flag)."""
    for shock_type in ("flood", "drought", "economic_crisis"):
        if shock_type in cfg["shock"]:
            cfg["shock"][shock_type].pop("disabled", None)
    return cfg


def _disable_all_policies(cfg: dict) -> dict:
    """Turn all three Karnataka schemes off."""
    cfg["anna_bhagya"]["enabled"]   = False
    cfg["gruha_jyothi"]["enabled"]  = False
    cfg["gruha_lakshmi"]["enabled"] = False
    return cfg


def _enable_all_policies(cfg: dict) -> dict:
    """Turn all three Karnataka schemes on."""
    cfg["anna_bhagya"]["enabled"]   = True
    cfg["gruha_jyothi"]["enabled"]  = True
    cfg["gruha_lakshmi"]["enabled"] = True
    return cfg


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO DEFINITIONS
# Each scenario is a tuple: (id, label, config_mutator_fn)
# The mutator receives a deep copy of the base city config.
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS = [
    (
        "exp1_baseline",
        "EXP 1 — Baseline (No Shocks, Policies ON)",
        lambda cfg: _enable_all_policies(_disable_all_shocks(cfg)),
    ),
    (
        "exp2_flood",
        "EXP 2 — Flood Shock (Policies ON)",
        lambda cfg: _enable_all_policies(_enable_only_shock(cfg, "flood")),
    ),
    (
        "exp3_drought",
        "EXP 3 — Drought Shock (Policies ON)",
        lambda cfg: _enable_all_policies(_enable_only_shock(cfg, "drought")),
    ),
    (
        "exp4_economic",
        "EXP 4 — Economic Shock (Policies ON)",
        lambda cfg: _enable_all_policies(_enable_only_shock(cfg, "economic_crisis")),
    ),
    (
        "exp5a_shock_nopolicy",
        "EXP 5A — All Shocks ON, Policies OFF",
        lambda cfg: _disable_all_policies(_enable_all_shocks(cfg)),
    ),
    (
        "exp5b_shock_policy",
        "EXP 5B — All Shocks ON, Policies ON",
        lambda cfg: _enable_all_policies(_enable_all_shocks(cfg)),
    ),
    (
        "exp6_combined",
        "EXP 6 — Combined Stress (All Shocks + All Policies, 24 months)",
        lambda cfg: _enable_all_policies(_enable_all_shocks(cfg)),
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_scenario(scenario_id: str, label: str, mutator, city: str) -> pd.DataFrame:
    """
    Run one scenario for one city and return the time-series DataFrame.
    """
    # Start from a guaranteed-fresh deep copy of the city config
    cfg = copy.deepcopy(load_city_config(city))
    cfg["num_steps"] = NUM_STEPS

    # Apply scenario-specific overrides
    cfg = mutator(cfg)

    model = UrbanStabilityModel(config=cfg)

    rows = []
    while model.running and model.current_step < NUM_STEPS:
        model.step()
        s = model.current_step
        rows.append({
            "step":           s,
            "month":          ((s - 1) % 12) + 1,
            "year":           ((s - 1) // 12) + 1,
            "USI":            round(model.current_usi,   4),
            "Gini":           round(model.current_gini,  4),
            "S_R":            round(model.current_S_R,   4),
            "Trust":          round(model.current_C,     4),
            "active_shocks":  str(model.shock_module.active_shock_names or []),
            "city":           city,
            "scenario":       scenario_id,
        })

    return pd.DataFrame(rows)


def main():
    all_summaries = []

    for scenario_id, label, mutator in SCENARIOS:
        out_dir = RESULTS_DIR / scenario_id
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*65}")
        print(f"  {label}")
        print(f"  Cities: {', '.join(CITIES)} | Steps: {NUM_STEPS}")
        print(f"{'='*65}")

        scenario_dfs = []

        for city in CITIES:
            print(f"\n  ▶ {city}")
            df = run_scenario(scenario_id, label, mutator, city)

            # Per-city CSV
            safe_city = city.replace(" ", "_").replace("-", "_")
            fpath = out_dir / f"{safe_city}.csv"
            df.to_csv(fpath, index=False)
            print(f"    Saved: {fpath}")

            # Console progress: final 3 months
            for _, row in df.tail(3).iterrows():
                print(
                    f"    Y{int(row.year)}M{int(row.month):02d} | "
                    f"USI={row.USI:.3f}  Gini={row.Gini:.3f}  "
                    f"Trust={row.Trust:.3f}  S_R={row.S_R:.3f}  "
                    f"Shocks={row.active_shocks}"
                )

            scenario_dfs.append(df)
            all_summaries.append({
                "scenario":    scenario_id,
                "city":        city,
                "final_USI":   df["USI"].iloc[-1],
                "min_USI":     df["USI"].min(),
                "final_Gini":  df["Gini"].iloc[-1],
                "final_Trust": df["Trust"].iloc[-1],
                "recovery_months": (df["USI"] >= 0.7).sum(),
            })

        # Combined CSV for the scenario (all cities)
        combined = pd.concat(scenario_dfs, ignore_index=True)
        combined.to_csv(out_dir / "_all_cities.csv", index=False)

    # ─────────────────────────────────────────────────────────────────────────
    # MASTER SUMMARY TABLE
    # ─────────────────────────────────────────────────────────────────────────
    summary_df = pd.DataFrame(all_summaries)
    summary_path = RESULTS_DIR / "MASTER_SUMMARY.csv"
    summary_df.to_csv(summary_path, index=False)

    print(f"\n\n{'='*70}")
    print("PHASE 6 EXPERIMENT SUMMARY")
    print(f"{'='*70}")
    print(summary_df.to_string(index=False))
    print(f"\nAll results saved in: {RESULTS_DIR.absolute()}/")
    print("Master summary: MASTER_SUMMARY.csv")


if __name__ == "__main__":
    main()
