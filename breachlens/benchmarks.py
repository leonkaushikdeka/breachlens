"""Cited industry benchmark knowledge base.

This module is the credibility anchor of BreachLens. Instead of inventing a cost
formula, the estimator is parameterised by **published industry figures** — primarily
the IBM / Ponemon *Cost of a Data Breach* report — with every constant traceable to a
source. All values are illustrative reference points and are overridable; they are not
a guarantee for any specific organisation.

Primary sources
---------------
- IBM Security, *Cost of a Data Breach Report 2024* (global average USD 4.88M; average
  cost per record; mean time to identify + contain ≈ 258 days; cost amplifiers and
  mitigators in USD). https://www.ibm.com/reports/data-breach
- IBM India figures (average breach ≈ ₹19.5 crore; lower per-record cost than the US).
- Verizon, *Data Breach Investigations Report (DBIR)* — relative breach frequency by
  industry. https://www.verizon.com/business/resources/reports/dbir/
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Jurisdiction(str, Enum):
    """Regulatory + currency regime the estimate is produced for."""

    IN = "IN"  # India — ₹ crore, DPDP Act 2023
    EU = "EU"  # European Union — € million, GDPR
    US = "US"  # United States — $ million, state breach laws


class Industry(str, Enum):
    HEALTHCARE = "healthcare"
    FINANCIAL = "financial"
    TECHNOLOGY = "technology"
    ENERGY = "energy"
    SERVICES = "services"
    RETAIL = "retail"
    PUBLIC = "public"
    EDUCATION = "education"


@dataclass(frozen=True)
class Citation:
    source: str
    year: int
    url: str
    note: str = ""

    def __str__(self) -> str:
        return f"{self.source} ({self.year})"


IBM_2024 = Citation(
    source="IBM Cost of a Data Breach Report",
    year=2024,
    url="https://www.ibm.com/reports/data-breach",
)
DBIR_2024 = Citation(
    source="Verizon DBIR",
    year=2024,
    url="https://www.verizon.com/business/resources/reports/dbir/",
)


@dataclass(frozen=True)
class JurisdictionBenchmark:
    """Per-jurisdiction cost anchors, expressed in that jurisdiction's display unit.

    The estimator works directly in ``unit_label`` (crore for INR, million for
    USD/EUR), so no FX conversion is needed inside the model.
    """

    code: Jurisdiction
    currency_symbol: str
    currency_code: str
    unit_label: str
    unit_value: float  # raw-currency value of one display unit (crore = 1e7)
    avg_total: float  # average breach total cost in display units
    avg_total_low: float  # plausibility band low (Monte Carlo)
    avg_total_high: float  # plausibility band high
    ref_records: int  # reference breach size the average corresponds to
    citation: Citation = IBM_2024

    def format(self, value: float, decimals: int = 2) -> str:
        unit = f" {self.unit_label}".rstrip()
        return f"{self.currency_symbol}{value:,.{decimals}f}{unit}"


# Average totals are anchored to published regional figures; low/high give the
# uncertainty band used by the Monte Carlo simulation.
JURISDICTIONS: dict[Jurisdiction, JurisdictionBenchmark] = {
    Jurisdiction.IN: JurisdictionBenchmark(
        code=Jurisdiction.IN,
        currency_symbol="₹",
        currency_code="INR",
        unit_label="crore",
        unit_value=1e7,
        avg_total=19.5,
        avg_total_low=14.0,
        avg_total_high=28.0,
        ref_records=25_000,
    ),
    Jurisdiction.EU: JurisdictionBenchmark(
        code=Jurisdiction.EU,
        currency_symbol="€",
        currency_code="EUR",
        unit_label="million",
        unit_value=1e6,
        avg_total=4.3,
        avg_total_low=3.2,
        avg_total_high=6.5,
        ref_records=25_000,
    ),
    Jurisdiction.US: JurisdictionBenchmark(
        code=Jurisdiction.US,
        currency_symbol="$",
        currency_code="USD",
        unit_label="million",
        unit_value=1e6,
        avg_total=9.36,
        avg_total_low=6.5,
        avg_total_high=13.0,
        ref_records=25_000,
    ),
}

# Breach cost scales sub-linearly with records (mega-breaches cost more in total but
# less per record). Exponent ≈ 0.6 reproduces IBM's "cost vs. breach size" curve shape.
RECORD_SCALING_EXPONENT: float = 0.6

# Industry cost multipliers relative to the cross-industry average. Healthcare has led
# IBM's ranking for over a decade; public sector sits lowest.
INDUSTRY_MULTIPLIERS: dict[Industry, float] = {
    Industry.HEALTHCARE: 1.55,
    Industry.FINANCIAL: 1.30,
    Industry.TECHNOLOGY: 1.15,
    Industry.ENERGY: 1.20,
    Industry.SERVICES: 1.00,
    Industry.RETAIL: 0.92,
    Industry.EDUCATION: 0.88,
    Industry.PUBLIC: 0.82,
}

# Relative annual breach likelihood by industry (DBIR-informed, normalised so
# SERVICES ≈ 1.0). Used for annualised-loss / frequency reasoning.
INDUSTRY_BREACH_FREQUENCY: dict[Industry, float] = {
    Industry.HEALTHCARE: 1.4,
    Industry.FINANCIAL: 1.5,
    Industry.TECHNOLOGY: 1.2,
    Industry.ENERGY: 1.0,
    Industry.SERVICES: 1.0,
    Industry.RETAIL: 1.1,
    Industry.EDUCATION: 0.9,
    Industry.PUBLIC: 1.2,
}

# Time-to-contain effect. IBM: breaches with a lifecycle > 200 days cost markedly more
# than those contained faster. Modelled as a multiplier pivoting at 200 days.
LIFECYCLE_PIVOT_DAYS: int = 200
LIFECYCLE_SLOPE_PER_DAY: float = 0.0017  # ≈ +34% at 400 days vs the 200-day pivot
LIFECYCLE_MULT_MIN: float = 0.80
LIFECYCLE_MULT_MAX: float = 1.45

# Security maturity effect. Net of IBM's largest mitigators (security AI/automation,
# IR team + tested plan, encryption, employee training) and amplifiers (skills
# shortage, system complexity, non-compliance). A 0–100 posture maps to ±30%.
MATURITY_MULT_AT_ZERO: float = 1.30
MATURITY_SLOPE_PER_POINT: float = 0.006  # 1.30 at score 0 → 1.00 at 50 → 0.70 at 100


def jurisdiction(code: Jurisdiction | str) -> JurisdictionBenchmark:
    key = Jurisdiction(code) if not isinstance(code, Jurisdiction) else code
    return JURISDICTIONS[key]
