# Stage 5 Data Quality and Verification Audit Report

**Dataset Source:** `results/stage4_full_matrix/`  
**Execution Timestamp:** 2026-10-24T12:32:11.199955  
**Git Commit Hash:** `83bb1919b3e63db884165e105972a41a86342063`  
**Total Records Analyzed:** 280 runs, 5200 dynamic step transitions  

## 1. Audit Check Summary Table

| Verification Dimension | Status | Verified Findings |
| :--- | :---: | :--- |
| **Run Count & Completeness** | `PASS` | Planned: 280, Actual: 280, Completed: 280, Failed: 0 |
| **Unique Run Identifiers** | `PASS` | Total unique run_id values: 280 / 280 |
| **Missing / Null Value Audit** | `PASS` | Missing values in critical fields: 0 |
| **Scenario Fingerprint Consistency** | `PASS` | Pair groups with matched identical fingerprints: 70 / 70 |
| **Route Feasibility (Constraints Satisfied)** | `PASS` | Feasibility rate across all 280 runs: 100.0% |
| **Frozen Prefix Preservation Invariance** | `PASS` | Prefix invariance preservation rate: 100.0% |
| **Hard Budget Enforcement at Step Level** | `PASS` | Step evaluations exceeding configured max_evaluations: 0 |
| **Run-to-Step Aggregation Consistency** | `PASS` | Effort sum: True, Candidate sum: True, Overhead sum: True |

## 2. Integrity Analysis Findings

1. **Complete Balanced Design:** All 14 conditions feature full factorial coverage with 5 seeds (42, 101, 202, 303, 505) and 4 strategies (A, B, C, ADAPTIVE), resulting in exactly 280 runs with zero missing values or execution dropouts.
2. **Identical Scenario Pairing:** All 70 paired comparison blocks (`pair_id`) share an identical 16-character SHA-256 `scenario_fingerprint`, verifying that differences between algorithms stem strictly from algorithmic behavior rather than stochastic variation in customer coordinates or revelation ordering.
3. **Hard Constraint Compliance:** Zero route feasibility violations occurred (`all_feasible == True` on 100% of runs). The committed frozen prefix remained completely invariant across all 280 runs.
4. **Computational Accounting Truth:** Computational effort strictly reconciles at the step and run level: `total_computational_effort = candidate_evaluations + overhead_evaluations`. Strategies A, B, and C incur zero overhead evaluations, while Strategy Adaptive incurs exactly 1 overhead evaluation per dynamic update step.
5. **Quality Verdict:** **CLEAN AND CERTIFIED (100% VALIDATED)**. No data cleaning, imputation, or outlier filtering is necessary.
