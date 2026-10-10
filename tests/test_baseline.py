"""Unit tests for baseline algorithms (Nearest Neighbor, Exact TSP).

Tests cover: NN construction, exact solver, exact-vs-heuristic comparison on small instances,
deterministic behavior under fixed seeds, edge cases.
"""

import math
import pytest

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.algorithms.baseline.nearest_neighbor import (
    nearest_neighbor,
    nearest_neighbor_from_coords,
)
from adaptive_route_optimization.algorithms.baseline.exact import (
    exact_tsp,
    exact_tsp_from_coords,
)


# --- Nearest Neighbor Tests ---

def test_nn_simple():
    """Test NN on simple 3-vertex instance (depot + 2 customers)."""
    coords = [(0, 0), (3, 0), (0, 4)]
    result = nearest_neighbor_from_coords(coords)

    # From depot (0): nearest is 1 (dist=3) vs 2 (dist=4) -> pick 1
    # From 1: only 2 left -> pick 2
    # Return to depot
    assert result.route.vertices == (0, 1, 2, 0)
    assert result.candidate_evaluations == 3  # 2 + 1


def test_nn_tie_breaking_by_index():
    """Test deterministic tie-breaking: lowest vertex index wins."""
    # Vertex 1 and 2 at equal distance from depot
    coords = [(0, 0), (3, 0), (-3, 0)]  # Both at distance 3
    result = nearest_neighbor_from_coords(coords)
    # Should pick vertex 1 (lower index)
    assert result.route.vertices == (0, 1, 2, 0)


def test_nn_deterministic_seed():
    """Test NN is deterministic given same instance."""
    inst = Instance.generate_random(n=10, seed=42)
    result1 = nearest_neighbor(inst)
    result2 = nearest_neighbor(inst)
    assert result1.route.vertices == result2.route.vertices
    assert result1.candidate_evaluations == result2.candidate_evaluations


def test_nn_vertex_subset():
    """Test NN on subset of vertices."""
    inst = Instance.from_coords([(0, 0), (3, 0), (0, 4), (6, 0)])
    # Only use depot, 1, 3 (skip vertex 2)
    result = nearest_neighbor(inst, vertex_subset={0, 1, 3})
    assert set(result.route.vertices[1:-1]) == {1, 3}
    assert result.route.vertices[0] == 0 and result.route.vertices[-1] == 0


def test_nn_only_depot():
    """Test NN with only depot (empty route)."""
    inst = Instance.from_coords([(0, 0)])
    result = nearest_neighbor(inst)
    assert result.route.vertices == (0, 0)
    assert result.candidate_evaluations == 0


def test_nn_candidate_evaluations_count():
    """Test candidate evaluation count matches formula n(n+1)/2."""
    # n non-depot vertices -> n + (n-1) + ... + 1 = n(n+1)/2 evaluations
    for n in [1, 2, 3, 4, 5, 10]:
        inst = Instance.generate_random(n=n, seed=123)
        result = nearest_neighbor(inst)
        expected = n * (n + 1) // 2
        assert result.candidate_evaluations == expected, f"Failed for n={n}"


def test_nn_feasible():
    """Test NN produces feasible routes."""
    inst = Instance.generate_random(n=20, seed=999)
    result = nearest_neighbor(inst)
    assert result.route.is_feasible(inst)


def test_nn_vertex_subset_feasible():
    """Test NN on subset produces feasible route for that subset."""
    inst = Instance.generate_random(n=20, seed=555)
    subset = {0, 1, 3, 5, 7, 9}
    result = nearest_neighbor(inst, vertex_subset=subset)
    assert result.route.is_feasible(inst, required_vertices=subset - {0})


# --- Exact TSP Tests ---

def test_exact_tsp_optimal():
    """Test exact solver finds optimal on small instance."""
    # Simple square: depot at (0,0), customers at (1,0), (1,1), (0,1)
    coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    result = exact_tsp_from_coords(coords)

    # Optimal tour: 0-1-2-3-0 or 0-3-2-1-0 (both cost = 4)
    assert math.isclose(result.cost, 4.0)
    assert result.route.is_feasible(Instance.from_coords(coords))


def test_exact_tsp_triangle():
    """Test exact solver on triangle (3 vertices)."""
    coords = [(0, 0), (3, 0), (0, 4)]
    result = exact_tsp_from_coords(coords)
    # Only one possible tour (up to reversal): 0-1-2-0
    # cost = 3 + 5 + 4 = 12
    assert math.isclose(result.cost, 12.0)


def test_exact_tsp_deterministic():
    """Test exact solver is deterministic."""
    inst = Instance.generate_random(n=6, seed=777)
    r1 = exact_tsp(inst)
    r2 = exact_tsp(inst)
    assert r1.route.vertices == r2.route.vertices
    assert math.isclose(r1.cost, r2.cost)


