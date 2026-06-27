"""Generate a LinkedIn share card (1200x627) for BreachLens.

Run: ``python scripts/social_card.py`` → docs/images/linkedin_card.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from breachlens import Industry, Jurisdiction, OrgProfile  # noqa: E402
from breachlens.montecarlo import simulate  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

BG = "#070b14"
PANEL = "#0f1a2b"
ACCENT = "#5eead4"
INK = "#e2e8f0"
MUTED = "#94a3b8"


def main() -> None:
    fig = plt.figure(figsize=(12, 6.27), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.27)
    ax.axis("off")
    ax.set_facecolor(BG)

    # accent rule
    ax.add_patch(plt.Rectangle((0.7, 5.95), 0.55, 0.06, color=ACCENT))
    ax.text(0.7, 5.55, "CYBER RISK QUANTIFICATION", color=ACCENT, fontsize=12.5,
            fontweight="bold", family="sans-serif")
    ax.text(0.68, 4.75, "BreachLens", color="white", fontsize=58, fontweight="bold")
    ax.text(0.7, 3.95, "What would a data breach actually cost you?",
            color=INK, fontsize=20)

    bullets = [
        "Grounded in real IBM breach-cost benchmarks",
        "Real penalties — DPDP Act 2023 (₹250 cr) & GDPR",
        "Monte Carlo risk + security-investment ROI",
    ]
    for i, text in enumerate(bullets):
        y = 3.25 - i * 0.52
        ax.add_patch(plt.Circle((0.85, y + 0.06), 0.055, color=ACCENT))
        ax.text(1.15, y, text, color=INK, fontsize=13.5, va="center")

    ax.text(0.7, 0.6, "github.com/leonkaushikdeka/breachlens", color=ACCENT,
            fontsize=14, fontweight="bold")
    ax.text(0.72, 0.25, "Python · scikit-learn · Streamlit · FastAPI · MIT",
            color=MUTED, fontsize=11.5)

    # right-hand hero panel with the exceedance curve
    panel = FancyBboxPatch((7.7, 1.25), 3.75, 3.75, boxstyle="round,pad=0.02,rounding_size=0.18",
                           linewidth=1, edgecolor="#1e293b", facecolor=PANEL)
    ax.add_patch(panel)
    curve = fig.add_axes([0.665, 0.26, 0.285, 0.45])
    curve.set_facecolor(PANEL)
    org = OrgProfile(records_exposed=350, detection_time=220, response_time=95,
                     security_score=45, industry=Industry.FINANCIAL,
                     jurisdiction=Jurisdiction.IN, regulatory_severity=0.4)
    mc = simulate(org, n=40000)
    losses, probs = mc.exceedance_curve()
    curve.fill_between(losses, probs * 100, color=ACCENT, alpha=0.18)
    curve.plot(losses, probs * 100, color=ACCENT, lw=2.5)
    curve.axvline(mc.p90, color="#fbbf24", ls="--", lw=1)
    curve.axvline(mc.p95, color="#fb7185", ls="--", lw=1)
    curve.set_title("Loss-exceedance curve", color=INK, fontsize=11, fontweight="bold")
    curve.set_xlabel("Breach cost (₹ crore)", color=MUTED, fontsize=9)
    curve.set_ylabel("P(exceeds) %", color=MUTED, fontsize=9)
    curve.tick_params(colors=MUTED, labelsize=8)
    for s in curve.spines.values():
        s.set_color("#334155")

    fig.savefig(OUT / "linkedin_card.png", facecolor=BG, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"Wrote {OUT / 'linkedin_card.png'}")


if __name__ == "__main__":
    main()
