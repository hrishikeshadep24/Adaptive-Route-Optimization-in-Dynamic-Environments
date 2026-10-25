"""Event-Driven Simulator for Dynamic Routing.



Runs controlled dynamic routing experiments with multiple strategies on

identical instance and event sequences.

References: RESEARCH_SPEC.md (Update Operator, Frozen-Prefix Rule),

PSEUDOCODE.md (UPDATE_WITH_FROZEN), PHASE_PLAN.md (Phase 5 tasks).

"""



from __future__ import annotations

from dataclasses import dataclass, field

from enum import Enum

from typing import Callable, Optional, Sequence

import time



import numpy as np



from adaptive_route_optimization.models.instance import Instance

from adaptive_route_optimization.models.route import Route

from adaptive_route_optimization.algorithms.repair.insertion import (

    greedy_insertion_repair,

    InsertionResult,

)

from adaptive_route_optimization.algorithms.repair.insertion_two_opt import (

    strategy_b_repair,

    InsertionTwoOptResult,

)

from adaptive_route_optimization.algorithms.repair.destroy_repair import (

    strategy_c_repair,

    DestroyRepairConfig,

    DestroyRepairResult,

)

from adaptive_route_optimization.algorithms.local_search.two_opt import two_opt, TwoOptResult

from adaptive_route_optimization.evaluation.metrics import (

    RouteMetrics,

    evaluate_route,

    TimedOperation,

)

from adaptive_route_optimization.simulation.state import DynamicState, create_initial_state

from adaptive_route_optimization.simulation.events import EventSequence, EventConfig





class Strategy(Enum):

    """Update strategy to apply."""

    A = "greedy_insertion"      # Strategy A: Greedy Insertion Repair

    B = "insertion_two_opt"     # Strategy B: Insertion + 2-opt Repair

    C = "destroy_repair"        # Strategy C: Suffix Destroy-and-Repair (Phase 4 / Stage 2)

    ADAPTIVE = "adaptive"       # Strategy Adaptive: Interpretable Adaptive Strategy Selector (Phase 8 / Stage 7)

    ADAPTIVE_V2 = "adaptive_v2" # Strategy Adaptive v2: Legacy A/B rule selector (Stage 5B)

    ADAPTIVE_V3 = "adaptive_v3" # Strategy Adaptive v3: Three-strategy A/B/C selector (Stage 7)





def cheapest_insertion_on_suffix(

    instance: Instance,

    suffix_vertices: Sequence[int],

    new_vertices: Sequence[int],

    max_evaluations: Optional[int] = None,

) -> tuple[tuple[int, ...], int, list[float]]:

    """Insert new vertices into a suffix path at cheapest positions.



    The suffix is a path (p_f, u_1, ..., u_k, 0) starting from the last

    frozen vertex and ending at depot. This is NOT a full Route (doesn't

    start at depot), but insertion positions are the edges in this path.



    Hard budget enforcement:

    If max_evaluations is specified, candidate evaluations will strictly not exceed

    max_evaluations. If budget is exhausted (remaining evals == 0), remaining

    vertices are inserted immediately before return depot 0 with 0 candidate evaluations,

    guaranteeing route feasibility and prefix preservation without violating budget.



    Args:

        instance: Problem instance.

        suffix_vertices: Tuple of vertices in the suffix path.

        new_vertices: New vertices to insert (processed in order).

        max_evaluations: Optional hard budget cap on candidate evaluations.



    Returns:

        Tuple of (updated_suffix_vertices, total_evaluations, deltas).

    """

    current_suffix = list(suffix_vertices)

    total_evals = 0

    deltas = []



    for v in new_vertices:

        # Number of insertion positions = number of edges in suffix

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

            # Documented safe fallback: insert before return depot 0

            # with 0 evaluations, guaranteeing feasibility and hard budget limit

            pos = len(current_suffix) - 1

            current_suffix.insert(pos, v)

            deltas.append(0.0)

            continue



        best_delta = float("inf")

        best_pos = -1



        # Evaluate candidate positions in the suffix up to evals_allowed

        for pos in range(evals_allowed):

            u = current_suffix[pos]

            w = current_suffix[pos + 1]

            delta = (

                instance.cost(u, v)

                + instance.cost(v, w)

                - instance.cost(u, w)

            )

            total_evals += 1



            if delta < best_delta:

                best_delta = delta

                best_pos = pos + 1  # Insert after position pos



        # Apply best insertion

        current_suffix.insert(best_pos, v)

        deltas.append(best_delta)



    return tuple(current_suffix), total_evals, deltas







