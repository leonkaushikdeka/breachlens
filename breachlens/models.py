"""Model zoo, benchmarking, training and persistence.

BreachLens does not assume linear regression is best — it benchmarks several
algorithms with cross-validation, selects the strongest by R², then fits a final
model with a conformal calibration set for honest prediction intervals.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import FEATURE_NAMES
from .data import load_dataset, split_features_target
from .intervals import ConformalCalibrator

ModelFactory = Callable[[int], Pipeline]


def _linear(seed: int) -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("model", LinearRegression())])


def _ridge(seed: int) -> Pipeline:
    return Pipeline(
        [("scale", StandardScaler()), ("model", RidgeCV(alphas=np.logspace(-3, 3, 25)))]
    )


def _random_forest(seed: int) -> Pipeline:
    return Pipeline(
        [("model", RandomForestRegressor(n_estimators=300, random_state=seed, n_jobs=-1))]
    )


def _gradient_boosting(seed: int) -> Pipeline:
    return Pipeline([("model", GradientBoostingRegressor(random_state=seed))])


MODEL_ZOO: dict[str, ModelFactory] = {
    "Linear Regression": _linear,
    "Ridge Regression": _ridge,
    "Random Forest": _random_forest,
    "Gradient Boosting": _gradient_boosting,
}


def benchmark_models(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    cv: int = 5,
    seed: int = 2,
) -> pd.DataFrame:
    """Cross-validate every model in the zoo and return a ranked scoreboard.

    Returns a DataFrame sorted by R² (desc) with columns:
    ``model, r2, r2_std, mae, mae_std``.
    """
    kfold = KFold(n_splits=cv, shuffle=True, random_state=seed)
    rows = []
    for name, factory in MODEL_ZOO.items():
        pipe = factory(seed)
        r2 = cross_val_score(pipe, X, y, cv=kfold, scoring="r2")
        mae = -cross_val_score(pipe, X, y, cv=kfold, scoring="neg_mean_absolute_error")
        rows.append(
            {
                "model": name,
                "r2": float(r2.mean()),
                "r2_std": float(r2.std()),
                "mae": float(mae.mean()),
                "mae_std": float(mae.std()),
            }
        )
    scoreboard = pd.DataFrame(rows).sort_values("r2", ascending=False).reset_index(drop=True)
    return scoreboard


@dataclass
class BreachModel:
    """A trained, calibrated breach-cost estimator with uncertainty.

    Bundles everything needed to score a new breach and explain the result:
    the fitted pipeline, the conformal calibrator, the headline metrics and
    provenance metadata.
    """

    pipeline: Pipeline
    name: str
    calibrator: ConformalCalibrator
    feature_names: list[str]
    metrics: dict[str, float]
    scoreboard: pd.DataFrame
    n_train: int
    confidence: float = 0.9
    trained_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def predict_point(self, X: pd.DataFrame) -> np.ndarray:
        """Point estimate(s) in native units (₹ crore)."""
        ordered = X[self.feature_names]
        return self.pipeline.predict(ordered)

    def predict_interval(
        self, X: pd.DataFrame, confidence: float | None = None
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return ``(point, lower, upper)`` arrays for the rows of ``X``."""
        conf = self.confidence if confidence is None else confidence
        point = self.predict_point(X)
        half = self.calibrator.half_width(conf)
        lower = np.clip(point - half, 0.0, None)
        upper = point + half
        return point, lower, upper


def train(
    data: pd.DataFrame | None = None,
    *,
    confidence: float = 0.9,
    cv: int = 5,
    seed: int = 2,
    model_name: str | None = None,
) -> BreachModel:
    """Benchmark, select and fit the final calibrated breach-cost model.

    Splits data into train / calibration / test (≈68/12/20). The best model (by
    cross-validated R², unless ``model_name`` forces one) is fit on the train split,
    conformal-calibrated on the calibration split, and evaluated on the held-out test
    split for honest headline metrics.
    """
    df = load_dataset() if data is None else data
    X, y = split_features_target(df)

    scoreboard = benchmark_models(X, y, cv=cv, seed=seed)
    chosen = model_name or str(scoreboard.iloc[0]["model"])
    if chosen not in MODEL_ZOO:
        raise ValueError(f"Unknown model '{chosen}'. Choose from {list(MODEL_ZOO)}.")

    X_rest, X_test, y_rest, y_test = train_test_split(X, y, test_size=0.2, random_state=seed)
    X_train, X_cal, y_train, y_cal = train_test_split(
        X_rest, y_rest, test_size=0.15, random_state=seed
    )

    pipeline = MODEL_ZOO[chosen](seed)
    pipeline.fit(X_train, y_train)

    calibrator = ConformalCalibrator.from_predictions(y_cal.to_numpy(), pipeline.predict(X_cal))

    test_pred = pipeline.predict(X_test)
    metrics = {
        "r2": float(r2_score(y_test, test_pred)),
        "mae": float(mean_absolute_error(y_test, test_pred)),
        "rmse": float(np.sqrt(np.mean((y_test.to_numpy() - test_pred) ** 2))),
        "cv_r2": float(scoreboard.loc[scoreboard["model"] == chosen, "r2"].iloc[0]),
        "interval_half_width": calibrator.half_width(confidence),
    }

    return BreachModel(
        pipeline=pipeline,
        name=chosen,
        calibrator=calibrator,
        feature_names=list(FEATURE_NAMES),
        metrics=metrics,
        scoreboard=scoreboard,
        n_train=len(X_train),
        confidence=confidence,
    )


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "breach_model.joblib"


def save_model(model: BreachModel, path: str | Path | None = None) -> Path:
    """Persist a trained model to disk with joblib."""
    target = Path(path) if path is not None else DEFAULT_MODEL_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_model(path: str | Path | None = None) -> BreachModel:
    """Load a persisted model from disk."""
    source = Path(path) if path is not None else DEFAULT_MODEL_PATH
    if not source.exists():
        raise FileNotFoundError(f"No saved model at {source}. Run `breachlens train` first.")
    return joblib.load(source)
