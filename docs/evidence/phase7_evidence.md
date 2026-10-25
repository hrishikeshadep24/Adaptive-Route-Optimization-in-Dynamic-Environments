# Phase 7 Evidence: Research Analysis & Ablation

## Gate Criterion (from PHASE_PLAN.md)
> **Gate**: >=3 evidence-backed findings AND >=1 limitation or non-significant result.

---

## 1. Gate Verification: Analysis Pipeline Execution

### Command
```bash
python -m adaptive_route_optimization.analysis.cli --runs results/pilot_matrix/runs.csv --steps results/pilot_matrix/steps.csv --manifest results/pilot_matrix/manifest.json --budget-runs results/budgeted_pilot/runs.csv --tables-dir results/tables --figures-dir results/figures
```

### Actual Output
```
=== PHASE 7 ANALYSIS PIPELINE COMPLETED SUCCESSFULLY ===
Validated Runs: 60
Paired Comparisons: 30
Output Tables Saved to: results/tables
Output Figures Saved to: results/figures
```

---

## 2. Gate Verification: Test Suite Results

### Command
```bash
pytest -q
```

### Actual Output
```
........................................................................ [ 38%]
........................................................................ [ 76%]
............................................                             [100%]
186 passed in 12.18s
```
**Total tests passed**: **186 passed** (161 from Phases 1–5 + 12 from Phase 6 + 13 from Phase 7).

---

## 3. Evidence-Backed Findings Summary (Gate Criterion)

| # | Type | Finding | Quantified Evidence | Sources |
|---|---|---|---|---|
| **1** | **Evidence-backed finding** | **Decisive superiority of Strategy B at low dynamicity (α ≤ 0.2)** | **100% win rate** (12/12 paired runs), mean cost improvement of **+10.86%** ($\text{median} = +10.87\%$). | `results/tables/ablation_by_regime.csv` (Row 3); `results/figures/fig1_dynamicity_vs_cost.png`, `fig6_paired_comparison.png`. |
| **2** | **Evidence-backed finding** | **Super-linear computational effort scaling of 2-opt** | Strategy B requires **$49.1\times$ to $75.1\times$** more candidate evaluations ($p = 1.86 \times 10^{-9}$), causing a **$110.8\times$** increase in update response time. | `results/tables/statistical_battery.csv` (Rows 3–4); `results/figures/fig4_size_vs_runtime.png`, `fig8_quality_vs_computation_tradeoff.png`. |
| **3** | **Evidence-backed finding** | **Route disruption doubling under 2-opt** | Strategy A disruption is minimal ($\text{mean } \delta = 0.0367$), while Strategy B causes more than double the structural edge turnover ($\text{mean } \delta = 0.0794$, $p = 1.86 \times 10^{-9}$, Cohen's $d_z = -0.93$). | `results/tables/statistical_battery.csv` (Row 5); `results/figures/fig7_route_disruption.png`. |
| **4** | **Evidence-backed finding** | **Budget cap Pareto-efficiency** | Capping Strategy B to 500 candidate evaluations captures **96.3%** of unbounded 2-opt's cost improvement while reducing evaluations by **32.3%**. | `results/tables/budget_ablation.csv`; `results/figures/fig9_budget_ablation.png`. |
| **5** | **Limitation / Non-significant result** | **Overall route cost difference across all dynamic conditions is NOT statistically significant** | Paired t-test: $t = 1.32, p = 0.1975$; Wilcoxon: $W = 163.0, p = 0.1579$. The 95% bootstrap confidence interval $[-11.49, +59.15]$ spans zero. | `results/tables/statistical_battery.csv` (Row 2); `docs/RESEARCH_FINDINGS.md`. |
| **6** | **Limitation / Negative finding** | **Myopic local search failure at high dynamicity (α ≥ 0.6)** | Strategy B was **inferior in 66.7% of cases** (6/9 runs), yielding an average cost penalty of **-5.01%** (worst case: 22.18% longer tour than Strategy A). | `results/tables/ablation_by_regime.csv` (Row 2); `results/figures/fig5_evals_vs_cost_improvement.png`. |

**Gate Status**: ✅ **SATISFIED** (4 evidence-backed findings and 2 limitations/non-significant results documented with exact numerical citations).

---

## 4. Deliverables Implemented

| Deliverable | File / Path | Status |
|---|---|---|
| Dataset Validation Module | `src/adaptive_route_optimization/analysis/validator.py` | ✅ Complete |
| Metrics Aggregation Module | `src/adaptive_route_optimization/analysis/metrics.py` | ✅ Complete |
| Statistical Battery Module | `src/adaptive_route_optimization/analysis/statistical.py` | ✅ Complete |
| Component & Budget Ablation | `src/adaptive_route_optimization/analysis/ablation.py` | ✅ Complete |
| Visualizer Module (9 Figures) | `src/adaptive_route_optimization/analysis/visualizer.py` | ✅ Complete |
| End-to-End Analysis Pipeline | `src/adaptive_route_optimization/analysis/pipeline.py` | ✅ Complete |
| Analysis CLI Tool | `src/adaptive_route_optimization/analysis/cli.py` | ✅ Complete |
| Research Findings Report | `docs/RESEARCH_FINDINGS.md` | ✅ Complete |
| Unit & Integration Tests | `tests/test_analysis.py` (13 tests) | ✅ 13/13 Passed |
| Generated Tables (CSV/JSON) | `results/tables/` (10 files) | ✅ Complete |
| Generated Figures (PNG) | `results/figures/` (9 files) | ✅ Complete |

---

## 5. Non-Negotiable Rules Adherence

1. **Non-Negotiable Rule 10**: Confirmed by `validate_experiment_data()` — both Strategy A and B share identical instance coordinates and dynamic event sequences on every seed.
2. **Non-Negotiable Rule 5**: No fabricated benchmark numbers, confidence intervals, or p-values. All values are computed directly from `results/pilot_matrix/runs.csv`.
3. **Non-Negotiable Rule 2**: No future phase code (Phase 8 adaptive selector or Phase 9 UI) was written.
