"""Unit tests for evaluation metrics and plotting.

Tests cover: disruption calculation, feasibility checking, route evaluation,
TimedOperation context manager, ExperimentMetrics aggregation.
"""

import math
import pytest
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for testing

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.evaluation.metrics import (
    RouteMetrics,
    ExperimentMetrics,
    compute_disruption,
    check_feasibility,
    evaluate_route,
    TimedOperation,
)
from adaptive_route_optimization.evaluation.plotting import (
    plot_route,
    plot_route_comparison,
    plot_cost_convergence,
    plot_disruption_over_time,
)


# --- Disruption Tests ---

def test_disruption_identical_routes():
    """Disruption between identical routes is 0."""
    route = Route((0, 1, 2, 3, 0))
    d = compute_disruption(route, route)
    assert math.isclose(d, 0.0)


def test_disruption_completely_different():
    """Disruption between routes with no shared edges is 1."""
    route1 = Route((0, 1, 2, 0))
    route2 = Route((0, 2, 1, 0))
    d = compute_disruption(route1, route2)
    assert math.isclose(d, 1.0)


def test_disruption_partial_overlap():
    """Disruption with partial edge overlap."""
    # S0 = (0, 1, 4, 2, 3, 0) - edges: (0,1), (1,4), (4,2), (2,3), (3,0)
    # S1 = (0, 1, 4, 5, 2, 3, 0) - edges: (0,1), (1,4), (4,5), (5,2), (2,3), (3,0)
    # Intersection: (0,1), (1,4), (2,3), (3,0) = 4 edges
    # max(|E0|, |E1|) = max(5, 6) = 6
    # disruption = 1 - 4/6 = 1/3
    route0 = Route((0, 1, 4, 2, 3, 0))
    route1 = Route((0, 1, 4, 5, 2, 3, 0))
    d = compute_disruption(route0, route1)
    assert math.isclose(d, 1.0 / 3.0)


def test_disruption_empty_routes():
    """Disruption with empty routes (just depot)."""
    route = Route((0, 0))
    d = compute_disruption(route, route)
    assert math.isclose(d, 0.0)


def test_disruption_different_lengths():
    """Disruption with different route lengths."""
    route1 = Route((0, 1, 0))  # 1 edge: (0,1), (1,0)
    route2 = Route((0, 1, 2, 0))  # 2 edges: (0,1), (1,2), (2,0)
    d = compute_disruption(route1, route2)
    # Edges1: {(0,1), (1,0)} vs Edges2: {(0,1), (1,2), (2,0)} -> intersection = {(0,1)} = 1
    # max(2, 3) = 3 -> disruption = 1 - 1/3 = 2/3
    assert math.isclose(d, 2.0 / 3.0)


# --- Feasibility Tests ---

def test_feasibility_valid():
    """Valid route passes feasibility."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1)])
    route = Route((0, 1, 2, 0))
    assert check_feasibility(route, inst)


def test_feasibility_missing_vertex():
    """Missing required vertex fails feasibility."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1)])
    route = Route((0, 1, 0))  # Missing vertex 2
    assert not check_feasibility(route, inst)


def test_feasibility_extra_vertex():
    """Extra vertex fails feasibility."""
    inst = Instance.from_coords([(0, 0), (1, 0)])
    route = Route((0, 1, 2, 0))  # Vertex 2 doesn't exist
    assert not check_feasibility(route, inst)


def test_feasibility_custom_required():
    """Feasibility with custom required vertex set."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1), (2, 2)])
    route = Route((0, 1, 2, 0))
    # Only require {1, 2}
    assert check_feasibility(route, inst, required_vertices={1, 2})
    # Require {1, 2, 3} -> fails
    assert not check_feasibility(route, inst, required_vertices={1, 2, 3})


# --- Route Evaluation Tests ---

def test_evaluate_route_initial():
    """Evaluate initial route (no previous route for disruption)."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1)])
    route = Route((0, 1, 2, 0))
    metrics = evaluate_route(route, inst, prev_route=None, computational_effort=10, response_time_ms=5.0)

    assert math.isclose(metrics.route_cost, 2 + math.sqrt(2))
    assert math.isclose(metrics.disruption, 0.0)
    assert metrics.feasible
    assert metrics.computational_effort == 10
    assert math.isclose(metrics.response_time_ms, 5.0)


