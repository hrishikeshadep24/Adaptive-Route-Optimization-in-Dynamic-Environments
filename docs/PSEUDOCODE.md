# Algorithm Pseudocode with Complexity Analysis

## Conventions
- `c(i, j)` — Euclidean distance function, O(1)
- `len(R)` — number of edges in route R (including return to depot)
- **Candidate evaluation** = one computation of a cost delta (insertion or 2-opt)
- All loops use deterministic iteration order (vertex indices ascending)
- Tie-breaking: lowest vertex index wins

---

## 1. Nearest-Neighbor Construction (Initial Solution)

**Input**: Known vertex set V_t (includes depot 0)
**Output**: Route R covering V_t starting/ending at 0

```
function NEAREST_NEIGHBOR(V_t):
    unvisited ← V_t \ {0}                    // O(n)
    R ← [0]                                   // Start at depot
    current ← 0
    
    while unvisited ≠ ∅:                      // n iterations
        best ← argmin_{v ∈ unvisited} c(current, v)   // O(|unvisited|) candidate evals
        R.append(best)                        // O(1)
        unvisited.remove(best)                // O(1) with set
        current ← best
    
    R.append(0)                               // Return to depot
    return R
```

**Complexity**:
- Time: O(n²) — outer loop n times, inner min over O(n) elements
- Space: O(n) — route + unvisited set
- **Candidate evaluations**: Σ_{k=1}^{n} k = n(n+1)/2 = O(n²)
  (Each iteration evaluates all remaining unvisited vertices)

**Determinism**: `argmin` breaks ties by lowest vertex index.

---

## 2. Cheapest-Insertion Repair (Single Vertex)

**Input**: Current route R = (0, v₁, ..., v_m, 0), new vertex v_new
**Output**: Updated route R' with v_new inserted

```
function CHEAPEST_INSERTION(R, v_new):
    best_cost ← +∞
    best_pos ← -1
    
    for i = 0 to len(R) - 2:                  // m iterations (m = |R| - 1)
        u ← R[i]
        w ← R[i + 1]
        delta ← c(u, v_new) + c(v_new, w) - c(u, w)   // 1 candidate evaluation
        if delta < best_cost or (delta == best_cost and i < best_pos):
            best_cost ← delta
            best_pos ← i + 1                   // Insert after position i
    
    R.insert(best_pos, v_new)                 // O(m) list insertion
    return R
```

**Complexity**:
- Time: O(m) where m = current route length
- Space: O(1) extra
- **Candidate evaluations**: m (one per insertion position)
- **Note**: For batch insertion of k vertices, process sequentially in vertex-index order. Total evaluations = Σ m_i where m_i grows with each insertion.

**Determinism**: Ties on delta broken by lowest insertion position (earliest in route).

---

## 3. 2-opt Local Search

**Input**: Route R = (0, v₁, ..., v_m, 0)
**Output**: Locally optimal route R* (no improving 2-opt move exists)

```
function TWO_OPT(R):
    improved ← true
    passes ← 0
    
    while improved:                           // k passes (k ≤ budget)
        improved ← false
        passes ← passes + 1
        
        for i = 0 to len(R) - 3:              // O(m²) edge pairs
            for j = i + 2 to len(R) - 1:      // j = i+2 avoids adjacent edges
                a ← R[i]
                b ← R[i + 1]
                c ← R[j]
                d ← R[(j + 1) % len(R)]       // Wraps for j = len(R)-1 (d = 0)
                
                // Skip if swap involves depot incorrectly
                if (a == 0 and d == 0): continue
                
                delta ← c(a, c) + c(b, d) - c(a, b) - c(c, d)  // 1 candidate evaluation
                
                if delta < -ε:                // ε = 1e-9 for numerical stability
                    // Reverse segment R[i+1 .. j]
                    R[i + 1 : j + 1] ← reversed(R[i + 1 : j + 1])
                    improved ← true
                    // Note: continue scanning for more improvements in this pass
                    // (first-improvement vs best-improvement; we use first-improvement)
    
    return R
```

