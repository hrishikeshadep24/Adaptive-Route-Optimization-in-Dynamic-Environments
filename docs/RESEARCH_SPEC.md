# Research Specification

## Problem Formalization

### Static Problem
- Graph G = (V, E) with |V| = n
- Cost function c: E -> R+
- Route R = (v_0, v_1, ..., v_{n-1}, v_0) visiting all vertices
- Total cost C(R) = sum_{i=0}^{n-1} c(v_i, v_{i+1})

### Dynamic Problem
- Time steps t = 0, 1, ..., T
- At t=0: known vertex set V_0 subset V
- At each t > 0: event reveals new vertex set Delta_t
- Known vertices at t: V_t = V_{t-1} union Delta_t
- Solution at t: S_t = route covering V_t
- Update operator: S_t = U(S_{t-1}, G[V_t])

### Dynamicity Level
- alpha = |V \ V_0| / |V| = proportion of vertices revealed after t=0

## Strategies

### A. Greedy Insertion Repair
For each new vertex v in Delta_t:
- Find position p in current route minimizing delta cost
- Insert v at position p
- Repeat for all new vertices (sequential or batch)

### B. Insertion + 2-opt Repair
- Apply greedy insertion for all new vertices
- Run 2-opt local search on resulting route
- Stop at local optimum or budget exhaustion

### C. Stronger Re-optimization (TBD)
- Periodic or triggered re-optimization
- Method: iterative local search, metaheuristic, or exact (small n)
- Budget-controlled

## Metrics

### Primary
- Route Cost: C(S_t) at each t, final C(S_T)
- Update Time: wall-clock time for U(S_{t-1}, G[V_t])

### Secondary
- Computational Effort: candidate evaluations, iterations, 2-opt moves
- Disruption: fraction of route edges changed between S_{t-1} and S_t
- Feasibility: all constraints satisfied (initially: valid tour)
- Scalability: metric trends vs n and alpha

## Experimental Factors
- n in {50, 100, 200} (pilot)
- alpha in {0.1, 0.2, 0.4, 0.6, 0.8} (pilot)
- Strategy in {A, B, C}
- Seeds: ~10 per cell (pilot)

## Analysis Plan
- Mean and CI for each metric per condition
- Paired comparisons (same instance/events)
- Quality vs computation trade-off curves
- Scaling plots
- Ablation: insertion only vs insertion+2-opt