"""BreachLens — open-source cyber breach cost & risk quantification engine.

Estimate the financial cost of a data breach from measurable security factors,
quantify the uncertainty, explain the drivers, and simulate which security
investments actually reduce the cost.

Quick start::

    from breachlens import BreachLens, BreachProfile

    lens = BreachLens.load_or_train()
    profile = BreachProfile(
        records_exposed=300, detection_time=200, response_time=90, security_score=40
    )
    result = lens.predict(profile)
    print(lens.format(result.expected_cost))
"""

from __future__ import annotations

from .config import FEATURES, REGIONS, get_region
from .models import BreachModel, benchmark_models, train
from .predictor import BreachLens
from .schema import BreachProfile, PredictionResult

__all__ = [
    "BreachLens",
    "BreachProfile",
    "PredictionResult",
    "BreachModel",
    "FEATURES",
    "REGIONS",
    "get_region",
    "benchmark_models",
    "train",
]

__version__ = "1.0.0"
