"""Tests for the Monte Carlo simulation."""

from __future__ import annotations

import numpy as np
import pytest

from breachlens import OrgProfile
from breachlens.montecarlo import simulate


@pytest.mark.unit
def test_percentiles_are_ordered(org: OrgProfile) -> None:
    mc = simulate(org, n=5000)
    assert mc.p50 <= mc.p90 <= mc.p95
    assert mc.mean > 0


@pytest.mark.unit
def test_reproducible_with_seed(org: OrgProfile) -> None:
    a = simulate(org, n=3000, seed=11)
    b = simulate(org, n=3000, seed=11)
    assert np.array_equal(a.samples, b.samples)


@pytest.mark.unit
def test_exceedance_curve_is_monotonic(org: OrgProfile) -> None:
    mc = simulate(org, n=4000)
    losses, probs = mc.exceedance_curve()
    assert losses[0] < losses[-1]
    assert np.all(np.diff(probs) <= 1e-9)  # non-increasing
    assert probs[0] == pytest.approx(probs.max())


@pytest.mark.unit
def test_controls_reduce_expected_cost(org: OrgProfile) -> None:
    base = simulate(org, n=4000, seed=3)
    improved = simulate(org, ["security_ai_automation", "ir_team_and_plan"], n=4000, seed=3)
    assert improved.mean < base.mean


@pytest.mark.unit
def test_rejects_non_positive_n(org: OrgProfile) -> None:
    with pytest.raises(ValueError):
        simulate(org, n=0)