@dataclass(frozen=True)

class StepResult:

    """Result of a single simulation step (event + update)."""

    time_step: int

    event_vertices: frozenset[int]           # Δ_t revealed at this step

    known_vertices: frozenset[int]           # V_t after event

    previous_route: Route                    # S_{t-1}

    updated_route: Route                     # S_t after repair

    metrics: RouteMetrics                    # All metrics for this step

    strategy: Strategy                       # Strategy used

    repair_result: InsertionResult | InsertionTwoOptResult | DestroyRepairResult  # Detailed repair info





@dataclass(frozen=True)

class SimulationResult:

    """Complete result of a simulation run."""

    strategy: Strategy

    seed: int

    config: EventConfig

    event_sequence: EventSequence

    instance: Instance

    initial_state: DynamicState

    steps: tuple[StepResult, ...]

    final_route: Route

    final_metrics: RouteMetrics



    @property

    def num_events(self) -> int:

        return len(self.steps)



    @property

    def total_computational_effort(self) -> int:

        return sum(s.metrics.computational_effort for s in self.steps)

    @property
    def total_candidate_evaluations(self) -> int:
        return sum(s.metrics.candidate_evaluations for s in self.steps if s.metrics.candidate_evaluations is not None)

    @property
    def total_overhead_evaluations(self) -> int:
        return sum(s.metrics.overhead_evaluations for s in self.steps)



    @property

    def total_response_time_ms(self) -> float:

        return sum(s.metrics.response_time_ms for s in self.steps)



    @property

    def mean_disruption(self) -> float:

        if not self.steps:

            return 0.0

        return sum(s.metrics.disruption for s in self.steps) / len(self.steps)



    @property

    def max_disruption(self) -> float:

        if not self.steps:

            return 0.0

        return max(s.metrics.disruption for s in self.steps)



    @property

    def all_feasible(self) -> bool:

        return all(s.metrics.feasible for s in self.steps)



    def get_route_at_step(self, t: int) -> Route:

        """Get route S_t at time step t (0 = initial, 1 = after first event, etc.)."""

        if t == 0:

            return self.initial_state.current_route

        if 1 <= t <= len(self.steps):

            return self.steps[t - 1].updated_route

        raise IndexError(f"Step {t} out of range [0, {len(self.steps)}]")



    def get_metrics_at_step(self, t: int) -> RouteMetrics:

        """Get metrics at time step t."""

        if t == 0:

            # Initial step has no disruption, no computational effort

            return evaluate_route(

                self.initial_state.current_route,

                self.instance,

                prev_route=None,

                required_vertices=self.initial_state.get_required_vertices_for_feasibility(),

                computational_effort=0,

                response_time_ms=0.0,

            )

        if 1 <= t <= len(self.steps):

            return self.steps[t - 1].metrics

        raise IndexError(f"Step {t} out of range [0, {len(self.steps)}]")





