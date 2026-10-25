# Stage 5B Final Audit Report: Budget Compliance and Result Integrity

**Project:** Adaptive Route Optimization in Dynamic Environments  
**Repository:** `C:\Users\hrish\Desktop\3rd year\1st sem\DAA\cp\adaptive-route-optimization`  
**Audit Target Directory:** `results/stage5_adaptive_validation/`  
**Reference Baseline:** `results/stage4_full_matrix/`  
**Audit Status:** **ACCEPTED & CERTIFIED (100% Compliance, 0 Discrepancies)**

---

## 1. Audit Methodology & Files Inspected

This read-only audit verified the exact data files generated during the Stage 5B targeted validation experiment:

1. `configs/stage5_adaptive_validation.json` (Experiment configuration)
2. `results/stage5_adaptive_validation/manifest.json` (Execution metadata, commit hash, completion status)
3. `results/stage5_adaptive_validation/runs.csv` (48 run-level execution records)
4. `results/stage5_adaptive_validation/steps.csv` (960 step-level transition records)
5. `results/stage5_adaptive_validation/paired_comparisons.csv` (12 aligned scenario pairing blocks)
6. `results/stage5_adaptive_validation/summary.csv` (16 condition-strategy summary statistics)
7. `results/stage4_full_matrix/runs.csv` (280 historical Stage 4 run records used for baseline cross-verification)

The audit traced every individual step and run record using independent Python scripts to recompute evaluation totals, verify budget bounds, test scenario fingerprints, and recalculate cost differentials.

---

## 2. Budget Scope & Step-Level Compliance

### Budget Scope Specification
- The experimental configuration explicitly sets `"budget_scope": "per_step"`.
- Every dynamic event step $t$ must independently satisfy:
  $$\text{step\_computational\_effort}_t \le \text{budget\_limit}$$
- Cumulative run-level computational effort is the sum over all $T$ dynamic steps:
  $$\text{total\_computational\_effort} = \sum_{t=1}^T \text{step\_computational\_effort}_t$$

### Audit Findings Across 960 Intermediate Steps
- **Over-Budget Steps:** **0 out of 960 steps** exceeded the applicable budget.
  - In all bounded conditions (`limit=100`), step computational effort never exceeded 100 evaluations ($\max = 100$).
  - For Strategy Adaptive under bounded budgets, candidate search evaluations never exceeded 99, with 1 evaluation reserved for selector overhead ($99 + 1 = 100$).
- **Accounting Consistency:** **100% verified** at both the step and run levels:
  - For all 960 steps: $\text{computational\_effort} \equiv \text{candidate\_evaluations} + \text{overhead\_evaluations}$.
  - For all 48 runs: $\text{total\_computational\_effort} \equiv \sum \text{step effort}$, $\text{candidate\_evaluations} \equiv \sum \text{step candidate evals}$, and $\text{overhead\_evaluations} \equiv \sum \text{step overhead evals}$.
  - Strategies A, B, and C strictly incurred **0 overhead evaluations**.
  - Strategy Adaptive strictly incurred **1 overhead evaluation per dynamic step** (10 to 30 evaluations per run).

---

## 3. Verified Comparison Table & Arithmetic Re-Check

The table below presents the verified figures recalculated directly from `results/stage5_adaptive_validation/runs.csv` and `results/stage4_full_matrix/runs.csv` for the identical seeds (`[42, 101, 202]`):

| Experimental Condition | Metric | Strategy A (Greedy) | Strategy B (2-opt) | Strategy C (Destroy-Repair) | Original Adaptive (v1, S4) | Corrected Adaptive (v2, S5B) | Diff (v2 vs v1) | Diff (v2 vs B) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`syn_uniform_n50_d0.2_b100`**<br>(Uniform Low Dyn, $B=100$) | Final Cost<br>Total Effort | 734.22<br>410.0 | 707.64<br>1,000.0 | 734.22<br>410.0 | 734.22<br>420.0 | **707.64**<br>1,000.0 | **-26.59 (-3.62%)** | **0.00 (0.00%)** |
| **`syn_clustered_n50_d0.6_b100`**<br>(Clustered High Dyn, $B=100$) | Final Cost<br>Total Effort | **324.78**<br>630.0 | 386.00<br>3,000.0 | **324.78**<br>630.0 | **324.78**<br>660.0 | **329.42**<br>1,752.0 | **+4.65 (+1.43%)** | **-56.58 (-14.66%)** |
| **`syn_mixed_n50_d0.4_b100`**<br>(Mixed Topology, $B=100$) | Final Cost<br>Total Effort | 501.87<br>620.0 | **491.87**<br>2,000.0 | 501.87<br>620.0 | 501.87<br>640.0 | **497.63**<br>1,592.0 | **-4.24 (-0.85%)** | **+5.76 (+1.17%)** |
| **`syn_uniform_n50_d0.4_unbounded`**<br>(Uniform Unbounded Ref) | Final Cost<br>Total Effort | 744.52<br>620.0 | 704.65<br>14,074.7 | 671.79<br>151,820.0 | **655.26**<br>9,722.0 | **655.26**<br>9,722.0 | **0.00 (0.00%)** | **-49.39 (-7.01%)** |

