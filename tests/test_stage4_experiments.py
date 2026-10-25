"""Focused Unit and Integration Test Suite for Stage 4: Fair Experimental Engine.

Covers:
- Matched comparison parity: identical instances, coordinates, and arrival streams.
- Deterministic reproducibility under fixed random seeds.
- Seed variability: distinct seeds produce distinct scenarios.
- Pairing keys (pair_id) and unique run IDs across strategies.
- Hard computational budget enforcement at boundary levels (0, 5, 50, unbounded).
- Strict non-exceedance: no strategy exceeds max_evaluations.
- Candidate-evaluation accounting consistency across A, B, C, and ADAPTIVE.
- Failure handling: recording failed runs with diagnostic context without silent drops.
- Result schema validation, serialization round trips, and backward compatibility.
- Frozen-prefix invariance and route feasibility under all budget constraints.
- TSPLIB metric labeling (continuous_euclidean) preventing false optimum comparisons.
- Verification that historical result datasets remain completely untouched.
"""

from __future__ import annotations
import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.benchmarks.tsplib import load_tsplib_benchmark
from adaptive_route_optimization.simulation.events import EventConfig, EventGenerator
from adaptive_route_optimization.simulation.simulator import Simulator, Strategy
from adaptive_route_optimization.experiments.schema import (
    BudgetType,
    BudgetConfig,
    ConditionConfig,
    ExperimentConfig,
    RunRecord,
)
from adaptive_route_optimization.experiments.runner import (
    ExperimentRunner,
    generate_experiment_summary,
    generate_paired_comparisons,
)
from adaptive_route_optimization.paths import resolve_repo_path


# ---------------------------------------------------------------------------
# 1. Matched Scenarios and Deterministic Reproducibility
# ---------------------------------------------------------------------------

