"""Dataset Validator for Experimental Route Optimization Data.

Validates that raw experiment outputs strictly comply with research rules,
including Non-Negotiable Rule 10 (identical instance/event stream parity),
schema integrity, metric bounds, and complete executions.
References: MASTER_BLUEPRINT.md (Rule 10, Integrity), RESEARCH_SPEC.md (Metrics).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import pandas as pd
import numpy as np


@dataclass
class ValidationIssue:
    """Represents a data validation warning or error."""
    category: str
    severity: str  # "ERROR" or "WARNING"
    message: str
    details: Optional[dict[str, Any]] = None


@dataclass
class DataValidationReport:
    """Comprehensive validation report for experimental datasets."""
    is_valid: bool
    total_runs: int
    total_steps: int
    conditions_count: int
    seeds_count: int
    strategies: list[str]
    rule_10_passed: bool
    all_feasible: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_runs": self.total_runs,
            "total_steps": self.total_steps,
            "conditions_count": self.conditions_count,
            "seeds_count": self.seeds_count,
            "strategies": self.strategies,
            "rule_10_passed": self.rule_10_passed,
            "all_feasible": self.all_feasible,
            "issues": [asdict(i) for i in self.issues],
        }


def validate_experiment_data(
    runs_df: pd.DataFrame,
    steps_df: Optional[pd.DataFrame] = None,
    manifest_dict: Optional[dict[str, Any]] = None,
    tolerance: float = 1e-6,
) -> DataValidationReport:
    """Perform rigorous validation checks on raw experiment results.

    Checks:
    1. Schema & non-empty data.
    2. Missing values / NaNs (outside expected unbounded budget_limit).
    3. Non-Negotiable Rule 10 parity: Strategy A and B on identical (condition, seed)
       must have exact same initial_cost and exact same num_events.
    4. Metric bounds: final_cost > 0, mean_disruption ∈ [0, 1], feasible == True.
    5. Step-level alignment (if steps_df provided).

    Args:
        runs_df: DataFrame of run-level records (from runs.csv).
        steps_df: Optional DataFrame of step-level records (from steps.csv).
        manifest_dict: Optional dictionary loaded from manifest.json.
        tolerance: Numerical tolerance for floating point parity checks.

    Returns:
        DataValidationReport with boolean is_valid and list of issues.
    """
    issues: list[ValidationIssue] = []

    if runs_df.empty:
        issues.append(ValidationIssue("SCHEMA", "ERROR", "Runs dataframe is completely empty"))
        return DataValidationReport(
            is_valid=False,
            total_runs=0,
            total_steps=0,
            conditions_count=0,
            seeds_count=0,
            strategies=[],
            rule_10_passed=False,
            all_feasible=False,
            issues=issues,
        )

    # Required columns
    required_cols = {
        "run_id", "condition_id", "strategy", "seed", "total_vertices",
        "dynamicity", "num_events", "initial_cost", "final_cost",
        "total_computational_effort", "total_response_time_ms",
        "mean_disruption", "all_feasible",
    }
    missing_cols = required_cols - set(runs_df.columns)
    if missing_cols:
        issues.append(ValidationIssue(
            "SCHEMA", "ERROR",
            f"Runs dataframe missing required columns: {sorted(missing_cols)}"
        ))

    # Check nulls (excluding budget_limit)
    cols_to_check = [c for c in runs_df.columns if c != "budget_limit"]
    null_counts = runs_df[cols_to_check].isnull().sum()
    bad_nulls = null_counts[null_counts > 0]
    if not bad_nulls.empty:
        for col, count in bad_nulls.items():
            issues.append(ValidationIssue(
                "NULLS", "ERROR",
                f"Column '{col}' has {count} unexpected missing/null values"
            ))

    # Check Feasibility
    all_feasible = bool(runs_df["all_feasible"].all()) if "all_feasible" in runs_df else False
    if not all_feasible:
        infeasible_runs = runs_df[~runs_df["all_feasible"]]["run_id"].tolist()
        issues.append(ValidationIssue(
            "FEASIBILITY", "ERROR",
            f"Found {len(infeasible_runs)} infeasible runs: {infeasible_runs}"
        ))

    # Check Metric Ranges
    if "final_cost" in runs_df and (runs_df["final_cost"] <= 0).any():
        issues.append(ValidationIssue("METRICS", "ERROR", "Detected non-positive final_cost values"))

    if "mean_disruption" in runs_df:
        if ((runs_df["mean_disruption"] < 0) | (runs_df["mean_disruption"] > 1.0 + tolerance)).any():
            issues.append(ValidationIssue(
                "METRICS", "ERROR",
                "Detected mean_disruption outside normalized range [0, 1]"
            ))

    # Non-Negotiable Rule 10 Verification (Pairwise check between strategies)
    rule_10_passed = True
    strategies = sorted(runs_df["strategy"].unique())
    if "A" in strategies and "B" in strategies:
        grouped = runs_df.groupby(["condition_id", "seed"])
        for (cond_id, seed), group in grouped:
            strats_in_group = group["strategy"].values
            if "A" in strats_in_group and "B" in strats_in_group:
                row_a = group[group["strategy"] == "A"].iloc[0]
                row_b = group[group["strategy"] == "B"].iloc[0]

                init_diff = abs(row_a["initial_cost"] - row_b["initial_cost"])
                if init_diff > tolerance:
                    rule_10_passed = False
                    issues.append(ValidationIssue(
                        "RULE_10_PARITY", "ERROR",
                        f"Initial cost mismatch for condition '{cond_id}', seed {seed}: "
                        f"A={row_a['initial_cost']:.6f} vs B={row_b['initial_cost']:.6f} (diff={init_diff:.6e})"
                    ))

                if row_a["num_events"] != row_b["num_events"]:
                    rule_10_passed = False
                    issues.append(ValidationIssue(
                        "RULE_10_PARITY", "ERROR",
                        f"Event count mismatch for condition '{cond_id}', seed {seed}: "
                        f"A={row_a['num_events']} vs B={row_b['num_events']}"
                    ))
            else:
                issues.append(ValidationIssue(
                    "PAIRING", "WARNING",
                    f"Condition '{cond_id}', seed {seed} does not have both Strategy A and B"
                ))

    # Check Manifest Consistency (if provided)
    if manifest_dict:
        planned = manifest_dict.get("total_planned_runs")
        completed = manifest_dict.get("completed_runs")
        failed = manifest_dict.get("failed_runs", 0)
        if completed != len(runs_df):
            issues.append(ValidationIssue(
                "MANIFEST", "WARNING",
                f"Manifest completed_runs ({completed}) differs from runs row count ({len(runs_df)})"
            ))
        if failed > 0:
            issues.append(ValidationIssue(
                "MANIFEST", "WARNING",
                f"Manifest records {failed} failed runs during batch execution"
            ))

    # Step Data Consistency (if provided)
    total_steps = len(steps_df) if steps_df is not None else 0
    if steps_df is not None and not steps_df.empty:
        # Sum of num_events across runs should align with steps count
        expected_steps = runs_df["num_events"].sum()
        if expected_steps != total_steps:
            issues.append(ValidationIssue(
                "STEPS_ALIGNMENT", "WARNING",
                f"Sum of num_events in runs ({expected_steps}) differs from steps rows ({total_steps})"
            ))

    has_errors = any(i.severity == "ERROR" for i in issues)
    return DataValidationReport(
        is_valid=not has_errors,
        total_runs=len(runs_df),
        total_steps=total_steps,
        conditions_count=runs_df["condition_id"].nunique(),
        seeds_count=runs_df["seed"].nunique(),
        strategies=list(strategies),
        rule_10_passed=rule_10_passed,
        all_feasible=all_feasible,
        issues=issues,
    )
