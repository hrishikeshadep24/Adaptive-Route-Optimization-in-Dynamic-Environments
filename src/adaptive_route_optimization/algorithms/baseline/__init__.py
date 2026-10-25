"""Baseline algorithms package."""

from adaptive_route_optimization.algorithms.baseline.nearest_neighbor import (
    NNResult,
    nearest_neighbor,
    nearest_neighbor_from_coords,
)
from adaptive_route_optimization.algorithms.baseline.exact import (
    ExactResult,
    exact_tsp,
    exact_tsp_from_coords,
)

__all__ = [
    "NNResult",
    "nearest_neighbor",
    "nearest_neighbor_from_coords",
    "ExactResult",
    "exact_tsp",
    "exact_tsp_from_coords",
]