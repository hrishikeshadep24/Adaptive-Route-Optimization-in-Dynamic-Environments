# Stage 6 Sign-Off Audit & Project Acceptance Report

**Project**: Adaptive Route Optimization in Dynamic Environments  
**Repository**: `C:\Users\hrish\Desktop\3rd year\1st sem\DAA\cp\adaptive-route-optimization`  
**Audit Date**: October 24, 2026  
**Final Status**: **ACCEPTED & COMPLETE (Stage 6 Final Software Sign-Off)**

---

## 1. Executive Summary & Audit Verdict

This document presents the final **Stage 6 Sign-Off Audit** for the project **Adaptive Route Optimization in Dynamic Environments**. All planned software implementation, algorithmic integrations, experiment pipelines, empirical analyses, and interactive user interfaces are complete.

### Audit Summary
- **Exact Data Reconciliation**: Completed. All runs, conditions, strategies, versions, seeds, and scenarios in `results/stage4_full_matrix/` (280 runs) and `results/stage5_adaptive_validation/` (48 runs) match configuration manifests with zero missing records or orphaned files.
- **Audit Scope Clarification**: Fully disambiguated. Clarifies the difference between the 40-claim Pre-Phase 9 Research Audit (198 historical runs) and the Stage 4/5B Campaign Verification (328 campaign runs, 6,160 dynamic steps).
- **Test Suite**: **336 passed in 39.41s** (100% success rate across all unit and integration tests).
- **Research Audit**: **40 / 40 claims PASS (100.0%)**, 0 failures, 0 inconclusive.
- **Dashboard Launch**: Confirmed. Streamlit server launched via `python scripts/run_dashboard.py --port 8501` on `http://localhost:8501` and returned **HTTP 200 OK**. Programmatic `AppTest` passed all 4 views with zero unhandled exceptions.
- **Git Working Tree**: Fully reviewed and cataloged (26 modified files, 16 untracked files; zero uncommitted user work lost or discarded).
- **README & CLI Verification**: Verified. All commands match current project layout.

---

## 2. Exact Dataset Reconciliation: Stage 4 & Stage 5B

An automated first-principles reconciliation was performed directly on `results/stage4_full_matrix/runs.csv` and `results/stage5_adaptive_validation/runs.csv`.

### 2.1 Stage 4 Full Matrix (`results/stage4_full_matrix/`)
- **Total Run Records**: **280** (280 unique `run_id`s, 0 duplicate or failed runs).
- **Experimental Conditions**: **14 conditions** (20 runs each):
  1. `syn_uniform_n50_d0.2_b100` (Uniform, $n=50$, $\alpha=0.2$, $B=100$)
  2. `syn_uniform_n50_d0.4_b100` (Uniform, $n=50$, $\alpha=0.4$, $B=100$)
  3. `syn_uniform_n50_d0.6_b100` (Uniform, $n=50$, $\alpha=0.6$, $B=100$)
  4. `syn_uniform_n50_d0.4_b50` (Uniform, $n=50$, $\alpha=0.4$, $B=50$)
  5. `syn_uniform_n50_d0.4_unbounded` (Uniform, $n=50$, $\alpha=0.4$, $B=\infty$)
  6. `syn_clustered_n50_d0.2_b100` (Clustered, $n=50$, $\alpha=0.2$, $B=100$)
  7. `syn_clustered_n50_d0.4_b100` (Clustered, $n=50$, $\alpha=0.4$, $B=100$)
  8. `syn_clustered_n50_d0.6_b100` (Clustered, $n=50$, $\alpha=0.6$, $B=100$)
  9. `syn_clustered_n50_d0.4_b50` (Clustered, $n=50$, $\alpha=0.4$, $B=50$)
  10. `syn_mixed_n50_d0.4_b100` (Mixed, $n=50$, $\alpha=0.4$, $B=100$)
  11. `tsplib_berlin52_d0.2_b100` (TSPLIB `berlin52`, $n=51$, $\alpha=0.2$, $B=100$)
  12. `tsplib_berlin52_d0.4_b100` (TSPLIB `berlin52`, $n=51$, $\alpha=0.4$, $B=100$)
  13. `tsplib_eil51_d0.2_b100` (TSPLIB `eil51`, $n=50$, $\alpha=0.2$, $B=100$)
  14. `tsplib_eil51_d0.4_b100` (TSPLIB `eil51`, $n=50$, $\alpha=0.4$, $B=100$)
