# Open Questions

## Phase 2: Algorithmic Specification — RESOLVED with Recommendations

| # | Question | Recommendation (Default) | Status |
|---|----------|--------------------------|--------|
| 1 | Single-route dynamic TSP vs multi-route VRP? | **Single-route dynamic TSP** as core. Multi-route VRP documented as optional extension for Phase 4+. | ✅ Resolved in RESEARCH_SPEC.md |
| 2 | Precise definition of route disruption metric | **Edge-based normalized disruption**: δ = 1 - \|E_t ∩ E_{t+1}\| / max(\|E_t\|, \|E_{t+1}\|) ∈ [0,1]. Captures structural change, invariant to vertex renumbering. | ✅ Resolved in RESEARCH_SPEC.md |
| 3 | Exact event model: single vertex or batches? | **Single vertex per event** (base model). Batch events (|Δ_t| > 1) supported as extension: process sequentially in vertex-index order. | ✅ Resolved in RESEARCH_SPEC.md |
| 4 | Time windows or other constraints on vertices? | **None in core model**. Only constraint: valid tour visiting each revealed vertex exactly once. Time windows/capacity noted as future VRP extensions. | ✅ Resolved in RESEARCH_SPEC.md |
| 5 | Fully connected Euclidean vs general weighted graph? | **Fully connected Euclidean on 2D points** (symmetric, triangle inequality). General weighted graphs noted as future extension. | ✅ Resolved in RESEARCH_SPEC.md |

## Phase 6: Experimental Framework — RESOLVED in Pilots

| # | Question | Recommendation / Resolution | Status |
|---|----------|-----------------------------|--------|
| 6 | Primary computational budget: wall-clock vs evaluation count? | **Fixed Candidate Evaluation Count** selected as primary budget for deterministic, cross-platform reproducibility. Wall-clock time (ms) recorded as secondary metric. | ✅ Resolved in Phase 6 |
| 7 | Number of seeds per condition | Initial pilot run on **3 seeds**; full campaign scaled to **10 seeds** per condition. | ✅ Resolved in Phase 6 |
| 8 | Exact instance sizes for pilot vs full campaign | Pilot matrix uses **50, 100, 200** across dynamicity {0.1, 0.2, 0.4, 0.6, 0.8}. | ✅ Resolved in Phase 6 |
| 9 | Random instance distribution | **Uniform in unit square** with min_separation=0.001 to prevent zero-cost edges. Clustered instances deferred to future robustness testing. | ✅ Resolved in Phase 6 |

## Phase 7: Analysis — RESOLVED in Phase 7

| # | Question | Recommendation / Resolution | Status |
|---|----------|-----------------------------|--------|
| 10 | Statistical tests | **Paired tests** (same instance/events): Wilcoxon signed-rank + paired t-test + Shapiro-Wilk + 95% bootstrap CIs (10,000 resamples). | ✅ Resolved in Phase 7 |
| 11 | Effect size measures | **Matched-pairs rank-biserial correlation $r$** (non-parametric) + **Cohen's $d_z$** (parametric). Both reported. | ✅ Resolved in Phase 7 |
| 12 | Held-out validation for adaptive selector | Formally partitioned into Development (seeds 42, 101), Validation (seed 777), and Held-Out (seeds 1234, 5678, 9999). | ✅ Resolved in Phase 8 |

## Phase 8: Adaptive Selection — RESOLVED in Phase 8

| # | Question | Recommendation / Resolution | Status |
|---|----------|-----------------------------|--------|
| 13 | State features at decision time | Cheap observable features: $n$, $|V_t|$, $f_t$, uncommitted suffix count, $|\Delta_t|$, $\alpha$, current cost $C(S_t)$, remaining budget, estimated 2-opt evals. Zero future information leakage. | ✅ Resolved in Phase 8 |
| 14 | Selection overhead budget | Charged **+1 candidate evaluation** per decision step for feature extraction and rule evaluation; tracked in all logs. | ✅ Resolved in Phase 8 |
| 15 | Oracle definition for regret | **Hindsight Oracle**: $\min(\text{Cost}_A, \text{Cost}_B)$ evaluated on identical instance/event streams. Regret = $\text{Cost}_{\text{Adaptive}} - \text{Cost}_{\text{Oracle}}$. | ✅ Resolved in Phase 8 |

## Additional Clarifications from Phase 2 Work

| # | Question | Resolution |
|---|----------|------------|
| 16 | Frozen prefix: how many vertices advance per step? | **Default: 1 vertex per event step**. Configurable in simulator; documented in RESEARCH_SPEC.md. |
| 17 | Zero-cost edges (coincident points)? | **Reject instance** or add ε=1e-9 jitter to coordinates. Generator spec handles this. |
| 18 | Duplicate vertex in event Δ_t? | **Ignore silently**; generator guarantees no duplicates. |
| 19 | Event at depot (v=0)? | **Impossible by construction**; V \ {0} only. |
| 20 | Empty initial route (V₀={0})? | **Supported**: insertion creates (0, v, 0). Cost = 2·c(0,v). |
| 21 | 2-opt variant: first-improvement vs best-improvement? | **First-improvement** (apply first improving move, restart scan). Documented in PSEUDOCODE.md. |
| 22 | 2-opt tie-breaking on equal delta? | **Earliest (i,j) in lexicographic order**. |
| 23 | 2-opt numerical stability threshold? | **ε = 1e-9**: only apply if delta < -ε. Prevents cycling on flat landscapes. |
| 24 | Computational budget for 2-opt in Strategy B? | **Run to local optimum** (no budget limit in spec). Budget limits applied in Phase 6 experiments. |

## Summary of Decisions Made in Phase 2

All Phase 2 questions are **resolved** with explicit definitions in:
- `docs/RESEARCH_SPEC.md` — formal problem specification
- `docs/NOTATION.md` — symbol table
- `docs/PSEUDOCODE.md` — algorithm pseudocode with complexity
- `docs/HAND_WORKED_EXAMPLE.md` — traceable 10-node example
- `tests/test_spec_examples.py` — executable verification

**No silent assumptions remain for Phase 2**. Remaining open questions are explicitly deferred to later phases with recommended defaults.