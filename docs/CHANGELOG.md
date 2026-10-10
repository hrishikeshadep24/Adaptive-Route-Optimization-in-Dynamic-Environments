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