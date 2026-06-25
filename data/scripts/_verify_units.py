import pandas as pd

w = pd.read_csv('data/processed/water_supply_monthly.csv')
e = pd.read_csv('data/processed/electricity_supply_monthly.csv')
f = pd.read_csv('data/processed/food_ration_supply.csv')

jan_w = w[w['month_name']=='Jan'].set_index('city')['water_per_hh_lpd']
jan_e = e[e['month_name']=='Jan'].set_index('city')['electricity_per_hh_kwh']
jan_f = f[f['month_name']=='Jan'].set_index('city')['food_per_hh_kg']

print("=== FINAL SANITY CHECK ===")
print("Expected: Water 400-700 | Food 20-120 | Elec 100-700")
print()
for city in ['Bengaluru','Mysuru','Mangaluru','Hubballi-Dharwad','Belagavi']:
    wv = jan_w.get(city, 0)
    ev = jan_e.get(city, 0)
    fv = jan_f.get(city, 0)
    print(f"  {city:20s}: Water={wv:>7.1f} L/HH/day | Food={fv:>7.2f} kg/HH/mo | Elec={ev:>7.1f} kWh/HH/mo")
