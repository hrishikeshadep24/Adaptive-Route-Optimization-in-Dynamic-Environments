"""Schema and Data Structures for Experimental Framework.



Defines configuration models, run records, step records, and manifest schemas

for controlled dynamic routing experiments.

References: RESEARCH_SPEC.md (Evaluation Metrics, Computational Budget),

PHASE_PLAN.md (Phase 6 tasks: raw-result schema, config files).

"""



from __future__ import annotations

from dataclasses import dataclass, field, asdict

from enum import Enum

from typing import Any, Optional, Sequence

import json





class BudgetType(str, Enum):

    """Type of computational budget enforced during dynamic repair."""

    UNBOUNDED = "unbounded"

    MAX_EVALUATIONS = "max_evaluations"

    MAX_PASSES = "max_passes"

    MAX_WALL_CLOCK_MS = "max_wall_clock_ms"





@dataclass(frozen=True)

class BudgetConfig:

    """Configuration for computational budget.



    Attributes:

        budget_type: Type of budget (evaluation count, passes, or unbounded).

        limit: Numeric limit value (None if unbounded).

        rationale: Justification for budget choice.

    """

    budget_type: BudgetType = BudgetType.UNBOUNDED

    limit: Optional[int | float] = None

    rationale: str = "Unbounded baseline execution"
    budget_scope: str = "per_step"



    def to_dict(self) -> dict[str, Any]:

        return {

            "budget_type": self.budget_type.value,

            "limit": self.limit,

            "rationale": self.rationale,

        }



    @classmethod

    def from_dict(cls, data: dict[str, Any]) -> BudgetConfig:

        return cls(

            budget_type=BudgetType(data.get("budget_type", BudgetType.UNBOUNDED.value)),

            limit=data.get("limit"),

            rationale=data.get("rationale", ""),
            budget_scope=data.get("budget_scope", "per_step"),

        )





@dataclass(frozen=True)

class ConditionConfig:

    """Experimental condition configuration.



    Attributes:

        condition_id: Unique string identifier for condition (e.g. 'n50_d0.4').

        total_vertices: Total customer vertices n (excluding depot).

        dynamicity: Fraction of customer vertices revealed dynamically (α ∈ [0, 1]).

        events_per_step: Number of vertices revealed per event (|Δ_t|).

        freeze_per_step: Number of vertices frozen per step.

        vertex_order: Revelation order ('random', 'index', 'distance').

        distribution: Spatial distribution of vertices ('uniform', 'clustered').

        budget: Computational budget applied during repair.

    """

    condition_id: str

    total_vertices: int

    dynamicity: float

    events_per_step: int = 1

    freeze_per_step: int = 1

    vertex_order: str = "random"

    distribution: str = "uniform"

    budget: BudgetConfig = field(default_factory=BudgetConfig)

    distribution_params: dict[str, Any] = field(default_factory=dict)

    instance_source: str = "synthetic"

    benchmark_name: Optional[str] = None

    batch_schedule: Optional[tuple[int, ...]] = None

    replicate: int = 0

    distance_metric: str = "continuous_euclidean"
    budget_scope: str = "per_step"



    def __post_init__(self) -> None:

        if self.total_vertices < 0:

            raise ValueError(f"total_vertices must be >= 0, got {self.total_vertices}")

        if not (0.0 <= self.dynamicity <= 1.0):

            raise ValueError(f"dynamicity must be in [0, 1], got {self.dynamicity}")

        if self.events_per_step < 1:

            raise ValueError(f"events_per_step must be >= 1, got {self.events_per_step}")



    def to_dict(self) -> dict[str, Any]:

        return {

            "condition_id": self.condition_id,

            "total_vertices": self.total_vertices,

            "dynamicity": self.dynamicity,

            "events_per_step": self.events_per_step,

            "freeze_per_step": self.freeze_per_step,

            "vertex_order": self.vertex_order,

            "distribution": self.distribution,

            "budget": self.budget.to_dict(),

            "distribution_params": dict(self.distribution_params),

            "instance_source": self.instance_source,

            "benchmark_name": self.benchmark_name,

            "batch_schedule": list(self.batch_schedule) if self.batch_schedule is not None else None,

            "replicate": self.replicate,

            "distance_metric": self.distance_metric,
            "budget_scope": self.budget_scope,

        }



    @classmethod

    def from_dict(cls, data: dict[str, Any]) -> ConditionConfig:

        budget_data = data.get("budget", {})

        budget = BudgetConfig.from_dict(budget_data) if isinstance(budget_data, dict) else BudgetConfig()

        return cls(

            condition_id=data["condition_id"],

            total_vertices=int(data["total_vertices"]),

            dynamicity=float(data["dynamicity"]),

            events_per_step=int(data.get("events_per_step", 1)),

            freeze_per_step=int(data.get("freeze_per_step", 1)),

            vertex_order=data.get("vertex_order", "random"),

            distribution=data.get("distribution", "uniform"),

            budget=budget,

            distribution_params=dict(data.get("distribution_params", {})),

            instance_source=data.get("instance_source", "synthetic"),

            benchmark_name=data.get("benchmark_name"),

            batch_schedule=tuple(data["batch_schedule"]) if data.get("batch_schedule") is not None else None,

            replicate=int(data.get("replicate", 0)),

            distance_metric=str(data.get("distance_metric", "continuous_euclidean")),
            budget_scope=str(data.get("budget_scope", "per_step")),

        )





