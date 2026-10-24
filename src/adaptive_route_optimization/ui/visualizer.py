"""Interactive 2D Spatial Route Visualizer for Dashboard.

Renders high-clarity 2D Euclidean route diagrams highlighting:
- Red square: Depot (0) [Start and finish]
- Green solid line & circles: Traversed prefix (already visited & frozen; immutable)
- Blue dashed line & circles: Uncommitted suffix (planned remaining route; re-optimized)
- Vehicle position ring: Current vehicle location along the route
- Orange star: Newly revealed dynamic customer vertices (Δ_t)
- Faint grey dots: Future unrevealed arrivals (hidden from algorithm unless ground truth enabled)
"""

from __future__ import annotations
from typing import Optional, Sequence
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


def _draw_route_on_axis(
    ax: plt.Axes,
    instance: Instance,
    route: Route,
    frozen_prefix_length: int,
    newly_revealed_vertices: Optional[Sequence[int]] = None,
    show_unrevealed: bool = False,
    is_before_state: bool = False,
    min_x: float = 0.0,
    max_x: float = 1.0,
    min_y: float = 0.0,
    max_y: float = 1.0,
) -> None:
    """Helper to draw a single route diagram with consistent styling and legend."""
    coords = instance.coords
    vertices = route.vertices
    n_vertices = len(vertices)
    new_set = set(newly_revealed_vertices or [])
    all_verts = set(range(instance.num_vertices))

    # 1. Unrevealed Background Customers (ONLY if explicitly toggled)
    known_set = set(vertices) | new_set
    unrevealed = all_verts - known_set
    if show_unrevealed and unrevealed:
        unrev_coords = np.array([coords[v] for v in unrevealed])
        ax.scatter(
            unrev_coords[:, 0],
            unrev_coords[:, 1],
            c="#b0b0b0",
            s=40,
            alpha=0.5,
            edgecolors="#707070",
            linewidths=0.6,
            label="Future Arrivals (Hidden from Algorithm)",
            zorder=2,
        )

    # 2. Frozen Prefix & Uncommitted Suffix Edges
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
            linewidth=3.2,
            label=f"Traversed Prefix (Frozen: {frozen_prefix_length} stops)",
            zorder=3,
        )
    else:
        # Include legend entry so the user understands why 0 edges are green at step 1
        ax.plot(
            [],
            [],
            "-",
            color="#2ca02c",
            linewidth=3.2,
            label="Traversed Prefix (0 stops; at depot)",
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
            linewidth=2.2,
            alpha=0.9,
            label="Planned Suffix (Uncommitted: can repair)",
            zorder=3,
        )

    # 3. Vertices by Role
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
        label="Depot (0) [Start/End]",
        zorder=5,
    )
    ax.annotate(
        "Depot",
        (depot_coord[0], depot_coord[1]),
        textcoords="offset points",
        xytext=(0, 9),
        ha="center",
        fontweight="bold",
        fontsize=8.5,
        color="#d62728",
        zorder=6,
    )

    # Visited Customer Vertices (in frozen prefix)
    committed_cust = [vertices[i] for i in range(1, frozen_idx_end + 1) if vertices[i] != 0]
    if committed_cust:
        comm_coords = np.array([coords[v] for v in committed_cust])
        ax.scatter(
            comm_coords[:, 0],
            comm_coords[:, 1],
            marker="o",
            c="#2ca02c",
            s=80,
            edgecolors="black",
            linewidths=1.0,
            label=f"Visited Customers ({len(committed_cust)})",
            zorder=4,
        )

    # Vehicle Current Position Indicator
    veh_v = vertices[frozen_idx_end]
    veh_coord = coords[veh_v]
    veh_label = f"Vehicle Position (Stop {frozen_prefix_length}: V{veh_v})" if frozen_idx_end > 0 else "Vehicle Position (At Depot)"
    ax.scatter(
        [veh_coord[0]],
        [veh_coord[1]],
        marker="o",
        s=190,
        facecolors="none",
        edgecolors="#006400",
        linewidths=2.6,
        label=veh_label,
        zorder=6,
    )

    # Uncommitted Customer Vertices
    uncomm_cust = [v for v in vertices if v != 0 and v not in committed_cust and v not in new_set]
    if uncomm_cust:
        uncomm_coords = np.array([coords[v] for v in uncomm_cust])
        ax.scatter(
            uncomm_coords[:, 0],
            uncomm_coords[:, 1],
            marker="o",
            c="#1f77b4",
            s=70,
            edgecolors="black",
            linewidths=0.9,
            label=f"Planned Customers ({len(uncomm_cust)})",
            zorder=4,
        )

    # Newly Arrived Dynamic Customer (Orange Star)
    if new_set:
        new_coords = np.array([coords[v] for v in new_set if v < instance.num_vertices])
        if len(new_coords) > 0:
            status_desc = "Pending" if is_before_state else "Integrated"
            ax.scatter(
                new_coords[:, 0],
                new_coords[:, 1],
                marker="*",
                c="#ff7f0e",
                s=220,
                edgecolors="black",
                linewidths=1.4,
                label=f"New Arrival Δ: {sorted(list(new_set))} ({status_desc})",
                zorder=7,
            )
            for v in new_set:
                if v < instance.num_vertices:
                    vx, vy = coords[v]
                    ax.annotate(
                        f"Customer {v}",
                        (vx, vy),
                        textcoords="offset points",
                        xytext=(0, 11),
                        ha="center",
                        fontsize=8,
                        fontweight="bold",
                        color="#d95f02",
                        zorder=8,
                    )

    # Set Coordinate Limits & Grid
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_xlabel("X Coordinate (Euclidean)", fontsize=8.5)
    ax.set_ylabel("Y Coordinate (Euclidean)", fontsize=8.5)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=7.5, framealpha=0.92)


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
    figsize: tuple[float, float] = (8.0, 6.2),
    show_unrevealed: bool = False,
    is_before_state: bool = False,
) -> plt.Figure:
    """Render a publication-quality 2D tour visualization for a dynamic step."""
    fig, ax = plt.subplots(figsize=figsize, dpi=120)
    coords = instance.coords

    # Stable bounds with 8% padding
    min_x, max_x = coords[:, 0].min(), coords[:, 0].max()
    min_y, max_y = coords[:, 1].min(), coords[:, 1].max()
    pad_x = max(0.05, (max_x - min_x) * 0.08)
    pad_y = max(0.05, (max_y - min_y) * 0.08)

    _draw_route_on_axis(
        ax=ax,
        instance=instance,
        route=current_route,
        frozen_prefix_length=frozen_prefix_length,
        newly_revealed_vertices=newly_revealed_vertices,
        show_unrevealed=show_unrevealed,
        is_before_state=is_before_state,
        min_x=min_x - pad_x,
        max_x=max_x + pad_x,
        min_y=min_y - pad_y,
        max_y=max_y + pad_y,
    )

    cost_val = current_route.cost(instance)
    cost_str = f"Route Cost: {cost_val:.2f}"
    if cost_before is not None and cost_after is not None:
        delta = cost_after - cost_before
        sign = "+" if delta >= 0 else ""
        cost_str = f"Cost: {cost_before:.2f} → {cost_after:.2f} (Δ={sign}{delta:.2f})"

    effort_str = f" | Evals: {evals_used:,}" if evals_used is not None else ""
    strat_str = f" | {strategy_label}" if strategy_label else ""
    full_title = f"{title} (Step {step_number})\n{cost_str}{effort_str}{strat_str}"

    ax.set_title(full_title, fontsize=11, fontweight="bold", pad=12)

    # Footnote explaining Euclidean metric space
    ax.text(
        0.5,
        -0.12,
        "Euclidean metric space: straight edges represent geometric distance, not street or road network travel.",
        ha="center",
        va="top",
        fontsize=7.5,
        color="#666666",
        style="italic",
        transform=ax.transAxes,
    )

    plt.tight_layout()
    return fig


