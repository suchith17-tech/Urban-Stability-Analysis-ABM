"""
Step 4 (FIXED): Water Supply — City-Specific Seasonal Multipliers + Per-HH Units
--------------------------------------------------------------------------------
Fix 1: City-specific seasonal multipliers based on hydrology:
  - Belagavi  : high rain-dependence (SW monsoon dominant)  → wider swing
  - Bengaluru : moderate (Cauvery + groundwater balance)
  - Mangaluru : coastal, stable rainfall                     → narrower swing
  - Hubballi  : semi-arid interior                           → severe summer
  - Mysuru    : moderate Cauvery; less monsoon swing than Belagavi

Fix 4: Add water_per_hh_lpd column (litres per household per day)
       which is the per-HH unit the ABM allocation logic uses
"""
import pathlib
import pandas as pd
import numpy as np

DATASETS  = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

CITY_NAME_MAP = {
    "Bengaluru":          "Bengaluru",
    "Mysuru":             "Mysuru",
    "Mangaluru":          "Mangaluru",
    "Hubballi\u2013Dharwad":   "Hubballi-Dharwad",
    "Hubballi-Dharwad":   "Hubballi-Dharwad",
    "Belagavi":           "Belagavi",
}

# -----------------------------------------------------------------------
# City-specific seasonal multipliers (Fix 1)
# Based on: Karnataka SW Monsoon variability, Cauvery basin hydrology,
# coastal vs. interior aquifer recharge patterns
# Rationale documented per city:
# -----------------------------------------------------------------------
#   Month index: 1=Jan, 2=Feb, 3=Mar, 4=Apr, 5=May, 6=Jun,
#                7=Jul, 8=Aug, 9=Sep, 10=Oct, 11=Nov, 12=Dec
CITY_SEASONAL_WATER = {
    "Bengaluru": {
        # Cauvery + TG Halli — moderate; summer demand high but urban infrastructure absorbs shock
        1:1.00, 2:1.00, 3:0.70, 4:0.70, 5:0.70,
        6:1.15, 7:1.15, 8:1.15, 9:1.15,
        10:0.90, 11:0.90, 12:0.90,
    },
    "Mysuru": {
        # Cauvery-fed KRS reservoir; moderate summer drop; monsoon fills but not extreme
        1:1.00, 2:1.00, 3:0.75, 4:0.75, 5:0.75,
        6:1.12, 7:1.12, 8:1.12, 9:1.12,
        10:0.92, 11:0.92, 12:0.92,
    },
    "Mangaluru": {
        # Coastal — Netravathi river; among highest rainfall in India (3500mm+)
        # Monsoon very strong; summer still relatively stable (river perennial)
        1:1.00, 2:1.00, 3:0.85, 4:0.85, 5:0.85,
        6:1.35, 7:1.35, 8:1.35, 9:1.35,
        10:0.95, 11:0.95, 12:0.95,
    },
    "Hubballi-Dharwad": {
        # Semi-arid interior; Dharwad receives ~800mm; groundwater-dependent
        # Severe summer depletion; modest monsoon recharge
        1:1.00, 2:1.00, 3:0.55, 4:0.55, 5:0.55,
        6:1.10, 7:1.10, 8:1.10, 9:1.10,
        10:0.85, 11:0.85, 12:0.85,
    },
    "Belagavi": {
        # Malaprabha catchment; highly rain-fed; SW Monsoon dominant
        # Largest seasonal swing of all 5 cities
        1:1.00, 2:1.00, 3:0.55, 4:0.55, 5:0.55,
        6:1.30, 7:1.30, 8:1.30, 9:1.30,
        10:0.88, 11:0.88, 12:0.88,
    },
}

MONTH_META = {
    1:("Jan","Winter"),  2:("Feb","Winter"),
    3:("Mar","Summer"),  4:("Apr","Summer"),  5:("May","Summer"),
    6:("Jun","Monsoon"), 7:("Jul","Monsoon"), 8:("Aug","Monsoon"), 9:("Sep","Monsoon"),
    10:("Oct","Post-Monsoon"), 11:("Nov","Post-Monsoon"), 12:("Dec","Post-Monsoon"),
}

