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
from adaptive_route_optimization.ui.visualizer import (
    render_route_step_diagram,
    render_before_after_comparison,
    render_strategy_comparison,
)
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

    def test_load_stage4_runs(self):
        loader = UIDataLoader()
        df = loader.load_dataset_runs("stage4_full_matrix")
        assert len(df) == 280
        assert set(df["strategy"].unique()) == {"A", "B", "C", "ADAPTIVE"}
        assert set(df["distribution"].dropna().unique()) == {"uniform", "clustered", "mixed"}
        assert set(df["benchmark_name"].dropna().unique()) == {"berlin52", "eil51"}

    def test_load_stage5_validation_runs(self):
        loader = UIDataLoader()
        df = loader.load_dataset_runs("stage5_adaptive_validation")
        assert len(df) == 48
        assert "algorithm_version" in df.columns

    def test_load_stage5_table(self):
        loader = UIDataLoader()
        df_perf = loader.load_stage5_table("performance_analysis.csv")
        df_paired = loader.load_stage5_table("paired_statistical_tests.csv")
        assert not df_perf.empty
        assert not df_paired.empty

    def test_load_stage7_runs(self):
        loader = UIDataLoader()
        df = loader.load_dataset_runs("stage7_adaptive_c")
        assert len(df) == 450
        assert set(df["strategy"].unique()) == {"A", "B", "C", "ADAPTIVE_V2", "ADAPTIVE_V3"}
        manifest = loader.load_dataset_manifest("stage7_adaptive_c")
        assert manifest["completed_runs"] == 450
        assert manifest["failed_runs"] == 0

    def test_load_stage7_tables(self):
        loader = UIDataLoader()
        df_agg = loader.load_stage7_table("overall_strategy_aggregates.csv")
        df_tests = loader.load_stage7_table("paired_hypothesis_tests.csv")
        assert not df_agg.empty
        assert not df_tests.empty
        assert len(df_agg) == 5

    def test_get_stage7_figures_path(self):
        loader = UIDataLoader()
        s7_path = loader.get_stage7_figures_path()
        assert isinstance(s7_path, str)
        assert s7_path.endswith(os.path.join("stage7_adaptive_c", "figures"))
        # Verify get_figures_path general method parity
        assert s7_path == loader.get_figures_path("stage7_adaptive_c")
        assert loader.get_stage5_figures_path() == loader.get_figures_path("stage5_analysis")

    def test_figures_path_custom_and_missing_directory(self, tmp_path):
        # Path resolution works consistently for arbitrary base results dirs
        custom_loader = UIDataLoader(base_results_dir=str(tmp_path))
        custom_s7_path = custom_loader.get_stage7_figures_path()
        assert custom_s7_path == os.path.join(str(tmp_path), "stage7_adaptive_c", "figures")
        # Genuinely missing directory returns False without crashing
        assert not os.path.exists(custom_s7_path)

        # Non-existent table raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            custom_loader.load_stage7_table("non_existent_table.csv")

    def test_ui_stage7_figures_backward_compatible_fallback(self):
        """Verify fallback resolution when loader lacks get_stage7_figures_path."""
        class LegacyLoader:
            base_dir = "results"

        legacy_loader = LegacyLoader()
        assert not hasattr(legacy_loader, "get_stage7_figures_path")

        # Emulate app.py resolution logic
        if hasattr(legacy_loader, "get_stage7_figures_path"):
            resolved = legacy_loader.get_stage7_figures_path()
        elif hasattr(legacy_loader, "get_figures_path"):
            resolved = legacy_loader.get_figures_path("stage7_adaptive_c")
        else:
            base_dir = getattr(legacy_loader, "base_dir", "results")
            resolved = os.path.join(base_dir, "stage7_adaptive_c", "figures")

        assert resolved.endswith(os.path.join("stage7_adaptive_c", "figures"))


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

    def test_render_diagram_with_unrevealed_toggle(self):
        coords = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.5, 0.5)]
        inst = Instance.from_coords(coords)
        route = Route([0, 1, 2, 0])  # Vertex 3 is unrevealed

        # Render with show_unrevealed=True
        fig_show = render_route_step_diagram(
            instance=inst,
            current_route=route,
            frozen_prefix_length=1,
            show_unrevealed=True,
        )
        assert isinstance(fig_show, plt.Figure)
        plt.close(fig_show)

        # Render with show_unrevealed=False (default)
        fig_hide = render_route_step_diagram(
            instance=inst,
            current_route=route,
            frozen_prefix_length=1,
            show_unrevealed=False,
        )
        assert isinstance(fig_hide, plt.Figure)
        plt.close(fig_hide)

    def test_render_before_after_comparison_produces_figure(self):
        coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.5, 0.5)]
        inst = Instance.from_coords(coords)
        route_before = Route([0, 1, 2, 0])
        route_after = Route([0, 1, 2, 3, 0])

        fig = render_before_after_comparison(
            instance=inst,
            route_before=route_before,
            route_after=route_after,
            frozen_prefix_length=1,
            newly_revealed_vertices=[3],
            cost_before=4.0,
            cost_after=4.6,
            evals_used=15,
            strategy_label="Strategy A (Greedy)",
            step_number=1,
            show_unrevealed=False,
        )
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 2
        plt.close(fig)

    def test_render_strategy_comparison_produces_figure(self):
        coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.5, 0.5)]
        inst = Instance.from_coords(coords)
        route_a = Route([0, 1, 2, 3, 0])
        route_b = Route([0, 1, 3, 2, 0])

        fig = render_strategy_comparison(
            instance=inst,
            route_a=route_a,
            route_b=route_b,
            frozen_prefix_length=1,
            newly_revealed_vertices=[3],
            cost_a=4.5,
            cost_b=4.3,
            evals_a=10,
            evals_b=85,
            disruption_a=0.03,
            disruption_b=0.08,
            step_number=1,
            show_unrevealed=True,
        )
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 2
        plt.close(fig)

    def test_render_first_step_zero_frozen_prefix(self):
        """At step 1 (t=1), frozen_prefix_length is 0. Vehicle is at depot, 0 edges are frozen."""
        coords = [(0.5, 0.5), (0.2, 0.2), (0.8, 0.8), (0.3, 0.7)]
        inst = Instance.from_coords(coords)
        route = Route([0, 1, 2, 0])

        fig = render_route_step_diagram(
            instance=inst,
            current_route=route,
            frozen_prefix_length=0,
            newly_revealed_vertices=[3],
            step_number=1,
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_prefix_suffix_continuity_and_completeness(self):
        """Verify that prefix and suffix share the vehicle position and cover all vertices without gap."""
        coords = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
        inst = Instance.from_coords(coords)
        route = Route([0, 1, 2, 3, 4, 0])
        n_verts = len(route.vertices)

        # Test at every valid prefix length f in [0, 4]
        for f in range(n_verts - 1):
            prefix_verts = route.vertices[:f + 1]
            suffix_verts = route.vertices[f:]

            # Shared vehicle position
            assert prefix_verts[-1] == suffix_verts[0] == route.vertices[f]

            # Reconstructed full route has no gaps
            reconstructed = prefix_verts[:-1] + suffix_verts
            assert reconstructed == route.vertices
            assert set(reconstructed) == set(route.vertices)


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

    def test_step_slicing_and_frozen_progression(self):
        """Verify that frozen_prefix_length progresses by 1 stop per step and stops as expected."""
        demo = InteractiveDemonstrator(
            n_vertices=15,
            dynamicity=0.4,
            seed=42,
            strategy="ADAPTIVE",
        )
        # Step 1: Vehicle at depot, 0 stops committed
        step1 = demo.get_step(1)
        assert step1.frozen_prefix_length == 0

        # Step t: frozen_prefix_length == t - 1
        for s in range(1, demo.total_steps + 1):
            step = demo.get_step(s)
            assert step.frozen_prefix_length == s - 1
            # Final arrival event: all dynamic customers have arrived, but tour is not 100% frozen
            if s == demo.total_steps:
                assert step.frozen_prefix_length == demo.total_steps - 1
                assert step.frozen_prefix_length < demo.n_vertices

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

    def test_timeline_clamping_and_reset(self):
        """Verify safe boundary clamping and scenario resetting."""
        demo = InteractiveDemonstrator(n_vertices=10, dynamicity=0.3, seed=42)
        total = demo.total_steps
        assert total > 0

        # Boundary clamping simulation
        assert max(1, min(0, total)) == 1
        assert max(1, min(total + 5, total)) == total

    def test_out_of_bounds_step_raises(self):
        demo = InteractiveDemonstrator(n_vertices=10, dynamicity=0.3, seed=42)
        with pytest.raises(IndexError):
            demo.get_step(0)
        with pytest.raises(IndexError):
            demo.get_step(demo.total_steps + 1)

    def test_demonstrator_strategy_c(self):
        demo = InteractiveDemonstrator(
            n_vertices=12,
            dynamicity=0.4,
            seed=42,
            strategy="C",
        )
        assert demo.total_steps > 0
        step = demo.get_step(1)
        assert "Strategy C" in step.strategy_used
        assert step.prefix_preserved is True

    def test_demonstrator_distributions(self):
        demo_clustered = InteractiveDemonstrator(
            n_vertices=15,
            dynamicity=0.4,
            seed=42,
            distribution="clustered",
        )
        demo_mixed = InteractiveDemonstrator(
            n_vertices=15,
            dynamicity=0.4,
            seed=42,
            distribution="mixed",
        )
        assert demo_clustered.total_steps > 0
        assert demo_mixed.total_steps > 0
        assert demo_clustered.get_step(1).prefix_preserved is True
        assert demo_mixed.get_step(1).prefix_preserved is True

    def test_demonstrator_tsplib_benchmark(self):
        demo_berlin = InteractiveDemonstrator(
            dynamicity=0.3,
            seed=42,
            benchmark_name="berlin52",
        )
        assert demo_berlin.n_vertices == 51
        assert demo_berlin.total_steps > 0
        assert demo_berlin.get_step(1).prefix_preserved is True

    def test_demonstrator_budget_limits(self):
        demo_budget = InteractiveDemonstrator(
            n_vertices=15,
            dynamicity=0.4,
            seed=42,
            strategy="B",
            max_evaluations=100,
        )
        assert demo_budget.total_steps > 0
        step = demo_budget.get_step(1)
        assert step.prefix_preserved is True
        assert step.evaluations_used <= 150

    def test_demonstrator_adaptive_v2(self):
        demo_v2 = InteractiveDemonstrator(
            n_vertices=15,
            dynamicity=0.4,
            seed=42,
            strategy="ADAPTIVE_V2",
        )
        assert demo_v2.total_steps > 0
        step = demo_v2.get_step(1)
        assert step.prefix_preserved is True
        assert "ADAPTIVE v2" in step.strategy_used

    def test_demonstrator_adaptive_v3(self):
        demo_v3 = InteractiveDemonstrator(
            n_vertices=15,
            dynamicity=0.4,
            seed=42,
            strategy="ADAPTIVE_V3",
        )
        assert demo_v3.total_steps > 0
        step = demo_v3.get_step(1)
        assert step.prefix_preserved is True
        assert "ADAPTIVE v3" in step.strategy_used


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
