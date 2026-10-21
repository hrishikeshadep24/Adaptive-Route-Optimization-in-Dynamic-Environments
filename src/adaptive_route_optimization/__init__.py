"""Adaptive Route Optimization - Dynamic Routing Research Framework.

A controlled experimental framework for studying route optimization strategies
in dynamic environments where new vertices are revealed during execution.

Main modules:
- models: Instance and Route representations
- algorithms: Baseline, local search, and repair strategies
- evaluation: Metrics and plotting
- simulation: Dynamic simulation engine (Phase 5)
"""

from adaptive_route_optimization.models import Instance, Route
from adaptive_route_optimization.algorithms.baseline import nearest_neighbor, exact_tsp
from adaptive_route_optimization.algorithms.local_search import two_opt
from adaptive_route_optimization.algorithms.repair import (
    greedy_insertion_repair,
    strategy_b_repair,
)
from adaptive_route_optimization.evaluation.metrics import (
    compute_disruption,
    evaluate_route,
    RouteMetrics,
    TimedOperation,
)

# Simulation (Phase 5)
from adaptive_route_optimization.simulation import (
    DynamicState,
    EventConfig,
    EventSequence,
    EventGenerator,
    Simulator,
    SimulationResult,
    Strategy,
    Replay,
    ReplayConfig,
    SimulationLogger,
    SimulationLog,
    animate_route_state,
)

# Experiments (Phase 6)
from adaptive_route_optimization.experiments import (
    BudgetType,
    BudgetConfig,
    ConditionConfig,
    ExperimentConfig,
    RunRecord,
    StepRecord,
    ExperimentManifest,
    create_manifest,
    get_git_commit_hash,
    get_environment_info,
    ExperimentRunner,
    run_experiment,
    verify_reproducibility,
)

# Analysis (Phase 7)
from adaptive_route_optimization.analysis import (
    DataValidationReport,
    validate_experiment_data,
    compute_relative_improvement,
    build_paired_dataset,
    aggregate_by_condition,
    aggregate_scalability,
    compute_step_level_statistics,
    PairedTestResult,
    compute_bootstrap_ci,
    run_paired_analysis,
    run_full_statistical_battery,
    analyze_component_ablation,
    analyze_dynamicity_regime_ablation,
    analyze_budget_cap_ablation,
    AnalysisPipeline,
    run_pipeline,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "Instance",
    "Route",
    # Algorithms
    "nearest_neighbor",
    "exact_tsp",
    "two_opt",
    "greedy_insertion_repair",
    "strategy_b_repair",
    # Evaluation
    "compute_disruption",
    "evaluate_route",
    "RouteMetrics",
    "TimedOperation",
    # Simulation (Phase 5)
    "DynamicState",
    "EventConfig",
    "EventSequence",
    "EventGenerator",
    "Simulator",
    "SimulationResult",
    "Strategy",
    "Replay",
    "ReplayConfig",
    "SimulationLogger",
    "SimulationLog",
    "animate_route_state",
    # Experiments (Phase 6)
    "BudgetType",
    "BudgetConfig",
    "ConditionConfig",
    "ExperimentConfig",
    "RunRecord",
    "StepRecord",
    "ExperimentManifest",
    "create_manifest",
    "get_git_commit_hash",
    "get_environment_info",
    "ExperimentRunner",
    "run_experiment",
    "verify_reproducibility",
    # Analysis (Phase 7)
    "DataValidationReport",
    "validate_experiment_data",
    "compute_relative_improvement",
    "build_paired_dataset",
    "aggregate_by_condition",
    "aggregate_scalability",
    "compute_step_level_statistics",
    "PairedTestResult",
    "compute_bootstrap_ci",
    "run_paired_analysis",
    "run_full_statistical_battery",
    "analyze_component_ablation",
    "analyze_dynamicity_regime_ablation",
    "analyze_budget_cap_ablation",
    "AnalysisPipeline",
    "run_pipeline",
]