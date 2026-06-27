"""Regenerate the static charts used in the README.

Run: ``python scripts/generate_figures.py``  (writes PNGs to docs/images/).
Deterministic given the cited benchmarks and a fixed Monte Carlo seed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from breachlens import Industry, Jurisdiction, OrgProfile  # noqa: E402
from breachlens.controls import CONTROL_CATALOG  # noqa: E402
from breachlens.cost_model import estimate_cost  # noqa: E402
from breachlens.montecarlo import simulate  # noqa: E402
from breachlens.scenario import build_investment_case  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#0f172a"
ACCENT = "#0d9488"
WARN = "#d97706"
DANGER = "#e11d48"
GRID = "#e2e8f0"

ORG = OrgProfile(
    records_exposed=350,
    detection_time=220,
    response_time=95,
    security_score=45,
    industry=Industry.FINANCIAL,
    jurisdiction=Jurisdiction.IN,
    regulatory_severity=0.4,
)


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor("white")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK)


def breakdown_chart() -> None:
    c = estimate_cost(ORG)
    fig, ax = plt.subplots(figsize=(7, 2.4), dpi=140)
    left = 0.0
    for label, value, color in [
        ("Recovery", c.recovery, ACCENT),
        ("Lost business", c.lost_business, WARN),
        ("Regulatory (DPDP)", c.regulatory, DANGER),
    ]:
        ax.barh([0], [value], left=[left], color=color, label=f"{label} (₹{value:.0f} cr)")
        left += value
    ax.set_yticks([])
    ax.set_xlabel("Breach cost (₹ crore)")
    ax.set_title(f"Itemised breach cost — ₹{c.total:.0f} crore total", color=INK, fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=3, frameon=False, fontsize=8)
    _style(ax)
    fig.savefig(OUT / "breakdown.png", bbox_inches="tight")
    plt.close(fig)


def exceedance_chart() -> None:
    mc = simulate(ORG, n=40000)
    losses, probs = mc.exceedance_curve()
    fig, ax = plt.subplots(figsize=(7, 3.4), dpi=140)
    ax.fill_between(losses, probs * 100, color=ACCENT, alpha=0.15)
    ax.plot(losses, probs * 100, color=ACCENT, lw=2.5)
    for label, val, color in [("P90", mc.p90, WARN), ("P95", mc.p95, DANGER)]:
        ax.axvline(val, color=color, ls="--", lw=1.2)
        ax.text(val, 60, f" {label}", color=color, fontweight="bold")
    ax.set_xlabel("Breach cost (₹ crore)")
    ax.set_ylabel("Probability of exceeding (%)")
    ax.set_title("Loss-exceedance curve (Monte Carlo)", color=INK, fontweight="bold")
    _style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "exceedance.png", bbox_inches="tight")
    plt.close(fig)


def roi_chart() -> None:
    controls = [
        "security_ai_automation",
        "ir_team_and_plan",
        "encryption",
        "identity_mfa",
        "employee_training",
    ]
    base = estimate_cost(ORG).total
    labels, savings = [], []
    for key in controls:
        case = build_investment_case(ORG, [key], investment=1.0)
        labels.append(CONTROL_CATALOG[key].name)
        savings.append(case.gross_savings)
    order = sorted(range(len(savings)), key=lambda i: savings[i])
    labels = [labels[i] for i in order]
    savings = [savings[i] for i in order]
    fig, ax = plt.subplots(figsize=(7, 3.4), dpi=140)
    ax.barh(labels, savings, color=ACCENT)
    for y, v in enumerate(savings):
        ax.text(v, y, f" ₹{v:.0f} cr", va="center", color=INK, fontweight="bold", fontsize=8)
    ax.set_xlabel("Breach cost avoided (₹ crore)")
    ax.set_title(f"Which controls pay off (baseline ₹{base:.0f} cr)", color=INK, fontweight="bold")
    _style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "roi.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    breakdown_chart()
    exceedance_chart()
    roi_chart()
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
