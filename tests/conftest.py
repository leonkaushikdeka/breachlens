"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from breachlens import BreachLens
from breachlens.models import BreachModel, train


@pytest.fixture(scope="session")
def model() -> BreachModel:
    """A trained model, built once per test session (training is fast)."""
    return train(seed=2)


@pytest.fixture(scope="session")
def lens(model: BreachModel) -> BreachLens:
    return BreachLens(model=model)
