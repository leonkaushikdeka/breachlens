"""Tests for the security control catalogue."""

from __future__ import annotations

import pytest

from breachlens.controls import (
    CONTROL_CATALOG,
    cost_reduction_factor,
    frequency_reduction_factor,
)


@pytest.mark.unit
def test_empty_controls_have_no_effect() -> None:
    assert cost_reduction_factor([]) == 1.0
    assert frequency_reduction_factor([]) == 1.0


@pytest.mark.unit
def test_controls_compound_multiplicatively() -> None:
    one = cost_reduction_factor(["encryption"])
    two = cost_reduction_factor(["encryption", "security_ai_automation"])
    assert two < one < 1.0


@pytest.mark.unit
def test_unknown_control_ignored() -> None:
    assert cost_reduction_factor(["nonexistent"]) == 1.0


@pytest.mark.unit
def test_every_control_has_a_positive_reduction() -> None:
    for control in CONTROL_CATALOG.values():
        assert 0 < control.cost_reduction < 1
        assert 0 <= control.frequency_reduction < 1
