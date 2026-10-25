"""UI and Visual Demonstrator Package for Adaptive Route Optimization."""

from adaptive_route_optimization.ui.data_loader import UIDataLoader
from adaptive_route_optimization.ui.visualizer import (
    render_route_step_diagram,
    render_before_after_comparison,
    render_strategy_comparison,
)
from adaptive_route_optimization.ui.demonstrator import InteractiveDemonstrator, DemonstrationStepRecord
from adaptive_route_optimization.ui.plots import (
    POLICY_COLORS,
    POLICY_LABELS,
    plot_cost_by_dynamicity,
    plot_effort_by_dynamicity,
    plot_pareto_frontier,
    plot_disruption_comparison,
    plot_budget_ablation_chart,
    plot_strategy_cost_bars,
    plot_strategy_effort_bars,
)

__all__ = [
    "UIDataLoader",
    "render_route_step_diagram",
    "render_before_after_comparison",
    "render_strategy_comparison",
    "InteractiveDemonstrator",
    "DemonstrationStepRecord",
    "POLICY_COLORS",
    "POLICY_LABELS",
    "plot_cost_by_dynamicity",
    "plot_effort_by_dynamicity",
    "plot_pareto_frontier",
    "plot_disruption_comparison",
    "plot_budget_ablation_chart",
    "plot_strategy_cost_bars",
    "plot_strategy_effort_bars",
]
