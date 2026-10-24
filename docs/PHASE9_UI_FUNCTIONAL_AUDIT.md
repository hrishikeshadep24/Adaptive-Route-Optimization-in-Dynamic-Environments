# Phase 9 UI & Functional Audit Report: Adaptive Route Optimization in Dynamic Environments

**Document Version**: 1.0.0  
**Audit Date**: 2026-10-21  
**Project**: Adaptive Route Optimization in Dynamic Environments (DAA Capstone Project)  
**Target Path**: `docs/PHASE9_UI_FUNCTIONAL_AUDIT.md`  
**Audit Scope**: Read-only technical, algorithmic, and functional inspection of the Phase 9 Research Demonstrator and Visualization Dashboard, supporting UI modules, simulation engine, empirical results, and audit verification artifacts.

---

## Executive Summary

This functional audit provides an exhaustive, self-contained technical inventory of the **Adaptive Route Optimization in Dynamic Environments** application. Its purpose is to document exactly what the software does, how every user interface control functions, how algorithms and simulations execute, what metrics are reported, and which empirical claims are verifiable before designing any UI/UX modifications.

The repository implements a controlled, application-neutral experimental study of route-update strategies for the single-route **Dynamic Traveling Salesperson Problem (Dynamic TSP)** under an immutable **frozen-prefix operational constraint**. It features:
1. Two baseline dynamic repair heuristics: **Strategy A** (Cheapest Greedy Insertion) and **Strategy B** (Cheapest Insertion followed by First-Improvement 2-opt Local Search).
2. An explainable, rule-based **Adaptive Strategy Selector** (Phase 8) designed to circumvent the discovered *"Myopic Local Search Trap"*.
3. A complete **Pre-Phase 9 Independent Research Audit** verifying 40 numerical claims, strict input parity (Rule 10), and zero future information leakage.
4. An interactive **Streamlit Dashboard** (`src/adaptive_route_optimization/ui/app.py`) providing step-by-step route visualization, audited results exploration, Pareto trade-off curves, and an audit drawer.

---

## 1. Project Purpose and Architecture

### 1.1 The Research Problem & Mathematical Model

The project investigates the core algorithmic question:
> **"How does the performance of different route-update strategies change with problem size ($n$) and level of dynamism ($\alpha$) under controlled computational budgets?"**

In dynamic routing (e.g., dispatching, autonomous inspection, robot surveillance), a vehicle departs a central depot along an initial planned tour. While the vehicle travels, **new customer requests arrive dynamically** at discrete time steps $t$. The system must update the remaining tour to incorporate new vertices without violating physical and operational constraints.

```
Initial State (t=0)        Event Step (t=1)               Event Step (t=2)
V_0 known                  New arrivals Δ_1               New arrivals Δ_2
Build initial tour         Vehicle visits p_1             Vehicle visits p_2
(Nearest Neighbor)         Prefix [0, p_1] FROZEN         Prefix [0, p_1, p_2] FROZEN
                           Repair suffix (p_1..0)         Repair suffix (p_2..0)
```

