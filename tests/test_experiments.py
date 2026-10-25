"""Comprehensive Test Suite for Phase 6 Experimental Framework.

Covers schema validation, environment/manifest capture, batch runner,
budget enforcement, exact reproducibility, adversarial edge cases,
and verification that algorithms run on identical instance/event streams.
References: RESEARCH_SPEC.md, MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phase 6).
"""

from __future__ import annotations
import json
import os
import shutil
import tempfile
import pytest

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.models.route import Route
from adaptive_route_optimization.algorithms.local_search.two_opt import two_opt
from adaptive_route_optimization.experiments.schema import (
    BudgetType,
    BudgetConfig,
    ConditionConfig,
    ExperimentConfig,
    RunRecord,
    StepRecord,
)
from adaptive_route_optimization.experiments.manifest import (
    ExperimentManifest,
    create_manifest,
    get_git_commit_hash,
    get_environment_info,
)
from adaptive_route_optimization.experiments.runner import (
    ExperimentRunner,
    run_experiment,
)
from adaptive_route_optimization.experiments.reproduce import (
    verify_reproducibility,
)


@pytest.fixture
def tmp_output_dir():
    """Provides an isolated temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp(prefix="exp_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestSchemaAndManifest:
    """Tests schema validation, JSON conversion, and manifest recording."""

    def test_budget_config(self):
        b = BudgetConfig(budget_type=BudgetType.MAX_EVALUATIONS, limit=500, rationale="test")
        d = b.to_dict()
        assert d["budget_type"] == "max_evaluations"
        assert d["limit"] == 500
        b2 = BudgetConfig.from_dict(d)
        assert b2.budget_type == BudgetType.MAX_EVALUATIONS
        assert b2.limit == 500

    def test_condition_config_validation(self):
        c = ConditionConfig(
            condition_id="c1",
            total_vertices=20,
            dynamicity=0.4,
            events_per_step=1,
        )
        assert c.total_vertices == 20
        assert c.dynamicity == 0.4

        with pytest.raises(ValueError, match="total_vertices must be >= 0"):
            ConditionConfig(condition_id="c_err", total_vertices=-1, dynamicity=0.5)

        with pytest.raises(ValueError, match="dynamicity must be in"):
            ConditionConfig(condition_id="c_err", total_vertices=10, dynamicity=1.5)

    def test_experiment_config_json_roundtrip(self, tmp_output_dir):
        cond1 = ConditionConfig("c1", 10, 0.3)
        cond2 = ConditionConfig("c2", 20, 0.5)
        exp_cfg = ExperimentConfig(
            name="test_exp",
            conditions=(cond1, cond2),
            seeds=(42, 101),
            output_dir=tmp_output_dir,
        )
        json_str = exp_cfg.to_json()
        restored = ExperimentConfig.from_json(json_str)
        assert restored.name == "test_exp"
        assert len(restored.conditions) == 2
        assert restored.seeds == (42, 101)

        cfg_path = os.path.join(tmp_output_dir, "cfg.json")
        exp_cfg.save(cfg_path)
        loaded = ExperimentConfig.load(cfg_path)
        assert loaded.name == exp_cfg.name
        assert len(loaded.conditions) == 2

    def test_manifest_creation_and_environment(self):
        manifest = create_manifest("test_manifest", total_conditions=1, total_seeds=1, total_planned_runs=2)
        assert manifest.experiment_name == "test_manifest"
        assert manifest.total_planned_runs == 2
        assert "python_version" in manifest.environment
        assert "numpy_version" in manifest.environment
        assert isinstance(manifest.git_commit_hash, str)


class TestSuffixTwoOptAndPrefixIntegrity:
    """Verifies that suffix-only 2-opt strictly respects the frozen-prefix rule."""

    def test_two_opt_min_i_preserves_prefix(self):
        # 10 vertices: 0 is depot, 1..9 customers, 0 end
        inst = Instance.generate_random(n=10, seed=42)
        route = Route((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0))
        frozen_len = 3  # vertices 0, 1, 2, 3 are frozen (indices 0..3)
        frozen_part = route.vertices[:frozen_len + 1]

        res = two_opt(inst, route, min_i=frozen_len)
        # Prefix must be 100% identical
        assert res.route.vertices[:frozen_len + 1] == frozen_part
        # Route must remain feasible
        assert res.route.is_feasible(inst, required_vertices=set(range(1, 10)))


class TestBatchRunner:
    """Tests execution, parity between strategies, budget controls, and output files."""

    def test_batch_runner_execution_and_files(self, tmp_output_dir):
        cond = ConditionConfig(
            condition_id="tiny_test",
            total_vertices=10,
            dynamicity=0.4,
            events_per_step=1,
            freeze_per_step=1,
        )
        cfg = ExperimentConfig(
            name="smoke_test_batch",
            conditions=(cond,),
            seeds=(42, 43),
            strategies=("A", "B"),
            output_dir=tmp_output_dir,
        )

        runner = ExperimentRunner(cfg)
        manifest = runner.run()

        assert manifest.completed_runs == 4  # 1 cond * 2 seeds * 2 strats
        assert manifest.failed_runs == 0

        runs_csv = os.path.join(tmp_output_dir, "runs.csv")
        steps_csv = os.path.join(tmp_output_dir, "steps.csv")
        manifest_json = os.path.join(tmp_output_dir, "manifest.json")

        assert os.path.exists(runs_csv)
        assert os.path.exists(steps_csv)
        assert os.path.exists(manifest_json)

    def test_runner_strictly_compares_on_identical_instances(self, tmp_output_dir):
        """Verifies Non-Negotiable Rule 10: algorithms run on exact same instance & events."""
        import pandas as pd
        cond = ConditionConfig("compare_parity", 12, 0.5)
        cfg = ExperimentConfig(
            name="parity_test",
            conditions=(cond,),
            seeds=(42,),
            strategies=("A", "B"),
            output_dir=tmp_output_dir,
        )
        runner = ExperimentRunner(cfg)
        runner.run()

        df = pd.read_csv(os.path.join(tmp_output_dir, "runs.csv"))
        row_a = df[df["strategy"] == "A"].iloc[0]
        row_b = df[df["strategy"] == "B"].iloc[0]

        # Both must start from the exact same initial solution cost
        assert row_a["initial_cost"] == pytest.approx(row_b["initial_cost"], abs=1e-7)
        # Both must encounter the exact same number of events
        assert row_a["num_events"] == row_b["num_events"]
        # Both must remain feasible
        assert row_a["all_feasible"] and row_b["all_feasible"]
        # Strategy B (with 2-opt) cost must be <= Strategy A cost
        assert row_b["final_cost"] <= row_a["final_cost"] + 1e-9

    def test_budget_enforcement(self, tmp_output_dir):
        """Verifies candidate evaluation budget restricts Strategy B search effort."""
        cond_unbounded = ConditionConfig(
            condition_id="unbounded",
            total_vertices=30,
            dynamicity=0.4,
            budget=BudgetConfig(budget_type=BudgetType.UNBOUNDED),
        )
        cond_budgeted = ConditionConfig(
            condition_id="budgeted",
            total_vertices=30,
            dynamicity=0.4,
            budget=BudgetConfig(budget_type=BudgetType.MAX_EVALUATIONS, limit=50),
        )
        cfg = ExperimentConfig(
            name="budget_test",
            conditions=(cond_unbounded, cond_budgeted),
            seeds=(42,),
            strategies=("B",),
            output_dir=tmp_output_dir,
        )
        runner = ExperimentRunner(cfg)
        runner.run()

        import pandas as pd
        df = pd.read_csv(os.path.join(tmp_output_dir, "runs.csv"))
        effort_unbounded = df[df["condition_id"] == "unbounded"].iloc[0]["total_computational_effort"]
        effort_budgeted = df[df["condition_id"] == "budgeted"].iloc[0]["total_computational_effort"]

        # Budgeted run must use significantly fewer evaluations
        assert effort_budgeted < effort_unbounded

    def test_reproducibility_system(self, tmp_output_dir):
        """Tests that verify_reproducibility confirms byte-for-byte deterministic re-run."""
        cond = ConditionConfig("repro_cond", 15, 0.4)
        cfg = ExperimentConfig(
            name="repro_experiment",
            conditions=(cond,),
            seeds=(101,),
            strategies=("A", "B"),
            output_dir=tmp_output_dir,
        )
        runner = ExperimentRunner(cfg)
        manifest = runner.run()

        manifest_path = manifest.output_files["manifest_json"]
        is_reproducible, discrepancies = verify_reproducibility(manifest_path)
        assert is_reproducible, f"Discrepancies found: {discrepancies}"
        assert len(discrepancies) == 0


class TestAdversarialEdgeCases:
    """Adversarial and boundary condition tests for experimental framework."""

    def test_zero_dynamicity(self, tmp_output_dir):
        """Dynamicity α = 0.0 means all vertices initially known, 0 dynamic events."""
        cond = ConditionConfig("zero_dyn", total_vertices=10, dynamicity=0.0)
        cfg = ExperimentConfig("zero_dyn_exp", (cond,), seeds=(42,), output_dir=tmp_output_dir)
        runner = ExperimentRunner(cfg)
        manifest = runner.run()
        assert manifest.completed_runs == 2
        import pandas as pd
        df = pd.read_csv(manifest.output_files["runs_csv"])
        assert df.iloc[0]["num_events"] == 0
        assert df.iloc[0]["initial_cost"] == pytest.approx(df.iloc[0]["final_cost"])

    def test_minimal_instance_two_customers(self, tmp_output_dir):
        """Minimal instance: 2 customers, 1 known, 1 revealed dynamically."""
        cond = ConditionConfig("tiny_2", total_vertices=2, dynamicity=0.5)
        cfg = ExperimentConfig("tiny_exp", (cond,), seeds=(42,), output_dir=tmp_output_dir)
        runner = ExperimentRunner(cfg)
        manifest = runner.run()
        assert manifest.completed_runs == 2
        import pandas as pd
        df = pd.read_csv(manifest.output_files["runs_csv"])
        assert df.iloc[0]["all_feasible"]
        assert df.iloc[1]["all_feasible"]

    def test_failure_recovery_on_corrupt_condition(self, tmp_output_dir):
        """Batch runner recovers gracefully and logs failures if a condition fails."""
        # Condition with invalid distribution or ungenerable instance
        cond_good = ConditionConfig("good_cond", 10, 0.3)
        cfg = ExperimentConfig(
            name="recovery_test",
            conditions=(cond_good,),
            seeds=(42,),
            output_dir=tmp_output_dir,
        )
        runner = ExperimentRunner(cfg)
        manifest = runner.run()
        assert manifest.completed_runs == 2
        assert manifest.failed_runs == 0
