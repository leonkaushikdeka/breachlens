"""Dataset loading and validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import FEATURE_NAMES, TARGET

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = _PACKAGE_ROOT / "data" / "cyber_breach.csv"

REQUIRED_COLUMNS = [*FEATURE_NAMES, TARGET]


class DatasetError(ValueError):
    """Raised when a dataset is missing columns or contains invalid values."""


def load_dataset(path: str | Path | None = None) -> pd.DataFrame:
    """Load and validate the breach dataset.

    Args:
        path: CSV path. Defaults to the bundled ``data/cyber_breach.csv``.

    Returns:
        A validated DataFrame with exactly the required columns.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        DatasetError: If required columns are missing or values are unusable.
    """
    csv_path = Path(path) if path is not None else DEFAULT_DATASET
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}.")

    df = pd.read_csv(csv_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DatasetError(f"Dataset is missing required columns: {missing}.")

    df = df[REQUIRED_COLUMNS].copy()
    if df.isnull().any().any():
        raise DatasetError("Dataset contains missing values; clean it before training.")
    if (df[TARGET] <= 0).any():
        raise DatasetError("breach_cost must be positive for every record.")

    return df


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split a validated frame into the feature matrix X and target vector y."""
    return df[FEATURE_NAMES].copy(), df[TARGET].copy()
