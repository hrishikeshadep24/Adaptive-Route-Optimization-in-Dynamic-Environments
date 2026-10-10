---BEGIN PHASE PLAN---
# Detailed Phase Plan (authoritative)

## Fixed vs open decisions
FIXED: studies how a routing solution is updated when the problem changes during execution; compares incremental repair, repair + local search, and stronger re-optimization under controlled budgets; application-neutral (delivery is only an interpretation); first dynamic event = a new vertex/request becomes available after the initial solution exists; no traffic APIs.
OPEN (decided by pilots, not assumed): the exact stronger search method, final benchmark mix, computational-budget definition, whether an adaptive selector is justified.
Primary question: under controlled budgets, when does incremental repair, local-search repair, or stronger re-optimization give the best quality-response trade-off as size and dynamicity change?
Secondary: can observed patterns support a simple interpretable strategy selector for unseen dynamic states?
Contribution: controlled, reproducible empirical algorithm study + (if justified) interpretable adaptive layer. NOT a new problem or metaheuristic.

## Phases
Phase 0 Foundation: COMPLETED. Frozen: identity, scope, RQs, contribution type, engineering principles; first dynamic model; primary metrics (route cost, update time, computational effort, disruption, feasibility, scalability); adaptive selector is conditional.
Phase 1 Literature and gap validation: COMPLETED. Gaps are evaluation/methodology gaps. Closest implementable baselines chosen. Traffic-aware ALNS+rollout is out of scope. Gate: nobody says "we invented dynamic routing/2-opt".

Phase 2 Algorithmic and mathematical specification (NEXT)
Goal: exact computational model before coding main algorithms.
Tasks: define G=(V,E), c(i,j); route and total cost; dynamic state at time t and the event; initial solution and update operator U(S_t, G_{t+1}); dynamicity = proportion of requests/vertices revealed after the initial solution; route disruption = fraction/number of route edges or positions changed after an event (define precisely); decide single-route dynamic TSP vs multi-route VRP (DEFAULT: single-route dynamic TSP first, multi-route only as later optional extension); define objective and all constraints before implementation.
Deliverables: formal problem spec, notation sheet, pseudocode for every baseline, complexity-analysis draft, small hand-worked examples.
Gate: a 10-node example can be manually traced initial route -> dynamic event -> updated route -> metric calculation.

Phase 3 Core routing engine
Goal: correct, modular, testable STATIC engine.
Tasks: graph/instance model; route representation; exact route-cost calculation; feasibility validation; deterministic seeded random-instance generation; baseline construction (nearest-neighbor/greedy); simple exact solver for very small instances ONLY (to verify heuristics against the known optimum); route plotting independent of final UI; unit tests before any dynamic behavior.
Deliverables: src/models/, src/algorithms/baseline/, src/evaluation/, tests/, small-instance correctness suite.
Gate: all baseline tests pass; costs independently verified; exact-vs-heuristic comparison works on small instances.
Out of scope: dynamic events, adaptive selection, GA/SA/ALNS, UI.

Phase 4 Local search and repair algorithms
Goal: algorithmic baselines that make the comparison meaningful.
Tasks: 2-opt local search; dynamic insertion/repair (new vertex at least additional-cost feasible position); repair + 2-opt as second strategy; instrument candidate evaluations, accepted moves, improvement iterations; deterministic under same seed/config; do NOT add GA/SA/ALNS unless pilots show a stronger comparator is necessary and feasible.
Deliverables: greedy/insertion repair, repair+2-opt, algorithm-level benchmarks, complexity notes, unit and integration tests, adversarial edge-case tests.
Gate: for the same dynamic event both repair methods yield valid routes and reproducible cost/time measurements.
Out of scope: dynamic simulator, adaptive selector.

Phase 5 Dynamic simulation engine
Goal: controlled environment for the research question.
Tasks: generate a complete hidden instance; reveal an initial subset and build the initial route; generate future events from a recorded seed; release new vertices at controlled event times/steps; freeze already-traversed route portions if the model requires it (only uncommitted portions may be repaired); run each strategy on exactly the same instance and event sequence; log every event and route state; support replay from seed/configuration.
Deliverables: event-driven simulator, dynamic state model, replay system, event logs, animated route-state prototype (debugging only).
Gate: a complete run can be replayed exactly with the same event sequence and results from the same seed.
Out of scope: final UI, statistical dashboard.

Phase 6 Controlled experimental framework
Goal: turn the simulator into a reproducible research lab.
Tasks: define pilot sizes and dynamicity levels (initial dynamicity 10/20/40/60/80%; pilot sizes 50/100/200; expand only if runtime permits); choose ONE primary computational budget (fixed wall-clock OR fixed evaluation count) and record the reason; multiple seeds per condition (start 10; more if variance high and time permits); store raw results in structured CSV/Parquet/JSON with config and seed metadata; never compare algorithms on different instance/event sequences; track commit hash. Produce a pilot matrix FIRST and report runtime before scaling.
Deliverables: experiment config files, batch runner, raw-result schema, experiment manifest, reproducibility script; batch execution, failure recovery, result validation, deterministic replay.
Gate: one command runs a full experiment matrix and produces raw results with no manual intervention.
Out of scope: interpreting results, adaptive selector.

