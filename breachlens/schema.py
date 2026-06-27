"""Input/output schemas and validation for BreachLens.

A single source of truth for what a valid breach profile looks like, used by the
predictor, the CLI, the FastAPI service and the Streamlit app alike.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .config import FEATURE_BY_NAME, FEATURE_NAMES


class BreachProfile(BaseModel):
    """A validated set of breach/security factors to be scored.

    Values are range-checked against :data:`breachlens.config.FEATURES`. Out-of-range
    inputs raise a ``ValidationError`` rather than silently producing a nonsense
    prediction.
    """

    records_exposed: float = Field(..., description="Records leaked, in thousands.")
    detection_time: float = Field(..., description="Days to detect the breach.")
    response_time: float = Field(..., description="Days to contain the breach.")
    security_score: float = Field(..., description="Security maturity (0-100).")

    @field_validator("records_exposed", "detection_time", "response_time", "security_score")
    @classmethod
    def _within_supported_range(cls, value: float, info: Any) -> float:
        spec = FEATURE_BY_NAME[info.field_name]
        if not spec.min <= value <= spec.max:
            raise ValueError(
                f"{spec.label} ({spec.name}) must be between {spec.min} and "
                f"{spec.max} {spec.unit}; got {value}."
            )
        return value

    def to_features(self) -> dict[str, float]:
        """Return an ordered feature dict matching the training column order."""
        return {name: getattr(self, name) for name in FEATURE_NAMES}

    @classmethod
    def midpoint(cls) -> BreachProfile:
        """A neutral profile using each feature's default — handy for demos/tests."""
        return cls(**{name: FEATURE_BY_NAME[name].default for name in FEATURE_NAMES})


class PredictionResult(BaseModel):
    """The output of a cost prediction with an uncertainty band."""

    expected_cost: float = Field(..., description="Point estimate in native units (crore).")
    lower: float = Field(..., description="Lower bound of the prediction interval.")
    upper: float = Field(..., description="Upper bound of the prediction interval.")
    confidence: float = Field(..., description="Interval confidence level, e.g. 0.9.")
    model_name: str = Field(..., description="Algorithm that produced the estimate.")

    @property
    def band_width(self) -> float:
        return self.upper - self.lower
