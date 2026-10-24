"""Pilot evaluation script for Adaptive v3 (Three-Strategy Selection).

Validates selection rules, budget adherence, frozen-prefix preservation,
and relative performance against Strategies A, B, C, and Adaptive v2.
"""

from __future__ import annotations
import sys
import time
import pandas as pd
import numpy as np

from adaptive_route_optimization.models.instance import Instance
from adaptive_route_optimization.simulation.events import EventConfig, EventGenerator
from adaptive_route_optimization.simulation.simulator import Simulator, Strategy
from adaptive_route_optimization.algorithms.adaptive.selector import (
    AdaptiveSelector, SelectorConfig, StrategyChoice
)
from adaptive_route_optimization.algorithms.adaptive.features import extract_features
from adaptive_route_optimization.benchmarks import load_tsplib_benchmark


def run_pilot():
    conditions = [
        # (name, family, n, dyn, budget, params)
        ("uniform_n50_d0.2_b100", "uniform", 50, 0.2, 100, {}),
        ("uniform_n50_d0.4_b100", "uniform", 50, 0.4, 100, {}),
        ("uniform_n50_d0.6_b100", "uniform", 50, 0.6, 100, {}),
        ("uniform_n50_d0.4_unbounded", "uniform", 50, 0.4, None, {}),
        ("clustered_n50_d0.4_b100", "clustered", 50, 0.4, 100, {"num_clusters": 3, "cluster_spread": 4.0}),
        ("clustered_n50_d0.6_b100", "clustered", 50, 0.6, 100, {"num_clusters": 3, "cluster_spread": 4.0}),
        ("mixed_n50_d0.4_b100", "mixed", 50, 0.4, 100, {"num_clusters": 2, "cluster_spread": 5.0, "uniform_fraction": 0.3}),
        ("tsplib_berlin52_d0.4_b100", "tsplib", 51, 0.4, 100, {"benchmark": "berlin52"}),
        ("tsplib_eil51_d0.4_b100", "tsplib", 50, 0.4, 100, {"benchmark": "eil51"}),
    ]

    seeds = [42, 101]
    results = []

    print(f"Starting Adaptive v3 Pilot across {len(conditions)} conditions and {len(seeds)} seeds...")

    for cond_name, family, n, dyn, budget, params in conditions:
        for seed in seeds:
            # 1. Instance
            if family == "tsplib":
                bench_obj = load_tsplib_benchmark(params["benchmark"])
                inst = bench_obj.instance
            elif family == "uniform":
                inst = Instance.generate_synthetic(n=n, distribution="uniform", seed=seed)
            elif family == "clustered":
                inst = Instance.generate_synthetic(n=n, distribution="clustered", seed=seed, **params)
            elif family == "mixed":
                inst = Instance.generate_synthetic(n=n, distribution="mixed", seed=seed, **params)

            # 2. Event sequence
            ecfg = EventConfig(total_vertices=inst.n, dynamicity=dyn, events_per_step=1, seed=seed)
            ev_seq = EventGenerator(ecfg).generate(inst)

            # Evaluated strategies
            # A, B, C, Adapt_v2, Adapt_v3
            sim_a = Simulator(inst, ev_seq, max_evaluations=budget)
            res_a = sim_a.run(Strategy.A, seed=seed)

            sim_b = Simulator(inst, ev_seq, max_evaluations=budget)
            res_b = sim_b.run(Strategy.B, seed=seed)

            sim_c = Simulator(inst, ev_seq, max_evaluations=budget)
            res_c = sim_c.run(Strategy.C, seed=seed)

            sel_v2 = AdaptiveSelector(SelectorConfig(name="rule_v2", version="v2"))
            sim_v2 = Simulator(inst, ev_seq, max_evaluations=budget, selector=sel_v2)
            res_v2 = sim_v2.run(Strategy.ADAPTIVE, seed=seed)

            sel_v3 = AdaptiveSelector(SelectorConfig(name="rule_v3", version="v3"))
            sim_v3 = Simulator(inst, ev_seq, max_evaluations=budget, selector=sel_v3)
            res_v3 = sim_v3.run(Strategy.ADAPTIVE, seed=seed)

            # Count choices made by sel_v3
            choices_v3 = [d.chosen_strategy.value for d in sel_v3.decision_history]
            c_count = choices_v3.count("C")
            b_count = choices_v3.count("B")
            a_count = choices_v3.count("A")

            results.append({
                "condition": cond_name,
                "seed": seed,
                "budget": str(budget),
                "cost_A": res_a.final_metrics.route_cost,
                "cost_B": res_b.final_metrics.route_cost,
                "cost_C": res_c.final_metrics.route_cost,
                "cost_Adapt_v2": res_v2.final_metrics.route_cost,
                "cost_Adapt_v3": res_v3.final_metrics.route_cost,
                "evals_A": res_a.final_metrics.candidate_evaluations,
                "evals_B": res_b.final_metrics.candidate_evaluations,
                "evals_C": res_c.final_metrics.candidate_evaluations,
                "evals_v2": res_v2.final_metrics.candidate_evaluations,
                "evals_v3": res_v3.final_metrics.candidate_evaluations,
                "v3_choices": f"A:{a_count}/B:{b_count}/C:{c_count}",
                "prefix_ok": res_v3.all_feasible,
            })

    df = pd.DataFrame(results)
    print("\n--- PILOT RESULTS SUMMARY ---")
    print(df[["condition", "seed", "cost_A", "cost_B", "cost_C", "cost_Adapt_v2", "cost_Adapt_v3", "v3_choices"]].to_string())

    # Aggregate by condition
    agg = df.groupby("condition")[["cost_A", "cost_B", "cost_C", "cost_Adapt_v2", "cost_Adapt_v3"]].mean()
    print("\n--- CONDITION MEANS ---")
    print(agg.to_string())


if __name__ == "__main__":
    run_pilot()
