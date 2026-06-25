"""
Step 5 (FIXED): Electricity Supply — Peak Stress Variability + Per-HH Units
-----------------------------------------------------------------------------
Fix 3: Add month-level supply variability (±5% random noise for normal months,
       ±10% for peak demand months Mar-May and Jun-Sep)
       This creates realistic supply fluctuations without shock events.
       Shock multipliers (e.g., 0.8 for outage) are added as separate columns
       so the ABM can apply them conditionally.

Fix 4: Add electricity_per_hh_kwh column for direct ABM allocation
"""
import pathlib
import pandas as pd
import numpy as np
import re

DATASETS  = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

RANDOM_SEED = 42  # reproducible stochastic output
rng = np.random.default_rng(RANDOM_SEED)

CITY_NAME_MAP = {
    "Bengaluru":          "Bengaluru",
    "Mysuru":             "Mysuru",
    "Mangaluru":          "Mangaluru",
    "Hubballi\u2013Dharwad":   "Hubballi-Dharwad",
    "Hubballi-Dharwad":   "Hubballi-Dharwad",
    "Belagavi":           "Belagavi",
}

# -----------------------------------------------------------------------
# A. Load snapshot
# -----------------------------------------------------------------------
edf = pd.read_excel(DATASETS / "electricity consumption data.xlsx")
edf = edf.iloc[:, :4].copy()
edf.columns = ["city_raw", "annual_mu_raw", "monthly_kwh_raw", "kwh_per_person_year"]
edf["city"]      = edf["city_raw"].astype(str).str.strip().map(CITY_NAME_MAP)
edf["annual_mu"] = pd.to_numeric(edf["annual_mu_raw"], errors="coerce")
edf = edf.dropna(subset=["city", "annual_mu"])
edf = edf[edf["city"].isin(CITY_NAME_MAP.values())]

# -----------------------------------------------------------------------
# B. Load time series for growth rate
# -----------------------------------------------------------------------
ts = pd.read_csv(DATASETS / "karnataka_electricity_timeseries.csv")
ts.columns = [c.strip() for c in ts.columns]

def parse_fy(yr):
    parts = str(yr).split("-")
    return int("20" + parts[1]) if len(parts) == 2 and len(parts[1]) == 2 else int(parts[0])

ts["year"] = ts["Year"].apply(parse_fy)
energy_col = next((c for c in ts.columns if "energy input" in c.lower()), None)
for col in ts.columns[1:]:
    ts[col] = pd.to_numeric(ts[col].astype(str).str.replace(",","").str.strip(), errors="coerce")

ts = ts.dropna(subset=[energy_col]).sort_values("year")
ts["yoy_growth"] = ts[energy_col].pct_change()
mean_annual_growth  = ts["yoy_growth"].dropna().mean()
monthly_growth_rate = mean_annual_growth / 12
print(f"Annual energy growth: {mean_annual_growth:.2%}, monthly: {monthly_growth_rate:.4%}")

# -----------------------------------------------------------------------
# C. Monthly demand multipliers + variability bands (Fix 3)
#
# Format: (base_mult, variability_range, is_peak_month)
# Normal months: ±5% uniform noise
# Peak months (summer + monsoon): ±10% noise (grid stress, load shedding)
# The variability is BAKED IN at data generation to represent expected
# supply uncertainty. The ABM can further apply shock multipliers on top.
# -----------------------------------------------------------------------
MONTHLY_ELEC = {
    1:  (0.95, 0.05, False, "Jan"),   # Winter — stable
    2:  (0.95, 0.05, False, "Feb"),
    3:  (1.10, 0.10, True,  "Mar"),   # Summer peak — AC load
    4:  (1.10, 0.10, True,  "Apr"),
    5:  (1.10, 0.10, True,  "May"),
    6:  (1.05, 0.10, True,  "Jun"),   # Monsoon — pumping + humid; grid stress
    7:  (1.05, 0.10, True,  "Jul"),
    8:  (1.05, 0.10, True,  "Aug"),
    9:  (1.05, 0.10, True,  "Sep"),
    10: (0.90, 0.05, False, "Oct"),   # Post-monsoon
    11: (0.90, 0.05, False, "Nov"),
    12: (0.90, 0.05, False, "Dec"),
}

demo       = pd.read_csv(PROCESSED / "city_demographics.csv")
hh_lookup  = demo.set_index("city")["households"].to_dict()
pop_lookup = demo.set_index("city")["population"].to_dict()

BASE_YEAR = 2023
records = []

for _, cr in edf.iterrows():
    city      = cr["city"]
    annual_mu = float(cr["annual_mu"])
    hh        = hh_lookup.get(city, 1)
    monthly_base_mu = annual_mu / 12

    for month, (base_mult, vrange, is_peak, mname) in MONTHLY_ELEC.items():
        # Stochastic noise — seeded for reproducibility (Fix 3)
        noise = rng.uniform(-vrange, vrange)
        effective_mult = round(base_mult + noise, 4)

        monthly_mu     = round(monthly_base_mu * effective_mult, 3)
        kwh_per_hh     = round((monthly_mu * 1_000_000) / hh, 1) if hh > 0 else 0.0

        # Shock column: ABM applies these conditionally; base is 1.0 (no shock)
        # During blackout/overload shock, ABM sets shock_multiplier < 1.0
        shock_multiplier_base = 1.0

        records.append({
            "city":                        city,
            "annual_mu_base":              round(annual_mu, 1),
            "base_year":                   BASE_YEAR,
            "monthly_growth_rate":         round(monthly_growth_rate, 6),
            "households":                  int(hh),
            "month":                       month,
            "month_name":                  mname,
            "is_peak_month":               is_peak,
            "base_demand_multiplier":      base_mult,
            "noise_applied":               round(noise, 4),
            "effective_demand_multiplier": effective_mult,
            "monthly_mu":                  monthly_mu,
            "electricity_per_hh_kwh":      kwh_per_hh,   # Fix 4
            "gruha_jyothi_free_units":     200,
            "above_free_threshold_kwh":    max(0, round(kwh_per_hh - 200, 1)),
            "shock_multiplier_base":       shock_multiplier_base,
        })

out_df = pd.DataFrame(records)
out_path = PROCESSED / "electricity_supply_monthly.csv"
out_df.to_csv(out_path, index=False)
print(f"Saved: {out_path}")

# -----------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------
print("\n--- Monthly electricity per HH (kWh) ---")
pivot = out_df.pivot(index="city", columns="month_name", values="electricity_per_hh_kwh")
pivot = pivot[["Jan","Mar","Jun","Oct","Dec"]]
print(pivot.round(1).to_string())

print("\n--- Base mult vs effective (noise applied) for Bengaluru ---")
ben = out_df[out_df["city"]=="Bengaluru"][["month_name","base_demand_multiplier","noise_applied","effective_demand_multiplier","electricity_per_hh_kwh","is_peak_month"]]
print(ben.to_string(index=False))

print(f"\nGruha Jyothi: 200 kWh free. Bengaluru HH above threshold in peak:")
over = out_df[(out_df["city"]=="Bengaluru") & (out_df["above_free_threshold_kwh"]>0)]
print(over[["month_name","electricity_per_hh_kwh","above_free_threshold_kwh"]].to_string(index=False))

print("\nStep 5 complete (FIXED).")
