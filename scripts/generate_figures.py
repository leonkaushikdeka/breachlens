"""Regenerate the static charts used in the README.

Run: ``python scripts/generate_figures.py``  (writes PNGs to docs/images/).
These are deterministic given the bundled dataset and fixed seed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from breachlens import BreachLens  # noqa: E402
from breachlens.schema import BreachProfile  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#0f172a"
ACCENT = "#0d9488"
GRID = "#e2e8f0"


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor("white")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK)


def benchmark_chart(lens: BreachLens) -> None:
    board = lens.model.scoreboard.sort_values("r2")
    fig, ax = plt.subplots(figsize=(7, 3.4), dpi=140)
    ax.barh(board["model"], board["r2"], color=ACCENT)
    for y, v in zip(range(len(board)), board["r2"], strict=False):
        ax.text(v - 0.02, y, f"{v:.3f}", va="center", ha="right", color="white", fontweight="bold")
    ax.set_xlim(0.85, 1.0)
    ax.set_xlabel("Cross-validated R²")
    ax.set_title("Model benchmark — selected automatically by R²", color=INK, fontweight="bold")
    _style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "benchmark.png", bbox_inches="tight")
    plt.close(fig)


def importance_chart(lens: BreachLens) -> None:
    imp = lens.importance().sort_values("importance_norm")
    fig, ax = plt.subplots(figsize=(7, 3.4), dpi=140)
    ax.barh(imp["label"], imp["importance_norm"] * 100, color=ACCENT)
    ax.set_xlabel("Share of model importance (%)")
    ax.set_title("Which factors drive breach cost", color=INK, fontweight="bold")
    _style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "feature_importance.png", bbox_inches="tight")
    plt.close(fig)


def whatif_chart(lens: BreachLens) -> None:
    profile = BreachProfile(
        records_exposed=350, detection_time=220, response_time=90, security_score=45
    )
    sweep = lens.sweep(profile, "detection_time", n=40)
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=140)
    ax.fill_between(
        sweep["value"],
        sweep["lower"],
        sweep["upper"],
        color=ACCENT,
        alpha=0.15,
        label="90% interval",
    )
    ax.plot(sweep["value"], sweep["expected"], color=ACCENT, lw=2.5, label="Expected cost")
    ax.set_xlabel("Detection time (days)")
    ax.set_ylabel("Breach cost (₹ crore)")
    ax.set_title(
        "Slower detection → higher cost (what-if sensitivity)", color=INK, fontweight="bold"
    )
    ax.legend(frameon=False)
    _style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "whatif.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    lens = BreachLens.train_fresh()
    benchmark_chart(lens)
    importance_chart(lens)
    whatif_chart(lens)
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
