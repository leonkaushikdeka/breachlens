"""Tests for the cited benchmark knowledge base."""

from __future__ import annotations

import pytest

from breachlens.benchmarks import (
    INDUSTRY_MULTIPLIERS,
    JURISDICTIONS,
    Industry,
    Jurisdiction,
    jurisdiction,
)


@pytest.mark.unit
def test_all_jurisdictions_present() -> None:
    assert set(JURISDICTIONS) == set(Jurisdiction)
    for jb in JURISDICTIONS.values():
        assert jb.avg_total_low < jb.avg_total < jb.avg_total_high
        assert jb.unit_value > 0


@pytest.mark.unit
def test_healthcare_is_costliest_industry() -> None:
    top = max(INDUSTRY_MULTIPLIERS, key=INDUSTRY_MULTIPLIERS.get)
    assert top is Industry.HEALTHCARE
    assert INDUSTRY_MULTIPLIERS[Industry.PUBLIC] < INDUSTRY_MULTIPLIERS[Industry.FINANCIAL]


@pytest.mark.unit
def test_jurisdiction_lookup_accepts_str_and_enum() -> None:
    assert jurisdiction("IN").currency_code == "INR"
    assert jurisdiction(Jurisdiction.EU).currency_symbol == "€"


@pytest.mark.unit
def test_format_includes_unit() -> None:
    assert "crore" in jurisdiction("IN").format(12.5)
    assert jurisdiction("US").format(4.0).startswith("$")
