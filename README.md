# Adaptive Route Optimization in Dynamic Environments

An academic-grade, reproducible research framework and interactive dashboard for evaluating dynamic single-vehicle route repair strategies under strict frozen-prefix constraints and computational budgets.

---

## 1. Research Overview & Problem Formulation

In dynamic routing, an initial tour is planned over initially known customer requests. As the vehicle travels along its route, **new customer requests arrive dynamically** at discrete event time steps $t$.

### Core Operational Constraints

1. **Frozen-Prefix Rule**: Customer vertices already traversed by the vehicle along prefix $(0, p_1, \dots, p_f)$ are **strictly immutable**. The vehicle cannot reverse direction in time or un-serve committed customers.
2. **Uncommitted Suffix Re-optimization**: Only the remaining unvisited suffix $(p_f, \dots, 0)$ connecting the vehicle's current location back to the depot may be reordered.
3. **Computational Budgeting**: Dynamic real-time decisions must execute within tight per-step evaluation budgets ($B$).

### Mathematical Model

- **Metric Space**: Complete undirected graph $G = (V, E)$ embedded in Euclidean 2D coordinate space. Depot is vertex $0$.
- **Distance Metric**: Euclidean geometric distance $c(i, j) = \sqrt{(x_i - x_j)^2 + (y_i - y_j)^2}$ satisfying symmetry and the triangle inequality.
- **Tour Cost**: Total Euclidean cycle length $C(R) = \sum_{i=0}^{|R|-2} c(R[i], R[i+1])$ starting and ending at depot $0$.
- **Dynamicity Level ($\alpha$)**: Fraction of total customer requests revealed dynamically during transit:
  $$\alpha = \frac{n - |V_0 \setminus \{0\}|}{n} \in [0.0, 1.0]$$
- **Route Disruption ($\delta$)**: Normalized edge turnover measuring trajectory instability between successive dynamic states:
  $$\delta(S_{t-1}, S_t) = 1.0 - \frac{|E(S_{t-1}) \cap E(S_t)|}{\max(|E(S_{t-1})|, |E(S_t)|)} \in [0.0, 1.0]$$

> **Application Neutrality**: Delivery and logistics scenarios serve as intuitive interpretations. The underlying computational model is an abstract dynamic graph routing problem on Euclidean metric space. No physical road networks, traffic congestion APIs, or GPS tracking are modeled.

---

## 2. Evaluated Strategies

| Strategy | Algorithmic Mechanism | Time / Evaluation Complexity | Primary Trade-Off |
|---|---|---|---|
| **Strategy A (Greedy)** | Cheapest Insertion of newly arrived vertices into the uncommitted suffix. | $O(m)$ candidate checks per vertex | Ultra-fast ($<1$ ms), minimal edge disruption ($\delta \approx 0.03$), but builds suboptimal tours. |
| **Strategy B (2-opt)** | Cheapest Insertion followed by First-Improvement 2-opt on the suffix. | $O(m^2)$ evaluations per pass | High tour quality at low dynamicity ($\alpha \le 0.2$), but heavy computation ($O(m^2)$) and prone to the high-dynamicity entrapment trap. |
| **Strategy C (Destroy-Repair)** | Suffix Ruin-and-Recreate: remove a subset of vertices and reinsert greedily. | $O(k \cdot m)$ evaluations per step | Escapes local minima without full pairwise edge swaps; balanced cost-effort trade-off. |
| **ADAPTIVE v2 (A/B)** | Interpretable meta-heuristic choosing between Strategy A and Strategy B using observable state features. | $O(1)$ decision overhead (+1 evaluation) | Automatically balances route quality and computational budget while avoiding the entrapment trap. |
| **ADAPTIVE v3 (A/B/C)** | Interpretable, budget-aware three-strategy selector with ruin-and-recreate and fallback cascade. | $O(1)$ decision overhead (+1 evaluation) | Dynamically invokes LNS restructuring for burst arrivals and cost spikes while enforcing strict budget compliance. |

### Corrected Adaptive Selector Logic (Rule v2)

In Stage 4, an empirical anomaly was discovered: under bounded budgets ($B=100$ and $B=50$), the original Adaptive selector (Rule v1) defaulted to Strategy A on 100% of steps because it checked if an estimated *exhaustive full pass* ($m(m-1)/2 \approx 464$ evals) exceeded the budget.

