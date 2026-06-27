"""Tests for board-ready report generation."""

from __future__ import annotations

import pytest

from breachlens import OrgProfile
from breachlens.report import build_html, build_markdown


@pytest.mark.unit
def test_markdown_has_core_sections(org: OrgProfile) -> None:
    md = build_markdown(org, n=2000)
    for heading in [
        "Executive summary",
        "Cost breakdown",
        "Risk distribution",
        "Recommended investments",
        "Methodology",
    ]:
        assert heading in md
    assert "₹" in md


@pytest.mark.unit
def test_markdown_total_matches_estimate(org: OrgProfile) -> None:
    from breachlens.cost_model import estimate_cost

    total = estimate_cost(org).total
    assert f"{total:,.2f}" in build_markdown(org, n=2000)


@pytest.mark.unit
def test_html_is_self_contained(org: OrgProfile) -> None:
    html = build_html(org, n=2000)
    assert html.startswith("<!doctype html>")
    assert "<table>" in html and "</table>" in html
    assert "<th>" in html  # header row detected
    assert "<script" not in html  # no external/JS dependencies
