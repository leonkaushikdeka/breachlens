"""Monte Carlo simulation of breach cost.

A single number implies false precision. Real cyber-risk quantification (e.g. the FAIR
standard) reports a *distribution*: an expected loss plus the tail an organisation must
plan for. This module samples the uncertain inputs and returns percentiles and a
**loss-exceedance curve** — "there is a 10% chance the breach exceeds ₹X crore" — which
is the headline output boards and insurers actually use.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cost_model import estimate_cost
from .penalties import regulatory_penalty
from .schema import OrgProfile

# Residual (model + idiosyncratic) uncertainty applied to operational cost, as the
# sigma of a multiplicative lognormal shock.
_OPERATIONAL_SIGMA = 0.18


@dataclass(frozen=True)
class MonteCarloResult:
    samples: np.ndarray  # simulated total costs, in the jurisdiction's display unit
    currency_symbol: str
    unit_label: str

    @property
    def mean(self) -> float:
        return float(self.samples.mean())

    def percentile(self, q: float) -> float:
        return float(np.percentile(self.samples, q))

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p90(self) -> float:
        return self.percentile(90)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    def exceedance_curve(self, points: int = 60) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(loss, probability)`` where probability = P(total > loss)."""
        losses = np.linspace(0.0, self.percentile(99.5), points)
        probs = np.array([(self.samples > x).mean() for x in losses])
        return losses, probs

    def format(self, value: float, decimals: int = 2) -> str:
        unit = f" {self.unit_label}".rstrip()
        return f"{self.currency_symbol}{value:,.{decimals}f}{unit}"


def simulate(
    profile: OrgProfile,
    controls: list[str] | None = None,
    *,
    n: int = 10_000,
    seed: int = 2,
) -> MonteCarloResult:
    """Run a Monte Carlo simulation of the total breach cost.

    The regional average (the dominant uncertainty) is sampled from a triangular
    distribution between the published low/high band; operational cost carries a
    lognormal residual shock; and regulatory severity is sampled around the input.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer.")

    rng = np.random.default_rng(seed)
    base = estimate_cost(profile, controls)
    jb = base.benchmark

    # Deterministic product of all multipliers (everything except the regional average).
    multiplier = base.operational / jb.avg_total if jb.avg_total else 0.0

    avg_samples = rng.triangular(jb.avg_total_low, jb.avg_total, jb.avg_total_high, size=n)
    shock = rng.lognormal(mean=-0.5 * _OPERATIONAL_SIGMA**2, sigma=_OPERATIONAL_SIGMA, size=n)
    operational = avg_samples * multiplier * shock

    sev = profile.regulatory_severity
    severity_samples = np.clip(
        rng.triangular(max(0.0, sev * 0.5), sev, min(1.0, sev * 1.6 + 1e-6), size=n), 0.0, 1.0
    )
    # Penalty scales linearly with severity for a fixed breach size, so evaluate the
    # severity=1 value once and scale, rather than recomputing the model n times.
    penalty_unit = regulatory_penalty(
        profile.jurisdiction, profile.records_actual, severity=1.0
    ).expected
    penalty = penalty_unit * severity_samples

    totals = operational + penalty
    return MonteCarloResult(
        samples=totals, currency_symbol=jb.currency_symbol, unit_label=jb.unit_label
    )
