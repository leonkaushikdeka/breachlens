"""Tests for the command-line interface."""

from __future__ import annotations

import json

import pytest

from breachlens.cli import main


@pytest.mark.unit
def test_predict_json(capsys) -> None:
    code = main(
        [
            "predict",
            "--records",
            "300",
            "--detection",
            "200",
            "--response",
            "90",
            "--security",
            "40",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["expected_cost"] > 0
    assert payload["lower"] <= payload["expected_cost"] <= payload["upper"]


@pytest.mark.unit
def test_benchmark_runs(capsys) -> None:
    assert main(["benchmark"]) == 0
    assert "Model benchmark" in capsys.readouterr().out


@pytest.mark.unit
def test_whatif_reports_savings(capsys) -> None:
    code = main(
        [
            "whatif",
            "--records",
            "300",
            "--detection",
            "200",
            "--response",
            "90",
            "--security",
            "40",
            "--improve",
            "security_score=90",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["savings"] > 0


@pytest.mark.unit
def test_whatif_requires_improvement() -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "whatif",
                "--records",
                "300",
                "--detection",
                "200",
                "--response",
                "90",
                "--security",
                "40",
            ]
        )


@pytest.mark.unit
def test_generate_data_writes_csv(tmp_path, capsys) -> None:
    out = tmp_path / "synth.csv"
    code = main(["generate-data", "--n", "30", "--seed", "1", "--out", str(out)])
    assert code == 0
    assert out.exists()
    assert "30" in capsys.readouterr().out


@pytest.mark.unit
def test_unknown_improve_feature_rejected() -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "whatif",
                "--records",
                "300",
                "--detection",
                "200",
                "--response",
                "90",
                "--security",
                "40",
                "--improve",
                "telepathy=1",
            ]
        )
