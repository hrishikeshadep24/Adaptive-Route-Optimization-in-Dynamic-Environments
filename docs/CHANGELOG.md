# Changelog

## [Unreleased]
- Repository initialized with structure
- AGENTS.md created with project rules
- MASTER_BLUEPRINT.md created
- LITERATURE_NOTES.md created
- PHASE_PLAN.md created

## [Phase 2 Complete] - 2026-10-10
### Formal Specification (Algorithmic & Mathematical)
- **docs/RESEARCH_SPEC.md**: Complete formal problem specification
  - Graph G=(V,E) with Euclidean cost c(i,j), depot at vertex 0
  - Route definition, total cost, dynamic state V_t, event model Δ_t
  - Initial solution (nearest-neighbor), update operator U(S_t, G_{t+1})
  - Feasibility constraints for single-route dynamic TSP
  - Dynamicity α = |V\V₀|/|V\{0\}|
  - Route disruption: edge-based normalized δ ∈ [0,1] with justification
  - Frozen-prefix rule: immutable traversed prefix, 1 vertex advance per step
  - Computational budget: placeholder (fixed eval count vs wall-clock, decision deferred)
  - All evaluation metrics defined
  - Single-route TSP confirmed as core; multi-route VRP as optional extension
  - Edge cases: empty route, duplicate vertex, depot event, batch events, zero-cost edges

- **docs/NOTATION.md**: Complete symbol table for all variables, sets, functions, metrics

- **docs/PSEUDOCODE.md**: Pseudocode with time/space complexity and candidate evaluation counts
  - Nearest-neighbor construction: O(n²), n(n+1)/2 evals
  - Cheapest-insertion repair: O(m), m evals per vertex
  - 2-opt local search: O(m²) per pass, m(m-3)/2 evals per pass
  - Candidate evaluation precisely defined for computational effort metric

- **docs/HAND_WORKED_EXAMPLE.md**: Fully traceable 10-node example
  - Explicit coordinates, distance matrix (6 decimal precision)
  - Initial NN route: (0,1,4,2,3,0) cost=18, 10 evals
  - Event Δ₀={5}: insertion at position 2, delta=2, cost=20, 5 evals
  - 2-opt: 9 pairs examined, no improvement, route unchanged
  - Disruption δ = 1/3, cumulative evals=24

- **tests/test_spec_examples.py**: Executable verification of all hand-worked numbers
  - 12 test functions covering costs, disruptions, eval counts, feasibility, distance spot-checks

- **docs/OPEN_QUESTIONS.md**: Updated with all Phase 2 resolutions and remaining deferrals
  - 5 Phase 2 questions resolved with explicit defaults
  - 10+ questions deferred to Phases 6-8 with recommended defaults
  - Additional clarifications (frozen prefix, 2-opt variant, numerical stability)

- **Phase 2 Gate**: 10-node example manually traceable and verified by tests

## [Phase 3 Complete] - 2026-10-10
### Core Routing Engine (Static)
- **src/models/instance.py**: Instance model with coordinates, cost matrix, Euclidean distances
  - `Instance` dataclass with frozen coordinates array
  - `cost(i,j)` method for Euclidean distance (symmetric, triangle inequality)
  - `cost_matrix()` for full O(n²) matrix
  - `generate_random(n, seed, ...)` for deterministic synthetic instances
  - `subset()` and `get_subinstance()` for dynamic vertex revelation
  - Minimum separation enforcement to avoid zero-cost edges

- **src/models/route.py**: Route representation with cost calculation and feasibility validation
  - `Route` frozen dataclass with tuple of vertices (starts/ends at depot)
  - Constructor enforces validity (depot at ends, no duplicates, no depot in middle)
  - `cost(instance)` computes total route cost C(R)
  - `edges()` returns frozenset of edges for disruption calculation
  - `is_feasible(instance, required_vertices)` validates against spec
  - `with_insertion(position, vertex)` and `with_2opt_swap(i,j)` for immutable updates
  - `validate_route()` helper returns (bool, error_list)

- **src/algorithms/baseline/nearest_neighbor.py**: Deterministic NN construction
  - `nearest_neighbor(instance, vertex_subset)` returns `NNResult(route, candidate_evaluations)`
  - Greedy: start at depot, repeatedly visit nearest unvisited vertex
  - Deterministic tie-breaking by vertex index
  - O(n²) time, O(n) space, n(n+1)/2 candidate evaluations
  - Supports vertex_subset for dynamic initial solutions

