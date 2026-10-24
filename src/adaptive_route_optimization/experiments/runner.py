"""Batch Experiment Runner for Dynamic Route Optimization.



Executes full condition matrices across multiple seeds, strictly enforcing

identical instance and event sequence comparison between strategies.

Outputs structured CSV, JSON, manifest, summary, and paired comparison files

with failure recovery.

References: RESEARCH_SPEC.md, MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phase 6 / Stage 4).

"""



from __future__ import annotations

import csv

import json

import logging

import math

import os

import time

from datetime import datetime

from typing import Any, Callable, Optional, Sequence



import numpy as np

import pandas as pd

from scipy import stats



from adaptive_route_optimization.models.instance import Instance

from adaptive_route_optimization.simulation.events import EventConfig, EventGenerator, EventSequence

from adaptive_route_optimization.simulation.simulator import Simulator, Strategy, SimulationResult

from adaptive_route_optimization.experiments.schema import (

    BudgetType,

    ConditionConfig,

    ExperimentConfig,

    RunRecord,

    StepRecord,

)

from adaptive_route_optimization.experiments.manifest import (

    ExperimentManifest,

    create_manifest,

    get_git_commit_hash,

)



logger = logging.getLogger(__name__)





def compute_scenario_fingerprint(instance: Instance, event_sequence: EventSequence) -> str:
    """Compute a deterministic SHA-256 hex digest uniquely identifying the scenario realization."""
    import hashlib
    h = hashlib.sha256()
    # Explicitly encode depot, full coordinates, initial known vertices, and exact arrival/batch ordering
    depot_x, depot_y = instance.coords[0]
    h.update(f"depot:{depot_x:.6f},{depot_y:.6f}|".encode("utf-8"))
    coords_str = ";".join(f"{x:.6f},{y:.6f}" for x, y in instance.coords)
    h.update(f"coords:{coords_str}|".encode("utf-8"))
    init_str = ",".join(str(v) for v in sorted(event_sequence.initial_known))
    h.update(f"initial:{init_str}|".encode("utf-8"))
    for t_idx, ev in enumerate(event_sequence.events):
        ev_str = ",".join(str(v) for v in sorted(ev))
        h.update(f"step_{t_idx}:{ev_str}|".encode("utf-8"))
    return h.hexdigest()[:16]