#### Core Mathematical Formulations
- **Metric Space**: Complete undirected graph $G = (V, E)$ embedded in the 2D Euclidean plane $[0.05, 0.95] \times [0.05, 0.95]$. Depot is vertex $0$, located at $(0.5, 0.5)$ in synthetic instances or $(0.0, 0.0)$ in origin-centered instances.
- **Cost Function**: Edge cost $c(i, j) = \sqrt{(x_i - x_j)^2 + (y_i - y_j)^2}$ (Euclidean distance, symmetric, satisfying triangle inequality). Implemented in [`src/adaptive_route_optimization/models/instance.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/models/instance.py#L44-L59).
- **Tour Representation**: A tour $R = (0, v_1, v_2, \dots, v_k, 0)$ starting and terminating at depot $0$, visiting every required customer vertex exactly once with no intermediate depot visits. Implemented in [`src/adaptive_route_optimization/models/route.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/models/route.py#L15-L41).
- **Tour Cost**: Total Euclidean length $C(R) = \sum_{i=0}^{|R|-2} c(R[i], R[i+1])$.
- **Dynamic Event $\Delta_t$**: A set of previously unrevealed customer vertices becoming known at time step $t$. Total customers $n = |V \setminus \{0\}|$. Initially revealed $V_0 \subseteq V$. Overall dynamicity $\alpha = \frac{n - |V_0 \setminus \{0\}|}{n} \in [0.0, 1.0]$.
- **Frozen-Prefix Rule**: At time step $t$, the vehicle has traversed a prefix of $f_t$ customer vertices: $(0, p_1, p_2, \dots, p_{f_t})$. **This prefix is strictly immutable.** No algorithm may insert, reorder, or delete edges within $R[0 : f_t + 1]$.
- **Uncommitted Suffix**: The remaining open path $(p_{f_t}, u_1, u_2, \dots, u_m, 0)$ connecting the vehicle's current position $p_{f_t}$ through unvisited customers back to the depot. **Only this suffix may be re-optimized.**
- **Route Disruption $\delta(S_{t-1}, S_t)$**: Normalized edge turnover measuring route instability:
  $$\delta = 1.0 - \frac{|E(S_{t-1}) \cap E(S_t)|}{\max(|E(S_{t-1})|, |E(S_t)|)} \in [0.0, 1.0]$$
  Implemented in [`src/adaptive_route_optimization/evaluation/metrics.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/evaluation/metrics.py#L47-L72).

### 1.2 Application Architecture and Module Responsibilities

The codebase follows a modular, dependency-injected design where each layer is strictly decoupled:

```
src/adaptive_route_optimization/
├── models/             # Problem representations (Instance, Route)
├── algorithms/
│   ├── baseline/       # Nearest Neighbor construction, small-n Brute-Force Exact solver
│   ├── local_search/   # First-improvement 2-opt with prefix constraints
│   ├── repair/         # Cheapest greedy insertion & composite insertion+2-opt
│   └── adaptive/       # Feature extraction, explainable rule selector, offline oracle
├── simulation/         # Discrete-event simulator, dynamic state, replay engine, event logs
├── experiments/        # Manifests, batch runners, matrix configs, reproducibility
├── analysis/           # Statistical battery (t-test, Wilcoxon, Cohen's d), visualizer, pipeline
├── audit/              # 40-claim catalog, independent recomputation, input-parity auditor
└── ui/                 # Streamlit app, data loader, interactive demonstrator, plotting
```

| Module | Core Classes / Functions | Primary Responsibility |
|---|---|---|
| `models` | `Instance`, `Route` | Immutable representations of problem topology, Euclidean coordinates, validity assertions, and edge indexing. |
| `algorithms.baseline` | `nearest_neighbor()`, `solve_exact()` | Initial static tour generation ($V_0$) and ground-truth verification on small $n \le 10$ instances. |
| `algorithms.repair` | `cheapest_insertion_repair()`, `strategy_b_repair()` | Algorithmic implementations of Strategy A and Strategy B on whole routes or suffixes. |
| `algorithms.local_search` | `two_opt()` | First-improvement 2-opt supporting a `min_i` boundary to preserve the frozen prefix. |
| `algorithms.adaptive` | `extract_features()`, `AdaptiveSelector`, `OracleEvaluator` | Decision-time feature extraction ($O(1)$), explainable rule-based meta-selection, and hindsight oracle regret computation. |
| `simulation` | `Simulator`, `DynamicState`, `EventSequence`, `generate_event_sequence()` | Step-by-step state machine, advancing time $t$, revealing events $\Delta_t$, enforcing the frozen prefix, and logging metrics. |
| `experiments` | `ExperimentRunner`, `ExperimentConfig`, `ExperimentManifest` | Headless execution of experiment matrices, tracking seeds, commit hashes, and JSON/CSV outputs. |
| `analysis` | `AnalysisPipeline`, `StatisticalBattery`, `plot_*` | Aggregates runs, executes hypothesis tests (Wilcoxon, t-test, Cohen's $d_z$), generates publication tables and figures. |
| `audit` | `ResearchAuditor`, `ClaimInventory`, `ReproducibilityAuditor` | Recalculates 40 research claims from raw CSVs, verifies input parity (Rule 10), and checks artifact integrity. |
| `ui` | `app.py`, `UIDataLoader`, `InteractiveDemonstrator`, `render_route_step_diagram()` | Interactive Streamlit dashboard, Matplotlib route visualizer, and filtered results explorer. |

### 1.3 Scope Boundaries: Implemented vs. Planned/Out-of-Scope

Per `AGENTS.md` (Project Rules) and `docs/PHASE_PLAN.md`:
- **Strictly Implemented (Phases 1–9)**:
  - Single-route Dynamic TSP with Euclidean distances.
  - Cheapest Greedy Insertion (Strategy A) and Insertion + 2-opt (Strategy B).
  - Frozen-prefix execution constraint ($f_t$ advances by 1 vertex per step).
  - Controlled computational budget instrumentation (candidate evaluations, response time).
  - Interpretable, rule-based adaptive selection (Phase 8).
  - Pre-Phase 9 independent verification audit of 40 empirical claims.
  - Streamlit demonstration and analysis dashboard (Phase 9).
- **Incomplete / Not Implemented in UI**:
  - *Algorithm Lab Synchronized Replay*: Mentioned in `PHASE_PLAN.md` Phase 9 tasks ("side-by-side strategy comparison with synchronized replay"), but not implemented in `app.py`. The demonstrator runs a single policy per session.
  - *Replay Mode from Stored Experiment Seeds*: The demonstrator uses synthetic instances generated on the fly from a UI seed, rather than loading the exact 200-customer instances from `results/pilot_matrix/`.
- **Strictly Out of Scope (Forbidden by `AGENTS.md` Rule 13)**:
  - Live GPS, real-world map data, traffic/weather APIs.
  - Reinforcement learning (RL), deep neural networks, or black-box ML.
  - Multi-vehicle routing (VRP), vehicle capacity, time windows, driver breaks.
  - Cloud deployment, mobile applications, production dispatch systems.

---

## 2. Complete Dashboard Inventory

The dashboard is implemented in [`src/adaptive_route_optimization/ui/app.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/ui/app.py) (479 lines). It is launched via [`scripts/run_dashboard.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/scripts/run_dashboard.py) on port 8501.

### 2.1 Global Shell & Sidebar
- **Header**: Title `"🗺️ Adaptive Route Optimization in Dynamic Environments"` with subtitle `"A Controlled Empirical Study of Dynamic Route-Repair Strategies and Interpretable Adaptive Selection"` (`app.py:L40-L41`).
- **Sidebar Navigation**: Radio selector `nav_selection` with 6 views (`app.py:L45-L55`).
- **Sidebar Provenance Card**: Displays project metadata: Dynamic TSP + Frozen Prefix, Baselines A & B, Adaptive Selector, Pre-Phase 9 Audit PASS, Regression Tests (hardcoded as `"212 Passed"` in sidebar info card, `app.py:L59-L67`).

---

### 2.2 View 1: Research Overview & Problem Formulation
- **Purpose**: Academic introduction to the dynamic routing problem, operational constraints, evaluated strategies, and pipeline architecture.
- **Source Code**: `app.py:L72-L125`.
- **Data Source**: Static Markdown; derives no data from files or runtime simulations.
- **Visible Elements**:
  1. *Core Research Question Callout* (`app.py:L79-L80`): Quotes the central research question.
  2. *Operational Constraints List* (`app.py:L85-L89`): Details the Frozen-Prefix Rule, Uncommitted Suffix Re-optimization, and Computational Budgeting.
  3. *Evaluated Strategies Table* (`app.py:L95-L100`): Markdown table contrasting Strategy A ($O(m)$), Strategy B ($O(m^2)$), and ADAPTIVE ($O(1)$ overhead).
  4. *Application Neutrality Note* (`app.py:L102-L103`): Clarifies that delivery is only an interpretation and no live GPS/map APIs are used.
  5. *Experimental Pipeline Flow Diagram* (`app.py:L107-L125`): Text ASCII flow diagram of instance $\to$ initial tour $\to$ dynamic arrivals $\to$ strategy repair.
- **Assessment**:
  - *Essential*: Provides necessary theoretical context.
  - *Limitations*: Static text only. First-time users have to read dense text before seeing visual demonstrations.

---

### 2.3 View 2: Interactive Dynamic Route Demonstrator
- **Purpose**: Step-by-step interactive visual simulation of a dynamic routing scenario, demonstrating customer arrivals, vehicle movement along the frozen prefix, suffix repair, and adaptive decision rationale.
- **Source Code**: `app.py:L130-L220`; uses `InteractiveDemonstrator` in [`demonstrator.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/ui/demonstrator.py) and `render_route_step_diagram()` in [`visualizer.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/ui/visualizer.py).
- **Data Source**: **Runs a fresh on-the-fly simulation** using synthetic instances generated deterministically from `demo_seed`. It does *not* read the saved experimental CSV files.
- **Visible Elements & Controls**:
  1. *Interactive Mode Disclaimer Banner* (`app.py:L139-L142`): Explicitly warns that this view runs interactive visual scenarios rather than loading the audited benchmark datasets.
  2. *Control Bar* (`app.py:L145-L154`):
     - `demo_n`: Problem Size dropdown (`[10, 15, 20, 30]`, default: 15).
     - `demo_dyn`: Dynamicity Level dropdown (`[0.2, 0.4, 0.6, 0.8]`, default: 0.4).
     - `demo_seed`: Random Seed numeric input (`min=1, max=9999`, default: 42).
     - `demo_strat`: Repair Policy dropdown (`["ADAPTIVE", "A", "B"]`, default: `"ADAPTIVE"`).
  3. *Timeline Step Slider* (`app.py:L169-L175`): `st.slider` stepping through event steps $t \in [1, T]$ (`total_steps = n * dynamicity`).
  4. *Metric Cards* (`app.py:L180-L190`):
     - `Route Cost`: Displays $C(S_t)$ with delta $C(S_t) - C(S_{t-1})$.
     - `Candidate Evals`: Evaluations consumed in step $t$ (`evaluations_used`).
     - `Edge Disruption (δ)`: Step edge turnover $\delta(S_{t-1}, S_t)$.
     - `Committed Vertices`: Count of frozen customer vertices $f_t$.
     - `Strategy Applied`: Label of policy applied at step $t$ (`"Strategy A (Greedy)"` or `"Strategy B (2-opt)"`).
  5. *Frozen-Prefix Invariance Callout* (`app.py:L193-L196`):
     - Green alert: `"✅ Frozen-Prefix Invariance Verified: Visited prefix edges remained strictly immutable during update."`
     - Red alert: `"❌ Invariant Violation: Frozen prefix was modified during repair!"`
  6. *Adaptive Selector Rationale Banner* (`app.py:L198-L199`): If ADAPTIVE is selected, displays the exact decision rule string (e.g. `"🧠 Adaptive Selector Rationale: High dynamicity early-stage (α=0.40, revealed=0.60): avoiding myopic trap"`).
  7. *2D Spatial Route Diagram* (`app.py:L202-L214`): Matplotlib figure rendering depot, frozen prefix, uncommitted suffix, and new arrivals.
  8. *Decision-Time Features Inspector* (`app.py:L217-L219`): Expandable JSON drawer (`st.expander`) displaying all 11 observable state features at decision time $t$.
- **Assessment**:
  - *Essential*: Core demonstration proving the algorithmic mechanics and verifying invariant preservation.
  - *Confusing / Overly Technical*: The faint grey dots representing "Unrevealed Customers" are visible in the background, which might cause a non-expert to think the algorithm can peek at future requests.

---

### 2.4 View 3: Saved Experimental Results Explorer
- **Purpose**: Direct inspection of the audited research datasets without running simulations. Allows filtering runs, viewing aggregate performance metrics, and inspecting raw tabular run logs.
- **Source Code**: `app.py:L224-L321`; uses `UIDataLoader` in [`data_loader.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/ui/data_loader.py).
- **Data Source**: **Reads raw, immutable CSV/JSON files** (`results/held_out_matrix/runs.csv`, `results/pilot_matrix/runs.csv`, `results/budgeted_pilot/runs.csv`). Computes derived means and counts.
- **Visible Elements & Controls**:
  1. *Experiment Batch Selector* (`app.py:L233-L240`): Dropdown choosing between:
     - `"Held-Out Matrix (Phase 8, Unseen Seeds [1234, 5678, 9999])"`
     - `"Pilot Matrix (Phase 6 & 7, Seeds [42, 101, 777])"`
     - `"Budgeted Pilot Matrix (Phase 6 & 7, Budget Caps)"`
  2. *Dataset Provenance Info Banner* (`app.py:L257-L261`): Shows file path, completed runs count, failed runs count (0), and Git commit hash (`manifest.json`).
  3. *Multi-Select Filter Bar* (`app.py:L264-L276`):
     - `Problem Size (n)`: Multi-select of unique sizes (e.g. `[50, 100, 200]`).
     - `Dynamicity (α)`: Multi-select of dynamicities (e.g. `[0.1, 0.2, 0.4, 0.6, 0.8]`).
     - `Strategy`: Multi-select (`['A', 'B', 'ADAPTIVE']`).
     - `Random Seed`: Multi-select of seeds (e.g. `[1234, 5678, 9999]`).
  4. *Filtered Summary Metric Cards* (`app.py:L288-L299`):
     - `Filtered Runs`: Count of matching records.
     - `Mean Final Cost`: Mean $C(S_T)$ across filtered runs.
     - `Mean Effort (Evals)`: Mean total candidate evaluations.
     - `Mean Time (ms)`: Mean total wall-clock runtime in ms.
     - `Feasibility Rate`: Percentage of runs where `all_feasible == True` (always 100.0%).
  5. *Interactive Data Table* (`app.py:L301-L318`): Interactive dataframe displaying `run_id`, `condition_id`, `strategy`, `total_vertices`, `dynamicity`, `seed`, `final_cost`, `total_computational_effort`, `total_response_time_ms`, `mean_disruption`, and `all_feasible`.
- **Assessment**:
  - *Essential*: Demonstrates transparency and proves results are not hardcoded.
  - *UI Problem*: In `app.py:L317`, uses deprecated Streamlit argument `use_container_width=True` which logs deprecation warnings in Streamlit 1.39+.

---

### 2.5 View 4: Comparative Visualizations & Pareto Frontier
- **Purpose**: Visual presentation of publication-quality empirical trade-off curves substantiating cost, effort, disruption, and budget diminishing returns.
- **Source Code**: `app.py:L325-L366`; uses plotting functions in [`plots.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/ui/plots.py).
- **Data Source**: **Computes figures on the fly from saved CSV files** (`results/held_out_matrix/runs.csv`, `results/pilot_matrix/runs.csv`, `results/budgeted_pilot/runs.csv`).
- **Visible Elements & Controls**:
  1. *Data Basis Radio Selector* (`app.py:L334-L338`): Radio choosing between:
     - `"Held-Out Matrix (Phase 8: Always A vs. Always B vs. ADAPTIVE)"`
     - `"Pilot Matrix (Phase 7: Strategy A vs. Strategy B)"`
  2. *Top Chart Row* (`app.py:L342-L347`):
     - Chart 1: *Mean Final Route Cost across Dynamicity* (Line chart comparing strategies across $\alpha \in [10\%, 80\%]$).
     - Chart 2: *Computational Effort (Candidate Evaluations, Log Scale)* across dynamicity.
  3. *Bottom Chart Row* (`app.py:L348-L353`):
     - Chart 3: *Quality vs. Computation Pareto Frontier* (Log-scale scatter plot: evaluations on x-axis vs final cost on y-axis).
     - Chart 4: *Mean Route Disruption (δ) Comparison* (Bar chart showing structural edge turnover).
  4. *Budget Cap Ablation Section* (`app.py:L355-L364`):
     - Chart 5: *Diminishing Marginal Returns of 2-opt Budget Caps* (Bar chart comparing Unbounded, 500 Evals, 200 Evals, and Strategy A).
     - Caption explaining that a 500-evaluation cap captures 96.1% of quality improvement while cutting evaluations by 32.3%.
- **Assessment**:
  - *Essential*: Directly answers the primary research question with clear visual trade-offs.

---

### 2.6 View 5: Research Findings & Methodological Limitations
- **Purpose**: Permanent scholarly record of findings, effect sizes, statistical significance, the mechanistic explanation of the local search trap, and project boundaries.
- **Source Code**: `app.py:L370-L410`.
- **Data Source**: Static Markdown replicating [`docs/RESEARCH_FINDINGS.md`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/docs/RESEARCH_FINDINGS.md).
- **Visible Elements**:
  1. *Empirically Backed Findings List* (`app.py:L374-L393`):
     - Finding 1: 100% win rate for Strategy B at $\alpha \le 0.2$ (+10.86% improvement).
     - Finding 2: Super-linear scaling of 2-opt ($49.1\times$ to $75.1\times$ evaluations, $p = 1.86 \times 10^{-9}$).
     - Finding 3: Route disruption doubling under 2-opt ($\delta = 0.0794$ vs $0.0367$).
     - Finding 4: Adaptive meta-selection superiority on unseen seeds (mean cost 944.71 vs 1023.13 and 969.68).
  2. *Negative Findings Callout: The Myopic Local Search Trap* (`app.py:L396-L404`):
     - Explains why Strategy B fails in 66.7% of cases at $\alpha \ge 0.6$ (-5.01% penalty) due to frozen prefix locking into an early trap trajectory.
  3. *Documented Project Limitations* (`app.py:L405-L409`): Lists topology scope (uniform 2D), threshold transferability, and application neutrality.
- **Assessment**:
  - *Essential*: Adheres strictly to scientific integrity; explicitly highlights limitations and negative results rather than burying them.

---

### 2.7 View 6: Reproducibility & Audit Drawer
- **Purpose**: Complete independent audit report displaying the pre-Phase 9 verification status, 40/40 claim reconciliation table, and integrity checks.
- **Source Code**: `app.py:L415-L476`; uses `load_audit_reconciliation()` and `load_audit_reports()` from `data_loader.py`.
- **Data Source**: **Reads saved audit reports** (`results/audit/metric_reconciliation.csv`, `results/audit/data_integrity_report.json`, `results/audit/reproducibility_report.json`).
- **Visible Elements**:
  1. *Audit Summary Metric Cards* (`app.py:L432-L442`):
     - `Overall Audit Verdict`: Displays `"PASS"` with delta `"100% Verified"`.
     - `Total Claims Audited`: 40.
     - `Passed Claims`: `"40 / 40"`.
     - `Regression Tests`: `"212 Passed"` (reflects pre-Phase 9 test count).
  2. *Claim Reconciliation Table* (`app.py:L444-L460`): Interactive table displaying all 40 claims with `claim_id`, `phase`, `metric_name`, `claimed_value`, `recomputed_value`, `abs_difference`, `tolerance`, `status`, and `source_file`.
  3. *Data Integrity & Parity Checks* (`app.py:L463-L466`): 5 bullet checks confirming identical initial costs, event sequences, and non-negative costs across strategies.
  4. *Reproducibility & Manifest Checks* (`app.py:L467-L470`): 6 bullet checks confirming manifest completeness and exact numerical reproduction of the pilot matrix.
  5. *Reproduction Commands Box* (`app.py:L472-L475`): Shows exact commands to rerun the audit (`python scripts/audit_research_results.py`) and test suite (`pytest -q`).
- **Assessment**:
  - *Essential*: Crucial academic defense artifact proving reproducibility.
  - *UI Problem*: In `app.py:L459`, uses deprecated Streamlit argument `use_container_width=True`.

---

## 3. Every Input Control and Its Actual Behaviour

Below is the complete specification of every interactive input control across the application:

| View | Control Label | Control Type | Allowed Values / Range | Default Value | Internal Variable & Type | Affected Functions / Calls | Actual Behaviour & Rerun Lifecycle | Scope Affected |
|---|---|---|---|---|---|---|---|---|
| **Global** | `"Select Dashboard View:"` | `st.sidebar.radio` | 6 view titles (strings) | `"1. Research Overview"` | `nav_selection` (`str`) | `app.py:L72, 130, 224, 325, 370, 415` | Full Streamlit page rerun. Conditionally switches the main container between Views 1–6. | Global UI |
| **View 2** | `"Problem Size (Total Customers n):"` | `st.selectbox` | `[10, 15, 20, 30]` | `15` | `demo_n` (`int`) | Passed to `InteractiveDemonstrator(n_vertices=demo_n, ...)` | Triggers full rerun. Instantiates a new `InteractiveDemonstrator`, creates new `Instance`, recalculates all simulation steps $t=1..T$, resets timeline slider. | Demonstrator only |
| **View 2** | `"Dynamicity Level α:"` | `st.selectbox` | `[0.2, 0.4, 0.6, 0.8]` | `0.4` (index 1) | `demo_dyn` (`float`) | Passed to `InteractiveDemonstrator(dynamicity=demo_dyn, ...)` | Triggers full rerun. Changes initial known count $V_0 = \max(2, \lfloor n(1-\alpha) \rfloor)$ and total event steps $T = n - |V_0 \setminus \{0\}|$. Re-simulates all steps. | Demonstrator only |
| **View 2** | `"Random Seed:"` | `st.number_input` | Integer `[1, 9999]` | `42` | `demo_seed` (`int`) | Passed to `InteractiveDemonstrator(seed=demo_seed, ...)` | Triggers full rerun. Reseeds `np.random.seed(seed)` to generate different synthetic customer coordinates and arrival orders. Re-simulates all steps. | Demonstrator only |
| **View 2** | `"Repair Policy:"` | `st.selectbox` | `["ADAPTIVE", "A", "B"]` | `"ADAPTIVE"` | `demo_strat` (`str`) | Passed to `InteractiveDemonstrator(strategy=demo_strat, ...)` | Triggers full rerun. Forces the simulator to apply Strategy A (Greedy), Strategy B (2-opt), or ADAPTIVE (meta-selector) at every dynamic step. | Demonstrator only |
| **View 2** | `"Dynamic Event Step (t):"` | `st.slider` | Integer `[1, total_steps]` | `1` | `step_idx` (`int`) | Calls `demo.get_step(step_idx)` | Triggers fast rerun. Extracts precomputed step record from `demo.step_records[step_idx - 1]`. Rerenders metric cards and calls `render_route_step_diagram()`. **Does NOT re-simulate.** | Demonstrator only |
| **View 3** | `"Select Experiment Batch:"` | `st.selectbox` | 3 string batch descriptions | `"Held-Out Matrix ..."` | `dataset_choice` (`str`) $\to$ `dataset_key` (`str`) | `loader.load_dataset_runs(dataset_key)`, `loader.load_dataset_manifest(dataset_key)` | Triggers rerun. Loads the corresponding dataset (`runs.csv` and `manifest.json`) from disk. Repopulates multi-select filter options and resets tables. | Results Explorer only |
| **View 3** | `"Problem Size (n):"` | `st.multiselect` | Subsets of `[50, 100, 200]` | All available sizes | `sel_sizes` (`list[int]`) | `loader.filter_runs(df_runs, sizes=sel_sizes, ...)` | Triggers rerun. Filters in-memory DataFrame rows matching `total_vertices.isin(sel_sizes)`. Updates summary metric cards and table. | Results Explorer only |
| **View 3** | `"Dynamicity (α):"` | `st.multiselect` | Subsets of `[0.1, 0.2, 0.4, 0.6, 0.8]` | All available dynamicities | `sel_dyns` (`list[float]`) | `loader.filter_runs(df_runs, dynamicities=sel_dyns, ...)` | Triggers rerun. Filters DataFrame rows where `dynamicity.round(4)` matches selected values. Updates cards and table. | Results Explorer only |
| **View 3** | `"Strategy:"` | `st.multiselect` | Subsets of `['A', 'B']` or `['A', 'B', 'ADAPTIVE']` | All available strategies | `sel_strats` (`list[str]`) | `loader.filter_runs(df_runs, strategies=sel_strats, ...)` | Triggers rerun. Filters DataFrame rows matching `strategy.isin(sel_strats)`. Updates cards and table. | Results Explorer only |
| **View 3** | `"Random Seed:"` | `st.multiselect` | Subsets of seeds present in batch | All available seeds | `sel_seeds` (`list[int]`) | `loader.filter_runs(df_runs, seeds=sel_seeds, ...)` | Triggers rerun. Filters DataFrame rows matching `seed.isin(sel_seeds)`. Updates cards and table. | Results Explorer only |
| **View 4** | `"Select Data Basis:"` | `st.radio` (horizontal) | `"Held-Out Matrix ..."` or `"Pilot Matrix ..."` | `"Held-Out Matrix ..."` | `vis_dataset` (`str`) $\to$ `dataset_key` (`str`) | `loader.load_dataset_runs(dataset_key)` passed to `plot_*()` | Triggers rerun. Switches source DataFrame passed to `plot_cost_by_dynamicity`, `plot_effort_by_dynamicity`, `plot_pareto_frontier`, and `plot_disruption_comparison`. Rerenders figures. | Visualizations only |

---

## 4. Route Visualization and Simulation Logic

### 4.1 Topology and Coordinate Generation
In [`src/adaptive_route_optimization/ui/demonstrator.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/ui/demonstrator.py#L60-L65):
```python
np.random.seed(seed)
coords = [(0.5, 0.5)]  # Depot at exact center
for _ in range(n_vertices):
    coords.append((float(np.random.uniform(0.05, 0.95)), float(np.random.uniform(0.05, 0.95))))
self.instance = Instance.from_coords(coords)
```
- **Depot**: Always index $0$, fixed at $(0.5, 0.5)$.
- **Customers**: Indices $1 \dots n$, generated uniformly within a 5% margin of the $[0, 1]^2$ unit box.
- **Distance Metric**: Strictly Euclidean distance $L_2 = \sqrt{\Delta x^2 + \Delta y^2}$. It is an abstract geometric graph; it does **not** model real-world roads, street grids, or turn penalties.
- **Repeatability**: Given the same `seed` and `n_vertices`, NumPy's seeded PRNG generates the exact same coordinate array every time.

### 4.2 Initial Route Construction & Event Sequence
1. **Initial Known Set $V_0$**: $\max(2, \lfloor n(1 - \alpha) \rfloor)$ non-depot customers plus depot $0$ are initially known (`events.py:L53`).
2. **Initial Tour $S_0$**: Nearest Neighbor heuristic starting at depot $0$, greedily visiting the closest unvisited vertex in $V_0$, and returning to depot $0$ (`simulator.py:L278-L282`).
3. **Event Generation**: Future customer vertices $V \setminus V_0$ are partitioned into sequential single-customer arrival events $\Delta_1, \Delta_2, \dots, \Delta_T$ ($T = n - |V_0 \setminus \{0\}|$). The arrival sequence is deterministically shuffled using `seed` (`events.py:L74-L75`).

### 4.3 Step-by-Step Simulation & Frozen-Prefix Preservation
At each discrete time step $t = 1 \dots T$:
1. **Arrival**: Event $\Delta_t = \{v\}$ arrives. $V_t = V_{t-1} \cup \{v\}$.
2. **Vehicle Position & Frozen Prefix $f_t$**: The vehicle advances by 1 customer along its current tour. Customers at positions $R[1 \dots f_t]$ are frozen.
3. **Suffix Extraction**: Suffix path $P_{\text{suffix}} = (R[f_t], u_1, \dots, u_m, 0)$ is extracted, starting at the vehicle's current location $R[f_t]$ and ending at depot $0$.
4. **Repair Execution**: The chosen policy inserts $v$ into $P_{\text{suffix}}$ and (if Strategy B) runs 2-opt on the suffix.
5. **Reconstruction**: Full tour is reconstructed: $S_t = R[0 : f_t + 1] + P_{\text{suffix, updated}}[1 : ]$.
6. **Invariance Assertion**:
   $$S_{t-1}[0 : f_t + 1] == S_t[0 : f_t + 1]$$
   Verified in `demonstrator.py:L151-L153` and tested across every step in `tests/test_ui.py:L149-L162`.

### 4.4 Visual Element Mapping in `render_route_step_diagram()`

Implemented in [`src/adaptive_route_optimization/ui/visualizer.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/ui/visualizer.py#L55-L206):

| Graphical Element | Marker / Line Style | Color | Z-Order | Semantic Meaning |
|---|---|---|---|---|
| **Depot (0)** | Large square (`s=140`) | Crimson Red (`#d62728`) | 5 | Central depot; tour start and terminal point. Annotated with text `"Depot"`. |
| **Committed Customers** | Circle (`s=75`) | Forest Green (`#2ca02c`) | 4 | Customers along the vehicle's traversed path ($R[1 \dots f_t]$); already visited/committed. |
| **Uncommitted Customers** | Circle (`s=65`) | Royal Blue (`#1f77b4`) | 4 | Known customers in the remaining suffix; not yet reached by the vehicle. |
| **Newly Arrived Customer ($\Delta_t$)** | Large star (`s=180`) | Vibrant Orange (`#ff7f0e`) | 6 | Customer vertex that arrived at the current step $t$. Highlighted for immediate recognition. |
| **Unrevealed Customers** | Small circle (`s=35`, $\alpha=0.5$) | Faint Light Grey (`#d3d3d3`) | 2 | Background customer locations in the hidden instance that have not yet arrived. |
| **Frozen Prefix Path** | Solid thick line (`linewidth=3.0`) | Solid Green (`#2ca02c`) | 3 | Physical trajectory already traversed; immutable. |
| **Uncommitted Suffix Path** | Dashed line (`linewidth=2.0`, `--`) | Dashed Blue (`#1f77b4`) | 3 | Planned remaining path; re-optimized during dynamic updates. |

#### Potential Ambiguity / Misleading Elements
1. **Unrevealed Customers Displayed**: Displaying faint grey dots gives the human observer full spatial context of the ground-truth benchmark, but a casual viewer might assume the routing algorithm has access to them. The UI must clearly emphasize that the algorithm is blind to these points.
2. **Path Crossover**: 2D straight Euclidean lines can cross over each other visually when 2-opt has not untangled them or when insertion creates a detour spike. This accurately reflects metric space cost, not road overpasses.

---

## 5. Algorithm Behaviour

### 5.1 Strategy A: Cheapest Greedy Insertion
- **Implementation**: [`cheapest_insertion_on_suffix()`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/simulation/simulator.py#L53-L93).
- **Mechanism**: For each newly arrived vertex $v \in \Delta_t$, the algorithm evaluates inserting $v$ into every existing edge $(u, w)$ in the uncommitted suffix.
- **Cost Delta**:
  $$\Delta c(u, v, w) = c(u, v) + c(v, w) - c(u, w)$$
- **Complexity & Effort Accounting**:
  - Suffix with $m$ edges $\implies$ exactly $m$ candidate position checks.
  - Candidate evaluations incremented: `total_evals += 1` for each edge checked.
  - Total complexity: $O(|\Delta_t| \cdot m)$ time, $O(1)$ auxiliary space.
  - Reconstructs tour by inserting $v$ at the index yielding $\min \Delta c$.

### 5.2 Strategy B: Cheapest Insertion followed by First-Improvement 2-opt
- **Implementation**: [`two_opt()`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/algorithms/local_search/two_opt.py#L42-L135) called via `simulator.py:L404-L436`.
- **Phase 1**: Executes Cheapest Greedy Insertion on the suffix exactly as in Strategy A (consuming $m$ evaluations).
- **Phase 2 (2-opt Local Search)**:
  - Constrained to the suffix by setting `min_i = state.frozen_prefix_length`.
  - Considers pairs of non-adjacent edges $(R[i], R[i+1])$ and $(R[j], R[j+1])$ where $i \ge \text{frozen\_prefix\_length}$ and $j > i + 1$.
  - Evaluation:
    $$\Delta c = c(R[i], R[j]) + c(R[i+1], R[j+1]) - c(R[i], R[i+1]) - c(R[j], R[j+1])$$
  - Acceptance Criterion: First-improvement ($\Delta c < -10^{-9}$). If a move improves cost, the segment $R[i+1 \dots j]$ is inverted immediately, and search restarts from the beginning of the pass.
  - Budget Control: Each edge-pair cost check increments `candidate_evaluations += 1`. Search terminates immediately if `candidate_evaluations >= max_evaluations`.
  - Termination: Terminates when a complete pass yields zero improving moves or when the evaluation cap is reached.

### 5.3 Adaptive Strategy Selector (Phase 8)
- **Implementation**: [`AdaptiveSelector`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/algorithms/adaptive/selector.py#L73-L156).
- **Observable Decision Features**: Extracted by [`extract_features()`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/src/adaptive_route_optimization/algorithms/adaptive/features.py#L54-L115) in $O(1)$ time with **zero future information leakage**:
  1. `total_vertices` ($n$)
  2. `known_vertices_count` ($|V_t|$)
  3. `frozen_prefix_length` ($f_t$)
  4. `uncommitted_count` (customers in suffix)
  5. `event_size` ($|\Delta_t|$)
  6. `revealed_ratio` ($\frac{|V_t| - 1}{n}$)
  7. `uncommitted_ratio` ($\frac{\text{uncommitted}}{\text{known}}$)
  8. `initial_dynamicity` ($\alpha$)
  9. `current_cost` ($C(S_t)$)
  10. `estimated_2opt_evals` ($\frac{m(m-3)}{2}$, where $m$ is suffix edge count)
  11. `remaining_eval_budget` (remaining evaluations if capped)
- **Selection Decision Rules**:
  ```python
  # Rule 1: Computational Budget Safety
  if remaining_eval_budget is not None and remaining_eval_budget < estimated_2opt_evals:
      return StrategyChoice.A, "Budget fallback: remaining < required"

  # Rule 2: Degeneracy Guard
  if suffix_edges < 4:
      return StrategyChoice.A, "Degeneracy guard: suffix length < 4"

  # Rule 3: Core Commitment Risk Evaluation
  if initial_dynamicity <= 0.20:
      return StrategyChoice.B, "Low dynamicity (α <= 0.20): high win rate for 2-opt"
  elif revealed_ratio >= 0.75:
      return StrategyChoice.B, "Late-stage event (revealed >= 0.75): commitment risk eliminated"
  else:
      return StrategyChoice.A, "High dynamicity early-stage: avoiding myopic trap"
  ```
- **Accounting Selection Overhead**: Every call to `select()` charges $+1$ evaluation to the cumulative computational effort counter (`selector.py:L45`).

---

## 6. Experimental Results and Metrics

### 6.1 Saved Datasets & Inventory

All experimental datasets reside under the `results/` directory:

| Dataset Identifier | Directory Path | File Format & Size | Runs Count | Conditions / Parameter Grid | Commit Hash Recorded |
|---|---|---|---|---|---|
| **Pilot Matrix** | `results/pilot_matrix/` | `runs.csv` (15.5 KB)<br>`steps.csv` (237 KB)<br>`manifest.json` (3.7 KB) | 60 runs (30 matched pairs) | $n \in [50, 100, 200]$, $\alpha \in [0.1, 0.2, 0.4, 0.6, 0.8]$, seeds `[42, 101, 777]`, Strategies A & B. | `00c9270` |
| **Held-Out Matrix** | `results/held_out_matrix/` | `runs.csv` (22.9 KB)<br>`steps.csv` (355 KB)<br>`manifest.json` (5.3 KB) | 90 runs (30 matched triplets) | $n \in [50, 100, 200]$, $\alpha \in [0.1, 0.2, 0.4, 0.6, 0.8]$, strictly unseen seeds `[1234, 5678, 9999]`, Strategies A, B, & ADAPTIVE. | `1a991a1` |
| **Budgeted Pilot** | `results/budgeted_pilot/` | `runs.csv` (3.3 KB)<br>`steps.csv` (51 KB)<br>`manifest.json` (1.5 KB) | 14 runs | $n=50, \alpha=0.4$, seeds `[42, 101]`, budgets: unbounded, 500 evals, 200 evals. | `ed28ef4` |
| **Analysis Tables** | `results/tables/` | 13 CSVs + 2 JSONs | N/A | Aggregated statistical battery, paired comparisons, scalability, regret summaries. | N/A |
| **Audit Evidence** | `results/audit/` | 2 CSVs + 2 JSONs | N/A | 40-claim catalog, metric reconciliation, integrity report, reproducibility report. | N/A |
| **Figures** | `results/figures/` | 12 PNG files | N/A | Publication plots `fig1` through `fig12`. | N/A |

### 6.2 Demonstrator vs. Saved Experiments
It is vital to distinguish:
1. **Interactive Route Demonstrator**: Runs dynamic scenarios on synthetic $n \in [10, 30]$ instances on demand in the browser for visual walkthrough.
2. **Saved Research Experiments**: The official, peer-reviewed empirical evidence consisting of 164 total batch runs across $n=50, 100, 200$ customer instances, recorded in `results/*/runs.csv`.

### 6.3 Metric Definitions & Calculations

| Metric Name | Symbol / Code Column | Mathematical Definition / Calculation | Unit | Aggregation Level | Source File |
|---|---|---|---|---|---|
| **Route Cost** | `final_cost` | $C(S_T) = \sum_{i} c(S_T[i], S_T[i+1])$ | Euclidean distance | Per-run scalar | `runs.csv` |
| **Cost Increase** | `cost_increase` | $C(S_T) - C(S_0)$ | Euclidean distance | Per-run scalar | `runs.csv` |
| **Computational Effort** | `total_computational_effort` | $\sum_{t=1}^T (\text{ins\_evals}_t + \text{two\_opt\_evals}_t + \text{overhead}_t)$ | Candidate evaluations | Per-run integer | `runs.csv` |
| **Update Response Time** | `total_response_time_ms` | Cumulative wall-clock time spent in update functions | Milliseconds (ms) | Per-run float | `runs.csv` |
| **Mean Disruption** | `mean_disruption` | $\frac{1}{T} \sum_{t=1}^T \left(1.0 - \frac{\|E(S_{t-1}) \cap E(S_t)\|}{\max(\|E(S_{t-1})\|, \|E(S_t)\|)}\right)$ | Normalized ratio $[0, 1]$ | Per-run float | `runs.csv` |
| **Max Disruption** | `max_disruption` | $\max_{t=1 \dots T} \delta(S_{t-1}, S_t)$ | Normalized ratio $[0, 1]$ | Per-run float | `runs.csv` |
| **Feasibility** | `all_feasible` | $\bigwedge_{t=1}^T (\text{valid\_cycle} \land \text{depot\_start\_end} \land \text{no\_duplicates})$ | Boolean (`True`/`False`) | Per-run boolean | `runs.csv` |
| **Absolute Regret** | `cost_regret` | $C(\text{ADAPTIVE}) - \min(C(\text{A}), C(\text{B}))$ | Euclidean distance | Per-instance float | `tables/held_out_triplet_instances.csv` |

### 6.4 The 90 Held-Out Runs & Regret Analysis
In Phase 8, 30 matched triplets (90 total runs) were executed on strictly unseen seeds `[1234, 5678, 9999]`.
- **Mean Cost A**: 1023.13
- **Mean Cost B**: 969.68
- **Mean Cost ADAPTIVE**: **944.71**
- **Mean Cost Hindsight Oracle**: 952.79
- **Mean Regret**: **-8.08** (Negative regret occurs because ADAPTIVE can switch between Strategy A and Strategy B dynamically at different steps of a single run, achieving a final tour shorter than either static policy).
- In **40.0% of held-out instances**, ADAPTIVE produced a tour shorter than both Always A and Always B simultaneously.

### 6.5 Discrepancies & Traceability Notes
- **Sidebar Test Count vs. Actual**: The sidebar in `app.py:L65` displays `"Regression Tests: 212 Passed"`. This string was written at the end of Phase 8. With Phase 9 UI tests (`tests/test_ui.py`, 14 tests) and smoke tests, the test suite now collects and passes **228 tests**. The UI text is an outdated static string rather than a dynamically queried count.
- **Audit Verdict Hardcoded in Sidebar**: The sidebar states `"Pre-Phase 9 Audit: PASS (40/40 claims)"` (`app.py:L64`), while the Audit Drawer in View 6 dynamically counts `len(df_recon)` and `(df_recon['status'] == 'PASS').sum()`. The dynamic view confirms the claims truthfully, but the sidebar is hardcoded.

---

## 7. Research Findings and Audit

### 7.1 Summary of Recorded Findings
1. **Low Dynamicity Advantage ($\alpha \le 0.2$)**: Strategy B achieved a 100% win rate (12/12 instances) with +10.86% mean cost improvement.
2. **Computational Explosion**: Strategy B required $49.1\times$ to $75.1\times$ more candidate evaluations ($p = 1.86 \times 10^{-9}$), causing a $110.8\times$ slower response time. At $n=200$, Strategy B required up to 1.22 million evaluations per run.
3. **Disruption Doubling**: Strategy B breaks twice as many edges as Strategy A ($\delta = 0.0794$ vs $0.0367$, $p = 1.86 \times 10^{-9}$).
4. **Diminishing Returns**: Capping Strategy B at 500 evaluations captures 96.3% of quality improvement while cutting evaluations by 32.3%.

### 7.2 The Myopic Local Search Trap
At high dynamicity ($\alpha \ge 0.6$):
- Strategy B was **inferior to Strategy A in 66.7% of runs** (-5.01% average penalty).
- *Root Cause*: Under the frozen-prefix rule, early 2-opt creates a tight tour through the 20%–40% initially known vertices. As the vehicle advances, it freezes edges along this loop, creating a spatial barrier that entraps future dynamic arrivals and forces expensive detour spikes. Pure greedy insertion preserves more spatial flexibility across the uncommitted suffix.

### 7.3 Independent Audit Verification
The pre-Phase 9 audit executed by [`scripts/audit_research_results.py`](file:///c:/Users/Admin/Desktop/college/sem5/daa/adaptive-route-optimization/adaptive-route-optimization/scripts/audit_research_results.py) verified:
- **40/40 Numerical Claims**: Recomputed pairwise t-tests, Wilcoxon tests, win rates, means, and standard deviations with zero failures (`results/audit/metric_reconciliation.csv`).
- **Rule 10 Input Parity**: Verified that across all pilot and held-out instances, Strategy A, Strategy B, and ADAPTIVE received identical coordinates, depot indices, and event sequences.
- **Data Partition Disjointness**: Verified that training seeds `[42, 101]`, validation seed `[777]`, and held-out test seeds `[1234, 5678, 9999]` have zero overlap.
- **Full Test Suite**: **228 tests passed** in 14.26 seconds with zero regressions.

---

## 8. UI/UX Recommendations

The following table provides actionable recommendations for every element in the Phase 9 dashboard, balancing academic clarity with user friendliness:

| Current Element | Current Purpose | Recommended Action | Reason | Research-Integrity Risk | Suggested User-Friendly Wording |
|---|---|---|---|---|---|
| **Sidebar Navigation (6 Views)** | Main multi-page radio selector | **SIMPLIFY** | 6 separate views dilute user attention. Research findings, charts, and results explorer have overlapping themes. | Low (No data changed) | Streamline into 3 top-level tabs: **1. Problem & Live Demo**, **2. Experimental Results & Trade-Offs**, **3. Audit & Reproducibility**. |
| **Sidebar "212 Passed" Label** | Provenance badge | **SIMPLIFY** | Static string is out of date (current test suite has 228 passing tests). | Zero | Update to dynamic query or change label to `"Automated Tests: 228 Passed (100%)"`. |
| **Unrevealed Customers (Grey Dots)** | Shows hidden future vertices in 2D plot | **SIMPLIFY** | Can mislead users into thinking the algorithm peeks into the future. | High if removed entirely (evaluators need to see ground truth) | Add a toggle checkbox: `[ ] Show ground-truth future arrivals (debug mode)`. Default to unchecked or add explicit subtitle: `"Faint dots show future arrivals (hidden from algorithm)"`. |
| **Interactive Mode Disclaimer Banner** | Warning that demo $\ne$ audited dataset | **KEEP** | Essential academic disclaimer preventing confusion between synthetic visual demo and saved benchmarks. | High if removed | Keep banner; reword to: `"Interactive Playground: Experimenting on live synthetic instances. View Tab 2 for audited research benchmarks."` |
| **Adaptive Selector Rationale Banner** | Explains why A or B was chosen at step $t$ | **KEEP** | Core demonstration of explainable AI / rule-based DAA principles. | High if removed | Keep prominent above the chart: `"Decision Rationale: [Text]"`. |
| **Decision-Time Features Inspector** | Raw JSON drawer of 11 state features | **MOVE TO ADVANCED SECTION** | Unformatted JSON blob overwhelms first-time viewers. | Low | Place inside a formatted 2-column key-value metrics table inside an expander labeled: `"Inspect Observable State Features at Step t"`. |
| **Experimental Results Multi-Select Filters** | Filters `runs.csv` by $n$, $\alpha$, strategy, seed | **KEEP** | Powerful proof of data provenance and interactive exploration. | Zero | Keep; add a `"Reset to Default"` button to quickly clear filters. |
| **Dataframe `use_container_width=True`** | Stretches tables to container width | **INVESTIGATE / FIX** | Deprecated in modern Streamlit; triggers warnings in logs. | Zero (pure syntax) | Replace with `width="stretch"` in `app.py:L317` and `L459`. |
| **Budget Cap Ablation Section in View 4** | Shows diminishing returns of 2-opt | **MOVE TO ADVANCED SECTION** | Placed below 4 charts; easily overlooked by scrolling. | Low | Group together with the Pareto frontier chart in an `"Algorithmic Efficiency & Budgets"` container. |
| **Synchronized Side-by-Side Replay** | Planned Phase 9 feature (currently missing) | **INVESTIGATE** | Evaluators cannot simultaneously watch Strategy A and Strategy B update side-by-side on the same screen. | Medium | Add a split-screen 2-column view showing Strategy A and Strategy B updating simultaneously on the same event sequence. |

### Minimal Coherent Navigation Structure for University Professor Demonstration
To present the project seamlessly to a university professor or examination panel without clutter:
- **Tab 1: Live Algorithmic Demonstrator**
  - Problem statement & dynamic TSP rules in an expandable banner.
  - Interactive scenario controls ($n$, $\alpha$, seed, strategy).
  - Synchronized side-by-side route trajectory visualizer (Frozen Prefix vs Uncommitted Suffix).
  - Live metric deltas ($\Delta \text{Cost}$, Candidate Evals, Disruption $\delta$).
  - Explainable Adaptive Selector decision rationale.
- **Tab 2: Empirical Research Results & Trade-Offs**
  - Interactive Pareto frontier (Quality vs. Computation).
  - Cost vs. Dynamicity curve (highlighting the Myopic Trap at $\alpha \ge 0.6$).
  - Filterable experimental dataset explorer reading directly from `results/held_out_matrix/runs.csv`.
- **Tab 3: Scientific Integrity & Audit Verification**
  - 40/40 Claim reconciliation table.
  - Parity & non-leakage check verification cards.
  - Exact CLI reproduction commands (`pytest`, `python scripts/audit_research_results.py`).

---

## 9. Evidence and Traceability

| Claim / Mechanism | Implementing File | Specific Identifier / Lines | Evidence & Code Expression |
|---|---|---|---|
| **Depot Definition** | `models/instance.py` | `Instance.cost()`, L44-L59 | `xi, yi = self.coords[i]; xj, yj = self.coords[j]; math.hypot(xi - xj, yi - yj)` |
| **Frozen-Prefix Invariance** | `simulation/simulator.py` | `Simulator._apply_strategy()`, L394, L409 | `full_route = state.reconstruct_route_from_suffix(updated_suffix)` |
| **Frozen-Prefix Check** | `ui/demonstrator.py` | `_simulate_all_steps()`, L151-L153 | `prefix_before = route_before.vertices[: prefix_len + 1]; prefix_after = updated_route.vertices[: prefix_len + 1]; prefix_preserved = (prefix_before == prefix_after)` |
| **Edge Disruption Metric** | `evaluation/metrics.py` | `compute_disruption()`, L47-L72 | `1.0 - len(intersection) / max_edges` |
| **Adaptive Decision Rules** | `algorithms/adaptive/selector.py` | `AdaptiveSelector.select()`, L87-L156 | Budget safety (L107), Degeneracy guard (L120), Low dynamicity $\alpha \le 0.20$ (L132), Late-stage $\ge 0.75$ (L139) |
| **Selection Overhead** | `algorithms/adaptive/selector.py` | `SelectorConfig.selection_overhead_evals`, L45 | `overhead_evaluations: int = 1` added to cumulative candidate evaluations. |
| **Hindsight Oracle** | `algorithms/adaptive/oracle.py` | `OracleEvaluator.compute_instance_oracle_and_regret()`, L46-L57 | Offline calculation: $\min(C_A, C_B)$; regret $= C_{\text{ADAPTIVE}} - C_{\text{ORACLE}}$. |
| **40-Claim Inventory** | `audit/inventory.py` | `CLAIMS_INVENTORY`, L60-L635 | 40 typed `Claim` instances covering Phase 6, Phase 7, and Phase 8. |
| **Input Parity (Rule 10)** | `audit/fairness.py` | `FairnessAuditor.audit_pilot_matrix_fairness()`, L24-L80 | Verifies `initial_cost` and `num_events` match identically across strategies on same seeds. |
| **Test Suite Passing** | `tests/` | 13 test files | **228 passed in 14.26s** (`pytest -v`). |

---

## 10. Report Verification & Conclusion

This audit was conducted strictly on the live repository. The following steps were executed and independently verified:
1. Re-verified Python environment: Python 3.13.5 with declared dependencies in `pyproject.toml` and `requirements.txt`.
2. Re-verified full test suite execution: **228 tests collected, 228 passed, 0 failed, 0 warnings**.
3. Re-verified Streamlit dashboard execution: Service running on `http://localhost:8501`.
4. Re-verified all 12 publication figures in `results/figures/` and confirmed full numerical correspondence with `results/audit/metric_reconciliation.csv`.
5. Confirmed that no application source code, experimental data files, or test suites were altered during this audit.

The existing implementation satisfies the core Gate Criteria of Phase 9. The code is modular, fully tested, scientifically rigorous, and ready for user-facing UI/UX enhancements.