- **Seeds Evaluated**: **5 seeds** (`[42, 101, 202, 303, 505]`).
- **Strategies Evaluated**: **4 strategies** (70 runs each):
  - Strategy A (Cheapest Insertion): 70 runs
  - Strategy B (Insertion + 2-opt): 70 runs
  - Strategy C (Destroy-Repair / LNS): 70 runs
  - ADAPTIVE (Selector v1): 70 runs
- **Algorithm Version**: `stage4_v1.0` (all 280 runs).
- **Matched Pair Identifiers**: **70 unique `pair_id`s** (each pair groups the 4 strategies on identical scenario realizations).
- **Scenario Fingerprints**: **55 unique `scenario_fingerprint`s**.
  - *Fingerprint Derivation Note*: There are 70 pairs across 14 conditions and 5 seeds. However, the budget ablation conditions (`syn_uniform_n50_d0.4_b100`, `b50`, `unbounded` [15 pairs $\to$ 5 distinct scenarios]) and (`syn_clustered_n50_d0.4_b100`, `b50` [10 pairs $\to$ 5 distinct scenarios]) share identical customer topologies and arrival sequences, varying solely by budget limit. Thus, $70 - 10 - 5 = 55$ unique scenario instances were evaluated.

### 2.2 Stage 5B Targeted Adaptive Validation (`results/stage5_adaptive_validation/`)
- **Total Run Records**: **48** (48 unique `run_id`s, 0 duplicate or failed runs).
- **Experimental Conditions**: **4 conditions** (12 runs each):
  1. `syn_uniform_n50_d0.2_b100` (Low dynamicity uniform, $B=100$)
  2. `syn_clustered_n50_d0.6_b100` (High dynamicity clustered, $B=100$)
  3. `syn_mixed_n50_d0.4_b100` (Medium dynamicity mixed, $B=100$)
  4. `syn_uniform_n50_d0.4_unbounded` (Medium dynamicity uniform, unbounded)
- **Seeds Evaluated**: **3 seeds** (`[42, 101, 202]`).
- **Strategies Evaluated**: **4 strategies** (12 runs each):
  - Strategy A: 12 runs
  - Strategy B: 12 runs
  - Strategy C: 12 runs
  - ADAPTIVE (Corrected Rule v2 selector): 12 runs
- **Algorithm Version**: `stage4_v1.0` (with Rule v2 budget-aware selection logic active).
- **Matched Pair Identifiers**: **12 unique `pair_id`s**.
- **Scenario Fingerprints**: **12 unique `scenario_fingerprint`s**.
  - All 12 scenario fingerprints exactly match the corresponding condition-seed fingerprints from Stage 4, guaranteeing strict pairwise comparability.

---

## 3. Disambiguation of Audited Runs

To prevent confusion between distinct verification scopes, the datasets and run counts are formally separated:

### 3.1 Historical Pre-Phase 9 Research Audit (`scripts/audit_research_results.py`)
This tool executes an automated reconciliation of **40 specific empirical claims** established during earlier research phases:
- **`results/pilot_matrix/`**: 60 runs (10 conditions $\times$ 3 seeds $\times$ 2 strategies A & B)
- **`results/budgeted_pilot/`**: 48 runs (4 conditions $\times$ 3 seeds $\times$ 4 budget caps for Strategy B)
- **`results/held_out_matrix/`**: 90 runs (10 conditions $\times$ 3 held-out seeds $\times$ 3 strategies A, B, ADAPTIVE)
- **Total Historical Runs**: **198 runs**
- **Claims Verified**: 40 / 40 (100% pass rate).

### 3.2 Stage 4 & Stage 5B Campaign Verification
This verification audits the newly generated dynamic benchmark matrices:
- **`results/stage4_full_matrix/`**: 280 runs (5,200 dynamic arrival steps)
- **`results/stage5_adaptive_validation/`**: 48 runs (960 dynamic arrival steps)
- **Total Campaign Runs**: **328 runs** (6,160 total dynamic steps; 5,520 steps under explicit evaluation budgets)
- **Verified Invariants**:
  - **Budget Compliance**: **0 over-budget steps** (every step satisfied $\text{candidate\_evaluations} \le \text{budget\_limit}$ and $\text{computational\_effort} \le \text{budget\_limit}$).
  - **Frozen-Prefix Invariance**: **100% preserved** across all 6,160 dynamic updates.
  - **Route Feasibility**: **100% feasible** (all visited customer vertices served exactly once; prefix sequence immutable; tour returns to depot 0).

---

## 4. Live Command Verification Outputs