def generate_experiment_summary(run_records: Sequence[RunRecord]) -> pd.DataFrame:

    """Generate aggregated summary statistics grouped by condition and strategy.



    Computes sample count, completed vs failed count, mean, median, standard deviation,

    and Student-t 95% confidence intervals for route cost and computational effort.



    Args:

        run_records: Sequence of completed or failed RunRecord objects.



    Returns:

        DataFrame with summary statistics per experimental group.

    """

    if not run_records:

        return pd.DataFrame()



    records_data = [r.to_dict() for r in run_records]

    df = pd.DataFrame(records_data)



    group_cols = ["instance_family", "condition_id", "strategy", "budget_type", "budget_limit"]

    # Ensure all grouping columns exist

    for col in group_cols:

        if col not in df.columns:

            df[col] = "unknown"



    rows: list[dict[str, Any]] = []



    for key, group in df.groupby(group_cols, dropna=False):

        inst_family, cond_id, strat, b_type, b_lim = key

        total_runs = len(group)

        success_group = group[group["status"] == "SUCCESS"]

        completed_runs = len(success_group)

        failed_runs = total_runs - completed_runs



        costs = success_group["final_cost"].dropna().to_numpy(dtype=float)

        efforts = success_group["total_computational_effort"].dropna().to_numpy(dtype=float)

        times = success_group["total_response_time_ms"].dropna().to_numpy(dtype=float)

        disruptions = success_group["mean_disruption"].dropna().to_numpy(dtype=float)



        n_valid = len(costs)



        if n_valid > 0:

            mean_cost = float(np.mean(costs))

            median_cost = float(np.median(costs))

            std_cost = float(np.std(costs, ddof=1)) if n_valid >= 2 else 0.0



            if n_valid >= 2 and std_cost > 0:

                se_cost = std_cost / math.sqrt(n_valid)

                t_crit = float(stats.t.ppf(0.975, df=n_valid - 1))

                ci95_low = mean_cost - t_crit * se_cost

                ci95_high = mean_cost + t_crit * se_cost

            else:

                ci95_low = mean_cost

                ci95_high = mean_cost



            mean_effort = float(np.mean(efforts))

            median_effort = float(np.median(efforts))

            cands = success_group["candidate_evaluations"].dropna().to_numpy(dtype=float) if "candidate_evaluations" in success_group else np.array([])
            overheads = success_group["overhead_evaluations"].dropna().to_numpy(dtype=float) if "overhead_evaluations" in success_group else np.array([])
            mean_cand = float(np.mean(cands)) if len(cands) > 0 else 0.0
            median_cand = float(np.median(cands)) if len(cands) > 0 else 0.0
            mean_overhead = float(np.mean(overheads)) if len(overheads) > 0 else 0.0

            mean_time_ms = float(np.mean(times))

            mean_disrupt = float(np.mean(disruptions))

        else:

            mean_cost = float("nan")

            median_cost = float("nan")

            std_cost = float("nan")

            ci95_low = float("nan")

            ci95_high = float("nan")

            mean_effort = float("nan")

            median_effort = float("nan")

            mean_cand = float("nan")
            median_cand = float("nan")
            mean_overhead = float("nan")

            mean_time_ms = float("nan")

            mean_disrupt = float("nan")



        feas_rate = float(group["all_feasible"].mean()) if "all_feasible" in group else 1.0

        prefix_rate = float(group["frozen_prefix_preserved"].mean()) if "frozen_prefix_preserved" in group else 1.0

        exhaust_rate = float(group["budget_exhausted"].mean()) if "budget_exhausted" in group else 0.0



        rows.append({

            "instance_family": inst_family,

            "condition_id": cond_id,

            "strategy": strat,

            "budget_type": b_type,

            "budget_limit": b_lim,

            "total_runs": total_runs,

            "completed_runs": completed_runs,

            "failed_runs": failed_runs,

            "mean_final_cost": mean_cost,

            "median_final_cost": median_cost,

            "std_final_cost": std_cost,

            "ci95_low_final_cost": ci95_low,

            "ci95_high_final_cost": ci95_high,

            "mean_computational_effort": mean_effort,

            "median_computational_effort": median_effort,

            "mean_candidate_evaluations": mean_cand,

            "median_candidate_evaluations": median_cand,

            "mean_overhead_evaluations": mean_overhead,

            "mean_response_time_ms": mean_time_ms,

            "mean_disruption": mean_disrupt,

            "feasibility_rate": feas_rate,

            "prefix_preservation_rate": prefix_rate,

            "budget_exhaustion_rate": exhaust_rate,

            "statistical_note": "Diagnostic sample only; not inferential" if n_valid < 30 else "Inferential sample (N>=30)",

        })



    return pd.DataFrame(rows)





