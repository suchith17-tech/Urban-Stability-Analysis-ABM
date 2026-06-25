from model.urban_model import UrbanStabilityModel
from config import CONFIG
import matplotlib.pyplot as plt
import copy


def run_simulation(config):

    model = UrbanStabilityModel(config=config)

    while model.running and model.current_step < model.config["num_steps"]:
        model.step()

    data = model.datacollector.get_model_vars_dataframe()

    return data["USI"]


# -------------------------
# BASELINE
# -------------------------

baseline_config = copy.deepcopy(CONFIG)

baseline_config["policy"]["pricing_multiplier"]["enabled"] = False
baseline_config["policy"]["subsidy"]["enabled"] = False
baseline_config["policy"]["consumption_cap"]["enabled"] = False

usi_baseline = run_simulation(baseline_config)


# -------------------------
# SUBSIDY POLICY
# -------------------------

subsidy_config = copy.deepcopy(CONFIG)

subsidy_config["policy"]["pricing_multiplier"]["enabled"] = False
subsidy_config["policy"]["subsidy"]["enabled"] = True
subsidy_config["policy"]["consumption_cap"]["enabled"] = False

usi_subsidy = run_simulation(subsidy_config)


# -------------------------
# CONSUMPTION CAP POLICY
# -------------------------

cap_config = copy.deepcopy(CONFIG)

cap_config["policy"]["pricing_multiplier"]["enabled"] = False
cap_config["policy"]["subsidy"]["enabled"] = False
cap_config["policy"]["consumption_cap"]["enabled"] = True

usi_cap = run_simulation(cap_config)


# -------------------------
# COMPARISON GRAPH
# -------------------------

plt.figure()

plt.plot(usi_baseline, label="Baseline")
plt.plot(usi_subsidy, label="Subsidy Policy")
plt.plot(usi_cap, label="Consumption Cap")

plt.title("Policy Comparison: Urban Stability Index")
plt.xlabel("Time Step")
plt.ylabel("USI")

plt.legend()

plt.show()