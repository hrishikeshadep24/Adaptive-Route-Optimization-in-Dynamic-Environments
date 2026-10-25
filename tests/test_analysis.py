"""Comprehensive Tests for Phase 7 Research Analysis & Ablation Package.

Covers data validation, paired matching, metric formulas, statistical testing,
component/budget ablation, and automated figure/table generation.
References: RESEARCH_SPEC.md, PHASE_PLAN.md (Phase 7).
"""

from __future__ import annotations
import os
import shutil
import tempfile
import numpy as np
import pandas as pd
import pytest

from adaptive_route_optimization.analysis.validator import (
    DataValidationReport,
    validate_experiment_data,
)
from adaptive_route_optimization.analysis.metrics import (
    compute_relative_improvement,
    build_paired_dataset,
    aggregate_by_condition,
    aggregate_scalability,
    compute_step_level_statistics,
)
from adaptive_route_optimization.analysis.statistical import (
    compute_bootstrap_ci,
    run_paired_analysis,
    run_full_statistical_battery,
)
from adaptive_route_optimization.analysis.ablation import (
    analyze_component_ablation,
    analyze_dynamicity_regime_ablation,
    analyze_budget_cap_ablation,
)
from adaptive_route_optimization.analysis.visualizer import (
    plot_dynamicity_vs_cost,
    plot_paired_comparison,
)
from adaptive_route_optimization.analysis.pipeline import AnalysisPipeline


@pytest.fixture
def sample_runs_df() -> pd.DataFrame:
    """Fixture providing synthetic valid runs dataframe with 2 conditions, 2 seeds, 2 strategies."""
    records = []
    for cond_id, n, alpha in [("c1", 50, 0.2), ("c2", 50, 0.6)]:
        for seed in [42, 101]:
            # Initial cost identical between A and B (Rule 10)
            init_cost = 500.0 + seed
            records.append({
                "run_id": f"{cond_id}_s{seed}_A",
                "condition_id": cond_id,
                "strategy": "A",
                "seed": seed,
                "total_vertices": n,
                "dynamicity": alpha,
                "num_events": 10,
                "initial_cost": init_cost,
                "final_cost": 600.0,
                "total_computational_effort": 200,
                "total_response_time_ms": 10.0,
                "mean_disruption": 0.03,
                "all_feasible": True,
                "budget_type": "unbounded",
                "budget_limit": np.nan,
                "git_commit_hash": "testcommit",
                "timestamp": "2026-10-21T00:00:00",
            })
            records.append({
                "run_id": f"{cond_id}_s{seed}_B",
                "condition_id": cond_id,
                "strategy": "B",
                "seed": seed,
                "total_vertices": n,
                "dynamicity": alpha,
                "num_events": 10,
                "initial_cost": init_cost,
                "final_cost": 550.0 if alpha == 0.2 else 620.0,  # B better at low dyn, worse at high
                "total_computational_effort": 5000,
                "total_response_time_ms": 250.0,
                "mean_disruption": 0.08,
                "all_feasible": True,
                "budget_type": "unbounded",
                "budget_limit": np.nan,
                "git_commit_hash": "testcommit",
                "timestamp": "2026-10-21T00:00:00",
            })
    return pd.DataFrame(records)


class TestValidator:
    """Tests data validation logic and detection of protocol violations."""

    def test_valid_data_passes(self, sample_runs_df):
        report = validate_experiment_data(sample_runs_df)
        assert report.is_valid
        assert report.rule_10_passed
        assert report.all_feasible
        assert len([i for i in report.issues if i.severity == "ERROR"]) == 0

    def test_rule_10_violation_caught(self, sample_runs_df):
        # Tamper with Strategy B initial cost
        bad_df = sample_runs_df.copy()
        bad_df.loc[bad_df["strategy"] == "B", "initial_cost"] = 999.0
        report = validate_experiment_data(bad_df)
        assert not report.is_valid
        assert not report.rule_10_passed
        assert any(i.category == "RULE_10_PARITY" for i in report.issues)

    def test_infeasible_run_caught(self, sample_runs_df):
        bad_df = sample_runs_df.copy()
        bad_df.loc[0, "all_feasible"] = False
        report = validate_experiment_data(bad_df)
        assert not report.is_valid
        assert any(i.category == "FEASIBILITY" for i in report.issues)

    def test_out_of_bounds_disruption(self, sample_runs_df):
        bad_df = sample_runs_df.copy()
        bad_df.loc[0, "mean_disruption"] = 1.5
        report = validate_experiment_data(bad_df)
        assert not report.is_valid
        assert any(i.category == "METRICS" for i in report.issues)


