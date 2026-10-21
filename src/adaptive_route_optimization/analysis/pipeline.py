"""End-to-End Research Analysis Pipeline for Dynamic Route Optimization.

Orchestrates data validation, metric aggregation, statistical testing,
component and budget ablation, figure generation, and structured report compilation.
References: RESEARCH_SPEC.md, MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phase 7).
"""

from __future__ import annotations
import json
import os
from dataclasses import asdict
from typing import Any, Optional
import pandas as pd

from adaptive_route_optimization.analysis.validator import (
    DataValidationReport,
    validate_experiment_data,
)
from adaptive_route_optimization.analysis.metrics import (
    build_paired_dataset,
    aggregate_by_condition,
    aggregate_scalability,
    compute_step_level_statistics,
)
from adaptive_route_optimization.analysis.statistical import (
    run_full_statistical_battery,
)
from adaptive_route_optimization.analysis.ablation import (
    analyze_component_ablation,
    analyze_dynamicity_regime_ablation,
    analyze_budget_cap_ablation,
)
from adaptive_route_optimization.analysis.visualizer import (
    plot_dynamicity_vs_cost,
    plot_dynamicity_vs_response_time,
    plot_size_vs_cost,
    plot_size_vs_runtime,
    plot_evals_vs_improvement,
    plot_paired_comparison,
    plot_route_disruption,
    plot_quality_vs_computation_tradeoff,
    plot_budget_ablation,
)


