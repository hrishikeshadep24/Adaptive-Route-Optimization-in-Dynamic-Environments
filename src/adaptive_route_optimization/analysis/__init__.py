"""Research Analysis & Ablation Package (Phase 7)."""

from adaptive_route_optimization.analysis.validator import (
    DataValidationReport,
    ValidationIssue,
    validate_experiment_data,
)
from adaptive_route_optimization.analysis.metrics import (
    compute_relative_improvement,
    build_paired_dataset,
    aggregate_by_condition,
    aggregate_scalability,
    compute_step_level_statistics,
)
from adaptive_route_optimization.analysis.statistical import (
    PairedTestResult,
    compute_bootstrap_ci,
    run_paired_analysis,
    run_full_statistical_battery,
)
from adaptive_route_optimization.analysis.ablation import (
    analyze_component_ablation,
    analyze_dynamicity_regime_ablation,
    analyze_budget_cap_ablation,
)
from adaptive_route_optimization.analysis.pipeline import (
    AnalysisPipeline,
    run_pipeline,
)

__all__ = [
    "DataValidationReport",
    "ValidationIssue",
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
