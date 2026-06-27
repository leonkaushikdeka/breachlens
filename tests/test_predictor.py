"""Tests for the BreachLens facade and schema validation."""

from __future__ import annotations

import pytest

from breachlens import BreachLens, Industry, Jurisdiction, OrgProfile


@pytest.mark.unit
def test_profile_validation_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        OrgProfile(records_exposed=5, detection_time=200, response_time=90, security_score=40)


@pytest.mark.unit
def test_org_profile_derived_properties() -> None:
    org = OrgProfile(records_exposed=300, detection_time=200, response_time=90, security_score=40)
    assert org.records_actual == 300_000
    assert org.lifecycle_days == 290


@pytest.mark.unit
def test_estimate_accepts_dict(lens: BreachLens) -> None:
    c = lens.estimate(
        {"records_exposed": 300, "detection_time": 200, "response_time": 90, "security_score": 40}
    )
    assert c.total > 0


@pytest.mark.unit
def test_simulate_and_money(lens: BreachLens, org: OrgProfile) -> None:
    mc = lens.simulate(org, n=2000)
    assert mc.p90 >= mc.p50
    assert lens.money(org, 12.5).startswith("₹")


@pytest.mark.unit
def test_investment_case_via_facade(lens: BreachLens, org: OrgProfile) -> None:
    case = lens.investment_case(org, ["encryption"], investment=1.0)
    assert case.improved.total < case.baseline.total


@pytest.mark.unit
def test_predict_ml_requires_model(lens: BreachLens, org: OrgProfile) -> None:
    with pytest.raises(RuntimeError):
        lens.predict_ml(org)


@pytest.mark.integration
def test_with_ml_attaches_model(org: OrgProfile) -> None:
    lens = BreachLens.with_ml(seed=2)
    result = lens.predict_ml(org)
    assert result.lower <= result.expected_cost <= result.upper


@pytest.mark.unit
def test_eu_profile_formats_in_euros(lens: BreachLens) -> None:
    org = OrgProfile(
        records_exposed=200,
        detection_time=150,
        response_time=60,
        security_score=65,
        industry=Industry.FINANCIAL,
        jurisdiction=Jurisdiction.EU,
    )
    assert lens.money(org, 4.0).startswith("€")
