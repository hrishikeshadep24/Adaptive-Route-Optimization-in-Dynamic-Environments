"""State Feature Extraction for Adaptive Route Optimization.

Extracts decision-time state features from the dynamic routing state without
any future information leakage.
References: RESEARCH_SPEC.md (Dynamic State, Frozen-Prefix), OPEN_QUESTIONS.md (#13).
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Optional
import math

from adaptive_route_optimization.simulation.state import DynamicState


@dataclass(frozen=True)
class StateFeatures:
    r"""State features available at dynamic event decision time t.

    All features are derived strictly from information observable at step t:
    - No future dynamic events Δ_{t+1}, ..., Δ_T are accessed.
    - No future strategy outcomes or offline oracle solutions are accessed.

    Attributes:
        total_vertices: Total customer vertices n in full problem instance.
        known_vertices_count: |V_t|, customer vertices currently revealed.
        frozen_prefix_length: f_t, number of customer vertices already committed.
        uncommitted_count: |S_t| - f_t - 2, uncommitted customer vertices in suffix.
        event_size: |Δ_t|, number of newly revealed customer vertices in this event.
        revealed_ratio: (|V_t| - 1) / n ∈ [0, 1], fraction of all customers known so far.
        uncommitted_ratio: uncommitted_count / max(1, known_vertices_count).
        initial_dynamicity: (n - |V_0 \ {0}|) / n, overall dynamicity α of the instance.
        current_cost: C(S_t), total Euclidean length of current tour.
        estimated_2opt_evals: Expected candidate evaluations for 1 full pass of 2-opt
                              on the updated uncommitted suffix: m*(m-3)/2.
        remaining_eval_budget: Candidate evaluations remaining under configured budget.
    """
    total_vertices: int
    known_vertices_count: int
    frozen_prefix_length: int
    uncommitted_count: int
    event_size: int
    revealed_ratio: float
    uncommitted_ratio: float
    initial_dynamicity: float
    current_cost: float
    estimated_2opt_evals: int
    remaining_eval_budget: Optional[int] = None
    estimated_insertion_evals: int = 0
    estimated_destroy_repair_evals: int = 0
    recent_cost_change: float = 0.0
    relative_cost_change: float = 0.0
    burst_arrival_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_features(
    state: DynamicState,
    new_vertices: frozenset[int],
    total_vertices: int,
    initial_known_count: int,
    remaining_eval_budget: Optional[int] = None,
    previous_cost: Optional[float] = None,
) -> StateFeatures:
    r"""Extract observable state features at decision time t.

    Complexity: O(1) time and space.

    Args:
        state: Current DynamicState at step t.
        new_vertices: Newly revealed customer vertices Δ_t.
        total_vertices: Problem instance total customers n.
        initial_known_count: |V_0 \ {0}|, customers known at t=0.
        remaining_eval_budget: Optional remaining candidate evaluation budget.
        previous_cost: Optional route cost from step t-1 to compute cost change.

    Returns:
        StateFeatures dataclass populated with decision-time features.
    """
    # Number of customers currently known (excluding depot 0)
    known_cust = len(state.known_vertices) - 1
    frozen_len = state.frozen_prefix_length
    event_sz = len(new_vertices)

    # Total customers known after this event arrives
    updated_known_cust = known_cust + event_sz
    revealed_ratio = float(min(1.0, max(0.0, updated_known_cust / max(1, total_vertices))))

    # Uncommitted customer vertices in current tour suffix
    # Current route has (f + 1) frozen vertices (0 + f customers) and return depot 0
    # Customer vertices in uncommitted suffix = known_cust - frozen_len
    uncommitted_cust = max(0, known_cust - frozen_len)
    uncommitted_ratio = float(uncommitted_cust / max(1, known_cust))

    # Overall problem dynamicity α = (n - initial_known) / n
    alpha = float(min(1.0, max(0.0, (total_vertices - initial_known_count) / max(1, total_vertices))))

    # Current tour cost
    current_cost = float(state.current_route.cost(state.instance))

    # Suffix length after inserting new vertices:
    # Suffix includes: last frozen vertex p_f, uncommitted customers, new vertices, and return depot 0
    # Total edges in suffix = uncommitted_cust + event_sz + 1
    # For a path of length m edges, candidate 2-opt edge pairs in 1 pass ≈ m*(m-3)/2
    m = uncommitted_cust + event_sz + 1
    estimated_2opt_evals = max(0, (m * (m - 3)) // 2) if m >= 4 else 0

    # Insertion candidate evaluations estimation
    k = max(0, event_sz)
    est_ins = k * uncommitted_cust + (k * (k + 1)) // 2 if k > 0 else 0

    # Destroy-and-Repair candidate evaluations estimation (1 pass cheapest repair)
    m_new = uncommitted_cust + k
    if m_new >= 2:
        q = max(1, int(m_new * 0.25))
        q = min(q, m_new)
        m_part = max(1, m_new - q)
        # Edges in partial suffix = m_part + 1
        e_repair = q * (m_part + 1) + (q * (q - 1)) // 2
        estimated_destroy_repair_evals = est_ins + e_repair
    else:
        estimated_destroy_repair_evals = est_ins

    # Dynamic burst arrival ratio
    burst_arrival_ratio = float(k / max(1, m_new))

    # Cost changes
    recent_cost_change = 0.0
    relative_cost_change = 0.0
    if previous_cost is not None:
        recent_cost_change = float(current_cost - previous_cost)
        if previous_cost > 1e-6:
            relative_cost_change = float(recent_cost_change / previous_cost)

    return StateFeatures(
        total_vertices=total_vertices,
        known_vertices_count=updated_known_cust,
        frozen_prefix_length=frozen_len,
        uncommitted_count=uncommitted_cust,
        event_size=event_sz,
        revealed_ratio=revealed_ratio,
        uncommitted_ratio=uncommitted_ratio,
        initial_dynamicity=alpha,
        current_cost=current_cost,
        estimated_2opt_evals=estimated_2opt_evals,
        remaining_eval_budget=remaining_eval_budget,
        estimated_insertion_evals=est_ins,
        estimated_destroy_repair_evals=estimated_destroy_repair_evals,
        recent_cost_change=recent_cost_change,
        relative_cost_change=relative_cost_change,
        burst_arrival_ratio=burst_arrival_ratio,
    )