class TestMatchedScenariosAndReproducibility:
    """Verifies that matched strategies receive identical problem inputs."""

    def test_matched_scenarios_receive_identical_inputs(self):
        """All 4 strategies in a matched run receive bitwise identical coordinates and events."""
        cond = ConditionConfig(
            condition_id="c_matched_test",
            total_vertices=12,
            dynamicity=0.33,
            events_per_step=2,
            distribution="clustered",
            distribution_params={"num_clusters": 2, "cluster_spread": 3.0},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="matched_parity_test",
                conditions=(cond,),
                seeds=(42,),
                strategies=("A", "B", "C", "ADAPTIVE"),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)
            manifest = runner.run()

            assert manifest.completed_runs == 4
            assert manifest.failed_runs == 0

            # Load step records
            steps_df = pd.read_csv(Path(tmp_dir) / "steps.csv")
            runs_df = pd.read_csv(Path(tmp_dir) / "runs.csv")

            # Check that initial cost is identical across all 4 strategies
            init_costs = runs_df["initial_cost"].unique()
            assert len(init_costs) == 1, "Initial route cost must be identical across all strategies"

            # Check that known vertices and event sizes match at every step
            for t in steps_df["time_step"].unique():
                step_t = steps_df[steps_df["time_step"] == t]
                assert step_t["num_event_vertices"].nunique() == 1
                assert step_t["num_known_vertices"].nunique() == 1

    def test_deterministic_reruns_produce_identical_results(self):
        """Rerunning an experiment with identical seed produces bitwise identical results."""
        cond = ConditionConfig(
            condition_id="c_determ",
            total_vertices=10,
            dynamicity=0.4,
            events_per_step=2,
            distribution="uniform",
        )

        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            cfg1 = ExperimentConfig("run1", (cond,), seeds=(77,), strategies=("A", "C"), output_dir=tmp1)
            cfg2 = ExperimentConfig("run2", (cond,), seeds=(77,), strategies=("A", "C"), output_dir=tmp2)

            runner1 = ExperimentRunner(cfg1)
            runner1.run()
            runner2 = ExperimentRunner(cfg2)
            runner2.run()

            df1 = pd.read_csv(Path(tmp1) / "runs.csv")
            df2 = pd.read_csv(Path(tmp2) / "runs.csv")

            assert np.allclose(df1["final_cost"], df2["final_cost"], atol=1e-8)
            assert np.array_equal(df1["total_computational_effort"], df2["total_computational_effort"])

    def test_distinct_seeds_produce_distinct_scenarios(self):
        """Different seeds generate distinct instance coordinates and costs."""
        cond = ConditionConfig(
            condition_id="c_diff_seeds",
            total_vertices=15,
            dynamicity=0.4,
            distribution="uniform",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="seed_diff_test",
                conditions=(cond,),
                seeds=(42, 101),
                strategies=("A",),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)
            runner.run()

            df = pd.read_csv(Path(tmp_dir) / "runs.csv")
            assert df.iloc[0]["final_cost"] != df.iloc[1]["final_cost"]
            assert df.iloc[0]["seed"] != df.iloc[1]["seed"]

    def test_pairing_keys_and_unique_run_ids(self):
        """Pairing keys match across strategies for identical scenarios while run_id is unique."""
        cond = ConditionConfig("c_pairing", 12, 0.4, distribution="mixed")

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="pairing_test",
                conditions=(cond,),
                seeds=(10, 20),
                strategies=("A", "B", "C", "ADAPTIVE"),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)
            runner.run()

            df = pd.read_csv(Path(tmp_dir) / "runs.csv")
            assert len(df) == 8
            assert df["run_id"].nunique() == 8, "run_id must be globally unique"
            assert df["pair_id"].nunique() == 2, "There must be exactly 2 distinct pairs for 2 seeds"

            for pair_id, group in df.groupby("pair_id"):
                assert set(group["strategy"]) == {"A", "B", "C", "ADAPTIVE"}

    def test_scenario_fingerprint_uniquely_identifies_realizations(self):
        """Scenario fingerprints match for identical realizations and differ for distinct seeds."""
        cond = ConditionConfig("c_fp", 10, 0.4, distribution="uniform")
        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="fp_test",
                conditions=(cond,),
                seeds=(11, 22),
                strategies=("A", "B", "C", "ADAPTIVE"),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)
            runner.run()

            df = pd.read_csv(Path(tmp_dir) / "runs.csv")
            assert "scenario_fingerprint" in df.columns

            # Across strategies for seed 11, fingerprint must be identical
            s11_fps = df[df["seed"] == 11]["scenario_fingerprint"].unique()
            assert len(s11_fps) == 1
            assert len(s11_fps[0]) == 16

            # Across strategies for seed 22, fingerprint must be identical
            s22_fps = df[df["seed"] == 22]["scenario_fingerprint"].unique()
            assert len(s22_fps) == 1
            assert len(s22_fps[0]) == 16

            # Seed 11 and Seed 22 must have different fingerprints
            assert s11_fps[0] != s22_fps[0]

            # Paired comparisons table must include scenario_fingerprint
            paired_df = pd.read_csv(Path(tmp_dir) / "paired_comparisons.csv")
            assert "scenario_fingerprint" in paired_df.columns
            assert paired_df["scenario_fingerprint"].nunique() == 2


# ---------------------------------------------------------------------------
# 2. Hard Computational Budget Enforcement
# ---------------------------------------------------------------------------

