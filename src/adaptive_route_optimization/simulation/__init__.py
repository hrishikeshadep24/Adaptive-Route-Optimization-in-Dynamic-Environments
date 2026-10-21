"""Simulation Package for Dynamic Routing.

Provides event-driven simulation, dynamic state management, event generation,
replay system, logging, and debugging animation.

Phase 5 deliverables:
- Event-driven simulator
- Dynamic state model
- Replay system
- Event logs
- Animated route-state prototype (debugging only)
"""

from adaptive_route_optimization.simulation.state import (
    DynamicState,
    create_initial_state,
)

from adaptive_route_optimization.simulation.events import (
    EventConfig,
    EventSequence,
    EventGenerator,
    generate_event_sequence,
)

from adaptive_route_optimization.simulation.simulator import (
    Strategy,
    StepResult,
    SimulationResult,
    Simulator,
    run_simulation,
    run_both_strategies,
)

from adaptive_route_optimization.simulation.replay import (
    ReplayConfig,
    Replay,
    replay_from_config,
    verify_replay,
    replay_from_original,
    verify_replay_exact,
)

from adaptive_route_optimization.simulation.logging import (
    LogEntry,
    SimulationLog,
    SimulationLogger,
    create_logger_from_result,
    log_to_csv,
)

from adaptive_route_optimization.simulation.animation import (
    AnimationConfig,
    animate_route_state,
    plot_route_evolution,
    create_animation_from_log,
)

__all__ = [
    # State
    "DynamicState",
    "create_initial_state",
    # Events
    "EventConfig",
    "EventSequence",
    "EventGenerator",
    "generate_event_sequence",
    # Simulator
    "Strategy",
    "StepResult",
    "SimulationResult",
    "Simulator",
    "run_simulation",
    "run_both_strategies",
    # Replay
    "ReplayConfig",
    "Replay",
    "replay_from_config",
    "verify_replay",
    "replay_from_original",
    "verify_replay_exact",
    # Logging
    "LogEntry",
    "SimulationLog",
    "SimulationLogger",
    "create_logger_from_result",
    "log_to_csv",
    # Animation (debugging)
    "AnimationConfig",
    "animate_route_state",
    "plot_route_evolution",
    "create_animation_from_log",
]