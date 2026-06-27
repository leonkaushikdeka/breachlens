"""FastAPI service exposing BreachLens over HTTP.

Run locally::

    uvicorn api.main:app --reload

Interactive docs are served at /docs (Swagger) and /redoc.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from breachlens import __version__
from breachlens.benchmarks import Industry, Jurisdiction
from breachlens.controls import CONTROL_CATALOG
from breachlens.penalties import regulatory_penalty
from breachlens.predictor import BreachLens
from breachlens.schema import OrgProfile

app = FastAPI(
    title="BreachLens API",
    version=__version__,
    description="Data breach cost predictor & risk quantification engine "
    "(IBM benchmarks + DPDP/GDPR penalties + Monte Carlo).",
)
lens = BreachLens()


class EstimateRequest(BaseModel):
    profile: OrgProfile
    controls: list[str] = Field(default_factory=list)


class InvestRequest(BaseModel):
    profile: OrgProfile
    add_controls: list[str]
    investment: float = Field(..., description="Annual control cost in display units.")
    breach_probability: float | None = None


@app.get("/", tags=["meta"])
def root() -> dict[str, Any]:
    return {"name": "BreachLens API", "version": __version__, "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/industries", tags=["meta"])
def industries() -> list[str]:
    return [e.value for e in Industry]


@app.get("/jurisdictions", tags=["meta"])
def jurisdictions() -> list[str]:
    return [e.value for e in Jurisdiction]


@app.get("/controls", tags=["meta"])
def controls() -> list[dict[str, Any]]:
    return [
        {
            "key": c.key,
            "name": c.name,
            "description": c.description,
            "cost_reduction": c.cost_reduction,
            "frequency_reduction": c.frequency_reduction,
        }
        for c in CONTROL_CATALOG.values()
    ]


@app.post("/estimate", tags=["estimate"])
def estimate(request: EstimateRequest) -> dict[str, Any]:
    c = lens.estimate(request.profile, request.controls)
    return {
        **c.as_dict(),
        "currency_code": c.benchmark.currency_code,
        "unit_label": c.benchmark.unit_label,
        "formatted_total": c.format(c.total),
        "drivers": c.drivers,
    }


@app.post("/simulate", tags=["estimate"])
def simulate(request: EstimateRequest) -> dict[str, Any]:
    mc = lens.simulate(request.profile, request.controls)
    losses, probs = mc.exceedance_curve()
    return {
        "mean": mc.mean,
        "p50": mc.p50,
        "p90": mc.p90,
        "p95": mc.p95,
        "currency_symbol": mc.currency_symbol,
        "unit_label": mc.unit_label,
        "exceedance_curve": {"loss": losses.tolist(), "probability": probs.tolist()},
    }


@app.post("/invest", tags=["estimate"])
def invest(request: InvestRequest) -> dict[str, Any]:
    if not request.add_controls:
        raise HTTPException(status_code=422, detail="add_controls must not be empty.")
    case = lens.investment_case(
        request.profile,
        request.add_controls,
        investment=request.investment,
        breach_probability=request.breach_probability,
    )
    return {
        "baseline_total": case.baseline.total,
        "improved_total": case.improved.total,
        "gross_savings": case.gross_savings,
        "expected_savings": case.expected_savings,
        "investment": case.investment,
        "breach_probability": case.breach_probability,
        "roi": case.roi,
        "payback_years": case.payback_years,
    }


@app.post("/penalty", tags=["estimate"])
def penalty(
    jurisdiction: Jurisdiction, records_thousands: float, severity: float = 0.35
) -> dict[str, Any]:
    p = regulatory_penalty(jurisdiction, records_thousands * 1000, severity=severity)
    return {
        "expected": p.expected,
        "statutory_max": p.statutory_max,
        "share_of_max": p.share_of_max,
        "regime": p.regime,
        "basis": p.basis,
    }
