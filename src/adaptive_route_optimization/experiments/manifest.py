"""Experiment Manifest and Environment Capture.

Records commit hash, runtime environment, hardware/OS, and batch execution status
for scientific reproducibility.
References: MASTER_BLUEPRINT.md (Research integrity), PHASE_PLAN.md (Phase 6 deliverables).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import json
import os
import platform
import subprocess
import sys
from datetime import datetime


def get_git_commit_hash(default: str = "unknown") -> str:
    """Retrieve the current Git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return default


def get_git_status_is_clean() -> bool:
    """Check if the git working tree has no uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return len(result.stdout.strip()) == 0
    except Exception:
        return False


def get_environment_info() -> dict[str, str]:
    """Capture runtime environment and package versions."""
    import numpy as np
    import pandas as pd
    import matplotlib

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "matplotlib_version": matplotlib.__version__,
    }


@dataclass
class ExperimentManifest:
    """Manifest describing a completed or in-progress experimental batch."""
    experiment_name: str
    git_commit_hash: str
    git_is_clean: bool
    start_time: str
    end_time: Optional[str] = None
    environment: dict[str, str] = field(default_factory=get_environment_info)
    total_conditions: int = 0
    total_seeds: int = 0
    total_planned_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    output_files: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def finalize(
        self,
        completed_runs: int,
        failed_runs: int,
        output_files: dict[str, str],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Mark manifest as finished and record final statistics."""
        self.end_time = datetime.now().isoformat()
        self.completed_runs = completed_runs
        self.failed_runs = failed_runs
        self.output_files = output_files
        if metadata:
            self.metadata.update(metadata)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentManifest:
        return cls(**data)

    @classmethod
    def load(cls, filepath: str) -> ExperimentManifest:
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def create_manifest(
    experiment_name: str,
    total_conditions: int,
    total_seeds: int,
    total_planned_runs: int,
    metadata: Optional[dict[str, Any]] = None,
) -> ExperimentManifest:
    """Factory to create a fresh ExperimentManifest initialized with current environment."""
    return ExperimentManifest(
        experiment_name=experiment_name,
        git_commit_hash=get_git_commit_hash(),
        git_is_clean=get_git_status_is_clean(),
        start_time=datetime.now().isoformat(),
        environment=get_environment_info(),
        total_conditions=total_conditions,
        total_seeds=total_seeds,
        total_planned_runs=total_planned_runs,
        metadata=metadata or {},
    )
