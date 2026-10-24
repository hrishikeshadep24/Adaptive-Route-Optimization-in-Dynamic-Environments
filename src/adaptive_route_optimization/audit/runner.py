"""Master Audit Runner for Pre-Phase 9 Verification.

Orchestrates:
1. Claim inventory reconciliation against independently recalculated metrics.
2. Fairness and Rule 10 parity verification.
3. Reproducibility, manifest integrity, and artifact traceability.
4. Exporting structured audit artifacts to results/audit/.
"""

from __future__ import annotations
import json
import math
import os
from typing import Any
import pandas as pd

from adaptive_route_optimization.audit.inventory import (
    Claim,
    ClaimStatus,
    MetricType,
    CLAIMS_INVENTORY,
)
from adaptive_route_optimization.paths import resolve_repo_path
from adaptive_route_optimization.audit.recompute import RawDataRecomputer
from adaptive_route_optimization.audit.fairness import FairnessAuditor, FairnessCheckResult
from adaptive_route_optimization.audit.reproducibility import (
    ReproducibilityAuditor,
    ReproducibilityCheckResult,
)


class ResearchAuditor:
    """Executes the complete audit and reconciles all empirical claims."""

    def __init__(self, audit_dir: str = "results/audit") -> None:
        self.audit_dir = resolve_repo_path(audit_dir)
        self.recomputer = RawDataRecomputer()

    def run_audit(self) -> dict[str, Any]:
        """Execute full audit suite and return structured findings."""
        os.makedirs(self.audit_dir, exist_ok=True)

        # 1. Independent Recomputations
        recomputed_values = self.recomputer.recompute_all()

        # 2. Reconcile Claims
        reconciliation_records = []
        pass_count = 0
        fail_count = 0
        inconclusive_count = 0
        unverifiable_count = 0

        for claim in CLAIMS_INVENTORY:
            claim_id = claim.claim_id
            claimed_val = claim.claimed_value

            if claim_id not in recomputed_values:
                status = ClaimStatus.UNVERIFIABLE
                recomputed_val = None
                abs_diff = None
                rel_diff = None
                unverifiable_count += 1
            else:
                recomputed_val = recomputed_values[claim_id]

                if isinstance(claimed_val, (int, float)) and isinstance(recomputed_val, (int, float)):
                    abs_diff = float(abs(claimed_val - recomputed_val))
                    denom = abs(claimed_val) if claimed_val != 0 else 1.0
                    rel_diff = float(abs_diff / denom)

                    if claim.is_relative_tolerance:
                        passed = rel_diff <= claim.tolerance
                    else:
                        passed = abs_diff <= claim.tolerance

                    if passed:
                        status = ClaimStatus.PASS
                        pass_count += 1
                    else:
                        status = ClaimStatus.FAIL
                        fail_count += 1
                elif claimed_val == recomputed_val:
                    status = ClaimStatus.PASS
                    abs_diff = 0.0
                    rel_diff = 0.0
                    pass_count += 1
                else:
                    status = ClaimStatus.FAIL
                    abs_diff = None
                    rel_diff = None
                    fail_count += 1

            reconciliation_records.append({
                "claim_id": claim.claim_id,
                "phase": claim.phase,
                "source_doc": claim.source_doc,
                "section": claim.section,
                "metric_name": claim.metric_name,
                "claimed_value": claimed_val,
                "recomputed_value": round(recomputed_val, 6) if isinstance(recomputed_val, float) else recomputed_val,
                "abs_difference": round(abs_diff, 6) if abs_diff is not None else None,
                "rel_difference": round(rel_diff, 6) if rel_diff is not None else None,
                "tolerance": claim.tolerance,
                "status": status.value,
                "source_file": claim.source_file,
                "recomputation_method": claim.recomputation_method,
                "description": claim.description,
            })

        # Save Claim Inventory and Reconciliation
        df_recon = pd.DataFrame(reconciliation_records)
        recon_path = os.path.join(self.audit_dir, "metric_reconciliation.csv")
        df_recon.to_csv(recon_path, index=False)

        inv_path = os.path.join(self.audit_dir, "claim_inventory.csv")
        df_inv = pd.DataFrame([c.to_dict() for c in CLAIMS_INVENTORY])
        df_inv.to_csv(inv_path, index=False)

        # 3. Fairness and Integrity Checks
        fairness_checks: list[FairnessCheckResult] = [
            FairnessAuditor.audit_rule10_parity(self.recomputer.pilot_runs, "Pilot Matrix"),
            FairnessAuditor.audit_rule10_parity(self.recomputer.held_out_runs, "Held-Out Matrix"),
            FairnessAuditor.audit_partition_disjointness(),
            FairnessAuditor.audit_feature_non_leakage(),
            FairnessAuditor.audit_selection_overhead(self.recomputer.held_out_steps),
        ]
        all_fairness_passed = all(c.passed for c in fairness_checks)

        data_integrity_report = {
            "all_passed": all_fairness_passed,
            "checks": [c.to_dict() for c in fairness_checks],
        }
        with open(os.path.join(self.audit_dir, "data_integrity_report.json"), "w", encoding="utf-8") as f:
            json.dump(data_integrity_report, f, indent=2)

        # 4. Reproducibility and Artifact Checks
        repro_checks: list[ReproducibilityCheckResult] = [
            ReproducibilityAuditor.audit_manifest("results/pilot_matrix/manifest.json", expected_runs=60),
            ReproducibilityAuditor.audit_manifest("results/budgeted_pilot/manifest.json", expected_runs=12),
            ReproducibilityAuditor.audit_manifest("results/held_out_matrix/manifest.json", expected_runs=90),
            ReproducibilityAuditor.audit_pilot_reproduction(),
            ReproducibilityAuditor.audit_figures_traceability(),
            ReproducibilityAuditor.audit_tables_traceability(),
        ]
        all_repro_passed = all(c.passed for c in repro_checks)

        reproducibility_report = {
            "all_passed": all_repro_passed,
            "checks": [c.to_dict() for c in repro_checks],
        }
        with open(os.path.join(self.audit_dir, "reproducibility_report.json"), "w", encoding="utf-8") as f:
            json.dump(reproducibility_report, f, indent=2)

        # 5. Overall Audit Verdict
        total_claims = len(CLAIMS_INVENTORY)
        if fail_count == 0 and inconclusive_count == 0 and unverifiable_count == 0 and all_fairness_passed and all_repro_passed:
            overall_verdict = "PASS"
        elif fail_count > 0:
            overall_verdict = "FAIL"
        elif inconclusive_count > 0:
            overall_verdict = "INCONCLUSIVE"
        else:
            overall_verdict = "UNVERIFIABLE"

        return {
            "overall_verdict": overall_verdict,
            "total_claims": total_claims,
            "passed_claims": pass_count,
            "failed_claims": fail_count,
            "inconclusive_claims": inconclusive_count,
            "unverifiable_claims": unverifiable_count,
            "all_fairness_passed": all_fairness_passed,
            "all_reproducibility_passed": all_repro_passed,
            "reconciliation_path": recon_path,
            "inventory_path": inv_path,
        }
