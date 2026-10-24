"""Event Generator for Dynamic Routing Simulation.

Generates deterministic event sequences from a seed.
References: RESEARCH_SPEC.md (Dynamic State and Events, Dynamicity),
NOTATION.md (V_t, Δ_t, α), OPEN_QUESTIONS.md (#3, #16-20).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from adaptive_route_optimization.models.instance import Instance


@dataclass(frozen=True)
class EventConfig:
    """Configuration for event generation.

    Attributes:
        total_vertices: Total number of non-depot vertices (n).
        initial_known_count: Number of non-depot vertices in V_0.
        dynamicity: Fraction of non-depot vertices revealed after initial (α).
                    If specified, overrides initial_known_count.
        events_per_step: Number of vertices revealed per event step (|Δ_t|).
                         Default 1 (single vertex per event).
        seed: Random seed for reproducible generation.
        vertex_order: Order of vertex revelation. Options:
                      "random" - random permutation (deterministic from seed)
                      "index" - ascending vertex index
                      "distance" - by distance from depot
    """
    total_vertices: int
    initial_known_count: Optional[int] = None
    dynamicity: Optional[float] = None
    events_per_step: int = 1
    seed: int = 0
    vertex_order: str = "random"
    batch_schedule: Optional[tuple[int, ...]] = None

    def __post_init__(self) -> None:
        if self.total_vertices < 0:
            raise ValueError("total_vertices must be non-negative")
        if self.events_per_step < 1:
            raise ValueError("events_per_step must be at least 1")
        if self.vertex_order not in ("random", "index", "distance"):
            raise ValueError(f"Unknown vertex_order: {self.vertex_order}")
        if self.batch_schedule is not None:
            if not isinstance(self.batch_schedule, tuple):
                object.__setattr__(self, "batch_schedule", tuple(self.batch_schedule))
            for b_sz in self.batch_schedule:
                if b_sz < 0:
                    raise ValueError(f"Batch sizes in batch_schedule must be non-negative, got {b_sz}")

        # Validate dynamicity vs initial_known_count
        if self.dynamicity is not None:
            if not (0.0 <= self.dynamicity <= 1.0):
                raise ValueError("dynamicity must be in [0, 1]")
            # α = |V \ V_0| / |V \ {0}| => |V_0| = n * (1 - α) + 1 (depot)
            implied_initial = int(round(self.total_vertices * (1.0 - self.dynamicity)))
            if self.initial_known_count is not None and self.initial_known_count != implied_initial:
                raise ValueError(
                    f"initial_known_count ({self.initial_known_count}) conflicts with "
                    f"dynamicity ({self.dynamicity} -> {implied_initial})"
                )
            object.__setattr__(self, "initial_known_count", implied_initial)

        if self.initial_known_count is not None:
            if not (0 <= self.initial_known_count <= self.total_vertices):
                raise ValueError(
                    f"initial_known_count must be in [0, {self.total_vertices}]"
                )


@dataclass(frozen=True)
class EventSequence:
    """Complete deterministic event sequence for a simulation run.

    Attributes:
        initial_known: Set V_0 of initially known vertices (includes depot).
        events: List of events, each a set of vertex indices Δ_t.
        config: The EventConfig used to generate this sequence.
    """
    initial_known: frozenset[int]
    events: tuple[frozenset[int], ...]
    config: EventConfig

    @property
    def num_event_steps(self) -> int:
        """Number of event steps (time steps with Δ_t ≠ ∅)."""
        return len(self.events)

    @property
    def total_revealed(self) -> int:
        """Total non-depot vertices revealed across all events."""
        return sum(len(e) for e in self.events)

    def get_known_at_step(self, t: int) -> frozenset[int]:
        """Get V_t: known vertices after t event steps."""
        if t < 0:
            raise ValueError("t must be non-negative")
        if t == 0:
            return self.initial_known
        known = set(self.initial_known)
        for i in range(min(t, len(self.events))):
            known.update(self.events[i])
        return frozenset(known)

    def get_event_at_step(self, t: int) -> frozenset[int]:
        """Get Δ_t: vertices revealed at step t (0-indexed)."""
        if t < 0 or t >= len(self.events):
            return frozenset()
        return self.events[t]


class EventGenerator:
    """Generates deterministic event sequences from a seed.

    The full hidden instance V is fixed at generation time.
    Events reveal vertices from V \\ V_0 in deterministic order.
    """

    def __init__(self, config: EventConfig) -> None:
        self.config = config

    def generate(self, instance: Instance) -> EventSequence:
        """Generate a complete event sequence for the given instance.

        Args:
            instance: Full problem instance (provides coordinates for distance-based ordering).

        Returns:
            EventSequence with initial_known and list of events.
        """
        # Create fresh RNG for each generation to ensure determinism
        rng = np.random.default_rng(self.config.seed)
        
        n = self.config.total_vertices
        if instance.n != n:
            raise ValueError(f"Instance has {instance.n} vertices, config expects {n}")

        # Determine initial known count
        initial_count = self.config.initial_known_count
        if initial_count is None:
            initial_count = n // 2  # Default: 50% known initially

        # All non-depot vertices
        all_customers = list(range(1, n + 1))

        # Determine revelation order
        if self.config.vertex_order == "index":
            ordered_customers = all_customers
        elif self.config.vertex_order == "distance":
            # Sort by distance from depot
            distances = [(v, instance.cost(0, v)) for v in all_customers]
            distances.sort(key=lambda x: x[1])
            ordered_customers = [v for v, _ in distances]
        else:  # "random"
            ordered_customers = all_customers[:]
            rng.shuffle(ordered_customers)

        # Initial known: depot + first initial_count customers
        initial_known = frozenset([0] + ordered_customers[:initial_count])

        # Remaining vertices to reveal
        remaining = ordered_customers[initial_count:]

        # Generate events: batch remaining according to schedule or events_per_step
        events = []
        if self.config.batch_schedule is not None:
            curr_idx = 0
            for batch_size in self.config.batch_schedule:
                if curr_idx < len(remaining):
                    take = min(batch_size, len(remaining) - curr_idx)
                    batch = remaining[curr_idx : curr_idx + take]
                    curr_idx += take
                else:
                    batch = []
                events.append(frozenset(batch))
            if curr_idx < len(remaining):
                events.append(frozenset(remaining[curr_idx:]))
        else:
            for i in range(0, len(remaining), self.config.events_per_step):
                batch = remaining[i : i + self.config.events_per_step]
                events.append(frozenset(batch))

        return EventSequence(
            initial_known=initial_known,
            events=tuple(events),
            config=self.config,
        )

    @classmethod
    def from_dynamicity(
        cls,
        total_vertices: int,
        dynamicity: float,
        seed: int = 0,
        events_per_step: int = 1,
        vertex_order: str = "random",
        batch_schedule: Optional[tuple[int, ...]] = None,
    ) -> EventGenerator:
        """Convenience constructor using dynamicity level."""
        config = EventConfig(
            total_vertices=total_vertices,
            dynamicity=dynamicity,
            events_per_step=events_per_step,
            seed=seed,
            vertex_order=vertex_order,
            batch_schedule=batch_schedule,
        )
        return cls(config)

    @classmethod
    def from_initial_count(
        cls,
        total_vertices: int,
        initial_known_count: int,
        seed: int = 0,
        events_per_step: int = 1,
        vertex_order: str = "random",
        batch_schedule: Optional[tuple[int, ...]] = None,
    ) -> EventGenerator:
        """Convenience constructor using initial known count."""
        config = EventConfig(
            total_vertices=total_vertices,
            initial_known_count=initial_known_count,
            events_per_step=events_per_step,
            seed=seed,
            vertex_order=vertex_order,
            batch_schedule=batch_schedule,
        )
        return cls(config)


def generate_event_sequence(
    instance: Instance,
    total_vertices: int,
    dynamicity: Optional[float] = None,
    initial_known_count: Optional[int] = None,
    seed: int = 0,
    events_per_step: int = 1,
    vertex_order: str = "random",
    batch_schedule: Optional[tuple[int, ...]] = None,
) -> EventSequence:
    """Convenience function to generate event sequence in one call.

    Args:
        instance: Full problem instance.
        total_vertices: Total non-depot vertices (n).
        dynamicity: Fraction revealed after initial (α).
        initial_known_count: Alternative to dynamicity.
        seed: Random seed.
        events_per_step: Vertices per event step.
        vertex_order: Revelation order strategy.

    Returns:
        EventSequence for the simulation.
    """
    if dynamicity is not None and initial_known_count is not None:
        raise ValueError("Specify either dynamicity or initial_known_count, not both")

    config = EventConfig(
        total_vertices=total_vertices,
        dynamicity=dynamicity,
        initial_known_count=initial_known_count,
        events_per_step=events_per_step,
        seed=seed,
        vertex_order=vertex_order,
        batch_schedule=batch_schedule,
    )
    generator = EventGenerator(config)
    return generator.generate(instance)