import json
with open('data/processed/model_config_by_city.json') as f:
    mc = json.load(f)
ben = mc['Bengaluru']

print('=== POLICY ===')
for k, v in ben['policy'].items():
    if isinstance(v, dict):
        src = v.get('source', 'N/A')
        print(f"  {k}: source={src[:80]}")
    else:
        print(f"  {k}: {v}")

print()
print('=== SHOCK ===')
for k, v in ben['shock'].items():
    src = v.get('source', 'NONE')
    vals = {k2:v2 for k2,v2 in v.items() if k2 != 'source'}
    print(f"  {k}: {vals}")
    print(f"    source: {src[:90]}")

print()
has_ph = json.dumps(mc).count('PLACEHOLDER')
print(f"PLACEHOLDER count in full config: {has_ph}")
if has_ph == 0:
    print("ALL CHECKS PASSED")
