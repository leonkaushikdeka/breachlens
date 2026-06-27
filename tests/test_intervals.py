"""Tests for split conformal prediction intervals."""

from __future__ import annotations

import numpy as np
import pytest

from breachlens.intervals import ConformalCalibrator


@pytest.mark.unit
def test_half_width_grows_with_confidence() -> None:
    rng = np.random.default_rng(0)
    cal = ConformalCalibrator.from_predictions(rng.normal(size=500), rng.normal(size=500))
    assert cal.half_width(0.8) <= cal.half_width(0.95)


@pytest.mark.unit
def test_interval_is_symmetric_and_nonnegative() -> None:
    cal = ConformalCalibrator.from_predictions(np.zeros(100), np.ones(100))
    lower, upper = cal.interval(10.0, confidence=0.9)
    assert lower >= 0
    assert pytest.approx((upper + lower) / 2, abs=1e-9) == 10.0 or lower == 0


@pytest.mark.unit
def test_lower_bound_clipped_at_zero() -> None:
    cal = ConformalCalibrator.from_predictions(np.zeros(50), np.full(50, 5.0))
    lower, _ = cal.interval(1.0, confidence=0.9)
    assert lower == 0.0


@pytest.mark.unit
def test_empirical_coverage_meets_nominal() -> None:
    rng = np.random.default_rng(42)
    y = rng.normal(0, 1, size=2000)
    pred = np.zeros_like(y)
    cal = ConformalCalibrator.from_predictions(y[:1000], pred[:1000])
    h = cal.half_width(0.9)
    covered = (np.abs(y[1000:] - pred[1000:]) <= h).mean()
    assert covered >= 0.88


@pytest.mark.unit
def test_invalid_confidence_rejected() -> None:
    cal = ConformalCalibrator.from_predictions(np.zeros(10), np.zeros(10))
    with pytest.raises(ValueError):
        cal.half_width(1.5)


@pytest.mark.unit
def test_empty_calibration_rejected() -> None:
    with pytest.raises(ValueError):
        ConformalCalibrator.from_predictions(np.array([]), np.array([]))