def test_evaluate_route_with_prev():
    """Evaluate route with previous route for disruption."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1)])
    route0 = Route((0, 1, 2, 0))
    route1 = Route((0, 2, 1, 0))
    metrics = evaluate_route(route1, inst, prev_route=route0, computational_effort=5, response_time_ms=2.0)

    assert math.isclose(metrics.disruption, 1.0)


def test_evaluate_route_infeasible():
    """Evaluate infeasible route."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1)])
    route = Route((0, 1, 0))  # Missing vertex 2
    metrics = evaluate_route(route, inst, required_vertices={1, 2})

    assert not metrics.feasible


# --- TimedOperation Tests ---

def test_timed_operation_basic():
    """Test TimedOperation context manager."""
    import time

    with TimedOperation() as timer:
        time.sleep(0.01)  # 10ms
        timer.add_evaluations(5)

    assert timer.evals == 5
    assert timer.elapsed_ms >= 10.0  # At least 10ms


def test_timed_operation_multiple_adds():
    """Test multiple evaluation additions."""
    with TimedOperation() as timer:
        timer.add_evaluations(3)
        timer.add_evaluations(7)
    assert timer.evals == 10


def test_timed_operation_negative_evals():
    """Test negative evaluations raise error."""
    with TimedOperation() as timer:
        with pytest.raises(ValueError):
            timer.add_evaluations(-1)


# --- ExperimentMetrics Tests ---

def test_experiment_metrics_aggregation():
    """Test ExperimentMetrics aggregation."""
    metrics = ExperimentMetrics(
        final_route_cost=100.0,
        route_costs=[80.0, 90.0, 100.0],
        disruptions=[0.0, 0.3, 0.2],
        total_computational_effort=1000,
        total_response_time_ms=50.0,
        all_feasible=True,
        num_time_steps=3,
    )

    assert math.isclose(metrics.mean_disruption, (0.0 + 0.3 + 0.2) / 3)
    assert math.isclose(metrics.max_disruption, 0.3)


def test_experiment_metrics_empty():
    """Test ExperimentMetrics with empty disruptions."""
    metrics = ExperimentMetrics(
        final_route_cost=0.0,
        route_costs=[],
        disruptions=[],
        total_computational_effort=0,
        total_response_time_ms=0.0,
        all_feasible=True,
        num_time_steps=0,
    )
    assert metrics.mean_disruption == 0.0
    assert metrics.max_disruption == 0.0


# --- Plotting Tests (smoke tests - just verify no errors) ---

def test_plot_route_smoke():
    """Smoke test: plot_route runs without error."""
    inst = Instance.from_coords([(0, 0), (1, 0), (1, 1), (0, 1)])
    route = Route((0, 1, 2, 3, 0))

    fig, ax = matplotlib.pyplot.subplots()
    plot_route(inst, route, ax=ax, title="Test Route")
    matplotlib.pyplot.close(fig)


def test_plot_route_comparison_smoke():
    """Smoke test: plot_route_comparison runs without error."""
    inst = Instance.from_coords([(0, 0), (1, 0), (1, 1), (0, 1)])
    route1 = Route((0, 1, 2, 3, 0))
    route2 = Route((0, 2, 1, 3, 0))

    fig = plot_route_comparison(inst, [route1, route2], labels=["Route A", "Route B"])
    matplotlib.pyplot.close(fig)


def test_plot_cost_convergence_smoke():
    """Smoke test: plot_cost_convergence runs without error."""
    fig = plot_cost_convergence(
        [[100, 95, 92, 90], [100, 98, 96, 95]],
        labels=["Strategy A", "Strategy B"]
    )
    matplotlib.pyplot.close(fig)


def test_plot_disruption_over_time_smoke():
    """Smoke test: plot_disruption_over_time runs without error."""
    fig = plot_disruption_over_time([0.0, 0.3, 0.2, 0.1, 0.15])
    matplotlib.pyplot.close(fig)


# --- RouteMetrics Validation Tests ---

def test_route_metrics_validation():
    """Test RouteMetrics validation."""
    # Valid
    m = RouteMetrics(
        route_cost=100.0,
        disruption=0.5,
        feasible=True,
        computational_effort=10,
        response_time_ms=5.0,
    )
    assert m.route_cost == 100.0

    # Invalid disruption
    with pytest.raises(ValueError):
        RouteMetrics(100.0, 1.5, True, 10, 5.0)

    with pytest.raises(ValueError):
        RouteMetrics(100.0, -0.1, True, 10, 5.0)

    # Negative effort
    with pytest.raises(ValueError):
        RouteMetrics(100.0, 0.5, True, -1, 5.0)

    # Negative time
    with pytest.raises(ValueError):
        RouteMetrics(100.0, 0.5, True, 10, -1.0)