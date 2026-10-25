"""Unit and integration tests for Adaptive v3: Three-Strategy Selection.

Covers:
- Strategy C selection on documented trigger conditions (burst arrivals, mid-stage high dynamism, cost jumps)
- Strategy B selection on low dynamicity and late-stage events
- Strategy A selection on high dynamicity early stage and tight budgets
- Budget-aware fallback cascades (C -> B -> A, B -> A)
- Small suffix degeneracy guards
- Strict candidate evaluation accounting and zero budget overruns
- Frozen-prefix preservation and route feasibility
- Deterministic reproducibility
"""

import pytest
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.simulation.state import DynamicState
from adaptive_route_optimization.simulation.events import EventConfig, EventGenerator
from adaptive_route_optimization.simulation.simulator import Simulator, Strategy
from adaptive_route_optimization.algorithms.adaptive.selector import (
    AdaptiveSelector,
    SelectorConfig,
    StrategyChoice,
    SelectionDecision,
)
from adaptive_route_optimization.algorithms.adaptive.features import (
    extract_features,
    StateFeatures,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_instance() -> Instance:
    """Deterministic 15-vertex instance."""
    coords = [
        (0.0, 0.0),   # 0: Depot
        (10.0, 0.0),  # 1
        (10.0, 10.0), # 2
        (0.0, 10.0),  # 3
        (5.0, 5.0),   # 4
        (15.0, 5.0),  # 5
        (5.0, 15.0),  # 6
        (12.0, 12.0), # 7
        (2.0, 7.0),   # 8
        (8.0, 2.0),   # 9
        (3.0, 12.0),  # 10
        (14.0, 2.0),  # 11
        (7.0, 8.0),   # 12
        (1.0, 4.0),   # 13
        (9.0, 14.0),  # 14
    ]
    return Instance.from_coords(coords)


# ---------------------------------------------------------------------------
# 1. Selection Rules Unit Tests
# ---------------------------------------------------------------------------

class TestAdaptiveV3SelectionRules:
    """Test rule logic and conditions for selecting A, B, and C."""

    def test_v3_selects_c_on_burst_arrival(self):
        """Criterion C1: Burst arrival (k >= burst_arrival_threshold) selects Strategy C when budget is sufficient."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=20,
            frozen_prefix_length=5,
            uncommitted_count=14,
            event_size=3,  # k=3 >= burst_arrival_threshold=2
            revealed_ratio=0.40,
            uncommitted_ratio=0.70,
            initial_dynamicity=0.40,
            current_cost=150.0,
            estimated_2opt_evals=100,
            remaining_eval_budget=2000,  # Ample budget
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.C
        assert "Strategy C" in decision.rationale
        assert "arrival burst" in decision.rationale
        assert decision.overhead_evaluations == 1

    def test_v3_selects_c_on_mid_stage_high_dynamicity(self):
        """Criterion C2: High dynamicity mid-stage with sufficient suffix selects Strategy C."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=25,
            frozen_prefix_length=5,
            uncommitted_count=19,  # m=19, suffix large
            event_size=1,
            revealed_ratio=0.50,  # in [0.35, 0.85]
            uncommitted_ratio=0.76,
            initial_dynamicity=0.60,  # >= 0.40
            current_cost=200.0,
            estimated_2opt_evals=150,
            remaining_eval_budget=2000,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.C
        assert "Strategy C" in decision.rationale
        assert "high dynamicity mid-stage" in decision.rationale

    def test_v3_selects_c_on_route_cost_jump(self):
        """Criterion C3: Sudden route cost deterioration (relative_cost_change >= 0.05) selects Strategy C."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=20,
            frozen_prefix_length=5,
            uncommitted_count=14,
            event_size=1,
            revealed_ratio=0.30,
            uncommitted_ratio=0.70,
            initial_dynamicity=0.30,
            current_cost=180.0,
            estimated_2opt_evals=100,
            remaining_eval_budget=2000,
            relative_cost_change=0.08,  # +8% jump >= 5% threshold
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.C
        assert "route deterioration jump" in decision.rationale

    def test_v3_selects_b_on_low_dynamicity(self):
        """Low dynamicity (alpha <= 0.20) selects Strategy B when B is eligible and no shock."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=20,
            frozen_prefix_length=5,
            uncommitted_count=14,
            event_size=1,
            revealed_ratio=0.30,
            uncommitted_ratio=0.70,
            initial_dynamicity=0.15,  # <= 0.20
            current_cost=120.0,
            estimated_2opt_evals=100,
            remaining_eval_budget=500,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.B
        assert "Strategy B" in decision.rationale
        assert "low dynamicity" in decision.rationale

    def test_v3_selects_b_on_late_stage(self):
        """Late-stage event (revealed_ratio >= 0.75) selects Strategy B when B is eligible."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=45,
            frozen_prefix_length=35,
            uncommitted_count=9,
            event_size=1,
            revealed_ratio=0.90,  # >= 0.75
            uncommitted_ratio=0.20,
            initial_dynamicity=0.60,
            current_cost=300.0,
            estimated_2opt_evals=40,
            remaining_eval_budget=500,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.B
        assert "Strategy B" in decision.rationale
        assert "late-stage event" in decision.rationale

    def test_v3_selects_a_on_early_high_dynamicity_without_shock(self):
        """Early stage high dynamicity (alpha > 0.20, revealed < 0.35) without shock selects Strategy A."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=12,
            frozen_prefix_length=3,
            uncommitted_count=8,
            event_size=1,
            revealed_ratio=0.24,  # < 0.35
            uncommitted_ratio=0.67,
            initial_dynamicity=0.60,  # High dynamicity
            current_cost=150.0,
            estimated_2opt_evals=45,
            remaining_eval_budget=1000,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.A
        assert "Strategy A" in decision.rationale
        assert "avoiding myopic trap" in decision.rationale


# ---------------------------------------------------------------------------
# 2. Budget Fallback Cascade Tests
# ---------------------------------------------------------------------------

class TestAdaptiveV3BudgetFallbacks:
    """Test budget-aware graceful degradation (C -> B -> A and B -> A)."""

    def test_v3_fallback_c_to_b_when_c_unaffordable(self):
        """When C is desired but budget is insufficient for C, degrade to B if B fits."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        # m=20, k=1 -> est_ins=21. Req_B = 21 + 10 = 31.
        # q=5, m_part=16 -> req_repair = 5*17 + 10 = 95. Req_C = 21 + 95 = 116.
        # If budget = 60: 60 < 116 (cannot afford C), but 60 >= 31 (can afford B).
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=25,
            frozen_prefix_length=5,
            uncommitted_count=20,
            event_size=1,
            revealed_ratio=0.50,  # Desires C (mid-stage high dynamicity)
            uncommitted_ratio=0.80,
            initial_dynamicity=0.60,
            current_cost=200.0,
            estimated_2opt_evals=180,
            remaining_eval_budget=60,  # 31 <= 60 < 116
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.B
        assert "Budget fallback (C -> B)" in decision.rationale
        assert decision.overhead_evaluations == 1

    def test_v3_fallback_c_to_a_when_both_unaffordable(self):
        """When C is desired but budget is insufficient for both C and B, degrade to A."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        # m=20, k=1 -> Req_B = 31, Req_C = 116.
        # If budget = 20: 20 < 31 (cannot afford B either).
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=25,
            frozen_prefix_length=5,
            uncommitted_count=20,
            event_size=1,
            revealed_ratio=0.50,
            uncommitted_ratio=0.80,
            initial_dynamicity=0.60,
            current_cost=200.0,
            estimated_2opt_evals=180,
            remaining_eval_budget=20,  # 20 < 31
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.A
        assert "Budget fallback (C -> A)" in decision.rationale

    def test_v3_fallback_b_to_a_when_b_unaffordable(self):
        """When B is desired (e.g. low dynamicity) but budget is insufficient, degrade to A."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        # m=15, k=1 -> Req_B = 15 + 1 + 10 = 26.
        # If budget = 15: 15 < 26.
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=20,
            frozen_prefix_length=5,
            uncommitted_count=15,
            event_size=1,
            revealed_ratio=0.40,
            uncommitted_ratio=0.75,
            initial_dynamicity=0.10,  # Desires B
            current_cost=100.0,
            estimated_2opt_evals=100,
            remaining_eval_budget=15,  # 15 < 26
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.A
        assert "Budget fallback (B -> A)" in decision.rationale

    def test_v3_degeneracy_guard_tiny_suffix(self):
        """When uncommitted suffix has too few edges for 2-opt, safe fallback to A."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=49,
            frozen_prefix_length=48,
            uncommitted_count=1,
            event_size=1,  # m_edges = 1 + 1 + 1 = 3 < 4
            revealed_ratio=0.98,
            uncommitted_ratio=0.02,
            initial_dynamicity=0.10,
            current_cost=100.0,
            estimated_2opt_evals=0,
            remaining_eval_budget=2000,
        )
        decision = selector.select(feat)
        assert decision.chosen_strategy == StrategyChoice.A


