# Research Specification

## Problem Formalization

### Graph and Cost Model
- **Graph**: G = (V, E) where V = {0, 1, ..., n} is the set of vertices and E = V × V is the complete set of edges.
- **Vertex 0**: The depot (start and end of every route).
- **Coordinates**: Each vertex v ∈ V has 2D coordinates (x_v, y_v).
- **Cost function**: Euclidean distance, symmetric:
  c(i, j) = √((x_i - x_j)² + (y_i - y_j)²) for all i, j ∈ V
  Properties: c(i, j) = c(j, i) ≥ 0, c(i, i) = 0, triangle inequality holds.

### Route and Total Cost
- **Route**: R = (v₀, v₁, ..., vₖ, v₀) where v₀ = 0 (depot), all other vertices are distinct and drawn from V \ {0}.
- **Route length**: |R| = k + 1 edges (including return to depot).
- **Total cost**: C(R) = Σ_{i=0}^{k} c(v_i, v_{i+1}) where v_{k+1} ≡ v₀.

### Dynamic State and Events
- **Time**: Discrete steps t = 0, 1, 2, ..., T.
- **Known vertices at time t**: V_t ⊆ V, with 0 ∈ V_t always.
- **Initial known set**: V₀ ⊆ V, with |V₀| ≥ 2 (depot + at least one customer).
- **Dynamic event at step t → t+1**: A set of new vertices Δ_t ⊆ V \ V_t becomes revealed.
  - V_{t+1} = V_t ∪ Δ_t.
  - In the base model, |Δ_t| = 1 (single vertex per event). Batch events are an extension noted in OPEN_QUESTIONS.
- **Event sequence**: Deterministically generated from a seed; the full hidden instance V is fixed at t=0.

### Initial Solution and Update Operator
- **Initial solution at t=0**: S₀ = route covering V₀, constructed by nearest-neighbor heuristic (deterministic tie-breaking by vertex index).
- **Update operator**: U(S_t, G_{t+1}) → S_{t+1} where S_t is a route covering V_t and S_{t+1} is a route covering V_{t+1}.
- **Strategies**:
  A. **Greedy Insertion Repair**: For each v ∈ Δ_t, insert v at position minimizing incremental cost.
  B. **Insertion + 2-opt Repair**: Apply A, then run 2-opt local search to local optimum.
  C. **Stronger Re-optimization**: Placeholder; method to be decided in Phase 4 after pilots.

### Feasibility (Single-Route Dynamic TSP)
A route R is **feasible** iff:
1. R starts and ends at depot: v₀ = 0 and v_{k+1} = 0.
2. Every vertex in V_t \ {0} appears exactly once in (v₁, ..., v_k).
3. No other vertices appear.
4. All edges (v_i, v_{i+1}) exist in E (always true for complete graph).
This is the **core problem**. Multi-route VRP is an optional later extension.

### Dynamicity
- **Dynamicity level**: α = |V \ V₀| / |V \ {0}| ∈ [0, 1].
- Fraction of non-depot vertices revealed after the initial solution.
- Pilot levels: α ∈ {0.1, 0.2, 0.4, 0.6, 0.8}.

### Route Disruption
**Definition**: Normalized edge-difference between consecutive routes.
Let S_t = (0, u₁, ..., u_m, 0) and S_{t+1} = (0, v₁, ..., v_n, 0).
- **Edge set of S_t**: E_t = {(0,u₁), (u₁,u₂), ..., (u_m,0)}.
- **Edge set of S_{t+1}**: E_{t+1} = {(0,v₁), (v₁,v₂), ..., (v_n,0)}.
- **Disruption**: δ(S_t, S_{t+1}) = 1 - |E_t ∩ E_{t+1}| / max(|E_t|, |E_{t+1}|) ∈ [0, 1].

**Justification**: Edge-based disruption captures structural change to the route (which edges are broken/replaced), is invariant to vertex renumbering, and correlates with practical re-planning cost. Position-based disruption would conflate insertion shift with actual edge changes.

### Frozen-Prefix Rule
- **Model**: The vehicle has already traversed a prefix of the route. Only the **uncommitted suffix** may be modified.
- **Representation**: At time t, the route is S_t = (0, p₁, ..., p_f, u₁, ..., u_k, 0) where (p₁, ..., p_f) is the frozen prefix (already visited, immutable). The update operator U only rearranges (u₁, ..., u_k) and inserts new vertices into this suffix.
- **Initial state (t=0)**: f = 0 (nothing frozen).
- **Advancement**: After each event step, the vehicle "travels" one edge of the current route, moving the next vertex from uncommitted to frozen. This is a modeling choice; the exact freeze schedule is configurable but defaults to one vertex per event step.
- **Edge case**: If an event occurs when the route is fully frozen, the new vertex must be appended after the frozen portion (handled in Phase 3 implementation).