class TestMetricsAndPairing:
    """Tests metric definitions, paired construction, and aggregations."""

    def test_relative_improvement_formula(self):
        # Cost reduced from 100 to 80 -> 20% improvement
        assert compute_relative_improvement(100.0, 80.0) == pytest.approx(20.0)
        # Cost increased from 100 to 120 -> -20% improvement
        assert compute_relative_improvement(100.0, 120.0) == pytest.approx(-20.0)
        # Zero baseline
        assert compute_relative_improvement(0.0, 50.0) == 0.0

    def test_paired_dataset_construction(self, sample_runs_df):
        paired = build_paired_dataset(sample_runs_df)
        assert len(paired) == 4  # 2 conditions * 2 seeds
        assert "pct_cost_improvement" in paired.columns
        assert "effort_ratio" in paired.columns
        assert "time_ratio" in paired.columns
        assert "b_superior" in paired.columns

        # Condition 1 (alpha 0.2): B cost 550 < A cost 600 -> B superior
        c1_pair = paired[paired["condition_id"] == "c1"].iloc[0]
        assert c1_pair["b_superior"]
        assert c1_pair["pct_cost_improvement"] > 0

        # Condition 2 (alpha 0.6): B cost 620 > A cost 600 -> B inferior
        c2_pair = paired[paired["condition_id"] == "c2"].iloc[0]
        assert c2_pair["b_inferior"]
        assert c2_pair["pct_cost_improvement"] < 0

    def test_aggregate_by_condition(self, sample_runs_df):
        agg = aggregate_by_condition(sample_runs_df)
        assert len(agg) == 4  # 2 conditions * 2 strategies
        assert "final_cost_mean" in agg.columns


class TestStatisticalBattery:
    """Tests hypothesis testing, effect size, and bootstrap confidence intervals."""

    def test_bootstrap_ci_deterministic(self):
        diffs = [10.0, 12.0, 15.0, 9.0, 11.0, 13.0]
        low1, up1 = compute_bootstrap_ci(diffs, seed=42)
        low2, up2 = compute_bootstrap_ci(diffs, seed=42)
        assert low1 == low2
        assert up1 == up2
        assert low1 < np.mean(diffs) < up1

    def test_paired_analysis_execution(self):
        a = [100.0, 110.0, 105.0, 120.0, 115.0]
        b = [90.0, 95.0, 92.0, 100.0, 98.0]  # B consistently better
        res = run_paired_analysis(a, b, metric_name="Test Cost")
        assert res.sample_size == 5
        assert res.mean_diff > 0
        assert res.pct_impr_mean > 0
        assert res.statistically_significant_05
        assert res.cohens_d > 0

    def test_full_battery(self, sample_runs_df):
        paired = build_paired_dataset(sample_runs_df)
        battery = run_full_statistical_battery(paired)
        assert len(battery) == 4
        metrics = battery["metric_name"].tolist()
        assert "Route Cost" in metrics
        assert "Computational Effort" in metrics


class TestAblationAndVisualizer:
    """Tests ablation summaries and headless plot generation."""

    def test_ablation_summaries(self, sample_runs_df):
        paired = build_paired_dataset(sample_runs_df)
        comp_abl = analyze_component_ablation(paired)
        assert len(comp_abl) == 2
        reg_abl = analyze_dynamicity_regime_ablation(paired)
        assert len(reg_abl) >= 1

    def test_plot_generation(self, sample_runs_df):
        tmp_dir = tempfile.mkdtemp()
        try:
            fig1_path = os.path.join(tmp_dir, "fig1.png")
            fig6_path = os.path.join(tmp_dir, "fig6.png")
            plot_dynamicity_vs_cost(sample_runs_df, fig1_path)
            paired = build_paired_dataset(sample_runs_df)
            plot_paired_comparison(paired, fig6_path)
            assert os.path.exists(fig1_path)
            assert os.path.exists(fig6_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_end_to_end_pipeline(self, sample_runs_df):
        tmp_dir = tempfile.mkdtemp()
        try:
            runs_csv = os.path.join(tmp_dir, "runs.csv")
            sample_runs_df.to_csv(runs_csv, index=False)
            tables_dir = os.path.join(tmp_dir, "tables")
            figures_dir = os.path.join(tmp_dir, "figures")

            pipeline = AnalysisPipeline(
                runs_csv_path=runs_csv,
                steps_csv_path=None,
                manifest_json_path=None,
                budgeted_runs_csv_path=None,
                tables_output_dir=tables_dir,
                figures_output_dir=figures_dir,
            )
            summary = pipeline.run_analysis()
            assert summary["sample_size_pairs"] == 4
            assert os.path.exists(os.path.join(tables_dir, "summary_by_condition.csv"))
            assert os.path.exists(os.path.join(figures_dir, "fig1_dynamicity_vs_cost.png"))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