class Simulator:

    """Event-driven simulator for dynamic routing experiments.



    Runs a complete simulation: initial solution -> event loop -> strategy updates.

    Ensures identical instance and event sequence for all strategies.

    """



    def __init__(

        self,

        instance: Instance,

        event_sequence: EventSequence,

        freeze_per_step: int = 1,

        max_passes: Optional[int] = None,

        max_evaluations: Optional[int] = None,

        strategy_a_func: Optional[Callable] = None,

        strategy_b_func: Optional[Callable] = None,

        strategy_c_func: Optional[Callable] = None,

        destroy_repair_config: Optional[DestroyRepairConfig] = None,

        selector: Optional[Any] = None,

    ) -> None:

        """Initialize simulator.



        Args:

            instance: Full problem instance (hidden from strategies).

            event_sequence: Deterministic event sequence.

            freeze_per_step: Vertices to advance in frozen prefix per step (default 1).

            max_passes: Optional limit on 2-opt passes per update (budget control).

            max_evaluations: Optional limit on evaluations per update (budget control).

            strategy_a_func: Custom Strategy A function (default: greedy_insertion_repair).

            strategy_b_func: Custom Strategy B function (default: strategy_b_repair).

            selector: Optional AdaptiveSelector instance for Strategy.ADAPTIVE (Phase 8).

        """

        self.instance = instance

        self.event_sequence = event_sequence

        self.freeze_per_step = freeze_per_step

        self.max_passes = max_passes

        self.max_evaluations = max_evaluations

        self.selector = selector

        self._strategy_a = strategy_a_func or greedy_insertion_repair

        self._strategy_b = strategy_b_func or strategy_b_repair

        self.destroy_repair_config = destroy_repair_config

        self._strategy_c = strategy_c_func or strategy_c_repair



    def run(self, strategy: Strategy, seed: int = 0) -> SimulationResult:

        """Run a complete simulation with the given strategy.



        Args:

            strategy: Strategy.A or Strategy.B.

            seed: Random seed (used for any stochastic components; currently deterministic).



        Returns:

            SimulationResult with complete trajectory and metrics.

        """

        # Create initial state (t=0)

        initial_state = create_initial_state(

            self.instance,

            set(self.event_sequence.initial_known),

            seed=seed,

        )



        # Verify initial state is valid

        valid, errors = initial_state.validate()

        if not valid:

            raise ValueError(f"Invalid initial state: {errors}")



        steps = []

        current_state = initial_state



        # Process each event step

        for t in range(self.event_sequence.num_event_steps):

            # Get event Δ_t

            event_vertices = self.event_sequence.get_event_at_step(t)



            # Add new vertices to known set

            current_state = current_state.with_new_vertices(event_vertices)



            # Apply strategy to update route

            repair_result, updated_route, metrics = self._apply_strategy(

                strategy, current_state, event_vertices, seed=seed

            )



            # Invariant check: committed frozen prefix must remain strictly unchanged

            frozen_prefix = current_state.get_frozen_prefix_vertices()

            if updated_route.vertices[: len(frozen_prefix)] != frozen_prefix:

                raise RuntimeError(

                    f"Frozen prefix invariant violated at step {t+1} by strategy {strategy.value}: "

                    f"expected {frozen_prefix}, got {updated_route.vertices[: len(frozen_prefix)]}"

                )



            # Record step result

            step_result = StepResult(

                time_step=t + 1,

                event_vertices=event_vertices,

                known_vertices=current_state.known_vertices,

                previous_route=current_state.current_route,

                updated_route=updated_route,

                metrics=metrics,

                strategy=strategy,

                repair_result=repair_result,

            )

            steps.append(step_result)



            # Update state with new route

            current_state = current_state.with_updated_route(updated_route)



            # Advance time step

            current_state = current_state.with_advanced_time(t + 1)



            # Advance frozen prefix (vehicle moves along route)

            current_state = current_state.advance_frozen_prefix(self.freeze_per_step)



            # Validate state after each step

            valid, errors = current_state.validate()

            if not valid:

                raise ValueError(f"Invalid state at step {t+1}: {errors}")



        # Final metrics

        final_metrics = evaluate_route(

            current_state.current_route,

            self.instance,

            prev_route=steps[-1].previous_route if steps else None,

            required_vertices=current_state.get_required_vertices_for_feasibility(),

            computational_effort=sum(s.metrics.computational_effort for s in steps),
            candidate_evaluations=sum(s.metrics.candidate_evaluations for s in steps if s.metrics.candidate_evaluations is not None),
            overhead_evaluations=sum(s.metrics.overhead_evaluations for s in steps),

            response_time_ms=sum(s.metrics.response_time_ms for s in steps),

        )



        return SimulationResult(

            strategy=strategy,

            seed=seed,

            config=self.event_sequence.config,

            event_sequence=self.event_sequence,

            instance=self.instance,

            initial_state=initial_state,

            steps=tuple(steps),

            final_route=current_state.current_route,

            final_metrics=final_metrics,

        )



    def _apply_strategy(

        self,

        strategy: Strategy,

        state: DynamicState,

        new_vertices: frozenset[int],

        seed: int = 0,

    ) -> tuple[InsertionResult | InsertionTwoOptResult | DestroyRepairResult, Route, RouteMetrics]:

        """Apply the specified strategy to update the route.



        Handles frozen-prefix rule: only uncommitted suffix may be modified.

        """

        # Get uncommitted suffix vertices for repair

        suffix_vertices = state.get_uncommitted_suffix_vertices()

        frozen_prefix = state.get_frozen_prefix_vertices()



        # Convert new_vertices to sorted list for deterministic processing

        sorted_new = sorted(new_vertices)



        # Handle Adaptive Strategy Selection (Phase 8)

        overhead_evals = 0

        effective_strategy = strategy

        if strategy in (Strategy.ADAPTIVE, Strategy.ADAPTIVE_V2, Strategy.ADAPTIVE_V3):

            from adaptive_route_optimization.algorithms.adaptive.features import extract_features

            from adaptive_route_optimization.algorithms.adaptive.selector import (
                AdaptiveSelector,
                SelectorConfig,
                StrategyChoice,
            )

            if self.selector is not None:
                sel = self.selector
            elif strategy == Strategy.ADAPTIVE_V2:
                sel = AdaptiveSelector(SelectorConfig(name="rule_v2_budget_aware", version="v2"))
            else:
                sel = AdaptiveSelector(SelectorConfig(name="rule_v3_three_strategy", version="v3"))

            features = extract_features(

                state=state,

                new_vertices=new_vertices,

                total_vertices=self.event_sequence.config.total_vertices,

                initial_known_count=len(self.event_sequence.initial_known) - 1,

                remaining_eval_budget=self.max_evaluations,

            )

            decision = sel.select(features)

            if decision.chosen_strategy == StrategyChoice.A:
                effective_strategy = Strategy.A
            elif decision.chosen_strategy == StrategyChoice.B:
                effective_strategy = Strategy.B
            elif decision.chosen_strategy == StrategyChoice.C:
                effective_strategy = Strategy.C
            else:
                raise ValueError(f"Unknown chosen strategy: {decision.chosen_strategy}")

            overhead_evals = decision.overhead_evaluations

            if self.max_evaluations is not None and self.max_evaluations == 0:

                overhead_evals = 0



        eff_max_evals = self.max_evaluations

        if eff_max_evals is not None and overhead_evals > 0:

            eff_max_evals = max(0, eff_max_evals - overhead_evals)



        if effective_strategy == Strategy.A:

            with TimedOperation() as timer:

                updated_suffix, ins_evals, ins_deltas = cheapest_insertion_on_suffix(

                    state.instance, suffix_vertices, sorted_new, max_evaluations=eff_max_evals

                )

            full_route = state.reconstruct_route_from_suffix(updated_suffix)

            computational_effort = ins_evals + overhead_evals

            repair_result = InsertionResult(

                route=full_route,

                cost=full_route.cost(state.instance),

                candidate_evaluations=computational_effort,

                deltas=ins_deltas,

            )



        elif effective_strategy == Strategy.B:

            with TimedOperation() as timer:

                # Suffix insertion with budget limit

                updated_suffix, ins_evals, ins_deltas = cheapest_insertion_on_suffix(

                    state.instance, suffix_vertices, sorted_new, max_evaluations=eff_max_evals

                )

                temp_route = state.reconstruct_route_from_suffix(updated_suffix)



                remaining_evals = None

                if eff_max_evals is not None:

                    remaining_evals = max(0, eff_max_evals - ins_evals)



                # Suffix-only 2-opt preserving frozen prefix (min_i = state.frozen_prefix_length)

                two_opt_result = two_opt(

                    state.instance,

                    temp_route,

                    max_passes=self.max_passes,

                    max_evaluations=remaining_evals,

                    min_i=state.frozen_prefix_length,

                )

                final_route = two_opt_result.route

                computational_effort = ins_evals + two_opt_result.candidate_evaluations + overhead_evals



            full_route = final_route

            repair_result = InsertionTwoOptResult(

                route=final_route,

                cost=final_route.cost(state.instance),

                insertion_evaluations=ins_evals,

                two_opt_evaluations=two_opt_result.candidate_evaluations,

                total_evaluations=computational_effort,

                insertion_deltas=ins_deltas,

                two_opt_accepted_moves=two_opt_result.accepted_moves,

                two_opt_passes=two_opt_result.passes,

            )



        elif effective_strategy == Strategy.C:

            import dataclasses

            if self.destroy_repair_config is not None:

                if self.destroy_repair_config.seed is not None:

                    cfg = self.destroy_repair_config

                else:

                    cfg = dataclasses.replace(self.destroy_repair_config, seed=seed)

            else:

                cfg = DestroyRepairConfig(seed=seed)



            with TimedOperation() as timer:

                c_res = self._strategy_c(

                    instance=state.instance,

                    current_route=state.current_route,

                    frozen_prefix_length=state.frozen_prefix_length,

                    new_vertices=sorted_new,

                    config=cfg,

                    max_evaluations=eff_max_evals,

                )

            full_route = c_res.route

            computational_effort = c_res.total_evaluations + overhead_evals

            repair_result = c_res



        else:

            raise ValueError(f"Unknown strategy: {strategy}")



        # Compute candidate evaluations (excluding selector overhead)
        pure_candidate_evals = max(0, computational_effort - overhead_evals)

        # Compute metrics
        metrics = evaluate_route(
            full_route,
            state.instance,
            prev_route=state.current_route,
            required_vertices=state.get_required_vertices_for_feasibility(),
            computational_effort=computational_effort,
            response_time_ms=timer.elapsed_ms,
            candidate_evaluations=pure_candidate_evals,
            overhead_evaluations=overhead_evals,
        )
        return repair_result, full_route, metrics



    def run_both_strategies(self, seed: int = 0) -> tuple[SimulationResult, SimulationResult]:

        """Run both strategies on the same instance and event sequence.



        This is the core requirement: identical instance, identical events,

        different strategies. Enables fair comparison.



        Args:

            seed: Random seed for reproducibility.



        Returns:

            Tuple of (result_A, result_B).

        """

        result_a = self.run(Strategy.A, seed=seed)

        result_b = self.run(Strategy.B, seed=seed)

        return result_a, result_b



    def run_all_strategies(self, seed: int = 0) -> tuple[SimulationResult, SimulationResult, SimulationResult]:

        """Run Strategy A, Strategy B, and Strategy ADAPTIVE on the same instance and event sequence.



        Enforces fair comparison across all three policies under identical conditions.

        """

        result_a = self.run(Strategy.A, seed=seed)

        result_b = self.run(Strategy.B, seed=seed)

        result_adapt = self.run(Strategy.ADAPTIVE, seed=seed)

        return result_a, result_b, result_adapt





def run_simulation(

    instance: Instance,

    event_sequence: EventSequence,

    strategy: Strategy,

    freeze_per_step: int = 1,

    max_passes: Optional[int] = None,

    max_evaluations: Optional[int] = None,

    destroy_repair_config: Optional[DestroyRepairConfig] = None,

    seed: int = 0,

) -> SimulationResult:

    """Convenience function to run a single simulation."""

    sim = Simulator(

        instance,

        event_sequence,

        freeze_per_step=freeze_per_step,

        max_passes=max_passes,

        max_evaluations=max_evaluations,

        destroy_repair_config=destroy_repair_config,

    )

    return sim.run(strategy, seed=seed)





def run_both_strategies(

    instance: Instance,

    event_sequence: EventSequence,

    freeze_per_step: int = 1,

    max_passes: Optional[int] = None,

    max_evaluations: Optional[int] = None,

    seed: int = 0,

) -> tuple[SimulationResult, SimulationResult]:

    """Convenience function to run both strategies."""

    sim = Simulator(

        instance,

        event_sequence,

        freeze_per_step=freeze_per_step,

        max_passes=max_passes,

        max_evaluations=max_evaluations,

    )

    return sim.run_both_strategies(seed=seed)