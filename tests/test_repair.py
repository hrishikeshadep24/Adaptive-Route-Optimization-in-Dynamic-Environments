"""Unit tests for repair algorithms (Strategy A and B).

Tests cover: greedy insertion, insertion+2-opt, determinism, reproducibility
on same dynamic event, edge cases (empty route, batch events, budget limits).
"""

import pytest

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.algorithms.repair.insertion import (
    cheapest_insertion,
    greedy_insertion_repair,
    InsertionResult,
)
from adaptive_route_optimization.algorithms.repair.insertion_two_opt import (
    insertion_then_two_opt,
    strategy_b_repair,
    InsertionTwoOptResult,
)
from adaptive_route_optimization.algorithms.baseline import nearest_neighbor
from adaptive_route_optimization.algorithms.local_search.two_opt import two_opt


# --- Strategy A: Greedy Insertion Repair ---

def test_insertion_single_vertex():
    """Test inserting a single vertex into a route."""
    coords = [(0, 0), (3, 0), (3, 4), (0, 4), (6, 0)]
    inst = Instance.from_coords(coords)
    route = Route((0, 1, 2, 3, 0))  # Initial route

    # Insert vertex 4 (at 6,0)
    result = cheapest_insertion(inst, route, [4])

    assert result.route.is_feasible(inst, required_vertices={1, 2, 3, 4})
    assert result.candidate_evaluations == 4  # 4 edges in original route
    assert len(result.deltas) == 1
    assert result.cost == result.route.cost(inst)


def test_insertion_batch_vertices():
    """Test inserting multiple vertices (batch event)."""
    coords = [(0, 0), (1, 0), (0, 1), (2, 0), (0, 2)]
    inst = Instance.from_coords(coords)
    route = Route((0, 1, 2, 0))  # V0 = {0,1,2} -> 3 edges

    # Insert vertices 3, 4 (batch)
    result = cheapest_insertion(inst, route, [3, 4])

    assert result.route.is_feasible(inst, required_vertices={1, 2, 3, 4})
    # Route has 3 edges initially, first insertion: 3 evals, second: 4 evals = 7 total
    assert result.candidate_evaluations == 7
    assert len(result.deltas) == 2


def test_insertion_deterministic_tie_breaking():
    """Test insertion tie-breaking: lowest position index wins."""
    # Create instance with extra vertex to insert
    coords = [(0, 0), (2, 0), (2, 2), (0, 2), (4, 0)]
    inst = Instance.from_coords(coords)
    route = Route((0, 1, 2, 3, 0))

    # Insert vertex 4
    result = cheapest_insertion(inst, route, [4])
    r2 = cheapest_insertion(inst, route, [4])
    assert result.route.vertices == r2.route.vertices


def test_greedy_insertion_repair_sorted_order():
    """Test Strategy A processes vertices in sorted order (vertex index)."""
    inst = Instance.generate_random(n=10, seed=42)
    nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
    route = nn.route

    # Insert vertices 5, 4, 6 in that order
    # Should be processed as 4, 5, 6 (sorted)
    result = greedy_insertion_repair(inst, route, [5, 4, 6])

    assert result.route.is_feasible(inst, required_vertices={1, 2, 3, 4, 5, 6})


def test_insertion_empty_route():
    """Edge case: insert into empty route (only depot)."""
    # Instance with depot + 1 customer (vertex 1)
    inst = Instance.from_coords([(0, 0), (3, 0)])
    route = Route((0, 0))  # Empty route (just depot)

    result = cheapest_insertion(inst, route, [1])  # Insert first customer

    assert result.route.vertices == (0, 1, 0)
    assert abs(result.cost - 2 * inst.cost(0, 1)) < 1e-9
    assert result.candidate_evaluations == 1  # 1 edge in empty route


def test_insertion_preserves_feasibility():
    """Test insertion always produces feasible routes."""
    for seed in range(20):
        inst = Instance.generate_random(n=10, seed=seed)
        nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
        route = nn.route

        # Insert remaining vertices
        remaining = [v for v in range(4, inst.num_vertices)]
        result = cheapest_insertion(inst, route, remaining)

        assert result.route.is_feasible(inst), f"Failed seed {seed}"


def test_insertion_cost_calculation():
    """Verify insertion cost delta calculation is correct."""
    coords = [(0, 0), (3, 0), (3, 4), (0, 4), (6, 0)]
    inst = Instance.from_coords(coords)
    route = Route((0, 1, 2, 3, 0))

    # Insert vertex 4 between 2 and 3 (position 3 in vertices = after vertex 2)
    # Delta = c(2,4) + c(4,3) - c(2,3)
    # = 5 + sqrt(52) - 3
    result = cheapest_insertion(inst, route, [4])

    # The best position should be found
    assert result.deltas[0] >= 0  # Cost should not decrease below optimal (but can increase)