LPCD_NORM = 135

# -----------------------------------------------------------------------
# Load raw data
# -----------------------------------------------------------------------
wdf = pd.read_excel(DATASETS / "water supply data.xlsx")
wdf["city"] = wdf["City"].str.strip().map(CITY_NAME_MAP).fillna(wdf["City"].str.strip())
wdf.rename(columns={"Population": "population_source",
                     "Estimated Water Demand (MLD)": "actual_demand_mld"}, inplace=True)

demo       = pd.read_csv(PROCESSED / "city_demographics.csv")
pop_lookup = demo.set_index("city")["population"].to_dict()
hh_lookup  = demo.set_index("city")["households"].to_dict()

wdf["population"] = wdf["city"].map(pop_lookup).fillna(wdf["population_source"])
wdf["required_mld_135lpcd"] = (wdf["population"] * LPCD_NORM / 1_000_000).round(3)
wdf["base_deficit_ratio"]   = (wdf["actual_demand_mld"] / wdf["required_mld_135lpcd"]).round(4)

# -----------------------------------------------------------------------
# Generate monthly records with city-specific multipliers
# -----------------------------------------------------------------------
records = []
for _, cr in wdf.iterrows():
    city     = cr["city"]
    base_mld = cr["actual_demand_mld"]
    pop      = cr["population"]
    hh       = hh_lookup.get(city, 1)
    city_mults = CITY_SEASONAL_WATER.get(city, {m:1.0 for m in range(1,13)})

    for month in range(1, 13):
        mname, season = MONTH_META[month]
        mult      = city_mults[month]
        eff_mld   = round(base_mld * mult, 3)
        monthly_L = round(eff_mld * 30 * 1_000_000, 0)
        lpcd      = round((eff_mld * 1_000_000) / pop, 1) if pop > 0 else 0.0

        # Fix 4: per-HH unit — MLD = Million Litres/DAY, so no /30 needed
        # water_per_hh_lpd = (MLD × 1,000,000 litres/day) / households
        # Expected: ~540 L/HH/day for 135 LPCD × avg HH size 4
        water_per_hh_lpd = round((eff_mld * 1_000_000) / hh, 1) if hh > 0 else 0.0

        records.append({
            "city":                    city,
            "population":              int(pop),
            "households":              int(hh),
            "actual_demand_mld":       base_mld,
            "required_mld_135lpcd":    round(cr["required_mld_135lpcd"], 3),
            "base_deficit_ratio":      cr["base_deficit_ratio"],
            "month":                   month,
            "month_name":              mname,
            "season":                  season,
            "seasonal_multiplier":     mult,
            "effective_mld":           eff_mld,
            "monthly_litres":          int(monthly_L),
            "per_capita_lpcd":         lpcd,
            "water_per_hh_lpd":        water_per_hh_lpd,  # Fix 4
            "meets_135lpcd_standard":  lpcd >= LPCD_NORM,
        })

out_df = pd.DataFrame(records)
out_path = PROCESSED / "water_supply_monthly.csv"
out_df.to_csv(out_path, index=False)
print(f"Saved: {out_path}")

# -----------------------------------------------------------------------
# Verification: show city-differentiated summer vs monsoon
# -----------------------------------------------------------------------
print("\n--- Effective MLD: Summer (May) vs Monsoon (Jul) vs Winter (Jan) ---")
check = out_df[out_df["month_name"].isin(["Jan","May","Jul"])].pivot_table(
    index="city", columns="month_name", values="effective_mld", aggfunc="first")
check["summer_pct"] = (check["May"] / check["Jan"] * 100).round(1)
check["monsoon_pct"] = (check["Jul"] / check["Jan"] * 100).round(1)
print(check[["Jan","May","Jul","summer_pct","monsoon_pct"]].to_string())

print("\n--- Water per HH per day (litres) ---")
hh_check = out_df[out_df["month_name"].isin(["Jan","May","Jul"])].pivot_table(
    index="city", columns="month_name", values="water_per_hh_lpd", aggfunc="first")
print(hh_check[["Jan","May","Jul"]].round(1).to_string())

print("\nStep 4 complete (FIXED).")
