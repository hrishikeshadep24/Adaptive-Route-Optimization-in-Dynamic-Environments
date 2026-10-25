"""Smoke test to verify the test environment works."""

import sys


def test_python_version():
    """Verify Python 3.11+ is available."""
    assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version}"


def test_imports():
    """Verify core dependencies can be imported."""
    import numpy as np
    import pandas as pd
    import matplotlib
    import pytest

    assert np.__version__ >= "1.24.0"
    assert pd.__version__ >= "2.0.0"


def test_project_structure():
    """Verify key project directories exist."""
    from pathlib import Path

    root = Path(__file__).parent.parent
    assert (root / "src").exists()
    assert (root / "tests").exists()
    assert (root / "docs").exists()
    assert (root / "configs").exists()
    assert (root / "data").exists()
    assert (root / "results").exists()
    assert (root / "notebooks").exists()
    assert (root / "app").exists()


def test_docs_exist():
    """Verify required documentation files exist."""
    from pathlib import Path

    root = Path(__file__).parent.parent
    docs = root / "docs"
    assert (docs / "MASTER_BLUEPRINT.md").exists()
    assert (docs / "PHASE_PLAN.md").exists()
    assert (docs / "LITERATURE_NOTES.md").exists()
    assert (docs / "CHANGELOG.md").exists()
    assert (docs / "OPEN_QUESTIONS.md").exists()
    assert (docs / "EXPERIMENT_PROTOCOL.md").exists()
    assert (docs / "RESEARCH_SPEC.md").exists()