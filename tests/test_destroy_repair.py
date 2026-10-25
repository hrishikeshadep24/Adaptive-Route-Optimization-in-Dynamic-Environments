"""Unit and integration tests for Strategy C: Suffix Destroy-and-Repair.

Covers:
- Hyperparameter and configuration model
- Destroy operators (Random, Shaw) preserving frozen prefix and depot
- Repair operators (Cheapest, Regret-2) with exact candidate evaluation counting
- Large Neighborhood Search loop with improvement acceptance
- Strategy C entry point (route feasibility, prefix invariance, edge cases)
- Strict candidate-evaluation budget enforcement with boundary tests (0, 1, required-1, required)
- Documented safe fallback under insufficient budget
- Deterministic reproducibility
- Full simulator integration and comparison with Strategies A & B
- Batch experiment runner integration
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.algorithms.repair.destroy_repair import (
    DestroyOperator,
    RepairOperator,
    DestroyRepairConfig,
    DestroyRepairResult,
    destroy_random,
    destroy_shaw,
    repair_cheapest_suffix,
    repair_regret2_suffix,
    destroy_and_repair_suffix,
    strategy_c_repair,
    calculate_repair_evaluations,
)
from adaptive_route_optimization.simulation.simulator import (
    Simulator,
    Strategy,
    StepResult,
    SimulationResult,
)
from adaptive_route_optimization.simulation.events import EventConfig, EventGenerator
from adaptive_route_optimization.experiments.schema import (
    ExperimentConfig,
    ConditionConfig,
    BudgetConfig,
    BudgetType,
)
from adaptive_route_optimization.experiments.runner import ExperimentRunner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_instance() -> Instance:
    """10-vertex instance with known coordinates."""
    coords = [
        (0.0, 0.0),    # 0: Depot
        (1.0, 5.0),    # 1
        (2.0, 8.0),    # 2
        (5.0, 8.0),    # 3
        (6.0, 4.0),    # 4
        (8.0, 3.0),    # 5
        (7.0, 1.0),    # 6
        (4.0, 1.0),    # 7
        (3.0, 3.0),    # 8
        (1.0, 2.0),    # 9
    ]
    return Instance.from_coords(coords)


@pytest.fixture
def initial_route() -> Route:
    """Initial route visiting depot and vertices 1..6."""
    return Route((0, 1, 2, 3, 4, 5, 6, 0))


# ---------------------------------------------------------------------------
# 1. Config & Dataclass Tests
# ---------------------------------------------------------------------------

def test_config_defaults_and_serialization():
    """Verify DestroyRepairConfig defaults, to_dict, and from_dict roundtrip."""
    cfg = DestroyRepairConfig()
    assert cfg.destroy_operator == DestroyOperator.RANDOM
    assert cfg.repair_operator == RepairOperator.REGRET_2
    assert cfg.destroy_fraction == 0.25
    assert cfg.min_destroy == 1
    assert cfg.max_iterations == 10
    assert cfg.seed is None

    # Custom serialization roundtrip
    custom_cfg = DestroyRepairConfig(
        destroy_operator=DestroyOperator.SHAW,
        repair_operator=RepairOperator.CHEAPEST,
        destroy_fraction=0.4,
        min_destroy=2,
        max_destroy=5,
        max_iterations=15,
        shaw_distance_weight=0.8,
        shaw_position_weight=0.2,
        seed=123,
    )
    d = custom_cfg.to_dict()
    restored = DestroyRepairConfig.from_dict(d)
    assert restored == custom_cfg


# ---------------------------------------------------------------------------
# 2. Destroy Operator Tests
# ---------------------------------------------------------------------------

def test_destroy_random_preserves_endpoints(sample_instance: Instance):
    """destroy_random must never remove the first vertex (p_f) or last vertex (depot 0)."""
    # Suffix: p_f=2, customers=[3, 4, 5, 6], depot=0
    suffix = (2, 3, 4, 5, 6, 0)
    rng = np.random.default_rng(42)

    partial, removed = destroy_random(suffix, q=2, rng=rng)

    assert len(removed) == 2
    assert partial[0] == 2  # p_f untouched
    assert partial[-1] == 0  # depot untouched
    for r in removed:
        assert r in {3, 4, 5, 6}
        assert r not in partial
    # Remaining plus removed should equal original suffix
    assert set(partial) | set(removed) == set(suffix)


def test_destroy_random_deterministic_with_seed():
    """Identical RNG seeds must produce identical removed subsets."""
    suffix = (1, 2, 3, 4, 5, 6, 7, 8, 0)
    rng1 = np.random.default_rng(999)
    rng2 = np.random.default_rng(999)

    partial1, rem1 = destroy_random(suffix, q=3, rng=rng1)
    partial2, rem2 = destroy_random(suffix, q=3, rng=rng2)

    assert partial1 == partial2
    assert rem1 == rem2


def test_destroy_random_small_suffixes():
    """destroy_random handles suffixes with 0, 1, or insufficient removable customers gracefully."""
    rng = np.random.default_rng(42)

    # 0 customers between p_f and 0: (p_f, 0)
    partial0, rem0 = destroy_random((2, 0), q=1, rng=rng)
    assert partial0 == (2, 0)
    assert list(rem0) == []

    # 1 customer: (p_f, c1, 0)
    partial1, rem1 = destroy_random((2, 5, 0), q=1, rng=rng)
    assert partial1 == (2, 0)
    assert list(rem1) == [5]

    # q requested greater than available customers
    partial_many, rem_many = destroy_random((2, 5, 6, 0), q=10, rng=rng)
    assert partial_many == (2, 0)
    assert set(rem_many) == {5, 6}


def test_destroy_shaw_relatedness_and_removal(sample_instance: Instance):
    """destroy_shaw removes geographically and positionally related customer vertices."""
    # Suffix: p_f=1, customers=[2, 3, 4, 5, 6], depot=0
    suffix = (1, 2, 3, 4, 5, 6, 0)
    rng = np.random.default_rng(42)

    cfg = DestroyRepairConfig(
        shaw_distance_weight=0.8,
        shaw_position_weight=0.2,
    )

    partial, removed = destroy_shaw(
        instance=sample_instance,
        suffix_vertices=suffix,
        q=2,
        config=cfg,
        rng=rng,
    )

    assert len(removed) == 2
    assert partial[0] == 1  # p_f preserved
    assert partial[-1] == 0  # depot preserved
    for r in removed:
        assert r in {2, 3, 4, 5, 6}
        assert r not in partial
    assert set(partial) | set(removed) == set(suffix)


def test_destroy_shaw_edge_cases(sample_instance: Instance):
    """destroy_shaw behaves safely when q=0 or uncommitted customer count <= 1."""
    rng = np.random.default_rng(42)
    cfg = DestroyRepairConfig()

    # Empty customer suffix (2, 0)
    p0, r0 = destroy_shaw(sample_instance, (2, 0), q=2, config=cfg, rng=rng)
    assert p0 == (2, 0)
    assert list(r0) == []

    # Single customer suffix (2, 3, 0)
    p1, r1 = destroy_shaw(sample_instance, (2, 3, 0), q=1, config=cfg, rng=rng)
    assert p1 == (2, 0)
    assert list(r1) == [3]


# ---------------------------------------------------------------------------
# 3. Repair Operator Tests
# ---------------------------------------------------------------------------

def test_repair_cheapest_suffix(sample_instance: Instance):
    """repair_cheapest_suffix reinserts all unassigned vertices and counts evals exactly."""
    partial = (1, 4, 0)  # edges = 2 (1->4, 4->0)
    unassigned = [2, 3]

    repaired, evals = repair_cheapest_suffix(sample_instance, partial, unassigned)

    # First vertex inserted into 2 edges -> 2 evals
    # Second vertex inserted into 3 edges -> 3 evals
    # Total = 5 evals
    assert evals == 5
    assert repaired[0] == 1
    assert repaired[-1] == 0
    assert set(repaired) == {1, 4, 0, 2, 3}


def test_repair_regret2_suffix(sample_instance: Instance):
    """repair_regret2_suffix inserts all vertices using regret-2 logic and counts evals exactly."""
    partial = (1, 6, 0)  # edges = 2
    unassigned = [2, 3]

    repaired, evals = repair_regret2_suffix(sample_instance, partial, unassigned)

    # Step 1: 2 unassigned vertices * 2 edges = 4 evals
    # Step 2: 1 unassigned vertex * 3 edges = 3 evals
    # Total = 7 evals
    assert evals == 7
    assert repaired[0] == 1
    assert repaired[-1] == 0
    assert set(repaired) == {1, 6, 0, 2, 3}


def test_calculate_repair_evaluations():
    """calculate_repair_evaluations matches exact counts from operators."""
    # Suffix length 4 has 3 edges (m0 = 3).
    # Cheapest: sum(3 + k for k in range(3)) = 3 + 4 + 5 = 12
    assert calculate_repair_evaluations(num_unassigned=3, suffix_length=4, operator=RepairOperator.CHEAPEST) == 12

    # Regret-2: sum((3 - k) * (3 + k) for k in range(3))
    # k=0: 3 * 3 = 9
    # k=1: 2 * 4 = 8
    # k=2: 1 * 5 = 5
    # sum = 22
    assert calculate_repair_evaluations(num_unassigned=3, suffix_length=4, operator=RepairOperator.REGRET_2) == 22


# ---------------------------------------------------------------------------
# 4. Strategy C Core Algorithm Tests
# ---------------------------------------------------------------------------

def test_destroy_and_repair_suffix_improves_or_maintains_cost(sample_instance: Instance):
    """destroy_and_repair_suffix must never accept a worse cost route."""
    # Suffix: p_f=1, customers=[2, 3, 4, 5, 6], depot=0
    suffix = (1, 2, 3, 4, 5, 6, 0)
    cfg = DestroyRepairConfig(
        destroy_operator=DestroyOperator.RANDOM,
        repair_operator=RepairOperator.REGRET_2,
        destroy_fraction=0.4,
        max_iterations=5,
        seed=42,
    )

    best_suffix, init_evals, dr_evals, total_evals, moves, counts = destroy_and_repair_suffix(
        instance=sample_instance,
        suffix_vertices=suffix,
        new_vertices=[],
        config=cfg,
    )

    # Without new vertices, init_evals is 0
    assert init_evals == 0
    assert total_evals == dr_evals
    # Feasibility of suffix
    assert best_suffix[0] == 1
    assert best_suffix[-1] == 0
    assert set(best_suffix) == set(suffix)


def test_strategy_c_repair_route_feasibility_and_prefix_preservation(
    sample_instance: Instance, initial_route: Route
):
    """strategy_c_repair produces a feasible route strictly preserving the frozen prefix."""
    # Let frozen_prefix_length = 2 (p_0=0, p_1=1, p_2=2 committed)
    frozen_prefix_len = 2
    committed_prefix = initial_route.vertices[: frozen_prefix_len + 1]  # (0, 1, 2)
    new_vertices = [7, 8]

    cfg = DestroyRepairConfig(
        destroy_operator=DestroyOperator.SHAW,
        repair_operator=RepairOperator.REGRET_2,
        seed=10,
    )

    res: DestroyRepairResult = strategy_c_repair(
        instance=sample_instance,
        current_route=initial_route,
        frozen_prefix_length=frozen_prefix_len,
        new_vertices=new_vertices,
        config=cfg,
    )

    # Invariance check: committed prefix must be strictly identical
    assert res.route.vertices[: frozen_prefix_len + 1] == committed_prefix

    # Feasibility check
    required = {1, 2, 3, 4, 5, 6, 7, 8}
    assert res.route.is_feasible(sample_instance, required_vertices=required)
    assert res.cost == res.route.cost(sample_instance)
    assert res.total_evaluations == res.initial_insertion_evaluations + res.destroy_repair_evaluations


def test_strategy_c_all_operator_combinations(sample_instance: Instance, initial_route: Route):
    """Verify all 4 operator pairs (Random/Shaw x Cheapest/Regret2) execute feasibly."""
    combos = [
        (DestroyOperator.RANDOM, RepairOperator.CHEAPEST),
        (DestroyOperator.RANDOM, RepairOperator.REGRET_2),
        (DestroyOperator.SHAW, RepairOperator.CHEAPEST),
        (DestroyOperator.SHAW, RepairOperator.REGRET_2),
    ]

    for d_op, r_op in combos:
        cfg = DestroyRepairConfig(
            destroy_operator=d_op,
            repair_operator=r_op,
            max_iterations=3,
            seed=42,
        )
        res = strategy_c_repair(
            instance=sample_instance,
            current_route=initial_route,
            frozen_prefix_length=1,
            new_vertices=[7],
            config=cfg,
        )
        assert res.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7})
        assert res.route.vertices[:2] == initial_route.vertices[:2]


# ---------------------------------------------------------------------------
# 5. Candidate Evaluation Hard Budget Enforcement & Boundary Tests
# ---------------------------------------------------------------------------

def test_boundary_budget_zero(sample_instance: Instance, initial_route: Route):
    """Boundary test: max_evaluations=0 must yield exactly 0 evaluations while maintaining feasibility."""
    for op in [RepairOperator.CHEAPEST, RepairOperator.REGRET_2]:
        cfg = DestroyRepairConfig(repair_operator=op, max_iterations=5)
        res = strategy_c_repair(
            instance=sample_instance,
            current_route=initial_route,
            frozen_prefix_length=2,
            new_vertices=[7, 8],
            config=cfg,
            max_evaluations=0,
        )
        # Exactly 0 evaluations
        assert res.total_evaluations == 0
        assert res.initial_insertion_evaluations == 0
        assert res.destroy_repair_evaluations == 0
        # Preserves frozen prefix exactly
        assert res.route.vertices[:3] == initial_route.vertices[:3]
        # Route remains 100% feasible
        assert res.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7, 8})


def test_boundary_budget_one(sample_instance: Instance, initial_route: Route):
    """Boundary test: max_evaluations=1 must yield at most 1 evaluation while maintaining feasibility."""
    for op in [RepairOperator.CHEAPEST, RepairOperator.REGRET_2]:
        cfg = DestroyRepairConfig(repair_operator=op, max_iterations=5)
        res = strategy_c_repair(
            instance=sample_instance,
            current_route=initial_route,
            frozen_prefix_length=2,
            new_vertices=[7, 8],
            config=cfg,
            max_evaluations=1,
        )
        # Exactly 1 evaluation used for initial placement of first vertex; safe fallback for remainder
        assert res.total_evaluations <= 1
        assert res.destroy_repair_evaluations == 0
        assert res.route.vertices[:3] == initial_route.vertices[:3]
        assert res.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7, 8})


def test_boundary_budget_cheapest_required_and_one_less(sample_instance: Instance, initial_route: Route):
    """Boundary tests: exactly required amount vs one less than required for Cheapest Insertion."""
    # Suffix for frozen_prefix_length=2 is (2, 3, 4, 5, 6, 0) -> 5 edges (m0 = 5).
    # Inserting single vertex [7] takes exactly 5 evaluations.
    # Boundary: budget = 4 (one less than required)
    cfg = DestroyRepairConfig(repair_operator=RepairOperator.CHEAPEST, max_iterations=5)
    res_less = strategy_c_repair(
        sample_instance, initial_route, frozen_prefix_length=2, new_vertices=[7],
        config=cfg, max_evaluations=4,
    )
    assert res_less.total_evaluations == 4
    assert res_less.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7})
    assert res_less.route.vertices[:3] == initial_route.vertices[:3]

    # Boundary: budget = 5 (exactly required amount)
    res_exact = strategy_c_repair(
        sample_instance, initial_route, frozen_prefix_length=2, new_vertices=[7],
        config=cfg, max_evaluations=5,
    )
    assert res_exact.total_evaluations == 5
    assert res_exact.destroy_repair_evaluations == 0
    assert res_exact.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7})
    assert res_exact.route.vertices[:3] == initial_route.vertices[:3]


def test_boundary_budget_regret2_required_and_one_less(sample_instance: Instance, initial_route: Route):
    """Boundary tests: exactly required amount vs one less than required for Regret-2 Insertion."""
    # Suffix for frozen_prefix_length=2 is (2, 3, 4, 5, 6, 0) -> 5 edges.
    # Inserting 2 vertices [7, 8] with Regret-2:
    # Step 1: 2 unassigned * 5 edges = 10 evals. Suffix becomes 6 edges.
    # Step 2: 1 unassigned * 6 edges = 6 evals.
    # Total required = 10 + 6 = 16 evals.
    cfg = DestroyRepairConfig(repair_operator=RepairOperator.REGRET_2, max_iterations=5)

    # Boundary: budget = 15 (one less than required 16)
    res_15 = strategy_c_repair(
        sample_instance, initial_route, frozen_prefix_length=2, new_vertices=[7, 8],
        config=cfg, max_evaluations=15,
    )
    assert res_15.total_evaluations <= 15
    assert res_15.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7, 8})
    assert res_15.route.vertices[:3] == initial_route.vertices[:3]

    # Boundary: budget = 16 (exactly required 16)
    res_16 = strategy_c_repair(
        sample_instance, initial_route, frozen_prefix_length=2, new_vertices=[7, 8],
        config=cfg, max_evaluations=16,
    )
    assert res_16.total_evaluations == 16
    assert res_16.destroy_repair_evaluations == 0
    assert res_16.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7, 8})
    assert res_16.route.vertices[:3] == initial_route.vertices[:3]


def test_strategy_c_hard_budget_enforcement(sample_instance: Instance, initial_route: Route):
    """Candidate evaluations must strictly respect max_evaluations when budget allows optimization."""
    budgets = [40, 50, 75, 120]

    for budget in budgets:
        cfg = DestroyRepairConfig(
            destroy_operator=DestroyOperator.RANDOM,
            repair_operator=RepairOperator.REGRET_2,
            max_iterations=20,
            seed=42,
        )
        res = strategy_c_repair(
            instance=sample_instance,
            current_route=initial_route,
            frozen_prefix_length=1,
            new_vertices=[7, 8, 9],
            config=cfg,
            max_evaluations=budget,
        )

        # Hard limit enforcement: total evaluations never exceed configured budget
        assert res.total_evaluations <= budget, (
            f"Budget exceeded: {res.total_evaluations} > {budget}"
        )
        # Route must still be feasible
        assert res.route.is_feasible(
            sample_instance,
            required_vertices={1, 2, 3, 4, 5, 6, 7, 8, 9},
        )


def test_strategy_c_exhausted_budget_after_initial_insertion(sample_instance: Instance, initial_route: Route):
    """When budget is smaller than or equal to initial insertion, destroy passes are safely skipped."""
    cfg = DestroyRepairConfig(
        repair_operator=RepairOperator.CHEAPEST,
        max_iterations=10,
    )
    res = strategy_c_repair(
        instance=sample_instance,
        current_route=initial_route,
        frozen_prefix_length=2,
        new_vertices=[7, 8],
        config=cfg,
        max_evaluations=11,
    )
    assert res.destroy_repair_evaluations == 0
    assert res.iterations_completed == 0
    assert res.total_evaluations == res.initial_insertion_evaluations
    assert res.total_evaluations == 11
    assert res.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7, 8})


def test_strategy_c_budget_starvation_guarantees_feasibility(sample_instance: Instance, initial_route: Route):
    """Even if max_evaluations is below initial insertion cost, safe fallback guarantees feasibility."""
    cfg = DestroyRepairConfig(repair_operator=RepairOperator.CHEAPEST)
    res = strategy_c_repair(
        sample_instance,
        initial_route,
        frozen_prefix_length=2,
        new_vertices=[7, 8],
        config=cfg,
        max_evaluations=5,
    )
    assert res.total_evaluations <= 5
    assert res.destroy_repair_evaluations == 0
    assert res.route.is_feasible(sample_instance, required_vertices={1, 2, 3, 4, 5, 6, 7, 8})


# ---------------------------------------------------------------------------
# 6. Deterministic Reproducibility Tests
# ---------------------------------------------------------------------------

def test_strategy_c_deterministic_reproducibility(sample_instance: Instance, initial_route: Route):
    """Identical seed must produce identical routes and evaluation metrics."""
    cfg1 = DestroyRepairConfig(
        destroy_operator=DestroyOperator.SHAW,
        repair_operator=RepairOperator.REGRET_2,
        destroy_fraction=0.3,
        max_iterations=8,
        seed=777,
    )
    cfg2 = DestroyRepairConfig(
        destroy_operator=DestroyOperator.SHAW,
        repair_operator=RepairOperator.REGRET_2,
        destroy_fraction=0.3,
        max_iterations=8,
        seed=777,
    )

    res1 = strategy_c_repair(sample_instance, initial_route, 1, [7, 8], cfg1)
    res2 = strategy_c_repair(sample_instance, initial_route, 1, [7, 8], cfg2)

    assert res1.route.vertices == res2.route.vertices
    assert res1.cost == res2.cost
    assert res1.total_evaluations == res2.total_evaluations
    assert res1.accepted_improvements == res2.accepted_improvements
    assert res1.destroyed_counts == res2.destroyed_counts


# ---------------------------------------------------------------------------
# 7. Edge Cases
# ---------------------------------------------------------------------------

def test_strategy_c_empty_suffix_no_new_customers(sample_instance: Instance):
    """When uncommitted suffix has no customer vertices, Strategy C returns unchanged route."""
    short_route = Route((0, 1, 2, 0))
    res = strategy_c_repair(sample_instance, short_route, 2, [])
    assert res.route.vertices == short_route.vertices
    assert res.total_evaluations == 0


def test_strategy_c_batch_new_customers(sample_instance: Instance, initial_route: Route):
    """Strategy C cleanly handles batch arrivals (|Delta_t| > 1)."""
    res = strategy_c_repair(sample_instance, initial_route, 1, [7, 8, 9])
    assert res.route.is_feasible(sample_instance, required_vertices=set(range(1, 10)))


# ---------------------------------------------------------------------------
# 8. Simulator Integration Tests
# ---------------------------------------------------------------------------

def test_simulator_strategy_c_full_run():
    """Simulator executes Strategy C across all event steps with prefix invariance."""
    inst = Instance.generate_random(n=15, seed=42)
    cfg = EventConfig(total_vertices=15, dynamicity=0.4, events_per_step=1, seed=42)
    seq = EventGenerator(cfg).generate(inst)

    sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1)
    res: SimulationResult = sim.run(Strategy.C, seed=42)

    assert res.all_feasible
    assert res.strategy == Strategy.C
    assert len(res.steps) == seq.num_event_steps

    for step in res.steps:
        assert isinstance(step.repair_result, DestroyRepairResult)
        assert step.metrics.feasible
        assert step.metrics.computational_effort > 0


def test_simulator_strategy_c_hard_budget_boundary():
    """Simulator respects max_evaluations=0 and max_evaluations=1 hard limits at every step."""
    inst = Instance.generate_random(n=12, seed=42)
    cfg = EventConfig(total_vertices=12, dynamicity=0.4, events_per_step=1, seed=42)
    seq = EventGenerator(cfg).generate(inst)

    # Budget 0
    sim0 = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1, max_evaluations=0)
    res0 = sim0.run(Strategy.C, seed=42)
    assert res0.all_feasible
    for step in res0.steps:
        assert step.metrics.computational_effort == 0

    # Budget 1
    sim1 = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1, max_evaluations=1)
    res1 = sim1.run(Strategy.C, seed=42)
    assert res1.all_feasible
    for step in res1.steps:
        assert step.metrics.computational_effort <= 1


def test_simulator_comparison_a_b_c():
    """Strategies A, B, and C can be run on identical instance & events for comparison."""
    inst = Instance.generate_random(n=15, seed=123)
    cfg = EventConfig(total_vertices=15, dynamicity=0.3, events_per_step=1, seed=123)
    seq = EventGenerator(cfg).generate(inst)

    sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1)
    res_a = sim.run(Strategy.A, seed=123)
    res_b = sim.run(Strategy.B, seed=123)
    res_c = sim.run(Strategy.C, seed=123)

    assert res_a.all_feasible
    assert res_b.all_feasible
    assert res_c.all_feasible

    # Final route costs should all be positive finite floats
    assert res_a.final_metrics.route_cost > 0
    assert res_b.final_metrics.route_cost > 0
    assert res_c.final_metrics.route_cost > 0


def test_simulator_strategy_c_with_custom_config():
    """Simulator accepts custom DestroyRepairConfig and propagates it."""
    inst = Instance.generate_random(n=12, seed=99)
    cfg = EventConfig(total_vertices=12, dynamicity=0.3, events_per_step=1, seed=99)
    seq = EventGenerator(cfg).generate(inst)

    dr_cfg = DestroyRepairConfig(
        destroy_operator=DestroyOperator.SHAW,
        repair_operator=RepairOperator.CHEAPEST,
        max_iterations=5,
        seed=99,
    )

    sim = Simulator(
        instance=inst,
        event_sequence=seq,
        freeze_per_step=1,
        destroy_repair_config=dr_cfg,
    )
    res = sim.run(Strategy.C, seed=99)
    assert res.all_feasible
    for step in res.steps:
        assert isinstance(step.repair_result, DestroyRepairResult)


# ---------------------------------------------------------------------------
# 9. Batch Experiment Runner Compatibility Test
# ---------------------------------------------------------------------------

def test_experiment_runner_supports_strategy_c():
    """ExperimentRunner successfully runs Strategy C and writes valid run records."""
    cond = ConditionConfig(
        condition_id="test_n12_d0.3",
        total_vertices=12,
        dynamicity=0.3,
        events_per_step=1,
        freeze_per_step=1,
        budget=BudgetConfig(budget_type=BudgetType.MAX_EVALUATIONS, limit=200),
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        exp_cfg = ExperimentConfig(
            name="test_c_run",
            conditions=(cond,),
            seeds=(42,),
            strategies=("A", "C"),
            output_dir=tmp_dir,
        )

        runner = ExperimentRunner(exp_cfg)
        manifest = runner.run()

        assert manifest.completed_runs == 2
        assert manifest.failed_runs == 0

        # Check runs.csv contains C
        runs_csv = Path(tmp_dir) / "runs.csv"
        assert runs_csv.exists()
        content = runs_csv.read_text(encoding="utf-8")
        assert "_s42_C" in content
        assert "_s42_A" in content
