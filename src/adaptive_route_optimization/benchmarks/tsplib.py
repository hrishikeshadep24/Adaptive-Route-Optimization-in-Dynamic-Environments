"""TSPLIB Benchmark Parser and Integration.

Provides parsing, metadata extraction, distance-convention preservation,
and dynamic scenario generation for standard TSPLIB benchmark instances.
"""

from __future__ import annotations
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.paths import resolve_repo_path
from adaptive_route_optimization.simulation.events import EventConfig, EventSequence, EventGenerator


@dataclass(frozen=True)
class TSPLIBMetadata:
    """Metadata extracted from TSPLIB problem specification.

    Attributes:
        name: Instance identifier (e.g. 'berlin52').
        comment: Descriptive comment from TSPLIB header.
        dimension: Total number of nodes in the benchmark.
        edge_weight_type: Distance specification ('EUC_2D', 'CEIL_2D').
        source_file: Original filename or path.
        source: Benchmark collection origin ('TSPLIB95 (University of Heidelberg)').
        provenance_note: Provenance verification and known benchmark characteristics.
    """
    name: str
    comment: str
    dimension: int
    edge_weight_type: str
    source_file: Optional[str] = None
    source: str = "TSPLIB95 (University of Heidelberg)"
    provenance_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "comment": self.comment,
            "dimension": self.dimension,
            "edge_weight_type": self.edge_weight_type,
            "source_file": self.source_file,
            "source": self.source,
            "provenance_note": self.provenance_note,
        }


@dataclass(frozen=True)
class TSPLIBInstance:
    """Wrapper coupling a routing Instance with TSPLIB metadata and distance conventions.

    In the TSPLIB coordinate mapping:
    - TSPLIB node 1 maps to Instance index 0 (Depot).
    - TSPLIB nodes 2..N map to Instance customer indices 1..(N-1).

    Attributes:
        instance: Routing problem Instance with 2D coordinates.
        metadata: Specification metadata from the TSPLIB header.
        node_map: Mapping from 1-based TSPLIB node ID to 0-based Instance index.
        reverse_node_map: Mapping from 0-based Instance index to 1-based TSPLIB node ID.
    """
    instance: Instance
    metadata: TSPLIBMetadata
    node_map: dict[int, int]
    reverse_node_map: dict[int, int]

    @property
    def dimension(self) -> int:
        return self.metadata.dimension

    @property
    def name(self) -> str:
        return self.metadata.name

    def tsplib_distance(self, i: int, j: int) -> int:
        """Compute standard TSPLIB integer distance according to benchmark convention.

        Supported conventions:
        - EUC_2D: d_ij = nint(sqrt((x_i - x_j)^2 + (y_i - y_j)^2))
          where nint(z) = floor(z + 0.5).
        - CEIL_2D: d_ij = ceil(sqrt((x_i - x_j)^2 + (y_i - y_j)^2)).
        """
        xi, yi = self.instance.coords[i]
        xj, yj = self.instance.coords[j]
        xd = xi - xj
        yd = yi - yj
        raw_dist = math.sqrt(xd * xd + yd * yd)
        if self.metadata.edge_weight_type == "CEIL_2D":
            return int(math.ceil(raw_dist))
        # Default EUC_2D: TSPLIB nint rounding
        return int(math.floor(raw_dist + 0.5))

    def cost(self, i: int, j: int) -> float:
        """Exact floating-point Euclidean cost used by the dynamic routing simulator."""
        return self.instance.cost(i, j)

    def tsplib_tour_cost(self, vertices: Sequence[int]) -> int:
        """Compute total tour length under standard TSPLIB integer distance convention.

        Args:
            vertices: Tour cycle sequence (e.g. (0, 1, ..., 0)).

        Returns:
            Sum of integer TSPLIB edge weights along the tour.
        """
        total = 0
        for k in range(len(vertices) - 1):
            total += self.tsplib_distance(vertices[k], vertices[k + 1])
        return total

    def continuous_tour_cost(self, vertices: Sequence[int]) -> float:
        """Compute total tour length under continuous floating-point Euclidean distance.

        Args:
            vertices: Tour cycle sequence (e.g. (0, 1, ..., 0)).

        Returns:
            Sum of exact Euclidean edge lengths along the tour.
        """
        total = 0.0
        for k in range(len(vertices) - 1):
            total += self.cost(vertices[k], vertices[k + 1])
        return total


