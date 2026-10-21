"""Interpretable Adaptive Strategy Selector for Dynamic Route Optimization.

Implements an explainable, rule-based decision mechanism that selects between
Strategy A (Greedy Insertion) and Strategy B (Greedy Insertion + 2-opt)
based on observable state features, preventing the myopic commitment trap.
References: RESEARCH_SPEC.md, MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phase 8).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

from adaptive_route_optimization.algorithms.adaptive.features import StateFeatures


class StrategyChoice(str, Enum):
    """Underlying repair strategy chosen by the adaptive selector."""
    A = "A"  # Greedy Insertion
    B = "B"  # Greedy Insertion + 2-opt


@dataclass(frozen=True)
class SelectorConfig:
    """Hyperparameters and thresholds for the adaptive selector.

    Derived strictly on designated development data (seeds 42, 101):
    - Low dynamicity regime (α <= 0.2): Strategy B demonstrated a 100% win rate.
    - Late-stage threshold (revealed_ratio >= 0.75): When >= 75% of customers are known,
      the risk of early-commitment distortion is low because few future vertices remain.
    - Suffix size check: 2-opt requires at least 4 edges to perform non-trivial swaps.

    Attributes:
        low_dyn_threshold: Dynamicity threshold below which Strategy B is preferred (0.2).
        late_stage_threshold: Fraction of revealed vertices above which Strategy B is safe (0.75).
        min_suffix_for_2opt: Minimum suffix edge count to justify 2-opt invocation (4).
        budget_safety_margin: Multiplier on estimated evaluations required before attempting 2-opt (1.0).
        selection_overhead_evals: Candidate evaluations charged for feature extraction and decision (1).
        name: Identifier for selector version.
    """
    low_dyn_threshold: float = 0.2
    late_stage_threshold: float = 0.75
    min_suffix_for_2opt: int = 4
    budget_safety_margin: float = 1.0
    selection_overhead_evals: int = 1
    name: str = "rule_v1_interpretable"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SelectorConfig:
        return cls(**data)


@dataclass(frozen=True)
class SelectionDecision:
    """Record of a strategy selection decision made at dynamic event step t."""
    chosen_strategy: StrategyChoice
    rationale: str
    features: StateFeatures
    overhead_evaluations: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "chosen_strategy": self.chosen_strategy.value,
            "rationale": self.rationale,
            "features": self.features.to_dict(),
            "overhead_evaluations": self.overhead_evaluations,
        }


class AdaptiveSelector:
    """Interpretable decision engine selecting between Strategy A and Strategy B.

    Design Principles:
    1. Interpretable: 3 explainable rules grounded in empirical DAA evidence.
    2. Zero Leakage: Only current state features and budget are inspected.
    3. Budget-Aware: Deterministic fallback to Strategy A if budget is insufficient.
    4. Accounted Overhead: Adds selection_overhead_evals to total effort.
    """

    def __init__(self, config: Optional[SelectorConfig] = None) -> None:
        self.config = config or SelectorConfig()
        self.decision_history: list[SelectionDecision] = []

    def select(self, features: StateFeatures) -> SelectionDecision:
        """Select Strategy A or Strategy B for the current dynamic event.

        Decision Rules:
        Rule 1 (Budget Safety): If candidate evaluation budget remaining is less than
               the estimated cost of 1 pass of 2-opt, select Strategy A.
        Rule 2 (Degeneracy Guard): If uncommitted suffix has fewer than min_suffix_for_2opt
               edges, 2-opt has no non-trivial swaps; select Strategy A.
        Rule 3 (Core Economic Trade-off):
               - If initial dynamicity is low (α <= low_dyn_threshold), 2-opt establishes
                 and maintains global tour quality with minimal trap risk; select Strategy B.
               - If currently revealed ratio >= late_stage_threshold, majority of vertices
                 are now known, eliminating early commitment risk; select Strategy B.
               - Otherwise (early-to-mid stages of high dynamicity), select Strategy A
                 to avoid the myopic local search trap and conserve computational effort.
        """
        cfg = self.config
        overhead = cfg.selection_overhead_evals

        # Rule 1: Computational Budget Feasibility
        if features.remaining_eval_budget is not None:
            required_evals = int(features.estimated_2opt_evals * cfg.budget_safety_margin)
            if features.remaining_eval_budget < required_evals:
                decision = SelectionDecision(
                    chosen_strategy=StrategyChoice.A,
                    rationale=f"Budget fallback: remaining {features.remaining_eval_budget} < required {required_evals}",
                    features=features,
                    overhead_evaluations=overhead,
                )
                self.decision_history.append(decision)
                return decision

        # Rule 2: Minimum Suffix Size
        m = features.uncommitted_count + features.event_size + 1
        if m < cfg.min_suffix_for_2opt:
            decision = SelectionDecision(
                chosen_strategy=StrategyChoice.A,
                rationale=f"Degeneracy guard: suffix length {m} < {cfg.min_suffix_for_2opt}",
                features=features,
                overhead_evaluations=overhead,
            )
            self.decision_history.append(decision)
            return decision

        # Rule 3: Core Commitment Risk Evaluation
        if features.initial_dynamicity <= cfg.low_dyn_threshold:
            decision = SelectionDecision(
                chosen_strategy=StrategyChoice.B,
                rationale=f"Low dynamicity (α={features.initial_dynamicity:.2f} <= {cfg.low_dyn_threshold:.2f}): high win rate for 2-opt",
                features=features,
                overhead_evaluations=overhead,
            )
        elif features.revealed_ratio >= cfg.late_stage_threshold:
            decision = SelectionDecision(
                chosen_strategy=StrategyChoice.B,
                rationale=f"Late-stage event (revealed={features.revealed_ratio:.2f} >= {cfg.late_stage_threshold:.2f}): commitment risk eliminated",
                features=features,
                overhead_evaluations=overhead,
            )
        else:
            decision = SelectionDecision(
                chosen_strategy=StrategyChoice.A,
                rationale=f"High dynamicity early-stage (α={features.initial_dynamicity:.2f}, revealed={features.revealed_ratio:.2f}): avoiding myopic trap",
                features=features,
                overhead_evaluations=overhead,
            )

        self.decision_history.append(decision)
        return decision

    def reset(self) -> None:
        """Clear decision history for a fresh simulation run."""
        self.decision_history.clear()
