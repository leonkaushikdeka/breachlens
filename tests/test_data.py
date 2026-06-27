"""Tests for dataset loading and validation."""

from __future__ import annotations

import pandas as pd
import pytest

from breachlens.config import FEATURE_NAMES, TARGET
from breachlens.data import DatasetError, load_dataset, split_features_target


@pytest.mark.unit
def test_load_dataset_has_required_columns() -> None:
    df = load_dataset()
    assert list(df.columns) == [*FEATURE_NAMES, TARGET]
    assert len(df) == 200


@pytest.mark.unit
def test_load_dataset_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_dataset("does/not/exist.csv")


@pytest.mark.unit
def test_load_dataset_rejects_missing_columns(tmp_path) -> None:
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"records_exposed": [1], "breach_cost": [2.0]}).to_csv(bad, index=False)
    with pytest.raises(DatasetError):
        load_dataset(bad)


@pytest.mark.unit
def test_load_dataset_rejects_nonpositive_cost(tmp_path) -> None:
    bad = tmp_path / "bad.csv"
    row = dict.fromkeys(FEATURE_NAMES, 50)
    row[TARGET] = 0.0
    pd.DataFrame([row]).to_csv(bad, index=False)
    with pytest.raises(DatasetError):
        load_dataset(bad)


@pytest.mark.unit
def test_split_features_target() -> None:
    X, y = split_features_target(load_dataset())
    assert list(X.columns) == FEATURE_NAMES
    assert y.name == TARGET
    assert len(X) == len(y)