**Rule v2 Correction (Stage 5B)**:
Replaces the full-pass test with an **insertion + minimal 2-opt threshold**:
$$\text{Required Budget} = k \cdot \text{uncommitted} + \frac{k(k+1)}{2} + \text{min\_2opt\_budget} \quad (\text{where } \text{min\_2opt\_budget} = 10)$$
If the remaining per-step budget covers insertion plus at least 10 two-opt evaluations, Strategy B is safely authorized to perform budget-capped partial local search. In Stage 5B validation, Rule v2 matched Strategy B on uniform topologies (saving 3.62% cost) and outperformed Strategy B by **56.58 cost units** on clustered topologies by avoiding early entrapment.

### Three-Strategy Adaptive Selection Architecture (Adaptive v3, Stage 7)

Adaptive v3 extends the deterministic rule-based framework to dynamically evaluate **Strategy C (Destroy-and-Repair)** alongside Strategies A and B.

#### 1. Observable State Features (Zero Future Information Leakage)
At dynamic arrival step $t$, the selector inspects only:
- $m$: Number of customer vertices currently in the uncommitted suffix (`uncommitted_count`).
- $|\Delta_t|$: Number of customers revealed in the current arrival event (`burst_arrival_count`).
- $|\Delta_t| / n$: Ratio of arriving customers relative to total problem size (`burst_arrival_ratio`).
- $\alpha$: Level of dynamicity (`dynamicity`).
- $r_t = |V_t \setminus \{0\}| / n$: Proportion of customer requests revealed so far (`revealed_ratio`).
- $B_{\text{rem}}$: Remaining evaluation budget allocated for step $t$ (`budget_remaining`).
- $\Delta C_{\text{rel}} = (C_t - C_{t-1}) / C_{t-1}$: Immediate relative tour cost increase (`relative_cost_change`).
- $E_{\text{ins}}$: Estimated evaluations for cheapest insertion: $k \cdot m + k(k+1)/2$.
- $E_{\text{repair}}$: Estimated evaluations for destroy-and-repair: $\lceil \gamma \cdot m \rceil \cdot m$.

#### 2. Exact Decision Rules & Selection Conditions
```
1. Degeneracy & Structural Guards:
   - If m < 4: Suffix too small for local search -> Select Strategy A
   - If m < min_suffix_for_c (6): Strategy C ineligible -> Consider Strategy B or A

2. Restructuring Need Evaluation (Strategy C Preference):
   - Condition C1 (Arrival Shock): |Δ_t| >= burst_arrival_threshold (2) OR burst_arrival_ratio >= 0.15
   - Condition C2 (Mid-Stage High Dynamism): α >= 0.40 AND revealed_ratio in [0.35, 0.85]
   - Condition C3 (Route Deterioration Spike): relative_cost_change >= cost_increase_threshold (0.05)

3. Local Search Evaluation (Strategy B Preference):
   - Condition B1 (Low Dynamism): α <= low_dynamicity_threshold (0.20)
   - Condition B2 (Late Stage): revealed_ratio >= late_stage_revealed_threshold (0.75)

4. Budget-Aware Fallback Cascade:
   - If Strategy C is indicated:
     Check: E_ins + E_repair <= B_rem
     If affordable -> Select Strategy C
     Else if E_ins + min_2opt_budget (10) <= B_rem -> Cascade to Strategy B
     Else -> Safe fallback to Strategy A
   - If Strategy B is indicated:
     Check: E_ins + min_2opt_budget (10) <= B_rem
     If affordable -> Select Strategy B
     Else -> Safe fallback to Strategy A
   - Otherwise -> Select Strategy A (budget conservation & entrapment avoidance)
```

#### 3. Configurable Thresholds
| Parameter | Default | Theoretical / Empirical Derivation |
|---|---|---|
| `version` | `"v2"` (backward compatible) or `"v3"` | Selector algorithm generation |
| `min_suffix_for_c` | `6` | Suffix must contain sufficient vertices for removal subset $k_d \ge 2$ |
| `c_destroy_fraction` | `0.25` | Standard LNS ruin fraction ($25\%$ of suffix removed) |
| `burst_arrival_threshold` | `2` | Batch arrival requiring multi-point structural healing |
| `burst_arrival_ratio` | `0.15` | Proportional arrival burst ($\ge 15\%$ of problem size) |
| `high_dynamicity_c_threshold` | `0.40` | Dynamism threshold where single-edge 2-opt is vulnerable to entrapment |
| `c_mid_stage_min` | `0.35` | Lower bound of mid-stage diversification window |
| `c_mid_stage_max` | `0.85` | Upper bound of mid-stage diversification window |
| `cost_increase_threshold` | `0.05` | Sudden tour length spike ($\ge +5\%$) indicating disruptive geometry |
| `min_2opt_budget` | `10` | Minimum evaluations required for partial first-improvement 2-opt |
| `low_dynamicity_threshold` | `0.20` | Stage 4 finding: 2-opt achieves 100% win rate when $\alpha \le 0.20$ |
| `late_stage_revealed_threshold` | `0.75` | Trajectory entrapment risk drops as fewer unrevealed nodes remain |

