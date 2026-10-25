"""Generate publication-grade figures for Stage 7 Adaptive v3 Campaign."""

from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def generate_figures():
    base_dir = "results/stage7_adaptive_c"
    fig_dir = os.path.join(base_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    runs_df = pd.read_csv(os.path.join(base_dir, "runs.csv"))
    paired_df = pd.read_csv(os.path.join(base_dir, "paired_comparisons.csv"))
    summary_df = pd.read_csv(os.path.join(base_dir, "summary.csv"))

    # Style
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({"font.size": 10, "figure.autolayout": True})

    # -----------------------------------------------------------------------
    # Figure 1: Cost by Condition & Strategy
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
    conds = sorted(runs_df["condition_id"].unique())
    x = np.arange(len(conds))
    width = 0.16

    strats = ["A", "B", "C", "ADAPTIVE_V2", "ADAPTIVE_V3"]
    colors = ["#7f7f7f", "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    labels = ["Strategy A (Greedy)", "Strategy B (2-opt)", "Strategy C (Destroy-Repair)", "Adaptive v2 (A/B)", "Adaptive v3 (A/B/C)"]

    for idx, (s, col, lab) in enumerate(zip(strats, colors, labels)):
        means = []
        for c in conds:
            sub = runs_df[(runs_df["condition_id"] == c) & (runs_df["strategy"] == s)]
            means.append(sub["final_cost"].mean() if not sub.empty else 0)
        ax.bar(x + (idx - 2) * width, means, width, label=lab, color=col, alpha=0.9)

    ax.set_ylabel("Mean Final Route Cost (Euclidean)")
    ax.set_title("Stage 7: Route Quality Comparison Across All 18 Experimental Conditions")
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("syn_", "").replace("tsplib_", "") for c in conds], rotation=45, ha="right")
    ax.legend(frameon=True)
    ax.grid(True, linestyle="--", alpha=0.5)

    f1_path = os.path.join(fig_dir, "cost_comparison_by_condition.png")
    fig.savefig(f1_path, dpi=300)
    plt.close(fig)
    print(f"Saved: {f1_path}")

    # -----------------------------------------------------------------------
    # Figure 2: Quality vs Computational Effort Pareto Frontier
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    for s, col, lab, marker in zip(strats, colors, labels, ["o", "s", "^", "D", "P"]):
        sub = runs_df[runs_df["strategy"] == s]
        mean_cost = sub["final_cost"].mean()
        mean_effort = sub["total_computational_effort"].mean()
        std_cost = sub["final_cost"].std() / np.sqrt(len(sub))
        ax.scatter(mean_effort, mean_cost, s=150, color=col, label=lab, marker=marker, edgecolors="black", zorder=5)
        ax.errorbar(mean_effort, mean_cost, yerr=std_cost, color=col, capsize=4, zorder=4)

    ax.set_xscale("log")
    ax.set_xlabel("Mean Computational Effort (Candidate Evaluations, Log Scale)")
    ax.set_ylabel("Mean Final Route Cost")
    ax.set_title("Stage 7: Quality vs. Computational Effort Pareto Trade-Off")
    ax.legend(frameon=True)
    ax.grid(True, which="both", linestyle="--", alpha=0.5)

    f2_path = os.path.join(fig_dir, "cost_vs_effort_pareto.png")
    fig.savefig(f2_path, dpi=300)
    plt.close(fig)
    print(f"Saved: {f2_path}")

    # -----------------------------------------------------------------------
    # Figure 3: Paired Cost Differences with 95% CIs
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    comparisons = [
        ("diff_cost_AdaptiveV3_vs_A", "Adaptive v3 vs Strategy A", "#1f77b4"),
        ("diff_cost_AdaptiveV3_vs_B", "Adaptive v3 vs Strategy B", "#2ca02c"),
        ("diff_cost_AdaptiveV3_vs_C", "Adaptive v3 vs Strategy C", "#ff7f0e"),
        ("diff_cost_AdaptiveV3_vs_V2", "Adaptive v3 vs Adaptive v2 (Ablation)", "#9467bd"),
        ("diff_cost_C_vs_A", "Strategy C vs Strategy A", "#d62728"),
        ("diff_cost_B_vs_A", "Strategy B vs Strategy A", "#8c564b"),
    ]

    y_pos = np.arange(len(comparisons))
    for idx, (col_name, lab, col) in enumerate(comparisons):
        if col_name in paired_df.columns:
            diffs = paired_df[col_name].dropna()
            mean_d = diffs.mean()
            ci = 1.96 * diffs.std(ddof=1) / np.sqrt(len(diffs))
            ax.errorbar(mean_d, idx, xerr=ci, fmt="o", color=col, ecolor=col, elinewidth=2, capsize=5, markersize=8)
            ax.text(mean_d, idx + 0.15, f"{mean_d:+.2f}", ha="center", fontsize=9, fontweight="bold", color=col)

    ax.axvline(0, color="black", linestyle="--", alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([c[1] for c in comparisons])
    ax.set_xlabel("Mean Paired Cost Difference (Negative = First Strategy is Better)")
    ax.set_title("Stage 7: Paired Tour Cost Differences with 95% Confidence Intervals (N=90 Pairs)")
    ax.grid(True, linestyle="--", alpha=0.5)

    f3_path = os.path.join(fig_dir, "paired_cost_differences.png")
    fig.savefig(f3_path, dpi=300)
    plt.close(fig)
    print(f"Saved: {f3_path}")

    # -----------------------------------------------------------------------
    # Figure 4: Strategy C Performance in Unbounded vs Bounded Conditions
    # -----------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    # Panel A: Unbounded conditions
    unbounded_conds = ["syn_uniform_n50_d0.4_unbounded", "syn_clustered_n50_d0.4_unbounded"]
    x_u = np.arange(len(unbounded_conds))
    w = 0.16
    for i, s in enumerate(strats):
        vals = [runs_df[(runs_df["condition_id"] == c) & (runs_df["strategy"] == s)]["final_cost"].mean() for c in unbounded_conds]
        ax1.bar(x_u + (i - 2) * w, vals, w, label=labels[i], color=colors[i], alpha=0.9)
    ax1.set_xticks(x_u)
    ax1.set_xticklabels(["Uniform (alpha=0.4)", "Clustered (alpha=0.4)"])
    ax1.set_ylabel("Final Route Cost")
    ax1.set_title("(a) Unbounded Reference Budget (LNS Active)")
    ax1.legend(fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Panel B: B=500 Conditions
    b500_conds = ["syn_uniform_n50_d0.4_b500", "syn_clustered_n50_d0.4_b500", "syn_uniform_n50_d0.4_burst_b500"]
    x_b = np.arange(len(b500_conds))
    for i, s in enumerate(strats):
        vals = [runs_df[(runs_df["condition_id"] == c) & (runs_df["strategy"] == s)]["final_cost"].mean() for c in b500_conds]
        ax2.bar(x_b + (i - 2) * w, vals, w, label=labels[i], color=colors[i], alpha=0.9)
    ax2.set_xticks(x_b)
    ax2.set_xticklabels(["Uniform (B=500)", "Clustered (B=500)", "Uniform Burst (k=2)"], rotation=15, ha="right")
    ax2.set_ylabel("Final Route Cost")
    ax2.set_title("(b) Bounded Budget B=500 Evaluation")
    ax2.legend(fontsize=8)
    ax2.grid(True, linestyle="--", alpha=0.5)

    f4_path = os.path.join(fig_dir, "strategy_c_budget_contrast.png")
    fig.savefig(f4_path, dpi=300)
    plt.close(fig)
    print(f"Saved: {f4_path}")

    print("All Stage 7 figures generated successfully!")


if __name__ == "__main__":
    generate_figures()
