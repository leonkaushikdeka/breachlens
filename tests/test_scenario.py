"""Tests for the what-if / investment-ROI engine."""

from __future__ import annotations

import pytest

from breachlens import OrgProfile
from breachlens.scenario import (
    annual_breach_probability,
    apply_changes,
    build_investment_case,
    sweep,
)


@pytest.mark.unit
def test_apply_changes_is_immutable(org: OrgProfile) -> None:
    updated = apply_changes(org, {"security_score": 80})
    assert updated.security_score == 80
    assert org.security_score == 45


@pytest.mark.unit
def test_apply_changes_revalidates(org: OrgProfile) -> None:
    with pytest.raises(ValueError):
        apply_changes(org, {"security_score": 999})


@pytest.mark.unit
def test_investment_case_reports_savings_and_roi(org: OrgProfile) -> None:
    case = build_investment_case(
        org, ["security_ai_automation", "ir_team_and_plan"], investment=2.0
    )
    assert case.gross_savings > 0
    assert case.expected_savings == pytest.approx(case.gross_savings * case.breach_probability)
    assert case.net_benefit == pytest.approx(case.expected_savings - 2.0)
    assert case.payback_years > 0


@pytest.mark.unit
def test_zero_investment_is_infinite_roi(org: OrgProfile) -> None:
    case = build_investment_case(org, ["encryption"], investment=0.0)
    assert case.roi == float("inf")


@pytest.mark.unit
def test_annual_probability_in_range(org: OrgProfile) -> None:
    p = annual_breach_probability(org)
    assert 0.0 < p < 1.0


@pytest.mark.unit
def test_sweep_returns_full_range(org: OrgProfile) -> None:
    df = sweep(org, "security_score", n=20)
    assert len(df) == 20
    assert {"value", "operational", "regulatory", "total"} <= set(df.columns)


@pytest.mark.unit
def test_sweep_rejects_unknown_feature(org: OrgProfile) -> None:
    with pytest.raises(ValueError):
        sweep(org, "industry")
