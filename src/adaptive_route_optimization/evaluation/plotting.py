"""Route plotting utilities.

Matplotlib-based plotting independent of final UI.
References: RESEARCH_SPEC.md (route plotting independent of final UI)
"""

from __future__ import annotations
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


def plot_route(
    instance: Instance,
    route: Route,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    show_vertex_labels: bool = True,
    depot_color: str = "red",
    customer_color: str = "blue",
    route_color: str = "gray",
    route_alpha: float = 0.7,
    figsize: tuple[float, float] = (8, 8),
) -> plt.Axes:
    """Plot a route on the given or new axes.

    Args:
        instance: Problem instance with coordinates.
        route: Route to plot.
        ax: Existing axes to plot on (creates new if None).
        title: Plot title.
        show_vertex_labels: Whether to show vertex indices.
        depot_color: Color for depot marker.
        customer_color: Color for customer markers.
        route_color: Color for route edges.
        route_alpha: Alpha for route edges.
        figsize: Figure size if creating new figure.

    Returns:
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)

    coords = instance.coords
    vertices = list(route.vertices)

    # Plot edges
    for i in range(len(vertices) - 1):
        u, v = vertices[i], vertices[i + 1]
        x = [coords[u, 0], coords[v, 0]]
        y = [coords[u, 1], coords[v, 1]]
        ax.plot(x, y, color=route_color, alpha=route_alpha, linewidth=1.5, zorder=1)

    # Plot vertices
    # Depot
    ax.scatter(
        coords[0, 0], coords[0, 1],
        c=depot_color, s=150, marker="s", zorder=3,
        edgecolors="black", linewidth=1.5, label="Depot"
    )
    # Customers (non-depot visited)
    if len(vertices) > 2:
        customer_idx = vertices[1:-1]
        ax.scatter(
            coords[customer_idx, 0], coords[customer_idx, 1],
            c=customer_color, s=80, marker="o", zorder=3,
            edgecolors="black", linewidth=0.5, label="Customers"
        )

    # Labels
    if show_vertex_labels:
        for i, (x, y) in enumerate(coords):
            if i == 0:
                label = "D"  # Depot
            elif i in vertices[1:-1]:
                label = str(i)
            else:
                continue  # Don't label unvisited
            ax.annotate(
                label, (x, y),
                xytext=(5, 5), textcoords="offset points",
                fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="none")
            )

    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    if title:
        ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()

    return ax


def plot_route_comparison(
    instance: Instance,
    routes: list[Route],
    labels: Optional[list[str]] = None,
    figsize: tuple[float, float] = (12, 4),
) -> plt.Figure:
    """Plot multiple routes side by side for comparison.

    Args:
        instance: Problem instance.
        routes: List of routes to compare.
        labels: Labels for each subplot.
        figsize: Overall figure size.

    Returns:
        Figure with subplots.
    """
    n = len(routes)
    fig, axes = plt.subplots(1, n, figsize=figsize, squeeze=False)
    axes = axes.flatten()

    for i, route in enumerate(routes):
        label = labels[i] if labels and i < len(labels) else f"Route {i}"
        plot_route(instance, route, ax=axes[i], title=label, show_vertex_labels=True)

    plt.tight_layout()
    return fig


def plot_cost_convergence(
    costs: list[float],
    labels: Optional[list[str]] = None,
    title: str = "Route Cost Convergence",
    figsize: tuple[float, float] = (8, 5),
) -> plt.Figure:
    """Plot route cost over time steps for one or more strategies.

    Args:
        costs: List of cost lists (one per strategy) or single list.
        labels: Labels for each strategy.
        title: Plot title.
        figsize: Figure size.

    Returns:
        Figure with convergence plot.
    """
    fig, ax = plt.subplots(figsize=figsize)

    if costs and isinstance(costs[0], (list, tuple)):
        # Multiple strategies
        for i, c in enumerate(costs):
            label = labels[i] if labels and i < len(labels) else f"Strategy {i}"
            ax.plot(range(len(c)), c, marker="o", label=label, linewidth=2)
        ax.legend()
    else:
        # Single strategy
        ax.plot(range(len(costs)), costs, marker="o", linewidth=2)
        if labels:
            ax.set_title(f"{title}: {labels[0]}")

    ax.set_xlabel("Time Step")
    ax.set_ylabel("Route Cost")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    return fig


def plot_disruption_over_time(
    disruptions: list[float],
    title: str = "Route Disruption Over Time",
    figsize: tuple[float, float] = (8, 5),
) -> plt.Figure:
    """Plot disruption at each time step.

    Args:
        disruptions: List of disruption values per time step.
        title: Plot title.
        figsize: Figure size.

    Returns:
        Figure with disruption plot.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(range(len(disruptions)), disruptions, marker="s", color="orange", linewidth=2)
    ax.set_xlabel("Time Step")
    ax.set_ylabel("Disruption δ")
    ax.set_title(title)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    return fig