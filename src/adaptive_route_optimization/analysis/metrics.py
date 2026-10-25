"""Metrics Aggregation and Paired Processing for Research Analysis.

Calculates comparative route quality, computational effort, response time,
route disruption, and scalability statistics.
References: RESEARCH_SPEC.md (Evaluation Metrics), PHASE_PLAN.md (Phase 7).
"""

from __future__ import annotations
from typing import Any, Optional
import numpy as np
import pandas as pd


def compute_relative_improvement(baseline_cost: float, optimized_cost: float) -> float:
    """Compute percentage reduction in route cost achieved by optimization.

    Formula:
        Δ% = ((baseline_cost - optimized_cost) / baseline_cost) * 100

    Positive values indicate that optimized_cost is lower (better) than baseline.
    """
    if baseline_cost <= 0:
        return 0.0
    return float(((baseline_cost - optimized_cost) / baseline_cost) * 100.0)


def build_paired_dataset(runs_df: pd.DataFrame) -> pd.DataFrame:
    """Construct paired observation dataset matching Strategy A and Strategy B.

    Matches strictly on identical (condition_id, seed, total_vertices, dynamicity),
    ensuring that comparisons are strictly pairwise per Non-Negotiable Rule 10.

    Returns:
        DataFrame with side-by-side columns and computed comparative metrics.
    """
    df_a = runs_df[runs_df["strategy"] == "A"].copy()
    df_b = runs_df[runs_df["strategy"] == "B"].copy()

    merge_keys = ["condition_id", "seed", "total_vertices", "dynamicity"]
    paired = pd.merge(
        df_a,
        df_b,
        on=merge_keys,
        suffixes=("_A", "_B"),
        how="inner",
    )

    # Core comparative metrics
    paired["cost_diff"] = paired["final_cost_A"] - paired["final_cost_B"]
    paired["pct_cost_improvement"] = (
        (paired["final_cost_A"] - paired["final_cost_B"]) / paired["final_cost_A"] * 100.0
    )

    paired["effort_ratio"] = paired["total_computational_effort_B"] / np.maximum(
        1, paired["total_computational_effort_A"]
    )
    paired["time_ratio"] = paired["total_response_time_ms_B"] / np.maximum(
        1e-6, paired["total_response_time_ms_A"]
    )

    paired["disruption_diff"] = paired["mean_disruption_B"] - paired["mean_disruption_A"]

    # Qualitative classification
    EPS = 1e-9
    paired["b_superior"] = paired["final_cost_B"] < (paired["final_cost_A"] - EPS)
    paired["b_equivalent"] = (paired["final_cost_A"] - paired["final_cost_B"]).abs() <= EPS
    paired["b_inferior"] = paired["final_cost_B"] > (paired["final_cost_A"] + EPS)

    return paired


def aggregate_by_condition(runs_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate primary experimental metrics by condition and strategy.

    Computes count, mean, std, median, min, max for cost, effort, response time, and disruption.
    """
    agg_funcs = ["count", "mean", "std", "median", "min", "max"]
    grouped = runs_df.groupby(["condition_id", "total_vertices", "dynamicity", "strategy"])

    summary = grouped.agg({
        "final_cost": agg_funcs,
        "total_computational_effort": agg_funcs,
        "total_response_time_ms": agg_funcs,
        "mean_disruption": agg_funcs,
    })

    # Flatten multi-index columns
    summary.columns = [f"{col}_{stat}" for col, stat in summary.columns]
    return summary.reset_index()


def aggregate_scalability(runs_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Analyze metric progression across problem sizes (n) and dynamicity levels (α).

    Returns:
        Tuple of (size_summary_df, dynamicity_summary_df).
    """
    size_summary = runs_df.groupby(["total_vertices", "strategy"]).agg({
        "final_cost": ["mean", "std"],
        "total_computational_effort": ["mean", "std"],
        "total_response_time_ms": ["mean", "std"],
        "mean_disruption": ["mean", "std"],
    })
    size_summary.columns = [f"{col}_{stat}" for col, stat in size_summary.columns]
    size_summary = size_summary.reset_index()

    dyn_summary = runs_df.groupby(["dynamicity", "strategy"]).agg({
        "final_cost": ["mean", "std"],
        "total_computational_effort": ["mean", "std"],
        "total_response_time_ms": ["mean", "std"],
        "mean_disruption": ["mean", "std"],
    })
    dyn_summary.columns = [f"{col}_{stat}" for col, stat in dyn_summary.columns]
    dyn_summary = dyn_summary.reset_index()

    return size_summary, dyn_summary


def compute_step_level_statistics(steps_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-dynamic-event step statistics (response time and computational effort)."""
    if steps_df is None or steps_df.empty:
        return pd.DataFrame()

    step_stats = steps_df.groupby(["strategy"]).agg(
        total_steps=("time_step", "count"),
        step_time_ms_mean=("response_time_ms", "mean"),
        step_time_ms_std=("response_time_ms", "std"),
        step_time_ms_median=("response_time_ms", "median"),
        step_time_ms_p95=("response_time_ms", lambda x: np.percentile(x, 95)),
        step_effort_mean=("computational_effort", "mean"),
        step_effort_median=("computational_effort", "median"),
        step_disruption_mean=("disruption", "mean"),
    ).reset_index()

    return step_stats