# ---------------------------------------------------------------------------
# 3. Determinism & Configuration Tests
# ---------------------------------------------------------------------------

class TestAdaptiveV3DeterminismAndConfig:
    """Test deterministic reproducibility and configuration roundtrip."""

    def test_v3_determinism_identical_inputs(self):
        """Repeated invocations on identical features must yield identical decisions."""
        selector = AdaptiveSelector(SelectorConfig.v3())
        feat = StateFeatures(
            total_vertices=50,
            known_vertices_count=25,
            frozen_prefix_length=5,
            uncommitted_count=19,
            event_size=3,
            revealed_ratio=0.50,
            uncommitted_ratio=0.76,
            initial_dynamicity=0.40,
            current_cost=175.0,
            estimated_2opt_evals=150,
            remaining_eval_budget=1000,
        )
        decisions = [selector.select(feat).chosen_strategy for _ in range(50)]
        assert all(d == StrategyChoice.C for d in decisions)

    def test_v3_config_roundtrip(self):
        """SelectorConfig serialization to and from dictionary."""
        cfg = SelectorConfig.v3(min_suffix_for_c=8, burst_arrival_threshold=3)
        d = cfg.to_dict()
        assert d["name"] == "rule_v3_three_strategy"
        assert d["version"] == "v3"
        assert d["min_suffix_for_c"] == 8
        assert d["burst_arrival_threshold"] == 3

        reconstructed = SelectorConfig.from_dict(d)
        assert reconstructed == cfg


