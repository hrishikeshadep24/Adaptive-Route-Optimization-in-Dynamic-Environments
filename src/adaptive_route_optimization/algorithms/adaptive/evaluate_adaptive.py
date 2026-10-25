"""Evaluation and Comparative Reporting for Adaptive Strategy Selection (Phase 8).

Analyzes held-out experimental results comparing Always Strategy A, Always Strategy B,
the Adaptive Selector, and the Theoretical Oracle upper-bound.
References: RESEARCH_SPEC.md, MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phase 8).
"""

from __future__ import annotations
import json
import os
from typing import Any, Optional
import numpy as np
import pandas as pd
from adaptive_route_optimization.paths import resolve_repo_path

# Headless matplotlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from adaptive_route_optimization.algorithms.adaptive.oracle import OracleEvaluator, RegretSummary


def evaluate_held_out_results(
    held_out_runs_path: str = "results/held_out_matrix/runs.csv",
    tables_dir: str = "results/tables",
    figures_dir: str = "results/figures",
) -> dict[str, Any]:
    """Analyze held-out experiment outputs and generate comparison tables and figures.

    Args:
        held_out_runs_path: Path to runs.csv from held-out experiment batch.
        tables_dir: Output directory for summary tables.
        figures_dir: Output directory for evaluation plots.

    Returns:
        Dictionary containing summary statistics and evaluation verdict.
    """
    if not os.path.exists(held_out_runs_path):
        raise FileNotFoundError(f"Held-out runs file not found: {held_out_runs_path}")

    held_out_runs_path = resolve_repo_path(held_out_runs_path)
    tables_dir = resolve_repo_path(tables_dir)
    figures_dir = resolve_repo_path(figures_dir)
    runs_df = pd.read_csv(held_out_runs_path)
    os.makedirs(tables_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    # 1. Pivot runs into triplet observation format [A, B, ADAPTIVE]
    eval_df = OracleEvaluator.compute_instance_oracle_and_regret(runs_df)
    regret_summary = OracleEvaluator.summarize_regret(eval_df)

    # 2. Overall Policy Performance Comparison
    policies = ["A", "B", "ADAPTIVE"]
    policy_summary_rows = []
    for pol in policies:
        sub = runs_df[runs_df["strategy"] == pol]
        policy_summary_rows.append({
            "policy": pol,
            "mean_cost": float(sub["final_cost"].mean()),
            "std_cost": float(sub["final_cost"].std()),
            "median_cost": float(sub["final_cost"].median()),
            "mean_effort": float(sub["total_computational_effort"].mean()),
            "std_effort": float(sub["total_computational_effort"].std()),
            "median_effort": float(sub["total_computational_effort"].median()),
            "mean_response_time_ms": float(sub["total_response_time_ms"].mean()),
            "mean_disruption": float(sub["mean_disruption"].mean()),
            "feasible_rate_pct": float(sub["all_feasible"].mean() * 100.0),
        })
    policy_comp_df = pd.DataFrame(policy_summary_rows)

    # 3. Regime Breakdown (Low α <= 0.2, Moderate α = 0.4, High α >= 0.6)
    def assign_regime(a: float) -> str:
        if a <= 0.2:
            return "Low (α <= 0.2)"
        elif a <= 0.4:
            return "Moderate (α = 0.4)"
        else:
            return "High (α >= 0.6)"

    eval_df["regime"] = eval_df["dynamicity"].apply(assign_regime)

    regime_rows = []
    for reg, grp in eval_df.groupby("regime"):
        cost_a = grp["final_cost_A"].mean()
        cost_b = grp["final_cost_B"].mean()
        cost_adapt = grp["final_cost_ADAPTIVE"].mean()
        cost_oracle = grp["cost_oracle"].mean()

        effort_a = grp["total_computational_effort_A"].mean()
        effort_b = grp["total_computational_effort_B"].mean()
        effort_adapt = grp["total_computational_effort_ADAPTIVE"].mean()

        regime_rows.append({
            "regime": reg,
            "instances": len(grp),
            "cost_strategy_a": cost_a,
            "cost_strategy_b": cost_b,
            "cost_adaptive": cost_adapt,
            "cost_oracle": cost_oracle,
            "impr_over_A_pct": ((cost_a - cost_adapt) / cost_a) * 100.0,
            "impr_over_B_pct": ((cost_b - cost_adapt) / cost_b) * 100.0,
            "effort_strategy_a": effort_a,
            "effort_strategy_b": effort_b,
            "effort_adaptive": effort_adapt,
            "effort_savings_vs_B_pct": ((effort_b - effort_adapt) / max(1, effort_b)) * 100.0,
            "mean_cost_regret": grp["cost_regret"].mean(),
            "mean_cost_regret_pct": grp["cost_regret_pct"].mean(),
        })
    regime_df = pd.DataFrame(regime_rows)

    # 4. Save Tables
    eval_df.to_csv(os.path.join(tables_dir, "held_out_triplet_instances.csv"), index=False)
    policy_comp_df.to_csv(os.path.join(tables_dir, "held_out_policy_comparison.csv"), index=False)
    regime_df.to_csv(os.path.join(tables_dir, "held_out_regime_comparison.csv"), index=False)

    with open(os.path.join(tables_dir, "held_out_regret_summary.json"), "w", encoding="utf-8") as f:
        json.dump(regret_summary.to_dict(), f, indent=2)

    # 5. Generate Figures
    # Fig 10: Policy Cost Comparison across Dynamicity
    plt.figure(figsize=(7, 5))
    dyn_grp = runs_df.groupby(["dynamicity", "strategy"])["final_cost"].mean().unstack()
    for col, color, mark in [("A", "#1f77b4", "o"), ("B", "#d62728", "s"), ("ADAPTIVE", "#2ca02c", "^")]:
        if col in dyn_grp:
            plt.plot(dyn_grp.index * 100, dyn_grp[col], f"-{mark}", color=color, label=f"Policy: {col}", linewidth=1.8, markersize=6)
    plt.xlabel("Dynamicity Level α (%)")
    plt.ylabel("Mean Final Route Cost")
    plt.title("Held-Out Evaluation: Route Cost across Dynamicity\n(Always A vs. Always B vs. Adaptive)")
    plt.grid(True)
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "fig10_adaptive_vs_baselines_cost.png"), dpi=200)
    plt.close()

    # Fig 11: Quality vs Computation Pareto Frontier (A, B, ADAPTIVE, ORACLE)
    plt.figure(figsize=(7, 5))
    colors = {"A": "#1f77b4", "B": "#d62728", "ADAPTIVE": "#2ca02c"}
    for pol in ["A", "B", "ADAPTIVE"]:
        sub = runs_df[runs_df["strategy"] == pol]
        plt.scatter(
            sub["total_computational_effort"],
            sub["final_cost"],
            color=colors[pol],
            label=f"Policy: {pol}",
            alpha=0.75,
            edgecolors="k",
            linewidths=0.5,
            s=45,
        )
    plt.xscale("log")
    plt.xlabel("Total Candidate Evaluations (log scale)")
    plt.ylabel("Final Route Cost")
    plt.title("Held-Out Quality vs. Computation Pareto Comparison")
    plt.grid(True, which="both")
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "fig11_adaptive_pareto_frontier.png"), dpi=200)
    plt.close()

    # Fig 12: Regret Distribution
    plt.figure(figsize=(6, 4.5))
    plt.hist(eval_df["cost_regret"], bins=10, color="#2ca02c", edgecolor="black", alpha=0.8)
    plt.xlabel("Route Cost Regret (Adaptive - Oracle)")
    plt.ylabel("Frequency (Instances)")
    plt.title(f"Adaptive Selector Regret Distribution\n(Mean Regret = {regret_summary.mean_absolute_regret:.2f})")
    plt.grid(True, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "fig12_adaptive_regret_distribution.png"), dpi=200)
    plt.close()

    return {
        "regret_summary": regret_summary.to_dict(),
        "policy_comparison": policy_comp_df.to_dict(orient="records"),
        "regime_comparison": regime_df.to_dict(orient="records"),
    }
