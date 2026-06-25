"""
Monte Carlo Runner — Phase 4
Executes R independent simulation runs with different random seeds.
Exports per-run CSVs and a summary CSV to results/.
"""
import os
import copy
import numpy as np
import pandas as pd
from model.urban_model import UrbanStabilityModel


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def _ensure_dirs():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(RESULTS_DIR, "plots"), exist_ok=True)


def run_single(config, seed):
    """
    Run one simulation with the given config and seed.
    Returns a dict with scalar summaries and the full time-series DataFrame.
    """
    cfg = copy.deepcopy(config)
    cfg["random_seed"] = seed

    model = UrbanStabilityModel(config=cfg)

    for _ in range(cfg["num_steps"]):
        if not model.running:
            break
        model.step()

    data = model.datacollector.get_model_vars_dataframe()

    # Time to collapse: first step where model stopped running (if any)
    if not model.running:
        time_to_collapse = model.current_step
    else:
        time_to_collapse = None

    summary = {
        "seed":              seed,
        "avg_usi":           data["USI"].mean(),
        "min_usi":           data["USI"].min(),
        "max_usi":           data["USI"].max(),
        "final_usi":         data["USI"].iloc[-1],
        "avg_gini":          data["Gini"].mean(),
        "final_gini":        data["Gini"].iloc[-1],
        "avg_trust":         data["Average_Trust"].mean(),
        "final_trust":       data["Average_Trust"].iloc[-1],
        "avg_S_R":           data["S_R"].mean(),
        "avg_S_I":           data["S_I"].mean(),
        "avg_S_O":           data["S_O"].mean(),
        "time_to_collapse":  time_to_collapse,
        "completed_steps":   model.current_step,
    }

    return summary, data


def run_monte_carlo(config, num_runs=None, label="run", verbose=True):
    """
    Execute R independent runs and export results to CSV.

    Args:
        config    : CONFIG dict (or deep copy with overrides)
        num_runs  : number of runs (default: config["num_runs"])
        label     : prefix for output files (e.g. "baseline", "shock")
        verbose   : print progress

    Returns:
        summary_df : DataFrame with one row per run (scalar metrics)
        all_series : dict {seed: time-series DataFrame}
    """
    _ensure_dirs()

    R = num_runs or config.get("num_runs", 30)
    seeds = [42 + i for i in range(R)]

    summaries = []
    all_series = {}

    for i, seed in enumerate(seeds):
        if verbose:
            print(f"  Run {i+1:3d}/{R}  (seed={seed})", end="\r")

        summary, data = run_single(config, seed)
        summaries.append(summary)
        all_series[seed] = data

        # Export per-run CSV
        run_filename = os.path.join(RESULTS_DIR, f"{label}_run_{i+1:03d}.csv")
        data.to_csv(run_filename)

    if verbose:
        print(f"  {R} runs complete.          ")

    summary_df = pd.DataFrame(summaries)

    # Export summary CSV
    summary_path = os.path.join(RESULTS_DIR, f"{label}_summary.csv")
    summary_df.to_csv(summary_path, index=False)

    if verbose:
        print(f"  Summary saved to: {summary_path}")
        _print_summary(summary_df, label)

    return summary_df, all_series


def _print_summary(df, label):
    print(f"\n  === Monte Carlo Summary: {label} ({len(df)} runs) ===")
    print(f"  USI  : mean={df['avg_usi'].mean():.4f}, "
          f"std={df['avg_usi'].std():.4f}, "
          f"min={df['min_usi'].min():.4f}, "
          f"max={df['max_usi'].max():.4f}")
    print(f"  Gini : mean={df['avg_gini'].mean():.4f}, "
          f"std={df['avg_gini'].std():.4f}")
    print(f"  Trust: mean={df['avg_trust'].mean():.4f}, "
          f"std={df['avg_trust'].std():.4f}")
    collapsed = df["time_to_collapse"].notna().sum()
    print(f"  Collapsed runs: {collapsed}/{len(df)}")
    print()


def get_confidence_bands(all_series, metric="USI"):
    """
    Compute mean, std, upper/lower 95% confidence bands across all runs.
    Returns a DataFrame indexed by step with columns: mean, std, lower, upper.
    """
    frames = [df[metric] for df in all_series.values()]
    combined = pd.concat(frames, axis=1)
    combined.columns = range(len(frames))

    stats = pd.DataFrame({
        "mean":  combined.mean(axis=1),
        "std":   combined.std(axis=1),
        "lower": combined.mean(axis=1) - 1.96 * combined.std(axis=1),
        "upper": combined.mean(axis=1) + 1.96 * combined.std(axis=1),
    })
    return stats
