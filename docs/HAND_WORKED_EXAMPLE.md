# Hand-Worked 10-Node Example

## Instance Definition

**Vertices (10 total, 0 = depot)**:

| Vertex | x | y |
|--------|---|---|
| 0 (depot) | 0 | 0 |
| 1 | 3 | 0 |
| 2 | 3 | 4 |
| 3 | 0 | 4 |
| 4 | 6 | 0 |
| 5 | 6 | 4 |
| 6 | 0 | 8 |
| 7 | -3 | 4 |
| 8 | 3 | -4 |
| 9 | 9 | 0 |

**Initial known set**: V₀ = {0, 1, 2, 3, 4} (depot + 4 customers)
**Dynamic event at t=0→1**: Δ₀ = {5} (single vertex revealed)
**Dynamicity**: α = |{5,6,7,8,9}| / 9 = 5/9 ≈ 0.556

---

## Distance Matrix (Euclidean, rounded to 6 decimals)

| c(i,j) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|--------|---|---|---|---|---|---|---|---|---|---|
| **0** | 0 | 3.0 | 5.0 | 4.0 | 6.0 | 7.211103 | 8.0 | 5.0 | 5.0 | 9.0 |
| **1** | 3.0 | 0 | 4.0 | 5.0 | 3.0 | 5.0 | 8.246211 | 6.708204 | 4.0 | 6.0 |
| **2** | 5.0 | 4.0 | 0 | 3.0 | 5.0 | 3.0 | 5.0 | 6.0 | 8.0 | 8.485281 |
| **3** | 4.0 | 5.0 | 3.0 | 0 | 7.211103 | 6.0 | 4.0 | 3.0 | 6.403124 | 10.816654 |
| **4** | 6.0 | 3.0 | 5.0 | 7.211103 | 0 | 4.0 | 10.0 | 10.816654 | 6.403124 | 3.0 |
| **5** | 7.211103 | 5.0 | 3.0 | 6.0 | 4.0 | 0 | 7.211103 | 9.0 | 8.0 | 5.0 |
| **6** | 8.0 | 8.246211 | 5.0 | 4.0 | 10.0 | 7.211103 | 0 | 5.0 | 10.770330 | 13.416408 |
| **7** | 5.0 | 6.708204 | 6.0 | 3.0 | 10.816654 | 9.0 | 5.0 | 0 | 9.433981 | 14.422205 |
| **8** | 5.0 | 4.0 | 8.0 | 6.403124 | 6.403124 | 8.0 | 10.770330 | 9.433981 | 0 | 6.708204 |
| **9** | 9.0 | 6.0 | 8.485281 | 10.816654 | 3.0 | 5.0 | 13.416408 | 14.422205 | 6.708204 | 0 |

**Exact values for key distances**:
- c(0,1) = 3
- c(1,4) = 3
- c(4,2) = √(3²+4²) = 5
- c(2,3) = 3
- c(3,0) = 4
- c(4,5) = 4
- c(5,2) = 3
- c(1,2) = 4
- c(0,4) = 6
- c(0,5) = √52 ≈ 7.211103
- c(4,3) = √52 ≈ 7.211103

---

## Step 1: Initial Solution (t=0) — Nearest-Neighbor on V₀ = {0,1,2,3,4}

**Trace**:
- Start at 0. Unvisited: {1,2,3,4}
  - c(0,1)=3, c(0,2)=5, c(0,3)=4, c(0,4)=6 → **pick 1** (min=3)
  - Route: [0, 1]
- Current=1. Unvisited: {2,3,4}
  - c(1,2)=4, c(1,3)=5, c(1,4)=3 → **pick 4** (min=3)
  - Route: [0, 1, 4]
- Current=4. Unvisited: {2,3}
  - c(4,2)=5, c(4,3)=√52≈7.211 → **pick 2** (min=5)
  - Route: [0, 1, 4, 2]
- Current=2. Unvisited: {3}
  - c(2,3)=3 → **pick 3**
  - Route: [0, 1, 4, 2, 3]
- Return to depot: c(3,0)=4

**Initial Route S₀**: (0, 1, 4, 2, 3, 0)

**Cost C(S₀)** = c(0,1) + c(1,4) + c(4,2) + c(2,3) + c(3,0)
= 3 + 3 + 5 + 3 + 4 = **18**

**Candidate evaluations**: 4 + 3 + 2 + 1 = 10

---

## Step 2: Dynamic Event — Vertex 5 Revealed (t=0 → 1)

**New vertex**: 5 at (6, 4)
**Known set V₁**: {0, 1, 2, 3, 4, 5}

---

## Step 3: Strategy A — Cheapest Insertion Repair

**Current route S₀**: (0, 1, 4, 2, 3, 0) — 5 edges, 6 vertices

**Insertion positions** (insert after index i, between R[i] and R[i+1]):