def generate_paired_comparisons(run_records: Sequence[RunRecord]) -> pd.DataFrame:

    """Generate paired comparison rows aligned by scenario pairing key (pair_id).



    Facilitates matched pairwise statistical hypothesis testing (paired t-test,

    Wilcoxon signed-rank test) on identical dynamic problem instances.



    Args:

        run_records: Sequence of RunRecord objects containing pair_id.



    Returns:

        DataFrame of paired comparisons between strategies across identical instances.

    """

    if not run_records:

        return pd.DataFrame()



    records_data = [r.to_dict() for r in run_records]

    df = pd.DataFrame(records_data)



    if "pair_id" not in df.columns or df["pair_id"].nunique() == 0:

        return pd.DataFrame()



    paired_rows: list[dict[str, Any]] = []



    for pair_id, group in df.groupby("pair_id"):

        strat_rows = {row["strategy"].upper(): row for _, row in group.iterrows()}



        first_row = group.iloc[0]

        base_info = {

            "pair_id": pair_id,

            "condition_id": first_row.get("condition_id"),

            "instance_family": first_row.get("instance_family"),

            "instance_id": first_row.get("instance_id"),

            "seed": first_row.get("seed"),

            "replicate": first_row.get("replicate", 0),

            "budget_type": first_row.get("budget_type"),

            "budget_limit": first_row.get("budget_limit"),

            "scenario_fingerprint": first_row.get("scenario_fingerprint", ""),

        }



        # Record per-strategy metrics
        for s_key in ["A", "B", "C", "ADAPTIVE"]:
            rec = strat_rows.get(s_key)
            if rec is not None and rec.get("status") == "SUCCESS":
                base_info[f"cost_{s_key}"] = rec.get("final_cost")
                base_info[f"effort_{s_key}"] = rec.get("total_computational_effort")
                base_info[f"candidate_evals_{s_key}"] = rec.get("candidate_evaluations", 0)
                base_info[f"overhead_{s_key}"] = rec.get("overhead_evaluations", 0)
                base_info[f"time_ms_{s_key}"] = rec.get("total_response_time_ms")
                base_info[f"status_{s_key}"] = "SUCCESS"
            else:
                base_info[f"cost_{s_key}"] = float("nan")
                base_info[f"effort_{s_key}"] = float("nan")
                base_info[f"candidate_evals_{s_key}"] = 0
                base_info[f"overhead_{s_key}"] = 0
                base_info[f"time_ms_{s_key}"] = float("nan")
                status_val = "MISSING"
                if rec is not None and hasattr(rec, "get"):
                    status_val = rec.get("status", "MISSING")
                base_info[f"status_{s_key}"] = status_val

        # Compute paired differences if both strategies succeeded
        pairs_to_diff = [
            ("B", "A", "diff_cost_B_vs_A", "diff_effort_B_vs_A"),
            ("C", "A", "diff_cost_C_vs_A", "diff_effort_C_vs_A"),
            ("ADAPTIVE", "A", "diff_cost_Adaptive_vs_A", "diff_effort_Adaptive_vs_A"),
            ("C", "B", "diff_cost_C_vs_B", "diff_effort_C_vs_B"),
            ("ADAPTIVE", "B", "diff_cost_Adaptive_vs_B", "diff_effort_Adaptive_vs_B"),
        ]

        for s1, s2, cost_diff_name, effort_diff_name in pairs_to_diff:
            c1 = base_info[f"cost_{s1}"]
            c2 = base_info[f"cost_{s2}"]
            e1 = base_info[f"effort_{s1}"]
            e2 = base_info[f"effort_{s2}"]

            if not math.isnan(c1) and not math.isnan(c2):
                base_info[cost_diff_name] = c1 - c2
                base_info[effort_diff_name] = e1 - e2
            else:
                base_info[cost_diff_name] = float("nan")
                base_info[effort_diff_name] = float("nan")
        paired_rows.append(base_info)



    return pd.DataFrame(paired_rows)





