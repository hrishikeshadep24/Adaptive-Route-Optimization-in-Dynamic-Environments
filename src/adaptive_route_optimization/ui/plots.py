"""Research Plotting Utilities for Dashboard.

Generates publication-quality charts directly from saved experimental datasets:
- Route Cost vs. Dynamicity across Strategies
- Candidate Evaluations (Computational Effort) scaling
- Quality vs. Computation Pareto Frontier
- Route Disruption comparison
- Budget Cap Diminishing Returns Ablation
- Adaptive Regret Distribution
"""

from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Color palette for consistent policy identity
POLICY_COLORS = {
    "A": "#1f77b4",          # Royal Blue
    "B": "#d62728",          # Crimson Red
    "ADAPTIVE": "#2ca02c",   # Forest Green
    "ORACLE": "#9467bd",     # Muted Purple
}

POLICY_LABELS = {
    "A": "Strategy A (Greedy Insertion)",
    "B": "Strategy B (Greedy + 2-opt)",
    "ADAPTIVE": "ADAPTIVE (Rule-Based)",
    "ORACLE": "Hindsight Oracle Benchmark",
}


def plot_cost_by_dynamicity(
    df: pd.DataFrame,
    title: str = "Mean Final Route Cost across Dynamicity",
    figsize: tuple[float, float] = (7.0, 4.5),
) -> plt.Figure:
    """Plot route cost vs dynamicity level (alpha) grouped by strategy."""
    fig, ax = plt.subplots(figsize=figsize, dpi=120)

    if "dynamicity" not in df.columns or "final_cost" not in df.columns:
        ax.text(0.5, 0.5, "Required columns missing", ha="center", va="center")
        return fig

    grouped = df.groupby(["dynamicity", "strategy"])["final_cost"].mean().unstack()

    for strat in ["A", "B", "ADAPTIVE"]:
        if strat in grouped.columns:
            ax.plot(
                grouped.index * 100,
                grouped[strat],
                marker="o",
                linewidth=2.0,
                markersize=6,
                color=POLICY_COLORS.get(strat, "#333333"),
                label=POLICY_LABELS.get(strat, strat),
            )

    ax.set_xlabel("Dynamicity Level α (%)", fontsize=10)
    ax.set_ylabel("Mean Final Route Cost", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True, fontsize=8)
    plt.tight_layout()
    return fig


