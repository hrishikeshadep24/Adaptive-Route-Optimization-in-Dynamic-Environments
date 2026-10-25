"""Logging for Dynamic Routing Simulation.

Captures every event, route state, and metric for analysis and reproducibility.
References: PHASE_PLAN.md (Phase 5 deliverables: event logs), RESEARCH_SPEC.md (Metrics).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json
from datetime import datetime

import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.evaluation.metrics import RouteMetrics
from adaptive_route_optimization.simulation.simulator import (
    SimulationResult,
    StepResult,
    Strategy,
)
from adaptive_route_optimization.simulation.events import EventSequence, EventConfig


@dataclass
class LogEntry:
    """Single log entry for one simulation step."""
    time_step: int
    timestamp: str  # ISO format
    event_vertices: list[int]      # Δ_t revealed at this step
    known_vertices: list[int]      # V_t after event
    previous_route: list[int]      # S_{t-1}
    updated_route: list[int]       # S_t after repair
    strategy: str                  # "A" or "B"
    metrics: dict                  # RouteMetrics as dict
    repair_details: dict           # Strategy-specific details
    frozen_prefix_length: int      # f_t at this step

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class SimulationLog:
    """Complete log of a simulation run."""
    strategy: str
    seed: int
    instance_seed: int
    total_vertices: int
    dynamicity: Optional[float]
    initial_known_count: int
    events_per_step: int
    freeze_per_step: int
    vertex_order: str
    start_time: str
    end_time: Optional[str] = None
    entries: list[LogEntry] = field(default_factory=list)
    final_route: Optional[list[int]] = None
    final_metrics: Optional[dict] = None
    config_hash: Optional[str] = None

    def add_entry(self, entry: LogEntry) -> None:
        """Add a step entry to the log."""
        self.entries.append(entry)

    def finalize(self, result: SimulationResult) -> None:
        """Finalize log with final results."""
        self.end_time = datetime.now().isoformat()
        self.final_route = list(result.final_route.vertices)
        self.final_metrics = {
            "route_cost": result.final_metrics.route_cost,
            "disruption": result.final_metrics.disruption,
            "feasible": result.final_metrics.feasible,
            "computational_effort": result.final_metrics.computational_effort,
            "response_time_ms": result.final_metrics.response_time_ms,
        }

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "strategy": self.strategy,
            "seed": self.seed,
            "instance_seed": self.instance_seed,
            "total_vertices": self.total_vertices,
            "dynamicity": self.dynamicity,
            "initial_known_count": self.initial_known_count,
            "events_per_step": self.events_per_step,
            "freeze_per_step": self.freeze_per_step,
            "vertex_order": self.vertex_order,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "entries": [e.to_dict() for e in self.entries],
            "final_route": self.final_route,
            "final_metrics": self.final_metrics,
            "config_hash": self.config_hash,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: str) -> None:
        """Save log to JSON file."""
        with open(filepath, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, filepath: str) -> SimulationLog:
        """Load log from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        log = cls(
            strategy=data["strategy"],
            seed=data["seed"],
            instance_seed=data["instance_seed"],
            total_vertices=data["total_vertices"],
            dynamicity=data["dynamicity"],
            initial_known_count=data["initial_known_count"],
            events_per_step=data["events_per_step"],
            freeze_per_step=data["freeze_per_step"],
            vertex_order=data["vertex_order"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            final_route=data.get("final_route"),
            final_metrics=data.get("final_metrics"),
            config_hash=data.get("config_hash"),
        )
        log.entries = [LogEntry(**e) for e in data.get("entries", [])]
        return log


class SimulationLogger:
    """Logs simulation runs with full detail for analysis and reproducibility."""

    def __init__(
        self,
        strategy: Strategy,
        seed: int,
        instance: Instance,
        event_sequence: EventSequence,
        freeze_per_step: int = 1,
    ) -> None:
        """Initialize logger with simulation configuration."""
        self.log = SimulationLog(
            strategy=strategy.value,
            seed=seed,
            instance_seed=event_sequence.config.seed,
            total_vertices=event_sequence.config.total_vertices,
            dynamicity=event_sequence.config.dynamicity,
            initial_known_count=len(event_sequence.initial_known) - 1,  # exclude depot
            events_per_step=event_sequence.config.events_per_step,
            freeze_per_step=freeze_per_step,
            vertex_order=event_sequence.config.vertex_order,
            start_time=datetime.now().isoformat(),
        )
        self._instance = instance
        self._event_sequence = event_sequence

    def log_initial_state(self, initial_state) -> None:
        """Log the initial state (t=0)."""
        from adaptive_route_optimization.evaluation.metrics import evaluate_route

        metrics = evaluate_route(
            initial_state.current_route,
            self._instance,
            prev_route=None,
            required_vertices=initial_state.get_required_vertices_for_feasibility(),
            computational_effort=0,
            response_time_ms=0.0,
        )

        entry = LogEntry(
            time_step=0,
            timestamp=datetime.now().isoformat(),
            event_vertices=[],
            known_vertices=sorted(initial_state.known_vertices),
            previous_route=[],
            updated_route=list(initial_state.current_route.vertices),
            strategy=self.log.strategy,
            metrics={
                "route_cost": metrics.route_cost,
                "disruption": metrics.disruption,
                "feasible": metrics.feasible,
                "computational_effort": metrics.computational_effort,
                "response_time_ms": metrics.response_time_ms,
            },
            repair_details={},
            frozen_prefix_length=initial_state.frozen_prefix_length,
        )
        self.log.add_entry(entry)

    def log_step(self, step_result: StepResult, frozen_prefix_length: int) -> None:
        """Log a simulation step result."""
        # Extract repair details based on strategy
        repair_details = {}
        if self.log.strategy == "greedy_insertion":  # Strategy.A.value
            repair_details = {
                "candidate_evaluations": step_result.repair_result.candidate_evaluations,
                "deltas": step_result.repair_result.deltas,
            }
        else:  # Strategy B: "insertion_two_opt"
            repair_details = {
                "insertion_evaluations": step_result.repair_result.insertion_evaluations,
                "two_opt_evaluations": step_result.repair_result.two_opt_evaluations,
                "total_evaluations": step_result.repair_result.total_evaluations,
                "insertion_deltas": step_result.repair_result.insertion_deltas,
                "two_opt_accepted_moves": step_result.repair_result.two_opt_accepted_moves,
                "two_opt_passes": step_result.repair_result.two_opt_passes,
            }

        entry = LogEntry(
            time_step=step_result.time_step,
            timestamp=datetime.now().isoformat(),
            event_vertices=sorted(step_result.event_vertices),
            known_vertices=sorted(step_result.known_vertices),
            previous_route=list(step_result.previous_route.vertices),
            updated_route=list(step_result.updated_route.vertices),
            strategy=self.log.strategy,
            metrics={
                "route_cost": step_result.metrics.route_cost,
                "disruption": step_result.metrics.disruption,
                "feasible": step_result.metrics.feasible,
                "computational_effort": step_result.metrics.computational_effort,
                "response_time_ms": step_result.metrics.response_time_ms,
            },
            repair_details=repair_details,
            frozen_prefix_length=frozen_prefix_length,
        )
        self.log.add_entry(entry)

    def finalize(self, result: SimulationResult) -> SimulationLog:
        """Finalize and return the complete log."""
        self.log.finalize(result)
        return self.log

    def get_log(self) -> SimulationLog:
        """Get the current log (before finalizing)."""
        return self.log


def create_logger_from_result(result: SimulationResult) -> SimulationLogger:
    """Create a logger and populate it from a completed SimulationResult."""
    logger = SimulationLogger(
        strategy=result.strategy,
        seed=result.seed,
        instance=result.instance,
        event_sequence=result.event_sequence,  # EventSequence
        freeze_per_step=1,  # Default, should be tracked in result
    )

    # Log initial state
    logger.log_initial_state(result.initial_state)

    # Log each step
    for i, step in enumerate(result.steps):
        frozen_len = result.initial_state.frozen_prefix_length + (i + 1) * 1
        logger.log_step(step, frozen_len)

    # Finalize
    logger.finalize(result)

    return logger


def log_to_csv(log: SimulationLog, filepath: str) -> None:
    """Export simulation log to CSV for analysis.

    Creates a flat CSV with one row per time step.
    """
    import pandas as pd

    rows = []
    for entry in log.entries:
        row = {
            "time_step": entry.time_step,
            "timestamp": entry.timestamp,
            "strategy": entry.strategy,
            "num_event_vertices": len(entry.event_vertices),
            "num_known_vertices": len(entry.known_vertices),
            "route_length": len(entry.updated_route) - 1,  # edges
            "frozen_prefix_length": entry.frozen_prefix_length,
            "route_cost": entry.metrics["route_cost"],
            "disruption": entry.metrics["disruption"],
            "feasible": entry.metrics["feasible"],
            "computational_effort": entry.metrics["computational_effort"],
            "response_time_ms": entry.metrics["response_time_ms"],
        }
        # Add repair details
        for key, value in entry.repair_details.items():
            row[key] = value
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False)