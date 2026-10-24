"""Generate all 12 publication figures for research reproducibility and audit traceability."""

from __future__ import annotations
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from adaptive_route_optimization.analysis.visualizer import (
    plot_dynamicity_vs_cost,
    plot_dynamicity_vs_response_time,
    plot_size_vs_cost,
    plot_size_vs_runtime,
    plot_evals_vs_improvement,
    plot_paired_comparison,
    plot_route_disruption,
    plot_quality_vs_computation_tradeoff,
    plot_budget_ablation,
)


def main() -> None:
    fig_dir = "results/figures"
    os.makedirs(fig_dir, exist_ok=True)

    runs_df = pd.read_csv("results/pilot_matrix/runs.csv")
    budget_runs_df = pd.read_csv("results/budgeted_pilot/runs.csv")
    paired_df = pd.read_csv("results/tables/paired_strategy_comparison.csv")

    plot_dynamicity_vs_cost(runs_df, os.path.join(fig_dir, "fig1_dynamicity_vs_cost.png"))
    plot_dynamicity_vs_response_time(runs_df, os.path.join(fig_dir, "fig2_dynamicity_vs_response_time.png"))
    plot_size_vs_cost(runs_df, os.path.join(fig_dir, "fig3_size_vs_cost.png"))
    plot_size_vs_runtime(runs_df, os.path.join(fig_dir, "fig4_size_vs_runtime.png"))
    plot_evals_vs_improvement(paired_df, os.path.join(fig_dir, "fig5_evals_vs_cost_improvement.png"))
    plot_paired_comparison(paired_df, os.path.join(fig_dir, "fig6_paired_comparison.png"))
    plot_route_disruption(runs_df, os.path.join(fig_dir, "fig7_route_disruption.png"))
    plot_quality_vs_computation_tradeoff(runs_df, os.path.join(fig_dir, "fig8_quality_vs_computation_tradeoff.png"))
    plot_budget_ablation(budget_runs_df, os.path.join(fig_dir, "fig9_budget_ablation.png"))

    held_out_runs = pd.read_csv("results/held_out_matrix/runs.csv")
    triplets = pd.read_csv("results/tables/held_out_triplet_instances.csv")
    with open("results/tables/held_out_regret_summary.json", "r", encoding="utf-8") as f:
        reg_summary = json.load(f)

    # Fig 10
    plt.figure(figsize=(7, 5))
    dyn_grp = held_out_runs.groupby(["dynamicity", "strategy"])["final_cost"].mean().unstack()
    for col, color, mark in [("A", "#1f77b4", "o"), ("B", "#d62728", "s"), ("ADAPTIVE", "#2ca02c", "^")]:
        if col in dyn_grp:
            plt.plot(dyn_grp.index * 100, dyn_grp[col], f"-{mark}", color=color, label=f"Policy: {col}", linewidth=1.8, markersize=6)
    plt.xlabel("Dynamicity Level α (%)")
    plt.ylabel("Mean Final Route Cost")
    plt.title("Held-Out Evaluation: Route Cost across Dynamicity\n(Always A vs. Always B vs. Adaptive)")
    plt.grid(True)
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig10_adaptive_vs_baselines_cost.png"), dpi=200)
    plt.close()

    # Fig 11
    plt.figure(figsize=(7, 5))
    colors = {"A": "#1f77b4", "B": "#d62728", "ADAPTIVE": "#2ca02c"}
    for pol in ["A", "B", "ADAPTIVE"]:
        sub = held_out_runs[held_out_runs["strategy"] == pol]
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
    plt.savefig(os.path.join(fig_dir, "fig11_adaptive_pareto_frontier.png"), dpi=200)
    plt.close()

    # Fig 12
    mean_reg = reg_summary.get("mean_absolute_regret", 0.0)
    plt.figure(figsize=(6, 4.5))
    plt.hist(triplets["cost_regret"], bins=10, color="#2ca02c", edgecolor="black", alpha=0.8)
    plt.xlabel("Route Cost Regret (Adaptive - Oracle)")
    plt.ylabel("Frequency (Instances)")
    plt.title(f"Adaptive Selector Regret Distribution\n(Mean Regret = {mean_reg:.2f})")
    plt.grid(True, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig12_adaptive_regret_distribution.png"), dpi=200)
    plt.close()

    print("ALL_12_FIGURES_GENERATED_SUCCESSFULLY")


if __name__ == "__main__":
    main()