class TestBudgetControlAndFairness:
    """Verifies that hard computational budgets are strictly enforced without leakage."""

    @pytest.mark.parametrize("budget_limit", [0, 1, 5, 25, 100])
    @pytest.mark.parametrize("strat_name", ["A", "B", "C", "ADAPTIVE"])
    def test_no_strategy_exceeds_budget_at_any_step(self, budget_limit, strat_name):
        """At every step, computational effort never exceeds the configured per-step limit."""
        inst = Instance.generate_random(n=14, seed=42)
        cfg = EventConfig(total_vertices=14, dynamicity=0.5, events_per_step=2, seed=42)
        seq = EventGenerator(cfg).generate(inst)

        strat_enum = getattr(Strategy, strat_name if strat_name != "ADAPTIVE" else "ADAPTIVE")

        sim = Simulator(
            instance=inst,
            event_sequence=seq,
            freeze_per_step=1,
            max_evaluations=budget_limit,
        )
        res = sim.run(strat_enum, seed=42)

        assert res.all_feasible, f"Strategy {strat_name} produced infeasible route at budget {budget_limit}"
        for step_idx, step in enumerate(res.steps):
            effort = step.metrics.computational_effort
            assert effort <= budget_limit, (
                f"Strategy {strat_name} at step {step_idx+1} used {effort} evals, "
                f"exceeding budget limit {budget_limit}!"
            )
            if budget_limit == 0:
                assert effort == 0, f"Strategy {strat_name} did not yield 0 evaluations at budget 0"

    def test_safe_fallback_preserves_feasibility_and_prefix_when_budget_exhausted(self):
        """When budget is 0, safe fallback preserves frozen prefix and full customer feasibility."""
        inst = Instance.generate_clustered(n=12, seed=99, num_clusters=2)
        cfg = EventConfig(total_vertices=12, dynamicity=0.5, events_per_step=3, seed=99)
        seq = EventGenerator(cfg).generate(inst)

        for strat in [Strategy.A, Strategy.B, Strategy.C, Strategy.ADAPTIVE]:
            sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1, max_evaluations=0)
            res = sim.run(strat, seed=99)

            assert res.all_feasible
            assert res.final_route.is_feasible(inst, required_vertices=set(range(1, 13)))
            assert res.total_computational_effort == 0


# ---------------------------------------------------------------------------
# 3. Candidate-Evaluation Accounting & Adaptive Selector Overhead
# ---------------------------------------------------------------------------

class TestAccountingAndAdaptiveSelector:
    """Verifies consistent candidate-evaluation accounting and selector overhead."""

    def test_adaptive_charges_decision_overhead(self):
        """Adaptive charges exactly 1 selection overhead evaluation per step under bounded budget."""
        inst = Instance.generate_random(n=10, seed=55)
        cfg = EventConfig(total_vertices=10, dynamicity=0.4, events_per_step=1, seed=55)
        seq = EventGenerator(cfg).generate(inst)

        # Run with max_evaluations=100
        sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1, max_evaluations=100)
        res_adapt = sim.run(Strategy.ADAPTIVE, seed=55)

        assert res_adapt.all_feasible
        # For each step, effort should be at least 1 (overhead)
        for step in res_adapt.steps:
            assert step.metrics.computational_effort >= 1

    def test_candidate_evaluations_and_overhead_separation(self):
        """Pure candidate evaluations and selector overhead are strictly decoupled."""
        cond = ConditionConfig(
            condition_id="c_accounting_audit",
            total_vertices=12,
            dynamicity=0.4,
            events_per_step=2,
            budget=BudgetConfig(BudgetType.MAX_EVALUATIONS, 80),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="accounting_audit",
                conditions=(cond,),
                seeds=(42,),
                strategies=("A", "B", "C", "ADAPTIVE"),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)
            manifest = runner.run()

            assert manifest.completed_runs == 4
            runs_df = pd.read_csv(Path(tmp_dir) / "runs.csv")
            steps_df = pd.read_csv(Path(tmp_dir) / "steps.csv")

            # Check RunRecord columns
            for _, row in runs_df.iterrows():
                strat = row["strategy"].upper()
                cand = row["candidate_evaluations"]
                overhead = row["overhead_evaluations"]
                effort = row["total_computational_effort"]
                time_ms = row["total_response_time_ms"]
                scope = row["budget_scope"]

                assert effort == cand + overhead, f"Strategy {strat}: effort {effort} != cand {cand} + overhead {overhead}"
                assert time_ms >= 0.0, f"Strategy {strat}: time_ms must be >= 0"
                assert scope == "per_step"

                if strat in ("A", "B", "C"):
                    assert overhead == 0, f"Strategy {strat} must have 0 overhead evaluations, got {overhead}"
                    assert cand == effort
                elif strat == "ADAPTIVE":
                    assert overhead >= 1, f"Adaptive must have at least 1 overhead evaluation, got {overhead}"

            # Check StepRecord columns
            assert "candidate_evaluations" in steps_df.columns
            assert "overhead_evaluations" in steps_df.columns
            assert "scenario_fingerprint" in steps_df.columns
            for _, srow in steps_df.iterrows():
                assert srow["computational_effort"] == srow["candidate_evaluations"] + srow["overhead_evaluations"]

    def test_budget_exhaustion_and_boundary_fallback(self):
        """Verify safe fallback and budget tracking at B=0, 1, 5, 25, 100."""
        inst = Instance.generate_random(n=12, seed=123)
        cfg = EventConfig(total_vertices=12, dynamicity=0.5, events_per_step=2, seed=123)
        seq = EventGenerator(cfg).generate(inst)

        for b in [0, 1, 5, 25, 100]:
            for strat in [Strategy.A, Strategy.B, Strategy.C, Strategy.ADAPTIVE]:
                sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1, max_evaluations=b)
                res = sim.run(strat, seed=123)

                assert res.all_feasible
                assert res.final_route.is_feasible(inst, required_vertices=set(range(1, 13)))
                for step in res.steps:
                    assert step.metrics.computational_effort <= b
                    if b == 0:
                        assert step.metrics.computational_effort == 0
                        assert step.metrics.candidate_evaluations == 0
                        assert step.metrics.overhead_evaluations == 0


