"""
Step 0: Housekeeping
- Renames UUID-named CSV files to descriptive names
- Verifies folder structure
"""
import os
import pathlib

DATASETS = pathlib.Path(__file__).parent.parent.parent / "DATASETS"
PROCESSED = pathlib.Path(__file__).parent.parent / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

renames = {
    "70d066f8-2145-4b98-9e94-d7657b8a04a0.csv": "karnataka_electricity_timeseries.csv",
    "880d7e38-82e9-41f7-98b9-f92dea3ef0f0.csv": "bangalore_sewage_infrastructure.csv",
}

for old_name, new_name in renames.items():
    old_path = DATASETS / old_name
    new_path = DATASETS / new_name
    if old_path.exists():
        old_path.rename(new_path)
        print(f"  Renamed: {old_name} -> {new_name}")
    elif new_path.exists():
        print(f"  Already renamed: {new_name}")
    else:
        print(f"  NOT FOUND: {old_name}")

print("\nFolder structure:")
print(f"  DATASETS : {DATASETS} — exists: {DATASETS.exists()}")
print(f"  PROCESSED: {PROCESSED} — exists: {PROCESSED.exists()}")
print("\nStep 0 complete.")
