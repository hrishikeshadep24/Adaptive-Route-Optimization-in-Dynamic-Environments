"""Ablation Studies for Strategy Components and Computational Budgets.

Explicitly isolates the marginal benefit and overhead of adding 2-opt local search
to greedy insertion (Strategy B vs Strategy A), as well as budget cap ablations.
References: MASTER_BLUEPRINT.md (Ablation plan), PHASE_PLAN.md (Phase 7).
"""

from __future__ import annotations
from typing import Any, Optional
import numpy as np
import pandas as pd


def analyze_component_ablation(paired_df: pd.DataFrame) -> pd.DataFrame:
    """Isolate the marginal contribution of 2-opt local search over greedy insertion.

    Baseline component: Cheapest Insertion (Strategy A).
    Augmented component: Cheapest Insertion + 2-opt Local Search (Strategy B).

    Calculates:
    - Absolute cost delta: Cost(A) - Cost(B)
    - Relative cost improvement (%): (Cost(A) - Cost(B)) / Cost(A) * 100
    - Multiplier in candidate evaluations: Effort(B) / Effort(A)
    - Multiplier in runtime: Time(B) / Time(A)
    - Cost-to-effort efficiency: (Cost Improvement %) / (Additional Evaluations / 1000)

    Returns:
        DataFrame summarizing component ablation across conditions.
    """
    df = paired_df.copy()

    df["marginal_cost_saving"] = df["final_cost_A"] - df["final_cost_B"]
    df["marginal_effort_cost"] = df["total_computational_effort_B"] - df["total_computational_effort_A"]
    df["marginal_time_cost_ms"] = df["total_response_time_ms_B"] - df["total_response_time_ms_A"]

    # Summary by condition
    grouped = df.groupby(["condition_id", "total_vertices", "dynamicity"]).agg(
        n_seeds=("seed", "count"),
        mean_cost_A=("final_cost_A", "mean"),
        mean_cost_B=("final_cost_B", "mean"),
        mean_pct_cost_improvement=("pct_cost_improvement", "mean"),
        b_wins=("b_superior", "sum"),
        b_losses=("b_inferior", "sum"),
        mean_effort_A=("total_computational_effort_A", "mean"),
        mean_effort_B=("total_computational_effort_B", "mean"),
        mean_effort_multiplier=("effort_ratio", "mean"),
        mean_time_A_ms=("total_response_time_ms_A", "mean"),
        mean_time_B_ms=("total_response_time_ms_B", "mean"),
        mean_time_multiplier=("time_ratio", "mean"),
        mean_disruption_A=("mean_disruption_A", "mean"),
        mean_disruption_B=("mean_disruption_B", "mean"),
    ).reset_index()

    grouped["pct_win_rate"] = (grouped["b_wins"] / grouped["n_seeds"]) * 100.0
    return grouped


def analyze_dynamicity_regime_ablation(paired_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze the effectiveness of 2-opt local search across dynamicity regimes.

    Regimes:
    - Low dynamicity (α <= 0.2): early route is well-known up-front.
    - Moderate dynamicity (α = 0.4): balanced dynamic revelation.
    - High dynamicity (α >= 0.6): majority of vertices arrive dynamically.
    """
    df = paired_df.copy()

    def get_regime(alpha: float) -> str:
        if alpha <= 0.2:
            return "Low (α <= 0.2)"
        elif alpha <= 0.4:
            return "Moderate (α = 0.4)"
        else:
            return "High (α >= 0.6)"

    df["regime"] = df["dynamicity"].apply(get_regime)

    regime_summary = df.groupby("regime").agg(
        total_runs=("seed", "count"),
        b_superior_count=("b_superior", "sum"),
        b_inferior_count=("b_inferior", "sum"),
        mean_pct_improvement=("pct_cost_improvement", "mean"),
        median_pct_improvement=("pct_cost_improvement", "median"),
        min_pct_improvement=("pct_cost_improvement", "min"),
        max_pct_improvement=("pct_cost_improvement", "max"),
        mean_effort_ratio=("effort_ratio", "mean"),
        mean_time_ratio=("time_ratio", "mean"),
    ).reset_index()

    regime_summary["win_rate_pct"] = (
        regime_summary["b_superior_count"] / regime_summary["total_runs"] * 100.0
    )
    return regime_summary


def analyze_budget_cap_ablation(budget_runs_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze how computational budget capping impacts Strategy B performance.

    Compares unbounded local search vs capped candidate evaluations (e.g. 500, 200).
    """
    if budget_runs_df.empty:
        return pd.DataFrame()

    grouped = budget_runs_df.groupby(["condition_id", "strategy", "budget_type", "budget_limit"]).agg(
        n_seeds=("seed", "count"),
        mean_final_cost=("final_cost", "mean"),
        mean_effort=("total_computational_effort", "mean"),
        mean_time_ms=("total_response_time_ms", "mean"),
        mean_disruption=("mean_disruption", "mean"),
    ).reset_index()

    return grouped
