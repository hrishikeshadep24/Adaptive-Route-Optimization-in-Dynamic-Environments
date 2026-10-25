"""Pre-Phase 9 Research Audit Package.

Provides claim inventories, independent recomputations, experimental fairness
verifications, and reproducibility audits for all empirical results.
"""

from adaptive_route_optimization.audit.inventory import (
    Claim,
    ClaimStatus,
    MetricType,
    CLAIMS_INVENTORY,
)
from adaptive_route_optimization.audit.recompute import RawDataRecomputer
from adaptive_route_optimization.audit.fairness import FairnessAuditor, FairnessCheckResult
from adaptive_route_optimization.audit.reproducibility import (
    ReproducibilityAuditor,
    ReproducibilityCheckResult,
)
from adaptive_route_optimization.audit.runner import ResearchAuditor

__all__ = [
    "Claim",
    "ClaimStatus",
    "MetricType",
    "CLAIMS_INVENTORY",
    "RawDataRecomputer",
    "FairnessAuditor",
    "FairnessCheckResult",
    "ReproducibilityAuditor",
    "ReproducibilityCheckResult",
    "ResearchAuditor",
]