@dataclass(frozen=True)

class ExperimentConfig:

    """Top-level configuration for an experiment campaign.



    Attributes:

        name: Name of experiment suite.

        conditions: Tuple of experimental conditions.

        seeds: Sequence of random seeds to execute per condition.

        strategies: Strategies to evaluate (e.g. ['A', 'B']).

        output_dir: Directory where raw CSV and JSON results will be written.

        description: Description of experimental purpose.

    """

    name: str

    conditions: tuple[ConditionConfig, ...]

    seeds: tuple[int, ...]

    strategies: tuple[str, ...] = ("A", "B")

    output_dir: str = "results"

    description: str = ""



    def to_dict(self) -> dict[str, Any]:

        return {

            "name": self.name,

            "description": self.description,

            "seeds": list(self.seeds),

            "strategies": list(self.strategies),

            "output_dir": self.output_dir,

            "conditions": [c.to_dict() for c in self.conditions],

        }



    def to_json(self, indent: int = 2) -> str:

        return json.dumps(self.to_dict(), indent=indent)



    @classmethod

    def from_dict(cls, data: dict[str, Any]) -> ExperimentConfig:

        conditions = tuple(ConditionConfig.from_dict(c) for c in data.get("conditions", []))

        return cls(

            name=data["name"],

            conditions=conditions,

            seeds=tuple(int(s) for s in data.get("seeds", [])),

            strategies=tuple(str(s) for s in data.get("strategies", ("A", "B"))),

            output_dir=data.get("output_dir", "results"),

            description=data.get("description", ""),

        )



    @classmethod

    def from_json(cls, json_str: str) -> ExperimentConfig:

        return cls.from_dict(json.loads(json_str))



    @classmethod

    def load(cls, filepath: str) -> ExperimentConfig:

        with open(filepath, "r", encoding="utf-8") as f:

            return cls.from_dict(json.load(f))



    def save(self, filepath: str) -> None:

        with open(filepath, "w", encoding="utf-8") as f:

            f.write(self.to_json())





@dataclass(frozen=True)

class StepRecord:

    """Record of a single simulation event step."""

    time_step: int

    num_event_vertices: int

    num_known_vertices: int

    route_cost: float

    disruption: float

    feasible: bool

    computational_effort: int

    response_time_ms: float

    frozen_prefix_length: int
    candidate_evaluations: int = 0
    overhead_evaluations: int = 0
    scenario_fingerprint: str = ""



    def to_dict(self) -> dict[str, Any]:

        return asdict(self)





@dataclass(frozen=True)

class RunRecord:

    """Complete summary record of one simulation execution for one strategy.



    Standard raw-result schema matching RESEARCH_SPEC.md metrics, extended

    for Stage 4 matched fair comparison with hard budget controls.

    """

    run_id: str

    condition_id: str

    strategy: str

    seed: int

    total_vertices: int

    dynamicity: float

    num_events: int

    initial_cost: float

    final_cost: float

    cost_increase: float

    total_computational_effort: int

    total_response_time_ms: float

    mean_disruption: float

    max_disruption: float

    all_feasible: bool

    budget_type: str

    budget_limit: Optional[int | float]

    git_commit_hash: str

    timestamp: str

    distribution: str = "uniform"

    events_per_step: int = 1

    instance_source: str = "synthetic"

    benchmark_name: Optional[str] = None

    # Stage 4 matched comparison and audit enhancements:

    pair_id: str = ""

    instance_family: str = "synthetic_uniform"

    instance_id: str = ""

    replicate: int = 0

    distribution_params: str = "{}"

    arrival_schedule_type: str = "uniform_batch"

    budget_exhausted: bool = False

    budget_utilization: Optional[float] = None

    distance_metric: str = "continuous_euclidean"
    budget_scope: str = "per_step"

    frozen_prefix_preserved: bool = True

    algorithm_version: str = "stage4_v1.0"

    status: str = "SUCCESS"

    error_message: str = ""
    candidate_evaluations: int = 0
    overhead_evaluations: int = 0
    scenario_fingerprint: str = ""



    def to_dict(self) -> dict[str, Any]:

        return asdict(self)

