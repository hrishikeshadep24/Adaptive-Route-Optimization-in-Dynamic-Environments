"""Unit tests for Pre-Phase 9 Research Audit Package.

Verifies:
- RawDataRecomputer calculations directly from raw files
- FairnessAuditor parity and non-leakage verification
- ReproducibilityAuditor manifest and artifact checks
- ResearchAuditor end-to-end reconciliation and verdict generation
"""

import os
import pytest
import pandas as pd

from adaptive_route_optimization.audit.inventory import (
    Claim,
    ClaimStatus,
    MetricType,
    CLAIMS_INVENTORY,
)
from adaptive_route_optimization.audit.recompute import RawDataRecomputer
from adaptive_route_optimization.audit.fairness import FairnessAuditor
from adaptive_route_optimization.audit.reproducibility import ReproducibilityAuditor
from adaptive_route_optimization.audit.runner import ResearchAuditor


class TestAuditRecomputer:
    """Test raw data recomputation logic."""

    def test_recomputer_loads_and_calculates(self):
        recomputer = RawDataRecomputer()
        metrics = recomputer.recompute_all()

        assert "P6_RUNS_TOTAL" in metrics
        assert metrics["P6_RUNS_TOTAL"] == 60
        assert metrics["P6_FAILED_RUNS"] == 0
        assert metrics["P6_CONDITIONS_COUNT"] == 10
        assert metrics["P6_SEEDS_COUNT"] == 3

        assert "P7_COST_A_MEAN" in metrics
        assert metrics["P7_COST_A_MEAN"] == pytest.approx(984.99, abs=0.05)
        assert metrics["P7_COST_B_MEAN"] == pytest.approx(960.08, abs=0.05)

        assert "P8_HELD_OUT_RUNS_TOTAL" in metrics
        assert metrics["P8_HELD_OUT_RUNS_TOTAL"] == 90
        assert metrics["P8_COST_ADAPTIVE_MEAN"] == pytest.approx(944.71, abs=0.05)


class TestAuditFairness:
    """Test fairness, parity, and non-leakage verification."""

    def test_rule10_parity_pilot(self):
        recomputer = RawDataRecomputer()
        res = FairnessAuditor.audit_rule10_parity(recomputer.pilot_runs, "Pilot")
        assert res.passed is True

    def test_rule10_parity_held_out(self):
        recomputer = RawDataRecomputer()
        res = FairnessAuditor.audit_rule10_parity(recomputer.held_out_runs, "Held-Out")
        assert res.passed is True

    def test_partition_disjointness(self):
        res = FairnessAuditor.audit_partition_disjointness()
        assert res.passed is True

    def test_feature_non_leakage(self):
        res = FairnessAuditor.audit_feature_non_leakage()
        assert res.passed is True

    def test_selection_overhead(self):
        recomputer = RawDataRecomputer()
        res = FairnessAuditor.audit_selection_overhead(recomputer.held_out_steps)
        assert res.passed is True


class TestAuditReproducibility:
    """Test reproducibility, manifests, and artifact checks."""

    def test_pilot_manifest(self):
        res = ReproducibilityAuditor.audit_manifest("results/pilot_matrix/manifest.json", expected_runs=60)
        assert res.passed is True

    def test_held_out_manifest(self):
        res = ReproducibilityAuditor.audit_manifest("results/held_out_matrix/manifest.json", expected_runs=90)
        assert res.passed is True

    def test_pilot_reproduction_agreement(self):
        res = ReproducibilityAuditor.audit_pilot_reproduction()
        assert res.passed is True

    def test_figures_traceability(self):
        res = ReproducibilityAuditor.audit_figures_traceability()
        assert res.passed is True

    def test_tables_traceability(self):
        res = ReproducibilityAuditor.audit_tables_traceability()
        assert res.passed is True


class TestResearchAuditorRunner:
    """Test full auditor runner execution and artifact export."""

    def test_audit_runner_verdict(self, tmp_path):
        auditor = ResearchAuditor(audit_dir=str(tmp_path))
        summary = auditor.run_audit()

        assert summary["overall_verdict"] == "PASS"
        assert summary["total_claims"] == len(CLAIMS_INVENTORY)
        assert summary["passed_claims"] == len(CLAIMS_INVENTORY)
        assert summary["failed_claims"] == 0
        assert summary["inconclusive_claims"] == 0
        assert summary["unverifiable_claims"] == 0
        assert summary["all_fairness_passed"] is True
        assert summary["all_reproducibility_passed"] is True

        # Check exported files
        assert os.path.exists(os.path.join(tmp_path, "metric_reconciliation.csv"))
        assert os.path.exists(os.path.join(tmp_path, "claim_inventory.csv"))
        assert os.path.exists(os.path.join(tmp_path, "data_integrity_report.json"))
        assert os.path.exists(os.path.join(tmp_path, "reproducibility_report.json"))
