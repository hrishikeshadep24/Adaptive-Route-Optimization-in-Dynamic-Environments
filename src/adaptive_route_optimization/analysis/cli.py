"""Analysis CLI Entry Point."""

from __future__ import annotations
import argparse
import sys
from adaptive_route_optimization.analysis.pipeline import AnalysisPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 7 research analysis pipeline.")
    parser.add_argument("--runs", default="results/pilot_matrix/runs.csv", help="Path to runs.csv")
    parser.add_argument("--steps", default="results/pilot_matrix/steps.csv", help="Path to steps.csv")
    parser.add_argument("--manifest", default="results/pilot_matrix/manifest.json", help="Path to manifest.json")
    parser.add_argument("--budget-runs", default="results/budgeted_pilot/runs.csv", help="Path to budgeted pilot runs.csv")
    parser.add_argument("--tables-dir", default="results/tables", help="Directory for output tables")
    parser.add_argument("--figures-dir", default="results/figures", help="Directory for output figures")

    args = parser.parse_args()

    pipeline = AnalysisPipeline(
        runs_csv_path=args.runs,
        steps_csv_path=args.steps,
        manifest_json_path=args.manifest,
        budgeted_runs_csv_path=args.budget_runs,
        tables_output_dir=args.tables_dir,
        figures_output_dir=args.figures_dir,
    )

    try:
        summary = pipeline.run_analysis()
        print("=== PHASE 7 ANALYSIS PIPELINE COMPLETED SUCCESSFULLY ===")
        print(f"Validated Runs: {summary['validation']['total_runs']}")
        print(f"Paired Comparisons: {summary['sample_size_pairs']}")
        print(f"Output Tables Saved to: {args.tables_dir}")
        print(f"Output Figures Saved to: {args.figures_dir}")
    except Exception as e:
        print(f"ERROR executing analysis pipeline: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