### 4.1 Research Audit Command
```bash
python scripts/audit_research_results.py
```
**Recorded Execution Output**:
```
======================================================================
      ADAPTIVE ROUTE OPTIMIZATION — PRE-PHASE 9 RESEARCH AUDIT        
======================================================================
Audit output directory: results/audit


--- RECONCILIATION SUMMARY ---
Total Claims Inventoried:   40
Passed Claims:              40 (100.0%)
Failed Claims:              0
Inconclusive Claims:        0
Unverifiable Claims:        0

--- INTEGRITY & REPRODUCIBILITY CHECKS ---
All Experimental Fairness Checks Passed: True
All Reproducibility & Artifact Checks Passed: True

======================================================================
                 OVERALL AUDIT VERDICT: PASS
======================================================================

Reconciliation table saved to: C:\Users\hrish\Desktop\3rd year\1st sem\DAA\cp\adaptive-route-optimization\results\audit\metric_reconciliation.csv
Claim inventory saved to:     C:\Users\hrish\Desktop\3rd year\1st sem\DAA\cp\adaptive-route-optimization\results\audit\claim_inventory.csv
```

### 4.2 Full Test Suite Command
```bash
python -m pytest
```
**Recorded Execution Output**:
```
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
................................................                         [100%]
336 passed in 39.41s
```

---

## 5. Dashboard Launch & Verification

### 5.1 Documented Launch Command
```bash
python scripts/run_dashboard.py --port 8501
```

### 5.2 Server Startup Confirmation
- **Startup Log**:
  ```
  2026-10-24 13:19:10.367 Uvicorn server started on :::8501
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
  Network URL: http://192.168.29.76:8501
  ```
- **HTTP Verification**:
  ```python
  import urllib.request
  response = urllib.request.urlopen("http://localhost:8501", timeout=5)
  assert response.status == 200
  ```
  Confirmed: `HTTP Response Status: 200 OK`.

### 5.3 Automated Headless AppTest Verification
All four primary views were exercised using `streamlit.testing.v1.AppTest`:
- **View 1 (Overview)**: Rendered markdown formulation, strategy complexity, and Rule v2 explanation (0 exceptions).
- **View 2 (Route Demonstration)**: Rendered live interactive simulator with metric cards, timeline slider, Before/After view, and Head-to-Head strategy comparisons on both synthetic and TSPLIB benchmarks (0 exceptions).
- **View 3 (Algorithm Comparison)**: Loaded Stage 5 analysis figures, statistical qualification warning, and filtered results explorer across `stage4_full_matrix` and `stage5_adaptive_validation` (0 exceptions).
- **View 4 (Research Evidence)**: Rendered audit status cards, claim inventory table, and data integrity checklist (0 exceptions).

### 5.4 Remaining Manual Browser Inspections Protocol
The following manual checks should be conducted in an interactive browser window during user evaluation:
1. **Canvas Margin & DPI Rendering**: Verify that Matplotlib route plots render clearly without clipping axis labels or legends on high-DPI displays.
2. **Animation Playback Cadence**: Click `Play` in View 2 and observe sequential arrival steps advancing at the configured ~0.7s interval until the final step.
3. **Sidebar Responsiveness**: Collapse and expand the navigation sidebar to verify responsive reflow on narrow desktop or mobile viewports.

---

## 6. Git Working Tree Review

The working tree was inspected using `git status --porcelain`. No files were discarded or overwritten.