- **src/algorithms/baseline/exact.py**: Exact TSP solver for verification (n ≤ 8)
  - `exact_tsp(instance, vertex_subset, max_vertices=8)` returns `ExactResult(route, cost, candidate_evaluations)`
  - Brute-force enumeration of all permutations
  - n! candidate evaluations
  - Used ONLY for verifying heuristics on tiny instances

- **src/evaluation/metrics.py**: All metrics from RESEARCH_SPEC.md
  - `compute_disruption(route_prev, route_curr)`: edge-based δ = 1 - |E_t ∩ E_{t+1}| / max(|E_t|, |E_{t+1}|)
  - `check_feasibility(route, instance, required_vertices)`: boolean validation
  - `evaluate_route(...)`: computes RouteMetrics (cost, disruption, feasible, effort, time)
  - `TimedOperation` context manager for wall-clock timing and evaluation counting
  - `ExperimentMetrics` for aggregated run statistics (mean/max disruption, etc.)

- **src/evaluation/plotting.py**: Route plotting independent of final UI
  - `plot_route(instance, route, ax)`: single route with depot/customers
  - `plot_route_comparison(instance, routes, labels)`: side-by-side comparison
  - `plot_cost_convergence(costs, labels)`: cost over time steps
  - `plot_disruption_over_time(disruptions)`: disruption curve

- **tests/test_models.py**: 28 unit tests covering
  - Instance creation, cost, subset, random generation, edge cases
  - Route construction, cost, edges, feasibility, insertion, 2-opt, validation
  - Edge cases: empty initial route, 1/2 customers, duplicate coords, zero-cost edges

- **tests/test_baseline.py**: 18 tests covering
  - NN construction, tie-breaking, determinism, vertex subsets, evaluation counts
  - Exact solver: optimal verification, determinism, subsets, evaluation counts
  - Exact vs heuristic comparison on 20 random seeds (n=5): NN cost ≥ exact cost always
  - Exact vs heuristic on known cases (line, square)

- **tests/test_evaluation.py**: 15 tests covering
  - Disruption: identical (0), completely different (1), partial (1/3), different lengths (2/3)
  - Feasibility: valid, missing vertex, extra vertex, custom required sets
  - Route evaluation: initial (disruption=0), with prev, infeasible
  - TimedOperation: basic, multiple adds, negative error
  - ExperimentMetrics aggregation
  - Plotting smoke tests (Agg backend)

- **Package restructuring**: `src/adaptive_route_optimization/` layout for editable install

- **Phase 3 Gate**: All baseline tests pass; costs independently verified; exact-vs-heuristic comparison works on small instances

## [Phase 4 Complete] - 2026-10-10
### Local Search and Repair Algorithms
- **src/algorithms/local_search/two_opt.py**: 2-opt local search (first-improvement)
  - `two_opt(instance, route, max_passes, max_evaluations)` returns `TwoOptResult`
  - First-improvement strategy: applies first improving move, restarts scan
  - Deterministic tie-breaking: earliest (i, j) in lexicographic order
  - Numerical stability: EPS = 1e-9 threshold (delta < -EPS required)
  - Candidate evaluations: one per pair examined (not per improving move)
  - Budget controls: max_passes and max_evaluations limits
  - Time: O(m²) per pass, Space: O(1) extra

- **src/algorithms/repair/insertion.py**: Greedy Insertion Repair (Strategy A)
  - `cheapest_insertion(instance, route, new_vertices)` returns `InsertionResult`
  - For each new vertex, evaluates all m insertion positions
  - Cost delta = c(u, v) + c(v, w) - c(u, w)
  - Deterministic tie-breaking: lowest position index wins
  - Candidate evaluations: m per new vertex
  - `greedy_insertion_repair`: Strategy A wrapper, processes vertices in sorted order

- **src/algorithms/repair/insertion_two_opt.py**: Insertion + 2-opt Repair (Strategy B)
  - `insertion_then_two_opt(instance, route, new_vertices, ...)` returns `InsertionTwoOptResult`
  - Phase 1: Apply greedy insertion for all new vertices
  - Phase 2: Run 2-opt to local optimum (or budget limit)
  - Combined candidate evaluations: insertion + 2-opt
  - Budget controls: max_passes and max_evaluations (shared budget)
  - `strategy_b_repair`: Strategy B with defaults (run to local optimum)

