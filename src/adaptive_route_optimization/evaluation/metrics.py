"""Evaluation metrics for the routing problem.

Implements all metrics defined in RESEARCH_SPEC.md:
- Route Cost (Primary Quality)
- Update Response Time (wall-clock)
- Computational Effort (candidate evaluations)
- Route Disruption (edge-based normalized)
- Feasibility (boolean)
- Scalability (trends vs n and alpha)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


@dataclass(frozen=True)
class RouteMetrics:
    """Complete metrics for a single route at a time step.

    Attributes:
        route_cost: Total cost C(S_t) - primary quality metric.
        disruption: Normalized edge-difference δ(S_{t-1}, S_t) ∈ [0, 1].
        feasible: Boolean feasibility check.
        computational_effort: Unified computational effort (candidate_evaluations + overhead_evaluations).
        response_time_ms: Wall-clock time for update in milliseconds.
        candidate_evaluations: Number of candidate route/path modifications evaluated.
        overhead_evaluations: Selector rule evaluation and feature extraction overhead.
    """
    route_cost: float
    disruption: float
    feasible: bool
    computational_effort: int
    response_time_ms: float
    candidate_evaluations: Optional[int] = None
    overhead_evaluations: int = 0

    def __post_init__(self) -> None:
        if not (0.0 <= self.disruption <= 1.0):
            raise ValueError(f"Disruption must be in [0, 1], got {self.disruption}")
        if self.computational_effort < 0:
            raise ValueError("Computational effort must be non-negative")
        if self.response_time_ms < 0:
            raise ValueError("Response time must be non-negative")
        if self.candidate_evaluations is None:
            cand = max(0, self.computational_effort - self.overhead_evaluations)
            object.__setattr__(self, "candidate_evaluations", cand)


def compute_disruption(route_prev: Route, route_curr: Route) -> float:
    """Compute normalized edge-based disruption δ(S_{t-1}, S_t).

    Formula: δ = 1 - |E_t ∩ E_{t+1}| / max(|E_t|, |E_{t+1}|)

    Args:
        route_prev: Previous route S_t.
        route_curr: Current route S_{t+1}.

    Returns:
        Disruption value in [0, 1].
    """
    edges_prev = route_prev.edges()
    edges_curr = route_curr.edges()

    if not edges_prev and not edges_curr:
        return 0.0

    intersection = edges_prev & edges_curr
    max_edges = max(len(edges_prev), len(edges_curr))

    if max_edges == 0:
        return 0.0

    return 1.0 - len(intersection) / max_edges


def check_feasibility(route: Route, instance: Instance, required_vertices: Optional[set[int]] = None) -> bool:
    """Check route feasibility for given required vertices.

    Args:
        route: Route to check.
        instance: Problem instance.
        required_vertices: Required vertices (default: all non-depot in instance).

    Returns:
        True if feasible, False otherwise.
    """
    return route.is_feasible(instance, required_vertices)


def evaluate_route(
    route: Route,
    instance: Instance,
    prev_route: Optional[Route] = None,
    required_vertices: Optional[set[int]] = None,
    computational_effort: int = 0,
    response_time_ms: float = 0.0,
    candidate_evaluations: Optional[int] = None,
    overhead_evaluations: int = 0,
) -> RouteMetrics:
    """Compute all metrics for a route at a time step.

    Args:
        route: Current route.
        instance: Problem instance.
        prev_route: Previous route for disruption calculation (None for t=0).
        required_vertices: Required vertices for feasibility.
        computational_effort: Unified computational effort.
        response_time_ms: Wall-clock time for update.
        candidate_evaluations: Explicit candidate move evaluations.
        overhead_evaluations: Explicit selector overhead evaluations.

    Returns:
        RouteMetrics with all computed values.
    """
    cost = route.cost(instance)
    feasible = check_feasibility(route, instance, required_vertices)

    if prev_route is not None:
        disruption = compute_disruption(prev_route, route)
    else:
        disruption = 0.0  # No disruption at initial solution

    if candidate_evaluations is not None and computational_effort == 0 and overhead_evaluations > 0:
        computational_effort = candidate_evaluations + overhead_evaluations

    return RouteMetrics(
        route_cost=cost,
        disruption=disruption,
        feasible=feasible,
        computational_effort=computational_effort,
        response_time_ms=response_time_ms,
        candidate_evaluations=candidate_evaluations,
        overhead_evaluations=overhead_evaluations,
    )


class TimedOperation:
    """Context manager for timing operations and counting evaluations.

    Usage:
        with TimedOperation() as timer:
            result = some_algorithm()
        metrics = evaluate_route(..., computational_effort=timer.evals, response_time_ms=timer.elapsed_ms)
    """

    def __init__(self) -> None:
        self._start: float = 0.0
        self._evals: int = 0
        self._elapsed_ms: float = 0.0

    def __enter__(self) -> TimedOperation:
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._elapsed_ms = (time.perf_counter() - self._start) * 1000.0

    def add_evaluations(self, count: int) -> None:
        """Add candidate evaluations."""
        if count < 0:
            raise ValueError("Evaluation count must be non-negative")
        self._evals += count

    @property
    def evals(self) -> int:
        return self._evals

    @property
    def elapsed_ms(self) -> float:
        return self._elapsed_ms


@dataclass(frozen=True)
class ExperimentMetrics:
    """Aggregated metrics for a full experiment run.

    Attributes:
        final_route_cost: Cost at final time step.
        route_costs: List of costs at each time step.
        disruptions: List of disruptions at each time step.
        total_computational_effort: Sum of evaluations across all steps.
        total_response_time_ms: Sum of wall-clock times.
        all_feasible: True if all routes were feasible.
        num_time_steps: Number of time steps (events + initial).
    """
    final_route_cost: float
    route_costs: list[float]
    disruptions: list[float]
    total_computational_effort: int
    total_response_time_ms: float
    all_feasible: bool
    num_time_steps: int

    @property
    def mean_disruption(self) -> float:
        return sum(self.disruptions) / len(self.disruptions) if self.disruptions else 0.0

    @property
    def max_disruption(self) -> float:
        return max(self.disruptions) if self.disruptions else 0.0