"""Regulatory penalty exposure models.

Breach cost is not only recovery and lost business — for many organisations the
largest and most feared component is the **regulatory fine**. These models encode the
real statutory schedules and return an *exposure estimate* scaled by breach size and
severity. They are decision-support estimates, not legal determinations; actual fines
are set by the relevant authority weighing many factors.

Sources
-------
- **DPDP Act 2023 (India)**, the Schedule: failure to take reasonable security
  safeguards to prevent a personal data breach — penalty up to **₹250 crore**; failure
  to notify the Board/affected principals — up to ₹200 crore. The Data Protection
  Board determines the amount (s.33) considering nature, gravity, and duration.
- **GDPR (EU)**, Art. 83(5): up to **€20 million or 4% of global annual turnover**,
  whichever is higher.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .benchmarks import Jurisdiction


@dataclass(frozen=True)
class PenaltyResult:
    expected: float  # exposure estimate, in the jurisdiction's display unit
    statutory_max: float  # the legal maximum, in the same unit
    regime: str
    basis: str

    @property
    def share_of_max(self) -> float:
        return self.expected / self.statutory_max if self.statutory_max else 0.0


# DPDP "failure to prevent a breach" maximum, in ₹ crore.
DPDP_MAX_CRORE: float = 250.0
# GDPR fixed cap in € million (the 4%-of-turnover branch can exceed this).
GDPR_FIXED_CAP_MILLION: float = 20.0
GDPR_TURNOVER_RATE: float = 0.04
# US has no single federal cap; approximate combined regulatory + litigation exposure
# per exposed record (class-action settlements commonly fall in this band), in USD.
US_PER_RECORD_USD: float = 90.0

# Records at which exposure approaches saturation (controls how fast big breaches
# approach the statutory ceiling).
_SATURATION_RECORDS: float = 200_000.0


def _saturation(records_actual: float) -> float:
    """0→1 curve: larger breaches push exposure toward the statutory ceiling."""
    return 1.0 - math.exp(-max(0.0, records_actual) / _SATURATION_RECORDS)


def regulatory_penalty(
    jurisdiction: Jurisdiction | str,
    records_actual: float,
    *,
    severity: float = 0.35,
    turnover_million: float | None = None,
) -> PenaltyResult:
    """Estimate regulatory penalty exposure for a breach.

    Args:
        jurisdiction: Which regime applies.
        records_actual: Number of personal-data records exposed (absolute count).
        severity: 0–1 estimate of regulatory severity (negligence, sensitivity of
            data, repeat offence). Higher → closer to the statutory maximum.
        turnover_million: Global annual turnover (€/$ million) for the GDPR
            4%-of-turnover branch. Ignored for other regimes.

    Returns:
        A :class:`PenaltyResult` in the jurisdiction's display unit.
    """
    code = (
        Jurisdiction(jurisdiction) if not isinstance(jurisdiction, Jurisdiction) else jurisdiction
    )
    severity = min(1.0, max(0.0, severity))
    scale = _saturation(records_actual)

    if code is Jurisdiction.IN:
        expected = DPDP_MAX_CRORE * scale * severity
        return PenaltyResult(
            expected=min(expected, DPDP_MAX_CRORE),
            statutory_max=DPDP_MAX_CRORE,
            regime="DPDP Act 2023",
            basis="Up to ₹250 cr for failure to prevent a breach (the Schedule).",
        )

    if code is Jurisdiction.EU:
        cap = GDPR_FIXED_CAP_MILLION
        if turnover_million is not None:
            cap = max(cap, GDPR_TURNOVER_RATE * turnover_million)
        expected = cap * scale * severity
        return PenaltyResult(
            expected=min(expected, cap),
            statutory_max=cap,
            regime="GDPR Art. 83(5)",
            basis="Up to €20M or 4% of global turnover, whichever is higher.",
        )

    # United States — no fixed cap; per-record regulatory + litigation exposure.
    raw_million = (US_PER_RECORD_USD * records_actual / 1e6) * severity
    statutory_max = US_PER_RECORD_USD * records_actual / 1e6
    return PenaltyResult(
        expected=raw_million,
        statutory_max=statutory_max,
        regime="US state laws + litigation",
        basis="≈ $90/record combined regulatory + class-action exposure.",
    )
