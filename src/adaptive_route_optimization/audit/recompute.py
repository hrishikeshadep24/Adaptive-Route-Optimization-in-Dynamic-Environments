"""Independent Recomputation Engine for Research Audit.

Loads raw experiment outputs and recalculates all statistical metrics,
paired comparisons, hypothesis tests, and trade-offs directly from first principles.
"""

from __future__ import annotations
import json
import math
import os
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats


class RawDataRecomputer:
    """Calculates all audited metrics directly from raw CSV/JSON files."""

    def __init__(
        self,
        pilot_runs_path: str = "results/pilot_matrix/runs.csv",
        pilot_steps_path: str = "results/pilot_matrix/steps.csv",
        pilot_manifest_path: str = "results/pilot_matrix/manifest.json",
        budgeted_runs_path: str = "results/budgeted_pilot/runs.csv",
        held_out_runs_path: str = "results/held_out_matrix/runs.csv",
        held_out_steps_path: str = "results/held_out_matrix/steps.csv",
        held_out_manifest_path: str = "results/held_out_matrix/manifest.json",
    ) -> None:
        self.pilot_runs_path = pilot_runs_path
        self.pilot_steps_path = pilot_steps_path
        self.pilot_manifest_path = pilot_manifest_path
        self.budgeted_runs_path = budgeted_runs_path
        self.held_out_runs_path = held_out_runs_path
        self.held_out_steps_path = held_out_steps_path
        self.held_out_manifest_path = held_out_manifest_path

        # Lazy loaded DataFrames
        self._df_pilot_runs: pd.DataFrame | None = None
        self._df_pilot_steps: pd.DataFrame | None = None
        self._pilot_manifest: dict[str, Any] | None = None
        self._df_budgeted: pd.DataFrame | None = None
        self._df_held_out_runs: pd.DataFrame | None = None
        self._df_held_out_steps: pd.DataFrame | None = None
        self._held_out_manifest: dict[str, Any] | None = None

    @property
    def pilot_runs(self) -> pd.DataFrame:
        if self._df_pilot_runs is None:
            self._df_pilot_runs = pd.read_csv(self.pilot_runs_path)
        return self._df_pilot_runs

    @property
    def pilot_steps(self) -> pd.DataFrame:
        if self._df_pilot_steps is None:
            self._df_pilot_steps = pd.read_csv(self.pilot_steps_path)
        return self._df_pilot_steps

    @property
    def pilot_manifest(self) -> dict[str, Any]:
        if self._pilot_manifest is None:
            with open(self.pilot_manifest_path, "r", encoding="utf-8") as f:
                self._pilot_manifest = json.load(f)
        return self._pilot_manifest

    @property
    def budgeted_runs(self) -> pd.DataFrame:
        if self._df_budgeted is None:
            self._df_budgeted = pd.read_csv(self.budgeted_runs_path)
        return self._df_budgeted

    @property
    def held_out_runs(self) -> pd.DataFrame:
        if self._df_held_out_runs is None:
            self._df_held_out_runs = pd.read_csv(self.held_out_runs_path)
        return self._df_held_out_runs

    @property
    def held_out_steps(self) -> pd.DataFrame:
        if self._df_held_out_steps is None:
            self._df_held_out_steps = pd.read_csv(self.held_out_steps_path)
        return self._df_held_out_steps

    @property
    def held_out_manifest(self) -> dict[str, Any]:
        if self._held_out_manifest is None:
            with open(self.held_out_manifest_path, "r", encoding="utf-8") as f:
                self._held_out_manifest = json.load(f)
        return self._held_out_manifest

    # -----------------------------------------------------------------------
    # Pilot Matrix Paired Dataset
    # -----------------------------------------------------------------------
    def get_pilot_paired_df(self) -> pd.DataFrame:
        """Construct matched pairs on [condition_id, seed] for Strategy A and B."""
        df = self.pilot_runs
        a_runs = df[df["strategy"] == "A"].set_index(["condition_id", "seed"])
        b_runs = df[df["strategy"] == "B"].set_index(["condition_id", "seed"])
        paired = a_runs.join(b_runs, lsuffix="_A", rsuffix="_B").reset_index()
        paired["cost_diff"] = paired["final_cost_A"] - paired["final_cost_B"]
        paired["impr_pct"] = (paired["cost_diff"] / paired["final_cost_A"]) * 100.0
        return paired

    # -----------------------------------------------------------------------
    # Held-Out Matrix Triplet Dataset
    # -----------------------------------------------------------------------
    def get_held_out_triplet_df(self) -> pd.DataFrame:
        """Construct matched triplets on [condition_id, seed] for A, B, and ADAPTIVE."""
        df = self.held_out_runs
        piv = df.pivot(
            index=["condition_id", "seed", "total_vertices", "dynamicity"],
            columns="strategy",
            values=["final_cost", "total_computational_effort", "total_response_time_ms", "mean_disruption"],
        ).reset_index()

        flat_cols = []
        for col in piv.columns:
            if col[1]:
                flat_cols.append(f"{col[0]}_{col[1]}")
            else:
                flat_cols.append(col[0])
        piv.columns = flat_cols

        piv["oracle_cost"] = np.minimum(piv["final_cost_A"], piv["final_cost_B"])
        piv["cost_regret"] = piv["final_cost_ADAPTIVE"] - piv["oracle_cost"]
        piv["beat_both"] = (piv["final_cost_ADAPTIVE"] < piv["final_cost_A"]) & (piv["final_cost_ADAPTIVE"] < piv["final_cost_B"])
        return piv

    # -----------------------------------------------------------------------
    # Metric Calculation Dispatch
    # -----------------------------------------------------------------------
    def recompute_all(self) -> dict[str, Any]:
        """Compute all inventory metrics directly from raw files."""
        results: dict[str, Any] = {}
        df_pilot = self.pilot_runs
        df_steps = self.pilot_steps
        paired_pilot = self.get_pilot_paired_df()
        df_budget = self.budgeted_runs
        df_held = self.held_out_runs
        triplet_held = self.get_held_out_triplet_df()

        # Phase 6
        results["P6_RUNS_TOTAL"] = len(df_pilot)
        results["P6_FAILED_RUNS"] = self.pilot_manifest.get("failed_runs", 0)
        results["P6_CONDITIONS_COUNT"] = df_pilot["condition_id"].nunique()
        results["P6_SEEDS_COUNT"] = df_pilot["seed"].nunique()
        results["P6_TOTAL_EVENT_STEPS"] = len(df_steps)

        # Phase 7 Statistical Battery
        cost_a = paired_pilot["final_cost_A"]
        cost_b = paired_pilot["final_cost_B"]
        diff = paired_pilot["cost_diff"]

        results["P7_COST_A_MEAN"] = float(cost_a.mean())
        results["P7_COST_B_MEAN"] = float(cost_b.mean())
        results["P7_COST_PAIRED_DIFF_MEAN"] = float(diff.mean())

        # Hypothesis Tests
        t_stat, t_pval = stats.ttest_rel(cost_a, cost_b)
        w_stat, w_pval = stats.wilcoxon(cost_a, cost_b)
        results["P7_PVAL_PAIRED_TTEST"] = float(t_pval)
        results["P7_PVAL_WILCOXON"] = float(w_pval)

        # Effect Size (Cohen's d_z)
        results["P7_COHEN_DZ_COST"] = float(diff.mean() / diff.std(ddof=1))

        # Computational Effort
        results["P7_EVALS_A_MEAN"] = float(df_pilot[df_pilot["strategy"] == "A"]["total_computational_effort"].mean())
        results["P7_EVALS_B_MEAN"] = float(df_pilot[df_pilot["strategy"] == "B"]["total_computational_effort"].mean())
        results["P7_RESP_TIME_A_MEAN"] = float(df_pilot[df_pilot["strategy"] == "A"]["total_response_time_ms"].mean())
        results["P7_RESP_TIME_B_MEAN"] = float(df_pilot[df_pilot["strategy"] == "B"]["total_response_time_ms"].mean())

        # Route Disruption
        results["P7_DISRUPT_A_MEAN"] = float(df_pilot[df_pilot["strategy"] == "A"]["mean_disruption"].mean())
        results["P7_DISRUPT_B_MEAN"] = float(df_pilot[df_pilot["strategy"] == "B"]["mean_disruption"].mean())

        # Regime comparisons (Phase 7)
        low_dyn = paired_pilot[paired_pilot["dynamicity_A"] <= 0.2]
        high_dyn = paired_pilot[paired_pilot["dynamicity_A"] >= 0.6]

        results["P7_LOW_DYN_WIN_RATE"] = float((low_dyn["final_cost_B"] < low_dyn["final_cost_A"]).mean() * 100.0)
        results["P7_LOW_DYN_IMPR_MEAN"] = float(low_dyn["impr_pct"].mean())

        results["P7_HIGH_DYN_INFERIOR_RATE"] = float((high_dyn["final_cost_B"] > high_dyn["final_cost_A"]).mean() * 100.0)
        results["P7_HIGH_DYN_COST_PENALTY"] = float(high_dyn["impr_pct"].mean())

        # Budget Cap Ablation (Phase 7)
        # In budgeted_pilot: compare cap 500 and cap 200 vs unbounded Strategy B and Strategy A
        # Conditions are n=50, alpha=0.4
        a_unbounded = df_budget[df_budget["strategy"] == "A"]["final_cost"].mean()
        b_unbounded = df_budget[(df_budget["strategy"] == "B") & (df_budget["budget_type"] == "unbounded")]["final_cost"].mean()
        b_cap500 = df_budget[(df_budget["strategy"] == "B") & (df_budget["budget_limit"] == 500.0)]["final_cost"].mean()

        evals_unbounded = df_budget[(df_budget["strategy"] == "B") & (df_budget["budget_type"] == "unbounded")]["total_computational_effort"].mean()
        evals_cap500 = df_budget[(df_budget["strategy"] == "B") & (df_budget["budget_limit"] == 500.0)]["total_computational_effort"].mean()

        max_impr = a_unbounded - b_unbounded
        cap500_impr = a_unbounded - b_cap500
        results["P7_BUDGET_500_IMPR_CAPTURE"] = float((cap500_impr / max_impr) * 100.0)
        results["P7_BUDGET_500_EVAL_SAVINGS"] = float(((evals_unbounded - evals_cap500) / evals_unbounded) * 100.0)

        # Phase 8 Held-Out
        results["P8_HELD_OUT_RUNS_TOTAL"] = len(df_held)
        results["P8_HELD_OUT_INSTANCES"] = len(triplet_held)

        results["P8_COST_A_MEAN"] = float(df_held[df_held["strategy"] == "A"]["final_cost"].mean())
        results["P8_COST_B_MEAN"] = float(df_held[df_held["strategy"] == "B"]["final_cost"].mean())
        results["P8_COST_ADAPTIVE_MEAN"] = float(df_held[df_held["strategy"] == "ADAPTIVE"]["final_cost"].mean())

        evals_a_p8 = float(df_held[df_held["strategy"] == "A"]["total_computational_effort"].mean())
        evals_b_p8 = float(df_held[df_held["strategy"] == "B"]["total_computational_effort"].mean())
        evals_adapt_p8 = float(df_held[df_held["strategy"] == "ADAPTIVE"]["total_computational_effort"].mean())

        results["P8_EVALS_A_MEAN"] = evals_a_p8
        results["P8_EVALS_B_MEAN"] = evals_b_p8
        results["P8_EVALS_ADAPTIVE_MEAN"] = evals_adapt_p8
        results["P8_EVAL_SAVINGS_VS_B_PCT"] = float(((evals_b_p8 - evals_adapt_p8) / evals_b_p8) * 100.0)

        results["P8_DISRUPT_ADAPTIVE_MEAN"] = float(df_held[df_held["strategy"] == "ADAPTIVE"]["mean_disruption"].mean())
        results["P8_FEASIBILITY_RATE"] = float(df_held["all_feasible"].mean() * 100.0)

        results["P8_BEAT_BOTH_INSTANCES"] = int(triplet_held["beat_both"].sum())
        results["P8_BEAT_BOTH_PCT"] = float((triplet_held["beat_both"].sum() / len(triplet_held)) * 100.0)

        results["P8_ORACLE_MEAN_COST"] = float(triplet_held["oracle_cost"].mean())
        results["P8_MEAN_REGRET"] = float(triplet_held["cost_regret"].mean())

        # Regime-specific savings (Phase 8)
        high_dyn_p8 = triplet_held[triplet_held["dynamicity"] >= 0.6]
        mod_dyn_p8 = triplet_held[triplet_held["dynamicity"] == 0.4]

        high_b_evals = high_dyn_p8["total_computational_effort_B"].mean()
        high_adapt_evals = high_dyn_p8["total_computational_effort_ADAPTIVE"].mean()
        results["P8_HIGH_DYN_EFFORT_SAVINGS"] = float(((high_b_evals - high_adapt_evals) / high_b_evals) * 100.0)

        mod_b_evals = mod_dyn_p8["total_computational_effort_B"].mean()
        mod_adapt_evals = mod_dyn_p8["total_computational_effort_ADAPTIVE"].mean()
        results["P8_MOD_DYN_EFFORT_SAVINGS"] = float(((mod_b_evals - mod_adapt_evals) / mod_b_evals) * 100.0)

        return results
