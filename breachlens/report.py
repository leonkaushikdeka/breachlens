"""Board-ready breach-cost report generation.

Produces a self-contained report (Markdown or printable HTML) summarising the estimate,
the risk distribution, and the highest-ROI security investments — the artifact a CISO,
vCISO, or consultant actually hands to a board or client. HTML can be opened in a
browser and "Print → Save as PDF" with no extra dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .controls import CONTROL_CATALOG
from .cost_model import estimate_cost
from .montecarlo import simulate
from .scenario import build_investment_case
from .schema import OrgProfile

_DISCLAIMER = (
    "Decision-support estimates, not actuarial or legal figures. Constants are "
    "illustrative reference points from public reports (IBM Cost of a Data Breach; "
    "DPDP Act 2023; GDPR) and are overridable. Not for sole use in insurance, "
    "financial, or legal decisions."
)


def _top_controls(profile: OrgProfile, k: int = 5) -> list[tuple[str, float]]:
    """Rank controls by the breach cost each avoids (gross savings), descending."""
    ranked = []
    for key in CONTROL_CATALOG:
        case = build_investment_case(profile, [key], investment=0.0)
        ranked.append((key, case.gross_savings))
    ranked.sort(key=lambda kv: kv[1], reverse=True)
    return ranked[:k]


def build_markdown(profile: OrgProfile, *, n: int = 10_000, seed: int = 2) -> str:
    """Return a board-ready Markdown report for ``profile``."""
    c = estimate_cost(profile)
    mc = simulate(profile, n=n, seed=seed)
    fmt = c.format
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        "# Data Breach Cost & Risk Report",
        "",
        f"_Generated {generated} · BreachLens · industry: **{profile.industry.value}** · "
        f"jurisdiction: **{profile.jurisdiction.value}**_",
        "",
        "## Executive summary",
        "",
        f"A data breach exposing **{profile.records_exposed:,.0f}k records** is estimated to "
        f"cost **{fmt(c.total)}**. There is a **10% chance the cost exceeds {mc.format(mc.p90)}** "
        f"and a 5% chance it exceeds {mc.format(mc.p95)} (tail risk).",
        "",
        "## Cost breakdown",
        "",
        "| Component | Estimated cost |",
        "|---|---|",
        f"| Recovery & response | {fmt(c.recovery)} |",
        f"| Lost business | {fmt(c.lost_business)} |",
        f"| Regulatory penalty | {fmt(c.regulatory)} |",
        f"| **Total** | **{fmt(c.total)}** |",
        "",
        "## Risk distribution (Monte Carlo)",
        "",
        "| Measure | Breach cost |",
        "|---|---|",
        f"| Expected (mean) | {mc.format(mc.mean)} |",
        f"| Median (P50) | {mc.format(mc.p50)} |",
        f"| P90 | {mc.format(mc.p90)} |",
        f"| P95 (tail risk) | {mc.format(mc.p95)} |",
        "",
        "## Recommended investments (by cost avoided)",
        "",
        "| Security control | Breach cost avoided |",
        "|---|---|",
    ]
    for key, savings in _top_controls(profile):
        lines.append(f"| {CONTROL_CATALOG[key].name} | {fmt(savings)} |")

    d = c.drivers
    lines += [
        "",
        "## Key drivers",
        "",
        f"- Breach size factor: **{d['size_factor']:.2f}×**",
        f"- Industry multiplier: **{d['industry_multiplier']:.2f}×**",
        f"- Detection + containment speed: **{d['lifecycle_multiplier']:.2f}×**",
        f"- Security posture: **{d['maturity_multiplier']:.2f}×**",
        "",
        "## Methodology & sources",
        "",
        "Cost is a transparent transformation of published industry figures: the regional "
        "average breach cost scaled by breach size, industry, detection/containment speed "
        "and security posture, plus a regulatory penalty. Uncertainty is quantified by "
        "Monte Carlo simulation.",
        "",
        "- IBM *Cost of a Data Breach Report 2024*",
        "- DPDP Act 2023 (India) · GDPR Art. 83(5) (EU)",
        "- Verizon DBIR (breach frequency by industry)",
        "",
        "---",
        "",
        f"> {_DISCLAIMER}",
    ]
    return "\n".join(lines)


def build_html(profile: OrgProfile, *, n: int = 10_000, seed: int = 2) -> str:
    """Return a self-contained, printable HTML report (Print → Save as PDF)."""
    import html

    body_md = build_markdown(profile, n=n, seed=seed)
    # Minimal Markdown → HTML for the subset we emit (headings, tables, lists, bold).
    rows: list[str] = []
    in_table = False
    header_pending = False
    for raw in body_md.splitlines():
        line = raw.rstrip()
        if line.startswith("| "):
            if not in_table:
                rows.append("<table>")
                in_table = True
                header_pending = True
            cells = [x.strip() for x in line.strip("|").split("|")]
            if set("".join(cells)) <= {"-", " "}:  # the |---|---| separator row
                continue
            tag = "th" if header_pending else "td"
            header_pending = False
            cells_html = "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells)
            rows.append(f"<tr>{cells_html}</tr>")
            continue
        if in_table:
            rows.append("</table>")
            in_table = False
        if line.startswith("# "):
            rows.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            rows.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            rows.append(f"<li>{_inline(line[2:])}</li>")
        elif line.startswith("> "):
            rows.append(f"<blockquote>{_inline(line[2:])}</blockquote>")
        elif line in ("", "---"):
            rows.append("<hr>" if line == "---" else "")
        else:
            rows.append(f"<p>{_inline(line)}</p>")
    if in_table:
        rows.append("</table>")

    content = "\n".join(rows)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>BreachLens Report</title><style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 820px;
          margin: 2rem auto; color: #0f172a; line-height: 1.5; padding: 0 1rem; }}
  h1 {{ font-size: 1.8rem; border-bottom: 3px solid #0d9488; padding-bottom: .3rem; }}
  h2 {{ font-size: 1.2rem; color: #0d9488; margin-top: 1.6rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: .6rem 0; }}
  th, td {{ border: 1px solid #cbd5e1; padding: .45rem .7rem; text-align: left; }}
  th {{ background: #f1f5f9; }}
  blockquote {{ color: #64748b; font-size: .85rem; border-left: 3px solid #cbd5e1;
                padding-left: .8rem; }}
</style></head><body>{content}</body></html>"""


def _inline(text: str) -> str:
    import html
    import re

    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
