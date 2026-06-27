"""BreachLens interactive web app (Streamlit).

A control-room style cyber-risk console: enter an organisation's breach profile,
get a calibrated cost estimate with an uncertainty band, see why, and simulate which
security investments cut the cost the most.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from breachlens import __version__
from breachlens.config import FEATURES, REGIONS
from breachlens.data import load_dataset
from breachlens.predictor import BreachLens
from breachlens.schema import BreachProfile

ACCENT = "#5eead4"
DANGER = "#fb7185"
GOOD = "#34d399"
INK = "#e2e8f0"
MUTED = "#94a3b8"

PRESETS: dict[str, dict[str, float]] = {
    "Mid-size bank": {
        "records_exposed": 350,
        "detection_time": 180,
        "response_time": 70,
        "security_score": 55,
    },
    "Healthcare provider": {
        "records_exposed": 220,
        "detection_time": 240,
        "response_time": 95,
        "security_score": 45,
    },
    "E-commerce platform": {
        "records_exposed": 480,
        "detection_time": 120,
        "response_time": 50,
        "security_score": 65,
    },
    "IT services firm": {
        "records_exposed": 150,
        "detection_time": 90,
        "response_time": 40,
        "security_score": 75,
    },
    "Custom": {},
}

_CSS = """
<style>
  .stApp { background: radial-gradient(1200px 600px at 80% -10%,
           #16304a 0%, #0b1220 45%, #070b14 100%); }
  .bl-hero { padding: 0.4rem 0 1.1rem 0; }
  .bl-kicker { color: #5eead4; letter-spacing: .22em; text-transform: uppercase;
               font-size: .72rem; font-weight: 700; }
  .bl-title { font-size: 2.5rem; font-weight: 800; line-height: 1.05; margin: .25rem 0;
              background: linear-gradient(90deg,#ffffff,#9fb4cc); -webkit-background-clip: text;
              -webkit-text-fill-color: transparent; }
  .bl-sub { color: #94a3b8; font-size: 1.02rem; max-width: 60ch; }
  .bl-card { background: rgba(148,163,184,.06); border: 1px solid rgba(148,163,184,.16);
             border-radius: 16px; padding: 1.1rem 1.25rem; }
  .bl-big { font-size: 2.6rem; font-weight: 800; color: #fff; line-height: 1; }
  .bl-band { color: #94a3b8; font-size: .95rem; margin-top: .35rem; }
  .bl-pill { display:inline-block; padding:.2rem .6rem; border-radius:999px; font-size:.72rem;
             font-weight:700; background:rgba(94,234,212,.12); color:#5eead4;
             border:1px solid rgba(94,234,212,.3); }
  [data-testid="stMetricValue"] { font-size: 1.6rem; }
  footer { visibility: hidden; }
</style>
"""


@st.cache_resource(show_spinner="Training BreachLens model…")
def get_lens(region_code: str) -> BreachLens:
    return BreachLens.load_or_train(region_code=region_code)


@st.cache_data
def dataset_stats() -> dict[str, float]:
    df = load_dataset()
    return {
        "max_cost": float(df["breach_cost"].max()),
        "mean_cost": float(df["breach_cost"].mean()),
    }


def _cost_gauge(result, region, axis_max: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=result.expected_cost,
            number={"prefix": region.currency_symbol, "font": {"size": 40, "color": INK}},
            gauge={
                "axis": {"range": [0, axis_max], "tickcolor": MUTED},
                "bar": {"color": ACCENT, "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, result.lower], "color": "rgba(148,163,184,.10)"},
                    {"range": [result.lower, result.upper], "color": "rgba(94,234,212,.18)"},
                    {"range": [result.upper, axis_max], "color": "rgba(148,163,184,.06)"},
                ],
                "threshold": {"line": {"color": DANGER, "width": 3}, "value": result.expected_cost},
            },
        )
    )
    fig.update_layout(
        height=260,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=INK,
    )
    return fig


def _waterfall(contributions: pd.DataFrame, region) -> go.Figure:
    base = contributions.attrs.get("baseline_cost", 0.0)
    labels = ["Typical breach", *contributions["label"], "This breach"]
    measures = ["absolute", *["relative"] * len(contributions), "total"]
    values = [base, *contributions["contribution"], 0]
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            connector={"line": {"color": "rgba(148,163,184,.4)"}},
            increasing={"marker": {"color": DANGER}},
            decreasing={"marker": {"color": GOOD}},
            totals={"marker": {"color": ACCENT}},
        )
    )
    fig.update_layout(
        height=360,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=INK,
        yaxis_title=f"Cost ({region.currency_symbol} {region.unit_label})",
        xaxis={"tickangle": -15},
    )
    return fig


def _sweep_chart(
    sweep: pd.DataFrame, current_value: float, current_cost: float, spec, region
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sweep["value"],
            y=sweep["upper"],
            mode="lines",
            line={"width": 0},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sweep["value"],
            y=sweep["lower"],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(94,234,212,.14)",
            hoverinfo="skip",
            name="90% interval",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sweep["value"],
            y=sweep["expected"],
            mode="lines",
            line={"color": ACCENT, "width": 3},
            name="Expected cost",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[current_value],
            y=[current_cost],
            mode="markers",
            marker={"color": DANGER, "size": 12, "line": {"color": "#fff", "width": 1}},
            name="Your input",
        )
    )
    fig.update_layout(
        height=340,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=INK,
        xaxis_title=f"{spec.label} ({spec.unit})",
        yaxis_title=f"Cost ({region.currency_symbol} {region.unit_label})",
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    return fig


def _sidebar() -> tuple[BreachProfile, str, float]:
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        region_code = st.selectbox(
            "Display region",
            list(REGIONS),
            format_func=lambda c: REGIONS[c].name,
            help="The model trains in ₹ crore; other regions convert for display (approx.).",
        )
        confidence = st.select_slider("Prediction interval", options=[0.8, 0.9, 0.95], value=0.9)

        st.markdown("### 🏢 Organisation profile")
        preset_name = st.selectbox("Start from a preset", list(PRESETS))
        preset = PRESETS[preset_name]

        values: dict[str, float] = {}
        for spec in FEATURES:
            default = float(preset.get(spec.name, spec.default))
            values[spec.name] = st.slider(
                f"{spec.label} ({spec.unit})",
                min_value=float(spec.min),
                max_value=float(spec.max),
                value=default,
                help=spec.help,
            )
        st.caption(f"BreachLens v{__version__} · synthetic data calibrated to IBM India figures")

    return BreachProfile(**values), region_code, confidence


def render() -> None:
    st.set_page_config(
        page_title="BreachLens · Cyber Breach Cost Estimator", page_icon="🛡️", layout="wide"
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    profile, region_code, confidence = _sidebar()
    lens = get_lens(region_code)
    region = lens.region
    stats = dataset_stats()
    axis_max = round(stats["max_cost"] * 1.25, 0)

    result = lens.predict(profile, confidence=confidence)

    st.markdown(
        """
        <div class="bl-hero">
          <div class="bl-kicker">Cyber Risk Quantification</div>
          <div class="bl-title">BreachLens</div>
          <div class="bl-sub">Estimate what a data breach would cost — with an honest
          uncertainty band — and prove which security investments pay for themselves.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 1])
    with left:
        pct = int(confidence * 100)
        expected = lens.format(result.expected_cost)
        low, high = lens.format(result.lower), lens.format(result.upper)
        st.markdown(
            f"""
            <div class="bl-card">
              <span class="bl-pill">Expected breach cost · {pct}% interval</span>
              <div class="bl-big" style="margin-top:.6rem">{expected}</div>
              <div class="bl-band">Likely range&nbsp; {low} &nbsp;–&nbsp; {high}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        m = lens.model.metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Model", lens.model.name)
        c2.metric("Test R²", f"{m['r2']:.3f}")
        c3.metric("Avg. error (MAE)", lens.format(m["mae"]))
    with right:
        st.plotly_chart(
            _cost_gauge(result, region, axis_max), width="stretch", config={"displayModeBar": False}
        )

    tab_why, tab_whatif, tab_model = st.tabs(
        ["🔍 Why this estimate", "🧪 What-if simulator", "📊 Model card"]
    )

    with tab_why:
        st.markdown("#### How this breach compares to a *typical* one")
        st.caption(
            "Each bar shows how much a factor pushes cost above (red) or below (green) "
            "a baseline breach with average characteristics."
        )
        st.plotly_chart(
            _waterfall(lens.explain(profile), region),
            width="stretch",
            config={"displayModeBar": False},
        )

    with tab_whatif:
        st.markdown("#### Simulate a security improvement")
        st.caption("Adjust the *target* posture and BreachLens estimates the cost reduction.")
        cols = st.columns(len(FEATURES))
        changes: dict[str, float] = {}
        current = profile.to_features()
        for col, spec in zip(cols, FEATURES, strict=False):
            with col:
                new_val = st.number_input(
                    f"{spec.label}",
                    min_value=float(spec.min),
                    max_value=float(spec.max),
                    value=float(current[spec.name]),
                    key=f"wi_{spec.name}",
                )
                if new_val != current[spec.name]:
                    changes[spec.name] = new_val

        if changes:
            scenario = lens.what_if(profile, changes, confidence=confidence)
            s1, s2, s3 = st.columns(3)
            s1.metric("Baseline cost", lens.format(scenario.baseline.expected_cost))
            s2.metric("Improved cost", lens.format(scenario.adjusted.expected_cost))
            s3.metric(
                "Estimated savings",
                lens.format(scenario.savings),
                delta=f"{-scenario.savings_pct:.0%}",
            )
        else:
            st.info("Change at least one target value above to estimate savings.")

        st.markdown("#### Sensitivity curve")
        feat_label = st.selectbox("Show cost vs", [f.label for f in FEATURES])
        spec = next(f for f in FEATURES if f.label == feat_label)
        sweep = lens.sweep(profile, spec.name, n=40, confidence=confidence)
        st.plotly_chart(
            _sweep_chart(sweep, current[spec.name], result.expected_cost, spec, region),
            width="stretch",
            config={"displayModeBar": False},
        )

    with tab_model:
        st.markdown("#### Model benchmark (5-fold cross-validation)")
        board = lens.model.scoreboard.rename(
            columns={
                "model": "Model",
                "r2": "R²",
                "r2_std": "R² ±",
                "mae": "MAE",
                "mae_std": "MAE ±",
            }
        )
        st.dataframe(
            board.style.format(
                {"R²": "{:.3f}", "R² ±": "{:.3f}", "MAE": "{:.2f}", "MAE ±": "{:.2f}"}
            ),
            width="stretch",
            hide_index=True,
        )
        st.markdown("#### Global feature importance (permutation)")
        imp = lens.importance()[["label", "importance_norm"]].rename(
            columns={"label": "Factor", "importance_norm": "Share of importance"}
        )
        st.dataframe(
            imp.style.format({"Share of importance": "{:.1%}"}), width="stretch", hide_index=True
        )
        st.markdown(
            f"""
            **Method.** BreachLens benchmarks four algorithms and selects the strongest by
            cross-validated R² (here: **{lens.model.name}**). Intervals use *split conformal
            prediction* — a distribution-free guarantee, not a Gaussian assumption.

            **Data.** {lens.model.n_train} training records from a transparent synthetic
            generator calibrated to the IBM *Cost of a Data Breach* report for India
            (real average ≈ ₹19.5 crore). Synthetic data is used because real per-company
            breach costs are confidential.

            **Disclaimer.** Estimates are directional decision-support, not actuarial
            figures. Do not use as the sole basis for insurance or financial decisions.
            """
        )
