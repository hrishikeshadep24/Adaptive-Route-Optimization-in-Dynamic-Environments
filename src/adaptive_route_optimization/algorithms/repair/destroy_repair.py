"""Strategy C: Suffix Destroy-and-Repair (Large Neighborhood Search).

Implements parameter-controlled destroy operators (Random removal, Shaw removal)
and repair operators (Cheapest insertion, Regret-2 insertion) operating strictly
on the uncommitted suffix under the frozen-prefix constraint.

References: RESEARCH_SPEC.md (Strategy C), MASTER_BLUEPRINT.md (Phase 4 / Strategy C).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional, Sequence
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route


class DestroyOperator(str, Enum):
    """Destroy operator for uncommitted suffix vertices."""
    RANDOM = "random"
    SHAW = "shaw"


class RepairOperator(str, Enum):
    """Repair operator for re-inserting unassigned vertices."""
    CHEAPEST = "cheapest"
    REGRET_2 = "regret_2"


@dataclass(frozen=True)
class DestroyRepairConfig:
    """Hyperparameters and configuration for Strategy C (Destroy-and-Repair).

    Attributes:
        destroy_operator: Operator for vertex removal (RANDOM or SHAW).
        repair_operator: Operator for vertex re-insertion (CHEAPEST or REGRET_2).
        destroy_fraction: Fraction of uncommitted suffix customers to remove per pass.
        min_destroy: Minimum number of vertices to remove (default 1).
        max_destroy: Optional maximum cap on number of vertices to remove.
        max_iterations: Maximum destroy-and-repair improvement iterations.
        shaw_distance_weight: Weight phi for spatial distance in Shaw relatedness.
        shaw_position_weight: Weight chi for route position in Shaw relatedness.
        seed: Random seed for deterministic reproducibility.
    """
    destroy_operator: DestroyOperator = DestroyOperator.RANDOM
    repair_operator: RepairOperator = RepairOperator.REGRET_2
    destroy_fraction: float = 0.25
    min_destroy: int = 1
    max_destroy: Optional[int] = None
    max_iterations: int = 10
    shaw_distance_weight: float = 0.75
    shaw_position_weight: float = 0.25
    seed: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "destroy_operator": self.destroy_operator.value,
            "repair_operator": self.repair_operator.value,
            "destroy_fraction": self.destroy_fraction,
            "min_destroy": self.min_destroy,
            "max_destroy": self.max_destroy,
            "max_iterations": self.max_iterations,
            "shaw_distance_weight": self.shaw_distance_weight,
            "shaw_position_weight": self.shaw_position_weight,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DestroyRepairConfig:
        return cls(
            destroy_operator=DestroyOperator(data.get("destroy_operator", DestroyOperator.RANDOM.value)),
            repair_operator=RepairOperator(data.get("repair_operator", RepairOperator.REGRET_2.value)),
            destroy_fraction=float(data.get("destroy_fraction", 0.25)),
            min_destroy=int(data.get("min_destroy", 1)),
            max_destroy=data.get("max_destroy"),
            max_iterations=int(data.get("max_iterations", 10)),
            shaw_distance_weight=float(data.get("shaw_distance_weight", 0.75)),
            shaw_position_weight=float(data.get("shaw_position_weight", 0.25)),
            seed=data.get("seed"),
        )


@dataclass(frozen=True)
class DestroyRepairResult:
    """Result of Strategy C Destroy-and-Repair execution.

    Attributes:
        route: Final reconstructed full route.
        cost: Exact Euclidean cost of final route.
        initial_insertion_evaluations: Candidate evaluations during initial event insertion.
        destroy_repair_evaluations: Candidate evaluations during destroy-and-repair passes.
        total_evaluations: Total candidate evaluations (initial + optimization).
        iterations_completed: Number of completed destroy-and-repair iterations.
        accepted_improvements: Number of improving moves accepted.
        destroyed_counts: List of vertex counts removed per iteration.
    """
    route: Route
    cost: float
    initial_insertion_evaluations: int
    destroy_repair_evaluations: int
    total_evaluations: int
    iterations_completed: int
    accepted_improvements: int
    destroyed_counts: list[int]


def compute_suffix_cost(instance: Instance, suffix_vertices: Sequence[int]) -> float:
    """Calculate Euclidean path cost along a suffix path."""
    total = 0.0
    for i in range(len(suffix_vertices) - 1):
        total += instance.cost(suffix_vertices[i], suffix_vertices[i + 1])
    return total


# ---------------------------------------------------------------------------
# Destroy Operators
# ---------------------------------------------------------------------------

def destroy_random(
    suffix_vertices: Sequence[int],
    q: int,
    rng: np.random.Generator,
) -> tuple[tuple[int, ...], list[int]]:
    """Remove q randomly selected customer vertices from uncommitted suffix.

    Neither the frozen boundary vertex (index 0) nor the final depot (index -1)
    may ever be removed.

    Args:
        suffix_vertices: Suffix path (p_f, u_1, ..., u_k, 0).
        q: Number of customer vertices to remove.
        rng: Seeded random number generator.

    Returns:
        Tuple of (partial_suffix, removed_vertices).
    """
    if len(suffix_vertices) <= 2:
        return tuple(suffix_vertices), []

    # Removable customer vertices: indices 1 to len - 2
    removable_indices = list(range(1, len(suffix_vertices) - 1))
    q_actual = min(q, len(removable_indices))
    if q_actual <= 0:
        return tuple(suffix_vertices), []

    chosen_indices = set(rng.choice(removable_indices, size=q_actual, replace=False))
    
    partial_suffix = [v for idx, v in enumerate(suffix_vertices) if idx not in chosen_indices]
    removed_vertices = [suffix_vertices[idx] for idx in sorted(chosen_indices)]

    return tuple(partial_suffix), removed_vertices


def destroy_shaw(
    instance: Instance,
    suffix_vertices: Sequence[int],
    q: int,
    config: DestroyRepairConfig,
    rng: np.random.Generator,
) -> tuple[tuple[int, ...], list[int]]:
    """Remove q related customer vertices using Shaw's relatedness measure.

    Relatedness combines spatial Euclidean proximity and sequence position similarity:
    R(i, j) = phi * (c(i,j) / D_max) + chi * (|pos(i) - pos(j)| / |U|)

    Neither the frozen boundary vertex (index 0) nor the final depot (index -1)
    may ever be removed.

    Args:
        instance: Problem instance.
        suffix_vertices: Suffix path (p_f, u_1, ..., u_k, 0).
        q: Number of customer vertices to remove.
        config: Configuration containing weights phi and chi.
        rng: Seeded random number generator.

    Returns:
        Tuple of (partial_suffix, removed_vertices).
    """
    if len(suffix_vertices) <= 2:
        return tuple(suffix_vertices), []

    # Removable customers (excluding p_f and return depot 0)
    customers = list(suffix_vertices[1:-1])
    n_cust = len(customers)
    q_actual = min(q, n_cust)
    if q_actual <= 0:
        return tuple(suffix_vertices), []

    # Compute max pairwise distance among uncommitted customers for normalization
    d_max = 1.0
    for i in range(n_cust):
        for j in range(i + 1, n_cust):
            d = instance.cost(customers[i], customers[j])
            if d > d_max:
                d_max = d

    # Pick initial seed vertex uniformly at random from removable customers
    seed_idx = int(rng.integers(0, n_cust))
    seed_vertex = customers[seed_idx]

    removed_set = {seed_vertex}
    removed_order = [seed_vertex]

    phi = config.shaw_distance_weight
    chi = config.shaw_position_weight

    # Mapping from vertex to initial position in uncommitted customer sequence
    pos_map = {v: idx for idx, v in enumerate(customers)}

    while len(removed_order) < q_actual:
        last_v = removed_order[-1]
        last_pos = pos_map[last_v]

        candidates = [v for v in customers if v not in removed_set]
        if not candidates:
            break

        # Calculate relatedness to last_v for all remaining candidates
        scores = []
        for cand in candidates:
            dist_term = instance.cost(last_v, cand) / d_max
            pos_term = abs(last_pos - pos_map[cand]) / max(1, n_cust)
            rel_score = phi * dist_term + chi * pos_term
            scores.append((rel_score, cand))

        # Deterministic tie-breaking: lowest score first, then lowest vertex index
        scores.sort(key=lambda item: (item[0], item[1]))
        selected_v = scores[0][1]

        removed_set.add(selected_v)
        removed_order.append(selected_v)

    partial_suffix = [v for v in suffix_vertices if v not in removed_set]
    # Return removed vertices sorted by index for deterministic re-insertion order
    return tuple(partial_suffix), sorted(removed_order)


# ---------------------------------------------------------------------------
# Repair Operators
# ---------------------------------------------------------------------------

def repair_cheapest_suffix(
    instance: Instance,
    suffix_vertices: Sequence[int],
    unassigned_vertices: Sequence[int],
    max_evaluations: Optional[int] = None,
) -> tuple[tuple[int, ...], int]:
    """Insert unassigned vertices one by one at cheapest incremental cost positions.

    Candidate evaluations count: up to m evaluations per unassigned vertex,
    where m is the current number of edges in the suffix path.

    Hard budget enforcement:
    If max_evaluations is specified, candidate evaluations will strictly not exceed
    max_evaluations.
    - If remaining evaluation budget is 0, vertices are inserted at a documented safe
      fallback position (immediately before return depot 0) incurring 0 evaluations.
    - If remaining evaluation budget is 0 < B < m, the first B candidate positions
      are evaluated and the best evaluated position is selected.

    Args:
        instance: Problem instance.
        suffix_vertices: Suffix path (starts at p_f, ends at 0).
        unassigned_vertices: Vertices to insert.
        max_evaluations: Optional hard budget cap on candidate evaluations.

    Returns:
        Tuple of (repaired_suffix_vertices, total_candidate_evaluations).
    """
    current_suffix = list(suffix_vertices)
    total_evals = 0

    sorted_unassigned = sorted(unassigned_vertices)

    for v in sorted_unassigned:
        m = len(current_suffix) - 1
        if m < 1:
            current_suffix.append(v)
            continue

        if max_evaluations is not None:
            remaining_evals = max(0, max_evaluations - total_evals)
            evals_allowed = min(m, remaining_evals)
        else:
            evals_allowed = m

        if evals_allowed == 0:
            # Documented safe fallback: insert before depot at position len(current_suffix) - 1
            # with 0 evaluations, strictly guaranteeing feasibility and budget limit
            current_suffix.insert(len(current_suffix) - 1, v)
            continue

        best_delta = float("inf")
        best_pos = -1

        for pos in range(evals_allowed):
            u = current_suffix[pos]
            w = current_suffix[pos + 1]
            delta = instance.cost(u, v) + instance.cost(v, w) - instance.cost(u, w)
            total_evals += 1

            if delta < best_delta:
                best_delta = delta
                best_pos = pos + 1

        current_suffix.insert(best_pos, v)

    return tuple(current_suffix), total_evals


def repair_regret2_suffix(
    instance: Instance,
    suffix_vertices: Sequence[int],
    unassigned_vertices: Sequence[int],
    max_evaluations: Optional[int] = None,
) -> tuple[tuple[int, ...], int]:
    """Insert unassigned vertices using 2-regret heuristic.

    At each step:
    - For each unassigned vertex, evaluates all m insertion positions in suffix.
    - Determines best insertion cost delta_1 and second-best delta_2.
    - Computes 2-regret = delta_2 - delta_1 >= 0.
    - Selects vertex with maximal 2-regret and inserts it at its best position.
    - Tie-breaking: highest regret, then lowest delta_1, then lowest vertex index.

    Candidate evaluations count: exactly |unassigned| * m evaluations per step
    when unbounded.

    Hard budget enforcement:
    If max_evaluations is specified and remaining budget is insufficient for a full
    2-regret step (|pending| * m candidate evaluations), falls back to budget-capped
    cheapest insertion for the remaining vertices. If remaining budget is 0, places
    remaining vertices at the safe fallback position (before depot 0) with 0 evaluations.

    Args:
        instance: Problem instance.
        suffix_vertices: Suffix path (starts at p_f, ends at 0).
        unassigned_vertices: Vertices to insert.
        max_evaluations: Optional hard budget cap on candidate evaluations.

    Returns:
        Tuple of (repaired_suffix_vertices, total_candidate_evaluations).
    """
    current_suffix = list(suffix_vertices)
    pending = sorted(unassigned_vertices)
    total_evals = 0

    while pending:
        m = len(current_suffix) - 1
        if m < 1:
            for v in pending:
                current_suffix.append(v)
            break

        # Check if remaining budget can afford full Regret-2 step across all pending vertices
        if max_evaluations is not None:
            remaining_evals = max(0, max_evaluations - total_evals)
            req_evals_step = len(pending) * m
            if remaining_evals < req_evals_step:
                # Documented safe fallback: switch to budget-capped cheapest insertion
                fallback_suffix, fallback_evals = repair_cheapest_suffix(
                    instance=instance,
                    suffix_vertices=current_suffix,
                    unassigned_vertices=pending,
                    max_evaluations=remaining_evals,
                )
                total_evals += fallback_evals
                return fallback_suffix, total_evals

        best_overall_vertex = None
        best_overall_pos = -1
        max_regret = -float("inf")
        best_vertex_delta1 = float("inf")

        for v in pending:
            # Evaluate all m positions for vertex v
            pos_deltas = []
            for pos in range(m):
                u = current_suffix[pos]
                w = current_suffix[pos + 1]
                delta = instance.cost(u, v) + instance.cost(v, w) - instance.cost(u, w)
                total_evals += 1
                pos_deltas.append((delta, pos + 1))

            # Sort candidate positions by delta ascending
            pos_deltas.sort(key=lambda x: (x[0], x[1]))

            delta_1, pos_1 = pos_deltas[0]
            if len(pos_deltas) > 1:
                delta_2 = pos_deltas[1][0]
                regret = delta_2 - delta_1
            else:
                # Only 1 position available (e.g. edge p_f -> 0)
                regret = 0.0

            # Find vertex with maximal regret
            # Tie-breaking: higher regret, lower delta_1, lower vertex index
            is_better = False
            if regret > max_regret + 1e-9:
                is_better = True
            elif abs(regret - max_regret) <= 1e-9:
                if delta_1 < best_vertex_delta1 - 1e-9:
                    is_better = True
                elif abs(delta_1 - best_vertex_delta1) <= 1e-9:
                    if best_overall_vertex is None or v < best_overall_vertex:
                        is_better = True

            if is_better:
                max_regret = regret
                best_vertex_delta1 = delta_1
                best_overall_vertex = v
                best_overall_pos = pos_1

        # Apply insertion for selected vertex
        current_suffix.insert(best_overall_pos, best_overall_vertex)
        pending.remove(best_overall_vertex)

    return tuple(current_suffix), total_evals


def calculate_repair_evaluations(num_unassigned: int, suffix_length: int, operator: RepairOperator) -> int:
    """Calculate exact candidate evaluations needed to insert unassigned vertices into suffix."""
    # Suffix of length L vertices has L - 1 edges.
    # At step i (i from 0 to num_unassigned - 1), suffix has (L - 1 + i) edges.
    total = 0
    m0 = suffix_length - 1
    if operator == RepairOperator.CHEAPEST:
        # Each vertex evaluates the current number of edges once
        for i in range(num_unassigned):
            total += (m0 + i)
    else:  # REGRET_2
        # At each step, all remaining (num_unassigned - i) vertices evaluate all (m0 + i) edges
        for i in range(num_unassigned):
            remaining_v = num_unassigned - i
            edges = m0 + i
            total += remaining_v * edges
    return total


# ---------------------------------------------------------------------------
# Suffix Destroy-and-Repair Engine
# ---------------------------------------------------------------------------

def destroy_and_repair_suffix(
    instance: Instance,
    suffix_vertices: Sequence[int],
    new_vertices: Sequence[int],
    config: Optional[DestroyRepairConfig] = None,
    max_evaluations: Optional[int] = None,
) -> tuple[tuple[int, ...], int, int, int, int, list[int]]:
    """Execute Suffix Destroy-and-Repair under frozen-prefix constraint.

    Workflow:
    1. Initial Repair: Inserts newly revealed vertices into uncommitted suffix
       using configured repair operator (Cheapest or Regret-2).
    2. Budget Check: If remaining candidate evaluations are insufficient for an
       additional pass, returns the feasible initially repaired suffix.
    3. Destroy-and-Repair Iterations:
       - Checks budget feasibility before every removal pass.
       - Removes q customer vertices using Random or Shaw removal.
       - Re-inserts vertices using configured repair operator.
       - Accepts strictly improving moves (first-improvement / descent LNS).

    Args:
        instance: Problem instance.
        suffix_vertices: Current uncommitted suffix path (p_f, u_1, ..., u_k, 0).
        new_vertices: Newly revealed vertices (Delta_t).
        config: Hyperparameters for destroy-and-repair.
        max_evaluations: Optional hard upper bound on candidate evaluations.

    Returns:
        Tuple of (
            best_suffix_vertices,
            initial_insertion_evaluations,
            destroy_repair_evaluations,
            total_evaluations,
            accepted_improvements,
            destroyed_counts
        ).
    """
    cfg = config or DestroyRepairConfig()
    rng = np.random.default_rng(cfg.seed)

    # -----------------------------------------------------------------------
    # Step 1: Initial Insertion of newly arrived vertices
    # -----------------------------------------------------------------------
    sorted_new = sorted(new_vertices)
    if sorted_new:
        if cfg.repair_operator == RepairOperator.CHEAPEST:
            current_suffix, init_evals = repair_cheapest_suffix(
                instance, suffix_vertices, sorted_new, max_evaluations=max_evaluations
            )
        else:
            current_suffix, init_evals = repair_regret2_suffix(
                instance, suffix_vertices, sorted_new, max_evaluations=max_evaluations
            )
    else:
        current_suffix = tuple(suffix_vertices)
        init_evals = 0

    best_suffix = current_suffix
    best_cost = compute_suffix_cost(instance, best_suffix)

    # -----------------------------------------------------------------------
    # Step 2: Check remaining budget for destroy-and-repair passes
    # -----------------------------------------------------------------------
    remaining_budget = None
    if max_evaluations is not None:
        remaining_budget = max(0, max_evaluations - init_evals)
        if remaining_budget == 0:
            return best_suffix, init_evals, 0, init_evals, 0, []

    # -----------------------------------------------------------------------
    # Step 3: Destroy-and-Repair Improvement Loop
    # -----------------------------------------------------------------------
    dr_evals = 0
    accepted_moves = 0
    destroyed_counts: list[int] = []

    for _ in range(cfg.max_iterations):
        # Uncommitted customer vertices (excluding p_f at 0 and return depot at -1)
        n_uncommitted = len(current_suffix) - 2
        if n_uncommitted < 2:
            # Need at least 2 removable vertices to perform a non-trivial rearrangement
            break

        # Determine number of vertices q to destroy
        q = max(cfg.min_destroy, int(n_uncommitted * cfg.destroy_fraction))
        q = min(q, n_uncommitted)
        if cfg.max_destroy is not None:
            q = min(q, cfg.max_destroy)
        if q < 1:
            break

        # Exact evaluations required for re-inserting q vertices into (len(current_suffix) - q) suffix
        partial_suffix_len = len(current_suffix) - q
        req_evals = calculate_repair_evaluations(q, partial_suffix_len, cfg.repair_operator)

        # Budget Guard: verify that candidate evaluations will NOT exceed max_evaluations
        if remaining_budget is not None and (dr_evals + req_evals) > remaining_budget:
            # Budget cannot afford another complete destroy-and-repair iteration
            break

        # Destroy phase
        if cfg.destroy_operator == DestroyOperator.RANDOM:
            partial_suffix, removed_vertices = destroy_random(current_suffix, q, rng)
        else:  # SHAW
            partial_suffix, removed_vertices = destroy_shaw(instance, current_suffix, q, cfg, rng)

        if not removed_vertices:
            break

        # Repair phase
        pass_budget = None
        if remaining_budget is not None:
            pass_budget = remaining_budget - dr_evals

        if cfg.repair_operator == RepairOperator.CHEAPEST:
            repaired_suffix, pass_evals = repair_cheapest_suffix(
                instance, partial_suffix, removed_vertices, max_evaluations=pass_budget
            )
        else:  # REGRET_2
            repaired_suffix, pass_evals = repair_regret2_suffix(
                instance, partial_suffix, removed_vertices, max_evaluations=pass_budget
            )

        dr_evals += pass_evals
        destroyed_counts.append(len(removed_vertices))

        # Evaluate move
        repaired_cost = compute_suffix_cost(instance, repaired_suffix)
        current_cost = compute_suffix_cost(instance, current_suffix)

        if repaired_cost < current_cost - 1e-9:
            current_suffix = repaired_suffix
            accepted_moves += 1

            if repaired_cost < best_cost - 1e-9:
                best_suffix = repaired_suffix
                best_cost = repaired_cost

    total_evals = init_evals + dr_evals
    return (
        best_suffix,
        init_evals,
        dr_evals,
        total_evals,
        accepted_moves,
        destroyed_counts,
    )


def strategy_c_repair(
    instance: Instance,
    current_route: Route,
    frozen_prefix_length: int,
    new_vertices: Sequence[int],
    config: Optional[DestroyRepairConfig] = None,
    max_evaluations: Optional[int] = None,
) -> DestroyRepairResult:
    """Strategy C entry point: Suffix Destroy-and-Repair.

    Args:
        instance: Problem instance.
        current_route: Current route covering known vertices.
        frozen_prefix_length: f_t, number of committed customer vertices.
        new_vertices: Newly revealed customer vertices.
        config: Optional configuration for destroy and repair operators.
        max_evaluations: Optional candidate evaluation budget limit.

    Returns:
        DestroyRepairResult with updated route and complete instrumentation.
    """
    # Extract uncommitted suffix path: starts at p_f (last frozen vertex)
    suffix_vertices = current_route.vertices[frozen_prefix_length:]
    frozen_prefix = current_route.vertices[: frozen_prefix_length + 1]

    (
        updated_suffix,
        init_evals,
        dr_evals,
        total_evals,
        accepted_moves,
        destroyed_counts,
    ) = destroy_and_repair_suffix(
        instance=instance,
        suffix_vertices=suffix_vertices,
        new_vertices=new_vertices,
        config=config,
        max_evaluations=max_evaluations,
    )

    # Reconstruct full route: frozen_prefix + updated_suffix[1:]
    suffix_list = list(updated_suffix)
    if suffix_list and suffix_list[0] == frozen_prefix[-1]:
        suffix_list = suffix_list[1:]
    full_vertices = tuple(list(frozen_prefix) + suffix_list)
    final_route = Route(full_vertices)

    return DestroyRepairResult(
        route=final_route,
        cost=final_route.cost(instance),
        initial_insertion_evaluations=init_evals,
        destroy_repair_evaluations=dr_evals,
        total_evaluations=total_evals,
        iterations_completed=len(destroyed_counts),
        accepted_improvements=accepted_moves,
        destroyed_counts=destroyed_counts,
    )
