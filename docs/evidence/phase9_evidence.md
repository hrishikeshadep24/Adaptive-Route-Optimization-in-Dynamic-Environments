# Phase 9 Evidence: Research Demonstrator and Visualization UI

## Gate Criterion (from `docs/PHASE_PLAN.md`)
> **Gate**: a person who knows nothing about the project can understand the problem, see a dynamic event, see the route change, and understand the measured trade-off without reading code.

---

## 1. Gate Verification: UI Implementation & Structure

The Research Demonstrator and Visualization Dashboard has been implemented as an interactive, academic-grade application using Streamlit and Matplotlib.

### Core Views & Sections Built:
1. **Research Overview & Problem Formulation**:
   - Explicitly presents the research question: *“How does the performance of different route-update strategies change with problem size ($n$) and level of dynamism ($\alpha$) under controlled computational budgets?”*
   - Defines the dynamic TSP model, the immutable frozen-prefix rule, and the uncommitted suffix repair space.
   - Compares Strategy A (Greedy Insertion), Strategy B (Insertion + 2-opt), and ADAPTIVE (explainable rule-based meta-selector).
   - Clarifies application neutrality (dynamic vehicle routing without GPS or map API dependencies).

2. **Interactive Dynamic Route Demonstrator**:
   - Visualizes the 2D Euclidean topology: Red square Depot (0), Green solid line Committed/Frozen Prefix, Royal Blue dashed line Uncommitted Suffix, and Orange star Newly Arrived Customer ($\Delta_t$).
   - Step slider ($1 \dots T$) allows stepping through time.
   - Displays live metrics: Route Cost ($C_{t-1} \to C_t$, $\Delta$), Candidate Evaluations used, Edge Disruption ($\delta$), Committed Count.
   - For ADAPTIVE: Displays the explicit decision rationale banner and an expandable inspector of observable decision-time state features ($|V_t|$, $f_t$, suffix edge count, dynamicity $\alpha$, revealed ratio, remaining budget).
   - Invariant check: Confirms and displays **"Frozen-Prefix Invariance Verified"** at every step.
   - Transparent disclaimer: Clearly labeled as an interactive demonstration distinct from the saved research benchmark datasets.

3. **Saved Experimental Results Explorer**:
   - Reads directly from immutable raw files: `results/held_out_matrix/runs.csv`, `results/pilot_matrix/runs.csv`, and `results/budgeted_pilot/runs.csv`.
   - Multi-select filters for problem size ($n \in [50, 100, 200]$), dynamicity ($\alpha \in [0.1, 0.2, 0.4, 0.6, 0.8]$), strategy (`A`, `B`, `ADAPTIVE`), and seed.
   - Live metric cards: Filtered run count, Mean Final Cost, Mean Candidate Evaluations, Mean Response Time (ms), Feasibility Rate (100%).
   - Interactive data table displaying full provenance (dataset path, run ID, commit hash, feasibility).

4. **Comparative Visualizations & Pareto Frontier**:
   - Interactive charts generated directly from filtered DataFrames:
     - Route Cost vs. Dynamicity across strategies.
     - Computational Effort (candidate evaluations, log scale) across dynamicity.
     - Quality vs. Computation Pareto Scatter Comparison.
     - Route Disruption ($\delta$) bar comparison.
     - Budget Cap Diminishing Returns Ablation chart.

5. **Research Findings & Methodological Limitations**:
   - Directly presents findings from `docs/RESEARCH_FINDINGS.md`:
     - 100% win rate for 2-opt at low dynamicity ($\alpha \le 0.2$, +10.86% improvement).
     - Super-linear computational scaling of 2-opt ($49.1\times$ to $75.1\times$ more evaluations, $110.8\times$ slower response time).
     - Route disruption doubling under 2-opt ($\delta = 0.0794$ vs $0.0367$).
     - The Myopic Local Search Trap: Strategy B fails in 66.7% of runs at $\alpha \ge 0.6$ (-5.01% penalty).
     - Adaptive selector superiority on unseen held-out seeds (944.71 vs 969.68 and 1023.13; 17.9% to 51.4% effort savings).
   - Notes limitations: uniform random 2D topology, threshold sensitivity, abstract problem formulation.

6. **Reproducibility & Audit Drawer**:
   - Shows pre-Phase 9 audit status: **VERDICT: PASS (40/40 claims verified)**.
   - Reconciles all 40 empirical claims side by side with claimed vs recomputed values and tolerances.
   - Inspects manifests and reports exact commands to rerun the audit and regression test suite.

---

## 2. Gate Verification: UI Launch & Availability

