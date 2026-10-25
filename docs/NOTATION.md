# Notation Symbol Table

## Sets and Spaces

| Symbol | Meaning | Domain |
|--------|---------|--------|
| V | Complete vertex set | {0, 1, ..., n} |
| V_t | Vertices known at time t | V_t ⊆ V, 0 ∈ V_t |
| Δ_t | New vertices revealed at t → t+1 | Δ_t ⊆ V \ V_t |
| E | Complete edge set | V × V |
| R | Route (sequence of vertices) | (v₀, v₁, ..., v_k, v₀) |
| S_t | Solution (route) at time t | Route covering V_t |

## Indices and Counters

| Symbol | Meaning | Domain |
|--------|---------|--------|
| n | Total number of non-depot vertices | |V| - 1 |
| m_t | Route length at time t (edges) | |V_t| |
| t | Discrete time step | 0, 1, ..., T |
| T | Final time step | T = |{t : Δ_t ≠ ∅}| |
| α | Dynamicity level | |V \ V₀| / |V \ {0}| ∈ [0, 1] |
| k | Number of 2-opt improvement passes | ℕ |
| f_t | Frozen prefix length at time t | 0 ≤ f_t ≤ m_t |

## Graph and Cost

| Symbol | Meaning | Domain |
|--------|---------|--------|
| c(i, j) | Cost of edge (i, j) | ℝ≥₀ |
| c(i, i) | Self-loop cost | 0 |
| (x_v, y_v) | 2D coordinates of vertex v | ℝ² |
| d_E(i, j) | Euclidean distance | √((x_i - x_j)² + (y_i - y_j)²) |

## Route and Cost Functions

| Symbol | Meaning | Formula |
|--------|---------|---------|
| C(R) | Total route cost | Σ_{i=0}^{k} c(v_i, v_{i+1}) |
| δ(S_t, S_{t+1}) | Route disruption | 1 - |E_t ∩ E_{t+1}| / max(|E_t|, |E_{t+1}|) |
| E(R) | Edge set of route R | {(v_i, v_{i+1}) : i = 0..k} |

## Algorithms and Operators

| Symbol | Meaning |
|--------|---------|
| NN(V_t) | Nearest-neighbor construction on V_t |
| INSERT(R, v) | Cheapest insertion of vertex v into route R |
| 2OPT(R) | 2-opt local search on route R |
| U(S_t, G_{t+1}) | Update operator: S_{t+1} = U(S_t, G_{t+1}) |

## Computational Effort

| Symbol | Meaning |
|--------|---------|
| eval_ins(R, v) | Candidate evaluations for inserting v into R |
| eval_2opt(R) | Candidate evaluations for one 2-opt pass on R |
| B | Computational budget (evaluations or time) |

## Metrics

| Symbol | Meaning |
|--------|---------|
| Q_t = C(S_t) | Route cost at time t (quality) |
| τ_t | Update response time at t |
| ξ_t | Computational effort at t |
| δ_t = δ(S_{t-1}, S_t) | Disruption at step t |
| φ_t | Feasibility boolean at t |

## Conventions

- **Vectors/Sequences**: Bold or parentheses: **v** = (v₁, ..., v_k)
- **Sets**: Calligraphic or capital letters
- **Functions**: Capitalized or camelCase
- **Indices**: i, j for vertices; t for time; k for passes
- **Constants**: ε = 10⁻⁹ (numerical tolerance for zero-cost edges)
- **Determinism**: All random choices (tie-breaking, instance generation) use a global seed; algorithm behavior is fully deterministic given seed and config.