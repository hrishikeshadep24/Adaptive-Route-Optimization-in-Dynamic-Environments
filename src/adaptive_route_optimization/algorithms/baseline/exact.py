"""Exact solver for small TSP instances (n <= 8).

Brute-force enumeration of all permutations to find optimal route.
Used ONLY for verification of heuristics on tiny instances.
References: RESEARCH_SPEC.md (simple exact solver for very small instances)
"""

from __future__ import annotations
from dataclasses import dataclass
from itertools import permutations
from typing import Optional

import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


@dataclass(frozen=True)
class ExactResult:
    """Result of exact TSP solve.

    Attributes:
        route: Optimal route.
        cost: Optimal cost.
        candidate_evaluations: Number of cost evaluations (permutations checked).
    """
    route: Route
    cost: float
    candidate_evaluations: int


def exact_tsp(
    instance: Instance,
    vertex_subset: Optional[set[int]] = None,
    max_vertices: int = 8,
) -> ExactResult:
    """Find exact optimal route for TSP by brute-force enumeration.

    Only works for small instances (n <= max_vertices non-depot vertices).
    Enumerates all permutations of non-depot vertices.

    Args:
        instance: Problem instance.
        vertex_subset: Optional set of vertices to include. Must include 0.
                       If None, uses all vertices in instance.
        max_vertices: Maximum number of non-depot vertices allowed (default 8).

    Returns:
        ExactResult with optimal route, cost, and evaluation count.

    Raises:
        ValueError: If number of non-depot vertices exceeds max_vertices.
    """
    if vertex_subset is None:
        vertex_subset = set(range(instance.num_vertices))

    if 0 not in vertex_subset:
        raise ValueError("Depot (0) must be in vertex_subset")

    customers = [v for v in vertex_subset if v != 0]
    n = len(customers)

    if n > max_vertices:
        raise ValueError(
            f"Exact solver limited to {max_vertices} non-depot vertices, got {n}. "
            f"Use a heuristic for larger instances."
        )

    if n == 0:
        # Only depot
        return ExactResult(
            route=Route((0, 0)),
            cost=0.0,
            candidate_evaluations=0,
        )

    best_cost = float("inf")
    best_perm = None
    evals = 0

    # Precompute cost matrix for subset for speed
    # Map local index -> global vertex index
    idx_to_vertex = [0] + customers

    # Enumerate all permutations of customers
    for perm in permutations(customers):
        # Build route: 0 -> perm -> 0
        route_vertices = (0,) + perm + (0,)
        route = Route(route_vertices)

        cost = route.cost(instance)
        evals += 1

        if cost < best_cost:
            best_cost = cost
            best_perm = perm

    optimal_route = Route((0,) + best_perm + (0,))

    return ExactResult(
        route=optimal_route,
        cost=best_cost,
        candidate_evaluations=evals,
    )


def exact_tsp_from_coords(
    coords: list[tuple[float, float]],
    vertex_subset: Optional[set[int]] = None,
    max_vertices: int = 8,
) -> ExactResult:
    """Convenience function to run exact TSP from coordinate list."""
    instance = Instance.from_coords(coords)
    return exact_tsp(instance, vertex_subset, max_vertices)