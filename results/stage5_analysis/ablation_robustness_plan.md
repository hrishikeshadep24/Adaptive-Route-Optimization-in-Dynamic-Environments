# Stage 5 Ablation and Robustness Experimental Plan

## 1. Scientific Motivation & Identified Gaps

The 280-run Stage 4 campaign revealed three critical empirical phenomena that require focused follow-up investigation:
1. **Strategy C Budget Starvation Threshold:** Strategy C (Suffix Destroy-and-Repair) performs identically to Strategy A under $B=50$ and $B=100$, but achieves top-tier solution quality under unbounded budget (682.38 vs 744.86). We need to determine the exact budget threshold $B^* \in [100, 1000]$ where LNS becomes computationally viable.
2. **Strategy C Component Ablation:** Does Regret-2 repair justify its quadratic cost over Cheapest Insertion repair? How does Shaw-relatedness removal compare to Uniform Random removal?
3. **Strategy B Local Search Intensity:** How many 2-opt passes or moves are needed to capture 90% of local search improvements? (Pass limit $P \in \{1, 2, 5\}$ vs evaluation budget).
4. **Sample Size Scaling for Confirmatory Power:** The current $N=5$ seeds per condition provide exploratory evidence but lack statistical power to confirm small-to-moderate effect sizes under multiple testing adjustments. Scaling to $N=30$ seeds on key representative conditions is required for journal publication.

## 2. Proposed Experiment Matrix (Minimal Non-Redundant Design)

### Experiment Series 1: Strategy C Operator Ablation (Fixed Suffix, $N=10$ seeds)
- **Goal:** Isolate the individual contributions of Destroy (Random vs Shaw) and Repair (Cheapest vs Regret-2).
- **Conditions:** Synthetic Uniform ($n=50, \alpha=0.4$) and Clustered ($n=50, \alpha=0.4, k=3$).
- **Factorial Variants (4 operators):**
  1. C1: Random Destroy + Cheapest Repair
  2. C2: Random Destroy + Regret-2 Repair (Standard Stage 4)
  3. C3: Shaw Destroy + Cheapest Repair
  4. C4: Shaw Destroy + Regret-2 Repair
- **Budget:** Unbounded and Bounded ($B=500$).
- **Run Count:** 2 conditions $\times$ 2 budget levels $\times$ 10 seeds $\times$ 4 operator variants = **160 runs**.

### Experiment Series 2: Computational Budget Sensitivity & Threshold Frontier
- **Goal:** Trace the performance frontier across fine-grained candidate evaluation budgets.
- **Conditions:** Synthetic Uniform ($n=50, \alpha=0.4$) and Clustered ($n=50, \alpha=0.4$).
- **Budget Grid ($B$ per step):** $B \in \{25, 50, 100, 200, 500, 1000, 2500\}$.
- **Strategies:** A, B, C, ADAPTIVE.
- **Seeds:** 5 seeds per condition.
- **Run Count:** 2 conditions $\times$ 7 budget levels $\times$ 5 seeds $\times$ 4 strategies = **280 runs**.

### Experiment Series 3: Inferential Statistical Scaling ($N=30$ Seeds)
- **Goal:** Establish confirmatory hypothesis tests ($p < 0.05$ with Holm-Bonferroni correction and tight 95% CIs) for journal claims.
- **Target Conditions (4 core representative regimes):**
  1. Uniform Low Dynamicity ($n=50, \alpha=0.2, B=100$)
  2. Uniform High Dynamicity ($n=50, \alpha=0.6, B=100$)
  3. Clustered High Dynamicity ($n=50, \alpha=0.6, B=100$)
  4. TSPLIB Berlin52 ($n=51, \alpha=0.4, B=100$)
- **Strategies:** A, B, C, ADAPTIVE.
- **Seeds:** 30 seeds per condition (subtracting the 5 existing seeds = 25 new seeds).
- **Run Count:** 4 conditions $\times$ 25 new seeds $\times$ 4 strategies = **400 runs**.

## 3. Summary of Proposed Follow-Up Campaign

| Experiment Series | Purpose | Conditions | Seeds | Strategies | Estimated Runs | Priority |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Series 1: Strategy C Operator Ablation** | Deconstruct LNS operator contributions | 2 | 10 | 4 variants | 160 | High |
| **Series 2: Budget Sensitivity Frontier** | Identify activation threshold $B^*$ | 2 | 5 | A, B, C, Adapt | 280 | High |
| **Series 3: Inferential Power Scaling ($N=30$)** | Journal-level confirmatory rigor | 4 | 25 new | A, B, C, Adapt | 400 | Medium |
| **Total Proposed Follow-Up Runs** | | | | | **840 runs** | |

> [!IMPORTANT]
> **Execution Gate:** This plan is submitted for review and approval. None of these follow-up runs have been launched.