---

## 3. Supported Benchmarks & Instance Generators

### Synthetic Distributions
1. **Uniform (`Instance.generate_random`)**: Customer coordinates distributed uniformly in $[0.05, 0.95]^2$ with central depot.
2. **Clustered (`Instance.generate_clustered`)**: Customers clustered around spatial centers with configurable cluster spread ($\sigma$).
3. **Mixed (`Instance.generate_mixed`)**: Combination of clustered cores and uniformly dispersed peripheral customers.

### Standard TSPLIB Benchmarks
Standard TSPLIB benchmark instances with exact parsing and continuous Euclidean costs:
- **`berlin52`** (52 total vertices: 1 depot + 51 customers; $L_2$ Euclidean distance)
- **`eil51`** (51 total vertices: 1 depot + 50 customers; $L_2$ Euclidean distance)

---

## 4. Repository Structure

```
adaptive-route-optimization/
├── configs/                              # Experiment configuration matrices
│   ├── stage4_full_matrix.json           # 14-condition, 280-run benchmark matrix
│   ├── stage5_adaptive_validation.json   # 48-run targeted validation matrix
│   └── stage7_adaptive_c.json            # 18-condition, 450-run three-strategy matrix
├── data/                                 # TSPLIB benchmark files (berlin52, eil51)
├── results/                              # Audited experiment records & analysis
│   ├── stage4_full_matrix/               # 280 completed runs (runs.csv, steps.csv)
│   ├── stage5_adaptive_validation/       # 48 validation runs (runs.csv, steps.csv)
│   ├── stage5_analysis/                  # Stage 5 figures and tables
│   ├── stage7_adaptive_c/                # 450 completed runs (runs.csv, steps.csv, summary.csv)
│   │   ├── figures/                      # 4 publication-grade comparative figures
│   │   ├── detailed_condition_summary.csv # Per-condition metrics across all 5 strategies
│   │   ├── overall_strategy_aggregates.csv # Global means, standard deviations, and medians
│   │   └── paired_hypothesis_tests.csv   # Paired t-tests, Wilcoxon tests, and Cohen's d
│   └── stage6_acceptance_report.md       # Stage 6 integration acceptance report
├── scripts/                              # CLI executables & analysis pipelines
│   ├── run_experiments.py                # Reproducible experiment runner CLI
│   ├── generate_figures.py               # Stage 5 figure generator
│   ├── analyze_stage7_adaptive_c.py      # Stage 7 statistical analysis pipeline
│   ├── generate_stage7_figures.py        # Stage 7 figure generator
│   ├── audit_research_results.py         # 40-claim research audit verification
│   └── run_dashboard.py                  # Streamlit dashboard launcher
├── src/adaptive_route_optimization/      # Production package
│   ├── algorithms/                       # Strategies A, B, C, Adaptive v2, Adaptive v3
│   │   ├── adaptive/                     # State features & rule-based selectors
│   │   ├── local_search/                 # Suffix-constrained 2-opt
│   │   └── repair/                       # Insertion & Destroy-Repair (LNS)
│   ├── benchmarks/                       # TSPLIB parser & scenario adapters
│   ├── models/                           # Instance, Route, and Distributions
│   ├── simulation/                       # Event simulator & frozen-prefix state
│   └── ui/                               # Streamlit application & visualizers
└── tests/                                # 354 automated unit & integration tests
```

---

## 5. Quick Start & Execution Guide

### Prerequisites & Installation

```bash
# 1. Clone repository and navigate to root
cd adaptive-route-optimization

# 2. Activate virtual environment
.\.venv\Scripts\activate   # Windows PowerShell
# source .venv/bin/activate  # Linux / macOS

# 3. Install dependencies in editable mode
pip install -e .
```

### Running Automated Tests & Research Audit

```bash
# Run full unit and integration test suite (354 passing tests)
pytest -v

# Run independent research audit (40/40 claims verified, 100% pass)
python scripts/audit_research_results.py
```

### Launching the Interactive Streamlit Dashboard

