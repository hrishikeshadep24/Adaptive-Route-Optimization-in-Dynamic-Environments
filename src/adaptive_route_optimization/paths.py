"""Path resolution utilities for repository-relative artifacts.

Provides functions to locate the repository root and resolve artifact paths
consistently, regardless of the current working directory.
"""

from __future__ import annotations
import os
from pathlib import Path

# Repo root is 2 levels up from src/adaptive_route_optimization:
# <repo_root>/src/adaptive_route_optimization/paths.py -> parents[2]
REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def get_repo_root() -> Path:
    """Return the absolute Path to the repository root directory."""
    return REPO_ROOT


def resolve_repo_path(path: str | Path) -> str:
    """Resolve path relative to repository root.

    Args:
        path: A file or directory path (absolute or relative).

    Returns:
        String path resolved to repository root if it exists there,
        otherwise resolved relative to CWD or as an absolute path.
    """
    p = Path(path)
    if p.is_absolute():
        return str(p)
    candidate = REPO_ROOT / p
    if candidate.exists():
        return str(candidate)
    if p.exists():
        return str(p)
    return str(candidate)
