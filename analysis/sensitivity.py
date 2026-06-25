"""
Sensitivity Analysis — Phase 4
Systematic parameter sweeps using the Monte Carlo runner.
Results exported to results/ as CSV files.
"""
import copy
import pandas as pd
from config import CONFIG
from analysis.monte_carlo import run_monte_carlo


def sweep_agent_count(base_config=None, runs_per_point=10):
    """
    4.3: Test how USI changes with different agent counts.
    N in {50, 100, 200, 500}
    """
    cfg = copy.deepcopy(base_config or CONFIG)
    agent_counts = [50, 100, 200, 500]
    rows = []

    print("Sweep: Agent Count")
    for N in agent_counts:
        print(f"  N={N}...", end=" ", flush=True)
        cfg["num_agents"] = N
        summary_df, _ = run_monte_carlo(cfg, num_runs=runs_per_point,
                                        label=f"sweep_N{N}", verbose=False)
        rows.append({
            "num_agents":  N,
            "avg_usi":     summary_df["avg_usi"].mean(),
            "std_usi":     summary_df["avg_usi"].std(),
            "avg_gini":    summary_df["avg_gini"].mean(),
            "avg_trust":   summary_df["avg_trust"].mean(),
            "collapsed":   summary_df["time_to_collapse"].notna().sum(),
        })
        print(f"USI={rows[-1]['avg_usi']:.4f}")

    result = pd.DataFrame(rows)
    result.to_csv("results/sweep_agent_count.csv", index=False)
    print(f"  Saved: results/sweep_agent_count.csv\n")
    return result


def sweep_shock_magnitude(base_config=None, runs_per_point=10):
    """
    4.4: Test recovery patterns under different shock magnitudes.
    magnitude in {0.1, 0.2, 0.3, 0.5, 0.7}
    """
    cfg = copy.deepcopy(base_config or CONFIG)
    cfg["shock"]["enabled"] = True
    cfg["shock"]["type"] = "resource_scarcity"
    cfg["shock"]["step"] = 25
    cfg["shock"]["persistent"] = False

    magnitudes = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]
    rows = []

    print("Sweep: Shock Magnitude")
    for mag in magnitudes:
        cfg["shock"]["magnitude"] = mag
        cfg["shock"]["enabled"] = mag > 0
        label = f"sweep_shock_{int(mag*10)}"
        print(f"  magnitude={mag:.1f}...", end=" ", flush=True)
        summary_df, _ = run_monte_carlo(cfg, num_runs=runs_per_point,
                                        label=label, verbose=False)
        rows.append({
            "magnitude":  mag,
            "avg_usi":    summary_df["avg_usi"].mean(),
            "std_usi":    summary_df["avg_usi"].std(),
            "min_usi":    summary_df["min_usi"].min(),
            "avg_trust":  summary_df["avg_trust"].mean(),
            "collapsed":  summary_df["time_to_collapse"].notna().sum(),
        })
        print(f"USI={rows[-1]['avg_usi']:.4f}")

    result = pd.DataFrame(rows)
    result.to_csv("results/sweep_shock_magnitude.csv", index=False)
    print(f"  Saved: results/sweep_shock_magnitude.csv\n")
    return result


def sweep_policy_effectiveness(base_config=None, runs_per_point=10):
    """
    4.5: Compare USI across policy combinations.
    """
    cfg_base = copy.deepcopy(base_config or CONFIG)

    scenarios = {
        "no_policy":        {},
        "pricing_only":     {"pricing_multiplier": {"enabled": True, "value": 1.5}},
        "subsidy_only":     {"subsidy": {"enabled": True, "rate": 0.3, "threshold_percentile": 30}},
        "cap_only":         {"consumption_cap": {"enabled": True, "cap_value": 50}},
        "all_combined":     {
            "pricing_multiplier": {"enabled": True, "value": 1.5},
            "subsidy":            {"enabled": True, "rate": 0.3, "threshold_percentile": 30},
            "consumption_cap":    {"enabled": True, "cap_value": 50},
        },
    }

    rows = []
    print("Sweep: Policy Effectiveness")
    for name, policy_override in scenarios.items():
        cfg = copy.deepcopy(cfg_base)
        for key, val in policy_override.items():
            cfg["policy"][key].update(val)

        print(f"  {name}...", end=" ", flush=True)
        summary_df, _ = run_monte_carlo(cfg, num_runs=runs_per_point,
                                        label=f"sweep_{name}", verbose=False)
        rows.append({
            "scenario":    name,
            "avg_usi":     summary_df["avg_usi"].mean(),
            "std_usi":     summary_df["avg_usi"].std(),
            "avg_gini":    summary_df["avg_gini"].mean(),
            "avg_trust":   summary_df["avg_trust"].mean(),
            "collapsed":   summary_df["time_to_collapse"].notna().sum(),
        })
        print(f"USI={rows[-1]['avg_usi']:.4f}")

    result = pd.DataFrame(rows)
    result.to_csv("results/sweep_policy_effectiveness.csv", index=False)
    print(f"  Saved: results/sweep_policy_effectiveness.csv\n")
    return result


def sweep_usi_weights(base_config=None, runs_per_point=5):
    """
    4.6: Vary USI component weights to assess metric dominance.
    Tests giving full weight (1.0) to each component in turn.
    """
    cfg_base = copy.deepcopy(base_config or CONFIG)

    weight_sets = {
        "equal_0.25":  [0.25, 0.25, 0.25, 0.25],
        "trust_heavy": [0.10, 0.70, 0.10, 0.10],
        "S_R_heavy":   [0.70, 0.10, 0.10, 0.10],
        "S_I_heavy":   [0.10, 0.10, 0.70, 0.10],
        "S_O_heavy":   [0.10, 0.10, 0.10, 0.70],
    }

    rows = []
    print("Sweep: USI Weight Sensitivity")
    for name, weights in weight_sets.items():
        cfg = copy.deepcopy(cfg_base)
        cfg["usi_weights"] = weights

        print(f"  {name}...", end=" ", flush=True)
        summary_df, _ = run_monte_carlo(cfg, num_runs=runs_per_point,
                                        label=f"sweep_weights_{name}", verbose=False)
        rows.append({
            "weight_set": name,
            "w_SR":       weights[0],
            "w_C":        weights[1],
            "w_SI":       weights[2],
            "w_SO":       weights[3],
            "avg_usi":    summary_df["avg_usi"].mean(),
            "std_usi":    summary_df["avg_usi"].std(),
        })
        print(f"USI={rows[-1]['avg_usi']:.4f}")

    result = pd.DataFrame(rows)
    result.to_csv("results/sweep_usi_weights.csv", index=False)
    print(f"  Saved: results/sweep_usi_weights.csv\n")
    return result


def run_all_sweeps(base_config=None, runs_per_point=10):
    """Run all sensitivity sweeps in sequence."""
    print("\n=== Sensitivity Analysis ===\n")
    results = {}
    results["agent_count"]         = sweep_agent_count(base_config, runs_per_point)
    results["shock_magnitude"]      = sweep_shock_magnitude(base_config, runs_per_point)
    results["policy_effectiveness"] = sweep_policy_effectiveness(base_config, runs_per_point)
    results["usi_weights"]          = sweep_usi_weights(base_config, runs_per_point)
    print("=== All sweeps complete ===\n")
    return results
