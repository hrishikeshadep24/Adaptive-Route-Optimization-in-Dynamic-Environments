#!/usr/bin/env python3
"""Pre-Phase 9 Research Audit Script.

Independently recalculates all reported metrics and verifies:
- Provenance and reproducibility of raw experiment datasets
- Statistical battery and effect sizes (Phase 7)
- Quality-computation Pareto frontier and regime breakdowns
- Held-out adaptive selector performance and regret analysis (Phase 8)
- Zero data leakage, Rule 10 parity, and overhead accounting
- Artifact traceability of all 12 figures and 14 tables

Usage:
    python scripts/audit_research_results.py [--audit-dir results/audit]
"""

from __future__ import annotations
import argparse
import sys
import pandas as pd

from adaptive_route_optimization.audit.runner import ResearchAuditor


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and reconcile all research claims.")
    parser.add_argument(
        "--audit-dir",
        default="results/audit",
        help="Directory to save audit CSV and JSON reports (default: results/audit)",
    )
    args = parser.parse_args()

    print("======================================================================")
    print("      ADAPTIVE ROUTE OPTIMIZATION — PRE-PHASE 9 RESEARCH AUDIT        ")
    print("======================================================================")
    print(f"Audit output directory: {args.audit_dir}\n")

    auditor = ResearchAuditor(audit_dir=args.audit_dir)
    summary = auditor.run_audit()

    print("\n--- RECONCILIATION SUMMARY ---")
    print(f"Total Claims Inventoried:   {summary['total_claims']}")
    print(f"Passed Claims:              {summary['passed_claims']} ({(summary['passed_claims']/summary['total_claims'])*100:.1f}%)")
    print(f"Failed Claims:              {summary['failed_claims']}")
    print(f"Inconclusive Claims:        {summary['inconclusive_claims']}")
    print(f"Unverifiable Claims:        {summary['unverifiable_claims']}")

    print("\n--- INTEGRITY & REPRODUCIBILITY CHECKS ---")
    print(f"All Experimental Fairness Checks Passed: {summary['all_fairness_passed']}")
    print(f"All Reproducibility & Artifact Checks Passed: {summary['all_reproducibility_passed']}")

    print(f"\n======================================================================")
    print(f"                 OVERALL AUDIT VERDICT: {summary['overall_verdict']}")
    print(f"======================================================================\n")

    # Print any failed claims if present
    df_recon = pd.read_csv(summary["reconciliation_path"])
    failed_rows = df_recon[df_recon["status"] == "FAIL"]
    if not failed_rows.empty:
        print("FAILED CLAIMS:")
        for _, r in failed_rows.iterrows():
            print(f"  [{r['claim_id']}] Claimed: {r['claimed_value']}, Recomputed: {r['recomputed_value']}, Diff: {r['abs_difference']} (Tolerance: {r['tolerance']})")
        return 1

    print(f"Reconciliation table saved to: {summary['reconciliation_path']}")
    print(f"Claim inventory saved to:     {summary['inventory_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
