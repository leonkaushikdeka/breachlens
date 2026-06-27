"""BreachLens — open-source data breach cost predictor & risk quantification engine.

Estimate what a data breach would cost an organisation from real, cited industry
benchmarks (IBM Cost of a Data Breach) plus regulatory penalty models (DPDP Act 2023,
GDPR), with Monte Carlo uncertainty and a security-investment ROI simulator.

Quick start::

    from breachlens import BreachLens, OrgProfile, Industry, Jurisdiction

    lens = BreachLens()
    org = OrgProfile(
        records_exposed=300, detection_time=200, response_time=90, security_score=45,
        industry=Industry.FINANCIAL, jurisdiction=Jurisdiction.IN,
    )
    cost = lens.estimate(org)
    print(cost.format(cost.total))            # e.g. ₹120.34 crore

    mc = lens.simulate(org)
    print(mc.format(mc.p90))                   # 90th-percentile loss
"""

from __future__ import annotations

from .benchmarks import Industry, Jurisdiction, jurisdiction
from .controls import CONTROL_CATALOG
from .cost_model import CostBreakdown, estimate_cost
from .montecarlo import MonteCarloResult, simulate
from .penalties import regulatory_penalty
from .predictor import BreachLens
from .report import build_html, build_markdown
from .scenario import InvestmentCase, build_investment_case
from .schema import BreachProfile, OrgProfile, PredictionResult

__all__ = [
    "BreachLens",
    "OrgProfile",
    "BreachProfile",
    "PredictionResult",
    "CostBreakdown",
    "MonteCarloResult",
    "InvestmentCase",
    "Industry",
    "Jurisdiction",
    "CONTROL_CATALOG",
    "estimate_cost",
    "simulate",
    "regulatory_penalty",
    "build_investment_case",
    "build_markdown",
    "build_html",
    "jurisdiction",
]

__version__ = "2.0.0"
