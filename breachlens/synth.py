"""Transparent synthetic breach-data generator.

Real per-company breach costs are confidential and unpublished, so BreachLens ships
a synthetic dataset calibrated to the magnitudes in the IBM *Cost of a Data Breach*
report for India (real average ≈ ₹19.5 crore; this generator centres near ₹17.5
crore). The generative model is fully documented here so anyone can audit, tweak, or
regenerate the data — no hidden "magic" dataset.

The relationship is intentionally linear-with-noise so that an honest model can
recover interpretable coefficients, while the noise term keeps R² realistic rather
than a perfect 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import FEATURE_NAMES, TARGET


@dataclass(frozen=True)
class GenerativeParams:
    """Coefficients of the ground-truth cost function (in ₹ crore).

    cost = intercept
         + per_record       * records_exposed
         + per_detect_day   * detection_time
         + per_response_day * response_time
         - per_security_pt  * security_score
         + Normal(0, noise_sd)
    """

    intercept: float = 9.6
    per_record: float = 0.040
    per_detect_day: float = 0.020
    per_response_day: float = 0.030
    per_security_pt: float = 0.120
    noise_sd: float = 3.0
    min_cost: float = 3.0


def generate_synthetic_breaches(
    n: int = 200,
    seed: int = 2,
    params: GenerativeParams | None = None,
) -> pd.DataFrame:
    """Generate ``n`` synthetic breach records.

    Args:
        n: Number of records to produce.
        seed: RNG seed for reproducibility.
        params: Ground-truth cost coefficients. Defaults to the calibrated set.

    Returns:
        DataFrame with the four feature columns plus ``breach_cost``.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer.")

    p = params or GenerativeParams()
    rng = np.random.default_rng(seed)

    records_exposed = rng.integers(13, 501, size=n)
    detection_time = rng.integers(10, 296, size=n)
    response_time = rng.integers(6, 121, size=n)
    security_score = rng.integers(20, 96, size=n)

    noise = rng.normal(0.0, p.noise_sd, size=n)
    cost = (
        p.intercept
        + p.per_record * records_exposed
        + p.per_detect_day * detection_time
        + p.per_response_day * response_time
        - p.per_security_pt * security_score
        + noise
    )
    cost = np.clip(cost, p.min_cost, None).round(2)

    frame = pd.DataFrame(
        {
            "records_exposed": records_exposed,
            "detection_time": detection_time,
            "response_time": response_time,
            "security_score": security_score,
            TARGET: cost,
        }
    )
    return frame[[*FEATURE_NAMES, TARGET]]
