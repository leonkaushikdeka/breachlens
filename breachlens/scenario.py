"""What-if scenario simulation and security-ROI analysis.

This is what turns BreachLens from a predictor into a decision tool. A CISO does not
just want "your expected breach costs ₹18 crore" — they want "if we cut detection
time from 200 to 100 days, we save ₹X crore", so security spend can be justified with
a number.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import FEATURE_BY_NAME
from .models import BreachModel
from .schema import BreachProfile, PredictionResult


def predict_profile(
    model: BreachModel, profile: BreachProfile, confidence: float | None = None
) -> PredictionResult:
    """Score a single validated profile into a ``PredictionResult`` with interval."""
    conf = model.confidence if confidence is None else confidence
    frame = pd.DataFrame([profile.to_features()])
    point, lower, upper = model.predict_interval(frame, conf)
    return PredictionResult(
        expected_cost=float(point[0]),
        lower=float(lower[0]),
        upper=float(upper[0]),
        confidence=conf,
        model_name=model.name,
    )


def apply_changes(profile: BreachProfile, changes: dict[str, float]) -> BreachProfile:
    """Return a new, re-validated profile with ``changes`` applied (immutably)."""
    merged = {**profile.to_features(), **changes}
    return BreachProfile(**merged)


@dataclass(frozen=True)
class ScenarioResult:
    """Before/after comparison for a security improvement."""

    baseline: PredictionResult
    adjusted: PredictionResult
    changes: dict[str, float]

    @property
    def savings(self) -> float:
        """Reduction in expected cost (positive = money saved)."""
        return self.baseline.expected_cost - self.adjusted.expected_cost

    @property
    def savings_pct(self) -> float:
        if self.baseline.expected_cost == 0:
            return 0.0
        return self.savings / self.baseline.expected_cost


def what_if(
    model: BreachModel,
    profile: BreachProfile,
    changes: dict[str, float],
    confidence: float | None = None,
) -> ScenarioResult:
    """Compare a baseline profile against one with security improvements applied."""
    baseline = predict_profile(model, profile, confidence)
    adjusted = predict_profile(model, apply_changes(profile, changes), confidence)
    return ScenarioResult(baseline=baseline, adjusted=adjusted, changes=dict(changes))


def sweep_feature(
    model: BreachModel,
    profile: BreachProfile,
    feature: str,
    *,
    n: int = 25,
    confidence: float | None = None,
) -> pd.DataFrame:
    """Sweep one feature across its full range, holding others fixed.

    Returns a DataFrame (``value, expected, lower, upper``) for plotting the cost
    curve and the band around it.
    """
    if feature not in FEATURE_BY_NAME:
        raise ValueError(f"Unknown feature '{feature}'.")
    spec = FEATURE_BY_NAME[feature]
    conf = model.confidence if confidence is None else confidence

    values = np.linspace(spec.min, spec.max, n)
    base = profile.to_features()
    grid = pd.DataFrame([{**base, feature: v} for v in values])
    point, lower, upper = model.predict_interval(grid[model.feature_names], conf)

    return pd.DataFrame({"value": values, "expected": point, "lower": lower, "upper": upper})


def roi(
    scenario: ScenarioResult,
    investment_cost: float,
    breach_probability: float = 1.0,
) -> dict[str, float]:
    """Translate expected savings into a return-on-investment figure.

    Args:
        scenario: A computed what-if result (savings in native units, ₹ crore).
        investment_cost: Cost of the security improvement, in the same units.
        breach_probability: Annual probability the breach actually occurs (0-1),
            used to risk-adjust the savings into an expected value.

    Returns:
        Dict with ``expected_savings`` (risk-adjusted), ``investment_cost``,
        ``net_benefit`` and ``roi`` (net benefit / investment).
    """
    if not 0.0 <= breach_probability <= 1.0:
        raise ValueError("breach_probability must be between 0 and 1.")
    if investment_cost < 0:
        raise ValueError("investment_cost cannot be negative.")

    expected_savings = scenario.savings * breach_probability
    net = expected_savings - investment_cost
    return {
        "expected_savings": expected_savings,
        "investment_cost": investment_cost,
        "net_benefit": net,
        "roi": (net / investment_cost) if investment_cost > 0 else float("inf"),
    }
