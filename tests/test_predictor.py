"""Tests for the BreachLens facade and schema validation."""

from __future__ import annotations

import pytest

from breachlens import BreachLens, BreachProfile
from breachlens.config import FEATURE_NAMES


@pytest.mark.unit
def test_profile_validation_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        BreachProfile(records_exposed=5, detection_time=200, response_time=90, security_score=40)


@pytest.mark.unit
def test_profile_midpoint_is_valid() -> None:
    p = BreachProfile.midpoint()
    assert set(p.to_features()) == set(FEATURE_NAMES)


@pytest.mark.integration
def test_predict_accepts_dict(lens: BreachLens) -> None:
    result = lens.predict(
        {"records_exposed": 300, "detection_time": 200, "response_time": 90, "security_score": 40}
    )
    assert result.expected_cost > 0
    assert result.lower <= result.expected_cost <= result.upper


@pytest.mark.integration
def test_explain_contributions_sum_close_to_prediction(lens: BreachLens) -> None:
    profile = BreachProfile(
        records_exposed=420, detection_time=250, response_time=110, security_score=30
    )
    contributions = lens.explain(profile)
    baseline = contributions.attrs["baseline_cost"]
    reconstructed = baseline + contributions["contribution"].sum()
    predicted = lens.predict(profile).expected_cost
    # Linear model -> additive attribution should reconstruct exactly.
    assert reconstructed == pytest.approx(predicted, abs=0.5)


@pytest.mark.integration
def test_importance_sums_to_one(lens: BreachLens) -> None:
    imp = lens.importance()
    assert imp["importance_norm"].sum() == pytest.approx(1.0, abs=1e-6)


@pytest.mark.unit
def test_format_uses_region(lens: BreachLens) -> None:
    assert lens.format(18.24).startswith("₹")
    assert "crore" in lens.format(18.24)


@pytest.mark.unit
def test_us_region_formats_in_dollars() -> None:
    from breachlens.models import train

    us = BreachLens(model=train(seed=2), region=None)
    us.region = __import__("breachlens").get_region("US")
    assert us.format(10.0).startswith("$")
