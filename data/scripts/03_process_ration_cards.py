"""
Step 3: Process Ration Card Data — Agent Class Proportions
Input : karnataka ration cards.xlsx
Output: data/processed/agent_class_proportions.csv

Ration card categories:
  AAY            = extreme poor   (Antyodaya Anna Yojana)
  PHH(NK)+PHH(K) = BPL poor       (Priority Household)
  NPHH(NK)+NPHH(K) = non-poor    (Non-Priority Household)
"""
import pathlib
import pandas as pd
import numpy as np

DATASETS  = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

RATION_FILE = DATASETS / "karnataka ration cards.xlsx"

# ---------------------------------------------------------------
# Load and clean the ration card Excel
# ---------------------------------------------------------------
raw = pd.read_excel(RATION_FILE)
print("Raw shape:", raw.shape)
print("Columns:", raw.columns.tolist())
print(raw.head(10).to_string())
print()

# Standardise column names
raw.columns = [str(c).strip() for c in raw.columns]

# The file has a known schema: Taluk Name | AAY RCs | PHH(NK) RCs | PHH(K) RCs | NPHH(NK) RCs | NPHH(K) RCs | TOTAL
# But may have multiple tables stacked. Filter to rows where Taluk Name is a real string
df = raw.copy()

# Find the actual data column — may differ across sheets
taluk_col   = [c for c in df.columns if "taluk" in c.lower() or "Taluk" in c]
if not taluk_col:
    # Try first column
    taluk_col = [df.columns[0]]
taluk_col = taluk_col[0]
print(f"Taluk column: '{taluk_col}'")

# Drop rows where Taluk is NaN, "TOTAL", or non-string
df = df[df[taluk_col].notna()]
df = df[~df[taluk_col].astype(str).str.upper().str.contains("TOTAL")]
df = df[~df[taluk_col].astype(str).str.upper().str.contains("TALUK")]  # header repeat rows

# Identify ration category columns
aay_col   = [c for c in df.columns if "AAY" in str(c).upper()][0]
phh_cols  = [c for c in df.columns if "PHH" in str(c).upper() and "NPHH" not in str(c).upper()]
nphh_cols = [c for c in df.columns if "NPHH" in str(c).upper()]
total_col = [c for c in df.columns if str(c).upper() == "TOTAL"]

print(f"AAY col:   {aay_col}")
print(f"PHH cols:  {phh_cols}")
print(f"NPHH cols: {nphh_cols}")
print(f"Total col: {total_col}")

# Convert to numeric
for col in [aay_col] + phh_cols + nphh_cols + total_col:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[aay_col])

# Aggregate PHH and NPHH
df["bpl_poor"]  = df[phh_cols].sum(axis=1)
df["non_poor"]  = df[nphh_cols].sum(axis=1)
df["total_rc"]  = df[aay_col] + df["bpl_poor"] + df["non_poor"]

# ---------------------------------------------------------------
# Map taluks to cities
# Map known Bengaluru-area taluks; use ALL data for state-level
# ---------------------------------------------------------------
TALUK_CITY_MAP = {
    "ANEKAL":          "Bengaluru",
    "BENGALURU NORTH": "Bengaluru",
    "BENGALURU SOUTH": "Bengaluru",
    "BENGALURU EAST":  "Bengaluru",
    "BENGALURU WEST":  "Bengaluru",
    "MYSURU":          "Mysuru",
    "MYSORE":          "Mysuru",
    "MANGALURU":       "Mangaluru",
    "MANGALORE":       "Mangaluru",
    "HUBLI":           "Hubballi-Dharwad",
    "DHARWAD":         "Hubballi-Dharwad",
    "HUBBALLI":        "Hubballi-Dharwad",
    "BELAGAVI":        "Belagavi",
    "BELGAUM":         "Belagavi",
}

def map_city(taluk_name):
    t = str(taluk_name).strip().upper()
    for key, city in TALUK_CITY_MAP.items():
        if key in t:
            return city
    return "Other"

df["city"] = df[taluk_col].apply(map_city)
print(f"\nCity mapping:")
print(df[[taluk_col, "city", aay_col, "bpl_poor", "non_poor", "total_rc"]].to_string(index=False))

# ---------------------------------------------------------------
# Aggregate by city + compute proportions
# ---------------------------------------------------------------
# Also add a Karnataka_All row
city_df  = df.groupby("city")[[aay_col, "bpl_poor", "non_poor", "total_rc"]].sum().reset_index()
city_df.columns = ["city", "aay_rc", "bpl_poor_rc", "non_poor_rc", "total_rc"]

all_row = city_df[city_df["city"] != "Other"][["aay_rc", "bpl_poor_rc", "non_poor_rc", "total_rc"]].sum()
all_row["city"] = "Karnataka_Urban_All"
city_df = pd.concat([city_df, pd.DataFrame([all_row])], ignore_index=True)

# Proportions
city_df["extreme_poor_pct"] = (city_df["aay_rc"] / city_df["total_rc"]).round(4)
city_df["bpl_poor_pct"]     = (city_df["bpl_poor_rc"] / city_df["total_rc"]).round(4)
city_df["non_poor_pct"]     = (city_df["non_poor_rc"] / city_df["total_rc"]).round(4)

# Sanity check: fractions should sum to ~1
city_df["check_sum"] = (city_df["extreme_poor_pct"] + city_df["bpl_poor_pct"] + city_df["non_poor_pct"]).round(4)

print("\n--- Agent Class Proportions ---")
print(city_df.to_string(index=False))

out_path = PROCESSED / "agent_class_proportions.csv"
city_df.to_csv(out_path, index=False)
print(f"\nSaved: {out_path}")
print("\nStep 3 complete.")
