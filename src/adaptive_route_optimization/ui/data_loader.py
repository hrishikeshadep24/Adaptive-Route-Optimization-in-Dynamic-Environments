"""Data Loader and Schema Validator for Research Dashboard.

Loads and caches saved experiment results, manifests, and audit reports:
- pilot_matrix/ (Phase 6 & 7)
- budgeted_pilot/ (Phase 6 & 7)
- held_out_matrix/ (Phase 8)
- tables/ (Phase 7 & 8)
- audit/ (Pre-Phase 9 Audit)
"""

from __future__ import annotations
import json
import os
from typing import Any, Optional
import pandas as pd


class UIDataLoader:
    """Robust data loader for dashboard UI."""

    def __init__(self, base_results_dir: str = "results") -> None:
        self.base_dir = base_results_dir

    def load_dataset_runs(self, dataset_name: str) -> pd.DataFrame:
        """Load runs.csv for a specific experiment dataset.

        Args:
            dataset_name: 'pilot_matrix', 'budgeted_pilot', or 'held_out_matrix'.

        Returns:
            DataFrame containing run records.
        """
        path = os.path.join(self.base_dir, dataset_name, "runs.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Experiment dataset not found: {path}")

        df = pd.read_csv(path)
        required_cols = ["run_id", "condition_id", "strategy", "seed", "final_cost", "total_computational_effort", "all_feasible"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Dataset {path} missing required columns: {missing}")

        return df

    def load_dataset_steps(self, dataset_name: str) -> pd.DataFrame:
        """Load steps.csv for a specific experiment dataset."""
        path = os.path.join(self.base_dir, dataset_name, "steps.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Steps dataset not found: {path}")

        df = pd.read_csv(path)
        return df

    def load_dataset_manifest(self, dataset_name: str) -> dict[str, Any]:
        """Load manifest.json for a specific experiment dataset."""
        path = os.path.join(self.base_dir, dataset_name, "manifest.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Manifest not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_table(self, table_filename: str) -> pd.DataFrame:
        """Load precomputed analysis table from results/tables/."""
        path = os.path.join(self.base_dir, "tables", table_filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Table file not found: {path}")
        return pd.read_csv(path)

    def load_audit_reconciliation(self) -> pd.DataFrame:
        """Load metric reconciliation table from results/audit/."""
        path = os.path.join(self.base_dir, "audit", "metric_reconciliation.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audit reconciliation table not found: {path}")
        return pd.read_csv(path)

    def load_audit_inventory(self) -> pd.DataFrame:
        """Load claim inventory table from results/audit/."""
        path = os.path.join(self.base_dir, "audit", "claim_inventory.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audit inventory table not found: {path}")
        return pd.read_csv(path)

    def load_audit_reports(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load data integrity and reproducibility reports from results/audit/."""
        integrity_path = os.path.join(self.base_dir, "audit", "data_integrity_report.json")
        repro_path = os.path.join(self.base_dir, "audit", "reproducibility_report.json")

        integrity_data = {}
        repro_data = {}

        if os.path.exists(integrity_path):
            with open(integrity_path, "r", encoding="utf-8") as f:
                integrity_data = json.load(f)

        if os.path.exists(repro_path):
            with open(repro_path, "r", encoding="utf-8") as f:
                repro_data = json.load(f)

        return integrity_data, repro_data

    @staticmethod
    def filter_runs(
        df: pd.DataFrame,
        sizes: Optional[list[int]] = None,
        dynamicities: Optional[list[float]] = None,
        strategies: Optional[list[str]] = None,
        seeds: Optional[list[int]] = None,
    ) -> pd.DataFrame:
        """Filter runs DataFrame by experimental parameters."""
        filtered = df.copy()

        if sizes and "total_vertices" in filtered.columns:
            filtered = filtered[filtered["total_vertices"].isin(sizes)]

        if dynamicities and "dynamicity" in filtered.columns:
            # Rounding to handle floating-point comparison
            filtered = filtered[filtered["dynamicity"].round(4).isin([round(d, 4) for d in dynamicities])]

        if strategies and "strategy" in filtered.columns:
            filtered = filtered[filtered["strategy"].isin(strategies)]

        if seeds and "seed" in filtered.columns:
            filtered = filtered[filtered["seed"].isin(seeds)]

        return filtered
