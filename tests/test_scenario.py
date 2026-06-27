"""Tests for the what-if scenario engine and ROI."""

from __future__ import annotations

import pytest

from breachlens.models import BreachModel
from breachlens.scenario import apply_changes, predict_profile, roi, sweep_feature, what_if
from breachlens.schema import BreachProfile


@pytest.fixture
def base_profile() -> BreachProfile:
    return BreachProfile(
        records_exposed=300, detection_time=200, response_time=90, security_score=40
    )


@pytest.mark.unit
def test_apply_changes_is_immutable(base_profile: BreachProfile) -> None:
    updated = apply_changes(base_profile, {"security_score": 80})
    assert updated.security_score == 80
    assert base_profile.security_score == 40  # original untouched


@pytest.mark.unit
def test_apply_changes_revalidates(base_profile: BreachProfile) -> None:
    with pytest.raises(ValueError):
        apply_changes(base_profile, {"security_score": 999})


@pytest.mark.integration
def test_stronger_security_reduces_cost(model: BreachModel, base_profile: BreachProfile) -> None:
    scenario = what_if(model, base_profile, {"security_score": 90})
    assert scenario.savings > 0
    assert scenario.savings_pct > 0


@pytest.mark.integration
def test_faster_detection_reduces_cost(model: BreachModel, base_profile: BreachProfile) -> None:
    scenario = what_if(model, base_profile, {"detection_time": 30})
    assert scenario.adjusted.expected_cost < scenario.baseline.expected_cost


@pytest.mark.unit
def test_sweep_returns_full_range(model: BreachModel, base_profile: BreachProfile) -> None:
    sweep = sweep_feature(model, base_profile, "records_exposed", n=15)
    assert len(sweep) == 15
    assert list(sweep.columns) == ["value", "expected", "lower", "upper"]
    assert (sweep["upper"] >= sweep["lower"]).all()


@pytest.mark.unit
def test_sweep_rejects_unknown_feature(model: BreachModel, base_profile: BreachProfile) -> None:
    with pytest.raises(ValueError):
        sweep_feature(model, base_profile, "not_a_feature")


@pytest.mark.unit
def test_roi_computes_net_benefit(model: BreachModel, base_profile: BreachProfile) -> None:
    scenario = what_if(model, base_profile, {"security_score": 90})
    result = roi(scenario, investment_cost=0.5, breach_probability=0.5)
    assert result["expected_savings"] == pytest.approx(scenario.savings * 0.5)
    assert result["net_benefit"] == pytest.approx(result["expected_savings"] - 0.5)


@pytest.mark.unit
def test_roi_rejects_bad_probability(model: BreachModel, base_profile: BreachProfile) -> None:
    scenario = what_if(model, base_profile, {"security_score": 90})
    with pytest.raises(ValueError):
        roi(scenario, investment_cost=1.0, breach_probability=2.0)


@pytest.mark.unit
def test_predict_profile_interval_brackets(model: BreachModel, base_profile: BreachProfile) -> None:
    result = predict_profile(model, base_profile, confidence=0.9)
    assert result.lower <= result.expected_cost <= result.upper
    assert result.model_name == model.name
