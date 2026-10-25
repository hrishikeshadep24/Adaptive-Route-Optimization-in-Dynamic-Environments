# Research Findings and Ablation Report

**Project**: Adaptive Route Optimization in Dynamic Environments  
**Phase**: Phase 7 — Research Analysis & Ablation  
**Date**: 2026-10-21  
**Dataset Analyzed**: `results/pilot_matrix/runs.csv` (60 runs, 30 matched pairs), `results/pilot_matrix/steps.csv` (2,070 event steps), `results/budgeted_pilot/runs.csv` (12 runs).

---

## 1. Executive Summary

This report presents a controlled empirical study comparing two fundamental route-update strategies under the single-route dynamic TSP with a frozen-prefix execution rule:
- **Strategy A**: Greedy (Cheapest) Insertion Repair.
- **Strategy B**: Greedy (Cheapest) Insertion followed by First-Improvement 2-opt Local Search.

Both strategies were executed under **identical problem instances, seeds, and dynamic event sequences** across 10 condition configurations ($n \in \{50, 100, 200\}$, $\alpha \in \{0.1, 0.2, 0.4, 0.6, 0.8\}$) and 3 random seeds ($N = 30$ matched pairs).

---

## 2. Statistical Comparison Battery

All comparative metrics are calculated pairwise on matched instances ($N = 30$). Differences are defined as $\Delta = \text{Metric}(A) - \text{Metric}(B)$ such that positive values indicate that Strategy A is larger (and Strategy B is lower/better for cost).

| Metric | Strategy A Mean (SD) | Strategy B Mean (SD) | Mean Paired Diff | 95% Bootstrap CI | Paired Test (p-value) | Effect Size | Stat. Sig. (α=0.05)? |
|---|---|---|---|---|---|---|---|
| **Route Cost** | 984.99 (267.43) | 960.08 (256.32) | +24.91 | [-11.49, +59.15] | Paired t: $p = 0.1975$<br>Wilcoxon: $p = 0.1579$ | Cohen's $d_z = 0.24$<br>Rank-biserial $r = 0.30$ | **No (Non-significant)** |
| **Computational Effort** (evals) | 2,497.0 (2,739.1) | 198,755.4 (324,570.6) | -196,258.4 | [-321,457, -89,604] | Wilcoxon: $p = 1.86 \times 10^{-9}$ | Rank-biserial $r = -1.0$<br>Cohen's $d_z = -0.60$ | **Yes (p < 0.001)** |
| **Response Time** (ms) | 40.34 (40.54) | 4,469.99 (7,335.63) | -4,429.65 | [-7,252.6, -2,011.1] | Wilcoxon: $p = 1.86 \times 10^{-9}$ | Rank-biserial $r = -1.0$<br>Cohen's $d_z = -0.60$ | **Yes (p < 0.001)** |
| **Mean Route Disruption** (δ) | 0.0367 (0.0152) | 0.0794 (0.0436) | -0.0428 | [-0.0600, -0.0282] | Wilcoxon: $p = 1.86 \times 10^{-9}$ | Rank-biserial $r = -1.0$<br>Cohen's $d_z = -0.93$ | **Yes (p < 0.001)** |

*Data source: `results/tables/statistical_battery.csv`.*

---

## 3. Evidence-Backed Findings

### Finding 1: Strategy B Strongly Outperforms Strategy A at Low Dynamicity
- **Evidence**: At low dynamicity ($\alpha \le 0.2$), Strategy B achieved a **100% win rate** (12 out of 12 runs), with a mean route cost improvement of **+10.86%** ($\text{median} = +10.87\%$, range: $+0.69\%$ to $+18.11\%$).
- **Explanation**: When 80% to 90% of the customer vertices are known initially, 2-opt produces a high-quality global tour structure that requires only minor, low-cost repairs as rare new events arrive.
- **Citations**: Table `results/tables/ablation_by_regime.csv` (Row 3); Figures `results/figures/fig1_dynamicity_vs_cost.png`, `results/figures/fig6_paired_comparison.png`.

### Finding 2: Exponential Computational Scaling of Unbounded 2-opt
- **Evidence**: Across all runs, Strategy B required a mean of **198,755 candidate evaluations** compared to **2,497** for Strategy A ($49.1\times$ to $75.1\times$ increase; $p = 1.86 \times 10^{-9}$). Total update response time increased from **40.3 ms** to **4,470.0 ms** ($110.8\times$ slower).
- At problem size $n=200$, Strategy B required up to **1,223,733 candidate evaluations** and **27.5 seconds** per run, compared to **993 evaluations** and **0.12 seconds** for Strategy A ($229\times$ runtime difference).
- **Citations**: Table `results/tables/scalability_by_size.csv`; Figures `results/figures/fig4_size_vs_runtime.png`, `results/figures/fig8_quality_vs_computation_tradeoff.png`.