```bash
python scripts/run_dashboard.py --port 8501
```
The dashboard provides four comprehensive views:
1. **Overview**: Formal mathematical formulation, operational constraints, strategy complexity, and Adaptive v3 fallback architecture.
2. **Route Demonstration**: Step-by-step interactive 2D Euclidean route visualizer showing frozen prefixes (solid green), uncommitted suffixes (dashed blue), incoming arrivals (orange stars), and head-to-head strategy comparisons among Strategies A, B, C, Adaptive v2, and Adaptive v3.
3. **Algorithm Comparison**: Saved results explorer across Stage 4 (280 runs), Stage 5B (48 runs), and Stage 7 (450 runs), Pareto trade-offs, budget sensitivity, and paired statistical significance tables.
4. **Research Evidence**: Audited findings, limitation statements, Stage 7 empirical conclusions, and claim reconciliation tables.

### Reproducing Experiments & Generating Figures

```bash
# Execute Stage 7 three-strategy benchmark campaign (450 runs)
python scripts/run_experiments.py --config configs/stage7_adaptive_c.json

# Run Stage 7 statistical analysis & generate hypothesis test tables
python scripts/analyze_stage7_adaptive_c.py

# Generate Stage 7 publication-quality figures
python scripts/generate_stage7_figures.py
```

---

## 6. Key Empirical Findings

1. **Decisive Superiority of Local Search at Low Dynamicity ($\alpha \le 0.2$)**:
   - Strategy B (2-opt) and Strategy C (Destroy-Repair) achieved **+10% to +14% lower route cost** than pure greedy insertion across uniform and clustered topologies.
   - When 80%–90% of requests are known initially, suffix local search constructs an efficient global tour foundation.
2. **The Myopic Entrapment Trap under High Dynamicity ($\alpha \ge 0.6$)**:
   - Under the frozen-prefix rule, early aggressive local search locks the vehicle into a spatial trajectory that traps future arrivals.
   - On instances with late arrivals, Strategy B was **inferior to Strategy A in up to 66.7% of high-dynamicity conditions**, requiring costly detour loops. Pure greedy insertion preserves more spatial flexibility.
3. **Diminishing Returns of Evaluation Budgets**:
   - Capping suffix repair at $B=100$ or $B=500$ evaluations captures **over 95% of quality gains** while eliminating extreme computational runtime tails ($>1.2 \times 10^6$ evaluations).
4. **Adaptive Rule v2 Validation**:
   - Under bounded budgets ($B=100$), Rule v2 enables partial 2-opt, matching Strategy B on uniform instances (saving 3.62% cost) and outperforming Strategy B by **56.58 cost units** on clustered instances by avoiding entrapment.
5. **Stage 7 Three-Strategy Campaign & Ruin-and-Recreate (450 Runs)**:
   - **Quality Ranking Across 90 Paired Instances**:
     1. **ADAPTIVE v2**: Mean cost = **1457.69**, Effort = **3,040 evals**
     2. **ADAPTIVE v3**: Mean cost = **1464.99**, Effort = **11,669 evals**
     3. **Fixed Strategy B**: Mean cost = **1470.76**, Effort = **4,052 evals**
     4. **Fixed Strategy C**: Mean cost = **1492.07**, Effort = **17,401 evals**
     5. **Fixed Strategy A**: Mean cost = **1496.37**, Effort = **581 evals**
   - **Where Strategy C Wins**: In unconstrained or generous budget regimes on clustered networks (`syn_clustered_n50_d0.4_unbounded`), Strategy C achieved **306.11** mean cost, beating Strategy B (317.52) and Strategy A (321.03), because ruin-and-recreate untangles inter-cluster connections that 2-opt cannot cross.
   - **Statistical Significance**: Adaptive v2, Adaptive v3, and Strategy B all significantly outperform Strategy A ($p < 0.001$, paired t-test and Wilcoxon signed-rank test). The difference between Adaptive v3 and Adaptive v2 (+7.30 cost units) is statistically insignificant after Holm-Bonferroni correction ($p = 0.148$, Wilcoxon $p = 0.112$).
   - **Strict Invariance**: 100% frozen-prefix preservation and zero evaluation-budget violations across all 7,250 dynamic steps.

---

## 7. Methodological Limitations & Future Work

- **Metric Space**: Evaluated on 2D Euclidean continuous coordinates; real-world turn restrictions, one-way streets, and traffic congestion are not modeled.
- **Problem Formulation**: Single-vehicle dynamic TSP; vehicle capacity limits (CVRP) and customer time windows (VRPTW) are outside project scope.
- **Sample Size Scope**: The completed Stage 4 campaign used $N=5$ seeds per condition (280 total runs). While paired tests demonstrate consistent directional patterns, definitive confirmation requires the proposed 840-run robustness matrix ($N=15$ seeds).
