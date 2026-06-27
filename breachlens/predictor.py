"""High-level facade: the one object apps, the API and the CLI talk to.

The **benchmark engine** (cited industry figures + regulatory penalties + Monte Carlo)
is the primary, credible path. A machine-learning model trained on real breach data you
supply is available as an optional second opinion.
"""

from __future__ import annotations

import pandas as pd

from .benchmarks import JurisdictionBenchmark, jurisdiction
from .cost_model import CostBreakdown, estimate_cost
from .models import BreachModel, train
from .montecarlo import MonteCarloResult, simulate
from .scenario import InvestmentCase, build_investment_case, sweep
from .schema import OrgProfile, PredictionResult


class BreachLens:
    """Breach-cost estimation with uncertainty, explanation and investment ROI."""

    def __init__(self, ml_model: BreachModel | None = None) -> None:
        self.ml_model = ml_model

    # --- coercion -------------------------------------------------------------
    @staticmethod
    def _coerce(profile: OrgProfile | dict) -> OrgProfile:
        return profile if isinstance(profile, OrgProfile) else OrgProfile(**profile)

    # --- benchmark engine (primary) ------------------------------------------
    def estimate(
        self, profile: OrgProfile | dict, controls: list[str] | None = None
    ) -> CostBreakdown:
        """Transparent, cited breach-cost breakdown (recovery + lost business + fines)."""
        return estimate_cost(self._coerce(profile), controls)

    def simulate(
        self,
        profile: OrgProfile | dict,
        controls: list[str] | None = None,
        *,
        n: int = 10_000,
        seed: int = 2,
    ) -> MonteCarloResult:
        """Monte Carlo cost distribution (expected, P50/P90/P95, exceedance curve)."""
        return simulate(self._coerce(profile), controls, n=n, seed=seed)

    def investment_case(
        self,
        profile: OrgProfile | dict,
        add_controls: list[str],
        *,
        investment: float,
        breach_probability: float | None = None,
    ) -> InvestmentCase:
        """ROI of adding security controls (savings, ROI, payback)."""
        return build_investment_case(
            self._coerce(profile),
            add_controls,
            investment=investment,
            breach_probability=breach_probability,
        )

    def sweep(self, profile: OrgProfile | dict, feature: str, *, n: int = 30) -> pd.DataFrame:
        """How total cost responds as one factor varies across its range."""
        return sweep(self._coerce(profile), feature, n=n)

    @staticmethod
    def benchmark(profile: OrgProfile | dict) -> JurisdictionBenchmark:
        p = profile if isinstance(profile, OrgProfile) else OrgProfile(**profile)
        return jurisdiction(p.jurisdiction)

    @staticmethod
    def money(profile: OrgProfile | dict, value: float, decimals: int = 2) -> str:
        return BreachLens.benchmark(profile).format(value, decimals)

    # --- optional ML second opinion ------------------------------------------
    @classmethod
    def with_ml(cls, **train_kwargs) -> BreachLens:
        """Attach an ML model trained on the bundled (or supplied) dataset."""
        return cls(ml_model=train(**train_kwargs))

    def predict_ml(self, profile: OrgProfile | dict, confidence: float = 0.9) -> PredictionResult:
        if self.ml_model is None:
            raise RuntimeError("No ML model attached. Use BreachLens.with_ml() first.")
        p = self._coerce(profile)
        frame = pd.DataFrame([p.to_features()])
        point, lower, upper = self.ml_model.predict_interval(frame, confidence)
        return PredictionResult(
            expected_cost=float(point[0]),
            lower=float(lower[0]),
            upper=float(upper[0]),
            confidence=confidence,
            model_name=self.ml_model.name,
        )