### Finding 3: Route Disruption Volatility
- **Evidence**: Strategy A maintains minimal route disruption across all conditions ($\text{mean } \delta_A = 0.0367$, standard deviation 0.0152). Strategy B induces more than double the structural route disruption ($\text{mean } \delta_B = 0.0794$, standard deviation 0.0436, $p = 1.86 \times 10^{-9}$, Cohen's $d_z = -0.93$).
- **Explanation**: Strategy A only breaks 1 existing edge to insert a new vertex ($O(1)$ edge alterations per event). Strategy B performs repeated 2-opt edge inversions across the uncommitted suffix, breaking up to $k$ edges per event step.
- **Citations**: Table `results/tables/statistical_battery.csv` (Row 5); Figure `results/figures/fig7_route_disruption.png`.

### Finding 4 (Budget Cap Ablation): Diminishing Marginal Returns of 2-opt
- **Evidence**: In `results/budgeted_pilot/runs.csv` ($n=50, \alpha=0.4$), capping Strategy B to **500 candidate evaluations per update** achieved **96.3%** of the cost reduction of unbounded 2-opt while reducing candidate evaluations by **32.3%** (9,962 vs 14,714).
- Capping at **200 evaluations** captured **73.1%** of the improvement while reducing evaluations by **72.8%** (4,000 vs 14,714).
- **Citations**: Table `results/tables/budget_ablation.csv`; Figure `results/figures/fig9_budget_ablation.png`.

---

## 4. Limitation & Non-Significant Result: The Myopic Local Search Trap

### Non-Significant Pooled Route Cost Difference
Across all 30 paired experimental runs, the overall route cost difference between Strategy A and Strategy B is **NOT statistically significant** ($p = 0.1975$, paired t-test; $p = 0.1579$, Wilcoxon signed-rank). The 95% bootstrap confidence interval $[-11.49, +59.15]$ spans zero.

### Systematic Failure at High Dynamicity ($\alpha \ge 0.6$)
At high dynamicity:
- Strategy B was **inferior to Strategy A in 66.7% of cases** (6 out of 9 runs).
- The average cost change was **-5.01%** (Strategy B produced tours that were on average 5% *longer* than greedy insertion).
- In the worst case ($n=50, \alpha=0.6$, seed 777), Strategy B produced a tour cost of **912.87**, compared to **782.24** for Strategy A (**22.18% worse**).

### Mechanistic Analysis
Under the frozen-prefix execution model:
1. At early timesteps $t$, Strategy B performs intensive 2-opt local search to construct a tour that is locally optimal for the small subset of currently revealed vertices $V_t$.
2. As the vehicle advances, it freezes edges along this locally optimal tour.
3. When dynamicity is high ($\alpha \ge 0.6$), 60% to 80% of customer vertices have not yet arrived. The vehicle's frozen prefix commits it to a physical path that becomes a "trap" for newly arriving vertices, necessitating long-distance zigzag detours.
4. Strategy A, by only greedily inserting vertices into the existing sequence, preserves more spatial flexibility across the uncommitted suffix.

---

## 5. Summary of Ablation Regimes

| Dynamicity Regime | N (Pairs) | Strategy B Win Rate | Mean % Improvement | Median % Improvement | Effort Multiplier (B/A) | Recommendation |
|---|---|---|---|---|---|---|
| **Low (α ≤ 0.2)** | 12 | **100.0%** (12/12) | **+10.86%** | +10.87% | $75.1\times$ | **Use Strategy B** (clear, decisive quality advantage). |
| **Moderate (α = 0.4)** | 9 | **55.6%** (5/9) | **+1.18%** | +1.60% | $48.2\times$ | **Budget-capped Strategy B** (diminishing returns). |
| **High (α ≥ 0.6)** | 9 | **33.3%** (3/9) | **-5.01%** | -2.44% | $15.2\times$ | **Use Strategy A** (Strategy B is detrimental and expensive). |

*Data source: `results/tables/ablation_by_regime.csv`.*

---

## 6. Implications for Future Phases

1. **Phase 8 (Adaptive Strategy Selection)**:
   The discovery that Strategy B's superiority is strictly condition-dependent provides strong, empirical motivation for an adaptive selector in Phase 8. A simple rule based on dynamicity ($\alpha \le 0.2 \to \text{Strategy B}$; $\alpha \ge 0.6 \to \text{Strategy A}$) is indicated by this data.
2. **Computational Budget Control**:
   Unbounded 2-opt is computationally prohibitive at $n \ge 200$. Fixed candidate evaluation budgets (e.g. 500 evals/update) provide superior Pareto-efficiency.
