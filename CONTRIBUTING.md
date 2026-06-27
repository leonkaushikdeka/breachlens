# Contributing to BreachLens

Thanks for your interest! BreachLens is a small, focused project and contributions are
welcome — bug reports, docs, new models, better explainers, or UI polish.

## Getting set up

```bash
git clone https://github.com/leonkaushikdeka/breachlens.git
cd breachlens
pip install -e ".[dev,app,api]"
pre-commit install        # optional but recommended
```

## Before opening a PR

Run the same checks CI runs:

```bash
make lint     # ruff check .
make type     # mypy breachlens
make cov      # pytest with coverage (keep ≥ 85%)
```

All three must pass. The test suite trains a model on a tiny dataset, so it runs in
well under a minute.

## Guidelines

- **Keep modules small and cohesive.** New behaviour usually belongs in its own
  module under `breachlens/`, wired through the `BreachLens` facade.
- **Type-annotate public functions** and add a short docstring.
- **Add tests** for new behaviour (unit for logic, integration when a trained model is
  involved). Mark them with `@pytest.mark.unit` / `@pytest.mark.integration`.
- **Don't break the honest-uncertainty contract** — predictions should always carry an
  interval, and the synthetic-data disclaimer must remain visible.

## Ideas to pick up

See the **Roadmap** in the [README](README.md#-roadmap). Good first issues:
bring-your-own-CSV training, a calibration/coverage plot, and a SHAP panel.
