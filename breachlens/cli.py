"""Command-line interface for BreachLens.

Examples::

    breachlens estimate --records 300 --detection 220 --response 95 --security 45 \\
        --industry financial --jurisdiction IN
    breachlens simulate --records 300 --detection 220 --response 95 --security 45
    breachlens invest --records 300 --detection 220 --response 95 --security 45 \\
        --controls security_ai_automation,ir_team_and_plan --investment 3
    breachlens penalty --records 300 --jurisdiction IN --severity 0.4
    breachlens controls
    breachlens train --out models/breach_model.joblib
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .benchmarks import Industry, Jurisdiction
from .controls import CONTROL_CATALOG
from .penalties import regulatory_penalty
from .predictor import BreachLens
from .schema import OrgProfile

_lens = BreachLens()


def _add_profile_flags(parser: argparse.ArgumentParser, *, full: bool = True) -> None:
    parser.add_argument("--records", type=float, required=True, help="Records exposed (thousands).")
    if full:
        parser.add_argument("--detection", type=float, default=160, help="Detection time (days).")
        parser.add_argument("--response", type=float, default=58, help="Containment time (days).")
        parser.add_argument("--security", type=float, default=60, help="Security maturity (0-100).")
        parser.add_argument("--industry", choices=[e.value for e in Industry], default="services")
    parser.add_argument("--jurisdiction", choices=[e.value for e in Jurisdiction], default="IN")
    parser.add_argument("--severity", type=float, default=0.35, help="Regulatory severity 0-1.")


def _profile(args: argparse.Namespace) -> OrgProfile:
    return OrgProfile(
        records_exposed=args.records,
        detection_time=getattr(args, "detection", 160),
        response_time=getattr(args, "response", 58),
        security_score=getattr(args, "security", 60),
        industry=Industry(getattr(args, "industry", "services")),
        jurisdiction=Jurisdiction(args.jurisdiction),
        regulatory_severity=args.severity,
    )


def _parse_controls(value: str | None) -> list[str]:
    keys = [k.strip() for k in (value or "").split(",") if k.strip()]
    for k in keys:
        if k not in CONTROL_CATALOG:
            raise SystemExit(f"Unknown control '{k}'. Run `breachlens controls`.")
    return keys


def _cmd_estimate(args: argparse.Namespace) -> int:
    profile = _profile(args)
    controls = _parse_controls(args.controls)
    c = _lens.estimate(profile, controls)
    if args.json:
        print(
            json.dumps(
                {**c.as_dict(), "currency": c.benchmark.currency_code, "drivers": c.drivers},
                indent=2,
            )
        )
        return 0
    print(f"Breach cost estimate · {profile.industry.value} · {profile.jurisdiction.value}")
    print(f"  Recovery       : {c.format(c.recovery)}")
    print(f"  Lost business  : {c.format(c.lost_business)}")
    print(f"  Regulatory fine: {c.format(c.regulatory)}")
    print(f"  {'-' * 30}")
    print(f"  TOTAL          : {c.format(c.total)}")
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    profile = _profile(args)
    mc = _lens.simulate(profile, _parse_controls(args.controls), n=args.n)
    if args.json:
        print(json.dumps({"mean": mc.mean, "p50": mc.p50, "p90": mc.p90, "p95": mc.p95}, indent=2))
        return 0
    print("Monte Carlo breach-cost distribution:")
    print(f"  Expected (mean): {mc.format(mc.mean)}")
    print(f"  Median  (P50)  : {mc.format(mc.p50)}")
    print(f"  P90            : {mc.format(mc.p90)}")
    print(f"  P95 (tail risk): {mc.format(mc.p95)}")
    return 0


def _cmd_invest(args: argparse.Namespace) -> int:
    profile = _profile(args)
    controls = _parse_controls(args.controls)
    if not controls:
        raise SystemExit("Provide --controls k1,k2 to evaluate.")
    case = _lens.investment_case(
        profile, controls, investment=args.investment, breach_probability=args.prob
    )
    fmt = case.baseline.format
    if args.json:
        print(
            json.dumps(
                {
                    "baseline": case.baseline.total,
                    "improved": case.improved.total,
                    "gross_savings": case.gross_savings,
                    "expected_savings": case.expected_savings,
                    "investment": case.investment,
                    "roi": case.roi,
                    "payback_years": case.payback_years,
                },
                indent=2,
            )
        )
        return 0
    print(f"Security investment case ({', '.join(controls)}):")
    print(f"  Baseline breach cost : {fmt(case.baseline.total)}")
    print(f"  After investment     : {fmt(case.improved.total)}")
    print(f"  Gross savings        : {fmt(case.gross_savings)}")
    print(f"  Annual breach prob   : {case.breach_probability:.1%}")
    print(f"  Risk-adjusted saving : {fmt(case.expected_savings)} / year")
    print(f"  Investment           : {fmt(case.investment)} / year")
    print(f"  ROI                  : {case.roi:.2f}×   payback {case.payback_years:.1f} yr")
    return 0


def _cmd_penalty(args: argparse.Namespace) -> int:
    p = regulatory_penalty(args.jurisdiction, args.records * 1000, severity=args.severity)
    if args.json:
        print(
            json.dumps(
                {"expected": p.expected, "statutory_max": p.statutory_max, "regime": p.regime},
                indent=2,
            )
        )
        return 0
    print(f"Regulatory exposure ({p.regime}):")
    print(f"  Estimated penalty: {p.expected:,.2f}")
    print(f"  Statutory maximum: {p.statutory_max:,.2f}")
    print(f"  Basis            : {p.basis}")
    return 0


def _cmd_controls(args: argparse.Namespace) -> int:
    print("Available security controls (cost reduction · frequency reduction):\n")
    for c in CONTROL_CATALOG.values():
        print(f"  {c.key:24s} −{c.cost_reduction:.0%} cost  −{c.frequency_reduction:.0%} freq")
        print(f"  {'':24s} {c.name}: {c.description}")
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    from .models import save_model, train

    model = train(seed=args.seed)
    path = save_model(model, args.out)
    m = model.metrics
    print(f"Trained ML model '{model.name}' on {model.n_train} samples -> {path}")
    print(f"  Test R2: {m['r2']:.3f} | MAE: {m['mae']:.2f} | RMSE: {m['rmse']:.2f}")
    print("  (optional second opinion; the benchmark engine is the primary estimator)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="breachlens",
        description="Data breach cost predictor & risk quantification engine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_est = sub.add_parser("estimate", help="Itemised breach-cost estimate.")
    _add_profile_flags(p_est)
    p_est.add_argument("--controls", default=None, help="Comma-separated control keys.")
    p_est.add_argument("--json", action="store_true")
    p_est.set_defaults(func=_cmd_estimate)

    p_sim = sub.add_parser("simulate", help="Monte Carlo cost distribution.")
    _add_profile_flags(p_sim)
    p_sim.add_argument("--controls", default=None)
    p_sim.add_argument("--n", type=int, default=10000)
    p_sim.add_argument("--json", action="store_true")
    p_sim.set_defaults(func=_cmd_simulate)

    p_inv = sub.add_parser("invest", help="ROI of adding security controls.")
    _add_profile_flags(p_inv)
    p_inv.add_argument("--controls", required=True, help="Comma-separated control keys.")
    p_inv.add_argument(
        "--investment", type=float, required=True, help="Annual cost (display units)."
    )
    p_inv.add_argument("--prob", type=float, default=None, help="Annual breach probability 0-1.")
    p_inv.add_argument("--json", action="store_true")
    p_inv.set_defaults(func=_cmd_invest)

    p_pen = sub.add_parser("penalty", help="Regulatory penalty exposure.")
    _add_profile_flags(p_pen, full=False)
    p_pen.add_argument("--json", action="store_true")
    p_pen.set_defaults(func=_cmd_penalty)

    p_ctl = sub.add_parser("controls", help="List the security control catalogue.")
    p_ctl.set_defaults(func=_cmd_controls)

    p_train = sub.add_parser("train", help="Train the optional ML second opinion.")
    p_train.add_argument("--out", default=None)
    p_train.add_argument("--seed", type=int, default=2)
    p_train.set_defaults(func=_cmd_train)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
