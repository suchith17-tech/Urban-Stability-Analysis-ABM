"""
12_analyze_results.py — Phase 7: Analysis & Visualization
==========================================================
Reads the experiment CSVs produced by 11_run_experiments.py and generates:

  1. USI vs Time — multi-city, per scenario
  2. Trust vs Time — collapse & recovery
  3. Policy Delta — EXP5a vs EXP5b bar chart (quantifying policy value)
  4. Cross-scenario heatmap — final USI for every city × scenario
  5. Min-USI bar chart — worst-case vulnerability ranking
  6. Bengaluru deep-dive
  7. Gini vs Time — dynamic consumption inequality across all scenarios

Outputs saved to results/figures/
"""
import sys
import pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))

# ─────────────────────────────────────────────────────────────────────────────
EXPERIMENTS_DIR = pathlib.Path("results/experiments")
FIGURES_DIR     = pathlib.Path("results/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

CITIES = ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi-Dharwad", "Belagavi"]
CITY_COLORS = {
    "Bengaluru":        "#E74C3C",   # red
    "Mysuru":           "#3498DB",   # blue
    "Mangaluru":        "#2ECC71",   # green
    "Hubballi-Dharwad": "#F39C12",   # orange
    "Belagavi":         "#9B59B6",   # purple
}

SCENARIO_LABELS = {
    "exp1_baseline":        "Baseline\n(No Shocks)",
    "exp2_flood":           "Flood\nShock",
    "exp3_drought":         "Drought\nShock",
    "exp4_economic":        "Economic\nShock",
    "exp5a_shock_nopolicy": "All Shocks\nNo Policy",
    "exp5b_shock_policy":   "All Shocks\nWith Policy",
    "exp6_combined":        "Combined\nStress Test",
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def load_all_cities(scenario_id: str) -> pd.DataFrame:
    """Load and concatenate all city CSVs for a given scenario."""
    path = EXPERIMENTS_DIR / scenario_id / "_all_cities.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

def style_ax(ax, title, xlabel="Month", ylabel=None):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(fontsize=9, loc="best")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 1: USI vs Time — one subplot per scenario (6 panels)
# ─────────────────────────────────────────────────────────────────────────────

def plot_usi_timeseries():
    scenarios = [
        "exp1_baseline", "exp2_flood", "exp3_drought",
        "exp4_economic", "exp5a_shock_nopolicy", "exp5b_shock_policy"
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Urban Stability Index (USI) Over 24 Months — All Scenarios",
                 fontsize=16, fontweight="bold", y=1.01)

    for ax, sid in zip(axes.flatten(), scenarios):
        df = load_all_cities(sid)
        if df.empty:
            ax.set_visible(False)
            continue
        for city in CITIES:
            cdf = df[df["city"] == city].sort_values("step")
            if cdf.empty:
                continue
            ax.plot(cdf["step"], cdf["USI"],
                    color=CITY_COLORS[city], label=city, linewidth=2)
        ax.axhline(0.5, color="red", linestyle=":", linewidth=1, alpha=0.7, label="Collapse threshold")
        ax.set_ylim(0.3, 1.05)
        ax.xaxis.set_major_locator(mticker.MultipleLocator(4))
        style_ax(ax, SCENARIO_LABELS[sid].replace("\n", " "), ylabel="USI")

    plt.tight_layout()
    out = FIGURES_DIR / "01_USI_timeseries.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 2: Trust Collapse & Recovery — baseline vs combined
# ─────────────────────────────────────────────────────────────────────────────

def plot_trust_recovery():
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("Trust Dynamics: Baseline vs Combined Shock Scenario",
                 fontsize=15, fontweight="bold")

    for ax, sid, label in [
        (axes[0], "exp1_baseline",  "Baseline (No Shocks)"),
        (axes[1], "exp6_combined",  "Combined Stress (All Shocks + Policies)"),
    ]:
        df = load_all_cities(sid)
        for city in CITIES:
            cdf = df[df["city"] == city].sort_values("step")
            ax.plot(cdf["step"], cdf["Trust"],
                    color=CITY_COLORS[city], label=city, linewidth=2)
        ax.axhline(0.5, color="orange", linestyle="--", alpha=0.7, label="Trust warning (0.5)")
        ax.axhline(0.3, color="red",    linestyle=":",  alpha=0.7, label="Protest risk  (0.3)")
        ax.set_ylim(-0.05, 1.05)
        ax.xaxis.set_major_locator(mticker.MultipleLocator(4))
        style_ax(ax, label, ylabel="Average Trust")

    plt.tight_layout()
    out = FIGURES_DIR / "02_Trust_dynamics.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 3: Policy Effectiveness — USI delta (5b - 5a) per city
# ─────────────────────────────────────────────────────────────────────────────

def plot_policy_delta():
    df_no  = load_all_cities("exp5a_shock_nopolicy")
    df_yes = load_all_cities("exp5b_shock_policy")

    results = []
    for city in CITIES:
        no  = df_no [df_no ["city"] == city].sort_values("step")
        yes = df_yes[df_yes["city"] == city].sort_values("step")
        if no.empty or yes.empty:
            continue
        results.append({
            "city":          city,
            "final_USI_no":  no["USI"].iloc[-1],
            "final_USI_yes": yes["USI"].iloc[-1],
            "delta_USI":     yes["USI"].iloc[-1] - no["USI"].iloc[-1],
            "min_USI_no":    no["USI"].min(),
            "min_USI_yes":   yes["USI"].min(),
        })

    rdf = pd.DataFrame(results)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Policy Effectiveness: Impact of Govt. Schemes Under Combined Shocks",
                 fontsize=14, fontweight="bold")

    x = np.arange(len(rdf))
    width = 0.35

    # Final USI comparison
    ax1.bar(x - width/2, rdf["final_USI_no"],  width, label="No Policy", color="#E74C3C", alpha=0.85)
    ax1.bar(x + width/2, rdf["final_USI_yes"], width, label="With Policy", color="#2ECC71", alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(rdf["city"], rotation=15, ha="right", fontsize=9)
    ax1.set_ylim(0, 1.1)
    ax1.set_ylabel("Final USI (Month 24)")
    ax1.axhline(0.5, color="red", linestyle=":", alpha=0.6)
    ax1.set_title("Final Stability (Month 24)")
    ax1.legend()
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Delta bar
    colors = ["#2ECC71" if d >= 0 else "#E74C3C" for d in rdf["delta_USI"]]
    ax2.bar(rdf["city"], rdf["delta_USI"], color=colors, alpha=0.85)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_xticks(range(len(rdf["city"])))
    ax2.set_xticklabels(rdf["city"], rotation=15, ha="right", fontsize=9)
    ax2.set_ylabel("USI Improvement (Policy ON − OFF)")
    ax2.set_title("USI Gain from Govt. Schemes")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    # Add value labels
    for i, (city, val) in enumerate(zip(rdf["city"], rdf["delta_USI"])):
        ax2.text(i, val + 0.005, f"+{val:.3f}" if val >= 0 else f"{val:.3f}",
                 ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.tight_layout()
    out = FIGURES_DIR / "03_Policy_effectiveness.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 4: Heatmap — final USI for all cities × all scenarios
# ─────────────────────────────────────────────────────────────────────────────

def plot_heatmap():
    summary = pd.read_csv(EXPERIMENTS_DIR / "MASTER_SUMMARY.csv")

    scenarios_ordered = [
        "exp1_baseline", "exp2_flood", "exp3_drought",
        "exp4_economic", "exp5a_shock_nopolicy", "exp5b_shock_policy",
    ]
    label_map = {
        "exp1_baseline":        "Baseline",
        "exp2_flood":           "Flood",
        "exp3_drought":         "Drought",
        "exp4_economic":        "Economic",
        "exp5a_shock_nopolicy": "All Shocks\nNo Policy",
        "exp5b_shock_policy":   "All Shocks\nWith Policy",
    }

    pivot = summary[summary["scenario"].isin(scenarios_ordered)].pivot(
        index="city", columns="scenario", values="final_USI"
    )
    pivot = pivot.reindex(columns=scenarios_ordered)
    pivot = pivot.reindex(CITIES)

    fig, ax = plt.subplots(figsize=(13, 5))
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=0.3, vmax=1.0, aspect="auto")

    ax.set_xticks(range(len(scenarios_ordered)))
    ax.set_xticklabels([label_map[s] for s in scenarios_ordered], fontsize=10)
    ax.set_yticks(range(len(CITIES)))
    ax.set_yticklabels(CITIES, fontsize=10)

    for i in range(len(CITIES)):
        for j in range(len(scenarios_ordered)):
            val = pivot.values[i, j]
            text_color = "white" if val < 0.55 else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=text_color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Final USI", fontsize=10)

    ax.set_title("Urban Stability Index Heatmap — City × Scenario (Month 24)",
                 fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    out = FIGURES_DIR / "04_USI_heatmap.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 5: Min USI (worst-case vulnerability) per city per shock
# ─────────────────────────────────────────────────────────────────────────────

def plot_vulnerability():
    summary = pd.read_csv(EXPERIMENTS_DIR / "MASTER_SUMMARY.csv")
    shock_scenarios = ["exp2_flood", "exp3_drought", "exp4_economic", "exp5a_shock_nopolicy"]
    shock_labels    = ["Flood", "Drought", "Economic", "All Shocks\n(No Policy)"]

    sub = summary[summary["scenario"].isin(shock_scenarios)]

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(CITIES))
    n = len(shock_scenarios)
    width = 0.18
    colors = ["#3498DB", "#E67E22", "#E74C3C", "#8E44AD"]

    for i, (sid, label, color) in enumerate(zip(shock_scenarios, shock_labels, colors)):
        vals = [
            sub[(sub["scenario"] == sid) & (sub["city"] == city)]["min_USI"].values[0]
            if len(sub[(sub["scenario"] == sid) & (sub["city"] == city)]) > 0 else 0
            for city in CITIES
        ]
        offset = (i - n/2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=label, color=color, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(CITIES, fontsize=10, rotation=10)
    ax.set_ylabel("Minimum USI Reached (Worst Month)", fontsize=11)
    ax.set_ylim(0.3, 1.0)
    ax.axhline(0.5, color="red", linestyle=":", alpha=0.7, label="Collapse threshold")
    ax.set_title("Worst-Case Vulnerability: Minimum USI per City per Shock Type",
                 fontsize=13, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=9)

    plt.tight_layout()
    out = FIGURES_DIR / "05_Vulnerability_min_USI.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 6: Bengaluru deep-dive — all shock scenarios overlaid
# ─────────────────────────────────────────────────────────────────────────────

def plot_bengaluru_deepdive():
    scenarios = {
        "exp1_baseline":        ("Baseline",          "#2ECC71",  "-"),
        "exp2_flood":           ("Flood Shock",        "#3498DB",  "--"),
        "exp3_drought":         ("Drought Shock",      "#E67E22",  "-."),
        "exp4_economic":        ("Economic Shock",     "#E74C3C",  ":"),
        "exp5a_shock_nopolicy": ("All Shocks/No Pol.", "#8E44AD",  "-"),
        "exp5b_shock_policy":   ("All Shocks/Policy",  "#27AE60",  "-"),
    }

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    fig.suptitle("Bengaluru Deep-Dive: USI & Trust Recovery Across All Scenarios",
                 fontsize=14, fontweight="bold")

    for sid, (label, color, ls) in scenarios.items():
        df = load_all_cities(sid)
        cdf = df[df["city"] == "Bengaluru"].sort_values("step")
        if cdf.empty:
            continue
        ax1.plot(cdf["step"], cdf["USI"],   color=color, linestyle=ls, label=label, linewidth=2)
        ax2.plot(cdf["step"], cdf["Trust"], color=color, linestyle=ls, label=label, linewidth=2)

    ax1.axhline(0.5, color="red", linestyle=":", alpha=0.6, linewidth=1)
    ax1.set_ylabel("USI", fontsize=11)
    ax1.set_ylim(0.3, 1.05)
    ax1.legend(fontsize=9, loc="lower right")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)

    ax2.axhline(0.5, color="orange", linestyle="--", alpha=0.6)
    ax2.axhline(0.3, color="red",    linestyle=":",  alpha=0.6)
    ax2.set_ylabel("Trust", fontsize=11)
    ax2.set_xlabel("Simulation Step (Month)", fontsize=11)
    ax2.set_ylim(-0.05, 1.05)
    ax2.xaxis.set_major_locator(mticker.MultipleLocator(4))
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    out = FIGURES_DIR / "06_Bengaluru_deepdive.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# PLOT 7: Gini time-series — dynamic inequality across scenarios
# ─────────────────────────────────────────────────────────────────────────────

def plot_gini_timeseries():
    """
    Compare Gini (consumption-based inequality) over 24 months.
    Each subplot = one city, showing how Gini evolves differently per scenario.
    """
    scenarios = {
        "exp1_baseline":        ("Baseline",           "#2ECC71", "-"),
        "exp3_drought":         ("Drought Shock",       "#E67E22", "--"),
        "exp4_economic":        ("Economic Shock",      "#E74C3C", "-."),
        "exp5a_shock_nopolicy": ("All Shocks/No Pol.",  "#8E44AD", ":"),
        "exp5b_shock_policy":   ("All Shocks/Policy",   "#3498DB", "-"),
    }

    # Load all scenario data once
    data = {sid: load_all_cities(sid) for sid in scenarios}

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(
        "Consumption Inequality (Gini) Over 24 Months — Per City\n"
        "Higher Gini = More unequal resource satisfaction between rich & poor agents",
        fontsize=14, fontweight="bold", y=1.02
    )

    city_list = CITIES  # 5 cities — 6th subplot left blank
    for ax, city in zip(axes.flatten(), city_list):
        for sid, (label, color, ls) in scenarios.items():
            df  = data[sid]
            cdf = df[df["city"] == city].sort_values("step")
            if cdf.empty:
                continue
            ax.plot(cdf["step"], cdf["Gini"],
                    color=color, linestyle=ls, label=label, linewidth=2)
        ax.set_title(city, fontsize=12, fontweight="bold")
        ax.set_xlabel("Step (Month)", fontsize=10)
        ax.set_ylabel("Gini", fontsize=10)
        ax.xaxis.set_major_locator(mticker.MultipleLocator(4))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend(fontsize=8)

    # Hide the 6th (empty) subplot
    axes.flatten()[-1].set_visible(False)

    plt.tight_layout()
    out = FIGURES_DIR / "07_Gini_timeseries.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  PHASE 7: GENERATING ANALYSIS FIGURES")
    print("="*60 + "\n")

    print("Plot 1: USI Time-Series (all scenarios, all cities)")
    plot_usi_timeseries()

    print("Plot 2: Trust Dynamics (baseline vs combined)")
    plot_trust_recovery()

    print("Plot 3: Policy Effectiveness Delta")
    plot_policy_delta()

    print("Plot 4: City × Scenario Heatmap")
    plot_heatmap()

    print("Plot 5: Worst-Case Vulnerability (min USI)")
    plot_vulnerability()

    print("Plot 6: Bengaluru Deep-Dive")
    plot_bengaluru_deepdive()

    print("Plot 7: Gini Time-Series (dynamic inequality)")
    plot_gini_timeseries()

    print(f"\nAll figures saved in: {FIGURES_DIR.absolute()}/")
    print("Phase 7 analysis complete.\n")


if __name__ == "__main__":
    main()
