"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from breachlens import BreachLens, Industry, Jurisdiction, OrgProfile
from breachlens.models import BreachModel, train


@pytest.fixture(scope="session")
def model() -> BreachModel:
    """An ML model (optional second opinion), trained once per session."""
    return train(seed=2)


@pytest.fixture
def org() -> OrgProfile:
    return OrgProfile(
        records_exposed=300,
        detection_time=220,
        response_time=95,
        security_score=45,
        industry=Industry.FINANCIAL,
        jurisdiction=Jurisdiction.IN,
        regulatory_severity=0.35,
    )


@pytest.fixture
def lens() -> BreachLens:
    return BreachLens()
