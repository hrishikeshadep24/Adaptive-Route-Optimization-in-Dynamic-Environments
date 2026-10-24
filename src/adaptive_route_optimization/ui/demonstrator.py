"""Interactive Demonstration Engine for Dynamic Route Optimization.

Provides step-by-step interactive simulation for visual inspection:
- Tracks dynamic event arrivals (Δ_t).
- Advances vehicle position (frozen prefix f_t).
- Applies Strategy A (Greedy), Strategy B (2-opt), Strategy C (Destroy-Repair), or ADAPTIVE (Selector).
- Verifies frozen-prefix invariance.
- Captures decision-time state features and explainable rule rationales.
- Supports Synthetic distributions (Uniform, Clustered, Mixed) and TSPLIB benchmarks (berlin52, eil51).
- Supports evaluation budgets, pass budgets, and unbounded execution.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Optional, Sequence
import numpy as np

from adaptive_route_optimization.models.instance import Instance, CustomerDistribution
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.benchmarks import load_tsplib_benchmark
from adaptive_route_optimization.simulation.events import EventConfig, generate_event_sequence, EventSequence
from adaptive_route_optimization.simulation.state import DynamicState, create_initial_state
from adaptive_route_optimization.simulation.simulator import Simulator, Strategy
from adaptive_route_optimization.algorithms.adaptive.features import extract_features, StateFeatures
from adaptive_route_optimization.algorithms.adaptive.selector import AdaptiveSelector, SelectionDecision, StrategyChoice


@dataclass(frozen=True)
class DemonstrationStepRecord:
    """Detailed record of a single interactive dynamic routing step."""
    time_step: int
    new_vertices: list[int]
    frozen_prefix_length: int
    route_before: Route
    route_after: Route
    cost_before: float
    cost_after: float
    evaluations_used: int
    disruption: float
    strategy_used: str
    decision_rationale: Optional[str] = None
    state_features: Optional[dict[str, Any]] = None
    prefix_preserved: bool = True


class InteractiveDemonstrator:
    """Controls step-by-step dynamic routing execution for visual exploration."""

    def __init__(
        self,
        n_vertices: int = 15,
        dynamicity: float = 0.4,
        seed: int = 42,
        strategy: str = "ADAPTIVE",
        max_evaluations: Optional[int] = 5000,
        distribution: str = "uniform",
        benchmark_name: Optional[str] = None,
        max_passes: Optional[int] = None,
        events_per_step: int = 1,
    ) -> None:
        self.n_vertices = n_vertices
        self.dynamicity = dynamicity
        self.seed = seed
        self.strategy_name = strategy
        self.max_evaluations = max_evaluations
        self.distribution = distribution
        self.benchmark_name = benchmark_name
        self.max_passes = max_passes
        self.events_per_step = events_per_step

        # 1. Deterministic synthetic or TSPLIB benchmark instance
        if benchmark_name:
            tsplib_obj = load_tsplib_benchmark(benchmark_name)
            self.instance = tsplib_obj.instance
            self.n_vertices = self.instance.n
        elif distribution == "uniform":
            self.instance = Instance.generate_synthetic(
                n=n_vertices,
                distribution="uniform",
                seed=seed,
                x_range=(0.05, 0.95),
                y_range=(0.05, 0.95),
            )
        else:
            self.instance = Instance.generate_synthetic(
                n=n_vertices,
                distribution=distribution,
                seed=seed,
            )

        # 2. Event Sequence
        initial_known = max(2, int(self.n_vertices * (1.0 - dynamicity)))
        self.event_sequence = generate_event_sequence(
            instance=self.instance,
            total_vertices=self.n_vertices,
            initial_known_count=initial_known,
            events_per_step=events_per_step,
            seed=seed,
        )

        # 3. Initial State (t=0)
        self.initial_state = create_initial_state(
            self.instance,
            set(self.event_sequence.initial_known),
            seed=seed,
        )

        # 4. Map Strategy
        upper_strat = strategy.upper()
        if upper_strat == "A":
            self.strategy_enum = Strategy.A
        elif upper_strat == "B":
            self.strategy_enum = Strategy.B
        elif upper_strat == "C":
            self.strategy_enum = Strategy.C
        else:
            self.strategy_enum = Strategy.ADAPTIVE

        # 5. Pre-compute complete step-by-step history
        self.step_records: list[DemonstrationStepRecord] = []
        self._simulate_all_steps()

    def _simulate_all_steps(self) -> None:
        """Run step-by-step recording complete visual state at each dynamic event."""
        current_state = self.initial_state
        selector = AdaptiveSelector()

        for t in range(self.event_sequence.num_event_steps):
            event_verts = self.event_sequence.get_event_at_step(t)
            new_verts_sorted = sorted(list(event_verts))

            route_before = current_state.current_route
            cost_before = route_before.cost(self.instance)
            prefix_len = current_state.frozen_prefix_length

            # Check features & adaptive decision if ADAPTIVE
            decision_rationale = None
            features_dict = None
            effective_strategy = self.strategy_enum
            overhead_evals = 0

            if self.strategy_enum == Strategy.ADAPTIVE:
                feat = extract_features(
                    state=current_state,
                    new_vertices=event_verts,
                    total_vertices=self.n_vertices,
                    initial_known_count=len(self.event_sequence.initial_known) - 1,
                    remaining_eval_budget=self.max_evaluations,
                )
                features_dict = feat.to_dict()
                dec = selector.select(feat)
                decision_rationale = dec.rationale
                overhead_evals = dec.overhead_evaluations
                effective_strategy = Strategy.A if dec.chosen_strategy == StrategyChoice.A else Strategy.B

            # Advance state with new vertices
            state_with_new = current_state.with_new_vertices(event_verts)

            # Repair suffix using existing simulator logic
            sim = Simulator(
                instance=self.instance,
                event_sequence=self.event_sequence,
                freeze_per_step=1,
                max_evaluations=self.max_evaluations,
                max_passes=self.max_passes,
            )
            repair_result, updated_route, metrics = sim._apply_strategy(
                effective_strategy, state_with_new, event_verts, seed=self.seed
            )

            cost_after = updated_route.cost(self.instance)
            step_evals = metrics.computational_effort + overhead_evals

            # Invariant check: Frozen prefix must be strictly identical
            prefix_before = route_before.vertices[: prefix_len + 1]
            prefix_after = updated_route.vertices[: prefix_len + 1]
            prefix_preserved = (prefix_before == prefix_after)

            # Descriptive strategy label
            if self.strategy_enum == Strategy.ADAPTIVE:
                sub_strat = "Greedy" if effective_strategy == Strategy.A else "2-opt"
                strat_label = f"ADAPTIVE ({sub_strat})"
            elif effective_strategy == Strategy.A:
                strat_label = "Strategy A (Greedy)"
            elif effective_strategy == Strategy.B:
                strat_label = "Strategy B (2-opt)"
            elif effective_strategy == Strategy.C:
                strat_label = "Strategy C (Destroy-Repair)"
            else:
                strat_label = str(effective_strategy.value)

            rec = DemonstrationStepRecord(
                time_step=t + 1,
                new_vertices=new_verts_sorted,
                frozen_prefix_length=prefix_len,
                route_before=route_before,
                route_after=updated_route,
                cost_before=cost_before,
                cost_after=cost_after,
                evaluations_used=step_evals,
                disruption=metrics.disruption,
                strategy_used=strat_label,
                decision_rationale=decision_rationale,
                state_features=features_dict,
                prefix_preserved=prefix_preserved,
            )
            self.step_records.append(rec)

            # Advance vehicle position for next step
            current_state = state_with_new.with_updated_route(updated_route).advance_frozen_prefix(1)

    @property
    def total_steps(self) -> int:
        return len(self.step_records)

    def get_step(self, step_idx: int) -> DemonstrationStepRecord:
        """Get record for step (1-based index)."""
        if 1 <= step_idx <= len(self.step_records):
            return self.step_records[step_idx - 1]
        raise IndexError(f"Step {step_idx} out of range [1, {len(self.step_records)}]")
