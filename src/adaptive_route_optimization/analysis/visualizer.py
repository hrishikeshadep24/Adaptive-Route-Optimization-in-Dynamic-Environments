"""Publication-Quality Scientific Visualizations for Experimental Analysis.

Generates the required research figures directly from verified experimental outputs,
incorporating uncertainty bars, clear axis units, sample sizes, and legends.
References: RESEARCH_SPEC.md, PHASE_PLAN.md (Phase 7 deliverables: plots).
"""

from __future__ import annotations
import os
from typing import Optional
import numpy as np
import pandas as pd

# Use Agg backend for headless / CI environments
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def set_plot_style() -> None:
    """Apply clean publication styling parameters."""
    plt.rcParams.update({
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 13,
        "grid.linestyle": ":",
        "grid.alpha": 0.6,
    })


def plot_dynamicity_vs_cost(
    runs_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 1: Dynamicity (α) versus Final Route Cost by Strategy."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    # Average over seeds for each (dynamicity, strategy)
    grouped = runs_df.groupby(["dynamicity", "strategy"]).agg(
        mean_cost=("final_cost", "mean"),
        std_cost=("final_cost", "std"),
        count=("final_cost", "count"),
    ).reset_index()

    for strat, color, marker, label in [
        ("A", "#1f77b4", "o", "Strategy A (Greedy Insertion)"),
        ("B", "#d62728", "s", "Strategy B (Insertion + 2-opt)"),
    ]:
        data = grouped[grouped["strategy"] == strat].sort_values("dynamicity")
        ax.errorbar(
            data["dynamicity"] * 100,
            data["mean_cost"],
            yerr=data["std_cost"],
            fmt=f"-{marker}",
            color=color,
            label=label,
            capsize=4,
            linewidth=1.8,
            markersize=6,
        )

    ax.set_xlabel("Dynamicity Level α (%)")
    ax.set_ylabel("Final Route Cost (Euclidean distance units)")
    ax.set_title("Dynamicity vs. Final Route Cost\n(Mean ± 1 SD across all problem sizes and seeds)")
    ax.grid(True)
    ax.legend(frameon=True)
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_dynamicity_vs_response_time(
    runs_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 2: Dynamicity (α) versus Update Response Time (Total ms) by Strategy."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    grouped = runs_df.groupby(["dynamicity", "strategy"]).agg(
        mean_time=("total_response_time_ms", "mean"),
        std_time=("total_response_time_ms", "std"),
    ).reset_index()

    for strat, color, marker, label in [
        ("A", "#1f77b4", "o", "Strategy A (Greedy Insertion)"),
        ("B", "#d62728", "s", "Strategy B (Insertion + 2-opt)"),
    ]:
        data = grouped[grouped["strategy"] == strat].sort_values("dynamicity")
        ax.errorbar(
            data["dynamicity"] * 100,
            data["mean_time"],
            yerr=data["std_time"],
            fmt=f"-{marker}",
            color=color,
            label=label,
            capsize=4,
            linewidth=1.8,
            markersize=6,
        )

    ax.set_yscale("log")
    ax.set_xlabel("Dynamicity Level α (%)")
    ax.set_ylabel("Total Response Time (ms, log scale)")
    ax.set_title("Dynamicity vs. Total Response Time (Log Scale)\n(Mean ± 1 SD)")
    ax.grid(True, which="both")
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_size_vs_cost(
    runs_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 3: Problem Size (n vertices) versus Route Cost."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    grouped = runs_df.groupby(["total_vertices", "strategy"]).agg(
        mean_cost=("final_cost", "mean"),
        std_cost=("final_cost", "std"),
    ).reset_index()

    for strat, color, marker, label in [
        ("A", "#1f77b4", "o", "Strategy A (Greedy Insertion)"),
        ("B", "#d62728", "s", "Strategy B (Insertion + 2-opt)"),
    ]:
        data = grouped[grouped["strategy"] == strat].sort_values("total_vertices")
        ax.errorbar(
            data["total_vertices"],
            data["mean_cost"],
            yerr=data["std_cost"],
            fmt=f"-{marker}",
            color=color,
            label=label,
            capsize=4,
            linewidth=1.8,
            markersize=6,
        )

    ax.set_xlabel("Problem Size n (Customer Vertices)")
    ax.set_ylabel("Final Route Cost (Euclidean distance)")
    ax.set_title("Problem Size vs. Final Route Cost\n(Mean ± 1 SD across dynamicity levels)")
    ax.grid(True)
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_size_vs_runtime(
    runs_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 4: Problem Size (n vertices) versus Total Runtime (ms)."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    grouped = runs_df.groupby(["total_vertices", "strategy"]).agg(
        mean_time=("total_response_time_ms", "mean"),
        std_time=("total_response_time_ms", "std"),
    ).reset_index()

    for strat, color, marker, label in [
        ("A", "#1f77b4", "o", "Strategy A (Greedy Insertion)"),
        ("B", "#d62728", "s", "Strategy B (Insertion + 2-opt)"),
    ]:
        data = grouped[grouped["strategy"] == strat].sort_values("total_vertices")
        ax.errorbar(
            data["total_vertices"],
            data["mean_time"],
            yerr=data["std_time"],
            fmt=f"-{marker}",
            color=color,
            label=label,
            capsize=4,
            linewidth=1.8,
            markersize=6,
        )

    ax.set_yscale("log")
    ax.set_xlabel("Problem Size n (Customer Vertices)")
    ax.set_ylabel("Response Time (ms, log scale)")
    ax.set_title("Problem Size vs. Total Response Time (Log Scale)")
    ax.grid(True, which="both")
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_evals_vs_improvement(
    paired_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 5: Additional Candidate Evaluations vs. Route-Quality Improvement (%)."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    x = paired_df["total_computational_effort_B"] - paired_df["total_computational_effort_A"]
    y = paired_df["pct_cost_improvement"]
    sizes = paired_df["total_vertices"]

    scatter = ax.scatter(
        x,
        y,
        c=paired_df["dynamicity"] * 100,
        cmap="viridis",
        s=sizes * 0.8,
        alpha=0.8,
        edgecolors="k",
        linewidths=0.5,
    )

    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Dynamicity Level α (%)")

    ax.axhline(0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xscale("log")
    ax.set_xlabel("Additional Candidate Evaluations (B - A, log scale)")
    ax.set_ylabel("Route Cost Improvement of B over A (%)")
    ax.set_title("Computational Effort vs. Route-Quality Improvement\n(Marker size = problem size n)")
    ax.grid(True, which="both")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_paired_comparison(
    paired_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 6: Strategy A versus Strategy B Paired Cost Comparison (Parity Plot)."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(6, 6))

    cost_a = paired_df["final_cost_A"]
    cost_b = paired_df["final_cost_B"]

    min_val = min(cost_a.min(), cost_b.min()) * 0.95
    max_val = max(cost_a.max(), cost_b.max()) * 1.05

    # Identity / parity line: y = x
    ax.plot([min_val, max_val], [min_val, max_val], "k--", label="Parity Line (Cost A = Cost B)", alpha=0.7)

    # Color by dynamicity
    scatter = ax.scatter(
        cost_a,
        cost_b,
        c=paired_df["dynamicity"] * 100,
        cmap="coolwarm",
        s=50,
        alpha=0.85,
        edgecolors="k",
        linewidths=0.5,
    )

    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Dynamicity Level α (%)")

    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)
    ax.set_aspect("equal")
    ax.set_xlabel("Strategy A Final Route Cost")
    ax.set_ylabel("Strategy B Final Route Cost")
    ax.set_title("Paired Route Cost Parity Plot\n(Points below diagonal indicate Strategy B is better)")
    ax.grid(True)
    ax.legend(frameon=True, loc="upper left")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_route_disruption(
    runs_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 7: Route Disruption (δ) by Strategy and Dynamicity."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    grouped = runs_df.groupby(["dynamicity", "strategy"]).agg(
        mean_disr=("mean_disruption", "mean"),
        std_disr=("mean_disruption", "std"),
    ).reset_index()

    width = 3.5
    dyns = sorted(runs_df["dynamicity"].unique())
    x_indices = np.array(dyns) * 100

    data_a = grouped[grouped["strategy"] == "A"].sort_values("dynamicity")
    data_b = grouped[grouped["strategy"] == "B"].sort_values("dynamicity")

    ax.bar(
        x_indices - width / 2,
        data_a["mean_disr"],
        width=width,
        yerr=data_a["std_disr"],
        capsize=3,
        color="#1f77b4",
        label="Strategy A (Greedy Insertion)",
        alpha=0.85,
    )
    ax.bar(
        x_indices + width / 2,
        data_b["mean_disr"],
        width=width,
        yerr=data_b["std_disr"],
        capsize=3,
        color="#d62728",
        label="Strategy B (Insertion + 2-opt)",
        alpha=0.85,
    )

    ax.set_xlabel("Dynamicity Level α (%)")
    ax.set_ylabel("Mean Route Disruption δ ∈ [0, 1]")
    ax.set_title("Edge-Based Route Disruption by Strategy and Dynamicity\n(Mean ± 1 SD)")
    ax.grid(True, axis="y")
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_quality_vs_computation_tradeoff(
    runs_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 8: Quality-versus-Computation Trade-off Frontier."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    for strat, color, marker, label in [
        ("A", "#1f77b4", "o", "Strategy A (Greedy Insertion)"),
        ("B", "#d62728", "s", "Strategy B (Insertion + 2-opt)"),
    ]:
        data = runs_df[runs_df["strategy"] == strat]
        ax.scatter(
            data["total_computational_effort"],
            data["final_cost"],
            color=color,
            marker=marker,
            alpha=0.7,
            s=45,
            label=label,
            edgecolors="k",
            linewidths=0.5,
        )

    ax.set_xscale("log")
    ax.set_xlabel("Total Candidate Evaluations (log scale)")
    ax.set_ylabel("Final Route Cost (lower is better)")
    ax.set_title("Quality vs. Computation Trade-Off\n(Candidate Evaluations vs. Route Cost)")
    ax.grid(True, which="both")
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_budget_ablation(
    budget_runs_df: pd.DataFrame,
    output_path: str,
) -> None:
    """Fig 9: Impact of Candidate Evaluation Budget Cap on Strategy B."""
    if budget_runs_df.empty:
        return

    set_plot_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    b_runs = budget_runs_df[budget_runs_df["strategy"] == "B"].copy()
    b_runs["budget_label"] = b_runs["budget_limit"].fillna("Unbounded").astype(str)

    grouped = b_runs.groupby("budget_label", sort=False).agg(
        mean_cost=("final_cost", "mean"),
        std_cost=("final_cost", "std"),
        mean_effort=("total_computational_effort", "mean"),
        std_effort=("total_computational_effort", "std"),
    ).reset_index()

    order = ["200.0", "500.0", "Unbounded"]
    grouped["order_key"] = grouped["budget_label"].apply(lambda x: order.index(x) if x in order else 99)
    grouped = grouped.sort_values("order_key")

    labels = ["Cap: 200", "Cap: 500", "Unbounded"]

    ax1.bar(
        labels,
        grouped["mean_cost"],
        yerr=grouped["std_cost"],
        capsize=4,
        color="#2ca02c",
        alpha=0.85,
    )
    ax1.set_ylabel("Mean Final Route Cost")
    ax1.set_title("Route Cost under Budget Limits")
    ax1.grid(True, axis="y")

    ax2.bar(
        labels,
        grouped["mean_effort"],
        yerr=grouped["std_effort"],
        capsize=4,
        color="#ff7f0e",
        alpha=0.85,
    )
    ax2.set_ylabel("Total Candidate Evaluations")
    ax2.set_title("Computational Effort under Budget Limits")
    ax2.grid(True, axis="y")

    fig.suptitle("Computational Budget Cap Ablation (n=50, α=0.4)", y=1.02)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
