"""Tests for the command-line interface."""

from __future__ import annotations

import json

import pytest

from breachlens.cli import main

_PROFILE = ["--records", "300", "--detection", "220", "--response", "95", "--security", "45"]


@pytest.mark.unit
def test_estimate_json(capsys) -> None:
    assert main(["estimate", *_PROFILE, "--industry", "financial", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == pytest.approx(payload["operational"] + payload["regulatory"])


@pytest.mark.unit
def test_simulate_json(capsys) -> None:
    assert main(["simulate", *_PROFILE, "--n", "2000", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["p50"] <= payload["p90"] <= payload["p95"]


@pytest.mark.unit
def test_invest_reports_savings(capsys) -> None:
    code = main(
        [
            "invest",
            *_PROFILE,
            "--controls",
            "security_ai_automation,encryption",
            "--investment",
            "2",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["gross_savings"] > 0


@pytest.mark.unit
def test_invest_rejects_unknown_control() -> None:
    with pytest.raises(SystemExit):
        main(["invest", *_PROFILE, "--controls", "telepathy", "--investment", "1"])


@pytest.mark.unit
def test_penalty_json(capsys) -> None:
    assert main(["penalty", "--records", "300", "--jurisdiction", "IN", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["expected"] <= payload["statutory_max"]


@pytest.mark.unit
def test_controls_lists_catalogue(capsys) -> None:
    assert main(["controls"]) == 0
    assert "security_ai_automation" in capsys.readouterr().out