Phase 7 Research analysis and ablation
Goal: learn what the data say before designing any adaptive method.
Tasks: compare route quality under equal budgets; update response time; computational effort; route disruption; scaling with size; scaling with dynamicity; ablations (insertion only vs insertion+2-opt; adaptation overhead vs none where relevant); repeated runs with uncertainty summaries; paired comparisons for shared seed/instance; convergence curves and quality-vs-time plots; identify regions where each strategy is clearly better, equivalent or worse. Do not change algorithm parameters after seeing final results without recording it as a NEW experiment.
Deliverables: clean analysis dataset, plots, statistical summaries, ablation results, findings document.
Gate: >=3 evidence-backed findings AND >=1 limitation or non-significant result.

Phase 8 Adaptive strategy selection (CONDITIONAL: only if Phase 7 shows meaningful instance-dependent behavior)
Tasks: extract cheap state features (size, dynamicity, current route cost, number of newly released vertices, route-change magnitude); small interpretable rule set or decision tree; derive ONLY from a designated development set; validate on held-out seeds/instances/regimes; count feature-extraction and selection overhead; compare against always using each fixed strategy; measure regret vs an after-the-fact oracle; if no improvement, do NOT force it: document the negative result and keep the controlled comparison as the primary contribution.
Deliverables: selector spec, selection logic, held-out validation, fixed-vs-adaptive comparison, failure analysis.
Gate: beats or meaningfully trades off against fixed baselines on unseen conditions, otherwise removed from the core claim.

Phase 9 Full UI, visualization and demonstration
Goal: polished understandable demonstrator of the validated engine (only after engine and result files are stable).
Tasks: modern minimal dashboard; show graph/current route/event arrival/route update/metrics; animations that explain algorithm behavior (new event -> affected route segment -> candidate repair -> chosen route -> before/after metrics); timeline/event panel; side-by-side strategy comparison; live metric cards (cost, update time, disruption, effort); research mode with results, plots, confidence intervals; replay mode from recorded seeds; clearly distinguish simulation from real-world map data; do not expose unfinished experimental controls. UI must consume saved result files and contain NO manually typed results. Application-neutral; avoid map/API dependencies.
Views: Home/Problem; Live Simulation; Algorithm Lab (same scenario, synchronized replay); Research Dashboard (dynamicity vs cost, dynamicity vs update time, quality-vs-computation frontier, scaling, disruption, uncertainty); Adaptive Decision View (only if Phase 8 succeeds; never "magic AI"); Replay; Methodology Drawer.
Gate: a person who knows nothing about the project can understand the problem, see a dynamic event, see the route change, and understand the measured trade-off without reading code.

Phase 10 Final validation, reproducibility and submission package
Tasks: freeze code; rerun the final matrix from a clean environment; regenerate all plots from raw results; verify every UI number against analysis data; run full tests; document hardware, Python version, dependencies, seeds, configs; prepare presentation/demo flow; final documentation and research report (part of this phase, not a separate one); archive raw results and manifests. Do not change the protocol to improve numbers; any needed change = new documented experiment.
Gate: a clean checkout reproduces the core experiments and the UI shows results traceable to saved outputs.

## Metrics
Route cost (primary quality); update response time; computational effort (function evaluations, iterations, candidate checks or chosen standardized budget measure); route disruption; feasibility; scalability; regret (adaptive only: selected strategy vs best strategy per instance/event).

## Team roles
M1 core algorithm and model (math model, representation, baseline, 2-opt, correctness, complexity). M2 dynamic simulation (events, state transitions, repair, replay, logging, simulator tests). M3 experiments and performance (runner, budgets, seeds, benchmarking, instrumentation, reproducibility). M4 analysis and product layer (statistics, plots, selector experiments, UI/animation, documentation). Shared: literature, explanation, testing, presentation, research decisions.

## Timeline (12 weeks)
W1 Phase 2 | W2 Phase 3 | W3 Phase 4 | W4 Phase 5 | W5-6 Phase 6 (pilot, then campaign) | W7-8 Phase 7 (analysis, robustness/held-out) | W9 Phase 8 if justified | W10 Phase 9 | W11-12 Phase 10.

## Scope boundaries and fallbacks
Core: dynamic graph routing, reproducible events, repair, local search, controlled re-optimization, experiments, analysis. Allowed later: stronger comparator, public benchmarks, multi-route extension, adaptive selection. Not core: live GPS, map/traffic/weather APIs, RL, deep learning, drones, production dispatch, mobile app, cloud.
Fallbacks: stronger method too complex -> simpler budget-controlled local-search baseline; selector not useful -> drop it; runtime too high -> shrink pilot matrix/optimize bottlenecks; benchmarks delayed -> synthetic first; UI too slow -> freeze algorithms, result-file-driven dashboard (never sacrifice validity for animation); mixed results -> report them, they answer when each strategy is useful.

## Definition of done
Math problem specified and reproducible; >=2 update strategies implemented and tested; stronger comparator only if feasible/useful; identical instances/events and controlled budgets; quality, computation, disruption reported; ablation and held-out validation where feasible; adaptive selector only if evidenced; UI reads real outputs; clean environment reproduces results; all members can explain algorithms, complexity, metrics, results, limitations.
---END PHASE PLAN---