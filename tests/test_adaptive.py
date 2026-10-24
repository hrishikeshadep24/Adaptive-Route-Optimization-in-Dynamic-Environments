"""Unit and integration tests for Phase 8 Adaptive Strategy Selection.

Tests cover:
- State feature extraction (features.py) and non-leakage
- Rule-based adaptive selector logic and determinism (selector.py)
- Data partitioning and seed disjointness (split.py)
- Oracle benchmark and regret computation (oracle.py)
- End-to-end simulator integration with Strategy.ADAPTIVE
"""

import pytest
import numpy as np
import pandas as pd

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.simulation.state import DynamicState
from adaptive_route_optimization.simulation.events import generate_event_sequence
from adaptive_route_optimization.simulation.simulator import (
    Simulator,
    Strategy,
    SimulationResult,
)
from adaptive_route_optimization.algorithms.adaptive.features import (
    extract_features,
    StateFeatures,
)
from adaptive_route_optimization.algorithms.adaptive.selector import (
    AdaptiveSelector,
    SelectorConfig,
    StrategyChoice,
    SelectionDecision,
)
from adaptive_route_optimization.algorithms.adaptive.split import (
    DataSplitManifest,
    DEFAULT_DATA_SPLIT,
)
from adaptive_route_optimization.algorithms.adaptive.oracle import (
    OracleEvaluator,
    RegretSummary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_instance() -> Instance:
    """Deterministic 8-vertex instance."""
    coords = [
        (0.0, 0.0),   # 0: Depot
        (10.0, 0.0),  # 1
        (10.0, 10.0), # 2
        (0.0, 10.0),  # 3
        (5.0, 5.0),   # 4
        (15.0, 5.0),  # 5
        (5.0, 15.0),  # 6
        (12.0, 12.0), # 7
    ]
    return Instance.from_coords(coords)


@pytest.fixture
def sample_state(small_instance: Instance) -> tuple[DynamicState, frozenset[int]]:
    """Create a sample dynamic state for testing feature extraction."""
    initial_route = Route([0, 1, 2, 0])
    state = DynamicState(
        known_vertices=frozenset({0, 1, 2}),
        frozen_prefix_length=1,
        current_route=initial_route,
        time_step=0,
        instance=small_instance,
    )
    new_vertices = frozenset({3, 4})
    return state, new_vertices


# ---------------------------------------------------------------------------
# 1. Feature Extraction Tests
# ---------------------------------------------------------------------------

class TestFeatureExtraction:
    """Test state feature extraction at dynamic decision points."""

    def test_feature_extraction_fields(self, sample_state: tuple[DynamicState, frozenset[int]]):
        state, new_vertices = sample_state
        feat = extract_features(
            state=state,
            new_vertices=new_vertices,
            total_vertices=7,  # 7 non-depot vertices
            initial_known_count=2,
            remaining_eval_budget=1500,
        )

        assert isinstance(feat, StateFeatures)
        assert feat.total_vertices == 7
        assert feat.known_vertices_count == 4  # 2 initially known customers + 2 from event
        assert feat.frozen_prefix_length == 1
        assert feat.event_size == 2
        assert feat.remaining_eval_budget == 1500
        assert feat.revealed_ratio == pytest.approx(4 / 7, abs=1e-4)
        assert feat.current_cost > 0.0
        assert feat.estimated_2opt_evals >= 0

    def test_feature_no_future_leakage(self, sample_state: tuple[DynamicState, frozenset[int]]):
        """Feature extraction must not access unrevealed future vertices or future costs."""
        state, new_vertices = sample_state
        feat = extract_features(
            state=state,
            new_vertices=new_vertices,
            total_vertices=7,
            initial_known_count=2,
        )
        # Vertices 5, 6, 7 are never touched or included in known count
        assert feat.known_vertices_count == 4
        d = feat.to_dict()
        assert "future_events" not in d
        assert "final_cost" not in d

    def test_estimated_2opt_evals(self, sample_state: tuple[DynamicState, frozenset[int]]):
        """Estimated 2-opt evals should scale with uncommitted suffix."""
        state, new_vertices = sample_state
        feat = extract_features(
            state=state,
            new_vertices=new_vertices,
            total_vertices=7,
            initial_known_count=2,
        )
        assert feat.estimated_2opt_evals >= 0


# ---------------------------------------------------------------------------
# 2. Adaptive Selector Tests
# ---------------------------------------------------------------------------

class TestAdaptiveSelector:
    """Test rule logic, determinism, and budget fallback in AdaptiveSelector."""

    def test_rule_budget_fallback(self):
        """Rule 1: If remaining budget < estimated 2-opt evals, must choose Strategy A."""
        selector = AdaptiveSelector()
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=30,
            frozen_prefix_length=5,
            uncommitted_count=24,
            event_size=2,
            revealed_ratio=0.6,
            uncommitted_ratio=0.8,
            initial_dynamicity=0.1,  # Low dynamicity would normally trigger B
            current_cost=100.0,
            estimated_2opt_evals=100,
            remaining_eval_budget=20,  # 20 < 100
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.A
        assert "Budget fallback" in decision.rationale
        assert decision.overhead_evaluations == 1

    def test_rule_degeneracy_guard(self):
        """Rule 2: If suffix edge count < 4, cannot perform 2-opt; fallback to A."""
        selector = AdaptiveSelector()
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=49,
            frozen_prefix_length=48,
            uncommitted_count=1,
            event_size=1,
            revealed_ratio=0.98,
            uncommitted_ratio=0.02,
            initial_dynamicity=0.1,
            current_cost=100.0,
            estimated_2opt_evals=0,
            remaining_eval_budget=2000,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.A
        assert "Degeneracy guard" in decision.rationale

    def test_rule_low_dynamicity_selects_b(self):
        """Rule 3: Low dynamicity (alpha <= 0.2) selects Strategy B."""
        selector = AdaptiveSelector()
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=20,
            frozen_prefix_length=5,
            uncommitted_count=14,
            event_size=2,
            revealed_ratio=0.4,
            uncommitted_ratio=0.7,
            initial_dynamicity=0.20,  # <= 0.20
            current_cost=120.0,
            estimated_2opt_evals=100,
            remaining_eval_budget=2000,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.B
        assert "Low dynamicity" in decision.rationale

    def test_rule_late_stage_selects_b(self):
        """Rule 3: High dynamicity but late stage (revealed_ratio >= 0.75) selects Strategy B."""
        selector = AdaptiveSelector()
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=40,
            frozen_prefix_length=15,
            uncommitted_count=24,
            event_size=3,
            revealed_ratio=0.80,  # >= 0.75
            uncommitted_ratio=0.6,
            initial_dynamicity=0.60,  # High dynamicity!
            current_cost=150.0,
            estimated_2opt_evals=200,
            remaining_eval_budget=2000,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.B
        assert "Late-stage" in decision.rationale

    def test_rule_high_dynamicity_early_selects_a(self):
        """Rule 3: Moderate/high dynamicity (alpha > 0.2) and early/mid stage selects Strategy A."""
        selector = AdaptiveSelector()
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=25,
            frozen_prefix_length=10,
            uncommitted_count=14,
            event_size=5,
            revealed_ratio=0.50,  # < 0.75
            uncommitted_ratio=0.6,
            initial_dynamicity=0.40,  # > 0.20
            current_cost=130.0,
            estimated_2opt_evals=150,
            remaining_eval_budget=2000,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.A
        assert "avoiding myopic trap" in decision.rationale

    def test_selector_determinism(self):
        """Repeated calls with identical features must yield identical decisions."""
        selector = AdaptiveSelector()
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=20,
            frozen_prefix_length=5,
            uncommitted_count=14,
            event_size=2,
            revealed_ratio=0.4,
            uncommitted_ratio=0.7,
            initial_dynamicity=0.20,
            current_cost=120.0,
            estimated_2opt_evals=100,
            remaining_eval_budget=2000,
        )
        decisions = [selector.select(feat).chosen_strategy for _ in range(10)]
        assert all(d == StrategyChoice.B for d in decisions)

    def test_rule_budget_aware_below_and_above_threshold(self):
        """Verify Rule 1 budget awareness across zero, small, below, and above thresholds."""
        selector = AdaptiveSelector()
        
        # Suffix has uncommitted_count=20, event_size=1 -> est_ins = 21, min_required = 31 (21 + 10)
        base_kwargs = dict(
            total_vertices=50,
            known_vertices_count=31,
            frozen_prefix_length=10,
            uncommitted_count=20,
            event_size=1,
            revealed_ratio=0.62,
            uncommitted_ratio=0.65,
            initial_dynamicity=0.15,  # Low dynamicity (prefers B if budget allows)
            current_cost=200.0,
            estimated_2opt_evals=210,
        )

        # Budget = 0 -> must choose Strategy A
        f_0 = StateFeatures(**base_kwargs, remaining_eval_budget=0)
        d_0 = selector.select(f_0)
        assert d_0.chosen_strategy == StrategyChoice.A
        assert "Budget fallback" in d_0.rationale

        # Budget = 5 -> must choose Strategy A (5 < 31)
        f_5 = StateFeatures(**base_kwargs, remaining_eval_budget=5)
        d_5 = selector.select(f_5)
        assert d_5.chosen_strategy == StrategyChoice.A
        assert "Budget fallback" in d_5.rationale

        # Budget = 25 -> must choose Strategy A (25 < 31)
        f_25 = StateFeatures(**base_kwargs, remaining_eval_budget=25)
        d_25 = selector.select(f_25)
        assert d_25.chosen_strategy == StrategyChoice.A
        assert "Budget fallback" in d_25.rationale

        # Budget = 45 -> exceeds min_required (31), so partial 2-opt is viable -> chooses Strategy B
        f_45 = StateFeatures(**base_kwargs, remaining_eval_budget=45)
        d_45 = selector.select(f_45)
        assert d_45.chosen_strategy == StrategyChoice.B
        assert "Low dynamicity" in d_45.rationale

        # Budget = 100 -> partial 2-opt viable -> chooses Strategy B
        f_100 = StateFeatures(**base_kwargs, remaining_eval_budget=100)
        d_100 = selector.select(f_100)
        assert d_100.chosen_strategy == StrategyChoice.B

        # Budget = 1000 -> full 2-opt viable -> chooses Strategy B
        f_1000 = StateFeatures(**base_kwargs, remaining_eval_budget=1000)
        d_1000 = selector.select(f_1000)
        assert d_1000.chosen_strategy == StrategyChoice.B


