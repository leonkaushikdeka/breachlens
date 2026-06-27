"""What-if simulation and security-investment ROI.

Turns the cost estimate into a decision: "if we invest ₹X in these controls, the
expected breach cost drops by ₹Y — here is the ROI and payback." Each control's effect
is anchored to a published IBM cost factor (see :mod:`breachlens.controls`).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .benchmarks import INDUSTRY_BREACH_FREQUENCY
from .controls import frequency_reduction_factor
from .cost_model import CostBreakdown, estimate_cost
from .schema import OrgProfile

_SWEEPABLE = ("records_exposed", "detection_time", "response_time", "security_score")
# Illustrative base annual probability of a material breach for an average-frequency
# sector; scaled by the industry's relative likelihood.
_BASE_ANNUAL_PROBABILITY = 0.22


def annual_breach_probability(profile: OrgProfile, controls: list[str] | None = None) -> float:
    """Illustrative annual probability of a material breach, 0-1."""
    freq = INDUSTRY_BREACH_FREQUENCY[profile.industry]
    prob = _BASE_ANNUAL_PROBABILITY * freq * frequency_reduction_factor(controls or [])
    return min(0.95, max(0.0, prob))


def apply_changes(profile: OrgProfile, changes: dict[str, float]) -> OrgProfile:
    """Return a new, re-validated profile with ``changes`` applied (immutably).

    Reconstructs the model (rather than ``model_copy``) so field validators run and
    out-of-range changes are rejected.
    """
    return type(profile)(**{**profile.model_dump(), **changes})


@dataclass(frozen=True)
class InvestmentCase:
    """Before/after comparison for a set of security investments."""

    baseline: CostBreakdown
    improved: CostBreakdown
    added_controls: list[str]
    investment: float
    breach_probability: float

    @property
    def gross_savings(self) -> float:
        """Reduction in the estimated breach cost if a breach occurs."""
        return self.baseline.total - self.improved.total

    @property
    def expected_savings(self) -> float:
        """Risk-adjusted annual saving (gross savings × breach probability)."""
        return self.gross_savings * self.breach_probability

    @property
    def net_benefit(self) -> float:
        return self.expected_savings - self.investment

    @property
    def roi(self) -> float:
        return self.net_benefit / self.investment if self.investment > 0 else float("inf")

    @property
    def payback_years(self) -> float:
        return (
            self.investment / self.expected_savings if self.expected_savings > 0 else float("inf")
        )


def build_investment_case(
    profile: OrgProfile,
    add_controls: list[str],
    *,
    investment: float,
    breach_probability: float | None = None,
) -> InvestmentCase:
    """Quantify the ROI of adding security controls to an organisation.

    Args:
        profile: The organisation's current breach scenario.
        add_controls: Control keys to add (see :data:`breachlens.controls.CONTROL_CATALOG`).
        investment: Annual cost of the controls, in the jurisdiction's display unit.
        breach_probability: Annual breach likelihood; defaults to an industry estimate.
    """
    baseline = estimate_cost(profile)
    improved = estimate_cost(profile, controls=add_controls)
    prob = (
        breach_probability
        if breach_probability is not None
        else annual_breach_probability(profile, add_controls)
    )
    return InvestmentCase(
        baseline=baseline,
        improved=improved,
        added_controls=list(add_controls),
        investment=investment,
        breach_probability=prob,
    )


def sweep(profile: OrgProfile, feature: str, *, n: int = 30) -> pd.DataFrame:
    """Sweep one core factor across its range, returning total estimated cost.

    Returns a DataFrame with ``value`` and the cost components for plotting how breach
    cost responds to that factor.
    """
    if feature not in _SWEEPABLE:
        raise ValueError(f"Cannot sweep '{feature}'. Choose from {_SWEEPABLE}.")

    from .config import FEATURE_BY_NAME

    spec = FEATURE_BY_NAME[feature]
    rows = []
    for i in range(n):
        value = spec.min + (spec.max - spec.min) * i / (n - 1)
        breakdown = estimate_cost(apply_changes(profile, {feature: value}))
        rows.append(
            {
                "value": value,
                "operational": breakdown.operational,
                "regulatory": breakdown.regulatory,
                "total": breakdown.total,
            }
        )
    return pd.DataFrame(rows)