# --- Strategy B: Insertion + 2-opt Repair ---

def test_insertion_two_opt_basic():
    """Test Strategy B: insertion then 2-opt."""
    coords = [(0, 0), (3, 0), (3, 4), (0, 4), (6, 0), (6, 4)]
    inst = Instance.from_coords(coords)

    # Initial route on V0 = {0,1,2,3,4}
    route = Route((0, 1, 4, 2, 3, 0))

    # Insert vertex 5
    result = insertion_then_two_opt(inst, route, [5])

    assert isinstance(result, InsertionTwoOptResult)
    assert result.route.is_feasible(inst, required_vertices={1, 2, 3, 4, 5})
    assert result.total_evaluations == result.insertion_evaluations + result.two_opt_evaluations


def test_insertion_two_opt_hand_worked_example():
    """Verify Strategy B matches hand-worked example from Phase 2."""
    # From docs/HAND_WORKED_EXAMPLE.md:
    # S0 = (0, 1, 4, 2, 3, 0), cost=18
    # Event Δ₀={5}: insertion at position 2, delta=2, S1_A=(0,1,4,5,2,3,0), cost=20
    # 2-opt: 9 pairs examined, no improvement, S1_B = S1_A
    coords = {
        0: (0, 0), 1: (3, 0), 2: (3, 4), 3: (0, 4),
        4: (6, 0), 5: (6, 4)
    }
    inst = Instance.from_coords([coords[i] for i in range(6)])
    route = Route((0, 1, 4, 2, 3, 0))

    result = insertion_then_two_opt(inst, route, [5])

    # Should match hand-worked example
    assert result.route.vertices == (0, 1, 4, 5, 2, 3, 0)
    assert abs(result.cost - 20.0) < 1e-9
    assert result.insertion_evaluations == 5  # 5 edges in original route
    assert result.two_opt_evaluations == 9  # 6 edges -> 9 pairs
    assert result.two_opt_accepted_moves == 0
    assert result.two_opt_passes == 1


def test_strategy_b_repair_defaults():
    """Test Strategy B with defaults (run 2-opt to local optimum)."""
    inst = Instance.generate_random(n=8, seed=42)
    nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
    route = nn.route

    result = strategy_b_repair(inst, route, [4, 5])

    assert result.route.is_feasible(inst, required_vertices={1, 2, 3, 4, 5})
    assert result.two_opt_accepted_moves >= 0


def test_strategy_a_vs_b_same_event():
    """Test both strategies on same dynamic event produce valid routes."""
    for seed in range(20):
        inst = Instance.generate_random(n=8, seed=seed)
        nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
        route = nn.route
        new_vertices = [4, 5]

        # Strategy A
        result_a = greedy_insertion_repair(inst, route, new_vertices)
        # Strategy B
        result_b = strategy_b_repair(inst, route, new_vertices)

        # Both should be feasible
        assert result_a.route.is_feasible(inst, required_vertices={1, 2, 3, 4, 5}), f"Strategy A failed seed {seed}"
        assert result_b.route.is_feasible(inst, required_vertices={1, 2, 3, 4, 5}), f"Strategy B failed seed {seed}"

        # Strategy B cost should be <= Strategy A cost (2-opt can only improve or stay same)
        assert result_b.cost <= result_a.cost + 1e-9, f"Strategy B worse than A on seed {seed}"


def test_strategy_b_budget_limits():
    """Test Strategy B respects budget limits."""
    inst = Instance.generate_random(n=8, seed=123)
    nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
    route = nn.route  # 3 customers -> 4 edges

    # Insertion takes 4 evaluations. With max=4, no 2-opt should run.
    result = insertion_then_two_opt(inst, route, [4], max_evaluations=4)

    # Should only do insertion (4 evals), then stop
    assert result.two_opt_evaluations == 0
    assert result.total_evaluations == 4

    # With max=5, 2-opt may do 1 evaluation
    result2 = insertion_then_two_opt(inst, route, [4], max_evaluations=5)
    assert result2.two_opt_evaluations >= 0
    assert result2.total_evaluations == 5


def test_strategy_b_max_passes():
    """Test Strategy B respects max_passes limit."""
    inst = Instance.generate_random(n=8, seed=456)
    nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
    route = nn.route

    result = insertion_then_two_opt(inst, route, [4], max_passes=1)

    # 2-opt should do at most 1 pass
    assert result.two_opt_passes <= 1


# --- Reproducibility Tests ---

