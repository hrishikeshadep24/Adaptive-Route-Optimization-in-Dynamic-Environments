"""Unit tests for models (Instance, Route).

Tests cover: construction, cost calculation, feasibility, edge cases
(empty route, 1 node, 2 nodes, duplicate coordinates, zero-cost edges, invalid routes).
"""

import math
import pytest
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route, validate_route


# --- Instance Tests ---

def test_instance_creation():
    """Test basic instance creation from coordinates."""
    coords = [(0, 0), (3, 0), (3, 4)]  # depot + 2 customers
    inst = Instance.from_coords(coords)
    assert inst.n == 2
    assert inst.num_vertices == 3


def test_instance_cost_euclidean():
    """Test Euclidean distance calculation."""
    inst = Instance.from_coords([(0, 0), (3, 0), (3, 4)])
    # c(0,1) = 3
    assert math.isclose(inst.cost(0, 1), 3.0)
    # c(1,2) = 4
    assert math.isclose(inst.cost(1, 2), 4.0)
    # c(0,2) = 5 (3-4-5 triangle)
    assert math.isclose(inst.cost(0, 2), 5.0)
    # Symmetry
    assert math.isclose(inst.cost(0, 1), inst.cost(1, 0))
    # Zero self-distance
    assert math.isclose(inst.cost(0, 0), 0.0)


def test_instance_cost_matrix():
    """Test full cost matrix generation."""
    inst = Instance.from_coords([(0, 0), (3, 0), (3, 4)])
    C = inst.cost_matrix()
    assert C.shape == (3, 3)
    assert math.isclose(C[0, 1], 3.0)
    assert math.isclose(C[1, 0], 3.0)
    assert math.isclose(C[0, 0], 0.0)


def test_instance_subset():
    """Test creating sub-instance with subset of vertices."""
    inst = Instance.from_coords([(0, 0), (3, 0), (3, 4), (0, 4)])
    # Keep depot and vertices 1, 3
    sub = inst.subset([0, 1, 3])
    assert sub.n == 2
    assert sub.num_vertices == 3
    # Coordinates should match
    assert math.isclose(sub.coords[0, 0], 0.0)
    assert math.isclose(sub.coords[1, 0], 3.0)
    assert math.isclose(sub.coords[2, 1], 4.0)


def test_instance_generate_random():
    """Test deterministic random instance generation."""
    inst1 = Instance.generate_random(n=5, seed=42)
    inst2 = Instance.generate_random(n=5, seed=42)
    # Same seed -> same coordinates
    assert np.allclose(inst1.coords, inst2.coords)
    # Different seed -> different coordinates (with high probability)
    inst3 = Instance.generate_random(n=5, seed=43)
    assert not np.allclose(inst1.coords, inst3.coords)


def test_instance_generate_random_depot_at_origin():
    """Test depot at origin option."""
    inst = Instance.generate_random(n=5, seed=1, depot_at_origin=True)
    assert math.isclose(inst.coords[0, 0], 0.0)
    assert math.isclose(inst.coords[0, 1], 0.0)


def test_instance_generate_random_min_separation():
    """Test minimum separation to avoid zero-cost edges."""
    # Generate many instances, none should have coincident points
    for seed in range(10):
        inst = Instance.generate_random(n=10, seed=seed, min_separation=1e-6)
        for i in range(inst.num_vertices):
            for j in range(i + 1, inst.num_vertices):
                assert inst.cost(i, j) >= 1e-6, f"Zero-cost edge between {i} and {j}"


def test_instance_get_subinstance():
    """Test getting sub-instance for known vertices."""
    inst = Instance.from_coords([(0, 0), (3, 0), (3, 4), (0, 4)])
    known = {0, 1, 3}
    sub = inst.get_subinstance(known)
    assert sub.n == 2
    assert sub.num_vertices == 3


def test_instance_errors():
    """Test error handling in Instance."""
    # Invalid coords shape
    with pytest.raises(ValueError):
        Instance(np.array([[[1, 2]]]))  # 3D

    # Cost index out of bounds
    inst = Instance.from_coords([(0, 0), (1, 1)])
    with pytest.raises(IndexError):
        inst.cost(0, 5)

    # Subset without depot
    with pytest.raises(ValueError):
        inst.subset([1, 2])

    # get_subinstance without depot
    with pytest.raises(ValueError):
        inst.get_subinstance({1, 2})


# --- Route Tests ---

def test_route_creation_valid():
    """Test valid route creation."""
    route = Route((0, 1, 2, 3, 0))
    assert route.num_edges == 4
    assert route.num_customers == 3
    assert route.visited_customers == {1, 2, 3}


def test_route_creation_errors():
    """Test route validation errors."""
    # Not starting at depot
    with pytest.raises(ValueError):
        Route((1, 2, 3, 1))

    # Not ending at depot
    with pytest.raises(ValueError):
        Route((0, 1, 2, 3))

    # Empty route
    with pytest.raises(ValueError):
        Route(())

    # Duplicate vertices
    with pytest.raises(ValueError):
        Route((0, 1, 2, 1, 0))

    # Depot in middle
    with pytest.raises(ValueError):
        Route((0, 1, 0, 2, 0))


def test_route_cost():
    """Test route cost calculation."""
    inst = Instance.from_coords([(0, 0), (3, 0), (3, 4), (0, 4)])
    route = Route((0, 1, 2, 3, 0))
    # 0->1: 3, 1->2: 4, 2->3: 3, 3->0: 4 = 14
    assert math.isclose(route.cost(inst), 14.0)


