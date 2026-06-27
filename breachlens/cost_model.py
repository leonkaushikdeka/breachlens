"""Transparent, benchmark-driven breach-cost estimator.

This replaces the original "ML on a synthetic formula" core. Every step is an explicit,
cited transformation of published industry figures, so the estimate can be audited and
explained — which is exactly what a board, an auditor, or an insurer requires.

    operational = regional_average
                × (records / reference_records) ** scaling_exponent   # size
                × industry_multiplier                                 # sector
                × lifecycle_multiplier(detection + containment days)  # speed
                × maturity_multiplier(security score)                 # posture
                × control_factor(extra controls)                      # investments

    total = operational  (recovery + lost business)  +  regulatory_penalty
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .benchmarks import (
    INDUSTRY_MULTIPLIERS,
    LIFECYCLE_MULT_MAX,
    LIFECYCLE_MULT_MIN,
    LIFECYCLE_PIVOT_DAYS,
    LIFECYCLE_SLOPE_PER_DAY,
    MATURITY_MULT_AT_ZERO,
    MATURITY_SLOPE_PER_POINT,
    RECORD_SCALING_EXPONENT,
    JurisdictionBenchmark,
    jurisdiction,
)
from .controls import cost_reduction_factor
from .penalties import regulatory_penalty
from .schema import OrgProfile

# IBM splits breach cost across detection/escalation, notification, post-breach
# response and lost business. We surface a recovery/lost-business split for the report.
_LOST_BUSINESS_SHARE = 0.38


def lifecycle_multiplier(days: float) -> float:
    """Cost multiplier from total breach lifecycle, pivoting at 200 days."""
    raw = 1.0 + LIFECYCLE_SLOPE_PER_DAY * (days - LIFECYCLE_PIVOT_DAYS)
    return min(LIFECYCLE_MULT_MAX, max(LIFECYCLE_MULT_MIN, raw))


def maturity_multiplier(security_score: float) -> float:
    """Cost multiplier from security posture (0-100); stronger posture lowers cost."""
    raw = MATURITY_MULT_AT_ZERO - MATURITY_SLOPE_PER_POINT * security_score
    return min(1.30, max(0.70, raw))


@dataclass(frozen=True)
class CostBreakdown:
    """A fully itemised breach-cost estimate in one jurisdiction's display unit."""

    recovery: float
    lost_business: float
    regulatory: float
    benchmark: JurisdictionBenchmark
    drivers: dict[str, float] = field(default_factory=dict)

    @property
    def operational(self) -> float:
        return self.recovery + self.lost_business

    @property
    def total(self) -> float:
        return self.operational + self.regulatory

    def format(self, value: float, decimals: int = 2) -> str:
        return self.benchmark.format(value, decimals)

    def as_dict(self) -> dict[str, float]:
        return {
            "recovery": self.recovery,
            "lost_business": self.lost_business,
            "regulatory": self.regulatory,
            "operational": self.operational,
            "total": self.total,
        }


def estimate_cost(profile: OrgProfile, controls: list[str] | None = None) -> CostBreakdown:
    """Produce a transparent breach-cost breakdown for an organisation profile.

    Args:
        profile: The breach scenario (records, lifecycle, posture, industry, region).
        controls: Optional extra security controls to credit (see ``controls``).
    """
    jb = jurisdiction(profile.jurisdiction)

    size_factor = (profile.records_actual / jb.ref_records) ** RECORD_SCALING_EXPONENT
    industry_mult = INDUSTRY_MULTIPLIERS[profile.industry]
    lifecycle_mult = lifecycle_multiplier(profile.lifecycle_days)
    maturity_mult = maturity_multiplier(profile.security_score)
    control_factor = cost_reduction_factor(controls or [])

    operational = (
        jb.avg_total * size_factor * industry_mult * lifecycle_mult * maturity_mult * control_factor
    )

    penalty = regulatory_penalty(
        profile.jurisdiction,
        profile.records_actual,
        severity=profile.regulatory_severity,
        turnover_million=profile.turnover_million,
    )

    return CostBreakdown(
        recovery=operational * (1.0 - _LOST_BUSINESS_SHARE),
        lost_business=operational * _LOST_BUSINESS_SHARE,
        regulatory=penalty.expected,
        benchmark=jb,
        drivers={
            "size_factor": size_factor,
            "industry_multiplier": industry_mult,
            "lifecycle_multiplier": lifecycle_mult,
            "maturity_multiplier": maturity_mult,
            "control_factor": control_factor,
        },
    )