### Launch Command
```powershell
python scripts/run_dashboard.py --port 8501
```
Or directly via Streamlit:
```powershell
streamlit run src/adaptive_route_optimization/ui/app.py --server.headless true --server.port 8501
```

### Smoke Test Verification
- Verified compilation and syntax: `python -m py_compile src/adaptive_route_optimization/ui/app.py` passed with code 0.
- Verified headless figure generation for all route diagrams and research plots.
- Verified that all datasets load cleanly with zero missing column errors.

---

## 3. Test Suite Execution (All Phases)

### Command
```powershell
pytest -q
```

### Actual Output
```
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 94%]
............                                                             [100%]
226 passed in 14.88s
```
- **Total passing tests**: **226 passed**
  - 186 baseline tests (Phases 1–7)
  - 14 Phase 8 adaptive selector and regret tests
  - 12 pre-Phase 9 research audit tests
  - 14 Phase 9 UI, data loader, visualizer, and demonstrator tests (`tests/test_ui.py`)
- Zero regressions.

---

## 4. Source Data Mapping and Metric Traceability

| UI View / Component | Displayed Metrics | Source Data File | Underlying Source Columns |
|---|---|---|---|
| **Results Explorer (Held-Out)** | Final Cost, Evaluations, Time (ms), Disruption, Feasibility | `results/held_out_matrix/runs.csv` | `final_cost`, `total_computational_effort`, `total_response_time_ms`, `mean_disruption`, `all_feasible` |
| **Results Explorer (Pilot)** | Final Cost, Evaluations, Time (ms), Disruption, Feasibility | `results/pilot_matrix/runs.csv` | `final_cost`, `total_computational_effort`, `total_response_time_ms`, `mean_disruption`, `all_feasible` |
| **Results Explorer (Budgeted)** | Cost vs. Budget Cap | `results/budgeted_pilot/runs.csv` | `final_cost`, `budget_type`, `budget_limit`, `total_computational_effort` |
| **Comparative Visualizations** | Cost curves, Effort curves, Pareto scatter, Disruption bars | Filtered `runs.csv` | `final_cost`, `total_computational_effort`, `dynamicity`, `strategy`, `mean_disruption` |
| **Audit Drawer** | Claimed vs. Recomputed reconciliation table | `results/audit/metric_reconciliation.csv` | `claim_id`, `metric_name`, `claimed_value`, `recomputed_value`, `abs_difference`, `status` |
| **Audit Drawer** | Integrity & Manifest checks | `results/audit/data_integrity_report.json`, `results/audit/reproducibility_report.json` | `check_name`, `passed`, `details` |
| **Route Demonstrator** | Tour coordinates, frozen prefix, step cost, evaluations, decision rationale | Recomputed dynamically or stepped via `Simulator` | `coords`, `vertices`, `frozen_prefix_length`, `cost`, `metrics.computational_effort`, `AdaptiveSelector` rationale |

---

## 5. Frozen-Prefix Invariance Verification in UI Demonstrator

In `InteractiveDemonstrator` and verified by `tests/test_ui.py::TestInteractiveDemonstrator::test_frozen_prefix_invariance_all_steps`:
- For every step $t = 1 \dots T$:
  $$\text{route\_before}[0 : f_t + 1] == \text{route\_after}[0 : f_t + 1]$$
- The vehicle's committed prefix remains 100% invariant during route repair across all strategies (Strategy A, Strategy B, and ADAPTIVE).

---

## 6. Deliverables Summary

| Deliverable | File Path |
|---|---|
| Data Loader Module | `src/adaptive_route_optimization/ui/data_loader.py` |
| Route Step Visualizer | `src/adaptive_route_optimization/ui/visualizer.py` |
| Research Plotting Module | `src/adaptive_route_optimization/ui/plots.py` |
| Interactive Demonstrator Engine | `src/adaptive_route_optimization/ui/demonstrator.py` |
| Streamlit Application | `src/adaptive_route_optimization/ui/app.py` |
| UI Package Exports | `src/adaptive_route_optimization/ui/__init__.py` |
| Dashboard Launcher Script | `scripts/run_dashboard.py` |
| Automated UI Unit/Integration Tests | `tests/test_ui.py` (14 passed) |
| Phase 9 Evidence Document | `docs/evidence/phase9_evidence.md` |

**Gate Status**: ✅ **SATISFIED**.
An external observer can launch the dashboard, immediately understand the dynamic TSP problem, step through dynamic customer arrivals, watch the route update while the green prefix remains frozen, and inspect the empirical quality-computation trade-offs directly from audited experiment data without inspecting code.