def test_route_edges():
    """Test edge set extraction."""
    route = Route((0, 1, 2, 3, 0))
    edges = route.edges()
    expected = {(0, 1), (1, 2), (2, 3), (3, 0)}
    assert edges == expected


def test_route_feasible():
    """Test feasibility checking."""
    inst = Instance.from_coords([(0, 0), (3, 0), (3, 4), (0, 4)])
    route = Route((0, 1, 2, 3, 0))
    assert route.is_feasible(inst)
    # Missing vertex 3
    route2 = Route((0, 1, 2, 0))
    assert not route2.is_feasible(inst, required_vertices={1, 2, 3})
    # Extra vertex
    route3 = Route((0, 1, 2, 3, 4, 0))  # vertex 4 doesn't exist
    assert not route3.is_feasible(inst)


def test_route_with_insertion():
    """Test route insertion."""
    route = Route((0, 1, 2, 0))
    # Insert vertex 3 at position 1 (between 1 and 2)
    new_route = route.with_insertion(1, 3)
    assert new_route.vertices == (0, 1, 3, 2, 0)

    # Insert at position 0 (after depot)
    new_route2 = route.with_insertion(0, 3)
    assert new_route2.vertices == (0, 3, 1, 2, 0)

    # Errors
    with pytest.raises(ValueError):
        route.with_insertion(0, 0)  # Can't insert depot
    with pytest.raises(ValueError):
        route.with_insertion(0, 1)  # Already in route
    with pytest.raises(ValueError):
        route.with_insertion(5, 3)  # Invalid position


def test_route_with_2opt_swap():
    """Test 2-opt swap."""
    route = Route((0, 1, 2, 3, 4, 0))
    # Swap edges (0,1) and (2,3) -> reverse segment 1..2
    new_route = route.with_2opt_swap(0, 2)
    # (0, 1, 2, 3, 4, 0) -> reverse 1..2 -> (0, 2, 1, 3, 4, 0)
    assert new_route.vertices == (0, 2, 1, 3, 4, 0)

    # Errors
    with pytest.raises(ValueError):
        route.with_2opt_swap(0, 1)  # Adjacent edges
    with pytest.raises(ValueError):
        route.with_2opt_swap(5, 10)  # Out of bounds


def test_validate_route():
    """Test route validation helper."""
    inst = Instance.from_coords([(0, 0), (3, 0), (3, 4)])
    route = Route((0, 1, 2, 0))
    valid, errors = validate_route(route, inst, required_vertices={1, 2})
    assert valid
    assert errors == []

    # Invalid route
    route2 = Route((0, 1, 0))  # Missing vertex 2
    valid, errors = validate_route(route2, inst, required_vertices={1, 2})
    assert not valid
    assert any("Missing" in e for e in errors)


def test_edge_case_empty_initial_route():
    """Edge case: only depot known (V0 = {0})."""
    inst = Instance.from_coords([(0, 0)])  # Only depot
    route = Route((0, 0))
    assert route.num_edges == 1
    assert route.num_customers == 0
    assert route.cost(inst) == 0.0
    assert route.is_feasible(inst, required_vertices=set())


def test_edge_case_single_customer():
    """Edge case: depot + 1 customer."""
    inst = Instance.from_coords([(0, 0), (5, 0)])
    route = Route((0, 1, 0))
    assert route.num_edges == 2
    assert route.num_customers == 1
    assert math.isclose(route.cost(inst), 10.0)  # 5 + 5
    assert route.is_feasible(inst, required_vertices={1})


def test_edge_case_two_customers():
    """Edge case: depot + 2 customers."""
    inst = Instance.from_coords([(0, 0), (3, 0), (0, 4)])
    route = Route((0, 1, 2, 0))
    assert math.isclose(route.cost(inst), 3 + 5 + 4)  # 3 + 5 + 4 = 12


def test_edge_case_duplicate_coordinates():
    """Edge case: duplicate coordinates (handled by min_separation in generator)."""
    # Manual creation with duplicate coords
    coords = [(0, 0), (1, 1), (1, 1)]  # Vertices 1 and 2 at same position
    inst = Instance.from_coords(coords)
    # Should still work, cost between 1 and 2 is 0
    assert math.isclose(inst.cost(1, 2), 0.0)
    route = Route((0, 1, 2, 0))
    cost = route.cost(inst)
    # 0->1: sqrt(2), 1->2: 0, 2->0: sqrt(2) = 2*sqrt(2)
    assert math.isclose(cost, 2 * math.sqrt(2))


def test_edge_case_zero_cost_edges():
    """Edge case: zero-cost edges in cost matrix."""
    # Already tested in duplicate_coordinates, but explicit
    inst = Instance.from_coords([(0, 0), (1, 1), (1, 1)])
    assert inst.cost(1, 2) == 0.0
    assert inst.cost(1, 1) == 0.0


def test_route_immutability():
    """Routes are immutable (frozen dataclass)."""
    route = Route((0, 1, 2, 0))
    with pytest.raises(AttributeError):
        route.vertices = (0, 2, 1, 0)


def test_route_indexing():
    """Test route indexing and iteration."""
    route = Route((0, 1, 2, 0))
    assert route[0] == 0
    assert route[1] == 1
    assert route[2] == 2
    assert route[3] == 0
    assert list(route) == [0, 1, 2, 0]
    assert len(route) == 4


def test_route_repr():
    """Test route string representation."""
    route = Route((0, 1, 2, 0))
    assert repr(route) == "Route([0, 1, 2, 0])"