- **tests/test_local_search.py**: 13 unit tests covering
  - No-improvement case, crossed route improvement, first-improvement strategy
  - Determinism, tie-breaking, max_passes/max_evaluations budget limits
  - Edge cases: empty route, 1/2/3 customers, numerical stability (EPS)
  - Hand-worked example verification: 9 evaluations, 0 moves on Phase 2 example

- **tests/test_repair.py**: 19 unit tests covering
  - Strategy A: single/batch vertex insertion, deterministic tie-breaking, empty route
  - Strategy B: insertion+2-opt, hand-worked example verification (9 evals, 0 moves)
  - Strategy A vs B on same event: both feasible, Strategy B cost ≤ Strategy A cost
  - Budget limits: max_evaluations (shared), max_passes
  - Reproducibility: same seed → same results, same instance+event → same results
  - Computational effort verification: insertion evals = 4+5, 2-opt evals ≥ 9
  - Edge cases: duplicate vertices, depot insertion, result structure validation

- **Algorithm-level instrumentation**:
  - Every algorithm tracks candidate_evaluations, accepted_moves, passes
  - 2-opt evaluates m(m-3)/2 pairs per pass (skips depot-depot)
  - Insertion evaluates m positions per new vertex

- **Phase 4 Gate**: For the same dynamic event both repair methods yield valid routes and reproducible cost/time measurements
  - Verified by `test_strategy_a_vs_b_same_event` (20 random seeds)
  - Verified by `test_repair_same_instance_event_sequence`
  - Hand-worked example reproduced exactly in `test_insertion_two_opt_hand_worked_example`

## [Phase 5 Complete] - 2026-10-11
### Dynamic Simulation Engine
- **src/simulation/state.py**: Dynamic state model with frozen-prefix support
  - `DynamicState` dataclass tracking V_t, frozen_prefix_length, current_route, time_step
  - `create_initial_state()` builds initial route via nearest-neighbor on V_0
  - `get_uncommitted_suffix_vertices()` returns suffix for repair (respects frozen prefix)
  - `advance_frozen_prefix(steps)` advances vehicle position along route
  - `reconstruct_route_from_suffix()` combines frozen prefix + updated suffix
  - Full validation of state consistency

- **src/simulation/events.py**: Deterministic event generation
  - `EventConfig` with total_vertices, initial_known_count/dynamicity, events_per_step, seed, vertex_order
  - `EventGenerator` class for reproducible event sequences
  - `generate_event_sequence()` convenience function
  - Supports single-vertex and batch events, multiple revelation orders (random, index, distance)
  - Deterministic: same seed → identical V_0 and Δ_t sequence

- **src/simulation/simulator.py**: Event-driven simulator
  - `Simulator` class runs complete dynamic routing experiments
  - `Strategy.A` (greedy insertion) and `Strategy.B` (insertion + 2-opt)
  - `run_both_strategies()` executes both on IDENTICAL instance and event sequence
  - Frozen-prefix enforcement: only uncommitted suffix modified during repair
  - Per-step metrics: route cost, disruption, computational effort, response time
  - `SimulationResult` with full trajectory and aggregate statistics

- **src/simulation/replay.py**: Exact reproduction system
  - `ReplayConfig` captures all parameters for exact reproduction
  - `replay_from_original()` re-runs with same instance + event sequence
  - `verify_replay_exact()` confirms byte-for-byte identical results
  - Phase 5 Gate satisfied: complete run replayable from seed/config

- **src/simulation/logging.py**: Comprehensive event/route state logging
  - `SimulationLogger` captures every step: event, routes, metrics, repair details
  - `SimulationLog` with JSON serialization and CSV export
  - Structured output for analysis pipeline

- **src/simulation/animation.py**: Debugging visualization prototype
  - `animate_route_state()` creates matplotlib animation of route evolution
  - `plot_route_evolution()` static plot with cost/disruption curves
  - Agg backend compatible for headless testing