class AnalysisPipeline:
    """Executes full reproducible analysis workflow on experiment results."""

    def __init__(
        self,
        runs_csv_path: str = "results/pilot_matrix/runs.csv",
        steps_csv_path: Optional[str] = "results/pilot_matrix/steps.csv",
        manifest_json_path: Optional[str] = "results/pilot_matrix/manifest.json",
        budgeted_runs_csv_path: Optional[str] = "results/budgeted_pilot/runs.csv",
        tables_output_dir: str = "results/tables",
        figures_output_dir: str = "results/figures",
    ) -> None:
        self.runs_csv_path = runs_csv_path
        self.steps_csv_path = steps_csv_path
        self.manifest_json_path = manifest_json_path
        self.budgeted_runs_csv_path = budgeted_runs_csv_path
        self.tables_output_dir = tables_output_dir
        self.figures_output_dir = figures_output_dir

        self.runs_df: pd.DataFrame = pd.DataFrame()
        self.steps_df: pd.DataFrame = pd.DataFrame()
        self.manifest_dict: dict[str, Any] = {}
        self.budget_runs_df: pd.DataFrame = pd.DataFrame()

        self.validation_report: Optional[DataValidationReport] = None
        self.paired_df: pd.DataFrame = pd.DataFrame()
        self.condition_summary_df: pd.DataFrame = pd.DataFrame()
        self.size_scalability_df: pd.DataFrame = pd.DataFrame()
        self.dyn_scalability_df: pd.DataFrame = pd.DataFrame()
        self.step_stats_df: pd.DataFrame = pd.DataFrame()
        self.stats_battery_df: pd.DataFrame = pd.DataFrame()
        self.ablation_df: pd.DataFrame = pd.DataFrame()
        self.regime_ablation_df: pd.DataFrame = pd.DataFrame()
        self.budget_ablation_df: pd.DataFrame = pd.DataFrame()

    def load_data(self) -> None:
        """Load and parse experimental files from disk."""
        if not os.path.exists(self.runs_csv_path):
            raise FileNotFoundError(f"Runs file not found: {self.runs_csv_path}")

        self.runs_df = pd.read_csv(self.runs_csv_path)

        if self.steps_csv_path and os.path.exists(self.steps_csv_path):
            self.steps_df = pd.read_csv(self.steps_csv_path)

        if self.manifest_json_path and os.path.exists(self.manifest_json_path):
            with open(self.manifest_json_path, "r", encoding="utf-8") as f:
                self.manifest_dict = json.load(f)

        if self.budgeted_runs_csv_path and os.path.exists(self.budgeted_runs_csv_path):
            self.budget_runs_df = pd.read_csv(self.budgeted_runs_csv_path)

    def run_analysis(self) -> dict[str, Any]:
        """Execute complete analysis pipeline and generate all artifacts."""
        self.load_data()

        # 1. Validation
        self.validation_report = validate_experiment_data(
            self.runs_df,
            self.steps_df,
            self.manifest_dict,
        )
        if not self.validation_report.is_valid:
            error_msgs = [i.message for i in self.validation_report.issues if i.severity == "ERROR"]
            raise ValueError(f"Experiment data validation failed: {error_msgs}")

        # 2. Metric Aggregations & Paired Comparison
        self.paired_df = build_paired_dataset(self.runs_df)
        self.condition_summary_df = aggregate_by_condition(self.runs_df)
        self.size_scalability_df, self.dyn_scalability_df = aggregate_scalability(self.runs_df)
        self.step_stats_df = compute_step_level_statistics(self.steps_df)

        # 3. Statistical Hypothesis Testing
        self.stats_battery_df = run_full_statistical_battery(self.paired_df)

        # 4. Ablation Studies
        self.ablation_df = analyze_component_ablation(self.paired_df)
        self.regime_ablation_df = analyze_dynamicity_regime_ablation(self.paired_df)
        if not self.budget_runs_df.empty:
            self.budget_ablation_df = analyze_budget_cap_ablation(self.budget_runs_df)

        # 5. Export Tables
        os.makedirs(self.tables_output_dir, exist_ok=True)
        self.paired_df.to_csv(os.path.join(self.tables_output_dir, "paired_strategy_comparison.csv"), index=False)
        self.condition_summary_df.to_csv(os.path.join(self.tables_output_dir, "summary_by_condition.csv"), index=False)
        self.size_scalability_df.to_csv(os.path.join(self.tables_output_dir, "scalability_by_size.csv"), index=False)
        self.dyn_scalability_df.to_csv(os.path.join(self.tables_output_dir, "scalability_by_dynamicity.csv"), index=False)
        self.stats_battery_df.to_csv(os.path.join(self.tables_output_dir, "statistical_battery.csv"), index=False)
        self.ablation_df.to_csv(os.path.join(self.tables_output_dir, "ablation_by_condition.csv"), index=False)
        self.regime_ablation_df.to_csv(os.path.join(self.tables_output_dir, "ablation_by_regime.csv"), index=False)
        if not self.step_stats_df.empty:
            self.step_stats_df.to_csv(os.path.join(self.tables_output_dir, "step_level_statistics.csv"), index=False)
        if not self.budget_ablation_df.empty:
            self.budget_ablation_df.to_csv(os.path.join(self.tables_output_dir, "budget_ablation.csv"), index=False)

        # 6. Generate Figures
        os.makedirs(self.figures_output_dir, exist_ok=True)
        plot_dynamicity_vs_cost(self.runs_df, os.path.join(self.figures_output_dir, "fig1_dynamicity_vs_cost.png"))
        plot_dynamicity_vs_response_time(self.runs_df, os.path.join(self.figures_output_dir, "fig2_dynamicity_vs_response_time.png"))
        plot_size_vs_cost(self.runs_df, os.path.join(self.figures_output_dir, "fig3_size_vs_cost.png"))
        plot_size_vs_runtime(self.runs_df, os.path.join(self.figures_output_dir, "fig4_size_vs_runtime.png"))
        plot_evals_vs_improvement(self.paired_df, os.path.join(self.figures_output_dir, "fig5_evals_vs_cost_improvement.png"))
        plot_paired_comparison(self.paired_df, os.path.join(self.figures_output_dir, "fig6_paired_comparison.png"))
        plot_route_disruption(self.runs_df, os.path.join(self.figures_output_dir, "fig7_route_disruption.png"))
        plot_quality_vs_computation_tradeoff(self.runs_df, os.path.join(self.figures_output_dir, "fig8_quality_vs_computation_tradeoff.png"))
        if not self.budget_runs_df.empty:
            plot_budget_ablation(self.budget_runs_df, os.path.join(self.figures_output_dir, "fig9_budget_ablation.png"))

        # 7. Compile Summary Report Dict
        summary_payload = {
            "validation": self.validation_report.to_dict(),
            "sample_size_pairs": len(self.paired_df),
            "statistical_battery": self.stats_battery_df.to_dict(orient="records"),
            "regime_ablation": self.regime_ablation_df.to_dict(orient="records"),
        }
        with open(os.path.join(self.tables_output_dir, "analysis_summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

        return summary_payload


def run_pipeline() -> dict[str, Any]:
    """Convenience entry point to run full analysis pipeline with default paths."""
    pipeline = AnalysisPipeline()
    return pipeline.run_analysis()