def test_exact_tsp_vertex_subset():
    """Test exact solver on vertex subset."""
    inst = Instance.from_coords([(0, 0), (1, 0), (2, 0), (3, 0)])
    result = exact_tsp(inst, vertex_subset={0, 1, 3})
    assert set(result.route.vertices[1:-1]) == {1, 3}


def test_exact_tsp_only_depot():
    """Test exact solver with only depot."""
    inst = Instance.from_coords([(0, 0)])
    result = exact_tsp(inst)
    assert result.route.vertices == (0, 0)
    assert result.cost == 0.0
    assert result.candidate_evaluations == 0


def test_exact_tsp_max_vertices_limit():
    """Test exact solver raises error for too many vertices."""
    inst = Instance.generate_random(n=10, seed=1)
    with pytest.raises(ValueError):
        exact_tsp(inst, max_vertices=8)


def test_exact_tsp_candidate_evaluations():
    """Test candidate evaluation count = n! for n customers."""
    # n=3 -> 6 permutations
    coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
    result = exact_tsp_from_coords(coords)
    assert result.candidate_evaluations == 6  # 3! = 6

    # n=4 -> 24 permutations
    coords2 = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
    result2 = exact_tsp_from_coords(coords2)
    assert result2.candidate_evaluations == 24  # 4! = 24


# --- Exact vs Heuristic Comparison Tests ---

def test_nn_vs_exact_small_instances():
    """Compare NN vs exact on many small random instances (n <= 7)."""
    for seed in range(20):
        n = 5  # Small enough for exact
        inst = Instance.generate_random(n=n, seed=seed)
        nn_result = nearest_neighbor(inst)
        exact_result = exact_tsp(inst)

        # NN cost should be >= exact cost (exact is optimal)
        assert nn_result.route.cost(inst) >= exact_result.cost - 1e-9, \
            f"NN better than exact on seed {seed}"

        # Both should be feasible
        assert nn_result.route.is_feasible(inst)
        assert exact_result.route.is_feasible(inst)


def test_nn_vs_exact_known_cases():
    """Test NN vs exact on specific known instances."""
    # Case 1: Line of points - NN should be optimal
    coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
    nn = nearest_neighbor_from_coords(coords)
    exact = exact_tsp_from_coords(coords)
    assert math.isclose(nn.route.cost(Instance.from_coords(coords)), exact.cost)

    # Case 2: Square - NN might not be optimal
    coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    nn = nearest_neighbor_from_coords(coords)
    exact = exact_tsp_from_coords(coords)
    # NN from depot: nearest is (1,0) or (0,1) at dist 1 -> picks index 1
    # Then from (1,0): nearest unvisited is (1,1) at dist 1
    # Then (0,1) -> back to depot
    # NN route: 0-1-2-3-0, cost = 1+1+1+1 = 4 (optimal in this case)
    assert math.isclose(nn.route.cost(Instance.from_coords(coords)), exact.cost)


def test_exact_result_structure():
    """Test ExactResult has correct structure."""
    coords = [(0, 0), (1, 0), (0, 1)]
    result = exact_tsp_from_coords(coords)
    assert isinstance(result.route, Route)
    assert isinstance(result.cost, float)
    assert isinstance(result.candidate_evaluations, int)
    assert result.candidate_evaluations > 0


def test_nn_result_structure():
    """Test NNResult has correct structure."""
    coords = [(0, 0), (1, 0), (0, 1)]
    result = nearest_neighbor_from_coords(coords)
    assert isinstance(result.route, Route)
    assert isinstance(result.candidate_evaluations, int)
    assert result.candidate_evaluations > 0


# --- Edge Cases ---

def test_nn_invalid_vertex_subset():
    """Test NN rejects subset without depot."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1)])
    with pytest.raises(ValueError):
        nearest_neighbor(inst, vertex_subset={1, 2})


def test_exact_invalid_vertex_subset():
    """Test exact solver rejects subset without depot."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1)])
    with pytest.raises(ValueError):
        exact_tsp(inst, vertex_subset={1, 2})


def test_nn_coordinate_consistency():
    """Test NN from coords matches NN from instance."""
    coords = [(0, 0), (3, 0), (3, 4), (0, 4)]
    result1 = nearest_neighbor_from_coords(coords)
    inst = Instance.from_coords(coords)
    result2 = nearest_neighbor(inst)
    assert result1.route.vertices == result2.route.vertices
    assert result1.candidate_evaluations == result2.candidate_evaluations


def test_exact_coordinate_consistency():
    """Test exact from coords matches exact from instance."""
    coords = [(0, 0), (3, 0), (3, 4)]
    result1 = exact_tsp_from_coords(coords)
    inst = Instance.from_coords(coords)
    result2 = exact_tsp(inst)
    assert result1.route.vertices == result2.route.vertices
    assert math.isclose(result1.cost, result2.cost)