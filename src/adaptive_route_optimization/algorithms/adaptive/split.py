"""Data Partitioning and Leakage Prevention Manifest for Phase 8.

Formally partitions experiment conditions and random seeds into Development,
Validation, and Held-Out Test sets to guarantee zero data leakage.
References: MASTER_BLUEPRINT.md (Research integrity), PHASE_PLAN.md (Phase 8).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Sequence
import json
import os


@dataclass(frozen=True)
class PartitionDefinition:
    """Definition of a single data partition."""
    partition_name: str
    seeds: tuple[int, ...]
    conditions: tuple[str, ...]
    purpose: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition_name": self.partition_name,
            "seeds": list(self.seeds),
            "conditions": list(self.conditions),
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class DataSplitManifest:
    """Formal partition manifest guaranteeing complete separation of data splits."""
    development: PartitionDefinition
    validation: PartitionDefinition
    held_out: PartitionDefinition
    created_at: str

    def validate_no_overlap(self) -> None:
        """Verify that seed sets are strictly disjoint."""
        dev_seeds = set(self.development.seeds)
        val_seeds = set(self.validation.seeds)
        test_seeds = set(self.held_out.seeds)

        dev_val = dev_seeds.intersection(val_seeds)
        dev_test = dev_seeds.intersection(test_seeds)
        val_test = val_seeds.intersection(test_seeds)

        if dev_val or dev_test or val_test:
            raise ValueError(
                f"Data split integrity violation! Overlapping seeds detected: "
                f"dev∩val={dev_val}, dev∩test={dev_test}, val∩test={val_test}"
            )

    def get_partition(self, seed: int) -> str:
        """Return the partition name for a given seed, or raise ValueError."""
        if seed in self.development.seeds:
            return self.development.partition_name
        if seed in self.validation.seeds:
            return self.validation.partition_name
        if seed in self.held_out.seeds:
            return self.held_out.partition_name
        raise ValueError(f"Seed {seed} not registered in any partition!")

    def to_dict(self) -> dict[str, Any]:
        return {
            "development": self.development.to_dict(),
            "validation": self.validation.to_dict(),
            "held_out": self.held_out.to_dict(),
            "created_at": self.created_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataSplitManifest:
        dev = PartitionDefinition(**data["development"])
        val = PartitionDefinition(**data["validation"])
        held = PartitionDefinition(**data["held_out"])
        return cls(development=dev, validation=val, held_out=held, created_at=data["created_at"])

    @classmethod
    def load(cls, filepath: str) -> DataSplitManifest:
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def get_default_data_split() -> DataSplitManifest:
    """Construct the official research data partition for Phase 8."""
    all_conditions = (
        "n50_d0.1", "n50_d0.2", "n50_d0.4", "n50_d0.6", "n50_d0.8",
        "n100_d0.2", "n100_d0.4", "n100_d0.6",
        "n200_d0.2", "n200_d0.4",
    )

    dev_partition = PartitionDefinition(
        partition_name="development",
        seeds=(42, 101),
        conditions=all_conditions,
        purpose="Empirical rule derivation, threshold discovery, and feature engineering (Phase 7 pilot).",
    )

    val_partition = PartitionDefinition(
        partition_name="validation",
        seeds=(777,),
        conditions=all_conditions,
        purpose="Hyperparameter selection and comparison of candidate selector rule variants.",
    )

    held_out_partition = PartitionDefinition(
        partition_name="held_out",
        seeds=(1234, 5678, 9999),
        conditions=all_conditions,
        purpose="Final unbiased confirmation of frozen adaptive selector vs Always A and Always B.",
    )

    manifest = DataSplitManifest(
        development=dev_partition,
        validation=val_partition,
        held_out=held_out_partition,
        created_at="2026-10-21T17:00:00",
    )
    manifest.validate_no_overlap()
    return manifest


DEFAULT_DATA_SPLIT: DataSplitManifest = get_default_data_split()

