"""
Step 7: Demand Calibration — Per-Group Resource Demand from MPCE Sub-Categories
--------------------------------------------------------------------------------
Input : consumer details per capita.xlsx (district MPCE by expenditure category)
        data/processed/income_distribution.csv (income groups per city)
Output: data/processed/demand_calibration.csv

Strategy:
  1. Extract per-district MPCE for demand-relevant sub-categories:
     - Food demand  ← "Food, Beverages & Tobacco Total" (₹/month)
     - Fuel/Energy  ← "Fuel & Light Total" (₹/month → kWh via tariff rate)
     - Housing      ← "Housing Total" (includes water charges → litres via rate)
  2. Map to 5 target cities via district names
  3. Split district MPCE into 3 income-group demand levels using group MPCE ratios:
     - extreme_poor: demand = district_demand × 0.38  (same ratios as Step 2)
     - bpl_poor:     demand = district_demand × 0.72
     - non_poor:     demand = district_demand × 1.85
  4. Convert ₹ expenditure → physical units:
     - Food ₹ → kg using avg ₹/kg (Karnataka PDS + market blend)
     - Fuel ₹ → kWh using BESCOM avg tariff ₹/kWh
     - Housing water component → litres using avg water tariff ₹/kL

Output: city | income_group | food_demand_kg | water_demand_lpd |
        electricity_demand_kwh | food_exp_rs | fuel_exp_rs | housing_exp_rs
"""
import pathlib
import pandas as pd
import numpy as np

DATASETS  = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

# -----------------------------------------------------------------------
# Conversion rates (Karnataka urban averages, 2024)
# -----------------------------------------------------------------------
# Food: weighted avg price of PDS rice (₹3/kg) + market food basket (~₹40/kg)
#   BPL basket ≈ ₹15/kg, APL basket ≈ ₹45/kg, blend ≈ ₹30/kg
FOOD_RS_PER_KG = {"extreme_poor": 15, "bpl_poor": 25, "non_poor": 45}

# Electricity: BESCOM domestic tariff (slab average)
#   0-50 units: ₹4.10, 51-100: ₹5.55, 101-200: ₹7.10, 200+: ₹8.15
#   Weighted avg for poor ≈ ₹4.5/kWh, non-poor ≈ ₹6.5/kWh
ELEC_RS_PER_KWH = {"extreme_poor": 4.5, "bpl_poor": 5.5, "non_poor": 6.5}

# Water: Karnataka Urban Water Board average domestic tariff
#   ₹6-8 per kL for first 8 kL, ₹12+ after
#   Avg ≈ ₹0.008/litre (₹8/kL)
WATER_RS_PER_LITRE = 0.008

# Fraction of Housing MPCE that goes to water charges
# Urban Karnataka: Housing MPCE is ~80% rent + 15% maintenance + ~5% water
# Source: NSSO Housing Condition Survey — water charges ≈ 5% of housing expenditure
HOUSING_WATER_FRACTION = 0.05

# Group demand ratios (same as income ratios from Step 2)
GROUP_RATIOS = {
    "extreme_poor": 0.38,
    "bpl_poor":     0.72,
    "non_poor":     1.85,
}

# -----------------------------------------------------------------------
# Load consumer details
# -----------------------------------------------------------------------
cdf = pd.read_excel(DATASETS / "consumer details per capita.xlsx")
cdf["District"] = cdf["District"].ffill()
urban_col = "Share of MPCE (in Rs.) - Urban"
cdf[urban_col] = pd.to_numeric(cdf[urban_col], errors="coerce")

DISTRICT_CITY = {
    "Bangalore Urban": "Bengaluru",
    "Mysore":          "Mysuru",
    "Dakshina Kannada":"Mangaluru",
    "Dharwad":         "Hubballi-Dharwad",
    "Belgaum":         "Belagavi",
}

# Extract totals per expenditure category per district
total_rows = cdf[cdf["Group"].str.contains("Total", na=False) & cdf["Sub Group"].isna()]

# Pivot: district × category → MPCE
cat_data = total_rows.pivot_table(index="District", columns="Group",
                                   values=urban_col, aggfunc="first")
cat_data.columns = [c.replace(" Total", "").strip().lower().replace(", ", "_").replace(" & ", "_")
                     for c in cat_data.columns]
cat_data = cat_data.rename(columns={
    "food_beverages_tobacco": "food_exp",
    "fuel_light": "fuel_exp",
    "housing": "housing_exp",
    "clothing_bedding_footwear": "clothing_exp",
    "miscellaneous": "misc_exp",
})
cat_data = cat_data.reset_index()
cat_data["city"] = cat_data["District"].map(DISTRICT_CITY)
cat_data = cat_data[cat_data["city"].notna()].copy()

print("District expenditure category MPCE (₹/person/month urban):")
print(cat_data[["city", "food_exp", "fuel_exp", "housing_exp"]].to_string(index=False))