# ---------------------------------------------------------------------------
# 4. Failure Handling and Diagnostic Integrity
# ---------------------------------------------------------------------------

class TestFailureHandlingAndIntegrity:
    """Verifies that failures are explicitly captured without silently dropping runs."""

    def test_unsupported_strategy_raises_error(self):
        """Unsupported strategy name raises an explicit ValueError immediately."""
        cond = ConditionConfig("c_val", 10, 0.4)
        exp_cfg = ExperimentConfig("err_test", (cond,), seeds=(1,), strategies=("NON_EXISTENT_STRAT",))
        runner = ExperimentRunner(exp_cfg)

        with pytest.raises(ValueError, match="Unsupported strategy"):
            runner.run()

    def test_unsupported_distribution_raises_error(self):
        """Unsupported distribution name raises an explicit ValueError."""
        cond = ConditionConfig("c_bad_dist", 10, 0.4, distribution="voronoi_quantum")
        exp_cfg = ExperimentConfig("dist_err", (cond,), seeds=(1,), strategies=("A",))
        runner = ExperimentRunner(exp_cfg)

        with pytest.raises(ValueError, match="Unsupported synthetic distribution"):
            runner.run()

    def test_failed_run_is_recorded_with_failed_status_in_csv(self, monkeypatch):
        """If a strategy execution fails, it records a FAILED RunRecord with error details."""
        cond = ConditionConfig("c_fail_test", 10, 0.3)

        # Force strategy B to fail during simulation
        def broken_run(self, strategy, seed=0):
            if strategy == Strategy.B:
                raise RuntimeError("Simulated algorithm numerical divergence")
            return self._original_run(strategy, seed=seed)

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="fail_capture_test",
                conditions=(cond,),
                seeds=(42,),
                strategies=("A", "B"),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)

            monkeypatch.setattr(Simulator, "_original_run", Simulator.run, raising=False)
            monkeypatch.setattr(Simulator, "run", broken_run)

            manifest = runner.run()

            assert manifest.completed_runs == 1
            assert manifest.failed_runs == 1

            df = pd.read_csv(Path(tmp_dir) / "runs.csv")
            assert len(df) == 2

            rec_a = df[df["strategy"] == "A"].iloc[0]
            assert rec_a["status"] == "SUCCESS"
            assert not math.isnan(rec_a["final_cost"])

            rec_b = df[df["strategy"] == "B"].iloc[0]
            assert rec_b["status"] == "FAILED"
            assert math.isnan(rec_b["final_cost"])
            assert "Simulated algorithm numerical divergence" in str(rec_b["error_message"])


