"""Algorithms package for route optimization."""

from adaptive_route_optimization.algorithms.baseline import (
    NNResult,
    nearest_neighbor,
    nearest_neighbor_from_coords,
    ExactResult,
    exact_tsp,
    exact_tsp_from_coords,
)
from adaptive_route_optimization.algorithms.local_search import (
    TwoOptResult,
    two_opt,
    two_opt_batch,
    two_opt_from_route,
)
from adaptive_route_optimization.algorithms.repair import (
    InsertionResult,
    cheapest_insertion,
    greedy_insertion_repair,
    InsertionTwoOptResult,
    insertion_then_two_opt,
    strategy_b_repair,
)

__all__ = [
    # Baseline
    "NNResult",
    "nearest_neighbor",
    "nearest_neighbor_from_coords",
    "ExactResult",
    "exact_tsp",
    "exact_tsp_from_coords",
    # Local search
    "TwoOptResult",
    "two_opt",
    "two_opt_batch",
    "two_opt_from_route",
    # Repair
    "InsertionResult",
    "cheapest_insertion",
    "greedy_insertion_repair",
    "InsertionTwoOptResult",
    "insertion_then_two_opt",
    "strategy_b_repair",
]