"""Nearest Neighbor baseline construction algorithm.

Deterministic greedy construction: start at depot, repeatedly visit nearest unvisited vertex.
Tie-breaking: lowest vertex index wins.
References: RESEARCH_SPEC.md (Initial Solution), PSEUDOCODE.md (Nearest-Neighbor Construction)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


@dataclass(frozen=True)
class NNResult:
    """Result of nearest-neighbor construction.

    Attributes:
        route: Constructed route.
        candidate_evaluations: Number of cost evaluations performed.
    """
    route: Route
    candidate_evaluations: int


def nearest_neighbor(
    instance: Instance,
    vertex_subset: Optional[set[int]] = None,
) -> NNResult:
    """Construct a route using the Nearest Neighbor heuristic.

    Starts at depot (0), repeatedly visits nearest unvisited vertex.
    Deterministic tie-breaking: lowest vertex index wins.

    Args:
        instance: Problem instance.
        vertex_subset: Optional set of vertices to include. Must include 0 (depot).
                       If None, uses all vertices in instance.

    Returns:
        NNResult with constructed route and candidate evaluation count.

    Time complexity: O(n^2) where n = number of vertices in subset.
    Space complexity: O(n).
    Candidate evaluations: n(n+1)/2 for n non-depot vertices.
    """
    if vertex_subset is None:
        vertex_subset = set(range(instance.num_vertices))

    if 0 not in vertex_subset:
        raise ValueError("Depot (0) must be in vertex_subset")

    # Non-depot vertices to visit
    unvisited = {v for v in vertex_subset if v != 0}
    route_vertices = [0]
    current = 0
    evals = 0

    while unvisited:
        best_vertex = min(
            unvisited,
            key=lambda v: (instance.cost(current, v), v)  # tie-break by index
        )
        # Count candidate evaluations: we evaluated all unvisited vertices
        evals += len(unvisited)
        route_vertices.append(best_vertex)
        unvisited.remove(best_vertex)
        current = best_vertex

    # Return to depot
    route_vertices.append(0)

    return NNResult(
        route=Route(tuple(route_vertices)),
        candidate_evaluations=evals,
    )


def nearest_neighbor_from_coords(
    coords: list[tuple[float, float]],
    vertex_subset: Optional[set[int]] = None,
) -> NNResult:
    """Convenience function to run NN from coordinate list."""
    instance = Instance.from_coords(coords)
    return nearest_neighbor(instance, vertex_subset)