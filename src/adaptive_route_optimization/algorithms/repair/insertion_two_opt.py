"""Insertion + 2-opt Repair for Dynamic Events (Strategy B).

Apply greedy insertion then run 2-opt local search to local optimum.
References: RESEARCH_SPEC.md (Strategy B), PSEUDOCODE.md (Update_LOCAL_SEARCH).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.algorithms.repair.insertion import (
    cheapest_insertion,
    greedy_insertion_repair,
    InsertionResult,
)
from adaptive_route_optimization.algorithms.local_search.two_opt import (
    two_opt,
    TwoOptResult,
)


@dataclass(frozen=True)
class InsertionTwoOptResult:
    """Result of insertion + 2-opt repair.

    Attributes:
        route: Final route after insertion and 2-opt.
        cost: Cost of the final route.
        insertion_evaluations: Candidate evaluations during insertion phase.
        two_opt_evaluations: Candidate evaluations during 2-opt phase.
        total_evaluations: Total candidate evaluations.
        insertion_deltas: Cost deltas from insertion phase.
        two_opt_accepted_moves: Number of improving 2-opt moves applied.
        two_opt_passes: Number of 2-opt passes until convergence.
    """
    route: Route
    cost: float
    insertion_evaluations: int
    two_opt_evaluations: int
    total_evaluations: int
    insertion_deltas: list[float]
    two_opt_accepted_moves: int
    two_opt_passes: int


def insertion_then_two_opt(
    instance: Instance,
    route: Route,
    new_vertices: Sequence[int],
    max_passes: Optional[int] = None,
    max_evaluations: Optional[int] = None,
) -> InsertionTwoOptResult:
    """Strategy B: Insertion + 2-opt Repair.

    Args:
        instance: Problem instance.
        route: Current route.
        new_vertices: New vertices to insert (processed in vertex-index order).
        max_passes: Optional limit on 2-opt passes.
        max_evaluations: Optional limit on total candidate evaluations
                         (insertion + 2-opt combined).

    Returns:
        InsertionTwoOptResult with combined statistics.
    """
    # Phase 1: Greedy insertion
    sorted_vertices = sorted(new_vertices)
    ins_result = cheapest_insertion(instance, route, sorted_vertices)

    # Check budget after insertion
    if max_evaluations is not None and ins_result.candidate_evaluations >= max_evaluations:
        return InsertionTwoOptResult(
            route=ins_result.route,
            cost=ins_result.cost,
            insertion_evaluations=ins_result.candidate_evaluations,
            two_opt_evaluations=0,
            total_evaluations=ins_result.candidate_evaluations,
            insertion_deltas=ins_result.deltas,
            two_opt_accepted_moves=0,
            two_opt_passes=0,
        )

    # Phase 2: 2-opt local search on the route after insertions
    # Remaining budget for 2-opt
    remaining_evals = None
    if max_evaluations is not None:
        remaining_evals = max_evaluations - ins_result.candidate_evaluations

    two_opt_result = two_opt(
        instance,
        ins_result.route,
        max_passes=max_passes,
        max_evaluations=remaining_evals,
    )

    return InsertionTwoOptResult(
        route=two_opt_result.route,
        cost=two_opt_result.cost,
        insertion_evaluations=ins_result.candidate_evaluations,
        two_opt_evaluations=two_opt_result.candidate_evaluations,
        total_evaluations=ins_result.candidate_evaluations + two_opt_result.candidate_evaluations,
        insertion_deltas=ins_result.deltas,
        two_opt_accepted_moves=two_opt_result.accepted_moves,
        two_opt_passes=two_opt_result.passes,
    )


def strategy_b_repair(
    instance: Instance,
    route: Route,
    new_vertices: Sequence[int],
) -> InsertionTwoOptResult:
    """Strategy B with defaults (run 2-opt to local optimum)."""
    return insertion_then_two_opt(instance, route, new_vertices)