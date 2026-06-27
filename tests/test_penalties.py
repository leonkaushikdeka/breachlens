"""Tests for the regulatory penalty models."""

from __future__ import annotations

import pytest

from breachlens.benchmarks import Jurisdiction
from breachlens.penalties import DPDP_MAX_CRORE, regulatory_penalty


@pytest.mark.unit
def test_dpdp_capped_at_statutory_max() -> None:
    p = regulatory_penalty(Jurisdiction.IN, 5_000_000, severity=1.0)
    assert p.statutory_max == DPDP_MAX_CRORE
    assert p.expected <= DPDP_MAX_CRORE
    assert "DPDP" in p.regime


@pytest.mark.unit
def test_bigger_breach_means_more_exposure() -> None:
    small = regulatory_penalty(Jurisdiction.IN, 10_000, severity=0.4).expected
    large = regulatory_penalty(Jurisdiction.IN, 400_000, severity=0.4).expected
    assert large > small


@pytest.mark.unit
def test_severity_scales_penalty_linearly() -> None:
    low = regulatory_penalty(Jurisdiction.IN, 200_000, severity=0.2).expected
    high = regulatory_penalty(Jurisdiction.IN, 200_000, severity=0.4).expected
    assert high == pytest.approx(2 * low, rel=1e-6)


@pytest.mark.unit
def test_gdpr_turnover_branch_raises_cap() -> None:
    base = regulatory_penalty(Jurisdiction.EU, 200_000, severity=0.5)
    big = regulatory_penalty(Jurisdiction.EU, 200_000, severity=0.5, turnover_million=2000)
    assert big.statutory_max > base.statutory_max  # 4% of €2bn = €80M > €20M floor


@pytest.mark.unit
def test_us_is_per_record() -> None:
    p = regulatory_penalty(Jurisdiction.US, 100_000, severity=1.0)
    assert p.expected == pytest.approx(90 * 100_000 / 1e6)


@pytest.mark.unit
def test_severity_clamped() -> None:
    p = regulatory_penalty(Jurisdiction.IN, 100_000, severity=5.0)
    capped = regulatory_penalty(Jurisdiction.IN, 100_000, severity=1.0)
    assert p.expected == pytest.approx(capped.expected)
