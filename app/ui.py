"""BreachLens interactive web app (Streamlit).

A control-room style cyber-risk console: profile an organisation, get a transparent,
benchmark-grounded breach-cost estimate with a Monte Carlo risk distribution, then
quantify which security investments cut that cost the most.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from breachlens import __version__
from breachlens.benchmarks import IBM_2024, Industry, Jurisdiction
from breachlens.controls import CONTROL_CATALOG
from breachlens.cost_model import estimate_cost
from breachlens.montecarlo import simulate
from breachlens.predictor import BreachLens
from breachlens.scenario import build_investment_case, sweep
from breachlens.schema import OrgProfile

ACCENT = "#5eead4"
DANGER = "#fb7185"
GOOD = "#34d399"
WARN = "#fbbf24"
INK = "#e2e8f0"
MUTED = "#94a3b8"

PRESETS: dict[str, dict] = {
    "Indian bank (large)": dict(
        records_exposed=400,
        detection_time=180,
        response_time=70,
        security_score=55,
        industry=Industry.FINANCIAL,
        jurisdiction=Jurisdiction.IN,
        regulatory_severity=0.4,
    ),
    "Hospital chain": dict(
        records_exposed=250,
        detection_time=240,
        response_time=95,
        security_score=45,
        industry=Industry.HEALTHCARE,
        jurisdiction=Jurisdiction.IN,
        regulatory_severity=0.45,
    ),
    "E-commerce platform": dict(
        records_exposed=480,
        detection_time=120,
        response_time=50,
        security_score=60,
        industry=Industry.RETAIL,
        jurisdiction=Jurisdiction.IN,
        regulatory_severity=0.35,
    ),
    "SaaS startup": dict(
        records_exposed=80,
        detection_time=90,
        response_time=40,
        security_score=70,
        industry=Industry.TECHNOLOGY,
        jurisdiction=Jurisdiction.IN,
        regulatory_severity=0.3,
    ),
    "EU fintech (GDPR)": dict(
        records_exposed=200,
        detection_time=150,
        response_time=60,
        security_score=65,
        industry=Industry.FINANCIAL,
        jurisdiction=Jurisdiction.EU,
        regulatory_severity=0.4,
    ),
    "Custom": {},
}

_CSS = """
<style>
  .stApp { background: radial-gradient(1200px 600px at 80% -10%,
           #16304a 0%, #0b1220 45%, #070b14 100%); }
  .bl-kicker { color:#5eead4; letter-spacing:.22em; text-transform:uppercase;
               font-size:.72rem; font-weight:700; }
  .bl-title { font-size:2.4rem; font-weight:800; line-height:1.05; margin:.2rem 0;
              background:linear-gradient(90deg,#fff,#9fb4cc); -webkit-background-clip:text;
              -webkit-text-fill-color:transparent; }
  .bl-sub { color:#94a3b8; font-size:1rem; max-width:64ch; }
  .bl-card { background:rgba(148,163,184,.06); border:1px solid rgba(148,163,184,.16);
             border-radius:16px; padding:1.1rem 1.25rem; }
  .bl-big { font-size:2.5rem; font-weight:800; color:#fff; line-height:1; }
  .bl-band { color:#94a3b8; font-size:.92rem; margin-top:.35rem; }
  .bl-pill { display:inline-block; padding:.2rem .6rem; border-radius:999px; font-size:.72rem;
             font-weight:700; background:rgba(94,234,212,.12); color:#5eead4;
             border:1px solid rgba(94,234,212,.3); }
  [data-testid="stMetricValue"] { font-size:1.5rem; }
  footer { visibility:hidden; }
</style>
"""


def _profile_from_sidebar() -> tuple[OrgProfile, str]:
    with st.sidebar:
        st.markdown("### 🏢 Organisation profile")
        preset_name = st.selectbox("Start from a preset", list(PRESETS))
        preset = PRESETS[preset_name]

        industry = st.selectbox(
            "Industry",
            list(Industry),
            index=list(Industry).index(preset.get("industry", Industry.SERVICES)),
            format_func=lambda e: e.value.title(),
        )
        jurisdiction = st.selectbox(
            "Jurisdiction",
            list(Jurisdiction),
            index=list(Jurisdiction).index(preset.get("jurisdiction", Jurisdiction.IN)),
            format_func=lambda e: {"IN": "India (DPDP)", "EU": "EU (GDPR)", "US": "US"}.get(
                e.value, e.value
            ),
        )
        records = st.slider(
            "Records exposed (thousands)", 10, 500, int(preset.get("records_exposed", 250))
        )
        detection = st.slider(
            "Detection time (days)", 10, 295, int(preset.get("detection_time", 160))
        )
        response = st.slider(
            "Containment time (days)", 6, 120, int(preset.get("response_time", 58))
        )
        security = st.slider(
            "Security maturity (0-100)", 20, 95, int(preset.get("security_score", 60))
        )
        severity = st.slider(
            "Regulatory severity (0-1)",
            0.0,
            1.0,
            float(preset.get("regulatory_severity", 0.35)),
            0.05,
            help="How egregious / non-compliant the breach is judged to be.",
        )
        st.caption(f"BreachLens v{__version__} · benchmarks: {IBM_2024} · figures illustrative")

    profile = OrgProfile(
        records_exposed=records,
        detection_time=detection,
        response_time=response,
        security_score=security,
        industry=industry,
        jurisdiction=jurisdiction,
        regulatory_severity=severity,
    )
    return profile, preset_name


def _breakdown_chart(c) -> go.Figure:
    fig = go.Figure()
    parts = [
        ("Recovery", c.recovery, ACCENT),
        ("Lost business", c.lost_business, WARN),
        ("Regulatory fine", c.regulatory, DANGER),
    ]
    for name, value, color in parts:
        fig.add_trace(
            go.Bar(
                y=["Breach cost"],
                x=[value],
                name=name,
                orientation="h",
                marker_color=color,
                hovertemplate=f"{name}: %{{x:.2f}}<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        height=130,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=INK,
        legend=dict(orientation="h", y=-0.4),
        xaxis=dict(title=f"{c.benchmark.currency_symbol} {c.benchmark.unit_label}"),
        yaxis=dict(showticklabels=False),
    )
    return fig


def _exceedance_chart(mc) -> go.Figure:
    losses, probs = mc.exceedance_curve()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=losses,
            y=probs * 100,
            mode="lines",
            line=dict(color=ACCENT, width=3),
            fill="tozeroy",
            fillcolor="rgba(94,234,212,.12)",
            name="P(loss exceeds)",
        )
    )
    for pct, val, color in [(10, mc.p90, WARN), (5, mc.p95, DANGER)]:
        fig.add_vline(
            x=val,
            line=dict(color=color, dash="dash"),
            annotation_text=f"P{100 - pct}",
            annotation_font_color=color,
        )
    fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=INK,
        xaxis_title=f"Breach cost ({mc.currency_symbol} {mc.unit_label})",
        yaxis_title="Probability of exceeding (%)",
    )
    return fig


def _histogram(mc) -> go.Figure:
    fig = go.Figure(go.Histogram(x=mc.samples, nbinsx=50, marker_color="rgba(94,234,212,.55)"))
    fig.add_vline(x=mc.p50, line=dict(color=INK, dash="dot"), annotation_text="P50")
    fig.add_vline(x=mc.p90, line=dict(color=DANGER, dash="dash"), annotation_text="P90")
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=INK,
        xaxis_title=f"Simulated cost ({mc.currency_symbol} {mc.unit_label})",
        yaxis_title="Simulations",
    )
    return fig


def _sweep_chart(df, current_value, spec, c) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["value"],
            y=df["total"],
            mode="lines",
            line=dict(color=ACCENT, width=3),
            name="Total cost",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["value"],
            y=df["regulatory"],
            mode="lines",
            line=dict(color=DANGER, width=1.5, dash="dot"),
            name="Regulatory",
        )
    )
    yval = float(np.interp(current_value, df["value"], df["total"]))
    fig.add_trace(
        go.Scatter(
            x=[current_value],
            y=[yval],
            mode="markers",
            marker=dict(color="#fff", size=11, line=dict(color=DANGER, width=2)),
            name="Your input",
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=INK,
        legend=dict(orientation="h", y=1.12),
        xaxis_title=f"{spec.label} ({spec.unit})",
        yaxis_title=f"Cost ({c.benchmark.currency_symbol} {c.benchmark.unit_label})",
    )
    return fig


def render() -> None:
    st.set_page_config(
        page_title="BreachLens · Data Breach Cost Predictor", page_icon="🛡️", layout="wide"
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    profile, _ = _profile_from_sidebar()
    c = estimate_cost(profile)

    st.markdown(
        """
        <div class="bl-kicker">Cyber Risk Quantification</div>
        <div class="bl-title">BreachLens</div>
        <div class="bl-sub">What a data breach would cost — grounded in IBM industry
        benchmarks and real regulatory penalties (DPDP&nbsp;Act&nbsp;2023, GDPR), with
        Monte&nbsp;Carlo uncertainty and security-investment ROI.</div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    left, right = st.columns([1, 1])
    with left:
        st.markdown(
            f"""
            <div class="bl-card">
              <span class="bl-pill">Expected breach cost · {profile.industry.value.title()}
              · {profile.jurisdiction.value}</span>
              <div class="bl-big" style="margin-top:.6rem">{c.format(c.total)}</div>
              <div class="bl-band">Recovery {c.format(c.recovery)} ·
              Lost business {c.format(c.lost_business)} ·
              Regulatory {c.format(c.regulatory)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.plotly_chart(_breakdown_chart(c), width="stretch", config={"displayModeBar": False})

    tab_break, tab_risk, tab_roi, tab_method = st.tabs(
        ["💰 Cost breakdown", "🎲 Risk distribution", "🛠️ Investment ROI", "📚 Methodology"]
    )

    with tab_break:
        st.markdown("#### What drives this estimate")
        d = c.drivers
        cols = st.columns(4)
        cols[0].metric(
            "Size factor",
            f"{d['size_factor']:.2f}×",
            help="Records exposed vs a reference breach (sub-linear scaling).",
        )
        cols[1].metric("Industry", f"{d['industry_multiplier']:.2f}×")
        cols[2].metric(
            "Speed (lifecycle)",
            f"{d['lifecycle_multiplier']:.2f}×",
            help="Detection + containment time vs the 200-day pivot.",
        )
        cols[3].metric("Security posture", f"{d['maturity_multiplier']:.2f}×")
        st.caption(
            "Each factor is a published industry effect applied to the regional "
            "average breach cost. Lower multipliers reduce cost."
        )

    with tab_risk:
        mc = simulate(profile, n=12000)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Expected", mc.format(mc.mean))
        m2.metric("Median (P50)", mc.format(mc.p50))
        m3.metric("P90", mc.format(mc.p90))
        m4.metric("P95 · tail risk", mc.format(mc.p95))
        st.markdown("#### Loss-exceedance curve")
        st.caption(
            "The headline cyber-risk view: the probability that the breach cost "
            "exceeds a given amount. Plan capital against the tail, not the average."
        )
        st.plotly_chart(_exceedance_chart(mc), width="stretch", config={"displayModeBar": False})
        st.plotly_chart(_histogram(mc), width="stretch", config={"displayModeBar": False})

    with tab_roi:
        st.markdown("#### Which security investments pay off?")
        chosen = st.multiselect(
            "Controls to add",
            list(CONTROL_CATALOG),
            format_func=lambda k: (
                f"{CONTROL_CATALOG[k].name} (−{CONTROL_CATALOG[k].cost_reduction:.0%})"
            ),
        )
        investment = st.number_input(
            f"Annual investment ({c.benchmark.currency_symbol} {c.benchmark.unit_label})",
            min_value=0.0,
            value=round(c.total * 0.02, 2),
            step=0.5,
        )
        if chosen:
            case = build_investment_case(profile, chosen, investment=investment)
            r1, r2, r3 = st.columns(3)
            r1.metric(
                "Breach cost saved",
                c.format(case.gross_savings),
                help="Reduction in cost if a breach occurs.",
            )
            r2.metric(
                "Risk-adjusted saving / yr",
                c.format(case.expected_savings),
                delta=f"{case.breach_probability:.0%} annual breach prob",
            )
            roi_txt = "∞" if case.roi == float("inf") else f"{case.roi:.1f}×"
            pay_txt = "—" if case.payback_years == float("inf") else f"{case.payback_years:.1f} yr"
            r3.metric("ROI", roi_txt, delta=f"payback {pay_txt}")
        else:
            st.info("Select one or more controls to see the business case.")

        st.markdown("#### Sensitivity — how cost responds to one factor")
        from breachlens.config import FEATURES

        feat_label = st.selectbox("Vary", [f.label for f in FEATURES])
        spec = next(f for f in FEATURES if f.label == feat_label)
        df = sweep(profile, spec.name, n=40)
        st.plotly_chart(
            _sweep_chart(df, profile.to_features()[spec.name], spec, c),
            width="stretch",
            config={"displayModeBar": False},
        )

    with tab_method:
        st.markdown(
            """
            **How the estimate is built.** Breach cost is *not* predicted by a black box.
            It is a transparent transformation of published industry figures:

            ```
            cost = regional average breach cost
                 × size factor (records, sub-linear)
                 × industry multiplier
                 × lifecycle multiplier (detection + containment speed)
                 × security-posture multiplier
                 + regulatory penalty (DPDP / GDPR / US)
            ```

            **Uncertainty.** A Monte Carlo simulation samples the regional average, a
            residual shock, and regulatory severity to produce a *distribution* and the
            loss-exceedance curve — the same shape of output as the FAIR standard, not a
            single false-precise number.

            **Sources.**
            - IBM *Cost of a Data Breach Report 2024* — average cost, per-record cost,
              time-to-contain effect, industry ranking, cost mitigators/amplifiers.
            - **DPDP Act 2023** (India) — fines up to **₹250 crore** for failure to
              prevent a breach. **GDPR** Art. 83(5) — up to €20M or 4% of turnover.
            - Verizon **DBIR** — relative breach frequency by industry.

            **Optional ML second opinion.** A scikit-learn model can be trained on real
            breach records you supply (`breachlens train`); the bundled synthetic dataset
            is a labelled demo seed only.

            > ⚠️ **Decision-support estimates, not actuarial or legal figures.** All
            > constants are illustrative and overridable. Do not use as the sole basis for
            > insurance, financial, or legal decisions.
            """
        )


# Streamlit-cloud / cached facade (kept for parity with other entrypoints).
def get_lens() -> BreachLens:
    return BreachLens()
