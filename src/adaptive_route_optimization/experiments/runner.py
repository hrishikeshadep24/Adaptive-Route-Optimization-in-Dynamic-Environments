"""Batch Experiment Runner for Dynamic Route Optimization.

Executes full condition matrices across multiple seeds, strictly enforcing
identical instance and event sequence comparison between strategies.
Outputs structured CSV, JSON, and manifest files with failure recovery.
References: RESEARCH_SPEC.md, MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phase 6).
"""

from __future__ import annotations
import csv
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Callable, Optional, Sequence

import pandas as pd

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.simulation.events import EventConfig, EventGenerator
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

        for cond_idx, condition in enumerate(self.config.conditions):
            for seed in self.config.seeds:
                # 1. Generate identical Instance for this (condition, seed)
                try:
                    instance = Instance.generate_random(
                        n=condition.total_vertices,
                        seed=seed,
                        min_separation=0.001,
                    )
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
                        total_vertices=condition.total_vertices,
                        dynamicity=condition.dynamicity,
                        events_per_step=condition.events_per_step,
                        seed=seed,
                        vertex_order=condition.vertex_order,
                    )
                    event_seq = EventGenerator(event_cfg).generate(instance)
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
                    max_evaluations = int(condition.budget.limit) if condition.budget.limit else None

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
                    elif upper_name in ("ADAPTIVE", "ADAPT"):
                        strat_enum = Strategy.ADAPTIVE
                    else:
                        raise ValueError(f"Unknown strategy name: {strat_name}")

                    run_id = f"{condition.condition_id}_s{seed}_{strat_name}"

                    try:
                        t_start = time.perf_counter()
                        sim_result = simulator.run(strat_enum, seed=seed)
                        elapsed_s = time.perf_counter() - t_start

                        # Validate feasibility and sanity
                        if not sim_result.all_feasible:
                            raise ValueError(f"Run {run_id} produced infeasible route intermediate steps")

                        init_cost = sim_result.initial_state.current_route.cost(instance)
                        final_cost = sim_result.final_metrics.route_cost

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
                        )
                        run_records.append(record)

                        # Collect step records
                        for step in sim_result.steps:
                            step_records.append({
                                "run_id": run_id,
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
                                "response_time_ms": step.metrics.response_time_ms,
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

        df_runs = pd.DataFrame([r.to_dict() for r in run_records])
        df_runs.to_csv(runs_csv_path, index=False)

        with open(runs_json_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in run_records], f, indent=2)

        if step_records:
            df_steps = pd.DataFrame(step_records)
            df_steps.to_csv(steps_csv_path, index=False)

        output_files = {
            "runs_csv": runs_csv_path,
            "runs_json": runs_json_path,
            "steps_csv": steps_csv_path,
            "manifest_json": manifest_path,
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
