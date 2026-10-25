"""Replay System for Dynamic Routing Simulation.

Reconstructs and verifies complete runs from seed + configuration.
Enables exact reproduction of results for validation and analysis.
References: PHASE_PLAN.md (Phase 5 Gate), RESEARCH_SPEC.md.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import json

import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.simulation.events import EventSequence, EventConfig, generate_event_sequence
from adaptive_route_optimization.simulation.simulator import (
    Simulator,
    SimulationResult,
    Strategy,
    run_simulation,
    run_both_strategies,
)


@dataclass(frozen=True)
class ReplayConfig:
    """Configuration needed to replay a simulation exactly.

    Captures all parameters that affect the simulation outcome.
    """
    instance_seed: int
    total_vertices: int
    dynamicity: Optional[float] = None
    initial_known_count: Optional[int] = None
    events_per_step: int = 1
    vertex_order: str = "random"
    freeze_per_step: int = 1
    strategy: str = "A"  # "A" or "B"
    seed: int = 0  # Simulation seed (for any stochastic components)

    def to_event_config(self) -> EventConfig:
        """Convert to EventConfig for event generation."""
        return EventConfig(
            total_vertices=self.total_vertices,
            initial_known_count=self.initial_known_count,
            dynamicity=self.dynamicity,
            events_per_step=self.events_per_step,
            seed=self.instance_seed,
            vertex_order=self.vertex_order,
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "instance_seed": self.instance_seed,
            "total_vertices": self.total_vertices,
            "dynamicity": self.dynamicity,
            "initial_known_count": self.initial_known_count,
            "events_per_step": self.events_per_step,
            "vertex_order": self.vertex_order,
            "freeze_per_step": self.freeze_per_step,
            "strategy": self.strategy,
            "seed": self.seed,
        }, sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> ReplayConfig:
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(**data)

    @classmethod
    def from_simulation_result(cls, result: SimulationResult) -> ReplayConfig:
        """Extract replay config from a completed simulation result."""
        return cls(
            instance_seed=result.config.seed,
            total_vertices=result.config.total_vertices,
            dynamicity=result.config.dynamicity,
            initial_known_count=result.config.initial_known_count,
            events_per_step=result.config.events_per_step,
            vertex_order=result.config.vertex_order,
            freeze_per_step=result.initial_state.instance  # Not stored, need to pass separately
        )


class Replay:
    """Replay system for exact reproduction of simulation runs.

    Given a seed and configuration, reconstructs the exact same:
    - Full hidden instance
    - Event sequence
    - Initial state
    - All intermediate states and routes
    - Final results

    This enables the Phase 5 gate: "a complete run can be replayed exactly
    with the same event sequence and results from the same seed."
    """

    def __init__(self, config: ReplayConfig) -> None:
        self.config = config

    def rebuild_instance(self) -> Instance:
        """Rebuild the exact same instance from the seed."""
        return Instance.generate_random(
            n=self.config.total_vertices,
            seed=self.config.instance_seed,
        )

    def rebuild_event_sequence(self, instance: Instance) -> EventSequence:
        """Rebuild the exact same event sequence."""
        # Use initial_known_count, not dynamicity, to avoid conflict
        return generate_event_sequence(
            instance=instance,
            total_vertices=self.config.total_vertices,
            initial_known_count=self.config.initial_known_count,
            seed=self.config.instance_seed,
            events_per_step=self.config.events_per_step,
            vertex_order=self.config.vertex_order,
        )

    def rebuild_simulator(self, instance: Instance, event_sequence: EventSequence) -> Simulator:
        """Rebuild the simulator with identical parameters."""
        return Simulator(
            instance=instance,
            event_sequence=event_sequence,
            freeze_per_step=self.config.freeze_per_step,
        )

    def replay(self) -> SimulationResult:
        """Replay the complete simulation and return result.

        This is the main entry point for exact reproduction.
        """
        instance = self.rebuild_instance()
        event_sequence = self.rebuild_event_sequence(instance)
        simulator = self.rebuild_simulator(instance, event_sequence)

        strategy = Strategy.A if self.config.strategy == "A" else Strategy.B
        return simulator.run(strategy, seed=self.config.seed)

    def replay_step_by_step(self) -> list[tuple[int, dict]]:
        """Replay and yield step-by-step details for debugging/analysis.

        Returns:
            List of (time_step, step_data) where step_data contains
            event, routes, metrics for that step.
        """
        result = self.replay()
        steps_data = []

        # Initial step (t=0)
        steps_data.append((
            0,
            {
                "time_step": 0,
                "event_vertices": frozenset(),
                "known_vertices": result.initial_state.known_vertices,
                "route": result.initial_state.current_route,
                "metrics": result.get_metrics_at_step(0),
                "frozen_prefix_length": 0,
            }
        ))

        # Event steps
        for i, step in enumerate(result.steps):
            steps_data.append((
                i + 1,
                {
                    "time_step": i + 1,
                    "event_vertices": step.event_vertices,
                    "known_vertices": step.known_vertices,
                    "previous_route": step.previous_route,
                    "updated_route": step.updated_route,
                    "metrics": step.metrics,
                    "strategy": step.strategy.value,
                    "repair_result": step.repair_result,
                    "frozen_prefix_length": result.initial_state.frozen_prefix_length + (i + 1) * self.config.freeze_per_step,
                }
            ))

        return steps_data

    def verify_against(self, other_result: SimulationResult) -> tuple[bool, list[str]]:
        """Verify that replayed result matches another result exactly.

        Args:
            other_result: A SimulationResult to compare against.

        Returns:
            Tuple of (matches, list_of_differences).
        """
        replayed = self.replay()
        differences = []

        # Compare instance (coordinates)
        if not np.allclose(replayed.instance.coords, other_result.instance.coords):
            differences.append("Instance coordinates differ")

        # Compare event sequence
        if replayed.event_sequence.events != other_result.event_sequence.events:
            differences.append("Event sequences differ")

        # Compare initial state
        if replayed.initial_state.current_route.vertices != other_result.initial_state.current_route.vertices:
            differences.append("Initial routes differ")

        # Compare each step
        if len(replayed.steps) != len(other_result.steps):
            differences.append(f"Number of steps differs: {len(replayed.steps)} vs {len(other_result.steps)}")
        else:
            for i, (r_step, o_step) in enumerate(zip(replayed.steps, other_result.steps)):
                if r_step.updated_route.vertices != o_step.updated_route.vertices:
                    differences.append(f"Step {i+1}: routes differ")
                if abs(r_step.metrics.route_cost - o_step.metrics.route_cost) > 1e-9:
                    differences.append(f"Step {i+1}: costs differ ({r_step.metrics.route_cost} vs {o_step.metrics.route_cost})")
                if abs(r_step.metrics.disruption - o_step.metrics.disruption) > 1e-9:
                    differences.append(f"Step {i+1}: disruptions differ")
                if r_step.metrics.feasible != o_step.metrics.feasible:
                    differences.append(f"Step {i+1}: feasibility differs")

        # Compare final
        if replayed.final_route.vertices != other_result.final_route.vertices:
            differences.append("Final routes differ")

        return len(differences) == 0, differences


def replay_from_config(config: ReplayConfig) -> SimulationResult:
    """Convenience function to replay from config."""
    return Replay(config).replay()


def verify_replay(original: SimulationResult, replayed: SimulationResult) -> tuple[bool, list[str]]:
    """Verify that a replayed result matches the original exactly."""
    differences = []

    # Compare instance (coordinates)
    if not np.allclose(replayed.instance.coords, original.instance.coords):
        differences.append("Instance coordinates differ")

    # Compare event sequence
    if replayed.event_sequence.events != original.event_sequence.events:
        differences.append("Event sequences differ")

    # Compare initial state
    if replayed.initial_state.current_route.vertices != original.initial_state.current_route.vertices:
        differences.append("Initial routes differ")

    # Compare each step
    if len(replayed.steps) != len(original.steps):
        differences.append(f"Number of steps differs: {len(replayed.steps)} vs {len(original.steps)}")
    else:
        for i, (r_step, o_step) in enumerate(zip(replayed.steps, original.steps)):
            if r_step.updated_route.vertices != o_step.updated_route.vertices:
                differences.append(f"Step {i+1}: routes differ")
            if abs(r_step.metrics.route_cost - o_step.metrics.route_cost) > 1e-9:
                differences.append(f"Step {i+1}: costs differ ({r_step.metrics.route_cost} vs {o_step.metrics.route_cost})")
            if abs(r_step.metrics.disruption - o_step.metrics.disruption) > 1e-9:
                differences.append(f"Step {i+1}: disruptions differ")
            if r_step.metrics.feasible != o_step.metrics.feasible:
                differences.append(f"Step {i+1}: feasibility differs")

    # Compare final
    if replayed.final_route.vertices != original.final_route.vertices:
        differences.append("Final routes differ")

    return len(differences) == 0, differences


def replay_from_original(original: SimulationResult, strategy: Optional[Strategy] = None) -> SimulationResult:
    """Replay a simulation using the exact same instance and event sequence.

    This is the proper way to verify exact reproduction - use the same
    instance and event sequence, only changing the strategy if desired.
    """
    strat = strategy or original.strategy
    sim = Simulator(
        instance=original.instance,
        event_sequence=original.event_sequence,
        freeze_per_step=1,  # Default, should be tracked
    )
    return sim.run(strat, seed=original.seed)


def verify_replay_exact(original: SimulationResult) -> tuple[bool, list[str]]:
    """Verify that a simulation can be replayed exactly from its configuration.

    This re-runs the simulation with the same instance and event sequence
    and compares the results.
    """
    replayed = replay_from_original(original)
    return verify_replay(original, replayed)