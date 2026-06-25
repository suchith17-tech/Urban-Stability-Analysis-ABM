"""
Step 6 (FIXED v3): Food Ration Supply — Core-Taluk Mapping + PDS-Norm Wheat/Dal
---------------------------------------------------------------------------------
ROOT CAUSE FIXES:
  1. Only Rice has real quantity in col[9] (Quintals). Wheat/Dal = 0 everywhere.
  2. Previous script mapped entire district (14 taluks for Belagavi) to city,
     inflating per-HH food by 10x. FIX: map only the CORE CITY taluk(s).
  3. Wheat/Dal quantities synthesized from PDS norms:
     AAY: 35 kg/RC/month (Rice 20 + Wheat 10 + Dal 5)  — Karnataka Anna Bhagya
     BPL: 25 kg/RC/month (Rice 15 + Wheat 7 + Dal 3)
     APL: 10 kg/RC/month (Rice 7 + Wheat 2 + Dal 1)
"""
import pathlib
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

DATASETS  = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

# -----------------------------------------------------------------------
# Core-city taluk names (ONLY the urban taluk, not the whole district)
# -----------------------------------------------------------------------
CORE_TALUK_CITY = {
    "ANEKAL":               "Bengaluru",
    "BENGALURU NORTH":      "Bengaluru",
    "BENGALURU SOUTH":      "Bengaluru",
    "BENGALURU EAST":       "Bengaluru",
    "BENGALURU WEST":       "Bengaluru",
    "YELAHANKA":            "Bengaluru",
    "DASARAHALLI":          "Bengaluru",
    "RAJARAJESHWARI NAGAR": "Bengaluru",
    "BOMMANAHALLI":         "Bengaluru",
    "MAHADEVAPURA":         "Bengaluru",
    "MYSURU":               "Mysuru",
    "MANGALURU":            "Mangaluru",
    "HUBBALLI":             "Hubballi-Dharwad",
    "HUBLI":                "Hubballi-Dharwad",
    "DHARWAD":              "Hubballi-Dharwad",
    "BELAGAVI":             "Belagavi",
}

def map_city(taluk_name):
    t = str(taluk_name).strip().upper()
    return CORE_TALUK_CITY.get(t, "Other")

# -----------------------------------------------------------------------
# Parse Rice file (only commodity with real quantity data)
# col[0]=Taluk, col[9]=Quantity Involved (Quintals), 1 Qtl = 100 KG
# -----------------------------------------------------------------------
def parse_rice():
    fpath = DATASETS / "feb -apr 2025 (Rice).xlsx"
    xl  = pd.ExcelFile(fpath)
    raw = pd.read_excel(fpath, sheet_name=xl.sheet_names[0], header=None)
    raw.columns = range(len(raw.columns))

    # Find first data row
    data_start = 0
    for i in range(len(raw)):
        val = str(raw.iloc[i, 0]).strip().upper()
        if val not in ["NAN","","TALUK NAME","FEBRUARY :","MARCH :","APRIL :"] \
                and len(val) > 2 and any(c.isalpha() for c in val) \
                and "TOTAL" not in val:
            data_start = i
            break

    data = raw.iloc[data_start:].copy().reset_index(drop=True)
    df = data[[0, 9]].copy()
    df.columns = ["taluk", "qty_qtls"]
    df["taluk"]    = df["taluk"].astype(str).str.strip()
    df["qty_qtls"] = pd.to_numeric(df["qty_qtls"], errors="coerce")
    df = df[~df["taluk"].str.upper().str.contains("TOTAL|GRAND|NAN", na=False)]
    df = df.dropna(subset=["qty_qtls"])
    df = df[df["qty_qtls"] > 0]

    df["rice_kg"] = df["qty_qtls"] * 100  # Quintals → KG
    df["city"]    = df["taluk"].apply(map_city)
    df = df[df["city"] != "Other"]

    city_rice = df.groupby("city")["rice_kg"].sum().reset_index()
    print("Rice from core taluks (KG):")
    for _, r in city_rice.iterrows():
        print(f"  {r['city']:20s}: {r['rice_kg']:>12,.0f} KG = {r['rice_kg']/1000:>8,.1f} T")
    return city_rice

rice_df = parse_rice()

# -----------------------------------------------------------------------
# Synthesize Wheat & Dal from PDS entitlement norms
# Karnataka Anna Bhagya: per-RC entitlements (kg/RC/month):
#   AAY  : Rice 20, Wheat 10, Dal 5
#   BPL  : Rice 15, Wheat 7,  Dal 3
#   APL  : Rice 7,  Wheat 2,  Dal 1
# Total city wheat/dal = sum over all RC categories × entitlement × RC count
# -----------------------------------------------------------------------
PDS_ENTITLEMENTS = {
    "extreme_poor": {"wheat_kg_per_rc": 10, "dal_kg_per_rc": 5},
    "bpl_poor":     {"wheat_kg_per_rc": 7,  "dal_kg_per_rc": 3},
    "non_poor":     {"wheat_kg_per_rc": 2,  "dal_kg_per_rc": 1},
}

ration_df = pd.read_csv(PROCESSED / "agent_class_proportions.csv")
ration_df = ration_df[~ration_df["city"].isin(["Other", "Karnataka_Urban_All"])]

def compute_wheat_dal(city):
    if city not in ration_df["city"].values:
        return 0, 0
    row = ration_df[ration_df["city"] == city].iloc[0]
    total_rc = row["total_rc"]
    wheat_total = 0
    dal_total   = 0
    for grp, ent in PDS_ENTITLEMENTS.items():
        frac_col = f"{grp}_pct"
        if frac_col in row.index:
            n_rc = total_rc * row[frac_col]
            wheat_total += n_rc * ent["wheat_kg_per_rc"]
            dal_total   += n_rc * ent["dal_kg_per_rc"]
    return round(wheat_total, 0), round(dal_total, 0)