**Complexity**:
- Time per pass: O(m²) — nested loops over edge pairs
- Space: O(1) extra (in-place reversal)
- **Candidate evaluations per pass**: m(m-3)/2 ≈ O(m²) (all non-adjacent edge pairs)
- **Total evaluations**: k · O(m²) where k = number of passes until local optimum
- **Worst-case k**: O(m) for pathological cases, but typically small (k ≤ 5) in practice
- **Budget interaction**: In experiments, 2-opt may be budget-limited (max evaluations or max passes)

**Determinism**: 
- Scans pairs in lexicographic order (i, j)
- First-improvement strategy: applies first improving move found, then restarts scan
- Ties on delta broken by earliest (i, j)

**Edge Cases**:
- Route length < 3: no 2-opt moves possible, return unchanged
- Depot handling: (0, v₁) and (v_m, 0) are valid edges; swap must keep depot at ends
- Zero-cost edges: ε threshold prevents infinite loops on delta ≈ 0

---

## 4. Update Operator U(S_t, G_{t+1}) — Strategy A (Greedy Insertion Only)

```
function UPDATE_GREEDY(S_t, Δ_t):
    R ← S_t
    for v in sorted(Δ_t):                   // Deterministic order
        R ← CHEAPEST_INSERTION(R, v)
    return R
```

**Candidate evaluations**: Σ_{v ∈ Δ_t} len(R_v) where R_v is route before inserting v.

---

## 5. Update Operator U(S_t, G_{t+1}) — Strategy B (Insertion + 2-opt)

```
function UPDATE_LOCAL_SEARCH(S_t, Δ_t):
    R ← S_t
    for v in sorted(Δ_t):
        R ← CHEAPEST_INSERTION(R, v)
    R ← TWO_OPT(R)                          // Run to local optimum (or budget limit)
    return R
```

**Candidate evaluations**: Insertion evals + 2-opt evals.

---

## 6. Frozen-Prefix Update (Model for Phase 3+)

```
function UPDATE_WITH_FROZEN(S_t, Δ_t, f_t):
    // S_t = (0, p₁..p_f, u₁..u_k, 0) where prefix p is frozen
    prefix ← S_t[0 : f_t + 1]               // Includes depot at 0
    suffix ← S_t[f_t : ]                    // From p_f to end (includes return to 0)
    
    // Apply update only to suffix
    for v in sorted(Δ_t):
        suffix ← CHEAPEST_INSERTION(suffix, v)
    suffix ← TWO_OPT(suffix)                // If Strategy B
    
    // Reconstruct: prefix + suffix[1:] (avoid duplicate p_f)
    return prefix + suffix[1:]
```

**Note**: The frozen prefix advances by 1 vertex per event step (configurable).

---

## Candidate Evaluation Definition (Computational Effort Metric)

| Operation | What Counts as One Evaluation |
|-----------|-------------------------------|
| Nearest-neighbor step | One call to `c(current, v)` for v ∈ unvisited |
| Insertion position | One computation of `c(u, v_new) + c(v_new, w) - c(u, w)` |
| 2-opt pair | One computation of `c(a, c) + c(b, d) - c(a, b) - c(c, d)` |

**Rationale**: These are the fundamental "cost delta" computations that dominate runtime. Counting them yields a hardware-independent, reproducible measure of algorithmic effort.

**Reporting**: 
- Total evaluations per update step
- Cumulative evaluations per run
- Broken down by insertion vs 2-opt vs initial construction

---

## Complexity Summary Table

| Algorithm | Time | Space | Candidate Evals (typical) |
|-----------|------|-------|---------------------------|
| Nearest-Neighbor | O(n²) | O(n) | n(n+1)/2 |
| Cheapest-Insertion (1 vertex) | O(m) | O(1) | m |
| 2-opt (1 pass) | O(m²) | O(1) | m(m-3)/2 |
| 2-opt (to local opt) | O(k·m²) | O(1) | k·m(m-3)/2 |
| Strategy A (1 event) | O(m) | O(1) | m |
| Strategy B (1 event) | O(m + k·m²) | O(1) | m + k·m(m-3)/2 |