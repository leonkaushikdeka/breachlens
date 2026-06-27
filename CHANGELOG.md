# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic versioning.

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
