import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from data.scripts.config_loader import load_city_config
from model.urban_model import UrbanStabilityModel

# Pick ONE city (start simple)
city_name = "Bengaluru"

# Load config via the dedicated loader (transforms raw JSON dicts into the expected lists)
config = load_city_config(city_name)

# Disable shocks and policies (baseline)
# 'enabled' is nested in the shock config
config["shock"]["enabled"] = False
config["anna_bhagya"]["enabled"] = False
config["gruha_jyothi"]["enabled"] = False
config["gruha_lakshmi"]["enabled"] = False

# Create model
model = UrbanStabilityModel(config)

# Run for 12 months~
for step in range(12):
    model.step()

# Get results
df = model.datacollector.get_model_vars_dataframe()

print(df.tail())

# Save
df.to_csv(f"{city_name}_baseline.csv", index=False)