# Data dictionary — `cyber_breach.csv`

200 synthetic data-breach records for Indian organisations. Synthetic data is used
because real per-company breach costs are confidential and unpublished. The dataset is
calibrated to the magnitudes in the IBM *Cost of a Data Breach* report for India.

| Column | Role | Type | Range | Meaning |
|--------|------|------|-------|---------|
| `records_exposed` | input | int | 13–500 | Records leaked, in **thousands**. |
| `detection_time` | input | int | 10–295 | Days to **detect** the breach (dwell time). |
| `response_time` | input | int | 6–120 | Days to **contain/remediate** once detected. |
| `security_score` | input | int | 20–95 | Security maturity (higher = stronger posture). |
| `breach_cost` | target | float | ~3–35 | Total financial cost, in **₹ crore**. |

## Provenance

The data is produced by a transparent generative model documented in
[`breachlens/synth.py`](../breachlens/synth.py):

```
breach_cost = 9.6
            + 0.040 · records_exposed
            + 0.020 · detection_time
            + 0.030 · response_time
            − 0.120 · security_score
            + Normal(0, 3)        # noise keeps R² realistic (~0.96, not 1.0)
```

Regenerate or extend it:

```bash
breachlens generate-data --n 500 --seed 7 --out data/extra.csv
```

## Calibration check

| Statistic | This dataset | IBM India (reference) |
|-----------|--------------|------------------------|
| Mean breach cost | ≈ ₹17.5 crore | ≈ ₹19.5 crore |

The `.xlsx` copy is the original coursework artifact; `cyber_breach.csv` is the
canonical, version-control-friendly source used by the package.
