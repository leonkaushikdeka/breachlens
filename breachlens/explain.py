"""Explainability: why did the model predict this cost?

Two complementary views, both model-agnostic (work for linear models and trees
alike):

* **Global importance** — permutation importance: how much test accuracy degrades
  when each feature is shuffled. Answers "which factors drive cost overall?".
* **Local contributions** — how a specific breach differs from a *typical* breach,
  attributed feature by feature. Answers "why is *this* estimate high/low?" and
  drives the waterfall chart in the app.

SHAP is supported as an optional extra (``pip install breachlens[explain]``) but is
not required; the core install stays lightweight for free hosting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from .config import FEATURE_BY_NAME, FEATURE_NAMES
from .models import BreachModel
from .schema import BreachProfile


def global_importance(
    model: BreachModel,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    n_repeats: int = 20,
    seed: int = 2,
) -> pd.DataFrame:
    """Permutation importance for each feature, normalised to sum to 1.

    Returns a DataFrame sorted by importance with columns:
    ``feature, label, importance, importance_norm``.
    """
    result = permutation_importance(
        model.pipeline,
        X[model.feature_names],
        y,
        n_repeats=n_repeats,
        random_state=seed,
        scoring="r2",
    )
    raw = np.clip(result.importances_mean, 0.0, None)
    total = raw.sum() or 1.0
    frame = pd.DataFrame(
        {
            "feature": model.feature_names,
            "label": [FEATURE_BY_NAME[f].label for f in model.feature_names],
            "importance": raw,
            "importance_norm": raw / total,
        }
    )
    return frame.sort_values("importance", ascending=False).reset_index(drop=True)


def local_contributions(
    model: BreachModel,
    profile: BreachProfile,
    baseline: BreachProfile | None = None,
) -> pd.DataFrame:
    """Attribute a prediction's gap from a baseline breach to each feature.

    For each feature, hold every other feature at the baseline and switch only that
    feature to its actual value; the change in predicted cost is its contribution.
    Contributions plus the baseline cost approximately reconstruct the prediction
    (exactly for additive models).

    Returns columns: ``feature, label, value, contribution`` (₹ crore), sorted by
    absolute contribution.
    """
    base = baseline or BreachProfile.midpoint()
    base_feats = base.to_features()
    actual_feats = profile.to_features()

    base_cost = float(model.predict_point(pd.DataFrame([base_feats]))[0])

    rows = []
    for name in FEATURE_NAMES:
        perturbed = dict(base_feats)
        perturbed[name] = actual_feats[name]
        cost = float(model.predict_point(pd.DataFrame([perturbed]))[0])
        rows.append(
            {
                "feature": name,
                "label": FEATURE_BY_NAME[name].label,
                "value": actual_feats[name],
                "contribution": cost - base_cost,
            }
        )

    frame = pd.DataFrame(rows)
    frame["abs"] = frame["contribution"].abs()
    frame = frame.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)
    frame.attrs["baseline_cost"] = base_cost
    return frame
