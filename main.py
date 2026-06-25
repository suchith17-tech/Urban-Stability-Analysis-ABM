"""
main.py — Phase 5: Data-driven 5-city baseline simulation

Runs 12-month (1 year) baseline for all 5 Karnataka cities.
Exports results to results/{city}_baseline.csv
Prints summary table at the end.
"""
import sys
import pathlib
import pandas as pd

# Add project root to path so imports work
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from data.scripts.config_loader import load_city_config, CITIES
from model.urban_model import UrbanStabilityModel

RESULTS_DIR = pathlib.Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

NUM_STEPS = 12   # 1 full year (monthly timestep)

# -----------------------------------------------------------------------
# RUN BASELINE FOR ALL 5 CITIES
# -----------------------------------------------------------------------
summaries = []

for city in CITIES:
    print(f"\n{'='*50}")
    print(f"Running: {city}  ({NUM_STEPS} monthly steps)")
    print(f"{'='*50}")

    cfg   = load_city_config(city)
    cfg["num_steps"] = NUM_STEPS
    model = UrbanStabilityModel(config=cfg)

    while model.running and model.current_step < NUM_STEPS:
        model.step()
        m = model.current_step
        print(
            f"  Month {m:02d} | USI={model.current_usi:.3f} "
            f"Gini={model.current_gini:.3f} "
            f"Trust={model.current_C:.3f} "
            f"S_R={model.current_S_R:.3f} "
            f"Shocks={model.shock_module.active_shock_names or 'none'}"
        )

    # Export city results
    df = model.datacollector.get_model_vars_dataframe()
    out = RESULTS_DIR / f"{city.replace(' ', '_').replace('-', '_')}_baseline.csv"
    df.to_csv(out)
    print(f"  Saved: {out}")

    summaries.append(model.get_summary())

# -----------------------------------------------------------------------
# SUMMARY TABLE
# -----------------------------------------------------------------------
print(f"\n{'='*70}")
print("BASELINE SIMULATION SUMMARY — ALL CITIES (12 months, no forced shocks)")
print(f"{'='*70}")

summary_df = pd.DataFrame(summaries)
summary_df = summary_df.set_index("city")

# Print formatted table
col_width = 12
header = (
    f"{'City':22s} | {'Final USI':>10} | {'Gini':>6} | "
    f"{'Trust':>6} | {'S_R':>5} | {'Collapse':>8}"
)
print(f"\n{header}")
print("-" * len(header))
for city, row in summary_df.iterrows():
    collapse_str = "YES ❗" if row["collapse"] else "no"
    print(
        f"  {city:20s} | {row['final_usi']:>10.3f} | {row['final_gini']:>6.3f} | "
        f"{row['final_trust']:>6.3f} | {row['final_S_R']:>5.3f} | {collapse_str:>8}"
    )

print(f"\nResults saved in: {RESULTS_DIR.absolute()}/")
print("Phase 5 baseline run complete.")