def render_before_after_comparison(
    instance: Instance,
    route_before: Route,
    route_after: Route,
    frozen_prefix_length: int,
    newly_revealed_vertices: Sequence[int],
    cost_before: float,
    cost_after: float,
    evals_used: int,
    strategy_label: str,
    step_number: int,
    show_unrevealed: bool = False,
    figsize: tuple[float, float] = (14.0, 5.8),
) -> plt.Figure:
    """Render a side-by-side Before vs. After comparison for a single dynamic event step.

    Left Panel: State BEFORE repair (route S_{t-1}, new customer highlighted as incoming).
    Right Panel: State AFTER repair (route S_t updated by chosen strategy, new customer integrated).
    """
    fig, (ax_before, ax_after) = plt.subplots(1, 2, figsize=figsize, dpi=120)
    coords = instance.coords

    # Stable coordinate bounds for both panels
    min_x, max_x = coords[:, 0].min(), coords[:, 0].max()
    min_y, max_y = coords[:, 1].min(), coords[:, 1].max()
    pad_x = max(0.05, (max_x - min_x) * 0.08)
    pad_y = max(0.05, (max_y - min_y) * 0.08)

    # 1. Left: Before Repair
    _draw_route_on_axis(
        ax=ax_before,
        instance=instance,
        route=route_before,
        frozen_prefix_length=frozen_prefix_length,
        newly_revealed_vertices=newly_revealed_vertices,
        show_unrevealed=show_unrevealed,
        is_before_state=True,
        min_x=min_x - pad_x,
        max_x=max_x + pad_x,
        min_y=min_y - pad_y,
        max_y=max_y + pad_y,
    )
    ax_before.set_title(
        f"1. BEFORE REPAIR (Event Step t={step_number})\n"
        f"Incoming Customer Arrived (Pending) | Cost: {cost_before:.2f}",
        fontsize=10.5,
        fontweight="bold",
        pad=10,
    )

    # 2. Right: After Repair
    _draw_route_on_axis(
        ax=ax_after,
        instance=instance,
        route=route_after,
        frozen_prefix_length=frozen_prefix_length,
        newly_revealed_vertices=newly_revealed_vertices,
        show_unrevealed=show_unrevealed,
        is_before_state=False,
        min_x=min_x - pad_x,
        max_x=max_x + pad_x,
        min_y=min_y - pad_y,
        max_y=max_y + pad_y,
    )
    delta = cost_after - cost_before
    sign = "+" if delta >= 0 else ""
    ax_after.set_title(
        f"2. AFTER REPAIR ({strategy_label})\n"
        f"Customer Integrated into Suffix | Cost: {cost_after:.2f} (Δ={sign}{delta:.2f}) | Evals: {evals_used:,}",
        fontsize=10.5,
        fontweight="bold",
        pad=10,
    )

    fig.suptitle(
        f"Dynamic Update Transition at Step {step_number} | Strategy: {strategy_label}",
        fontsize=12,
        fontweight="bold",
        y=1.02,
    )

    plt.tight_layout()
    return fig


