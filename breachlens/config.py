"""Domain configuration for BreachLens.

Defines the feature schema (the measurable security factors that drive breach
cost) and region/currency presets. The machine-learning model is trained in the
dataset's native unit (Indian Rupee *crore*); regions only affect how a cost is
*displayed*, so the same trained model serves every locale.
"""

from __future__ import annotations

from dataclasses import dataclass

TARGET: str = "breach_cost"


@dataclass(frozen=True)
class FeatureSpec:
    """Metadata for a single model input feature.

    Attributes:
        name: Column name used in the dataset and model.
        label: Human-readable label for UI / reports.
        unit: Unit the value is measured in.
        min: Minimum realistic value (used for validation and UI sliders).
        max: Maximum realistic value.
        default: A sensible mid-range default for forms.
        higher_increases_cost: True if larger values are expected to raise the
            breach cost (records, detection time, response time); False if larger
            values are expected to lower it (security score).
        help: Short explanation surfaced as tooltip / docs.
    """

    name: str
    label: str
    unit: str
    min: float
    max: float
    default: float
    higher_increases_cost: bool
    help: str


FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        name="records_exposed",
        label="Records exposed",
        unit="thousands",
        min=10,
        max=500,
        default=250,
        higher_increases_cost=True,
        help="Number of customer/employee records leaked, in thousands.",
    ),
    FeatureSpec(
        name="detection_time",
        label="Detection time",
        unit="days",
        min=10,
        max=295,
        default=160,
        higher_increases_cost=True,
        help="Days taken to detect the breach (the 'dwell time'). "
        "Industry data shows slower detection sharply raises cost.",
    ),
    FeatureSpec(
        name="response_time",
        label="Containment time",
        unit="days",
        min=6,
        max=120,
        default=58,
        higher_increases_cost=True,
        help="Days taken to contain/remediate the breach once detected.",
    ),
    FeatureSpec(
        name="security_score",
        label="Security maturity score",
        unit="0-100",
        min=20,
        max=95,
        default=60,
        higher_increases_cost=False,
        help="Security posture maturity (higher is stronger). "
        "Captures controls, training, MFA, encryption, IR readiness.",
    ),
)

FEATURE_NAMES: list[str] = [f.name for f in FEATURES]
FEATURE_BY_NAME: dict[str, FeatureSpec] = {f.name: f for f in FEATURES}


@dataclass(frozen=True)
class RegionConfig:
    """How breach costs are displayed for a given locale.

    The model always predicts in the dataset's native unit (INR crore). For other
    regions, ``display_multiplier`` converts that native value into the display
    currency/unit. Conversions are approximate and meant for illustration.
    """

    code: str
    name: str
    currency_symbol: str
    currency_code: str
    unit_label: str
    display_multiplier: float = 1.0
    approximate: bool = False

    def to_display(self, native_value: float) -> float:
        """Convert a native (crore) value into this region's display units."""
        return native_value * self.display_multiplier

    def format(self, native_value: float, decimals: int = 2) -> str:
        """Format a native (crore) value as a display string, e.g. '₹18.24 crore'."""
        shown = self.to_display(native_value)
        unit = f" {self.unit_label}".rstrip()
        return f"{self.currency_symbol}{shown:,.{decimals}f}{unit}"


# 1 crore INR = 10,000,000 INR. At ~₹83/USD that is ≈ 0.12 USD million.
_INR_CRORE_TO_USD_MILLION = 0.12

REGIONS: dict[str, RegionConfig] = {
    "IN": RegionConfig(
        code="IN",
        name="India",
        currency_symbol="₹",
        currency_code="INR",
        unit_label="crore",
    ),
    "US": RegionConfig(
        code="US",
        name="United States (approx.)",
        currency_symbol="$",
        currency_code="USD",
        unit_label="million",
        display_multiplier=_INR_CRORE_TO_USD_MILLION,
        approximate=True,
    ),
}

DEFAULT_REGION: str = "IN"


def get_region(code: str | None = None) -> RegionConfig:
    """Return the region config for ``code`` (defaults to India)."""
    return REGIONS.get((code or DEFAULT_REGION).upper(), REGIONS[DEFAULT_REGION])
