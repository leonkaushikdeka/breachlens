"""Input/output schemas and validation for BreachLens.

A single source of truth for what a valid breach profile looks like, used by the
predictor, the CLI, the FastAPI service and the Streamlit app alike.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .benchmarks import Industry, Jurisdiction
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


class OrgProfile(BreachProfile):
    """A breach scenario for the benchmark-driven estimator.

    Extends the four core breach factors with the context the published benchmarks
    are keyed on: industry, regulatory jurisdiction, and an estimate of regulatory
    severity. Defaults keep it usable from a single line.
    """

    industry: Industry = Industry.SERVICES
    jurisdiction: Jurisdiction = Jurisdiction.IN
    regulatory_severity: float = Field(
        0.35, ge=0.0, le=1.0, description="0-1 estimate of regulatory severity."
    )
    turnover_million: float | None = Field(
        None, description="Global annual turnover for the GDPR 4%-of-turnover branch."
    )

    @property
    def records_actual(self) -> float:
        """Absolute record count (input is in thousands)."""
        return self.records_exposed * 1000.0

    @property
    def lifecycle_days(self) -> float:
        """Total breach lifecycle: time to detect plus time to contain."""
        return self.detection_time + self.response_time


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
