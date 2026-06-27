"""Command-line interface for BreachLens.

Examples::

    breachlens benchmark
    breachlens train --out models/breach_model.joblib
    breachlens predict --records 300 --detection 200 --response 90 --security 40
    breachlens whatif --records 300 --detection 200 --response 90 --security 40 \\
        --improve detection_time=100 --improve security_score=70
    breachlens generate-data --n 500 --seed 7 --out data/extra.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .config import FEATURE_NAMES, get_region
from .models import benchmark_models
from .predictor import BreachLens
from .schema import BreachProfile
from .synth import generate_synthetic_breaches

_FLAG_TO_FEATURE = {
    "records": "records_exposed",
    "detection": "detection_time",
    "response": "response_time",
    "security": "security_score",
}


def _add_profile_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--records", type=float, required=True, help="Records exposed (thousands).")
    parser.add_argument("--detection", type=float, required=True, help="Detection time (days).")
    parser.add_argument("--response", type=float, required=True, help="Containment time (days).")
    parser.add_argument("--security", type=float, required=True, help="Security maturity (0-100).")


def _profile_from_args(args: argparse.Namespace) -> BreachProfile:
    return BreachProfile(
        records_exposed=args.records,
        detection_time=args.detection,
        response_time=args.response,
        security_score=args.security,
    )


def _parse_improvements(pairs: Sequence[str] | None) -> dict[str, float]:
    changes: dict[str, float] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--improve expects KEY=VALUE, got '{pair}'.")
        key, value = pair.split("=", 1)
        if key not in FEATURE_NAMES:
            raise SystemExit(f"Unknown feature '{key}'. Choose from {FEATURE_NAMES}.")
        changes[key] = float(value)
    return changes


def _cmd_benchmark(args: argparse.Namespace) -> int:
    from .data import load_dataset, split_features_target

    X, y = split_features_target(load_dataset())
    board = benchmark_models(X, y, seed=args.seed)
    if args.json:
        print(board.to_json(orient="records", indent=2))
    else:
        print("Model benchmark (5-fold CV):\n")
        print(board.to_string(index=False))
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    lens = BreachLens.train_fresh(seed=args.seed)
    path = lens.save(args.out)
    m = lens.model.metrics
    print(f"Trained '{lens.model.name}' on {lens.model.n_train} samples -> {path}")
    print(f"  Test R2 : {m['r2']:.3f}")
    print(f"  Test MAE: {m['mae']:.2f} crore")
    print(f"  Test RMSE: {m['rmse']:.2f} crore")
    print(
        f"  {int(lens.model.confidence * 100)}% interval half-width: "
        f"±{m['interval_half_width']:.2f} crore"
    )
    return 0


def _cmd_predict(args: argparse.Namespace) -> int:
    lens = BreachLens.load_or_train(args.model, region_code=args.region)
    profile = _profile_from_args(args)
    result = lens.predict(profile, confidence=args.confidence)
    contributions = lens.explain(profile)

    if args.json:
        payload = {
            "expected_cost": result.expected_cost,
            "lower": result.lower,
            "upper": result.upper,
            "confidence": result.confidence,
            "model": result.model_name,
            "currency": lens.region.currency_code,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Model: {result.model_name}")
    print(f"Expected breach cost: {lens.format(result.expected_cost)}")
    print(
        f"{int(result.confidence * 100)}% interval: "
        f"{lens.format(result.lower)} – {lens.format(result.upper)}"
    )
    print("\nTop cost drivers vs a typical breach:")
    for _, row in contributions.head(4).iterrows():
        sign = "+" if row["contribution"] >= 0 else "-"
        print(f"  {row['label']:24s} {sign}{lens.format(abs(row['contribution']))}")
    return 0


def _cmd_whatif(args: argparse.Namespace) -> int:
    lens = BreachLens.load_or_train(args.model, region_code=args.region)
    profile = _profile_from_args(args)
    changes = _parse_improvements(args.improve)
    if not changes:
        raise SystemExit("Provide at least one --improve KEY=VALUE.")
    scenario = lens.what_if(profile, changes, confidence=args.confidence)

    if args.json:
        print(
            json.dumps(
                {
                    "baseline": scenario.baseline.expected_cost,
                    "adjusted": scenario.adjusted.expected_cost,
                    "savings": scenario.savings,
                    "savings_pct": scenario.savings_pct,
                    "changes": scenario.changes,
                },
                indent=2,
            )
        )
        return 0

    print(f"Baseline expected cost : {lens.format(scenario.baseline.expected_cost)}")
    print(f"Adjusted expected cost : {lens.format(scenario.adjusted.expected_cost)}")
    verb = "saves" if scenario.savings >= 0 else "adds"
    print(f"This change {verb} {lens.format(abs(scenario.savings))} ({scenario.savings_pct:+.1%}).")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    df = generate_synthetic_breaches(n=args.n, seed=args.seed)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} synthetic records to {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="breachlens",
        description="Cyber breach cost & risk quantification engine.",
    )
    parser.add_argument("--region", default=None, help="Display region (IN, US).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bench = sub.add_parser("benchmark", help="Cross-validate the model zoo.")
    p_bench.add_argument("--seed", type=int, default=2)
    p_bench.add_argument("--json", action="store_true")
    p_bench.set_defaults(func=_cmd_benchmark)

    p_train = sub.add_parser("train", help="Train and persist the best model.")
    p_train.add_argument("--out", default=None, help="Output .joblib path.")
    p_train.add_argument("--seed", type=int, default=2)
    p_train.set_defaults(func=_cmd_train)

    p_pred = sub.add_parser("predict", help="Predict the cost of one breach profile.")
    _add_profile_flags(p_pred)
    p_pred.add_argument("--confidence", type=float, default=0.9)
    p_pred.add_argument("--model", default=None, help="Path to a saved model.")
    p_pred.add_argument("--json", action="store_true")
    p_pred.set_defaults(func=_cmd_predict)

    p_wi = sub.add_parser("whatif", help="Simulate a security improvement.")
    _add_profile_flags(p_wi)
    p_wi.add_argument(
        "--improve",
        action="append",
        metavar="KEY=VALUE",
        help="Feature change, repeatable (e.g. detection_time=100).",
    )
    p_wi.add_argument("--confidence", type=float, default=0.9)
    p_wi.add_argument("--model", default=None)
    p_wi.add_argument("--json", action="store_true")
    p_wi.set_defaults(func=_cmd_whatif)

    p_gen = sub.add_parser("generate-data", help="Write a fresh synthetic dataset.")
    p_gen.add_argument("--n", type=int, default=200)
    p_gen.add_argument("--seed", type=int, default=2)
    p_gen.add_argument("--out", default="data/synthetic_breaches.csv")
    p_gen.set_defaults(func=_cmd_generate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Validate region early for a friendly message.
    if args.region:
        get_region(args.region)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