# ---------------------------------------------------------------------------
# 4. Simulation Integration & Invariants Tests
# ---------------------------------------------------------------------------

class TestAdaptiveV3SimulationIntegration:
    """Test full dynamic routing simulation with Strategy.ADAPTIVE_V3."""

    def test_simulator_runs_adaptive_v3_successfully(self, sample_instance: Instance):
        """Simulator executes ADAPTIVE_V3 end-to-end, maintaining invariants."""
        ecfg = EventConfig(
            total_vertices=sample_instance.n,
            dynamicity=0.4,
            events_per_step=1,
            seed=42,
        )
        ev_seq = EventGenerator(ecfg).generate(sample_instance)

        sel = AdaptiveSelector(SelectorConfig.v3())
        sim = Simulator(
            instance=sample_instance,
            event_sequence=ev_seq,
            freeze_per_step=1,
            max_evaluations=500,
            selector=sel,
        )
        result = sim.run(Strategy.ADAPTIVE_V3, seed=42)

        # 1. Feasibility check
        assert result.all_feasible, "All dynamic intermediate steps must be feasible"
        assert result.final_metrics.feasible

        # 2. Prefix invariance check
        for step_idx, step in enumerate(result.steps):
            prev_route = step.previous_route.vertices
            cur_route = step.updated_route.vertices
            prefix_len = min(step_idx + 1, len(prev_route))
            assert cur_route[:prefix_len] == prev_route[:prefix_len], f"Prefix violated at step {step_idx+1}"

        # 3. Budget compliance check
        for step in result.steps:
            assert step.metrics.computational_effort <= 500, f"Effort {step.metrics.computational_effort} exceeded budget 500"

        # 4. Selector decisions recorded
        assert len(sel.decision_history) == len(result.steps)

    def test_simulator_runs_all_three_under_unbounded(self, sample_instance: Instance):
        """Under unconstrained budget, selector selects Strategy C on mid-stage events."""
        ecfg = EventConfig(
            total_vertices=sample_instance.n,
            dynamicity=0.6,
            events_per_step=2,  # Burst arrivals of 2
            seed=42,
        )
        ev_seq = EventGenerator(ecfg).generate(sample_instance)

        sel = AdaptiveSelector(SelectorConfig.v3(burst_arrival_threshold=2))
        sim = Simulator(
            instance=sample_instance,
            event_sequence=ev_seq,
            freeze_per_step=1,
            max_evaluations=None,  # Unbounded
            selector=sel,
        )
        result = sim.run(Strategy.ADAPTIVE_V3, seed=42)

        choices = [d.chosen_strategy for d in sel.decision_history]
        assert StrategyChoice.C in choices, f"Strategy C should be selected on burst arrivals, got {choices}"
        assert result.all_feasible
