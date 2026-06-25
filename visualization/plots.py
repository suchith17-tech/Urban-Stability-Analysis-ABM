"""
Static Scenario Plots — Phase 4 Pre-Dashboard Visualization
Runs all 7 scenarios and generates 4 comparison plots saved to results/plots/.

Scenarios:
    1. Baseline                 (no policy, no shock)
    2. Shock Only               (resource scarcity at t=25)
    3. Policy Only              (subsidy + pricing, no shock)
    4. Shock + Policy           (subsidy + pricing + resource shock at t=25)
    5. Trust Breakdown Shock    (social shock at t=25, no policy)
    6. Shock + Subsidy Only     (subsidy only + resource shock at t=25)
    7. Shock + Pricing Only     (pricing only + resource shock at t=25)

Plots generated:
    1. USI vs Time              (all scenarios overlaid)
    2. Gini Evolution           (all scenarios)
    3. Cooperation Trend        (trust dynamics)
    4. Recovery Analysis        (bar chart: time-to-recovery after shock)

Run with: python visualization/plots.py
"""
import os
import sys
import copy
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import CONFIG
from model.urban_model import UrbanStabilityModel

# ─── Output directory ────────────────────────────────────────────────────────
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# ─── Scenario Definitions ────────────────────────────────────────────────────
SCENARIOS = {
    "1. Baseline": {
        "color": "#4CAF50", "linestyle": "-",
        "policy": {},
        "shock": {"enabled": False},
    },
    "2. Shock Only": {
        "color": "#F44336", "linestyle": "--",
        "policy": {},
        "shock": {"enabled": True, "type": "resource_scarcity", "step": 25, "magnitude": 0.3, "persistent": False},
    },
    "3. Policy Only": {
        "color": "#2196F3", "linestyle": "-.",
        "policy": {
            "pricing_multiplier": {"enabled": True, "value": 1.5},
            "subsidy":            {"enabled": True, "rate": 0.3, "threshold_percentile": 30},
        },
        "shock": {"enabled": False},
    },
    "4. Shock + All Policies": {
        "color": "#FF9800", "linestyle": ":",
        "policy": {
            "pricing_multiplier": {"enabled": True, "value": 1.5},
            "subsidy":            {"enabled": True, "rate": 0.3, "threshold_percentile": 30},
        },
        "shock": {"enabled": True, "type": "resource_scarcity", "step": 25, "magnitude": 0.3, "persistent": False},
    },
    "5. Trust Breakdown Shock": {
        "color": "#9C27B0", "linestyle": (0, (5, 2)),
        "policy": {},
        "shock": {"enabled": True, "type": "trust_breakdown", "step": 25, "magnitude": 0.5, "persistent": False},
    },
    "6. Shock + Subsidy Only": {
        "color": "#00BCD4", "linestyle": (0, (3, 1, 1, 1)),
        "policy": {
            "subsidy": {"enabled": True, "rate": 0.3, "threshold_percentile": 30},
        },
        "shock": {"enabled": True, "type": "resource_scarcity", "step": 25, "magnitude": 0.3, "persistent": False},
    },
    "7. Shock + Pricing Only": {
        "color": "#FF5722", "linestyle": (0, (1, 1)),
        "policy": {
            "pricing_multiplier": {"enabled": True, "value": 1.5},
        },
        "shock": {"enabled": True, "type": "resource_scarcity", "step": 25, "magnitude": 0.3, "persistent": False},
    },
}

# ─── Run All Scenarios ────────────────────────────────────────────────────────
def run_scenario(name, defn):
    cfg = copy.deepcopy(CONFIG)
    for key, val in defn["policy"].items():
        cfg["policy"][key].update(val)
    cfg["shock"].update(defn["shock"])

    model = UrbanStabilityModel(config=cfg)
    for _ in range(cfg["num_steps"]):
        if not model.running:
            break
        model.step()

    data = model.datacollector.get_model_vars_dataframe()
    return data


print("Running 7 scenarios...")
results = {}
for name, defn in SCENARIOS.items():
    print(f"  {name}...", end=" ", flush=True)
    results[name] = run_scenario(name, defn)
    print("done")

steps = range(1, CONFIG["num_steps"] + 1)
COLLAPSE_THRESHOLD = 0.3

# ─── Plot 1: USI vs Time ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
for name, data in results.items():
    defn = SCENARIOS[name]
    usi = data["USI"].values
    ax.plot(range(1, len(usi) + 1), usi,
            label=name, color=defn["color"],
            linestyle=defn["linestyle"], linewidth=2.0)

ax.axhline(COLLAPSE_THRESHOLD, color="black", linestyle="--",
           linewidth=1.2, alpha=0.6, label=f"Collapse Threshold ({COLLAPSE_THRESHOLD})")
