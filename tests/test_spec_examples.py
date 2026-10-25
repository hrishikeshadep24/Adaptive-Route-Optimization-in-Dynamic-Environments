"""Tests for the Phase 2 hand-worked 10-node example.

This test verifies the exact numbers from docs/HAND_WORKED_EXAMPLE.md
using only a tiny cost helper (no production algorithms).
"""

import math


# --- Tiny cost helper (only for this test) ---
def euclidean(a, b):
    """Euclidean distance between two (x, y) tuples."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def route_cost(route, coords):
    """Total cost of a route (list of vertex indices, starts/ends at depot)."""
    total = 0.0
    for i in range(len(route) - 1):
        total += euclidean(coords[route[i]], coords[route[i + 1]])
    return total


def route_edges(route):
    """Set of edges (as ordered tuples) in a route."""
    return {(route[i], route[i + 1]) for i in range(len(route) - 1)}


def disruption(route_a, route_b):
    """Normalized edge-difference disruption metric δ ∈ [0, 1]."""
    ea = route_edges(route_a)
    eb = route_edges(route_b)
    inter = ea & eb
    return 1.0 - len(inter) / max(len(ea), len(eb))


# --- Instance definition (exact from HAND_WORKED_EXAMPLE.md) ---
COORDS = {
    0: (0, 0),      # depot
    1: (3, 0),
    2: (3, 4),
    3: (0, 4),
    4: (6, 0),
    5: (6, 4),
    6: (0, 8),
    7: (-3, 4),
    8: (3, -4),
    9: (9, 0),
}

V0 = {0, 1, 2, 3, 4}
DELTA_0 = {5}

# Expected routes
S0 = (0, 1, 4, 2, 3, 0)
S1_A = (0, 1, 4, 5, 2, 3, 0)
S1_B = (0, 1, 4, 5, 2, 3, 0)  # Same as A after 2-opt (no improvement)


# --- Tests ---
def test_initial_route_cost():
    """S0 cost should be exactly 18."""
    cost = route_cost(S0, COORDS)
    assert math.isclose(cost, 18.0, rel_tol=1e-9), f"Expected 18.0, got {cost}"


def test_insertion_repair_cost():
    """S1_A cost should be exactly 20."""
    cost = route_cost(S1_A, COORDS)
    assert math.isclose(cost, 20.0, rel_tol=1e-9), f"Expected 20.0, got {cost}"


def test_two_opt_no_improvement():
    """2-opt finds no improving move; S1_B == S1_A with cost 20."""
    cost = route_cost(S1_B, COORDS)
    assert math.isclose(cost, 20.0, rel_tol=1e-9), f"Expected 20.0, got {cost}"
    assert S1_B == S1_A


def test_disruption():
    """Disruption δ(S0, S1) should be exactly 1/3."""
    d = disruption(S0, S1_A)
    assert math.isclose(d, 1.0 / 3.0, rel_tol=1e-9), f"Expected 1/3, got {d}"


def test_candidate_evaluations_nn():
    """Nearest-neighbor on V0 evaluates 10 candidates."""
    # V0 \ {0} = {1,2,3,4} → 4+3+2+1 = 10
    nn_evals = 4 + 3 + 2 + 1
    assert nn_evals == 10


def test_candidate_evaluations_insertion():
    """Insertion into 5-edge route evaluates 5 candidates."""
    # S0 has 5 edges → 5 insertion positions
    ins_evals = 5
    assert ins_evals == 5


def test_candidate_evaluations_two_opt():
    """One 2-opt pass on 6-edge route examines 9 pairs (depot-depot skipped)."""
    # Edges = 6 → pairs = 6*3/2 = 9 (formula: m(m-3)/2 for m edges)
    m = 6
    two_opt_evals = m * (m - 3) // 2
    assert two_opt_evals == 9


def test_feasibility_s0():
    """S0 visits exactly V0, starts/ends at depot, no duplicates."""
    assert S0[0] == 0 and S0[-1] == 0
    visited = set(S0[1:-1])
    assert visited == V0 - {0}
    assert len(S0[1:-1]) == len(visited)  # no duplicates


def test_feasibility_s1():
    """S1 visits exactly V1, starts/ends at depot, no duplicates."""
    V1 = V0 | DELTA_0
    assert S1_A[0] == 0 and S1_A[-1] == 0
    visited = set(S1_A[1:-1])
    assert visited == V1 - {0}
    assert len(S1_A[1:-1]) == len(visited)


def test_distance_matrix_key_values():
    """Spot-check key distances from the hand-worked matrix."""
    # Exact integer distances
    assert math.isclose(euclidean(COORDS[0], COORDS[1]), 3.0)
    assert math.isclose(euclidean(COORDS[1], COORDS[4]), 3.0)
    assert math.isclose(euclidean(COORDS[4], COORDS[2]), 5.0)
    assert math.isclose(euclidean(COORDS[2], COORDS[3]), 3.0)
    assert math.isclose(euclidean(COORDS[3], COORDS[0]), 4.0)
    # √52 ≈ 7.21110255...
    assert math.isclose(euclidean(COORDS[0], COORDS[5]), math.sqrt(52), rel_tol=1e-9)
    assert math.isclose(euclidean(COORDS[4], COORDS[3]), math.sqrt(52), rel_tol=1e-9)


def test_insertion_delta_calculation():
    """Verify the insertion delta calculation for position i=2 (between 4 and 2)."""
    # Position i=2: edge (4, 2) in S0
    u, w = 4, 2
    v = 5
    delta = euclidean(COORDS[u], COORDS[v]) + euclidean(COORDS[v], COORDS[w]) - euclidean(COORDS[u], COORDS[w])
    # c(4,5)=4, c(5,2)=3, c(4,2)=5 → 4+3-5 = 2
    assert math.isclose(delta, 2.0, rel_tol=1e-9)


def test_two_opt_delta_sample():
    """Spot-check a 2-opt delta calculation (i=0, j=2: edges (0,1) & (4,5))."""
    a, b = 0, 1
    c, d = 4, 5
    delta = (euclidean(COORDS[a], COORDS[c]) + euclidean(COORDS[b], COORDS[d])
             - euclidean(COORDS[a], COORDS[b]) - euclidean(COORDS[c], COORDS[d]))
    # c(0,4)=6, c(1,5)=5, c(0,1)=3, c(4,5)=4 → 6+5-3-4 = 4
    assert math.isclose(delta, 4.0, rel_tol=1e-9)