| i | Edge (u,w) | Δ = c(u,5)+c(5,w)-c(u,w) |
|---|------------|--------------------------|
| 0 | (0,1) | c(0,5)+c(5,1)-c(0,1) = 7.211103 + 5 - 3 = **9.211103** |
| 1 | (1,4) | c(1,5)+c(5,4)-c(1,4) = 5 + 4 - 3 = **6.0** |
| 2 | (4,2) | c(4,5)+c(5,2)-c(4,2) = 4 + 3 - 5 = **2.0** ← **BEST** |
| 3 | (2,3) | c(2,5)+c(5,3)-c(2,3) = 3 + 6 - 3 = **6.0** |
| 4 | (3,0) | c(3,5)+c(5,0)-c(3,0) = 6 + 7.211103 - 4 = **9.211103** |

**Best insertion**: after position 2 (between 4 and 2), Δ = 2.0

**Route after insertion S₁ᴬ**: (0, 1, 4, 5, 2, 3, 0)

**Cost C(S₁ᴬ)** = 18 + 2.0 = **20**

**Candidate evaluations**: 5

---

## Step 4: Strategy B — Insertion + 2-opt

**Starting route for 2-opt**: S₁ᴬ = (0, 1, 4, 5, 2, 3, 0)

**Edges**: E = {(0,1), (1,4), (4,5), (5,2), (2,3), (3,0)}

**2-opt scan** (first-improvement, lexicographic order (i,j)):

| i | j | Edges (a,b) & (c,d) | Δ = c(a,c)+c(b,d)-c(a,b)-c(c,d) | Improving? |
|---|---|---------------------|----------------------------------|------------|
| 0 | 2 | (0,1) & (4,5) | c(0,4)+c(1,5)-3-4 = 6+5-7 = **4.0** | No |
| 0 | 3 | (0,1) & (5,2) | c(0,5)+c(1,2)-3-3 = 7.211+4-6 = **5.211** | No |
| 0 | 4 | (0,1) & (2,3) | c(0,2)+c(1,3)-3-3 = 5+5-6 = **4.0** | No |
| 0 | 5 | (0,1) & (3,0) | involves depot twice → skip | — |
| 1 | 3 | (1,4) & (5,2) | c(1,5)+c(4,2)-3-3 = 5+5-6 = **4.0** | No |
| 1 | 4 | (1,4) & (2,3) | c(1,2)+c(4,3)-3-3 = 4+7.211-6 = **5.211** | No |
| 1 | 5 | (1,4) & (3,0) | c(1,3)+c(4,0)-3-4 = 5+6-7 = **4.0** | No |
| 2 | 4 | (4,5) & (2,3) | c(4,2)+c(5,3)-4-3 = 5+6-7 = **4.0** | No |
| 2 | 5 | (4,5) & (3,0) | c(4,3)+c(5,0)-4-4 = 7.211+7.211-8 = **6.422** | No |
| 3 | 5 | (5,2) & (3,0) | c(5,3)+c(2,0)-3-4 = 6+5-7 = **4.0** | No |

**No improving moves found**. Route is already locally optimal.

**Final route S₁ᴮ**: (0, 1, 4, 5, 2, 3, 0) — identical to S₁ᴬ

**Cost C(S₁ᴮ)** = **20**

**2-opt candidate evaluations**: 9 (all non-adjacent pairs examined; depot-depot pair skipped)

---

## Step 5: Metrics Comparison

| Metric | Strategy A (Insertion) | Strategy B (Insertion + 2-opt) |
|--------|------------------------|--------------------------------|
| Final Route | (0,1,4,5,2,3,0) | (0,1,4,5,2,3,0) |
| Route Cost | 20 | 20 |
| Insertion Evals | 5 | 5 |
| 2-opt Evals | 0 | 9 |
| Total Evals (this step) | 5 | 14 |
| Cumulative Evals | 15 | 24 |
| Disruption δ(S₀, S₁) | 1/3 ≈ 0.333 | 1/3 ≈ 0.333 |
| Feasible? | Yes | Yes |

**Disruption calculation**:
- E(S₀) = {(0,1), (1,4), (4,2), (2,3), (3,0)} — 5 edges
- E(S₁) = {(0,1), (1,4), (4,5), (5,2), (2,3), (3,0)} — 6 edges
- Intersection = {(0,1), (1,4), (2,3), (3,0)} — 4 edges
- δ = 1 - 4/max(5,6) = 1 - 4/6 = **1/3 ≈ 0.333333**

---

## Verification Checklist (for test_spec_examples.py)

```python
# Coordinates
coords = {
    0: (0, 0), 1: (3, 0), 2: (3, 4), 3: (0, 4), 4: (6, 0),
    5: (6, 4), 6: (0, 8), 7: (-3, 4), 8: (3, -4), 9: (9, 0)
}

# S0 = (0, 1, 4, 2, 3, 0), cost = 18
# S1_A = (0, 1, 4, 5, 2, 3, 0), cost = 20
# S1_B = (0, 1, 4, 5, 2, 3, 0), cost = 20
# Disruption = 1/3
# Insertion evals = 5
# 2-opt evals = 9
# NN evals = 10
```