def plot_effort_by_dynamicity(
    df: pd.DataFrame,
    title: str = "Computational Effort (Candidate Evaluations, Log Scale)",
    figsize: tuple[float, float] = (7.0, 4.5),
) -> plt.Figure:
    """Plot candidate evaluation counts across dynamicity on log scale."""
    fig, ax = plt.subplots(figsize=figsize, dpi=120)

    if "dynamicity" not in df.columns or "total_computational_effort" not in df.columns:
        ax.text(0.5, 0.5, "Required columns missing", ha="center", va="center")
        return fig

    grouped = df.groupby(["dynamicity", "strategy"])["total_computational_effort"].mean().unstack()

    for strat in ["A", "B", "ADAPTIVE"]:
        if strat in grouped.columns:
            ax.plot(
                grouped.index * 100,
                grouped[strat],
                marker="s",
                linewidth=2.0,
                markersize=6,
                color=POLICY_COLORS.get(strat, "#333333"),
                label=POLICY_LABELS.get(strat, strat),
            )

    ax.set_yscale("log")
    ax.set_xlabel("Dynamicity Level α (%)", fontsize=10)
    ax.set_ylabel("Candidate Evaluations (log scale)", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
    ax.grid(True, which="both", linestyle=":", alpha=0.6)
    ax.legend(frameon=True, fontsize=8)
    plt.tight_layout()
    return fig


def plot_pareto_frontier(
    df: pd.DataFrame,
    title: str = "Quality vs. Computation Pareto Scatter Comparison",
    figsize: tuple[float, float] = (7.5, 5.0),
) -> plt.Figure:
    """Plot cost vs computational effort scatter showing empirical trade-off frontier."""
    fig, ax = plt.subplots(figsize=figsize, dpi=120)

    if "total_computational_effort" not in df.columns or "final_cost" not in df.columns:
        ax.text(0.5, 0.5, "Required columns missing", ha="center", va="center")
        return fig

    for strat in ["A", "B", "ADAPTIVE"]:
        sub = df[df["strategy"] == strat]
        if not sub.empty:
            ax.scatter(
                sub["total_computational_effort"],
                sub["final_cost"],
                color=POLICY_COLORS.get(strat, "#333333"),
                label=POLICY_LABELS.get(strat, strat),
                alpha=0.75,
                edgecolors="black",
                linewidths=0.6,
                s=55,
            )

    ax.set_xscale("log")
    ax.set_xlabel("Candidate Evaluations (Effort, log scale)", fontsize=10)
    ax.set_ylabel("Final Route Cost (Lower is Better)", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
    ax.grid(True, which="both", linestyle=":", alpha=0.6)
    ax.legend(frameon=True, fontsize=8)
    plt.tight_layout()
    return fig


def plot_disruption_comparison(
    df: pd.DataFrame,
    title: str = "Mean Route Disruption (δ) by Strategy",
    figsize: tuple[float, float] = (6.0, 4.0),
) -> plt.Figure:
    """Plot bar chart comparing edge disruption across policies."""
    fig, ax = plt.subplots(figsize=figsize, dpi=120)

    if "mean_disruption" not in df.columns or "strategy" not in df.columns:
        ax.text(0.5, 0.5, "Required columns missing", ha="center", va="center")
        return fig

    means = df.groupby("strategy")["mean_disruption"].mean()
    stds = df.groupby("strategy")["mean_disruption"].std()

    strats = [s for s in ["A", "B", "ADAPTIVE"] if s in means.index]
    x_pos = np.arange(len(strats))
    vals = [means[s] for s in strats]
    errs = [stds[s] for s in strats]
    colors = [POLICY_COLORS.get(s, "#555") for s in strats]

    bars = ax.bar(x_pos, vals, yerr=errs, capsize=4, color=colors, alpha=0.85, edgecolor="black", width=0.55)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f"Strategy {s}" for s in strats], fontsize=9)
    ax.set_ylabel("Edge Disruption δ ∈ [0, 1]", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    # Value labels on top of bars
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.4f}", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    return fig


def plot_budget_ablation_chart(
    df_budget: pd.DataFrame,
    figsize: tuple[float, float] = (7.0, 4.2),
) -> plt.Figure:
    """Plot candidate evaluation savings vs quality for budget caps."""
    fig, ax = plt.subplots(figsize=figsize, dpi=120)

    # In budgeted_pilot: cap 200, cap 500, unbounded
    summary = df_budget.groupby(["strategy", "budget_type", "budget_limit"])[["final_cost", "total_computational_effort"]].mean().reset_index()

    labels = []
    costs = []
    efforts = []

    for _, r in summary.iterrows():
        strat = r["strategy"]
        btype = r["budget_type"]
        blim = r["budget_limit"]
        if strat == "A":
            labels.append("Strategy A")
        elif btype == "unbounded":
            labels.append("Strategy B (Unbounded)")
        else:
            labels.append(f"Strategy B (Cap {int(blim)})")
        costs.append(r["final_cost"])
        efforts.append(r["total_computational_effort"])

    ax.scatter(efforts, costs, s=120, c="#d62728", edgecolors="black", zorder=3)
    for i, txt in enumerate(labels):
        ax.annotate(f"{txt}\n({costs[i]:.1f}, {efforts[i]:.0f} evals)", (efforts[i], costs[i]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

    ax.set_xscale("log")
    ax.set_xlabel("Candidate Evaluations (Effort, log scale)", fontsize=10)
    ax.set_ylabel("Final Route Cost", fontsize=10)
    ax.set_title("Budget Cap Diminishing Returns (n=50, α=0.4)", fontsize=11, fontweight="bold", pad=10)
    ax.grid(True, which="both", linestyle=":", alpha=0.6)
    plt.tight_layout()
    return fig