### Computational Budget (PLACEHOLDER)
Two candidate definitions; **no choice made yet**. Decision deferred to Phase 6 pilots.

| Aspect | Fixed Evaluation Count | Fixed Wall-Clock Time |
|--------|------------------------|----------------------|
| Definition | Max candidate evaluations per update | Max seconds per update |
| Pros | Deterministic, reproducible, hardware-independent | Reflects real-time constraints, intuitive |
| Cons | Does not map directly to real time; implementation overhead varies | Non-deterministic across hardware; hard to reproduce exactly |
| Candidate evaluation | One call to c(i,j) or one route cost delta computation | N/A |
| Recommendation | **Lean toward fixed evaluation count** for research reproducibility; wall-clock as secondary reporting metric. |

**Decision rule**: Run pilot matrix under both; choose the one that yields cleaner strategy differentiation and document rationale in CHANGELOG.

### Evaluation Metrics
1. **Route Cost (Primary Quality)**: C(S_t) at each t; final C(S_T).
2. **Update Response Time**: Wall-clock time for U(S_t, G_{t+1}) (reported in ms).
3. **Computational Effort**: Number of candidate evaluations (see definition below).
4. **Route Disruption**: δ(S_t, S_{t+1}) as defined above.
5. **Feasibility**: Boolean; all constraints satisfied at each t.
6. **Scalability**: Trends of metrics vs n (size) and α (dynamicity).

### Candidate Evaluation (Computational Effort Metric)
A **candidate evaluation** is one computation of a route cost change ΔC for a specific insertion position or 2-opt move.
- **Insertion**: For a route of length m, there are m possible insertion positions. Each requires computing c(u, v) + c(v, w) - c(u, w) where u, w are adjacent in current route and v is the new vertex. **Count = m evaluations per new vertex**.
- **2-opt**: For a route of length m, there are O(m²) possible edge pairs. Each requires computing c(a,c) + c(b,d) - c(a,b) - c(c,d). **Count = 1 evaluation per pair examined** (not per improving move; all examined pairs count).
- **Total effort**: Sum of candidate evaluations across all events in a run.

### Single-Route vs Multi-Route Decision
- **Core**: Single-route dynamic TSP (one vehicle, one depot, all vertices in one tour).
- **Optional extension**: Multi-route VRP (multiple vehicles, capacity constraints, 2-opt* inter-route moves).
- **Rationale**: Single-route isolates the dynamic update mechanism; multi-route adds combinatorial complexity that obscures the core quality-vs-effort trade-off. Multi-route is documented as a future extension in Phase 4+.

## Edge Cases (Defined)

1. **Event on empty route**: V₀ = {0} (only depot known). Insertion places new vertex between 0 and 0, forming (0, v, 0). Cost = 2·c(0,v). Well-defined.

2. **Duplicate vertex in event**: Δ_t ∩ V_t ≠ ∅. **Rule**: Ignore duplicates; only process v ∈ Δ_t \ V_t. Event sequence generator guarantees no duplicates, but operator is defensive.

3. **Event located at depot**: v = 0. **Rule**: Not possible; V \ {0} only. Depot is always in V₀. If input contains it, ignore silently.

4. **Several events at one timestep**: |Δ_t| > 1 (batch). **Rule**: Process sequentially in vertex-index order (deterministic). Each insertion updates the route for the next. Total disruption measured after all insertions.

5. **Zero-cost edges**: c(i,j) = 0 for i ≠ j. **Rule**: Euclidean distance on distinct points is > 0. If synthetic generator produces coincident points, add ε = 10⁻⁹ to all coordinates or reject instance. Documented in generator spec.

## Computational Complexity Summary

| Algorithm | Time Complexity | Space Complexity | Notes |
|-----------|----------------|------------------|-------|
| Nearest-Neighbor Construction | O(n²) | O(n) | Greedy, deterministic tie-break by index |
| Cheapest-Insertion Repair (single vertex) | O(m) where m = current route length | O(1) extra | Evaluates m positions |
| 2-opt Local Search (one pass) | O(m²) | O(1) extra | Examines all edge pairs; repeated until no improvement |
| 2-opt (full to local optimum) | O(k·m²) worst-case, k = # passes | O(1) extra | k typically small in practice; bounded by budget |

## Notation Reference
See `docs/NOTATION.md` for complete symbol table.

## Pseudocode Reference
See `docs/PSEUDOCODE.md` for algorithm pseudocode with complexity annotations.

## Hand-Worked Example
See `docs/HAND_WORKED_EXAMPLE.md` for the 10-node trace.
See `tests/test_spec_examples.py` for executable verification.