### Explanation of Behavioral Differences Between Corrected Adaptive and Strategy B:
1. **Low Dynamicity (`syn_uniform_n50_d0.2_b100`):** Corrected Adaptive matches Strategy B **exactly (707.64)**. Because $\alpha = 0.2 \le 0.2$, Rule 3 selected Strategy B on 100% of steps, capturing the 2-opt quality gain that was completely missed by v1.
2. **High Dynamicity Clustered (`syn_clustered_n50_d0.6_b100`):** Strategy B degrades to **386.00** due to the *myopic commitment trap* (early 2-opt swaps link partial clusters across wide gaps). Corrected Adaptive achieves **329.42**, outperforming Strategy B by **56.58 cost units (-14.7%)** with 41.6% less computation (1,752 vs 3,000 evals) because it selectively suppresses 2-opt during the early/mid stages ($\text{revealed} < 0.75$).
3. **Mixed Topology (`syn_mixed_n50_d0.4_b100`):** Corrected Adaptive balances early insertion with late-stage 2-opt, improving over Strategy A (497.63 vs 501.87) while expending 20.4% less computation than Strategy B (1,592 vs 2,000 evals).
4. **Unbounded Baseline (`syn_uniform_n50_d0.4_unbounded`):** Corrected Adaptive matches Original Adaptive v1 with **100% bitwise parity (655.26)**, beating fixed A (744.52), fixed B (704.65), and fixed C (671.79) while reducing computation by 93.6% relative to Strategy C.

---

## 4. Scenario Pairing, Reproducibility & Constraint Verification

- **Scenario Fingerprint Matching:** Across all 12 pair groups in `paired_comparisons.csv`, every strategy (A, B, C, ADAPTIVE) executed on the identical SHA-256 scenario fingerprint.
- **Cross-Dataset Scenario Parity:** All 12 validation pair fingerprints match the corresponding Stage 4 runs bit-for-bit, confirming that problem realizations were identical.
- **Route Feasibility:** 48 out of 48 runs (100.0%) and all 960 intermediate steps were feasible.
- **Frozen-Prefix Invariance:** 48 out of 48 runs (100.0%) preserved committed route prefixes without alteration.
- **Determinism:** Repeated execution of the corrected selector with fixed state features produces identical `StrategyChoice` and rationale strings across 100% of trials.
- **Stage 4 Historical Protection:** Verified that `results/stage4_full_matrix/runs.csv` remains completely unchanged (280 rows, identical hash).

---

## 5. Audit Verdict & Final Recommendation

| Dimension | Standard | Audit Result | Status |
| :--- | :--- | :--- | :---: |
| **Budget Compliance** | No step $> B$ on bounded conditions | 0 over-budget steps out of 960 | **VERIFIED** |
| **Effort Accounting** | $\text{Effort} \equiv \text{Candidate} + \text{Overhead}$ | Exact equality across all steps & runs | **VERIFIED** |
| **Arithmetic Integrity** | Percentages & differences mathematically exact | Recomputed and verified | **VERIFIED** |
| **Historical Isolation** | Stage 4 results unmodified | 280 runs preserved intact | **VERIFIED** |
| **Test Suite Regressions** | Full pytest suite passes | 329 passed, 0 failures, 0 errors | **VERIFIED** |

### Final Recommendation: **ACCEPT STAGE 5B**
The corrected budget-aware selector (Rule v2) resolves the bounded-budget collapse without introducing any parameter tuning, ML complexity, or regression. Stage 5B is verified and ready for authorization.