- **tests/test_simulation.py**: 42 comprehensive tests
  - DynamicState: frozen prefix, suffix extraction, reconstruction, validation
  - EventGenerator: determinism, dynamicity levels, batch events, vertex orders
  - Simulator: both strategies, frozen-prefix enforcement, same instance/events
  - Replay: exact match verification, step-by-step, both strategies
  - Logging: captures all steps, JSON/CSV export
  - Animation: frame creation smoke test
  - Edge cases: empty route, 1 vertex, full freeze, batch events
  - Adversarial: duplicate coords, zero-cost edges
  - Hand-worked example reproduction (Phase 2 example)
  - Deterministic full runs across multiple seeds

- **Phase 5 Gate**: "a complete run can be replayed exactly with the same event sequence and results from the same seed" — VERIFIED
  - `test_replay_exact_match`: replay matches original byte-for-byte
  - `test_replay_step_by_step`: every intermediate state matches
  - `test_replay_different_strategies`: both strategies replay exactly
  - `test_deterministic_full_run`: 20 seeds produce identical results
  - `test_hand_worked_example_reproduction`: Phase 2 example reproduced exactly

## [Phase 6 Complete] - 2026-10-21
### Controlled Experimental Framework
- **src/algorithms/local_search/two_opt.py**: Suffix-aware 2-opt support
  - Added `min_i: int = 0` to preserve immutable frozen prefix $(0, \dots, p_f)$
  - Preserves 100% backward compatibility and strictly respects frozen-prefix rule

- **src/simulation/simulator.py**: Integrated budget controls & suffix 2-opt
  - `Simulator` accepts `max_passes` and `max_evaluations`
  - Eliminates duplicate vertex / route reconstruction slicing bug
  - Both strategies run to budget cutoff or local optimum

- **src/adaptive_route_optimization/experiments/schema.py**: Structured schemas
  - `BudgetType`, `BudgetConfig`, `ConditionConfig`, `ExperimentConfig`
  - `RunRecord`: standard schema for single simulation run with full metric recording
  - `StepRecord`: standard schema for step-by-step dynamic tracking
  - JSON serialization, loading, and strict validation

- **src/adaptive_route_optimization/experiments/manifest.py**: Reproducibility manifest
  - Captures Git commit hash, clean tree status, Python version, platform/hardware, package versions
  - Tracks total conditions, planned runs, completed runs, failure logs, and output paths

- **src/adaptive_route_optimization/experiments/runner.py**: Batch experiment runner
  - Executes condition matrix $\times$ seeds $\times$ strategies
  - Strictly guarantees Rule 10: identical instance and dynamic event sequences across strategies
  - Failure recovery: logs failed conditions and continues batch execution
  - Structured output generation: `runs.csv`, `steps.csv`, `runs.json`, `manifest.json`

- **src/adaptive_route_optimization/experiments/reproduce.py**: Reproducibility system
  - CLI and API `verify_reproducibility` to re-execute from manifest
  - Verifies exact floating-point and integer equality across runs

- **configs/pilot_matrix.json** & **configs/budgeted_pilot.json**: Standard experiment configs
  - Sizes $n \in \{50, 100, 200\}$, dynamicity $\alpha \in \{0.1, 0.2, 0.4, 0.6, 0.8\}$
  - Budget cap variations (200 evals, 500 evals, unbounded)

- **tests/test_experiments.py**: 12 unit & integration tests
  - Schema roundtrip, condition validation, manifest capture
  - Suffix 2-opt prefix preservation
  - Batch runner execution, identical instance parity (Rule 10), budget enforcement
  - Manifest reproducibility verification
  - Adversarial edge cases: zero dynamicity ($\alpha = 0$), $n=2$ minimal instance, failure recovery

- **Phase 6 Gate**: "one command runs a full experiment matrix and produces raw results with no manual intervention" — VERIFIED
  - Executed 60-run pilot matrix in 141.13s with zero failures
  - Re-run from manifest confirmed byte-for-byte exact reproducibility with 0 discrepancies

## [Phase 7 Complete] - 2026-10-21
### Research Analysis & Ablation
- **src/adaptive_route_optimization/analysis/validator.py**: Rigorous data validation
  - Validates Non-Negotiable Rule 10 parity (identical initial cost and event count between strategies)
  - Checks schema completeness, range boundaries (cost > 0, disruption in [0,1]), feasibility, null checks

