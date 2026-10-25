"""Reproducibility Verification System for Experimental Framework.

Re-executes an experiment matrix from an existing configuration or manifest
and verifies exact numerical reproducibility against recorded raw outputs.
References: MASTER_BLUEPRINT.md (Gate criteria, Research integrity),
PHASE_PLAN.md (Phase 6 deliverables: reproducibility script, deterministic replay).
"""

from __future__ import annotations
import argparse
import os
import sys
from typing import Any

import pandas as pd

from adaptive_route_optimization.experiments.schema import ExperimentConfig
from adaptive_route_optimization.experiments.manifest import ExperimentManifest
from adaptive_route_optimization.experiments.runner import ExperimentRunner


def verify_reproducibility(
    original_manifest_path: str,
    target_output_dir: Optional[str] = None,
    tolerance: float = 1e-7,
) -> tuple[bool, list[str]]:
    """Re-runs an experiment from its manifest and compares raw results against original.

    Args:
        original_manifest_path: Path to original manifest.json file.
        target_output_dir: Optional directory for re-run outputs.
        tolerance: Numerical tolerance for floating-point route costs.

    Returns:
        Tuple of (is_reproducible, list_of_discrepancies).
    """
    manifest = ExperimentManifest.load(original_manifest_path)
    orig_runs_csv = manifest.output_files.get("runs_csv")
    if not orig_runs_csv or not os.path.exists(orig_runs_csv):
        return False, [f"Original runs CSV not found at {orig_runs_csv}"]

    original_df = pd.read_csv(orig_runs_csv)

    # Reconstruct ExperimentConfig from manifest metadata
    conditions_data = manifest.metadata.get("conditions", [])
    if not conditions_data:
        return False, ["No condition definitions stored in manifest metadata"]

    experiment_dir = os.path.dirname(os.path.abspath(original_manifest_path))
    rerun_dir = target_output_dir or os.path.join(experiment_dir, "reproduction_run")

    seeds = tuple(sorted(original_df["seed"].unique()))
    strategies = tuple(sorted(original_df["strategy"].unique()))

    config_dict = {
        "name": f"{manifest.experiment_name}_repro",
        "description": f"Reproducibility verification of {manifest.experiment_name}",
        "conditions": conditions_data,
        "seeds": list(seeds),
        "strategies": list(strategies),
        "output_dir": rerun_dir,
    }
    config = ExperimentConfig.from_dict(config_dict)

    # Run the batch
    runner = ExperimentRunner(config)
    new_manifest = runner.run()

    new_runs_csv = new_manifest.output_files.get("runs_csv")
    if not new_runs_csv or not os.path.exists(new_runs_csv):
        return False, ["New runs CSV was not produced"]

    new_df = pd.read_csv(new_runs_csv)

    discrepancies: list[str] = []

    # Sort both for exact comparison
    orig_sorted = original_df.sort_values(by=["condition_id", "seed", "strategy"]).reset_index(drop=True)
    new_sorted = new_df.sort_values(by=["condition_id", "seed", "strategy"]).reset_index(drop=True)

    if len(orig_sorted) != len(new_sorted):
        discrepancies.append(
            f"Run count mismatch: original={len(orig_sorted)}, reproduced={len(new_sorted)}"
        )
        return False, discrepancies

    for idx, orig_row in orig_sorted.iterrows():
        new_row = new_sorted.iloc[idx]
        run_id = orig_row["run_id"]

        # Check identical identities
        if orig_row["run_id"] != new_row["run_id"]:
            discrepancies.append(f"Row {idx} run_id mismatch: {orig_row['run_id']} vs {new_row['run_id']}")
            continue

        # Check final route cost
        orig_cost = float(orig_row["final_cost"])
        new_cost = float(new_row["final_cost"])
        if abs(orig_cost - new_cost) > tolerance:
            discrepancies.append(
                f"Run {run_id} final_cost mismatch: orig={orig_cost:.8f}, new={new_cost:.8f}"
            )

        # Check computational effort (must be exact integer match)
        orig_effort = int(orig_row["total_computational_effort"])
        new_effort = int(new_row["total_computational_effort"])
        if orig_effort != new_effort:
            discrepancies.append(
                f"Run {run_id} computational_effort mismatch: orig={orig_effort}, new={new_effort}"
            )

        # Check disruption
        orig_disr = float(orig_row["mean_disruption"])
        new_disr = float(new_row["mean_disruption"])
        if abs(orig_disr - new_disr) > tolerance:
            discrepancies.append(
                f"Run {run_id} mean_disruption mismatch: orig={orig_disr:.8f}, new={new_disr:.8f}"
            )

    is_reproducible = len(discrepancies) == 0
    return is_reproducible, discrepancies


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce experiment matrix.")
    parser.add_argument("--config", type=str, help="Path to experiment config JSON")
    parser.add_argument("--manifest", type=str, help="Path to manifest JSON to verify")
    args = parser.parse_args()

    if args.config:
        config = ExperimentConfig.load(args.config)
        runner = ExperimentRunner(config)
        manifest = runner.run()
        print(f"Executed experiment. Manifest saved to {manifest.output_files.get('manifest_json')}")
    elif args.manifest:
        ok, errors = verify_reproducibility(args.manifest)
        if ok:
            print(f"SUCCESS: Manifest {args.manifest} reproduced exactly.")
            sys.exit(0)
        else:
            print(f"FAILURE: Discrepancies found:\n" + "\n".join(errors))
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
