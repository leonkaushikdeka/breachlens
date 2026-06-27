"""High-level facade: the one object apps, the API and the CLI talk to."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import RegionConfig, get_region
from .data import load_dataset, split_features_target
from .explain import global_importance, local_contributions
from .models import BreachModel, load_model, save_model, train
from .scenario import ScenarioResult, predict_profile, sweep_feature, what_if
from .schema import BreachProfile, PredictionResult


class BreachLens:
    """A trained breach-cost estimator with prediction, explanation and what-if.

    Construct it the easy way with :meth:`load_or_train`, which loads a persisted
    model if one exists and otherwise trains a fresh one in memory — so a clean
    clone (or a free Streamlit deploy) works with zero setup steps.
    """

    def __init__(self, model: BreachModel, region: RegionConfig | None = None) -> None:
        self.model = model
        self.region = region or get_region()

    @classmethod
    def load_or_train(
        cls,
        path: str | Path | None = None,
        *,
        region_code: str | None = None,
    ) -> BreachLens:
        region = get_region(region_code)
        try:
            model = load_model(path)
        except FileNotFoundError:
            model = train()
        return cls(model=model, region=region)

    @classmethod
    def train_fresh(cls, *, region_code: str | None = None, **train_kwargs) -> BreachLens:
        return cls(model=train(**train_kwargs), region=get_region(region_code))

    def save(self, path: str | Path | None = None) -> Path:
        return save_model(self.model, path)

    # --- coercion -------------------------------------------------------------
    @staticmethod
    def _coerce(profile: BreachProfile | dict[str, float]) -> BreachProfile:
        return profile if isinstance(profile, BreachProfile) else BreachProfile(**profile)

    # --- core operations ------------------------------------------------------
    def predict(
        self,
        profile: BreachProfile | dict[str, float],
        confidence: float | None = None,
    ) -> PredictionResult:
        return predict_profile(self.model, self._coerce(profile), confidence)

    def explain(self, profile: BreachProfile | dict[str, float]) -> pd.DataFrame:
        return local_contributions(self.model, self._coerce(profile))

    def importance(self) -> pd.DataFrame:
        X, y = split_features_target(load_dataset())
        return global_importance(self.model, X, y)

    def what_if(
        self,
        profile: BreachProfile | dict[str, float],
        changes: dict[str, float],
        confidence: float | None = None,
    ) -> ScenarioResult:
        return what_if(self.model, self._coerce(profile), changes, confidence)

    def sweep(
        self,
        profile: BreachProfile | dict[str, float],
        feature: str,
        *,
        n: int = 25,
        confidence: float | None = None,
    ) -> pd.DataFrame:
        return sweep_feature(self.model, self._coerce(profile), feature, n=n, confidence=confidence)

    # --- presentation ---------------------------------------------------------
    def format(self, native_value: float, decimals: int = 2) -> str:
        return self.region.format(native_value, decimals)
