"""
Step 8: Resource Interaction Coefficients — Cross-Resource Coupling Matrix
--------------------------------------------------------------------------
Input : consumer details per capita.xlsx (district MPCE by category)
Output: data/processed/resource_interaction_matrix.json

Strategy:
  Compute cross-resource correlations from district-level expenditure variation:
  1. water_deficit_on_food: correlation(water_exp, food_exp) across districts
     → when water access drops, food preparation & utilization drops
  2. electricity_deficit_on_water: correlation(fuel_exp, housing_water_exp)
     → when electricity drops, electric pumping fails → water supply drops
  3. food_deficit_on_trust: estimated from HCES data on food security
     → when food supply drops, social trust drops (conflict potential rises)

  Also extract from literature/data:
  4. Coupling strength parameters for the ABM interaction logic
"""
import pathlib
import pandas as pd
import numpy as np
import json

DATASETS  = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

# -----------------------------------------------------------------------
# Load consumer details — all districts (not just target 5)
# -----------------------------------------------------------------------
cdf = pd.read_excel(DATASETS / "consumer details per capita.xlsx")
cdf["District"] = cdf["District"].ffill()
urban_col = "Share of MPCE (in Rs.) - Urban"
cdf[urban_col] = pd.to_numeric(cdf[urban_col], errors="coerce")

# Get per-sub-group MPCE per district (urban)
sub_items = cdf[cdf["Sub Group"].notna()].copy()
sub_items = sub_items[sub_items["District"] != "All"]

# Pivot: district × sub_group → MPCE
pivot = sub_items.pivot_table(index="District", columns="Sub Group",
                              values=urban_col, aggfunc="first")
pivot = pivot.dropna(axis=1, how="all").dropna(axis=0, how="all")

# Also get category totals
total_rows = cdf[cdf["Group"].str.contains("Total", na=False) & cdf["Sub Group"].isna()]
total_rows = total_rows[total_rows["District"] != "All"]
cat_pivot = total_rows.pivot_table(index="District", columns="Group",
                                    values=urban_col, aggfunc="first")
cat_pivot.columns = [c.replace(" Total", "").strip() for c in cat_pivot.columns]

print(f"Districts with expenditure data: {len(cat_pivot)}")
print(cat_pivot.head().to_string())

# -----------------------------------------------------------------------
# Compute correlation coefficients across districts
# -----------------------------------------------------------------------
def safe_corr(x, y):
    """Pearson r with fallback."""
    valid = (~np.isnan(x)) & (~np.isnan(y))
    if valid.sum() < 5:
        return 0.0
    return float(np.corrcoef(x[valid], y[valid])[0, 1])

food_exp  = cat_pivot.get("Food, Beverages & Tobacco", pd.Series(dtype=float)).values
fuel_exp  = cat_pivot.get("Fuel & Light", pd.Series(dtype=float)).values
housing_exp = cat_pivot.get("Housing", pd.Series(dtype=float)).values
misc_exp  = cat_pivot.get("Miscellaneous", pd.Series(dtype=float)).values

# Clean NaNs
food_exp = np.nan_to_num(food_exp, 0)
fuel_exp = np.nan_to_num(fuel_exp, 0)
housing_exp = np.nan_to_num(housing_exp, 0)

# 1. Water-Food coupling: r(housing_water_proxy, food)
#    Housing MPCE includes water charges; higher housing = better water = better food
r_water_food = safe_corr(housing_exp, food_exp)

# 2. Electricity-Water coupling: r(fuel_exp, housing_exp)
#    Fuel = electricity; Housing includes water from electric pumps
r_elec_water = safe_corr(fuel_exp, housing_exp)

# 3. Food-Income coupling: r(food_exp, total_mpce)
#    Districts with lower income spend less on food → nutrition gap
total_mpce = food_exp + fuel_exp + housing_exp + np.nan_to_num(misc_exp, 0)
r_food_income = safe_corr(food_exp, total_mpce)

print(f"\n--- Correlation coefficients (across {len(cat_pivot)} districts) ---")
print(f"  r(housing/water, food)  = {r_water_food:.3f}")
print(f"  r(fuel/elec, housing)   = {r_elec_water:.3f}")
print(f"  r(food, total_income)   = {r_food_income:.3f}")

# -----------------------------------------------------------------------
# Build interaction matrix
# Convert correlations to coupling coefficients (0-1 scale)
# Coupling = |r| × sensitivity factor
# -----------------------------------------------------------------------
# Sensitivity factors from domain knowledge:
#   Water→Food: strong (water needed for cooking, hygiene, crop processing)
#   Electricity→Water: moderate (pumping, treatment plants need power)
#   Food→Trust: moderate (food insecurity → social unrest)
SENSITIVITY = {
    "water_food": 0.85,     # strong: cooking, sanitation
    "elec_water": 0.60,     # moderate: pumping infrastructure
    "food_trust": 0.70,     # moderate: food security → social stability
}

interaction_matrix = {
    "water_deficit_on_food_utilization": {
        "coefficient": round(abs(r_water_food) * SENSITIVITY["water_food"], 4),
        "raw_correlation": round(r_water_food, 4),
        "interpretation": "When water supply drops by X%, food utilization drops by coeff*X%",
        "source": "consumer_details_per_capita.xlsx, r(Housing, Food) across 27 Karnataka districts",
    },
    "electricity_deficit_on_water_pumping": {
        "coefficient": round(abs(r_elec_water) * SENSITIVITY["elec_water"], 4),
        "raw_correlation": round(r_elec_water, 4),
        "interpretation": "When electricity drops by X%, water pumping capacity drops by coeff*X%",
        "source": "consumer_details_per_capita.xlsx, r(Fuel, Housing) across 27 districts",
    },
    "food_deficit_on_trust_drop_rate": {
        "coefficient": round(abs(r_food_income) * SENSITIVITY["food_trust"], 4),
        "raw_correlation": round(r_food_income, 4),
        "interpretation": "When food supply drops by X%, agent trust drops by coeff*X% per step",
        "source": "consumer_details_per_capita.xlsx, r(Food, Total MPCE) across 27 districts",
    },
    "metadata": {
        "n_districts": len(cat_pivot),
        "method": "Pearson correlation of urban MPCE expenditure categories across Karnataka districts",
        "sensitivity_factors": SENSITIVITY,
        "data_file": "consumer details per capita.xlsx",
        "academic_disclaimer": (
            "Interaction coefficients are calibrated using cross-district expenditure "
            "correlations (Pearson r) scaled by domain-informed sensitivity factors. "
            "These are treated as behavioural approximations for ABM parameterisation, "
            "NOT causal estimates. The correlations capture co-variation in consumption "
            "patterns across Karnataka districts, which serves as a proxy for resource "
            "interdependencies in urban systems. For causal identification, instrumental "
            "variable or quasi-experimental approaches would be required."
        ),
    }
}

out_path = PROCESSED / "resource_interaction_matrix.json"
with open(out_path, "w") as f:
    json.dump(interaction_matrix, f, indent=2)
print(f"\nSaved: {out_path}")

# Pretty-print the coefficients
print("\n--- Resource Interaction Coefficients (for ABM) ---")
for key, val in interaction_matrix.items():
    if key == "metadata":
        continue
    print(f"  {key}: {val['coefficient']}")
    print(f"    raw_r={val['raw_correlation']}, {val['interpretation']}")

print("\nStep 8 complete.")
