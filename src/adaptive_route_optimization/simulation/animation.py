"""Animated Route-State Prototype for Debugging.

Creates matplotlib animations showing route evolution over time steps.
For debugging/visualization only - not part of final UI.
References: PHASE_PLAN.md (Phase 5: animated route-state prototype).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for testing
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.simulation.simulator import SimulationResult, StepResult


@dataclass
class AnimationConfig:
    """Configuration for route animation."""
    figsize: tuple[float, float] = (10, 8)
    dpi: int = 100
    depot_color: str = "red"
    depot_size: int = 150
    customer_color: str = "blue"
    customer_size: int = 60
    new_vertex_color: str = "orange"
    new_vertex_size: int = 80
    frozen_color: str = "green"
    frozen_size: int = 80
    route_color: str = "gray"
    route_alpha: float = 0.7
    route_width: float = 2.0
    frozen_route_color: str = "green"
    frozen_route_width: float = 3.0
    show_vertex_labels: bool = True
    show_cost: bool = True
    show_disruption: bool = True
    interval: int = 1000  # ms between frames


def animate_route_state(
    instance: Instance,
    simulation_result: SimulationResult,
    config: Optional[AnimationConfig] = None,
    save_path: Optional[str] = None,
    show: bool = False,
) -> animation.FuncAnimation:
    """Create animation of route evolution during simulation.

    Args:
        instance: Problem instance with vertex coordinates.
        simulation_result: Complete simulation result with all steps.
        config: Animation configuration (optional).
        save_path: Path to save animation (GIF/MP4). If None, not saved.
        show: Whether to display animation (requires interactive backend).

    Returns:
        FuncAnimation object (can be saved or displayed).
    """
    config = config or AnimationConfig()

    # Get all routes at each time step
    routes = []
    disruptions = []
    costs = []
    event_vertices_list = []
    frozen_lengths = []

    # Initial state (t=0)
    routes.append(simulation_result.initial_state.current_route)
    disruptions.append(0.0)
    costs.append(simulation_result.initial_state.current_route.cost(instance))
    event_vertices_list.append(frozenset())
    frozen_lengths.append(simulation_result.initial_state.frozen_prefix_length)

    # Each event step
    for step in simulation_result.steps:
        routes.append(step.updated_route)
        disruptions.append(step.metrics.disruption)
        costs.append(step.metrics.route_cost)
        event_vertices_list.append(step.event_vertices)
        # Frozen prefix advances by 1 per step (default)
        frozen_lengths.append(
            simulation_result.initial_state.frozen_prefix_length + step.time_step
        )

    # Set up figure
    fig, ax = plt.subplots(figsize=config.figsize, dpi=config.dpi)
    coords = instance.coords

    # Get coordinate bounds for consistent axis limits
    x_coords = coords[:, 0]
    y_coords = coords[:, 1]
    x_margin = (x_coords.max() - x_coords.min()) * 0.1 + 1
    y_margin = (y_coords.max() - y_coords.min()) * 0.1 + 1
    ax.set_xlim(x_coords.min() - x_margin, x_coords.max() + x_margin)
    ax.set_ylim(y_coords.min() - y_margin, y_coords.max() + y_margin)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    # Plot all vertices (static background)
    # Depot
    ax.scatter(
        coords[0, 0], coords[0, 1],
        c=config.depot_color, s=config.depot_size,
        marker="s", zorder=10, label="Depot (0)",
        edgecolors="black", linewidth=1.5
    )

    # All customers (will be colored differently based on state)
    customer_indices = list(range(1, instance.num_vertices))
    ax.scatter(
        coords[customer_indices, 0], coords[customer_indices, 1],
        c=config.customer_color, s=config.customer_size,
        marker="o", zorder=5, label="Customers",
        edgecolors="black", linewidth=0.5
    )

    # Vertex labels
    if config.show_vertex_labels:
        for v in range(instance.num_vertices):
            ax.annotate(
                str(v), (coords[v, 0], coords[v, 1]),
                textcoords="offset points", xytext=(5, 5),
                fontsize=9, fontweight="bold"
            )

    # Route line (will be updated per frame)
    route_line, = ax.plot([], [], color=config.route_color,
                           alpha=config.route_alpha, linewidth=config.route_width,
                           zorder=3, label="Current Route")

    # Frozen prefix line
    frozen_line, = ax.plot([], [], color=config.frozen_route_color,
                            linewidth=config.frozen_route_width,
                            zorder=4, label="Frozen Prefix")

    # Highlighted new vertices
    new_vertices_scatter = ax.scatter(
        [], [], c=config.new_vertex_color, s=config.new_vertex_size,
        marker="o", zorder=8, label="New Vertex",
        edgecolors="black", linewidth=1.5
    )

    # Frozen prefix vertices
    frozen_vertices_scatter = ax.scatter(
        [], [], c=config.frozen_color, s=config.frozen_size,
        marker="s", zorder=7, label="Frozen",
        edgecolors="black", linewidth=1.5
    )

    # Title and info text
    title = ax.set_title("")
    info_text = ax.text(0.02, 0.98, "", transform=ax.transAxes,
                         verticalalignment="top", fontsize=10,
                         bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

    ax.legend(loc="upper right", fontsize=9)

    def init():
        """Initialize animation."""
        route_line.set_data([], [])
        frozen_line.set_data([], [])
        new_vertices_scatter.set_offsets(np.empty((0, 2)))
        frozen_vertices_scatter.set_offsets(np.empty((0, 2)))
        title.set_text("")
        info_text.set_text("")
        return route_line, frozen_line, new_vertices_scatter, frozen_vertices_scatter, title, info_text

    def update(frame):
        """Update animation for each frame."""
        route = routes[frame]
        vertices = route.vertices
        frozen_len = frozen_lengths[frame]
        event_verts = event_vertices_list[frame]

        # Route coordinates
        route_coords = coords[list(vertices)]
        route_line.set_data(route_coords[:, 0], route_coords[:, 1])

        # Frozen prefix coordinates
        if frozen_len > 0:
            frozen_verts = vertices[:frozen_len + 1]  # +1 because frozen_len is count of frozen customers
            frozen_coords = coords[list(frozen_verts)]
            frozen_line.set_data(frozen_coords[:, 0], frozen_coords[:, 1])
        else:
            frozen_line.set_data([], [])

        # New vertices at this step
        if event_verts:
            new_coords = coords[list(event_verts)]
            new_vertices_scatter.set_offsets(new_coords)
        else:
            new_vertices_scatter.set_offsets(np.empty((0, 2)))

        # Frozen vertices (excluding depot which is always frozen)
        if frozen_len > 0:
            frozen_cust = [v for v in vertices[1:frozen_len + 1] if v != 0]
            if frozen_cust:
                frozen_coords = coords[frozen_cust]
                frozen_vertices_scatter.set_offsets(frozen_coords)
            else:
                frozen_vertices_scatter.set_offsets(np.empty((0, 2)))
        else:
            frozen_vertices_scatter.set_offsets(np.empty((0, 2)))

        # Update title and info
        strategy_name = "Greedy Insertion (A)" if simulation_result.strategy.value == "A" else "Insertion + 2-opt (B)"
        title.set_text(f"Dynamic Routing Simulation - {strategy_name} - Step {frame}/{len(routes)-1}")

        info_lines = [
            f"Step: {frame}",
            f"Route Cost: {costs[frame]:.2f}",
            f"Vertices Known: {len(set().union(*[set(r.vertices) for r in routes[:frame+1]])) - 1}",  # exclude depot
            f"Frozen Prefix: {frozen_len} vertices",
        ]
        if frame > 0:
            info_lines.append(f"Disruption: {disruptions[frame]:.3f}")
        if event_verts:
            info_lines.append(f"New Vertex: {sorted(event_verts)}")
        info_text.set_text("\n".join(info_lines))

        return route_line, frozen_line, new_vertices_scatter, frozen_vertices_scatter, title, info_text

    # Create animation
    anim = animation.FuncAnimation(
        fig, update, frames=len(routes),
        init_func=init, blit=True, interval=config.interval, repeat=True
    )

    # Save if requested
    if save_path:
        if save_path.endswith(".gif"):
            anim.save(save_path, writer="pillow", fps=1000//config.interval)
        elif save_path.endswith(".mp4"):
            anim.save(save_path, writer="ffmpeg", fps=1000//config.interval)
        else:
            raise ValueError("save_path must end with .gif or .mp4")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return anim


def plot_route_evolution(
    instance: Instance,
    simulation_result: SimulationResult,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Create a static plot showing route evolution (all steps overlaid).

    Useful for quick visualization without animation.
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Left: Final route with all vertices
    ax1 = axes[0]
    coords = instance.coords

    # Plot all vertices
    ax1.scatter(coords[0, 0], coords[0, 1], c="red", s=150, marker="s",
                zorder=10, label="Depot", edgecolors="black", linewidth=1.5)
    ax1.scatter(coords[1:, 0], coords[1:, 1], c="blue", s=60, marker="o",
                zorder=5, label="Customers", edgecolors="black", linewidth=0.5)

    # Final route
    final_route = simulation_result.final_route
    route_coords = coords[list(final_route.vertices)]
    ax1.plot(route_coords[:, 0], route_coords[:, 1], "k-", alpha=0.7, linewidth=2, label="Final Route")

    # Frozen prefix at end
    if simulation_result.steps:
        final_frozen = simulation_result.initial_state.frozen_prefix_length + len(simulation_result.steps)
        frozen_verts = final_route.vertices[:final_frozen + 1]
        frozen_coords = coords[list(frozen_verts)]
        ax1.plot(frozen_coords[:, 0], frozen_coords[:, 1], "g-", linewidth=3, label="Frozen Prefix")

    ax1.set_title(f"Final Route (Cost: {simulation_result.final_metrics.route_cost:.2f})")
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Right: Cost and disruption over time
    ax2 = axes[1]
    
    # Extract costs and disruptions from simulation result
    costs = [simulation_result.initial_state.current_route.cost(instance)]
    disruptions = [0.0]
    for step in simulation_result.steps:
        costs.append(step.metrics.route_cost)
        disruptions.append(step.metrics.disruption)
    
    steps = list(range(len(simulation_result.steps) + 1))
    ax2.plot(steps, costs, "b-o", label="Route Cost")
    ax2.set_xlabel("Time Step")
    ax2.set_ylabel("Route Cost", color="b")
    ax2.tick_params(axis="y", labelcolor="b")

    ax2_twin = ax2.twinx()
    ax2_twin.plot(steps, disruptions, "r-s", label="Disruption")
    ax2_twin.set_ylabel("Disruption", color="r")
    ax2_twin.tick_params(axis="y", labelcolor="r")

    ax2.set_title("Cost and Disruption Over Time")
    ax2.grid(True, alpha=0.3)

    # Combine legends
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.close(fig)

    return fig


def create_animation_from_log(
    instance: Instance,
    log,  # SimulationLog from logging module
    config: Optional[AnimationConfig] = None,
    save_path: Optional[str] = None,
) -> animation.FuncAnimation:
    """Create animation from a SimulationLog (without full SimulationResult).

    Reconstructs minimal route sequence from log entries.
    """
    # Reconstruct routes from log
    routes = []
    disruptions = []
    costs = []
    event_vertices_list = []
    frozen_lengths = []

    for entry in log.entries:
        routes.append(Route(tuple(entry.updated_route)) if entry.updated_route else Route(tuple(entry.previous_route)))
        disruptions.append(entry.metrics["disruption"])
        costs.append(entry.metrics["route_cost"])
        event_vertices_list.append(frozenset(entry.event_vertices))
        frozen_lengths.append(entry.frozen_prefix_length)

    # Create a minimal SimulationResult-like object for the animation
    class MinimalResult:
        def __init__(self):
            self.initial_state = type("State", (), {
                "current_route": routes[0],
                "frozen_prefix_length": frozen_lengths[0],
            })()
            self.strategy = type("Strategy", (), {"value": log.strategy})()
            self.steps = []
            self.final_route = routes[-1]
            self.final_metrics = type("Metrics", (), {
                "route_cost": costs[-1],
            })()

    result = MinimalResult()
    return animate_route_state(instance, result, config, save_path)