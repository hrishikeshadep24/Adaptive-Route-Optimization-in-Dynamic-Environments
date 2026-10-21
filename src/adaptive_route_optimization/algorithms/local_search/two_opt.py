"""2-opt Local Search for TSP.

First-improvement strategy with deterministic tie-breaking.
References: RESEARCH_SPEC.md (Strategy B), PSEUDOCODE.md (2-opt Local Search),
OPEN_QUESTIONS.md (Questions 21-23).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


# Numerical stability threshold for 2-opt (OPEN_QUESTIONS.md #23)
EPS = 1e-9


@dataclass(frozen=True)
class TwoOptResult:
    """Result of 2-opt local search.

    Attributes:
        route: Locally optimal route.
        cost: Cost of the final route.
        candidate_evaluations: Total candidate evaluations (pairs examined).
        accepted_moves: Number of improving moves applied.
        passes: Number of full passes until convergence.
    """
    route: Route
    cost: float
    candidate_evaluations: int
    accepted_moves: int
    passes: int


def two_opt(
    instance: Instance,
    route: Route,
    max_passes: Optional[int] = None,
    max_evaluations: Optional[int] = None,
    min_i: int = 0,
) -> TwoOptResult:
    """Run 2-opt local search to local optimum (first-improvement).

    Args:
        instance: Problem instance.
        route: Initial route.
        max_passes: Optional limit on number of passes (for budget control).
        max_evaluations: Optional limit on candidate evaluations (for budget control).
        min_i: Minimum starting index for edge pair scan (default 0).
               When min_i > 0, edges before index min_i are preserved,
               allowing suffix-only local search under the frozen-prefix rule.

    Returns:
        TwoOptResult with optimized route and statistics.

    Algorithm (per PSEUDOCODE.md and OPEN_QUESTIONS.md #21-22):
    - First-improvement: apply first improving move found, restart scan
    - Deterministic tie-breaking: earliest (i, j) in lexicographic order
    - Numerical stability: only apply if delta < -EPS (EPS=1e-9)
    - Candidate evaluation = one delta computation per pair examined
    """
    current_route = route
    current_cost = route.cost(instance)

    total_evals = 0
    accepted_moves = 0
    passes = 0

    # Maximum passes if not specified: unbounded (run to local optimum)
    # Per OPEN_QUESTIONS.md #24: run to local optimum by default
    while True:
        if max_passes is not None and passes >= max_passes:
            break

        passes += 1
        improved = False
        n_edges = current_route.num_edges
        vertices = list(current_route.vertices)

        # Scan all non-adjacent edge pairs in lexicographic order (i, j)
        # i from min_i to n-3, j from i+2 to n-1 (wrapping handled by depot)
        for i in range(min_i, n_edges - 2):
            for j in range(i + 2, n_edges):
                # Skip if this involves depot-depot (first and last edge both incident to depot)
                if i == 0 and j == n_edges - 1:
                    continue

                # Edges are (a, b) and (c, d) where:
                # a = vertices[i], b = vertices[i+1]
                # c = vertices[j], d = vertices[(j+1) % n_edges]
                a, b = vertices[i], vertices[i + 1]
                c, d = vertices[j], vertices[(j + 1) % n_edges]

                # Compute delta = c(a,c) + c(b,d) - c(a,b) - c(c,d)
                delta = (
                    instance.cost(a, c)
                    + instance.cost(b, d)
                    - instance.cost(a, b)
                    - instance.cost(c, d)
                )
                total_evals += 1

                if max_evaluations is not None and total_evals >= max_evaluations:
                    # Budget exhausted
                    return TwoOptResult(
                        route=current_route,
                        cost=current_cost,
                        candidate_evaluations=total_evals,
                        accepted_moves=accepted_moves,
                        passes=passes - 1,  # Current pass didn't complete
                    )

                # Check for improving move (first-improvement)
                if delta < -EPS:
                    # Apply 2-opt: reverse segment from i+1 to j
                    new_vertices = vertices[:]
                    new_vertices[i + 1 : j + 1] = reversed(new_vertices[i + 1 : j + 1])
                    current_route = Route(tuple(new_vertices))
                    current_cost += delta
                    accepted_moves += 1
                    improved = True
                    break  # Restart scan (first-improvement)

            if improved:
                break

        if not improved:
            # Local optimum reached
            break

    return TwoOptResult(
        route=current_route,
        cost=current_cost,
        candidate_evaluations=total_evals,
        accepted_moves=accepted_moves,
        passes=passes,
    )


def two_opt_from_route(route: Route, instance: Instance) -> TwoOptResult:
    """Convenience wrapper with defaults (run to local optimum)."""
    return two_opt(instance, route)


# --- Batch 2-opt for multiple routes (for benchmarking) ---

def two_opt_batch(
    instance: Instance,
    routes: list[Route],
    max_passes: Optional[int] = None,
    max_evaluations: Optional[int] = None,
) -> list[TwoOptResult]:
    """Apply 2-opt to multiple routes independently."""
    return [two_opt(instance, r, max_passes, max_evaluations) for r in routes]