def parse_tsplib_file(file_path: str | Path) -> TSPLIBInstance:
    """Parse a standard TSPLIB coordinate file (.tsp).

    Supports TSPLIB 2D coordinate specifications (EUC_2D, CEIL_2D).
    Does NOT silently convert non-Euclidean conventions (e.g. GEO, EXPLICIT matrix).

    Args:
        file_path: Path to .tsp file.

    Returns:
        TSPLIBInstance with parsed coordinates and preserved metadata.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"TSPLIB file not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    name = ""
    comment = ""
    dimension = -1
    edge_weight_type = ""
    node_coords: list[tuple[int, float, float]] = []

    in_coord_section = False

    for line in lines:
        if line == "EOF":
            break

        if line.startswith("NODE_COORD_SECTION"):
            in_coord_section = True
            continue

        if not in_coord_section:
            # Parse header field
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().upper()
                val = val.strip()
            else:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key = parts[0].strip().upper()
                    val = parts[1].strip()
                else:
                    continue

            if key == "NAME":
                name = val
            elif key == "COMMENT":
                comment = val
            elif key == "DIMENSION":
                try:
                    dimension = int(val)
                except ValueError:
                    raise ValueError(f"Invalid TSPLIB DIMENSION: {val}")
            elif key == "EDGE_WEIGHT_TYPE":
                edge_weight_type = val.upper()
        else:
            # Parse node coordinate line: id x y
            parts = line.split()
            if len(parts) >= 3:
                node_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                node_coords.append((node_id, x, y))

    if dimension <= 0:
        raise ValueError(f"TSPLIB file missing or invalid DIMENSION: {dimension}")

    if len(node_coords) != dimension:
        raise ValueError(
            f"Parsed {len(node_coords)} nodes but header DIMENSION specified {dimension}"
        )

    # Validate distance convention against official TSPLIB 2D Cartesian types
    supported_types = {"EUC_2D", "CEIL_2D"}
    if edge_weight_type not in supported_types:
        raise ValueError(
            f"Unsupported TSPLIB EDGE_WEIGHT_TYPE '{edge_weight_type}'. "
            f"Supported 2D Euclidean coordinate conventions: {sorted(supported_types)}"
        )

    # Sort nodes by node_id ascending
    node_coords.sort(key=lambda item: item[0])

    # Mapping: Node 1 -> Index 0 (Depot); Nodes 2..N -> Indices 1..(N-1)
    node_map: dict[int, int] = {}
    reverse_node_map: dict[int, int] = {}
    coords_array = np.zeros((dimension, 2), dtype=float)

    for idx, (node_id, x, y) in enumerate(node_coords):
        coords_array[idx, 0] = x
        coords_array[idx, 1] = y
        node_map[node_id] = idx
        reverse_node_map[idx] = node_id

    instance = Instance(coords_array)

    # Establish provenance note
    inst_name = (name or path.stem).lower()
    if "berlin52" in inst_name:
        prov = (
            "Origin: Martin Grötschel (1977); collected in TSPLIB95 (G. Reinelt). "
            "Verified optimal tour length under integer EUC_2D is 7542."
        )
    elif "eil51" in inst_name:
        prov = (
            "Origin: N. Christofides & S. Eilon (1969); collected in TSPLIB95 (G. Reinelt). "
            "Verified optimal tour length under integer EUC_2D is 426."
        )
    else:
        prov = "Loaded from local TSPLIB repository file."

    metadata = TSPLIBMetadata(
        name=name or path.stem,
        comment=comment,
        dimension=dimension,
        edge_weight_type=edge_weight_type,
        source_file=str(path),
        provenance_note=prov,
    )

    return TSPLIBInstance(
        instance=instance,
        metadata=metadata,
        node_map=node_map,
        reverse_node_map=reverse_node_map,
    )


def load_tsplib_benchmark(
    name: str,
    benchmark_dir: Optional[str | Path] = None,
) -> TSPLIBInstance:
    """Load a TSPLIB benchmark by name from the dedicated benchmark directory.

    Args:
        name: Instance name (e.g. 'berlin52', 'eil51', with or without '.tsp').
        benchmark_dir: Optional override for benchmark directory.

    Returns:
        TSPLIBInstance ready for routing experiments.
    """
    clean_name = name if name.endswith(".tsp") else f"{name}.tsp"

    if benchmark_dir is not None:
        target_path = Path(benchmark_dir) / clean_name
    else:
        # Default dedicated benchmark directory
        target_path = resolve_repo_path(Path("data") / "benchmarks" / "tsplib" / clean_name)

    return parse_tsplib_file(target_path)


def create_dynamic_scenario_from_instance(
    instance: Instance,
    event_config: EventConfig,
) -> tuple[Instance, EventSequence]:
    """Derive a dynamic customer arrival scenario from a static benchmark instance.

    Strictly separates the original static benchmark topology from the
    dynamic revelation schedule.

    Args:
        instance: Static benchmark Instance.
        event_config: Configuration defining dynamicity, arrival order, and batch sizes.

    Returns:
        Tuple of (static_instance, event_sequence).
    """
    generator = EventGenerator(event_config)
    sequence = generator.generate(instance)
    return instance, sequence
