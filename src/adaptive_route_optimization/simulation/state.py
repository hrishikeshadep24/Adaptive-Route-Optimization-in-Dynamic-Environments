"""Dynamic State Model for Dynamic Routing Simulation.

Tracks the known vertex set V_t, frozen prefix, current route, and time step.
References: RESEARCH_SPEC.md (Dynamic State and Events, Frozen-Prefix Rule),
NOTATION.md (V_t, f_t, S_t), PSEUDOCODE.md (UPDATE_WITH_FROZEN).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route, validate_route


@dataclass(frozen=True)
class DynamicState:
    """Complete dynamic state at time step t.

    Attributes:
        known_vertices: Set of vertex indices known at time t (includes depot 0).
        frozen_prefix_length: Number of vertices in frozen prefix (f_t).
                              The prefix includes the depot at position 0.
        current_route: Current route S_t covering known_vertices.
        time_step: Current discrete time step t.
        instance: Full problem instance (hidden from algorithms).
    """
    known_vertices: frozenset[int]
    frozen_prefix_length: int
    current_route: Route
    time_step: int
    instance: Instance

    def __post_init__(self) -> None:
        if 0 not in self.known_vertices:
            raise ValueError("Depot (0) must be in known_vertices")
        if self.frozen_prefix_length < 0:
            raise ValueError("frozen_prefix_length must be non-negative")
        if self.frozen_prefix_length >= len(self.current_route.vertices) - 1:
            # Allow full freeze (only depot-to-depot edge uncommitted)
            pass
        if self.time_step < 0:
            raise ValueError("time_step must be non-negative")

    @property
    def num_known_customers(self) -> int:
        """Number of known non-depot vertices."""
        return len(self.known_vertices) - 1  # exclude depot

    @property
    def is_fully_frozen(self) -> bool:
        """True if entire route except depot-to-depot edge is frozen."""
        # Route has len(vertices) = num_edges + 1
        # Frozen prefix length f means first f+1 vertices are frozen (including depot)
        # Uncommitted suffix starts at index f
        # Fully frozen when f >= num_edges - 1 = len(vertices) - 2
        max_frozen = len(self.current_route.vertices) - 2
        return self.frozen_prefix_length >= max_frozen

    def get_uncommitted_suffix_vertices(self) -> tuple[int, ...]:
        """Return the uncommitted suffix vertices for repair.

        Per RESEARCH_SPEC.md Frozen-Prefix Rule:
        S_t = (0, p_1, ..., p_f, u_1, ..., u_k, 0)
        where (p_1, ..., p_f) is frozen prefix.

        The suffix for repair is (p_f, u_1, ..., u_k, 0) starting from the
        last frozen vertex. This allows re-routing from the last committed point.

        Returns:
            Tuple of vertex indices representing the suffix path.
        """
        if self.is_fully_frozen:
            # If fully frozen, return minimal path from last frozen vertex to depot
            last_frozen_idx = min(self.frozen_prefix_length, len(self.current_route.vertices) - 2)
            last_frozen = self.current_route.vertices[last_frozen_idx]
            return (last_frozen, 0)

        # Suffix starts at frozen_prefix_length (the last frozen vertex)
        # and goes to the end (including return to depot)
        return self.current_route.vertices[self.frozen_prefix_length:]

    def get_uncommitted_suffix(self) -> Route:
        """Return the uncommitted suffix as a Route (for backward compatibility).

        Note: This may not be a valid Route (doesn't start at depot) if frozen.
        Prefer using get_uncommitted_suffix_vertices() for repair operations.
        """
        suffix_vertices = self.get_uncommitted_suffix_vertices()
        # Only return as Route if it starts with depot (frozen_prefix_length == 0)
        if suffix_vertices[0] == 0:
            return Route(suffix_vertices)
        # Otherwise, this is not a standard Route - caller should use vertices directly
        raise ValueError("Suffix does not start at depot; use get_uncommitted_suffix_vertices()")

    def get_frozen_prefix_vertices(self) -> tuple[int, ...]:
        """Return the frozen prefix vertices (including depot at index 0)."""
        # Frozen prefix includes indices 0 to frozen_prefix_length (inclusive)
        # This gives f+1 vertices: depot + f customers
        end_idx = self.frozen_prefix_length + 1
        return self.current_route.vertices[:end_idx]

    def advance_frozen_prefix(self, steps: int = 1) -> DynamicState:
        """Advance the frozen prefix by given number of steps.

        Per RESEARCH_SPEC.md: "After each event step, the vehicle 'travels'
        one edge of the current route, moving the next vertex from uncommitted
        to frozen. Default: 1 vertex per event step."

        Args:
            steps: Number of vertices to advance (default 1).

        Returns:
            New DynamicState with advanced frozen prefix.
        """
        new_frozen = self.frozen_prefix_length + steps
        # Cap at maximum possible (route length - 1 = last vertex before final depot)
        max_frozen = len(self.current_route.vertices) - 2
        new_frozen = min(new_frozen, max_frozen)

        return DynamicState(
            known_vertices=self.known_vertices,
            frozen_prefix_length=new_frozen,
            current_route=self.current_route,
            time_step=self.time_step,
            instance=self.instance,
        )

    def with_new_vertices(self, new_vertices: set[int]) -> DynamicState:
        """Return new state with additional vertices added to known set.

        Args:
            new_vertices: Set of newly revealed vertex indices (Δ_t).

        Returns:
            New DynamicState with updated known_vertices.
        """
        updated_known = self.known_vertices | frozenset(new_vertices)
        return DynamicState(
            known_vertices=updated_known,
            frozen_prefix_length=self.frozen_prefix_length,
            current_route=self.current_route,
            time_step=self.time_step,
            instance=self.instance,
        )

    def with_updated_route(self, new_route: Route) -> DynamicState:
        """Return new state with updated route (after repair).

        Args:
            new_route: Updated route covering the known vertices.

        Returns:
            New DynamicState with updated route.
        """
        return DynamicState(
            known_vertices=self.known_vertices,
            frozen_prefix_length=self.frozen_prefix_length,
            current_route=new_route,
            time_step=self.time_step,
            instance=self.instance,
        )

    def with_advanced_time(self, new_time_step: int) -> DynamicState:
        """Return new state with advanced time step."""
        return DynamicState(
            known_vertices=self.known_vertices,
            frozen_prefix_length=self.frozen_prefix_length,
            current_route=self.current_route,
            time_step=new_time_step,
            instance=self.instance,
        )

    def reconstruct_route_from_suffix(self, new_suffix: Route | tuple[int, ...]) -> Route:
        """Reconstruct full route from frozen prefix + new suffix.

        Per PSEUDOCODE.md UPDATE_WITH_FROZEN:
        prefix + suffix[1:] (avoid duplicate p_f)

        Args:
            new_suffix: New uncommitted suffix starting from last frozen vertex.
                       Can be a Route or a tuple of vertex indices.

        Returns:
            Full reconstructed route.
        """
        frozen_prefix = self.get_frozen_prefix_vertices()
        
        # Handle both Route and tuple
        if isinstance(new_suffix, Route):
            suffix_vertices = list(new_suffix.vertices)
        else:
            suffix_vertices = list(new_suffix)
        
        # suffix starts with the last frozen vertex; avoid duplicating it
        if suffix_vertices and suffix_vertices[0] == frozen_prefix[-1]:
            suffix_vertices = suffix_vertices[1:]
        full_vertices = list(frozen_prefix) + suffix_vertices
        return Route(tuple(full_vertices))

    def get_required_vertices_for_feasibility(self) -> set[int]:
        """Get the set of vertices that must be visited in current route."""
        return self.known_vertices - {0}

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the dynamic state consistency.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        # Route must be feasible for known vertices
        required = self.get_required_vertices_for_feasibility()
        is_feasible, route_errors = validate_route(
            self.current_route, self.instance, required
        )
        if not is_feasible:
            errors.extend(route_errors)

        # Frozen prefix must be valid
        if self.frozen_prefix_length > len(self.current_route.vertices) - 2:
            errors.append(
                f"frozen_prefix_length {self.frozen_prefix_length} exceeds "
                f"route length {len(self.current_route.vertices) - 1}"
            )

        # Frozen prefix vertices must match route prefix
        frozen_vertices = self.get_frozen_prefix_vertices()
        if list(frozen_vertices) != list(self.current_route.vertices[: len(frozen_vertices)]):
            errors.append("Frozen prefix does not match route prefix")

        return len(errors) == 0, errors


def create_initial_state(
    instance: Instance,
    initial_known_vertices: set[int],
    seed: int = 0,
) -> DynamicState:
    """Create initial dynamic state at t=0.

    Builds initial route using nearest-neighbor on V_0.
    Frozen prefix starts at 0 (nothing frozen yet).

    Args:
        instance: Full problem instance.
        initial_known_vertices: Set V_0 of initially known vertices (must include 0).
        seed: Random seed for deterministic tie-breaking (passed to NN).

    Returns:
        DynamicState at t=0 with initial route.
    """
    from adaptive_route_optimization.algorithms.baseline import nearest_neighbor

    if 0 not in initial_known_vertices:
        raise ValueError("Depot (0) must be in initial_known_vertices")

    # Build initial route using nearest-neighbor on known vertices
    subinstance = instance.get_subinstance(initial_known_vertices)
    nn_result = nearest_neighbor(subinstance)

    # Map route back to original vertex indices
    # The subinstance re-indexes vertices; we need to map back
    sorted_known = sorted(initial_known_vertices)
    index_map = {new_idx: orig_idx for new_idx, orig_idx in enumerate(sorted_known)}
    original_route_vertices = tuple(index_map[v] for v in nn_result.route.vertices)
    original_route = Route(original_route_vertices)

    return DynamicState(
        known_vertices=frozenset(initial_known_vertices),
        frozen_prefix_length=0,
        current_route=original_route,
        time_step=0,
        instance=instance,
    )