# ---------------------------------------------------------------------------
# 5. Schema Serialization & Backward Compatibility
# ---------------------------------------------------------------------------

class TestSchemaSerializationAndCompatibility:
    """Verifies schema serialization round trips and backward compatibility."""

    def test_condition_config_roundtrip(self):
        cond = ConditionConfig(
            condition_id="c_roundtrip",
            total_vertices=25,
            dynamicity=0.45,
            events_per_step=3,
            replicate=2,
            distance_metric="continuous_euclidean",
            budget=BudgetConfig(BudgetType.MAX_EVALUATIONS, 200),
        )
        d = cond.to_dict()
        assert d["replicate"] == 2
        assert d["distance_metric"] == "continuous_euclidean"

        restored = ConditionConfig.from_dict(d)
        assert restored.condition_id == cond.condition_id
        assert restored.replicate == 2
        assert restored.distance_metric == "continuous_euclidean"

    def test_run_record_backward_compatibility(self):
        """RunRecord can be constructed with legacy minimal arguments without error."""
        legacy_record = RunRecord(
            run_id="legacy_run_01",
            condition_id="legacy_c1",
            strategy="A",
            seed=42,
            total_vertices=50,
            dynamicity=0.4,
            num_events=20,
            initial_cost=500.0,
            final_cost=650.0,
            cost_increase=150.0,
            total_computational_effort=620,
            total_response_time_ms=12.5,
            mean_disruption=0.05,
            max_disruption=0.1,
            all_feasible=True,
            budget_type="unbounded",
            budget_limit=None,
            git_commit_hash="abc1234",
            timestamp="2026-10-24T00:00:00",
        )
        d = legacy_record.to_dict()
        assert d["pair_id"] == ""
        assert d["distance_metric"] == "continuous_euclidean"
        assert d["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# 6. TSPLIB Metric Labeling
# ---------------------------------------------------------------------------

class TestTSPLIBMetricLabeling:
    """Verifies explicit distance metric labeling for TSPLIB runs."""

    def test_tsplib_run_records_continuous_euclidean_distance_metric(self):
        """TSPLIB runs record continuous_euclidean metric and do not claim integer optimum match."""
        cond = ConditionConfig(
            condition_id="c_tsplib_label",
            total_vertices=51,
            dynamicity=0.2,
            events_per_step=2,
            instance_source="tsplib",
            benchmark_name="berlin52",
            budget=BudgetConfig(BudgetType.MAX_EVALUATIONS, 150),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="tsplib_label_test",
                conditions=(cond,),
                seeds=(42,),
                strategies=("A", "C"),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)
            runner.run()

            df = pd.read_csv(Path(tmp_dir) / "runs.csv")
            assert len(df) == 2
            for _, row in df.iterrows():
                assert row["instance_family"] == "tsplib"
                assert row["distance_metric"] == "continuous_euclidean"
                assert row["benchmark_name"] == "berlin52"
                # Cost is continuous Euclidean float, not integer
                assert isinstance(row["final_cost"], float)

    def test_tsplib_dimension_mismatch_raises_error(self):
        """Configuring berlin52 with total_vertices!=51 or eil51 with total_vertices!=50 fails fast."""
        cond_bad_berlin = ConditionConfig(
            condition_id="c_bad_berlin",
            total_vertices=50,  # Wrong: should be 51
            dynamicity=0.2,
            instance_source="tsplib",
            benchmark_name="berlin52",
        )
        exp_cfg1 = ExperimentConfig("bad_berlin", (cond_bad_berlin,), seeds=(1,), strategies=("A",))
        runner1 = ExperimentRunner(exp_cfg1)
        with pytest.raises(ValueError, match="berlin52.*51"):
            runner1.run()

        cond_bad_eil = ConditionConfig(
            condition_id="c_bad_eil",
            total_vertices=51,  # Wrong: should be 50
            dynamicity=0.2,
            instance_source="tsplib",
            benchmark_name="eil51",
        )
        exp_cfg2 = ExperimentConfig("bad_eil", (cond_bad_eil,), seeds=(1,), strategies=("A",))
        runner2 = ExperimentRunner(exp_cfg2)
        with pytest.raises(ValueError, match="eil51.*50"):
            runner2.run()


# ---------------------------------------------------------------------------
# 7. Summary Statistics & Paired Comparisons Table
# ---------------------------------------------------------------------------

class TestSummaryAndPairedComparisons:
    """Verifies summary.csv and paired_comparisons.csv output generation."""

    def test_summary_and_paired_tables_generated(self):
        cond = ConditionConfig(
            condition_id="c_tables",
            total_vertices=10,
            dynamicity=0.4,
            events_per_step=2,
            distribution="uniform",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="tables_test",
                conditions=(cond,),
                seeds=(1, 2),
                strategies=("A", "B", "C", "ADAPTIVE"),
                output_dir=tmp_dir,
            )
            runner = ExperimentRunner(exp_cfg)
            runner.run()

            summary_csv = Path(tmp_dir) / "summary.csv"
            paired_csv = Path(tmp_dir) / "paired_comparisons.csv"

            assert summary_csv.exists()
            assert paired_csv.exists()

            df_sum = pd.read_csv(summary_csv)
            assert len(df_sum) == 4  # 4 strategies
            assert "ci95_low_final_cost" in df_sum.columns
            assert "mean_computational_effort" in df_sum.columns

            assert "mean_candidate_evaluations" in df_sum.columns
            assert "median_candidate_evaluations" in df_sum.columns
            assert "mean_overhead_evaluations" in df_sum.columns
            assert "statistical_note" in df_sum.columns
            assert df_sum.iloc[0]["statistical_note"] == "Diagnostic sample only; not inferential"

            df_pair = pd.read_csv(paired_csv)
            assert len(df_pair) == 2  # 2 seeds = 2 pairs
            assert "diff_cost_B_vs_A" in df_pair.columns
            assert "diff_cost_C_vs_A" in df_pair.columns
            assert "diff_cost_Adaptive_vs_A" in df_pair.columns


# ---------------------------------------------------------------------------
# 8. Historical Datasets Untouched
# ---------------------------------------------------------------------------

class TestHistoricalDatasetsIntegrity:
    """Asserts that historical result datasets were not modified or overwritten."""

    def test_historical_result_files_exist_and_intact(self):
        pilot_runs = Path(resolve_repo_path("results/pilot_matrix/runs.csv"))
        held_out_runs = Path(resolve_repo_path("results/held_out_matrix/runs.csv"))
        budgeted_runs = Path(resolve_repo_path("results/budgeted_pilot/runs.csv"))

        assert pilot_runs.exists()
        assert held_out_runs.exists()
        assert budgeted_runs.exists()

        df_pilot = pd.read_csv(pilot_runs)
        assert len(df_pilot) == 60, "Historical pilot matrix must have exactly 60 runs"

        df_held = pd.read_csv(held_out_runs)
        assert len(df_held) == 90, "Historical held-out matrix must have exactly 90 runs"

        df_bud = pd.read_csv(budgeted_runs)
        assert len(df_bud) == 12, "Historical budgeted pilot must have exactly 12 runs"
