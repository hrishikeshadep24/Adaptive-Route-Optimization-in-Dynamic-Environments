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
  - 2-opt: 10 pairs examined, no improvement, route unchanged
  - Disruption δ = 1/3, cumulative evals=25

- **tests/test_spec_examples.py**: Executable verification of all hand-worked numbers
  - 12 test functions covering costs, disruptions, eval counts, feasibility, distance spot-checks

- **docs/OPEN_QUESTIONS.md**: Updated with all Phase 2 resolutions and remaining deferrals
  - 5 Phase 2 questions resolved with explicit defaults
  - 10+ questions deferred to Phases 6-8 with recommended defaults
  - Additional clarifications (frozen prefix, 2-opt variant, numerical stability)

- **Phase 2 Gate**: 10-node example manually traceable and verified by tests