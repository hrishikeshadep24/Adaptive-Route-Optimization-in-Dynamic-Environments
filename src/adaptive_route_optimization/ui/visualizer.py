"""Interactive 2D Spatial Route Visualizer for Dashboard.

Renders high-clarity 2D Euclidean route diagrams highlighting:
- Red square: Depot (0)
- Green solid line & circles: Immutable frozen prefix (already traversed)
- Blue dashed line & circles: Uncommitted suffix (re-optimized during repair)
- Orange markers: Newly revealed dynamic customer vertices (Δ_t)
- Directional arrowheads illustrating tour sequence
"""

from __future__ import annotations
from typing import Optional, Sequence
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


def render_route_step_diagram(
    instance: Instance,
    current_route: Route,
    frozen_prefix_length: int,
    newly_revealed_vertices: Optional[Sequence[int]] = None,
    previous_route: Optional[Route] = None,
    title: str = "Route State",
    step_number: int = 0,
    cost_before: Optional[float] = None,
    cost_after: Optional[float] = None,
    evals_used: Optional[int] = None,
    strategy_label: Optional[str] = None,
    figsize: tuple[float, float] = (7.5, 6.0),
) -> plt.Figure:
    """Render a publication-quality 2D tour visualization for a dynamic step.

    Args:
        instance: Problem instance containing 2D vertex coordinates.
        current_route: Tour sequence S_t at this step.
        frozen_prefix_length: Number of frozen customer vertices f_t (prefix length).
        newly_revealed_vertices: Customer vertices arriving in this event step Δ_t.
        previous_route: Optional prior tour S_{t-1} for comparison.
        title: Plot title.
        step_number: Current dynamic step t.
        cost_before: Tour length before dynamic repair.
        cost_after: Tour length after dynamic repair.
        evals_used: Candidate evaluations consumed by update.
        strategy_label: Strategy identifier (e.g. 'Strategy A (Greedy)', 'ADAPTIVE').
        figsize: Matplotlib figure dimensions.

    Returns:
        Matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=120)
    coords = instance.coords  # shape (N, 2)
    vertices = current_route.vertices
    n_vertices = len(vertices)

    # 1. Plot Unrevealed/Background Vertices (if full instance has more vertices)
    known_set = set(vertices)
    all_verts = set(range(instance.num_vertices))
    unrevealed = all_verts - known_set
    if unrevealed:
        unrev_coords = np.array([coords[v] for v in unrevealed])
        ax.scatter(
            unrev_coords[:, 0],
            unrev_coords[:, 1],
            c="#d3d3d3",
            s=35,
            alpha=0.5,
            edgecolors="gray",
            linewidths=0.5,
            label="Unrevealed Customers",
            zorder=2,
        )

    # 2. Draw Route Edges
    # The route has (frozen_prefix_length + 1) frozen vertices at the start:
    # vertices[0] (depot 0), vertices[1], ..., vertices[frozen_prefix_length]
    # Edges between indices 0..frozen_prefix_length are FROZEN.
    # Edges after frozen_prefix_length are UNCOMMITTED SUFFIX.
    frozen_idx_end = min(frozen_prefix_length, n_vertices - 1)

    # Frozen Prefix Edges (Solid Green)
    if frozen_idx_end > 0:
        prefix_x = [coords[vertices[i]][0] for i in range(frozen_idx_end + 1)]
        prefix_y = [coords[vertices[i]][1] for i in range(frozen_idx_end + 1)]
        ax.plot(
            prefix_x,
            prefix_y,
            "-",
            color="#2ca02c",
            linewidth=3.0,
            label=f"Frozen Prefix (Committed: {frozen_prefix_length})",
            zorder=3,
        )

    # Uncommitted Suffix Edges (Dashed Royal Blue)
    if frozen_idx_end < n_vertices - 1:
        suffix_x = [coords[vertices[i]][0] for i in range(frozen_idx_end, n_vertices)]
        suffix_y = [coords[vertices[i]][1] for i in range(frozen_idx_end, n_vertices)]
        ax.plot(
            suffix_x,
            suffix_y,
            "--",
            color="#1f77b4",
            linewidth=2.0,
            alpha=0.85,
            label="Uncommitted Suffix (Re-optimized)",
            zorder=3,
        )

    # 3. Draw Vertices by Role
    # Depot (0)
    depot_coord = coords[0]
    ax.scatter(
        [depot_coord[0]],
        [depot_coord[1]],
        marker="s",
        c="#d62728",
        s=140,
        edgecolors="black",
        linewidths=1.5,
        label="Depot (0)",
        zorder=5,
    )
    ax.annotate(
        "Depot",
        (depot_coord[0], depot_coord[1]),
        textcoords="offset points",
        xytext=(0, 10),
        ha="center",
        fontweight="bold",
        fontsize=9,
        color="#d62728",
        zorder=6,
    )

    # Committed Customer Vertices (in frozen prefix)
    committed_cust = [vertices[i] for i in range(1, frozen_idx_end + 1) if vertices[i] != 0]
    if committed_cust:
        comm_coords = np.array([coords[v] for v in committed_cust])
        ax.scatter(
            comm_coords[:, 0],
            comm_coords[:, 1],
            marker="o",
            c="#2ca02c",
            s=75,
            edgecolors="black",
            linewidths=1.0,
            zorder=4,
        )

    # Uncommitted Customer Vertices
    new_set = set(newly_revealed_vertices or [])
    uncomm_cust = [v for v in vertices if v != 0 and v not in committed_cust and v not in new_set]
    if uncomm_cust:
        uncomm_coords = np.array([coords[v] for v in uncomm_cust])
        ax.scatter(
            uncomm_coords[:, 0],
            uncomm_coords[:, 1],
            marker="o",
            c="#1f77b4",
            s=65,
            edgecolors="black",
            linewidths=0.8,
            label="Uncommitted Customers",
            zorder=4,
        )

    # Newly Revealed Vertices in this step (Highlighted Orange)
    if new_set:
        new_coords = np.array([coords[v] for v in new_set if v < instance.num_vertices])
        if len(new_coords) > 0:
            ax.scatter(
                new_coords[:, 0],
                new_coords[:, 1],
                marker="*",
                c="#ff7f0e",
                s=180,
                edgecolors="black",
                linewidths=1.2,
                label=f"Newly Arrived: {sorted(list(new_set))}",
                zorder=6,
            )

    # 4. Annotations and Layout
    cost_str = f"Cost: {current_route.cost(instance):.2f}"
    if cost_before is not None and cost_after is not None:
        delta = cost_after - cost_before
        sign = "+" if delta >= 0 else ""
        cost_str = f"Cost: {cost_before:.2f} → {cost_after:.2f} (Δ={sign}{delta:.2f})"

    effort_str = f" | Evals: {evals_used}" if evals_used is not None else ""
    strat_str = f" | {strategy_label}" if strategy_label else ""
    full_title = f"{title} (Step {step_number})\n{cost_str}{effort_str}{strat_str}"

    ax.set_title(full_title, fontsize=11, fontweight="bold", pad=12)
    ax.set_xlabel("X Coordinate", fontsize=9)
    ax.set_ylabel("Y Coordinate", fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    plt.tight_layout()

    return fig
