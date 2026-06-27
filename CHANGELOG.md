# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic versioning.

## [2.0.0] — 2026-06-27

Replaced the synthetic-data ML core with a credible, real-world engine. The ML model
moved to an optional "second opinion" trained on user-supplied data.

### Added
- **Cited benchmark knowledge base** (`benchmarks.py`) — per-record cost, time-to-contain
  effect, and industry multipliers from IBM *Cost of a Data Breach 2024*; jurisdictions
  (India/EU/US) and industries.
- **Regulatory penalty models** (`penalties.py`) — DPDP Act 2023 (₹250 cr cap), GDPR
  (€20M / 4% turnover), US per-record exposure.
- **Transparent cost estimator** (`cost_model.py`) — itemised recovery + lost business +
  regulatory breakdown, every step auditable.
- **Monte Carlo** (`montecarlo.py`) — cost distribution, P50/P90/P95, loss-exceedance curve.
- **Security control catalogue** (`controls.py`) + **investment ROI** (`scenario.py`).
- Reworked Streamlit app, FastAPI service, and CLI (`estimate`, `simulate`, `invest`,
  `penalty`, `controls`).

### Changed
- `OrgProfile` adds industry, jurisdiction, and regulatory severity to the four core factors.
- The synthetic dataset is now a labelled demo seed for the optional ML path only.

### Removed
- SHAP-based `explain.py` (superseded by the cost model's transparent drivers).

## [1.0.0] — 2026-06-27

First public release. Reworked from a single-script university ML project into a
deployable cyber risk quantification tool.

### Added
- Core library `breachlens` with a clean module layout and the `BreachLens` facade.
- Model zoo (Linear, Ridge, Random Forest, Gradient Boosting) with cross-validated
  automatic selection.
- Split conformal prediction intervals (distribution-free uncertainty).
- Explainability: permutation importance + local contribution waterfall.
- What-if scenario simulator and risk-adjusted ROI.
- Transparent, regenerable synthetic data generator calibrated to IBM India figures.
- Interactive **Streamlit** app, **FastAPI** service, and **CLI**.
- pydantic input validation, region/currency configuration (India default).
- Test suite (92% coverage), ruff + mypy, GitHub Actions CI, Docker, pre-commit.

### Notes
- The bundled dataset is synthetic by design; estimates are directional
  decision-support, not actuarial figures.
