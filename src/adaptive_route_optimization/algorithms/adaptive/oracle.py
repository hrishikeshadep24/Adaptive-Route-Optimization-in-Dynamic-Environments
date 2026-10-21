"""Oracle Upper-Bound and Regret Analysis for Adaptive Strategy Selection.

Defines the hindsight oracle benchmark and computes quantitative regret for
the adaptive strategy selector against this theoretical upper bound.
References: MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phase 8), OPEN_QUESTIONS.md (#15).
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RegretSummary:
    """Summary of regret metrics across evaluated instances."""
    total_instances: int
    mean_cost_adaptive: float
    mean_cost_oracle: float
    mean_cost_strategy_a: float
    mean_cost_strategy_b: float
    mean_absolute_regret: float  # Mean(Cost_Adaptive - Cost_Oracle)
    median_absolute_regret: float
    max_absolute_regret: float
    mean_relative_regret_pct: float  # Mean((Cost_Adaptive - Cost_Oracle) / Cost_Oracle * 100)
    zero_regret_rate_pct: float  # Percentage of instances where Adaptive achieved Oracle cost (Regret == 0)
    better_than_strategy_a_pct: float
    better_than_strategy_b_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OracleEvaluator:
    """Computes hindsight oracle benchmarks and selector regret.

    IMPORTANT NOTE ON RESEARCH INTEGRITY:
    The Oracle is an offline, after-the-fact theoretical bound. It selects
    the minimum cost between Strategy A and Strategy B in hindsight.
    It CANNOT be deployed in reality, because it relies on observing
    both execution futures. It serves strictly as a performance benchmark.
    """

    @staticmethod
    def compute_instance_oracle_and_regret(
        triplet_df: pd.DataFrame,
        tolerance: float = 1e-6,
    ) -> pd.DataFrame:
        """Calculate per-instance oracle costs and adaptive regret.

        Expects a DataFrame containing runs for 'A', 'B', and 'ADAPTIVE' (or pivoted columns).
        If triplet_df contains 'strategy', it pivots on [condition_id, seed].

        Returns:
            DataFrame with instance-level costs for A, B, ADAPTIVE, ORACLE, and REGRET.
        """
        if "strategy" in triplet_df.columns:
            possible_values = ["final_cost", "total_computational_effort", "total_response_time_ms", "mean_disruption"]
            pivot_values = [col for col in possible_values if col in triplet_df.columns]
            if not pivot_values:
                pivot_values = ["final_cost"]
            piv = triplet_df.pivot(
                index=["condition_id", "seed", "total_vertices", "dynamicity"],
                columns="strategy",
                values=pivot_values,
            ).reset_index()

            # Flatten columns
            flat_cols = []
            for col in piv.columns:
                if col[1]:
                    flat_cols.append(f"{col[0]}_{col[1]}")
                else:
                    flat_cols.append(col[0])
            piv.columns = flat_cols
            df = piv
        else:
            df = triplet_df.copy()

        # Oracle cost is min(Cost_A, Cost_B) in hindsight
        df["cost_oracle"] = np.minimum(df["final_cost_A"], df["final_cost_B"])
        df["oracle_best_strategy"] = np.where(
            df["final_cost_B"] < (df["final_cost_A"] - tolerance),
            "B",
            np.where(df["final_cost_A"] < (df["final_cost_B"] - tolerance), "A", "TIE"),
        )

        # Regret = Cost_Adaptive - Cost_Oracle
        df["cost_regret"] = df["final_cost_ADAPTIVE"] - df["cost_oracle"]
        df["cost_regret_pct"] = (df["cost_regret"] / df["cost_oracle"]) * 100.0

        # Success flags
        df["adaptive_matched_oracle"] = df["cost_regret"].abs() <= tolerance
        df["adaptive_beat_A"] = df["final_cost_ADAPTIVE"] < (df["final_cost_A"] - tolerance)
        df["adaptive_beat_B"] = df["final_cost_ADAPTIVE"] < (df["final_cost_B"] - tolerance)

        return df

    @staticmethod
    def summarize_regret(evaluated_df: pd.DataFrame) -> RegretSummary:
        """Compute aggregate summary of selector regret metrics."""
        n = len(evaluated_df)
        if n == 0:
            raise ValueError("Evaluated DataFrame is empty")

        cost_adapt = float(evaluated_df["final_cost_ADAPTIVE"].mean())
        cost_oracle = float(evaluated_df["cost_oracle"].mean())
        cost_a = float(evaluated_df["final_cost_A"].mean())
        cost_b = float(evaluated_df["final_cost_B"].mean())

        regrets = evaluated_df["cost_regret"]
        mean_regret = float(regrets.mean())
        median_regret = float(regrets.median())
        max_regret = float(regrets.max())

        pct_regrets = evaluated_df["cost_regret_pct"]
        mean_pct_regret = float(pct_regrets.mean())

        zero_regret_rate = float((evaluated_df["adaptive_matched_oracle"].sum() / n) * 100.0)
        beat_a_rate = float((evaluated_df["adaptive_beat_A"].sum() / n) * 100.0)
        beat_b_rate = float((evaluated_df["adaptive_beat_B"].sum() / n) * 100.0)

        return RegretSummary(
            total_instances=n,
            mean_cost_adaptive=cost_adapt,
            mean_cost_oracle=cost_oracle,
            mean_cost_strategy_a=cost_a,
            mean_cost_strategy_b=cost_b,
            mean_absolute_regret=mean_regret,
            median_absolute_regret=median_regret,
            max_absolute_regret=max_regret,
            mean_relative_regret_pct=mean_pct_regret,
            zero_regret_rate_pct=zero_regret_rate,
            better_than_strategy_a_pct=beat_a_rate,
            better_than_strategy_b_pct=beat_b_rate,
        )
