"""Prediction intervals via split conformal prediction.

A point estimate alone ("the breach will cost ₹18 crore") is not credible for risk
decisions. Split conformal prediction gives a distribution-free interval with a
finite-sample coverage guarantee: hold out a calibration set the model never trained
on, measure absolute residuals, and use their quantile as a ± band. No assumption of
Gaussian errors required.

Reference: Vovk et al.; Lei et al. (2018), "Distribution-Free Predictive Inference
for Regression".
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ConformalCalibrator:
    """Holds absolute residuals from a calibration set to build ± intervals."""

    abs_residuals: np.ndarray

    @classmethod
    def from_predictions(cls, y_true: np.ndarray, y_pred: np.ndarray) -> ConformalCalibrator:
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        if y_true.shape != y_pred.shape:
            raise ValueError("y_true and y_pred must have the same shape.")
        if y_true.size == 0:
            raise ValueError("Calibration set must contain at least one sample.")
        return cls(abs_residuals=np.sort(np.abs(y_true - y_pred)))

    def half_width(self, confidence: float = 0.9) -> float:
        """Return the ± half-width for the requested confidence level.

        Uses the finite-sample conformal quantile rank
        ``ceil((n + 1)(1 - alpha)) / n`` rather than the naive empirical quantile,
        which is what gives the coverage guarantee.
        """
        if not 0.0 < confidence < 1.0:
            raise ValueError("confidence must be in the open interval (0, 1).")
        n = self.abs_residuals.size
        alpha = 1.0 - confidence
        rank = math.ceil((n + 1) * (1.0 - alpha))
        if rank >= n:  # interval not finite at this confidence given calibration size
            return float(self.abs_residuals[-1])
        return float(self.abs_residuals[rank - 1])

    def interval(self, point: float, confidence: float = 0.9) -> tuple[float, float]:
        """Return ``(lower, upper)`` around a point estimate (lower clipped at 0)."""
        h = self.half_width(confidence)
        return max(0.0, point - h), point + h
