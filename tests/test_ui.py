"""Unit and integration tests for Phase 9 UI and Demonstrator.

Tests cover:
- UIDataLoader loading, schema validation, and filtering
- render_route_step_diagram rendering without GUI display
- InteractiveDemonstrator simulation and frozen-prefix invariance verification
- Research plotting utilities with headless figures and empty/missing column robustness
"""

import os
import pytest
import pandas as pd
import matplotlib.pyplot as plt

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.ui.data_loader import UIDataLoader
from adaptive_route_optimization.ui.visualizer import render_route_step_diagram
from adaptive_route_optimization.ui.demonstrator import InteractiveDemonstrator, DemonstrationStepRecord
from adaptive_route_optimization.ui.plots import (
    plot_cost_by_dynamicity,
    plot_effort_by_dynamicity,
    plot_pareto_frontier,
    plot_disruption_comparison,
    plot_budget_ablation_chart,
)


# ---------------------------------------------------------------------------
# 1. UIDataLoader Tests
# ---------------------------------------------------------------------------

class TestUIDataLoader:
    """Test loading and filtering of saved research datasets."""

    def test_load_pilot_runs(self):
        loader = UIDataLoader()
        df = loader.load_dataset_runs("pilot_matrix")
        assert len(df) == 60
        assert "run_id" in df.columns
        assert "final_cost" in df.columns
        assert "total_computational_effort" in df.columns

    def test_load_held_out_runs(self):
        loader = UIDataLoader()
        df = loader.load_dataset_runs("held_out_matrix")
        assert len(df) == 90
        assert "strategy" in df.columns
        assert set(df["strategy"].unique()) == {"A", "B", "ADAPTIVE"}

    def test_load_manifest(self):
        loader = UIDataLoader()
        manifest = loader.load_dataset_manifest("held_out_matrix")
        assert manifest["completed_runs"] == 90
        assert manifest["failed_runs"] == 0
        assert "git_commit_hash" in manifest

    def test_load_audit_files(self):
        loader = UIDataLoader()
        recon = loader.load_audit_reconciliation()
        inv = loader.load_audit_inventory()
        assert len(recon) == 40
        assert len(inv) == 40

    def test_filter_runs(self):
        loader = UIDataLoader()
        df = loader.load_dataset_runs("pilot_matrix")

        # Filter by size n=50
        filtered = loader.filter_runs(df, sizes=[50])
        assert len(filtered) == 30  # 5 dynamicities * 3 seeds * 2 strategies
        assert set(filtered["total_vertices"].unique()) == {50}

        # Filter by strategy 'A'
        filtered_a = loader.filter_runs(df, strategies=["A"])
        assert len(filtered_a) == 30
        assert set(filtered_a["strategy"].unique()) == {"A"}

    def test_invalid_dataset_raises(self):
        loader = UIDataLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_dataset_runs("non_existent_dataset_directory")


# ---------------------------------------------------------------------------
# 2. Route Visualizer Tests
# ---------------------------------------------------------------------------

class TestRouteVisualizer:
    """Test rendering of 2D spatial route diagrams."""

    def test_render_diagram_produces_figure(self):
        coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.5, 0.5)]
        inst = Instance.from_coords(coords)
        route = Route([0, 1, 2, 3, 4, 0])

        fig = render_route_step_diagram(
            instance=inst,
            current_route=route,
            frozen_prefix_length=2,
            newly_revealed_vertices=[4],
            step_number=1,
            cost_before=4.0,
            cost_after=4.5,
            evals_used=12,
            strategy_label="ADAPTIVE",
        )

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_render_diagram_zero_frozen(self):
        coords = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        inst = Instance.from_coords(coords)
        route = Route([0, 1, 2, 0])

        fig = render_route_step_diagram(
            instance=inst,
            current_route=route,
            frozen_prefix_length=0,
            step_number=0,
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# ---------------------------------------------------------------------------
# 3. Interactive Demonstrator Tests
# ---------------------------------------------------------------------------

class TestInteractiveDemonstrator:
    """Test step-by-step interactive simulation and invariant preservation."""

    def test_demonstrator_simulation_runs(self):
        demo = InteractiveDemonstrator(
            n_vertices=12,
            dynamicity=0.4,
            seed=42,
            strategy="ADAPTIVE",
        )
        assert demo.total_steps > 0
        step1 = demo.get_step(1)
        assert isinstance(step1, DemonstrationStepRecord)
        assert step1.time_step == 1
        assert step1.cost_after > 0.0
        assert step1.evaluations_used > 0
        assert step1.prefix_preserved is True

    def test_frozen_prefix_invariance_all_steps(self):
        """Verify that the frozen prefix remains strictly identical across every step."""
        demo = InteractiveDemonstrator(
            n_vertices=15,
            dynamicity=0.5,
            seed=101,
            strategy="ADAPTIVE",
        )
        for s in range(1, demo.total_steps + 1):
            step = demo.get_step(s)
            assert step.prefix_preserved is True, f"Prefix violated at step {s}!"

    def test_adaptive_captures_rationale_and_features(self):
        demo = InteractiveDemonstrator(
            n_vertices=10,
            dynamicity=0.4,
            seed=42,
            strategy="ADAPTIVE",
        )
        step = demo.get_step(1)
        assert step.decision_rationale is not None
        assert step.state_features is not None
        assert "revealed_ratio" in step.state_features
        assert "uncommitted_count" in step.state_features

    def test_out_of_bounds_step_raises(self):
        demo = InteractiveDemonstrator(n_vertices=10, dynamicity=0.3, seed=42)
        with pytest.raises(IndexError):
            demo.get_step(0)
        with pytest.raises(IndexError):
            demo.get_step(demo.total_steps + 1)


# ---------------------------------------------------------------------------
# 4. Research Plots Tests
# ---------------------------------------------------------------------------

class TestResearchPlots:
    """Test figure generation for all research charts."""

    def test_plots_generate_figures(self):
        loader = UIDataLoader()
        df_held = loader.load_dataset_runs("held_out_matrix")
        df_budget = loader.load_dataset_runs("budgeted_pilot")

        fig1 = plot_cost_by_dynamicity(df_held)
        assert isinstance(fig1, plt.Figure)
        plt.close(fig1)

        fig2 = plot_effort_by_dynamicity(df_held)
        assert isinstance(fig2, plt.Figure)
        plt.close(fig2)

        fig3 = plot_pareto_frontier(df_held)
        assert isinstance(fig3, plt.Figure)
        plt.close(fig3)

        fig4 = plot_disruption_comparison(df_held)
        assert isinstance(fig4, plt.Figure)
        plt.close(fig4)

        fig5 = plot_budget_ablation_chart(df_budget)
        assert isinstance(fig5, plt.Figure)
        plt.close(fig5)

    def test_plots_empty_dataframe_robustness(self):
        empty_df = pd.DataFrame()
        fig = plot_cost_by_dynamicity(empty_df)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
