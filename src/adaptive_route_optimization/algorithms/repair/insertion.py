"""Greedy Insertion Repair for Dynamic Events (Strategy A).

Insert new vertices at positions minimizing incremental cost.
References: RESEARCH_SPEC.md (Strategy A), PSEUDOCODE.md (Cheapest-Insertion Repair).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


@dataclass(frozen=True)
class InsertionResult:
    """Result of greedy insertion repair.

    Attributes:
        route: Updated route after all insertions.
        cost: Cost of the updated route.
        candidate_evaluations: Total insertion position evaluations.
        deltas: List of cost deltas for each insertion.
    """
    route: Route
    cost: float
    candidate_evaluations: int
    deltas: list[float]


def cheapest_insertion(
    instance: Instance,
    route: Route,
    new_vertices: Sequence[int],
) -> InsertionResult:
    """Insert new vertices one by one at cheapest positions.

    Args:
        instance: Problem instance.
        route: Current route.
        new_vertices: Sequence of new vertices to insert (processed in order).

    Returns:
        InsertionResult with updated route and statistics.

    Algorithm (per PSEUDOCODE.md):
    - For each new vertex v, evaluate all m insertion positions
    - Position i means inserting between route[i] and route[i+1]
    - Cost delta = c(u, v) + c(v, w) - c(u, w)
    - Deterministic tie-breaking: lowest position index wins
    - Candidate evaluations = m per new vertex
    """
    current_route = route
    total_evals = 0
    deltas = []

    for v in new_vertices:
        m = current_route.num_edges  # Number of insertion positions
        best_delta = float("inf")
        best_pos = -1

        # Evaluate all insertion positions
        for pos in range(m):
            u = current_route.vertices[pos]
            w = current_route.vertices[pos + 1]
            delta = (
                instance.cost(u, v)
                + instance.cost(v, w)
                - instance.cost(u, w)
            )
            total_evals += 1

            if delta < best_delta:
                best_delta = delta
                best_pos = pos + 1  # Insert after position pos

        # Apply best insertion
        current_route = current_route.with_insertion(best_pos - 1, v)
        deltas.append(best_delta)

    return InsertionResult(
        route=current_route,
        cost=current_route.cost(instance),
        candidate_evaluations=total_evals,
        deltas=deltas,
    )


def greedy_insertion_repair(
    instance: Instance,
    route: Route,
    new_vertices: Sequence[int],
) -> InsertionResult:
    """Strategy A: Greedy Insertion Repair.

    Process new vertices in given order (deterministic: sorted by vertex index
    if not already sorted per RESEARCH_SPEC.md Edge Case #4).
    """
    # Ensure deterministic order (vertex index ascending)
    sorted_vertices = sorted(new_vertices)
    return cheapest_insertion(instance, route, sorted_vertices)