### 6.1 Modified Tracked Files (26 files)
1. `README.md`: Overhauled documentation with full mathematical model, strategy table, Rule v2 details, benchmarks, and CLI instructions.
2. `pyproject.toml`: Project build configuration and package metadata.
3. `requirements.txt`: Python runtime dependencies.
4. `src/adaptive_route_optimization/__init__.py`: Package entry point and versioning.
5. `src/adaptive_route_optimization/algorithms/adaptive/evaluate_adaptive.py`: Adaptive evaluation routines.
6. `src/adaptive_route_optimization/algorithms/adaptive/selector.py`: Corrected AdaptiveSelector with Rule v2 budget-aware selection logic.
7. `src/adaptive_route_optimization/algorithms/local_search/two_opt.py`: Suffix-constrained 2-opt local search with candidate evaluation accounting.
8. `src/adaptive_route_optimization/algorithms/repair/__init__.py`: Repair package exports.
9. `src/adaptive_route_optimization/audit/recompute.py`: Metric recalculation engine for research audit.
10. `src/adaptive_route_optimization/audit/reproducibility.py`: Manifest and artifact integrity auditing.
11. `src/adaptive_route_optimization/audit/runner.py`: Research audit orchestrator.
12. `src/adaptive_route_optimization/evaluation/metrics.py`: Route metrics, disruption calculation, and timing.
13. `src/adaptive_route_optimization/experiments/runner.py`: Experiment execution engine with budget tracking and fingerprinting.
14. `src/adaptive_route_optimization/experiments/schema.py`: Dataclass schemas for experimental conditions and budgets.
15. `src/adaptive_route_optimization/models/__init__.py`: Model exports.
16. `src/adaptive_route_optimization/models/instance.py`: Problem instance representations and synthetic generators (Uniform, Clustered, Mixed).
17. `src/adaptive_route_optimization/simulation/events.py`: Dynamic event sequence generation and arrival schedule types.
18. `src/adaptive_route_optimization/simulation/simulator.py`: Event simulator supporting Strategies A, B, C, and Adaptive with frozen-prefix enforcement.
19. `src/adaptive_route_optimization/ui/__init__.py`: UI package exports.
20. `src/adaptive_route_optimization/ui/app.py`: Streamlit research dashboard with 4 views and Stage 4/5 results explorer.
21. `src/adaptive_route_optimization/ui/data_loader.py`: UIDataLoader supporting Stage 4, Stage 5B, and historical datasets.
22. `src/adaptive_route_optimization/ui/demonstrator.py`: InteractiveDemonstrator supporting all distributions, benchmarks, budgets, and strategies.
23. `src/adaptive_route_optimization/ui/visualizer.py`: Matplotlib route visualizer supporting flexible head-to-head strategy comparisons.
24. `tests/test_adaptive.py`: Adaptive selector unit tests including Rule v2 budget threshold tests.
25. `tests/test_simulation.py`: Event simulator and frozen-prefix invariance unit tests.
26. `tests/test_ui.py`: UI and demonstrator tests (28 tests covering loaders, visualizers, TSPLIB, and Strategy C).

### 6.2 Untracked Files and Directories (16 items)
1. `configs/stage4_full_matrix.json`: 14-condition, 280-run benchmark campaign specification.
2. `configs/stage5_adaptive_validation.json`: 4-condition, 48-run targeted validation specification.
3. `docs/PHASE9_UI_FUNCTIONAL_AUDIT.md`: Historical UI functional audit document.
4. `results/stage4_full_matrix/`: Primary Stage 4 experimental outputs (280 runs, 5,200 steps, manifest, and paired comparisons).
5. `results/stage4_smoke/`: Preflight smoke test outputs from Stage 4 verification.
6. `results/stage5_adaptive_validation/`: Stage 5B validation outputs (48 runs, 960 steps, manifest, and audit report).
7. `results/stage5_analysis/`: Stage 5 analysis tables (`performance_analysis.csv`, `paired_statistical_tests.csv`) and figures directory.
8. `results/stage6_acceptance_report.md`: This comprehensive final sign-off audit report.
9. `scripts/generate_figures.py`: CLI figure generator script.
10. `scripts/run_experiments.py`: CLI experiment execution script.
11. `src/adaptive_route_optimization/algorithms/repair/destroy_repair.py`: Strategy C Destroy-and-Repair / LNS suffix repair implementation.
12. `src/adaptive_route_optimization/benchmarks/`: TSPLIB parser (`tsplib.py`) and standard benchmark loader.
13. `src/adaptive_route_optimization/paths.py`: Path resolution helper across repository environments.
14. `tests/test_benchmark_expansion.py`: 44 unit tests for synthetic distributions and TSPLIB integration.
15. `tests/test_destroy_repair.py`: 24 unit tests for Strategy C operators and invariants.
16. `tests/test_stage4_experiments.py`: 12 unit tests for experiment runner schemas and matrix execution.

---

## 7. README & CLI Verification

All instructions and commands documented in `README.md` were tested and verified against the actual repository layout:
- Virtual environment activation: `.\.venv\Scripts\activate` (Valid)
- Package installation: `pip install -e .` (Valid)
- Unit and integration tests: `pytest -v` (336 passing tests)
- Research audit: `python scripts/audit_research_results.py` (40/40 claims passing)
- Dashboard launch: `python scripts/run_dashboard.py --port 8501` (Uvicorn started; HTTP 200)
- Campaign execution CLI: `python scripts/run_experiments.py --config configs/stage4_full_matrix.json` (Valid CLI with `--config` and `--output-dir` arguments)
- Figure generation CLI: `python scripts/generate_figures.py` (Valid CLI; outputs verified in `results/figures/`)

---

## 8. Final Stage 6 Sign-Off

All required audit checks have been performed and verified from first principles. No blockers or defects were identified.

**Stage 6 is marked COMPLETE**. Planned software development for the **Adaptive Route Optimization in Dynamic Environments** project is finished.
