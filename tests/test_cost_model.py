"""Tests for the benchmark-driven cost estimator."""

from __future__ import annotations

import pytest

from breachlens import Industry, Jurisdiction, OrgProfile
from breachlens.cost_model import estimate_cost, lifecycle_multiplier, maturity_multiplier


@pytest.mark.unit
def test_total_is_operational_plus_regulatory(org: OrgProfile) -> None:
    c = estimate_cost(org)
    assert c.total == pytest.approx(c.operational + c.regulatory)
    assert c.operational == pytest.approx(c.recovery + c.lost_business)


@pytest.mark.unit
def test_stronger_security_lowers_cost(org: OrgProfile) -> None:
    weak = estimate_cost(org.model_copy(update={"security_score": 30}))
    strong = estimate_cost(org.model_copy(update={"security_score": 90}))
    assert strong.operational < weak.operational


@pytest.mark.unit
def test_slower_lifecycle_raises_cost(org: OrgProfile) -> None:
    fast = estimate_cost(org.model_copy(update={"detection_time": 20, "response_time": 10}))
    slow = estimate_cost(org.model_copy(update={"detection_time": 290, "response_time": 120}))
    assert slow.operational > fast.operational


@pytest.mark.unit
def test_more_records_raises_cost(org: OrgProfile) -> None:
    small = estimate_cost(org.model_copy(update={"records_exposed": 20}))
    big = estimate_cost(org.model_copy(update={"records_exposed": 480}))
    assert big.total > small.total


@pytest.mark.unit
def test_healthcare_costs_more_than_public(org: OrgProfile) -> None:
    health = estimate_cost(org.model_copy(update={"industry": Industry.HEALTHCARE}))
    public = estimate_cost(org.model_copy(update={"industry": Industry.PUBLIC}))
    assert health.operational > public.operational


@pytest.mark.unit
def test_controls_reduce_cost(org: OrgProfile) -> None:
    base = estimate_cost(org)
    improved = estimate_cost(org, controls=["security_ai_automation", "encryption"])
    assert improved.operational < base.operational


@pytest.mark.unit
def test_jurisdiction_changes_currency(org: OrgProfile) -> None:
    inr = estimate_cost(org)
    eur = estimate_cost(org.model_copy(update={"jurisdiction": Jurisdiction.EU}))
    assert inr.benchmark.currency_code == "INR"
    assert eur.benchmark.currency_code == "EUR"


@pytest.mark.unit
def test_lifecycle_multiplier_pivots_at_200() -> None:
    assert lifecycle_multiplier(200) == pytest.approx(1.0)
    assert lifecycle_multiplier(400) > 1.0
    assert lifecycle_multiplier(20) < 1.0


@pytest.mark.unit
def test_maturity_multiplier_is_bounded() -> None:
    assert maturity_multiplier(0) == pytest.approx(1.30)
    assert maturity_multiplier(50) == pytest.approx(1.0)
    assert 0.70 <= maturity_multiplier(100) <= 0.71
