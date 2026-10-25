"""Interpretable Adaptive Strategy Selector for Dynamic Route Optimization.

Implements an explainable, rule-based decision mechanism that selects among:
- Strategy A (Greedy Insertion)
- Strategy B (Greedy Insertion + 2-opt)
- Strategy C (Suffix Destroy-and-Repair / LNS)
based on observable state features, preventing the myopic commitment trap
under strict evaluation budgets and frozen-prefix invariance.
References: RESEARCH_SPEC.md, MASTER_BLUEPRINT.md, PHASE_PLAN.md (Phases 8 & Stage 7).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

from adaptive_route_optimization.algorithms.adaptive.features import StateFeatures
from adaptive_route_optimization.algorithms.repair.destroy_repair import (
    calculate_repair_evaluations,
    RepairOperator,
)


class StrategyChoice(str, Enum):
    """Underlying repair strategy chosen by the adaptive selector."""
    A = "A"  # Greedy Insertion
    B = "B"  # Greedy Insertion + 2-opt
    C = "C"  # Suffix Destroy-and-Repair (LNS)


@dataclass(frozen=True)
class SelectorConfig:
    """Hyperparameters and thresholds for the adaptive selector.

    Derived strictly on designated development data (seeds 42, 101):
    - Low dynamicity regime (α <= 0.2): Strategy B demonstrated a 100% win rate.
    - Late-stage threshold (revealed_ratio >= 0.75): When >= 75% of customers are known,
      the risk of early-commitment distortion is low because few future vertices remain.
    - Suffix size check: 2-opt requires at least 4 edges to perform non-trivial swaps.
    - Strategy C Restructuring: Ruin-and-recreate triggered on arrival bursts (k >= 2),
      mid-stage high dynamicity (alpha >= 0.4, revealed in [0.35, 0.85]), or significant
      route cost jumps, provided budget covers at least 1 destroy-repair pass.

    Attributes:
        low_dyn_threshold: Dynamicity threshold below which Strategy B is preferred (0.2).
        late_stage_threshold: Fraction of revealed vertices above which Strategy B is safe (0.75).
        min_suffix_for_2opt: Minimum suffix edge count to justify 2-opt invocation (4).
        min_2opt_budget: Minimum evaluation budget required for budget-capped 2-opt (10).
        budget_safety_margin: Multiplier on estimated evaluations required before attempting search (1.0).
        selection_overhead_evals: Candidate evaluations charged for feature extraction and decision (1).
        name: Identifier for selector version.
        version: Algorithm version string ("v2" for legacy two-strategy, "v3" for three-strategy).
        min_suffix_for_c: Minimum customer vertices in suffix to justify Destroy-and-Repair (6).
        c_destroy_fraction: Fraction of uncommitted suffix customers to remove (0.25).
        c_repair_operator: Operator for re-insertion during C estimation ("cheapest" or "regret_2").
        burst_arrival_threshold: Newly arriving vertices threshold to trigger restructuring (2).
        burst_arrival_ratio: Ratio of arrival event size to suffix size triggering restructuring (0.15).
        high_dynamicity_c_threshold: Dynamicity threshold above which mid-stage C is considered (0.4).
        c_mid_stage_min: Minimum revealed ratio to activate mid-stage restructuring (0.35).
        c_mid_stage_max: Maximum revealed ratio to activate mid-stage restructuring (0.85).
        cost_increase_threshold: Relative route cost increase triggering restructuring (0.05).
    """
    low_dyn_threshold: float = 0.2
    late_stage_threshold: float = 0.75
    min_suffix_for_2opt: int = 4
    min_2opt_budget: int = 10
    budget_safety_margin: float = 1.0
    selection_overhead_evals: int = 1
    name: str = "rule_v2_budget_aware"
    version: str = "v2"

    # Strategy C thresholds
    min_suffix_for_c: int = 6
    c_destroy_fraction: float = 0.25
    c_repair_operator: str = "cheapest"
    burst_arrival_threshold: int = 2
    burst_arrival_ratio: float = 0.15
    high_dynamicity_c_threshold: float = 0.4
    c_mid_stage_min: float = 0.35
    c_mid_stage_max: float = 0.85
    cost_increase_threshold: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SelectorConfig:
        return cls(**data)

    @classmethod
    def v3(cls, **kwargs: Any) -> SelectorConfig:
        """Create an Adaptive v3 (Three-Strategy) configuration."""
        data: dict[str, Any] = {
            "name": "rule_v3_three_strategy",
            "version": "v3",
            "low_dyn_threshold": 0.2,
            "late_stage_threshold": 0.75,
            "min_suffix_for_2opt": 4,
            "min_2opt_budget": 10,
            "budget_safety_margin": 1.0,
            "selection_overhead_evals": 1,
            "min_suffix_for_c": 6,
            "c_destroy_fraction": 0.25,
            "c_repair_operator": "cheapest",
            "burst_arrival_threshold": 2,
            "burst_arrival_ratio": 0.15,
            "high_dynamicity_c_threshold": 0.4,
            "c_mid_stage_min": 0.35,
            "c_mid_stage_max": 0.85,
            "cost_increase_threshold": 0.05,
        }
        data.update(kwargs)
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
    """Interpretable decision engine selecting among Strategies A, B, and C.

    Design Principles:
    1. Interpretable: Explainable, transparent heuristic rules grounded in DAA complexity.
    2. Zero Leakage: Only current decision-time state features and budget are inspected.
    3. Budget-Aware: Deterministic fallback cascade (C -> B -> A, or B -> A) when budgets are constrained.
    4. Accounted Overhead: Adds selection_overhead_evals (+1 evaluation) to total effort.
    5. Reproducible: 100% deterministic given identical state features.
    """

    def __init__(self, config: Optional[SelectorConfig] = None) -> None:
        self.config = config or SelectorConfig()
        self.decision_history: list[SelectionDecision] = []

    def select(self, features: StateFeatures) -> SelectionDecision:
        """Select Strategy A, B, or C for the current dynamic event."""
        cfg = self.config
        overhead = cfg.selection_overhead_evals

        # -------------------------------------------------------------------
        # Legacy Rule v2 Mode (for Ablation and Backward Compatibility)
        # -------------------------------------------------------------------
        if cfg.version == "v2":
            if features.remaining_eval_budget is not None:
                k = max(1, features.event_size)
                est_ins = k * features.uncommitted_count + (k * (k + 1)) // 2
                min_2opt_budget = getattr(cfg, "min_2opt_budget", 10)
                min_required = est_ins + min_2opt_budget
                if features.remaining_eval_budget < min_required:
                    decision = SelectionDecision(
                        chosen_strategy=StrategyChoice.A,
                        rationale=f"Budget fallback: remaining {features.remaining_eval_budget} < required {min_required} (ins={est_ins} + 2opt={min_2opt_budget})",
                        features=features,
                        overhead_evaluations=overhead,
                    )
                    self.decision_history.append(decision)
                    return decision

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

            if features.initial_dynamicity <= cfg.low_dyn_threshold:
                decision = SelectionDecision(
                    chosen_strategy=StrategyChoice.B,
                    rationale=f"Low dynamicity (alpha={features.initial_dynamicity:.2f} <= {cfg.low_dyn_threshold:.2f}): high win rate for 2-opt",
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
                    rationale=f"High dynamicity early-stage (alpha={features.initial_dynamicity:.2f}, revealed={features.revealed_ratio:.2f}): avoiding myopic trap",
                    features=features,
                    overhead_evaluations=overhead,
                )
            self.decision_history.append(decision)
            return decision

        # -------------------------------------------------------------------
        # Adaptive v3: Three-Strategy Selection Logic (A, B, C)
        # -------------------------------------------------------------------
        k = max(1, features.event_size)
        m = features.uncommitted_count
        est_ins = k * m + (k * (k + 1)) // 2
        suffix_edges = m + k + 1
        m_new = m + k
        rem_budget = features.remaining_eval_budget

        # 1. Strategy B Eligibility
        min_2opt_budget = getattr(cfg, "min_2opt_budget", 10)
        req_b = est_ins + min_2opt_budget
        b_budget_ok = (rem_budget is None) or (rem_budget >= req_b)
        b_struct_ok = (suffix_edges >= cfg.min_suffix_for_2opt)
        eligible_b = b_budget_ok and b_struct_ok

        # 2. Strategy C Eligibility
        q = max(1, int(m_new * cfg.c_destroy_fraction))
        q = min(q, m_new)
        m_part = max(1, m_new - q)
        op = RepairOperator.CHEAPEST if cfg.c_repair_operator == "cheapest" else RepairOperator.REGRET_2
        req_repair_c = calculate_repair_evaluations(q, m_part + 1, op)
        req_c = est_ins + req_repair_c
        c_budget_ok = (rem_budget is None) or (rem_budget >= req_c)
        c_struct_ok = (m_new >= cfg.min_suffix_for_c) and (q >= 1)
        eligible_c = c_budget_ok and c_struct_ok

        # 3. Restructuring Need Assessment (Should Strategy C be preferred?)
        c_desired = False
        c_reasons = []

        # Criterion C1: Arrival Burst / Shock (multi-vertex event)
        if features.event_size >= cfg.burst_arrival_threshold:
            c_desired = True
            c_reasons.append(f"arrival burst (|Delta_t|={features.event_size} >= {cfg.burst_arrival_threshold})")
        elif features.burst_arrival_ratio >= cfg.burst_arrival_ratio and features.event_size > 1:
            c_desired = True
            c_reasons.append(f"high arrival shock ratio ({features.burst_arrival_ratio:.2f} >= {cfg.burst_arrival_ratio:.2f})")

        # Criterion C2: Mid-Stage High Dynamicity Restructuring
        if (features.initial_dynamicity >= cfg.high_dynamicity_c_threshold and
            cfg.c_mid_stage_min <= features.revealed_ratio <= cfg.c_mid_stage_max and
            m_new >= cfg.min_suffix_for_c):
            c_desired = True
            c_reasons.append(f"high dynamicity mid-stage diversification (alpha={features.initial_dynamicity:.2f}, revealed={features.revealed_ratio:.2f})")

        # Criterion C3: Significant Route Cost Deterioration
        if features.relative_cost_change >= cfg.cost_increase_threshold and m_new >= cfg.min_suffix_for_c:
            c_desired = True
            c_reasons.append(f"route deterioration jump (+{features.relative_cost_change*100:.1f}% >= +{cfg.cost_increase_threshold*100:.1f}%)")

        # 4. Strategy Selection and Fallback Cascade
        if c_desired:
            if eligible_c:
                decision = SelectionDecision(
                    chosen_strategy=StrategyChoice.C,
                    rationale=f"Strategy C (Destroy-Repair) selected: {'; '.join(c_reasons)} [budget ok: rem={rem_budget} >= req={req_c}]",
                    features=features,
                    overhead_evaluations=overhead,
                )
            elif eligible_b:
                # Graceful degradation from C to B
                decision = SelectionDecision(
                    chosen_strategy=StrategyChoice.B,
                    rationale=f"Budget fallback (C -> B): desired C ({'; '.join(c_reasons)}) requires {req_c} > rem {rem_budget}; degrading to 2-opt [req={req_b}]",
                    features=features,
                    overhead_evaluations=overhead,
                )
            else:
                # Graceful degradation to A
                decision = SelectionDecision(
                    chosen_strategy=StrategyChoice.A,
                    rationale=f"Budget fallback (C -> A): desired C requires {req_c} > rem {rem_budget} and B requires {req_b} > rem; safe Greedy Insertion fallback",
                    features=features,
                    overhead_evaluations=overhead,
                )
            self.decision_history.append(decision)
            return decision

        # 5. Local Search Strategy B Evaluation
        b_desired = False
        b_reason = ""
        if features.initial_dynamicity <= cfg.low_dyn_threshold:
            b_desired = True
            b_reason = f"low dynamicity (alpha={features.initial_dynamicity:.2f} <= {cfg.low_dyn_threshold:.2f}): high win rate for 2-opt"
        elif features.revealed_ratio >= cfg.late_stage_threshold:
            b_desired = True
            b_reason = f"late-stage event (revealed={features.revealed_ratio:.2f} >= {cfg.late_stage_threshold:.2f}): commitment risk eliminated"

        if b_desired:
            if eligible_b:
                decision = SelectionDecision(
                    chosen_strategy=StrategyChoice.B,
                    rationale=f"Strategy B (2-opt) selected: {b_reason} [budget ok: rem={rem_budget} >= req={req_b}]",
                    features=features,
                    overhead_evaluations=overhead,
                )
            else:
                decision = SelectionDecision(
                    chosen_strategy=StrategyChoice.A,
                    rationale=f"Budget fallback (B -> A): desired B ({b_reason}) requires {req_b} > rem {rem_budget}; safe Greedy Insertion fallback",
                    features=features,
                    overhead_evaluations=overhead,
                )
            self.decision_history.append(decision)
            return decision

        # 6. Default to Strategy A
        decision = SelectionDecision(
            chosen_strategy=StrategyChoice.A,
            rationale=f"Strategy A (Greedy Insertion) selected: high dynamicity early-stage (alpha={features.initial_dynamicity:.2f}, revealed={features.revealed_ratio:.2f}); avoiding myopic trap",
            features=features,
            overhead_evaluations=overhead,
        )
        self.decision_history.append(decision)
        return decision

    def reset(self) -> None:
        """Clear decision history for a fresh simulation run."""
        self.decision_history.clear()
