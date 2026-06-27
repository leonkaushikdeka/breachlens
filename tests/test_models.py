"""Tests for benchmarking, training and persistence."""

from __future__ import annotations

import pandas as pd
import pytest

from breachlens.data import load_dataset, split_features_target
from breachlens.models import (
    MODEL_ZOO,
    BreachModel,
    benchmark_models,
    load_model,
    save_model,
    train,
)


@pytest.mark.unit
def test_benchmark_ranks_all_models() -> None:
    X, y = split_features_target(load_dataset())
    board = benchmark_models(X, y)
    assert set(board["model"]) == set(MODEL_ZOO)
    # Sorted by R² descending.
    assert board["r2"].is_monotonic_decreasing


@pytest.mark.integration
def test_train_produces_strong_linear_fit(model: BreachModel) -> None:
    # The synthetic relationship is linear, so R² should be high.
    assert model.metrics["r2"] > 0.9
    assert model.metrics["mae"] > 0
    assert model.name in MODEL_ZOO


@pytest.mark.unit
def test_train_respects_forced_model() -> None:
    m = train(model_name="Random Forest", seed=2)
    assert m.name == "Random Forest"


@pytest.mark.unit
def test_train_rejects_unknown_model() -> None:
    with pytest.raises(ValueError):
        train(model_name="Telepathy", seed=2)


@pytest.mark.unit
def test_predict_interval_brackets_point(model: BreachModel) -> None:
    X = pd.DataFrame(
        [{"records_exposed": 300, "detection_time": 200, "response_time": 90, "security_score": 40}]
    )
    point, lower, upper = model.predict_interval(X, confidence=0.9)
    assert lower[0] <= point[0] <= upper[0]
    assert lower[0] >= 0


@pytest.mark.integration
def test_conformal_interval_has_reasonable_coverage(model: BreachModel) -> None:
    df = load_dataset()
    X, y = split_features_target(df)
    _, lower, upper = model.predict_interval(X, confidence=0.9)
    covered = ((y.to_numpy() >= lower) & (y.to_numpy() <= upper)).mean()
    # In-sample coverage should comfortably exceed the nominal level.
    assert covered >= 0.85


@pytest.mark.unit
def test_save_and_load_roundtrip(model: BreachModel, tmp_path) -> None:
    path = tmp_path / "m.joblib"
    save_model(model, path)
    loaded = load_model(path)
    assert loaded.name == model.name
    assert loaded.feature_names == model.feature_names


@pytest.mark.unit
def test_load_missing_model_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_model(tmp_path / "nope.joblib")