print("\nSynthetic Wheat/Dal from PDS norms:")
wheat_dal = []
for city in rice_df["city"].unique():
    w, d = compute_wheat_dal(city)
    wheat_dal.append({"city": city, "wheat_kg": w, "dal_kg": d})
    print(f"  {city:20s}: Wheat={w:>10,.0f} KG, Dal={d:>10,.0f} KG")

wd_df = pd.DataFrame(wheat_dal)

# Merge rice + wheat + dal
base = rice_df.merge(wd_df, on="city")
base["total_base_kg"] = base["rice_kg"] + base["wheat_kg"] + base["dal_kg"]

# -----------------------------------------------------------------------
# Load demographics + ration card counts for per-HH calculation
# IMPORTANT: PDS food is only for ration-card-holding HH
# So food_per_hh_kg = total_food / total_rc (ration cards)
# We also provide pds_coverage_ratio = min(total_rc / households, 1.0)
#   so the ABM knows what fraction of HH actually gets PDS food
# -----------------------------------------------------------------------
demo   = pd.read_csv(PROCESSED / "city_demographics.csv")
pop_lkp = demo.set_index("city")["population"].to_dict()
hh_lkp  = demo.set_index("city")["households"].to_dict()

# Get total ration cards per city for correct denominator
rc_lkp = ration_df.set_index("city")["total_rc"].to_dict()

# -----------------------------------------------------------------------
# Seasonal multipliers + ±10% noise
# -----------------------------------------------------------------------
FOOD_MULT = {
    1:(1.00,"Jan","Winter"),  2:(1.00,"Feb","Winter"),  3:(1.00,"Mar","Winter"),
    4:(0.90,"Apr","Summer"),  5:(0.90,"May","Summer"),  6:(0.90,"Jun","Summer"),
    7:(0.85,"Jul","Monsoon"), 8:(0.85,"Aug","Monsoon"), 9:(0.85,"Sep","Monsoon"),
    10:(1.05,"Oct","Post-Monsoon"),11:(1.05,"Nov","Post-Monsoon"),12:(1.05,"Dec","Post-Monsoon"),
}
NOISE = 0.10

rat_lkp = ration_df.set_index("city")
ANNA_NORM = 5  # kg rice per BPL person per month

records = []
for _, cr in base.iterrows():
    city = cr["city"]
    pop  = pop_lkp.get(city, 0)
    hh   = hh_lkp.get(city, 1)
    total_rc = rc_lkp.get(city, hh)  # fallback to HH if no RC data
    pds_coverage = min(total_rc / hh, 1.0) if hh > 0 else 1.0
    bpl_frac = (float(rat_lkp.loc[city,"extreme_poor_pct"]) +
                float(rat_lkp.loc[city,"bpl_poor_pct"])) if city in rat_lkp.index else 0.45
    anna_floor = round(pop * bpl_frac * ANNA_NORM, 0)

    for month, (smult, mname, season) in FOOD_MULT.items():
        nr = rng.uniform(-NOISE, NOISE)
        nw = rng.uniform(-NOISE, NOISE)
        nd = rng.uniform(-NOISE, NOISE)

        rice_kg  = max(0, round(cr["rice_kg"]  * smult * (1 + nr)))
        wheat_kg = max(0, round(cr["wheat_kg"] * smult * (1 + nw)))
        dal_kg   = max(0, round(cr["dal_kg"]   * smult * (1 + nd)))
        total_kg = rice_kg + wheat_kg + dal_kg

        # Use min(total_rc, hh) as denominator: PDS food is for RC holders
        # For Bengaluru: total_rc=716K < hh=2.1M → use total_rc → ~30 kg/RC
        # For Belagavi:  total_rc=296K > hh=111K → use hh → cap at HH count
        denom = min(total_rc, hh) if total_rc > 0 else hh
        food_per_hh_kg = round(total_kg / denom, 2) if denom > 0 else 0.0

        records.append({
            "city": city, "population": int(pop), "households": int(hh),
            "bpl_fraction": round(bpl_frac, 4),
            "month": month, "month_name": mname, "season": season,
            "seasonal_multiplier": smult,
            "noise_rice": round(nr,4), "noise_wheat": round(nw,4), "noise_dal": round(nd,4),
            "rice_kg": int(rice_kg), "wheat_kg": int(wheat_kg), "dal_kg": int(dal_kg),
            "total_food_kg": int(total_kg),
            "food_per_hh_kg": food_per_hh_kg,
            "pds_coverage_ratio": round(pds_coverage, 4),
            "anna_bhagya_floor_kg": int(anna_floor),
            "policy_gap_flag": bool(rice_kg < anna_floor),
            "drought_shock_multiplier": 1.0,
            "flood_shock_multiplier": 1.0,
        })

out_df = pd.DataFrame(records)
out_path = PROCESSED / "food_ration_supply.csv"
out_df.to_csv(out_path, index=False)
print(f"\nSaved: {out_path}")

# -----------------------------------------------------------------------
# SANITY CHECK
# -----------------------------------------------------------------------
print("\n--- food_per_hh_kg: SANITY CHECK (expected 40-80 kg/HH/month) ---")
jan = out_df[out_df["month_name"]=="Jan"].set_index("city")
print(jan[["food_per_hh_kg","rice_kg","wheat_kg","dal_kg"]].to_string())

print("\n--- Monthly food_per_hh_kg across seasons ---")
pivot = out_df.pivot_table(index="city", columns="season",
                           values="food_per_hh_kg", aggfunc="mean").round(2)
print(pivot.to_string())

print("\nStep 6 complete (FIXED v3).")
