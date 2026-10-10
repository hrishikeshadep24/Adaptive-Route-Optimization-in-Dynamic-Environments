"""Route representation for the routing problem.

A route is a sequence of vertices starting and ending at the depot (0).
References: RESEARCH_SPEC.md (Route and Total Cost, Feasibility), NOTATION.md (R, C(R))
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from adaptive_route_optimization.models.instance import Instance


@dataclass(frozen=True)
class Route:
    """A valid route visiting a set of vertices exactly once, starting/ending at depot.

    Representation: tuple of vertex indices, e.g., (0, 1, 4, 2, 3, 0).
    The first and last elements must be 0 (depot).
    All intermediate vertices are distinct and non-zero.

    Attributes:
        vertices: Tuple of vertex indices forming the route.
    """
    vertices: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.vertices:
            raise ValueError("Route cannot be empty")
        if self.vertices[0] != 0 or self.vertices[-1] != 0:
            raise ValueError("Route must start and end at depot (0)")
        if len(self.vertices) < 2:
            raise ValueError("Route must have at least depot->depot")
        # Check for duplicates in the middle (excluding first/last which are both 0)
        middle = self.vertices[1:-1]
        if len(middle) != len(set(middle)):
            raise ValueError("Route contains duplicate vertices")
        if 0 in middle:
            raise ValueError("Depot (0) cannot appear in middle of route")

    @property
    def num_edges(self) -> int:
        """Number of edges in the route (including return to depot)."""
        return len(self.vertices) - 1

    @property
    def num_customers(self) -> int:
        """Number of non-depot vertices visited."""
        return len(self.vertices) - 2  # exclude start and end depot

    @property
    def visited_vertices(self) -> set[int]:
        """Set of all vertices visited (including depot)."""
        return set(self.vertices)

    @property
    def visited_customers(self) -> set[int]:
        """Set of non-depot vertices visited."""
        return set(self.vertices[1:-1])

    def cost(self, instance: Instance) -> float:
        """Total route cost C(R) = sum of consecutive edge costs.

        Args:
            instance: Problem instance providing cost function.

        Returns:
            Total cost of the route.
        """
        total = 0.0
        for i in range(self.num_edges):
            u = self.vertices[i]
            v = self.vertices[i + 1]
            total += instance.cost(u, v)
        return total

    def edges(self) -> frozenset[tuple[int, int]]:
        """Set of edges in the route as (u, v) pairs.

        Used for disruption calculation.
        """
        return frozenset(
            (self.vertices[i], self.vertices[i + 1])
            for i in range(self.num_edges)
        )

    def is_feasible(self, instance: Instance, required_vertices: Optional[set[int]] = None) -> bool:
        """Check if route is feasible for the given instance and required vertices.

        Feasibility (RESEARCH_SPEC.md):
        1. Starts and ends at depot (enforced by constructor)
        2. Every required non-depot vertex appears exactly once
        3. No other vertices appear
        4. All edges exist (always true for complete graph)

        Args:
            instance: Problem instance.
            required_vertices: Set of vertices that must be visited.
                              Defaults to all vertices in instance except depot.

        Returns:
            True if feasible, False otherwise.
        """
        if required_vertices is None:
            required_vertices = set(range(1, instance.num_vertices))

        # Check all required vertices are visited exactly once
        visited = self.visited_customers
        if visited != required_vertices:
            return False

        # All vertices in route must be valid for instance
        if not all(0 <= v < instance.num_vertices for v in self.vertices):
            return False

        return True

    @classmethod
    def from_list(cls, vertices: list[int]) -> Route:
        """Create Route from list of vertex indices."""
        return cls(tuple(vertices))

    def with_insertion(self, position: int, vertex: int) -> Route:
        """Return new route with vertex inserted at position.

        Args:
            position: Index in vertices list where new vertex goes (0 = after depot).
                      Valid range: 0 to num_edges - 1 (insert before last depot).
            vertex: Vertex to insert (must not be 0 and not already in route).

        Returns:
            New Route with vertex inserted.
        """
        if vertex == 0:
            raise ValueError("Cannot insert depot into middle of route")
        if vertex in self.vertices[1:-1]:
            raise ValueError(f"Vertex {vertex} already in route")
        if not (0 <= position < self.num_edges):
            raise ValueError(f"Position {position} out of range [0, {self.num_edges})")

        new_vertices = list(self.vertices)
        new_vertices.insert(position + 1, vertex)  # +1 because position 0 = after depot
        return Route(tuple(new_vertices))

    def with_2opt_swap(self, i: int, j: int) -> Route:
        """Return new route with 2-opt swap applied (reverse segment i+1 to j).

        Args:
            i: First edge index (0 to num_edges-2)
            j: Second edge index (i+2 to num_edges-1)

        Returns:
            New Route with segment reversed.
        """
        if not (0 <= i < j <= self.num_edges):
            raise ValueError(f"Invalid indices i={i}, j={j} for route with {self.num_edges} edges")
        if j - i < 2:
            raise ValueError("2-opt requires non-adjacent edges (j - i >= 2)")

        new_vertices = list(self.vertices)
        # Reverse segment from i+1 to j (inclusive)
        new_vertices[i + 1 : j + 1] = reversed(new_vertices[i + 1 : j + 1])
        return Route(tuple(new_vertices))

    def __len__(self) -> int:
        return len(self.vertices)

    def __getitem__(self, idx: int) -> int:
        return self.vertices[idx]

    def __iter__(self):
        return iter(self.vertices)

    def __repr__(self) -> str:
        return f"Route({list(self.vertices)})"


def validate_route(route: Route, instance: Instance, required_vertices: Optional[set[int]] = None) -> tuple[bool, list[str]]:
    """Validate a route and return (is_valid, list_of_errors).

    Args:
        route: Route to validate.
        instance: Problem instance.
        required_vertices: Required vertices (default: all non-depot in instance).

    Returns:
        Tuple of (is_valid, error_messages).
    """
    errors = []

    if route.vertices[0] != 0 or route.vertices[-1] != 0:
        errors.append("Route must start and end at depot (0)")

    middle = route.vertices[1:-1]
    if len(middle) != len(set(middle)):
        errors.append("Route contains duplicate vertices")
    if 0 in middle:
        errors.append("Depot (0) appears in middle of route")

    if required_vertices is None:
        required_vertices = set(range(1, instance.num_vertices))

    visited = set(middle)
    missing = required_vertices - visited
    extra = visited - required_vertices
    if missing:
        errors.append(f"Missing required vertices: {sorted(missing)}")
    if extra:
        errors.append(f"Extra vertices not in required set: {sorted(extra)}")

    for v in route.vertices:
        if not (0 <= v < instance.num_vertices):
            errors.append(f"Vertex {v} out of bounds for instance with {instance.num_vertices} vertices")

    return len(errors) == 0, errors