def render_strategy_comparison(
    instance: Instance,
    route_a: Route,
    route_b: Route,
    frozen_prefix_length: int,
    newly_revealed_vertices: Sequence[int],
    cost_a: float,
    cost_b: float,
    evals_a: int,
    evals_b: int,
    disruption_a: float,
    disruption_b: float,
    step_number: int,
    show_unrevealed: bool = False,
    figsize: tuple[float, float] = (14.0, 5.8),
    label_a: str = "Strategy A (Greedy Insertion)",
    label_b: str = "Strategy B (Insertion + 2-opt)",
) -> plt.Figure:
    """Render a side-by-side comparison of two strategies for the same step.

    Left Panel: Strategy A / First Strategy route, cost, evals, disruption.
    Right Panel: Strategy B / Second Strategy route, cost, evals, disruption.
    Both share identical coordinates, arrival sequence, and event step.
    """
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=figsize, dpi=120)
    coords = instance.coords

    min_x, max_x = coords[:, 0].min(), coords[:, 0].max()
    min_y, max_y = coords[:, 1].min(), coords[:, 1].max()
    pad_x = max(0.05, (max_x - min_x) * 0.08)
    pad_y = max(0.05, (max_y - min_y) * 0.08)

    # 1. Left: Strategy A / First Strategy
    _draw_route_on_axis(
        ax=ax_a,
        instance=instance,
        route=route_a,
        frozen_prefix_length=frozen_prefix_length,
        newly_revealed_vertices=newly_revealed_vertices,
        show_unrevealed=show_unrevealed,
        is_before_state=False,
        min_x=min_x - pad_x,
        max_x=max_x + pad_x,
        min_y=min_y - pad_y,
        max_y=max_y + pad_y,
    )
    ax_a.set_title(
        f"{label_a}\n"
        f"Cost: {cost_a:.2f} | Evals: {evals_a:,} | Disruption δ: {disruption_a:.4f}",
        fontsize=10.5,
        fontweight="bold",
        pad=10,
    )

    # 2. Right: Strategy B / Second Strategy
    _draw_route_on_axis(
        ax=ax_b,
        instance=instance,
        route=route_b,
        frozen_prefix_length=frozen_prefix_length,
        newly_revealed_vertices=newly_revealed_vertices,
        show_unrevealed=show_unrevealed,
        is_before_state=False,
        min_x=min_x - pad_x,
        max_x=max_x + pad_x,
        min_y=min_y - pad_y,
        max_y=max_y + pad_y,
    )
    diff_cost = cost_b - cost_a
    diff_sign = "+" if diff_cost >= 0 else ""
    ax_b.set_title(
        f"{label_b}\n"
        f"Cost: {cost_b:.2f} ({diff_sign}{diff_cost:.2f} vs Left) | Evals: {evals_b:,} | Disruption δ: {disruption_b:.4f}",
        fontsize=10.5,
        fontweight="bold",
        pad=10,
    )

    fig.suptitle(
        f"Strategy Head-to-Head Comparison: Step {step_number} (Same Scenario & Arrivals)",
        fontsize=12,
        fontweight="bold",
        y=1.02,
    )

    plt.tight_layout()
    return fig
