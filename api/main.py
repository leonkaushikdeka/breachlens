"""FastAPI service exposing BreachLens over HTTP.

Run locally::

    uvicorn api.main:app --reload

Interactive docs are served at /docs (Swagger) and /redoc.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from breachlens import __version__
from breachlens.config import FEATURES
from breachlens.predictor import BreachLens
from breachlens.schema import BreachProfile

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["lens"] = BreachLens.load_or_train(
        os.getenv("BREACHLENS_MODEL_PATH"), region_code=os.getenv("BREACHLENS_REGION")
    )
    yield
    _state.clear()


app = FastAPI(
    title="BreachLens API",
    version=__version__,
    description="Cyber breach cost & risk quantification engine.",
    lifespan=lifespan,
)


def _lens() -> BreachLens:
    lens = _state.get("lens")
    if lens is None:  # pragma: no cover - lifespan guarantees presence
        raise HTTPException(status_code=503, detail="Model not ready.")
    return lens


class PredictResponse(BaseModel):
    expected_cost: float
    lower: float
    upper: float
    confidence: float
    model_name: str
    currency_code: str
    formatted: str
    contributions: list[dict[str, Any]]


class WhatIfRequest(BaseModel):
    profile: BreachProfile
    changes: dict[str, float] = Field(..., description="Feature -> new value.")
    confidence: float = 0.9


class WhatIfResponse(BaseModel):
    baseline_cost: float
    adjusted_cost: float
    savings: float
    savings_pct: float
    changes: dict[str, float]


@app.get("/", tags=["meta"])
def root() -> dict[str, Any]:
    lens = _lens()
    return {
        "name": "BreachLens API",
        "version": __version__,
        "model": lens.model.name,
        "metrics": lens.model.metrics,
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok" if _state.get("lens") else "starting"}


@app.get("/features", tags=["meta"])
def features() -> list[dict[str, Any]]:
    return [
        {
            "name": f.name,
            "label": f.label,
            "unit": f.unit,
            "min": f.min,
            "max": f.max,
            "default": f.default,
            "higher_increases_cost": f.higher_increases_cost,
            "help": f.help,
        }
        for f in FEATURES
    ]


@app.get("/benchmark", tags=["model"])
def benchmark() -> list[dict[str, Any]]:
    return _lens().model.scoreboard.to_dict(orient="records")


@app.get("/importance", tags=["model"])
def importance() -> list[dict[str, Any]]:
    return _lens().importance().to_dict(orient="records")


@app.post("/predict", response_model=PredictResponse, tags=["predict"])
def predict(profile: BreachProfile, confidence: float = 0.9) -> PredictResponse:
    lens = _lens()
    result = lens.predict(profile, confidence=confidence)
    contributions = lens.explain(profile).to_dict(orient="records")
    return PredictResponse(
        expected_cost=result.expected_cost,
        lower=result.lower,
        upper=result.upper,
        confidence=result.confidence,
        model_name=result.model_name,
        currency_code=lens.region.currency_code,
        formatted=lens.format(result.expected_cost),
        contributions=contributions,
    )


@app.post("/whatif", response_model=WhatIfResponse, tags=["predict"])
def whatif(request: WhatIfRequest) -> WhatIfResponse:
    lens = _lens()
    try:
        scenario = lens.what_if(request.profile, request.changes, confidence=request.confidence)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WhatIfResponse(
        baseline_cost=scenario.baseline.expected_cost,
        adjusted_cost=scenario.adjusted.expected_cost,
        savings=scenario.savings,
        savings_pct=scenario.savings_pct,
        changes=scenario.changes,
    )
