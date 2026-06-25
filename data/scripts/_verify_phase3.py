import pandas as pd
import json

# Check demand calibration
d = pd.read_csv('data/processed/demand_calibration.csv')
print("=== Demand Calibration ===")
print(d[['city','income_group','food_demand_kg_hh','electricity_demand_kwh_hh','water_demand_lpd_hh']].to_string(index=False))

print()
print("=== Resource Interactions ===")
with open('data/processed/resource_interaction_matrix.json') as f:
    ri = json.load(f)
for k, v in ri.items():
    if k != 'metadata' and isinstance(v, dict) and 'coefficient' in v:
        print(f"  {k}: coeff={v['coefficient']}, raw_r={v['raw_correlation']}")

print()
print("=== Model Config Cities ===")
with open('data/processed/model_config_by_city.json') as f:
    mc = json.load(f)
for city in mc:
    cfg = mc[city]
    print(f"  {city}: pop={cfg['population']:,}, groups={list(cfg['agent_groups'].keys())}")
    for g, dem in cfg['demand_by_group'].items():
        print(f"    {g:14s}: food={dem['food_demand_kg_hh']:.1f}kg, elec={dem['electricity_demand_kwh_hh']:.1f}kWh, water={dem['water_demand_lpd_hh']:.1f}L/day")
