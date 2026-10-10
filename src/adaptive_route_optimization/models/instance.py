"""Instance model for the routing problem.

Represents a complete problem instance with vertex coordinates and cost matrix.
References: RESEARCH_SPEC.md (Graph and Cost Model), NOTATION.md (V, c(i,j))
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass(frozen=True)
class Instance:
    """Complete problem instance: vertices with 2D coordinates and cost function.

    Vertex 0 is always the depot. Costs are Euclidean distances (symmetric,
    satisfying triangle inequality).

    Attributes:
        coords: Array of shape (n+1, 2) where n = number of non-depot vertices.
                coords[0] is the depot.
        n: Number of non-depot vertices.
    """
    coords: np.ndarray  # shape (n+1, 2)

    def __post_init__(self) -> None:
        if self.coords.ndim != 2 or self.coords.shape[1] != 2:
            raise ValueError("coords must be shape (n+1, 2)")
        if self.n < 0:
            raise ValueError("Must have at least depot (n >= 0)")

    @property
    def n(self) -> int:
        """Number of non-depot vertices."""
        return len(self.coords) - 1

    @property
    def num_vertices(self) -> int:
        """Total vertices including depot."""
        return len(self.coords)

    def cost(self, i: int, j: int) -> float:
        """Euclidean distance c(i, j) between vertices i and j.

        Args:
            i: Vertex index (0 to n)
            j: Vertex index (0 to n)

        Returns:
            Euclidean distance, symmetric and non-negative.
        """
        if not (0 <= i < self.num_vertices and 0 <= j < self.num_vertices):
            raise IndexError(f"Vertex index out of bounds [0, {self.num_vertices})")
        xi, yi = self.coords[i]
        xj, yj = self.coords[j]
        return math.hypot(xi - xj, yi - yj)

    def cost_matrix(self) -> np.ndarray:
        """Full cost matrix C where C[i, j] = c(i, j).

        Returns:
            Square matrix of shape (n+1, n+1).
        """
        n1 = self.num_vertices
        C = np.zeros((n1, n1), dtype=float)
        for i in range(n1):
            for j in range(i + 1, n1):
                d = self.cost(i, j)
                C[i, j] = d
                C[j, i] = d
        return C

    @classmethod
    def from_coords(cls, coords: list[tuple[float, float]]) -> Instance:
        """Create instance from list of (x, y) tuples."""
        return cls(np.array(coords, dtype=float))

    @classmethod
    def generate_random(
        cls,
        n: int,
        seed: int,
        x_range: tuple[float, float] = (0.0, 100.0),
        y_range: tuple[float, float] = (0.0, 100.0),
        depot_at_origin: bool = False,
        min_separation: float = 1e-6,
    ) -> Instance:
        """Generate a random instance with n non-depot vertices.

        Args:
            n: Number of non-depot vertices.
            seed: Random seed for reproducibility.
            x_range: Range for x coordinates.
            y_range: Range for y coordinates.
            depot_at_origin: If True, depot at (0, 0); else random in range.
            min_separation: Minimum distance between any two vertices (avoids
                            zero-cost edges). If violated, adds small jitter.

        Returns:
            Instance with n+1 vertices (0 = depot).
        """
        rng = np.random.default_rng(seed)

        if depot_at_origin:
            depot = np.array([[0.0, 0.0]])
        else:
            depot = rng.uniform(
                low=[x_range[0], y_range[0]],
                high=[x_range[1], y_range[1]],
                size=(1, 2),
            )

        # Generate customer coordinates
        customers = rng.uniform(
            low=[x_range[0], y_range[0]],
            high=[x_range[1], y_range[1]],
            size=(n, 2),
        )

        coords = np.vstack([depot, customers])

        # Ensure minimum separation to avoid zero-cost edges
        # Simple approach: add small jitter to any coincident points
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                if np.linalg.norm(coords[i] - coords[j]) < min_separation:
                    coords[j] += rng.uniform(-min_separation, min_separation, size=2)

        return cls(coords)

    def subset(self, vertex_indices: list[int]) -> Instance:
        """Return a new instance with only the specified vertices.

        Preserves vertex 0 (depot) as index 0 in the subset.
        Other vertices are re-indexed in ascending order of original index.

        Args:
            vertex_indices: List of vertex indices to keep. Must include 0.

        Returns:
            New Instance with subset of vertices.
        """
        if 0 not in vertex_indices:
            raise ValueError("Depot (vertex 0) must be included in subset")

        # Sort: depot first, then others in ascending order
        sorted_indices = [0] + sorted(v for v in vertex_indices if v != 0)
        new_coords = self.coords[sorted_indices]
        return Instance(new_coords)

    def get_subinstance(self, known_vertices: set[int]) -> Instance:
        """Get sub-instance for currently known vertices.

        Args:
            known_vertices: Set of vertex indices known at current time step.
                           Must include 0 (depot).

        Returns:
            Instance containing only known vertices, re-indexed.
        """
        if 0 not in known_vertices:
            raise ValueError("Depot must be in known_vertices")
        return self.subset(sorted(known_vertices))