# -----------------------------------------------------------------------
# Load income distribution for group fractions
# -----------------------------------------------------------------------
income_df = pd.read_csv(PROCESSED / "income_distribution.csv")
demo_df   = pd.read_csv(PROCESSED / "city_demographics.csv")
hh_lkp    = demo_df.set_index("city")["avg_household_size"].to_dict()

# -----------------------------------------------------------------------
# Compute per-group demand by converting ₹ expenditure → physical units
# -----------------------------------------------------------------------
records = []
for _, cr in cat_data.iterrows():
    city         = cr["city"]
    food_exp_pc  = cr["food_exp"]    # ₹/person/month
    fuel_exp_pc  = cr["fuel_exp"]    # ₹/person/month
    housing_exp_pc = cr["housing_exp"]  # ₹/person/month
    avg_hh       = hh_lkp.get(city, 4.3)

    for group, ratio in GROUP_RATIOS.items():
        # Scale district-average MPCE to this group's level
        g_food    = food_exp_pc * ratio
        g_fuel    = fuel_exp_pc * ratio
        g_housing = housing_exp_pc * ratio

        # Convert to physical units (per person per month)
        food_kg_pp   = g_food / FOOD_RS_PER_KG[group]            # kg/person/month
        elec_kwh_pp  = g_fuel / ELEC_RS_PER_KWH[group]           # kWh/person/month
        water_charge = g_housing * HOUSING_WATER_FRACTION         # ₹/person/month on water
        water_l_pp   = water_charge / WATER_RS_PER_LITRE          # litres/person/month

        # Per household per month
        food_kg_hh   = round(food_kg_pp * avg_hh, 2)
        elec_kwh_hh  = round(elec_kwh_pp * avg_hh, 2)
        water_lpd_hh = round((water_l_pp * avg_hh) / 30, 2)      # litres/HH/day

        # --- FIX 1: PDS share of total food demand ---
        # PDS covers different fractions depending on income group:
        #   extreme_poor (AAY): ~60% of food from PDS (heavily subsidised)
        #   bpl_poor:           ~35% from PDS (part PDS, part market)
        #   non_poor (APL):     ~10% from PDS (mostly market purchase)
        # The rest is bought at market prices.
        # This means PDS supply (30 kg/HH) is PARTIAL — total demand is higher.
        PDS_SHARE = {"extreme_poor": 0.60, "bpl_poor": 0.35, "non_poor": 0.10}
        pds_share = PDS_SHARE[group]
        pds_food_kg_hh    = round(food_kg_hh * pds_share, 2)
        market_food_kg_hh = round(food_kg_hh * (1 - pds_share), 2)

        # Get group fraction
        grp_row = income_df[(income_df["city"] == city) & (income_df["income_group"] == group)]
        frac = float(grp_row["group_fraction"].values[0]) if len(grp_row) > 0 else 0.33

        records.append({
            "city":                    city,
            "income_group":            group,
            "group_fraction":          round(frac, 4),
            "food_exp_rs_pp":          round(g_food, 2),
            "fuel_exp_rs_pp":          round(g_fuel, 2),
            "housing_exp_rs_pp":       round(g_housing, 2),
            "food_demand_kg_hh":       food_kg_hh,
            "pds_food_kg_hh":          pds_food_kg_hh,       # FIX 1
            "market_food_kg_hh":       market_food_kg_hh,     # FIX 1
            "pds_share":               pds_share,             # FIX 1
            "electricity_demand_kwh_hh": elec_kwh_hh,
            "water_demand_lpd_hh":     water_lpd_hh,
            "food_demand_kg_pp":       round(food_kg_pp, 2),
            "electricity_demand_kwh_pp": round(elec_kwh_pp, 2),
            "water_demand_lpd_pp":     round(water_l_pp / 30, 2),
        })

out_df = pd.DataFrame(records)
out_path = PROCESSED / "demand_calibration.csv"
out_df.to_csv(out_path, index=False)
print(f"\nSaved: {out_path}")

# -----------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------
print("\n--- Per-HH demand by group (Bengaluru) ---")
ben = out_df[out_df["city"] == "Bengaluru"]
print(ben[["income_group", "food_demand_kg_hh", "electricity_demand_kwh_hh",
           "water_demand_lpd_hh"]].to_string(index=False))

print("\n--- Sanity check: expected ranges ---")
print("  Food: 20-80 kg/HH/mo | Elec: 50-300 kWh/HH/mo | Water: 200-800 L/HH/day")
for _, r in out_df.iterrows():
    flags = []
    if not 5 <= r["food_demand_kg_hh"] <= 150: flags.append("food")
    if not 20 <= r["electricity_demand_kwh_hh"] <= 500: flags.append("elec")
    if not 50 <= r["water_demand_lpd_hh"] <= 1500: flags.append("water")
    if flags:
        print(f"  Warning: {r['city']} {r['income_group']}: {flags}")

print("\nStep 7 complete.")