- **src/adaptive_route_optimization/analysis/metrics.py**: Metrics aggregation & paired matching
  - `compute_relative_improvement`: standardized percentage improvement formula: $((A - B)/A) \times 100$
  - `build_paired_dataset`: strictly matches Strategy A and B on identical (condition, seed)
  - Aggregates by condition, problem size ($n \in \{50, 100, 200\}$), dynamicity ($\alpha \in \{0.1, 0.2, 0.4, 0.6, 0.8\}$), and per-event steps

- **src/adaptive_route_optimization/analysis/statistical.py**: Hypothesis testing & effect sizes
  - Normality checks via Shapiro-Wilk test
  - Parametric paired t-test with Cohen's $d_z$ effect size
  - Non-parametric Wilcoxon signed-rank test with matched-pairs rank-biserial correlation $r$
  - Deterministic 95% bootstrap confidence intervals for mean difference ($10,000$ iterations)

- **src/adaptive_route_optimization/analysis/ablation.py**: Component & budget ablation
  - `analyze_component_ablation`: isolates the marginal cost and benefit of adding 2-opt to cheapest insertion
  - `analyze_dynamicity_regime_ablation`: segments performance across Low ($\alpha \le 0.2$), Moderate ($\alpha = 0.4$), and High ($\alpha \ge 0.6$) regimes
  - `analyze_budget_cap_ablation`: evaluates the trade-off of 200 vs 500 evals/update vs unbounded search

- **src/adaptive_route_optimization/analysis/visualizer.py**: Publication figures (Agg backend)
  - Generated all 9 publication figures saved to `results/figures/` (dpi=200):
    1. `fig1_dynamicity_vs_cost.png`
    2. `fig2_dynamicity_vs_response_time.png`
    3. `fig3_size_vs_cost.png`
    4. `fig4_size_vs_runtime.png`
    5. `fig5_evals_vs_cost_improvement.png`
    6. `fig6_paired_comparison.png`
    7. `fig7_route_disruption.png`
    8. `fig8_quality_vs_computation_tradeoff.png`
    9. `fig9_budget_ablation.png`

- **src/adaptive_route_optimization/analysis/pipeline.py** & **cli.py**: Automated analysis pipeline
  - Full CLI and API tool generating summary tables in `results/tables/`:
    `summary_by_condition.csv`, `paired_strategy_comparison.csv`, `statistical_battery.csv`, `scalability_by_size.csv`, `scalability_by_dynamicity.csv`, `ablation_by_condition.csv`, `ablation_by_regime.csv`, `step_level_statistics.csv`, `budget_ablation.csv`, `analysis_summary.json`

- **docs/RESEARCH_FINDINGS.md**: Formal research report
  - Comprehensive documentation of all comparative findings, limitations, and regime breakdowns

- **tests/test_analysis.py**: 13 unit and integration tests
  - Validator tests (clean data, Rule 10 parity violations, infeasibility, out-of-bound disruption)
  - Metric calculations, paired construction, statistical battery, ablation summaries, plot generation, end-to-end pipeline

- **Phase 7 Gate**: ">=3 evidence-backed findings AND >=1 limitation or non-significant result" — VERIFIED
  - Finding 1: Decisive superiority of Strategy B at low dynamicity ($\alpha \le 0.2$: 100% win rate, +10.86% mean cost reduction)
  - Finding 2: Exponential computational scaling of 2-opt ($49.1\times$ to $75.1\times$ more evals, $110.8\times$ slower response time; $p = 1.86 \times 10^{-9}$)
  - Finding 3: Route disruption doubling under 2-opt ($\text{mean } \delta = 0.0794$ vs $0.0367$; $p = 1.86 \times 10^{-9}$)
  - Finding 4: Budget cap Pareto efficiency (500 evals/update captures 96.3% of benefits while saving 32.3% of effort)
  - Limitation/Non-significant result: Overall route cost difference across all dynamic conditions is NOT statistically significant ($p = 0.1975$, 95% CI $[-11.49, +59.15]$ spans 0)
  - Limitation/Negative finding: Myopic local search trap at high dynamicity ($\alpha \ge 0.6$: Strategy B inferior in 66.7% of runs, -5.01% average cost penalty)

