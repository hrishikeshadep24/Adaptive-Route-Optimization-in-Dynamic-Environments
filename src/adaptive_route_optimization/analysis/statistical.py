"""Rigorous Statistical Testing and Effect Size Calculation for Paired Experiments.

Performs parametric (paired t-test) and non-parametric (Wilcoxon signed-rank) tests,
normality verification, effect size estimation (Cohen's d_z, rank-biserial r),
and deterministic bootstrap confidence intervals.
References: MASTER_BLUEPRINT.md (Experimental design), PHASE_PLAN.md (Phase 7).
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Sequence
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class PairedTestResult:
    """Result of comparative hypothesis test between paired conditions."""
    metric_name: str
    sample_size: int
    mean_a: float
    mean_b: float
    mean_diff: float  # Mean(A - B)
    std_diff: float
    pct_impr_mean: float
    shapiro_pvalue: float
    is_normal: bool
    t_statistic: float
    t_pvalue: float
    cohens_d: float
    wilcoxon_statistic: float
    wilcoxon_pvalue: float
    rank_biserial_r: float
    ci_95_lower: float
    ci_95_upper: float
    statistically_significant_05: bool
    statistically_significant_01: bool
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_bootstrap_ci(
    differences: Sequence[float],
    confidence_level: float = 0.95,
    n_resamples: int = 10000,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute deterministic bootstrap confidence interval for the mean difference.

    Args:
        differences: Sequence of paired difference observations.
        confidence_level: Desired coverage probability (default 0.95).
        n_resamples: Number of bootstrap iterations.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    diff_arr = np.asarray(differences, dtype=float)
    if len(diff_arr) < 2:
        return float(diff_arr[0]), float(diff_arr[0])

    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_resamples)
    n = len(diff_arr)

    for i in range(n_resamples):
        sample = rng.choice(diff_arr, size=n, replace=True)
        boot_means[i] = sample.mean()

    alpha = 1.0 - confidence_level
    lower = float(np.percentile(boot_means, 100 * (alpha / 2.0)))
    upper = float(np.percentile(boot_means, 100 * (1.0 - alpha / 2.0)))
    return lower, upper


def run_paired_analysis(
    values_a: Sequence[float],
    values_b: Sequence[float],
    metric_name: str = "metric",
    seed: int = 42,
) -> PairedTestResult:
    """Execute comprehensive paired statistical comparison between Strategy A and B.

    Computes:
    - Normality check on differences (Shapiro-Wilk)
    - Paired t-test and Cohen's d_z: d_z = mean(diff) / std(diff)
    - Wilcoxon signed-rank test and matched-pairs rank-biserial correlation
    - 95% Bootstrap Confidence Interval for mean difference (A - B)

    Args:
        values_a: Sequence of measurements for Strategy A.
        values_b: Sequence of measurements for Strategy B (matched pairs).
        metric_name: Identifying name of the evaluated metric.
        seed: Random seed for deterministic bootstrap CI.

    Returns:
        PairedTestResult dataclass.
    """
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)

    if len(a) != len(b):
        raise ValueError(f"Lengths must match for paired analysis: len(a)={len(a)}, len(b)={len(b)}")

    n = len(a)
    diff = a - b  # diff > 0 means A > B (B is smaller/better for cost)
    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    mean_diff = float(np.mean(diff))
    std_diff = float(np.std(diff, ddof=1)) if n > 1 else 0.0

    # Percentage improvement of B over A: ((A - B) / A) * 100
    with np.errstate(divide="ignore", invalid="ignore"):
        pct_impr = np.where(a != 0, (a - b) / a * 100.0, 0.0)
    pct_impr_mean = float(np.mean(pct_impr))

    # Normality test
    if n >= 3 and not np.all(diff == diff[0]):
        shapiro_stat, shapiro_p = stats.shapiro(diff)
    else:
        shapiro_p = 1.0
    is_normal = bool(shapiro_p >= 0.05)

    # Paired t-test
    if n >= 2 and std_diff > 1e-12:
        t_stat, t_p = stats.ttest_rel(a, b)
        cohens_d = float(mean_diff / std_diff)
    else:
        t_stat, t_p = 0.0, 1.0
        cohens_d = 0.0

    # Wilcoxon signed-rank test
    non_zero_diffs = diff[np.abs(diff) > 1e-12]
    if len(non_zero_diffs) >= 5:
        try:
            wilc_res = stats.wilcoxon(a, b, alternative="two-sided")
            wilc_stat = float(wilc_res.statistic)
            wilc_p = float(wilc_res.pvalue)

            # Matched-pairs rank-biserial correlation
            # r = (sum(pos_ranks) - sum(neg_ranks)) / total_rank_sum
            ranks = stats.rankdata(np.abs(non_zero_diffs))
            w_pos = np.sum(ranks[non_zero_diffs > 0])
            w_neg = np.sum(ranks[non_zero_diffs < 0])
            w_total = w_pos + w_neg
            rank_biserial_r = float((w_pos - w_neg) / w_total) if w_total > 0 else 0.0

        except Exception:
            wilc_stat, wilc_p, rank_biserial_r = 0.0, 1.0, 0.0
    else:
        wilc_stat, wilc_p, rank_biserial_r = 0.0, 1.0, 0.0

    # Primary p-value: use t_p if normal, else wilcoxon_p
    primary_p = t_p if is_normal else wilc_p
    sig_05 = bool(primary_p < 0.05)
    sig_01 = bool(primary_p < 0.01)

    # Bootstrap 95% CI
    ci_lower, ci_upper = compute_bootstrap_ci(diff, confidence_level=0.95, seed=seed)

    # Descriptive interpretation
    if sig_05:
        dir_str = "significantly lower (better)" if mean_diff > 0 else "significantly higher (worse)"
        interp = f"Strategy B is {dir_str} on {metric_name} (p={primary_p:.4e}, effect={cohens_d:.2f})"
    else:
        interp = f"No statistically significant difference between A and B on {metric_name} (p={primary_p:.4f})"

    return PairedTestResult(
        metric_name=metric_name,
        sample_size=n,
        mean_a=mean_a,
        mean_b=mean_b,
        mean_diff=mean_diff,
        std_diff=std_diff,
        pct_impr_mean=pct_impr_mean,
        shapiro_pvalue=float(shapiro_p),
        is_normal=is_normal,
        t_statistic=float(t_stat),
        t_pvalue=float(t_p),
        cohens_d=cohens_d,
        wilcoxon_statistic=wilc_stat,
        wilcoxon_pvalue=wilc_p,
        rank_biserial_r=rank_biserial_r,
        ci_95_lower=ci_lower,
        ci_95_upper=ci_upper,
        statistically_significant_05=sig_05,
        statistically_significant_01=sig_01,
        interpretation=interp,
    )


def run_full_statistical_battery(paired_df: pd.DataFrame) -> pd.DataFrame:
    """Run paired hypothesis tests across all primary research metrics.

    Metrics evaluated:
    - Route cost (final_cost)
    - Total computational effort (total_computational_effort)
    - Response time (total_response_time_ms)
    - Route disruption (mean_disruption)
    """
    tests = [
        ("final_cost", "Route Cost"),
        ("total_computational_effort", "Computational Effort"),
        ("total_response_time_ms", "Response Time (ms)"),
        ("mean_disruption", "Mean Disruption"),
    ]

    results = []
    for col, name in tests:
        res = run_paired_analysis(
            paired_df[f"{col}_A"],
            paired_df[f"{col}_B"],
            metric_name=name,
        )
        results.append(res.to_dict())

    return pd.DataFrame(results)