ax.axvline(25, color="gray", linestyle=":", linewidth=1.0, alpha=0.5, label="Shock at t=25")
ax.set_title("Urban Stability Index (USI) Over Time — All 7 Scenarios", fontsize=14, fontweight="bold")
ax.set_xlabel("Time Step", fontsize=12)
ax.set_ylabel("USI", fontsize=12)
ax.set_ylim(0, 1)
ax.legend(loc="lower right", fontsize=8)
ax.grid(True, alpha=0.3)
plt.tight_layout()
path = os.path.join(PLOTS_DIR, "usi_vs_time.png")
plt.savefig(path, dpi=150)
plt.close()
print(f"  Saved: {path}")

# ─── Plot 2: Gini Evolution ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
for name, data in results.items():
    defn = SCENARIOS[name]
    gini = data["Gini"].values
    ax.plot(range(1, len(gini) + 1), gini,
            label=name, color=defn["color"],
            linestyle=defn["linestyle"], linewidth=2.0)

ax.axvline(25, color="gray", linestyle=":", linewidth=1.0, alpha=0.5, label="Shock at t=25")
ax.set_title("Gini Coefficient (Allocation Inequality) Over Time", fontsize=14, fontweight="bold")
ax.set_xlabel("Time Step", fontsize=12)
ax.set_ylabel("Gini Coefficient", fontsize=12)
ax.set_ylim(0, 1)
ax.legend(loc="upper right", fontsize=8)
ax.grid(True, alpha=0.3)
plt.tight_layout()
path = os.path.join(PLOTS_DIR, "gini_evolution.png")
plt.savefig(path, dpi=150)
plt.close()
print(f"  Saved: {path}")

# ─── Plot 3: Cooperation (Trust) Trend ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
for name, data in results.items():
    defn = SCENARIOS[name]
    trust = data["Average_Trust"].values
    ax.plot(range(1, len(trust) + 1), trust,
            label=name, color=defn["color"],
            linestyle=defn["linestyle"], linewidth=2.0)

ax.axvline(25, color="gray", linestyle=":", linewidth=1.0, alpha=0.5, label="Shock at t=25")
ax.set_title("Cooperation Trend (Average Agent Trust) Over Time", fontsize=14, fontweight="bold")
ax.set_xlabel("Time Step", fontsize=12)
ax.set_ylabel("Average Trust", fontsize=12)
ax.set_ylim(0, 1)
ax.legend(loc="lower right", fontsize=8)
ax.grid(True, alpha=0.3)
plt.tight_layout()
path = os.path.join(PLOTS_DIR, "cooperation_trend.png")
plt.savefig(path, dpi=150)
plt.close()
print(f"  Saved: {path}")

# ─── Plot 4: Recovery Analysis (bar chart) ───────────────────────────────────
# For shock scenarios: how many steps post-shock until USI recovers to >= pre-shock avg
shock_scenarios = [
    "2. Shock Only",
    "4. Shock + All Policies",
    "5. Trust Breakdown Shock",
    "6. Shock + Subsidy Only",
    "7. Shock + Pricing Only",
]

SHOCK_STEP = 25

recovery_times = {}
for name in shock_scenarios:
    data = results[name]
    usi = data["USI"].values
    pre_shock_avg = float(np.mean(usi[:SHOCK_STEP]))
    recovery_step = None
    for i in range(SHOCK_STEP, len(usi)):
        if usi[i] >= pre_shock_avg * 0.95:
            recovery_step = i - SHOCK_STEP
            break
    recovery_times[name] = recovery_step if recovery_step is not None else CONFIG["num_steps"] - SHOCK_STEP

fig, ax = plt.subplots(figsize=(10, 5))
names  = list(recovery_times.keys())
values = list(recovery_times.values())
colors = [SCENARIOS[n]["color"] for n in names]
short_names = [n.split(". ", 1)[1] for n in names]

bars = ax.bar(short_names, values, color=colors, edgecolor="white", linewidth=1.2)
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{val} steps", ha="center", va="bottom", fontsize=9, fontweight="bold")

ax.set_title("Recovery Analysis — Steps to Recover Pre-Shock USI Level", fontsize=13, fontweight="bold")
ax.set_xlabel("Scenario", fontsize=11)
ax.set_ylabel("Steps to Recovery", fontsize=11)
ax.set_ylim(0, max(values) * 1.2 + 2)
plt.xticks(rotation=15, ha="right", fontsize=9)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
path = os.path.join(PLOTS_DIR, "recovery_analysis.png")
plt.savefig(path, dpi=150)
plt.close()
print(f"  Saved: {path}")

print()
print("All 4 plots saved to results/plots/")
print("  - usi_vs_time.png")
print("  - gini_evolution.png")
print("  - cooperation_trend.png")
print("  - recovery_analysis.png")
