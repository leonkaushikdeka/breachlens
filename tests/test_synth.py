"""Tests for the synthetic data generator."""

from __future__ import annotations

import pytest

from breachlens.config import FEATURE_NAMES, TARGET
from breachlens.synth import GenerativeParams, generate_synthetic_breaches


@pytest.mark.unit
def test_generate_shape_and_columns() -> None:
    df = generate_synthetic_breaches(n=120, seed=1)
    assert len(df) == 120
    assert list(df.columns) == [*FEATURE_NAMES, TARGET]


@pytest.mark.unit
def test_generate_is_reproducible() -> None:
    a = generate_synthetic_breaches(n=50, seed=7)
    b = generate_synthetic_breaches(n=50, seed=7)
    assert a.equals(b)


@pytest.mark.unit
def test_generate_costs_are_positive_and_calibrated() -> None:
    df = generate_synthetic_breaches(n=500, seed=3)
    assert (df[TARGET] >= GenerativeParams().min_cost).all()
    # Calibrated to roughly the IBM India magnitude (~₹17.5 crore mean).
    assert 14 <= df[TARGET].mean() <= 21


@pytest.mark.unit
def test_security_score_reduces_cost_on_average() -> None:
    df = generate_synthetic_breaches(n=2000, seed=5)
    high = df[df["security_score"] > df["security_score"].median()][TARGET].mean()
    low = df[df["security_score"] <= df["security_score"].median()][TARGET].mean()
    assert high < low


@pytest.mark.unit
def test_generate_rejects_non_positive_n() -> None:
    with pytest.raises(ValueError):
        generate_synthetic_breaches(n=0)