## [Phase 8 Complete] - 2026-10-21
### Adaptive Strategy Selection
- **src/adaptive_route_optimization/algorithms/adaptive/features.py**: State feature extraction
  - `StateFeatures` dataclass capturing decision-time observable features:
    $n$ (total customers), $|V_t|$ (revealed customers), $f_t$ (frozen prefix), uncommitted suffix count, $|\Delta_t|$ (event size), $\alpha$ (dynamicity), current route cost $C(S_t)$, remaining evaluation budget, estimated 2-opt evaluation requirement.
  - Zero future information leakage: only current and past state inspected; no access to future dynamic events or offline costs.

- **src/adaptive_route_optimization/algorithms/adaptive/selector.py**: Interpretable rule-based selector
  - `AdaptiveSelector` implementing 3 explainable DAA decision rules grounded in Phase 7 findings:
    - Rule 1 (Budget Safety): Fallback to Strategy A if remaining evaluations < estimated 2-opt cost.
    - Rule 2 (Degeneracy Guard): Fallback to Strategy A if uncommitted suffix edges < 4.
    - Rule 3 (Dynamic Uncertainty / Commitment Trap): Select Strategy B if initial dynamicity $\alpha \le 0.2$ (established win rate) OR late-stage convergence ($\ge 75\%$ vertices revealed); otherwise select Strategy A to avoid myopic entrapment.
  - Fully deterministic decisions and transparent rationales logged for every dynamic event.
  - Selection overhead accounted for (+1 candidate evaluation charged per decision).

- **src/adaptive_route_optimization/algorithms/adaptive/split.py**: Data partitioning & leakage prevention
  - `DataSplitManifest` establishing strictly disjoint seed partitions:
    - Development: seeds `[42, 101]`
    - Validation: seed `[777]`
    - Held-Out Test: seeds `[1234, 5678, 9999]`
  - Validates zero overlap across partition seed sets.

- **src/adaptive_route_optimization/algorithms/adaptive/oracle.py**: Theoretical upper-bound & regret analysis
  - `OracleEvaluator` computes per-instance hindsight benchmark $\min(\text{Cost}_A, \text{Cost}_B)$ and quantitative regret: $\text{Cost}_{\text{Adaptive}} - \text{Cost}_{\text{Oracle}}$.
  - `summarize_regret()` computes aggregate regret distribution, zero-regret rates, and baseline win rates.

- **src/adaptive_route_optimization/algorithms/adaptive/evaluate_adaptive.py**: Evaluation & reporting
  - Generates summary tables: `held_out_policy_comparison.csv`, `held_out_regime_comparison.csv`, `held_out_triplet_instances.csv`, `held_out_regret_summary.json`.
  - Generates publication figures:
    - `fig10_adaptive_vs_baselines_cost.png`
    - `fig11_adaptive_pareto_frontier.png`
    - `fig12_adaptive_regret_distribution.png`

- **src/adaptive_route_optimization/simulation/simulator.py** & **runner.py**: Engine integration
  - Added `Strategy.ADAPTIVE` to simulation engine and runner.
  - Added `Simulator.run_all_strategies()` ensuring Rule 10 parity across A, B, and ADAPTIVE.

- **configs/held_out_matrix.json**: Held-out experiment matrix
  - 10 conditions $\times$ 3 unseen seeds ($1234, 5678, 9999$) $\times$ 3 strategies (`["A", "B", "ADAPTIVE"]`) = 90 runs.
  - Executed to 100% completion (90/90 completed, 0 failures).

- **tests/test_adaptive.py**: 14 comprehensive unit & integration tests
  - State feature extraction and non-leakage verification
  - Selector rule triggers, budget fallbacks, degeneracy guards, and determinism
  - Disjoint partition integrity
  - Oracle and regret calculations
  - End-to-end simulator integration and parity

- **Phase 8 Gate**: "beats or meaningfully trades off against fixed baselines on unseen conditions, otherwise removed from the core claim" — VERIFIED
  - Route Quality: Mean cost **944.71** (ADAPTIVE) vs **1023.13** (Always A, -7.66% lower) and **969.68** (Always B, -2.57% lower).
  - Computational Effort: Mean evaluations **169,997** (ADAPTIVE) vs **207,071** (Always B) — **17.9% reduction in computational effort**.
  - High Dynamicity Savings: Slashes evaluations by **51.4%** at $\alpha \ge 0.6$ while achieving lower route cost than both baselines.
  - Step-level Switching Synergy: In **12 out of 30 held-out instances (40.0%)**, Adaptive beat **both** Always A and Always B on the exact same instance.


