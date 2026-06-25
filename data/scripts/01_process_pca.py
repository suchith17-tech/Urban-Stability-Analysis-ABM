"""
Step 1: Process PCA City Census Data (Census of India 2011)
Input : 5 PCA CSV files in DATASETS/
Output: data/processed/city_demographics.csv
"""
import pathlib
import pandas as pd
import re
import csv

DATASETS  = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"

PCA_FILES = {
    "Bengaluru":        "PCA_29_572_99999_803162(Banglore) (1).csv",
    "Belagavi":         "PCA_29_555_5438_803033(Belagavi) (1).csv",
    "Hubballi-Dharwad": "PCA_29_562_99999_803083(Hubballi-Dharvad) (1).csv",
    "Mangaluru":        "PCA_29_575_5561_803181(Manglaore) (1).csv",
    "Mysuru":           "PCA_29_577_5572_803194(Mysore) (1).csv",
}

# Map S.No (1-indexed row number) directly to column name
# PCA rows are consistently ordered: 1=Population, 2=Child Pop, 3=SC, 4=ST, 5=Literate, 6=Illiterate, 7=Workers, 8=NonWorkers
SNO_MAP = {
    1: "population",
    2: "child_population",
    3: "sc_pop",
    4: "st_pop",
    5: "literate",
    6: "illiterate",
    7: "workers",
    8: "non_workers",
}

def parse_households(line):
    clean = line.replace('"', "")
    match = re.search(r"[\d,]+", clean)
    if match:
        return int(match.group().replace(",", ""))
    return None

records = []

for city, fname in PCA_FILES.items():
    fpath = DATASETS / fname
    if not fpath.exists():
        print(f"  MISSING: {fname}")
        continue

    with open(fpath, encoding="utf-8") as f:
        raw_lines = f.readlines()

    households = parse_households(raw_lines[3])

    with open(fpath, encoding="utf-8") as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    row_data = {"city": city, "households": households}

    # Data rows start at index 5 (0-based). Row format: [S.No, Indicator, Persons, Males, Females]
    for row in all_rows[5:]:
        if len(row) < 3:
            continue
        try:
            sno = int(row[0].strip())
        except ValueError:
            continue
        col = SNO_MAP.get(sno)
        if col is None:
            continue
        persons_raw = row[2].strip().replace(",", "")
        try:
            row_data[col] = int(persons_raw)
        except ValueError:
            pass

    records.append(row_data)
    print(f"  Parsed {city}: population={row_data.get('population', 0):,}, "
          f"households={households:,}, workers={row_data.get('workers', 0):,}")

df = pd.DataFrame(records)

# Fill missing non_workers
if "non_workers" not in df.columns:
    df["non_workers"] = df["population"] - df["workers"]
else:
    df["non_workers"] = df["non_workers"].fillna(df["population"] - df["workers"])

# Derived metrics
df["worker_ratio"]       = (df["workers"] / df["population"]).round(4)
df["literacy_rate"]      = (df["literate"] / df["population"]).round(4)
df["sc_fraction"]        = (df["sc_pop"] / df["population"]).round(4)
df["st_fraction"]        = (df["st_pop"] / df["population"]).round(4)
df["avg_household_size"] = (df["population"] / df["households"]).round(2)

out_path = PROCESSED / "city_demographics.csv"
df.to_csv(out_path, index=False)
print(f"\nSaved: {out_path}")
print(df[["city", "population", "households", "workers", "literacy_rate", "avg_household_size"]].to_string(index=False))
print("\nStep 1 complete.")