class ExperimentRunner:

    """Orchestrates batch execution of dynamic routing experiments."""



    def __init__(self, config: ExperimentConfig) -> None:

        self.config = config

        self.commit_hash = get_git_commit_hash()



    def run(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> ExperimentManifest:

        """Execute the entire experiment matrix defined by the configuration.



        Args:

            progress_callback: Optional callback(completed, total, message) for reporting progress.



        Returns:

            Finalized ExperimentManifest.

        """

        output_dir = self.config.output_dir

        os.makedirs(output_dir, exist_ok=True)



        total_conditions = len(self.config.conditions)

        total_seeds = len(self.config.seeds)

        total_strategies = len(self.config.strategies)

        total_planned_runs = total_conditions * total_seeds * total_strategies



        manifest = create_manifest(

            experiment_name=self.config.name,

            total_conditions=total_conditions,

            total_seeds=total_seeds,

            total_planned_runs=total_planned_runs,

            metadata={"description": self.config.description},

        )



        run_records: list[RunRecord] = []

        step_records: list[dict[str, Any]] = []

        completed_runs = 0

        failed_runs = 0

        failures: list[dict[str, Any]] = []



        logger.info(

            f"Starting experiment '{self.config.name}': "

            f"{total_conditions} conditions x {total_seeds} seeds x {total_strategies} strategies "

            f"= {total_planned_runs} total runs."

        )



        # Validate strategy configuration early

        valid_strategies = {"A", "B", "C", "ADAPTIVE", "ADAPT"}

        for s in self.config.strategies:

            if s.upper() not in valid_strategies:

                raise ValueError(

                    f"Unsupported strategy '{s}'. Supported strategies: {sorted(list(valid_strategies))}"

                )



        for cond_idx, condition in enumerate(self.config.conditions):

            # Validate condition instance source

            if condition.instance_source == "synthetic":

                if condition.distribution.lower() not in ("uniform", "clustered", "mixed"):

                    raise ValueError(

                        f"Unsupported synthetic distribution '{condition.distribution}'. "

                        f"Supported distributions: ['uniform', 'clustered', 'mixed']"

                    )

                inst_family = f"synthetic_{condition.distribution.lower()}"

            elif condition.instance_source == "tsplib":

                if not condition.benchmark_name or condition.benchmark_name.lower().replace(".tsp", "") not in ("berlin52", "eil51"):

                    raise ValueError(

                        f"Unsupported TSPLIB benchmark '{condition.benchmark_name}'. "

                        f"Supported benchmarks: ['berlin52', 'eil51']"

                    )

                bench_clean = condition.benchmark_name.lower().replace(".tsp", "")
                if bench_clean == "berlin52" and condition.total_vertices != 51:
                    raise ValueError(f"Benchmark 'berlin52' has 51 non-depot customer vertices, but condition specified total_vertices={condition.total_vertices}")
                elif bench_clean == "eil51" and condition.total_vertices != 50:
                    raise ValueError(f"Benchmark 'eil51' has 50 non-depot customer vertices, but condition specified total_vertices={condition.total_vertices}")

                inst_family = "tsplib"

            else:

                raise ValueError(

                    f"Unsupported instance_source '{condition.instance_source}'. Supported: ['synthetic', 'tsplib']"

                )



            for seed in self.config.seeds:

                replicate = getattr(condition, "replicate", 0)

                if replicate > 0:
                    pair_id = f"{condition.condition_id}_s{seed}_r{replicate}"
                else:
                    pair_id = f"{condition.condition_id}_s{seed}"



                # 1. Generate identical Instance for this (condition, seed)

                try:

                    if condition.instance_source == "tsplib" and condition.benchmark_name:

                        from adaptive_route_optimization.benchmarks.tsplib import load_tsplib_benchmark

                        tsplib_obj = load_tsplib_benchmark(condition.benchmark_name)

                        instance = tsplib_obj.instance

                        inst_id = condition.benchmark_name.lower().replace(".tsp", "")

                    else:

                        instance = Instance.generate_synthetic(

                            n=condition.total_vertices,

                            distribution=condition.distribution,

                            seed=seed,

                            min_separation=0.001,

                            **condition.distribution_params,

                        )

                        inst_id = f"{condition.distribution.lower()}_n{condition.total_vertices}_s{seed}"

                except Exception as e:

                    logger.error(f"Instance generation failed for {condition.condition_id} seed {seed}: {e}")

                    failed_runs += total_strategies

                    failures.append({

                        "condition_id": condition.condition_id,

                        "seed": seed,

                        "stage": "instance_generation",

                        "error": str(e),

                    })

                    continue



                # 2. Generate identical EventSequence for this (condition, seed)

                try:

                    event_cfg = EventConfig(

                        total_vertices=instance.n,

                        dynamicity=condition.dynamicity,

                        events_per_step=condition.events_per_step,

                        seed=seed,

                        vertex_order=condition.vertex_order,

                        batch_schedule=condition.batch_schedule,

                    )

                    event_seq = EventGenerator(event_cfg).generate(instance)
                    scenario_fp = compute_scenario_fingerprint(instance, event_seq)

                except Exception as e:

                    logger.error(f"Event generation failed for {condition.condition_id} seed {seed}: {e}")

                    failed_runs += total_strategies

                    failures.append({

                        "condition_id": condition.condition_id,

                        "seed": seed,

                        "stage": "event_generation",

                        "error": str(e),

                    })

                    continue



                # 3. Setup Simulator with configured budget

                max_passes = None

                max_evaluations = None

                if condition.budget.budget_type == BudgetType.MAX_PASSES:

                    max_passes = int(condition.budget.limit) if condition.budget.limit else None

                elif condition.budget.budget_type == BudgetType.MAX_EVALUATIONS:

                    max_evaluations = int(condition.budget.limit) if condition.budget.limit is not None else None



                simulator = Simulator(

                    instance=instance,

                    event_sequence=event_seq,

                    freeze_per_step=condition.freeze_per_step,

                    max_passes=max_passes,

                    max_evaluations=max_evaluations,

                )



                # 4. Execute each strategy on this exact same instance and event stream

                for strat_name in self.config.strategies:

                    upper_name = strat_name.upper()

                    if upper_name == "A":

                        strat_enum = Strategy.A

                    elif upper_name == "B":

                        strat_enum = Strategy.B

                    elif upper_name == "C":

                        strat_enum = Strategy.C

                    elif upper_name in ("ADAPTIVE", "ADAPT"):

                        strat_enum = Strategy.ADAPTIVE

                    else:

                        raise ValueError(f"Unknown strategy name: {strat_name}")



                    if replicate > 0:
                        run_id = f"{condition.condition_id}_s{seed}_r{replicate}_{strat_name}"
                    else:
                        run_id = f"{condition.condition_id}_s{seed}_{strat_name}"

                    dist_params_json = json.dumps(condition.distribution_params)

                    sched_type = "variable_schedule" if condition.batch_schedule else "uniform_batch"

                    distance_metric = getattr(condition, "distance_metric", "continuous_euclidean")



                    try:

                        t_start = time.perf_counter()

                        sim_result = simulator.run(strat_enum, seed=seed)

                        elapsed_s = time.perf_counter() - t_start



                        # Validate feasibility

                        if not sim_result.all_feasible:

                            raise ValueError(f"Run {run_id} produced infeasible route intermediate steps")



                        # Verify frozen prefix invariance across all steps

                        frozen_preserved = True

                        for step_idx, step in enumerate(sim_result.steps):

                            # The committed prefix from step t-1 must be unchanged in step t

                            prev_route = step.previous_route.vertices

                            cur_route = step.updated_route.vertices

                            prefix_len = min(step_idx + 1, len(prev_route))

                            if cur_route[:prefix_len] != prev_route[:prefix_len]:

                                frozen_preserved = False

                                break



                        if not frozen_preserved:

                            raise RuntimeError(f"Run {run_id} violated frozen prefix invariance")



                        init_cost = sim_result.initial_state.current_route.cost(instance)

                        final_cost = sim_result.final_metrics.route_cost



                        # Budget exhaustion and utilization calculation

                        budget_exhausted = False

                        budget_utilization = None

                        if max_evaluations is not None and max_evaluations > 0:

                            budget_exhausted = any(s.metrics.computational_effort >= max_evaluations for s in sim_result.steps)

                            total_capacity = max_evaluations * len(sim_result.steps)

                            budget_utilization = (

                                sim_result.total_computational_effort / total_capacity if total_capacity > 0 else 0.0

                            )



                        record = RunRecord(

                            run_id=run_id,

                            condition_id=condition.condition_id,

                            strategy=strat_name,

                            seed=seed,

                            total_vertices=condition.total_vertices,

                            dynamicity=condition.dynamicity,

                            num_events=sim_result.num_events,

                            initial_cost=init_cost,

                            final_cost=final_cost,

                            cost_increase=final_cost - init_cost,

                            total_computational_effort=sim_result.total_computational_effort,

                            total_response_time_ms=sim_result.total_response_time_ms,

                            mean_disruption=sim_result.mean_disruption,

                            max_disruption=sim_result.max_disruption,

                            all_feasible=sim_result.all_feasible,

                            budget_type=condition.budget.budget_type.value,

                            budget_limit=condition.budget.limit,

                            git_commit_hash=self.commit_hash,

                            timestamp=datetime.now().isoformat(),

                            distribution=condition.distribution,

                            events_per_step=condition.events_per_step,

                            instance_source=condition.instance_source,

                            benchmark_name=condition.benchmark_name,

                            pair_id=pair_id,

                            instance_family=inst_family,

                            instance_id=inst_id,

                            replicate=replicate,

                            distribution_params=dist_params_json,

                            arrival_schedule_type=sched_type,

                            budget_exhausted=budget_exhausted,

                            budget_utilization=budget_utilization,

                            distance_metric=distance_metric,

                            frozen_prefix_preserved=frozen_preserved,

                            algorithm_version="stage4_v1.0",

                            status="SUCCESS",

                            error_message="",
                            candidate_evaluations=sim_result.total_candidate_evaluations,
                            overhead_evaluations=sim_result.total_overhead_evaluations,
                            budget_scope=getattr(condition, "budget_scope", "per_step"),
                            scenario_fingerprint=scenario_fp,

                        )

                        run_records.append(record)



                        # Collect step records

                        for step in sim_result.steps:

                            step_records.append({

                                "run_id": run_id,

                                "pair_id": pair_id,

                                "time_step": step.time_step,

                                "condition_id": condition.condition_id,

                                "strategy": strat_name,

                                "seed": seed,

                                "num_event_vertices": len(step.event_vertices),

                                "num_known_vertices": len(step.known_vertices),

                                "route_cost": step.metrics.route_cost,

                                "disruption": step.metrics.disruption,

                                "feasible": step.metrics.feasible,

                                "computational_effort": step.metrics.computational_effort,

                                "candidate_evaluations": getattr(step.metrics, "candidate_evaluations", step.metrics.computational_effort),

                                "overhead_evaluations": getattr(step.metrics, "overhead_evaluations", 0),

                                "response_time_ms": step.metrics.response_time_ms,

                                "scenario_fingerprint": scenario_fp,

                            })



                        completed_runs += 1



                    except Exception as e:

                        logger.error(f"Strategy {strat_name} failed on {run_id}: {e}", exc_info=True)

                        failed_runs += 1

                        failures.append({

                            "run_id": run_id,

                            "condition_id": condition.condition_id,

                            "strategy": strat_name,

                            "seed": seed,

                            "error": str(e),

                        })



                        # Record failed run in RunRecord to prevent silent drops

                        failed_record = RunRecord(

                            run_id=run_id,

                            condition_id=condition.condition_id,

                            strategy=strat_name,

                            seed=seed,

                            total_vertices=condition.total_vertices,

                            dynamicity=condition.dynamicity,

                            num_events=0,

                            initial_cost=float("nan"),

                            final_cost=float("nan"),

                            cost_increase=float("nan"),

                            total_computational_effort=0,

                            total_response_time_ms=0.0,

                            mean_disruption=float("nan"),

                            max_disruption=float("nan"),

                            all_feasible=False,

                            budget_type=condition.budget.budget_type.value,

                            budget_limit=condition.budget.limit,

                            git_commit_hash=self.commit_hash,

                            timestamp=datetime.now().isoformat(),

                            distribution=condition.distribution,

                            events_per_step=condition.events_per_step,

                            instance_source=condition.instance_source,

                            benchmark_name=condition.benchmark_name,

                            pair_id=pair_id,

                            instance_family=inst_family,

                            instance_id=inst_id,

                            replicate=replicate,

                            distribution_params=dist_params_json,

                            arrival_schedule_type=sched_type,

                            budget_exhausted=False,

                            budget_utilization=None,

                            distance_metric=distance_metric,

                            frozen_prefix_preserved=False,

                            algorithm_version="stage4_v1.0",

                            status="FAILED",

                            error_message=str(e),
                            candidate_evaluations=0,
                            overhead_evaluations=0,
                            budget_scope=getattr(condition, "budget_scope", "per_step"),
                            scenario_fingerprint=scenario_fp if "scenario_fp" in locals() else "",

                        )

                        run_records.append(failed_record)



                    if progress_callback:

                        progress_callback(

                            completed_runs + failed_runs,

                            total_planned_runs,

                            f"Completed {run_id}",

                        )



        # 5. Persist raw structured outputs (CSV + JSON)

        runs_csv_path = os.path.join(output_dir, "runs.csv")

        steps_csv_path = os.path.join(output_dir, "steps.csv")

        runs_json_path = os.path.join(output_dir, "runs.json")

        manifest_path = os.path.join(output_dir, "manifest.json")

        summary_csv_path = os.path.join(output_dir, "summary.csv")

        paired_csv_path = os.path.join(output_dir, "paired_comparisons.csv")



        df_runs = pd.DataFrame([r.to_dict() for r in run_records])

        df_runs.to_csv(runs_csv_path, index=False)



        with open(runs_json_path, "w", encoding="utf-8") as f:

            json.dump([r.to_dict() for r in run_records], f, indent=2)



        if step_records:

            df_steps = pd.DataFrame(step_records)

            df_steps.to_csv(steps_csv_path, index=False)



        # Generate summary and paired comparison artifacts

        df_summary = generate_experiment_summary(run_records)

        if not df_summary.empty:

            df_summary.to_csv(summary_csv_path, index=False)



        df_paired = generate_paired_comparisons(run_records)

        if not df_paired.empty:

            df_paired.to_csv(paired_csv_path, index=False)



        output_files = {

            "runs_csv": runs_csv_path,

            "runs_json": runs_json_path,

            "steps_csv": steps_csv_path,

            "manifest_json": manifest_path,

            "summary_csv": summary_csv_path,

            "paired_csv": paired_csv_path,

        }



        manifest.finalize(

            completed_runs=completed_runs,

            failed_runs=failed_runs,

            output_files=output_files,

            metadata={

                "failures": failures,

                "conditions": [c.to_dict() for c in self.config.conditions],

            },

        )

        manifest.save(manifest_path)



        logger.info(

            f"Experiment batch '{self.config.name}' completed: "

            f"{completed_runs} succeeded, {failed_runs} failed. "

            f"Results saved to '{output_dir}'."

        )



        return manifest





def run_experiment(config: ExperimentConfig) -> ExperimentManifest:

    """Convenience entry point to run an experiment from configuration."""

    runner = ExperimentRunner(config)

    return runner.run()


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Batch Experiment Runner for Dynamic Route Optimization")
    parser.add_argument("--config", "-c", required=True, help="Path to ExperimentConfig JSON file")
    parser.add_argument("--output-dir", "-o", default=None, help="Override output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    cfg = ExperimentConfig.load(args.config)
    if args.output_dir:
        import dataclasses
        cfg = dataclasses.replace(cfg, output_dir=args.output_dir)

    manifest = run_experiment(cfg)
    sys.exit(0 if manifest.failed_runs == 0 else 1)


