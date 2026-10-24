"""Instance model for the routing problem.

Represents a complete problem instance with vertex coordinates and cost matrix.
References: RESEARCH_SPEC.md (Graph and Cost Model), NOTATION.md (V, c(i,j))
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
import numpy as np


class CustomerDistribution(str, Enum):
    """Customer spatial distribution types."""
    UNIFORM = "uniform"
    CLUSTERED = "clustered"
    MIXED = "mixed"


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

    @classmethod
    def generate_clustered(
        cls,
        n: int,
        seed: int,
        num_clusters: int = 3,
        cluster_spread: float = 5.0,
        x_range: tuple[float, float] = (0.0, 100.0),
        y_range: tuple[float, float] = (0.0, 100.0),
        depot_at_origin: bool = False,
        min_separation: float = 1e-6,
    ) -> Instance:
        """Generate an instance with customer vertices grouped in spatial clusters.

        Args:
            n: Number of non-depot customer vertices.
            seed: Random seed for deterministic reproducibility.
            num_clusters: Number of spatial cluster centers (must be >= 1).
            cluster_spread: Standard deviation of customers around cluster centers (> 0).
            x_range: Coordinate bounds for x-axis.
            y_range: Coordinate bounds for y-axis.
            depot_at_origin: If True, depot is at (0, 0); else placed uniformly.
            min_separation: Minimum distance between coincident points.

        Returns:
            Instance with n+1 vertices (index 0 is depot).
        """
        if n < 0:
            raise ValueError(f"Customer count n must be >= 0, got {n}")
        if num_clusters < 1:
            raise ValueError(f"num_clusters must be >= 1, got {num_clusters}")
        if cluster_spread <= 0:
            raise ValueError(f"cluster_spread must be > 0, got {cluster_spread}")
        if x_range[0] >= x_range[1] or y_range[0] >= y_range[1]:
            raise ValueError(f"Invalid coordinate ranges: x_range={x_range}, y_range={y_range}")

        rng = np.random.default_rng(seed)

        if depot_at_origin:
            depot = np.array([[0.0, 0.0]])
        else:
            depot = rng.uniform(
                low=[x_range[0], y_range[0]],
                high=[x_range[1], y_range[1]],
                size=(1, 2),
            )

        if n == 0:
            return cls(depot)

        actual_clusters = min(num_clusters, n)
        centers = rng.uniform(
            low=[x_range[0], y_range[0]],
            high=[x_range[1], y_range[1]],
            size=(actual_clusters, 2),
        )

        assignments = np.array([i % actual_clusters for i in range(n)])
        rng.shuffle(assignments)

        offsets = rng.normal(loc=0.0, scale=cluster_spread, size=(n, 2))
        customers = centers[assignments] + offsets

        customers[:, 0] = np.clip(customers[:, 0], x_range[0], x_range[1])
        customers[:, 1] = np.clip(customers[:, 1], y_range[0], y_range[1])

        coords = np.vstack([depot, customers])

        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                if np.linalg.norm(coords[i] - coords[j]) < min_separation:
                    coords[j] += rng.uniform(-min_separation, min_separation, size=2)

        return cls(coords)

    @classmethod
    def generate_mixed(
        cls,
        n: int,
        seed: int,
        num_clusters: int = 3,
        cluster_spread: float = 5.0,
        cluster_ratio: float = 0.7,
        x_range: tuple[float, float] = (0.0, 100.0),
        y_range: tuple[float, float] = (0.0, 100.0),
        depot_at_origin: bool = False,
        min_separation: float = 1e-6,
    ) -> Instance:
        """Generate an instance with mixed clustered and uniform customer distributions.

        Args:
            n: Number of non-depot customer vertices.
            seed: Random seed for deterministic reproducibility.
            num_clusters: Number of spatial cluster centers (must be >= 1).
            cluster_spread: Standard deviation of customers around cluster centers (> 0).
            cluster_ratio: Fraction of customers assigned to clusters in [0.0, 1.0].
            x_range: Coordinate bounds for x-axis.
            y_range: Coordinate bounds for y-axis.
            depot_at_origin: If True, depot is at (0, 0); else placed uniformly.
            min_separation: Minimum distance between coincident points.

        Returns:
            Instance with n+1 vertices (index 0 is depot).
        """
        if not (0.0 <= cluster_ratio <= 1.0):
            raise ValueError(f"cluster_ratio must be in [0.0, 1.0], got {cluster_ratio}")
        if n < 0:
            raise ValueError(f"Customer count n must be >= 0, got {n}")
        if num_clusters < 1:
            raise ValueError(f"num_clusters must be >= 1, got {num_clusters}")
        if cluster_spread <= 0:
            raise ValueError(f"cluster_spread must be > 0, got {cluster_spread}")
        if x_range[0] >= x_range[1] or y_range[0] >= y_range[1]:
            raise ValueError(f"Invalid coordinate ranges: x_range={x_range}, y_range={y_range}")

        rng = np.random.default_rng(seed)

        if depot_at_origin:
            depot = np.array([[0.0, 0.0]])
        else:
            depot = rng.uniform(
                low=[x_range[0], y_range[0]],
                high=[x_range[1], y_range[1]],
                size=(1, 2),
            )

        if n == 0:
            return cls(depot)

        n_clustered = int(round(n * cluster_ratio))
        n_uniform = n - n_clustered

        customer_list = []

        if n_clustered > 0:
            actual_clusters = min(num_clusters, n_clustered)
            centers = rng.uniform(
                low=[x_range[0], y_range[0]],
                high=[x_range[1], y_range[1]],
                size=(actual_clusters, 2),
            )
            assignments = np.array([i % actual_clusters for i in range(n_clustered)])
            rng.shuffle(assignments)
            offsets = rng.normal(loc=0.0, scale=cluster_spread, size=(n_clustered, 2))
            clustered_cust = centers[assignments] + offsets
            clustered_cust[:, 0] = np.clip(clustered_cust[:, 0], x_range[0], x_range[1])
            clustered_cust[:, 1] = np.clip(clustered_cust[:, 1], y_range[0], y_range[1])
            customer_list.append(clustered_cust)

        if n_uniform > 0:
            uniform_cust = rng.uniform(
                low=[x_range[0], y_range[0]],
                high=[x_range[1], y_range[1]],
                size=(n_uniform, 2),
            )
            customer_list.append(uniform_cust)

        if customer_list:
            customers = np.vstack(customer_list)
        else:
            customers = np.empty((0, 2))

        coords = np.vstack([depot, customers])

        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                if np.linalg.norm(coords[i] - coords[j]) < min_separation:
                    coords[j] += rng.uniform(-min_separation, min_separation, size=2)

        return cls(coords)

    @classmethod
    def generate_synthetic(
        cls,
        n: int,
        distribution: str | CustomerDistribution = CustomerDistribution.UNIFORM,
        seed: int = 0,
        **kwargs: Any,
    ) -> Instance:
        """Unified factory for generating synthetic problem instances.

        Supported distributions:
        - 'uniform': customers spread uniformly across coordinate plane.
        - 'clustered': customers concentrated around spatial cluster centers.
        - 'mixed': combination of clustered and uniformly dispersed customers.

        Args:
            n: Number of customer vertices.
            distribution: Distribution type ('uniform', 'clustered', 'mixed').
            seed: Random seed.
            **kwargs: Additional parameters passed to distribution-specific generator.

        Returns:
            Instance with n+1 vertices.
        """
        dist_str = distribution.value if isinstance(distribution, CustomerDistribution) else str(distribution).lower()
        if dist_str == "uniform":
            uniform_keys = {"x_range", "y_range", "depot_at_origin", "min_separation"}
            return cls.generate_random(n=n, seed=seed, **{k: v for k, v in kwargs.items() if k in uniform_keys})
        elif dist_str == "clustered":
            clustered_keys = {"num_clusters", "cluster_spread", "x_range", "y_range", "depot_at_origin", "min_separation"}
            return cls.generate_clustered(n=n, seed=seed, **{k: v for k, v in kwargs.items() if k in clustered_keys})
        elif dist_str == "mixed":
            mixed_keys = {"num_clusters", "cluster_spread", "cluster_ratio", "x_range", "y_range", "depot_at_origin", "min_separation"}
            return cls.generate_mixed(n=n, seed=seed, **{k: v for k, v in kwargs.items() if k in mixed_keys})
        else:
            raise ValueError(
                f"Unknown distribution: '{distribution}'. "
                f"Supported distributions are: 'uniform', 'clustered', 'mixed'."
            )

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