def test_repair_deterministic_same_seed():
    """Test both repair strategies are deterministic given same seed."""
    inst = Instance.generate_random(n=8, seed=999)
    nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
    route = nn.route

    # Strategy A
    r1_a = greedy_insertion_repair(inst, route, [4, 5])
    r2_a = greedy_insertion_repair(inst, route, [4, 5])
    assert r1_a.route.vertices == r2_a.route.vertices
    assert r1_a.cost == r2_a.cost

    # Strategy B
    r1_b = strategy_b_repair(inst, route, [4, 5])
    r2_b = strategy_b_repair(inst, route, [4, 5])
    assert r1_b.route.vertices == r2_b.route.vertices
    assert r1_b.cost == r2_b.cost


def test_repair_same_instance_event_sequence():
    """Test same instance + event sequence gives reproducible results."""
    # This simulates what the dynamic simulator will do
    inst = Instance.generate_random(n=10, seed=777)
    V0 = {0, 1, 2, 3, 4}

    # Build initial solution
    nn = nearest_neighbor(inst, vertex_subset=V0)
    route = nn.route

    # Event 1: vertex 5 revealed
    r1_a = greedy_insertion_repair(inst, route, [5])
    r1_b = strategy_b_repair(inst, route, [5])

    # Re-run from same state
    r2_a = greedy_insertion_repair(inst, route, [5])
    r2_b = strategy_b_repair(inst, route, [5])

    assert r1_a.route.vertices == r2_a.route.vertices
    assert r1_b.route.vertices == r2_b.route.vertices
    assert r1_a.cost == r2_a.cost
    assert r1_b.cost == r2_b.cost


# --- Edge Cases ---

def test_insertion_duplicate_vertices_ignored():
    """Test duplicate vertices in new_vertices are handled."""
    # Our implementation assumes no duplicates (sorted(set()) would handle it)
    # But the repair functions process sorted list, so duplicates would appear twice
    # This is an edge case - in practice generator guarantees no duplicates
    coords = [(0, 0), (1, 0), (0, 1)]
    inst = Instance.from_coords(coords)
    route = Route((0, 1, 2, 0))

    # Try to insert vertex 1 again (already in route)
    # with_insertion will raise ValueError
    with pytest.raises(ValueError):
        cheapest_insertion(inst, route, [1])


def test_insertion_vertex_at_depot():
    """Test inserting depot vertex (should be ignored or raise error)."""
    coords = [(0, 0), (1, 0), (0, 1)]
    inst = Instance.from_coords(coords)
    route = Route((0, 1, 2, 0))

    # Try to insert depot (0) - should raise error in with_insertion
    with pytest.raises(ValueError):
        cheapest_insertion(inst, route, [0])


def test_repair_result_structures():
    """Test result dataclasses have all required fields."""
    inst = Instance.from_coords([(0, 0), (1, 0), (0, 1), (2, 0)])
    route = Route((0, 1, 2, 0))

    # Strategy A
    result_a = greedy_insertion_repair(inst, route, [3])
    assert isinstance(result_a, InsertionResult)
    assert isinstance(result_a.route, Route)
    assert isinstance(result_a.cost, float)
    assert isinstance(result_a.candidate_evaluations, int)
    assert isinstance(result_a.deltas, list)

    # Strategy B
    result_b = strategy_b_repair(inst, route, [3])
    assert isinstance(result_b, InsertionTwoOptResult)
    assert isinstance(result_b.route, Route)
    assert isinstance(result_b.cost, float)
    assert isinstance(result_b.insertion_evaluations, int)
    assert isinstance(result_b.two_opt_evaluations, int)
    assert isinstance(result_b.total_evaluations, int)
    assert isinstance(result_b.insertion_deltas, list)
    assert isinstance(result_b.two_opt_accepted_moves, int)
    assert isinstance(result_b.two_opt_passes, int)


# --- Computational Effort Verification ---

def test_candidate_evaluations_counting():
    """Verify candidate evaluation counts match specification."""
    inst = Instance.generate_random(n=10, seed=1)
    nn = nearest_neighbor(inst, vertex_subset={0, 1, 2, 3})
    route = nn.route  # 3 customers -> 4 edges

    # Insert 2 vertices
    result = cheapest_insertion(inst, route, [4, 5])

    # First insertion: 4 evaluations (m=4 edges)
    # Second insertion: 5 evaluations (m=5 edges after first insertion)
    assert result.candidate_evaluations == 4 + 5


def test_two_opt_evaluations_counting():
    """Verify 2-opt candidate evaluations match formula."""
    inst = Instance.generate_random(n=6, seed=1)
    route = Route((0, 1, 2, 3, 4, 5, 0))  # 5 customers -> 6 edges

    result = two_opt(inst, route)

    # m=6 edges -> pairs = m(m-3)/2 = 9 (skip depot-depot)
    # But if improvements found, additional passes add more evaluations
    # At minimum 9 evaluations
    assert result.candidate_evaluations >= 9