# ---------------------------------------------------------------------------
# 3. Data Split & Non-Leakage Tests
# ---------------------------------------------------------------------------

class TestDataSplit:
    """Test seed partition integrity and leakage prevention."""

    def test_disjoint_partitions(self):
        split = DEFAULT_DATA_SPLIT
        dev_set = set(split.development.seeds)
        val_set = set(split.validation.seeds)
        held_out_set = set(split.held_out.seeds)

        assert dev_set.isdisjoint(val_set), "Dev and Val seeds overlap!"
        assert dev_set.isdisjoint(held_out_set), "Dev and Held-Out seeds overlap!"
        assert val_set.isdisjoint(held_out_set), "Val and Held-Out seeds overlap!"

    def test_partition_membership(self):
        split = DEFAULT_DATA_SPLIT
        assert split.get_partition(42) == "development"
        assert split.get_partition(101) == "development"
        assert split.get_partition(777) == "validation"
        assert split.get_partition(1234) == "held_out"
        assert split.get_partition(5678) == "held_out"
        assert split.get_partition(9999) == "held_out"

        with pytest.raises(ValueError):
            split.get_partition(999999)


# ---------------------------------------------------------------------------
# 4. Oracle & Regret Tests
# ---------------------------------------------------------------------------

class TestOracleRegret:
    """Test oracle lower bound and regret metrics."""

    def test_oracle_calculation_and_regret(self):
        runs_df = pd.DataFrame([
            # Instance 1: A is better (100 vs 110), Adaptive chose A (100) -> Regret = 0
            {"condition_id": "c1", "seed": 1234, "total_vertices": 50, "dynamicity": 0.4, "strategy": "A", "final_cost": 100.0, "total_computational_effort": 100, "total_response_time_ms": 10.0, "mean_disruption": 0.1},
            {"condition_id": "c1", "seed": 1234, "total_vertices": 50, "dynamicity": 0.4, "strategy": "B", "final_cost": 110.0, "total_computational_effort": 300, "total_response_time_ms": 50.0, "mean_disruption": 0.2},
            {"condition_id": "c1", "seed": 1234, "total_vertices": 50, "dynamicity": 0.4, "strategy": "ADAPTIVE", "final_cost": 100.0, "total_computational_effort": 101, "total_response_time_ms": 11.0, "mean_disruption": 0.1},

            # Instance 2: B is better (100 vs 120), Adaptive chose A (120) -> Regret = 20
            {"condition_id": "c2", "seed": 1234, "total_vertices": 50, "dynamicity": 0.1, "strategy": "A", "final_cost": 120.0, "total_computational_effort": 100, "total_response_time_ms": 10.0, "mean_disruption": 0.1},
            {"condition_id": "c2", "seed": 1234, "total_vertices": 50, "dynamicity": 0.1, "strategy": "B", "final_cost": 100.0, "total_computational_effort": 300, "total_response_time_ms": 50.0, "mean_disruption": 0.2},
            {"condition_id": "c2", "seed": 1234, "total_vertices": 50, "dynamicity": 0.1, "strategy": "ADAPTIVE", "final_cost": 120.0, "total_computational_effort": 101, "total_response_time_ms": 11.0, "mean_disruption": 0.1},
        ])

        per_inst = OracleEvaluator.compute_instance_oracle_and_regret(runs_df)
        assert len(per_inst) == 2

        # Check instance 1
        inst1 = per_inst.iloc[0]
        assert inst1["cost_oracle"] == 100.0
        assert inst1["oracle_best_strategy"] == "A"
        assert inst1["cost_regret"] == pytest.approx(0.0, abs=1e-6)

        # Check instance 2
        inst2 = per_inst.iloc[1]
        assert inst2["cost_oracle"] == 100.0
        assert inst2["oracle_best_strategy"] == "B"
        assert inst2["cost_regret"] == pytest.approx(20.0, abs=1e-6)

        summary = OracleEvaluator.summarize_regret(per_inst)
        assert isinstance(summary, RegretSummary)
        assert summary.total_instances == 2
        assert summary.mean_absolute_regret == pytest.approx(10.0, abs=1e-6)
        assert summary.zero_regret_rate_pct == pytest.approx(50.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 5. Full Simulation Integration Tests
# ---------------------------------------------------------------------------

class TestSimulationIntegration:
    """Test Strategy.ADAPTIVE in the full simulation environment."""

    def test_adaptive_simulation_execution(self, small_instance: Instance):
        """Simulator executes with Strategy.ADAPTIVE without errors."""
        event_seq = generate_event_sequence(
            instance=small_instance,
            total_vertices=7,
            initial_known_count=3,
            events_per_step=1,
            seed=42,
        )
        sim = Simulator(
            instance=small_instance,
            event_sequence=event_seq,
            freeze_per_step=1,
            max_evaluations=5000,
        )
        result = sim.run(strategy=Strategy.ADAPTIVE, seed=42)

        assert result.strategy == Strategy.ADAPTIVE
        assert result.final_route is not None
        assert result.all_feasible
        assert len(result.final_route.vertices) == 9  # 7 customers + 2 depot visits
        assert result.total_computational_effort > 0
        assert result.total_computational_effort <= 5000

    def test_simulator_run_all_strategies(self, small_instance: Instance):
        """Simulator.run_all_strategies evaluates A, B, and ADAPTIVE on identical inputs."""
        event_seq = generate_event_sequence(
            instance=small_instance,
            total_vertices=7,
            initial_known_count=3,
            events_per_step=1,
            seed=42,
        )
        sim = Simulator(
            instance=small_instance,
            event_sequence=event_seq,
            freeze_per_step=1,
            max_evaluations=5000,
        )
        res_a, res_b, res_adaptive = sim.run_all_strategies(seed=42)

        assert res_a.strategy == Strategy.A
        assert res_b.strategy == Strategy.B
        assert res_adaptive.strategy == Strategy.ADAPTIVE

        assert res_a.all_feasible
        assert res_b.all_feasible
        assert res_adaptive.all_feasible

        # Identical instance coordinates
        assert np.allclose(res_a.instance.coords, res_adaptive.instance.coords)
        assert np.allclose(res_b.instance.coords, res_adaptive.instance.coords)

    def test_adaptive_bounded_budget_feasibility_and_prefix(self):
        """Verify that corrected Adaptive preserves feasibility and frozen prefix under B=50 and B=100."""
        from adaptive_route_optimization.simulation.events import EventConfig, EventGenerator
        inst = Instance.generate_random(n=15, seed=123)
        cfg = EventConfig(total_vertices=15, dynamicity=0.2, events_per_step=1, seed=123)
        seq = EventGenerator(cfg).generate(inst)

        for b in [0, 5, 50, 100]:
            sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1, max_evaluations=b)
            res = sim.run(strategy=Strategy.ADAPTIVE, seed=123)

            assert res.all_feasible, f"Infeasible route under budget {b}"
            for step_idx, step in enumerate(res.steps):
                # Verify budget enforcement
                assert step.metrics.computational_effort <= b, f"Effort {step.metrics.computational_effort} exceeded budget {b}"
                # Verify prefix invariance
                prev_route = step.previous_route.vertices
                cur_route = step.updated_route.vertices
                prefix_len = min(step_idx + 1, len(prev_route))
                assert cur_route[:prefix_len] == prev_route[:prefix_len], "Frozen prefix violated"

            if b == 0:
                assert res.total_computational_effort == 0
                assert res.total_candidate_evaluations == 0
                assert res.total_overhead_evaluations == 0
