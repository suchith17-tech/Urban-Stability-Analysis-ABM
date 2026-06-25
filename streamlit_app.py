"""
streamlit_app.py — Urban Stability ABM Dashboard (Phase 8)
============================================================
4-tab research dashboard with Insight Engine:
  Tab 1 — 🏙️  City Overview      (KPIs + insights + profile)
  Tab 2 — 📊  Experiment Compare  (scenario selector + Plotly charts + insights)
  Tab 3 — 🗺️  Cross-City Analysis (heatmap + ranking)
  Tab 4 — ▶️  Live Simulation     (custom run + live insights)

Paths: all relative to this file's location — no hardcoded user paths.
Run:   streamlit run streamlit_app.py
"""
import sys
import copy
import pathlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Make project root importable regardless of CWD ──
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from data.scripts.config_loader import load_city_config, CITIES
from model.urban_model import UrbanStabilityModel
from dashboard.insight_engine import generate_insights, generate_verdict

# ─────────────────────────────────────────────────────────────────────────────
# PATHS  (all relative — portable across machines)
# ─────────────────────────────────────────────────────────────────────────────
EXPERIMENTS_DIR = ROOT / "results" / "experiments"
FIGURES_DIR     = ROOT / "results" / "figures"

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & DARK THEME CSS
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Urban Stability ABM",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #0d1117; color: #e6edf3;
}
[data-testid="stSidebar"] {
    background-color: #161b22; border-right: 1px solid #30363d;
}
.kpi-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 18px 20px; text-align: center;
}
.kpi-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
.kpi-value { font-size: 30px; font-weight: 700; margin: 6px 0 2px; }
.kpi-delta { font-size: 12px; }
.badge-green  { color: #3fb950; font-weight: 700; }
.badge-yellow { color: #d29922; font-weight: 700; }
.badge-red    { color: #f85149; font-weight: 700; }
.section-head {
    font-size: 17px; font-weight: 600; color: #58a6ff;
    border-left: 3px solid #58a6ff; padding-left: 10px; margin: 18px 0 10px;
}
/* Insight cards */
.insight-info     { background:#0d419d22; border-left:4px solid #58a6ff;
                    border-radius:8px; padding:12px 16px; margin:8px 0; }
.insight-warning  { background:#9e6a0322; border-left:4px solid #d29922;
                    border-radius:8px; padding:12px 16px; margin:8px 0; }
.insight-critical { background:#f8514922; border-left:4px solid #f85149;
                    border-radius:8px; padding:12px 16px; margin:8px 0; }
.insight-title    { font-weight:600; font-size:14px; margin-bottom:4px; }
.insight-body     { font-size:13px; color:#c9d1d9; line-height:1.5; }
[data-testid="stTabs"] button { color: #8b949e !important; font-weight: 500; }
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #58a6ff !important; border-bottom: 2px solid #58a6ff;
}
label { color: #c9d1d9 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
CITY_COLORS = {
    "Bengaluru":        "#e74c3c",
    "Mysuru":           "#3498db",
    "Mangaluru":        "#2ecc71",
    "Hubballi-Dharwad": "#f39c12",
    "Belagavi":         "#9b59b6",
}
SCENARIO_LABELS = {
    "exp1_baseline":        "Baseline (No Shocks)",
    "exp2_flood":           "Flood Shock",
    "exp3_drought":         "Drought Shock",
    "exp4_economic":        "Economic Shock",
    "exp5a_shock_nopolicy": "All Shocks — No Policy",
    "exp5b_shock_policy":   "All Shocks — With Policy",
    "exp6_combined":        "Combined Stress Test",
}
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(22,27,34,0.8)",
    font=dict(color="#c9d1d9", size=12),
    xaxis=dict(gridcolor="#21262d", showgrid=True),
    yaxis=dict(gridcolor="#21262d", showgrid=True),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#30363d", borderwidth=1),
    margin=dict(l=40, r=20, t=40, b=40),
)

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────
# Columns expected in every scenario CSV
_SCENARIO_COLS = ["step", "city", "USI", "Trust", "S_R", "Gini"]
_EMPTY_SCENARIO = pd.DataFrame(columns=_SCENARIO_COLS)

# Bump this string whenever data files change — forces cache invalidation
_CACHE_VER = "v4-data-added"

@st.cache_data(ttl=3600, show_spinner=False)
def load_scenario(scenario_id: str, _ver: str = _CACHE_VER) -> pd.DataFrame:
    """Load _all_cities.csv for a scenario; return typed empty DF if missing."""
    path = EXPERIMENTS_DIR / scenario_id / "_all_cities.csv"
    if path.exists():
        df = pd.read_csv(path)
        for col in _SCENARIO_COLS:
            if col not in df.columns:
                df[col] = None
        return df
    return _EMPTY_SCENARIO.copy()

@st.cache_data(ttl=3600, show_spinner=False)
def load_master_summary(_ver: str = _CACHE_VER) -> pd.DataFrame:
    path = EXPERIMENTS_DIR / "MASTER_SUMMARY.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

# Force-flush any stale empty-DataFrame cache from before data files existed
if "cache_cleared" not in st.session_state:
    st.cache_data.clear()
    st.session_state["cache_cleared"] = True

def stability_grade(usi: float) -> str:
    if usi >= 0.85:
        return '<span class="badge-green">🟢 Stable</span>'
    elif usi >= 0.65:
        return '<span class="badge-yellow">🟡 Moderate</span>'
    return '<span class="badge-red">🔴 Fragile</span>'

def render_insights(insights: list[dict]):
    """Render insight cards to Streamlit."""
    for ins in insights:
        css = f"insight-{ins['level']}"
        st.markdown(
            f'<div class="{css}">'
            f'<div class="insight-title">{ins["icon"]} {ins["title"]}</div>'
            f'<div class="insight-body">{ins["body"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏙️ Urban Stability ABM")
    st.markdown("**Karnataka, India · 5 Cities · 24 Months**")
    st.markdown("---")
    st.caption("**USI Formula:**")
    st.caption("USI = 0.25·S_R + 0.25·C + 0.25·S_I + 0.25·S_O")
    st.caption("S_R = 0.4·food + 0.4·water + 0.2·elec")
    st.caption("Gini = consumption-satisfaction inequality")
    st.markdown("---")
    st.caption("📂 Results: `results/experiments/`")
    st.caption("🖼️ Figures: `results/figures/`")
    data_ok = (EXPERIMENTS_DIR / "MASTER_SUMMARY.csv").exists()
    if data_ok:
        st.success("✅ Master summary loaded")
    else:
        st.error("❌ Run `11_run_experiments.py` first")

    # Per-scenario data availability (helps diagnose Cloud file issues)
    st.markdown("---")
    st.caption("**Scenario data files:**")
    for sid, slabel in [
        ("exp1_baseline",        "Baseline"),
        ("exp2_flood",           "Flood"),
        ("exp3_drought",         "Drought"),
        ("exp4_economic",        "Economic"),
        ("exp5a_shock_nopolicy", "All Shocks (no policy)"),
        ("exp5b_shock_policy",   "All Shocks (with policy)"),
    ]:
        p = EXPERIMENTS_DIR / sid / "_all_cities.csv"
        icon = "✅" if p.exists() else "❌"
        st.caption(f"{icon} {slabel}")

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🏙️  City Overview",
    "📊  Experiment Compare",
    "🗺️  Cross-City Analysis",
    "▶️  Live Simulation",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CITY OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-head">City Overview — Baseline Performance</div>',
                unsafe_allow_html=True)

    city = st.selectbox("Select City", CITIES, key="t1_city")
    summary = load_master_summary()
    baseline_df = load_scenario("exp1_baseline")

    if summary.empty or baseline_df.empty:
        st.warning("⚠️ Run `11_run_experiments.py` to generate experiment data first.")
    else:
        row = summary[(summary["scenario"] == "exp1_baseline") & (summary["city"] == city)]
        if row.empty:
            st.info(f"No baseline data found for {city}. Run 11_run_experiments.py first.")
        else:
            r = row.iloc[0]
            final_usi   = float(r["final_USI"])
            final_gini  = float(r["final_Gini"])
            final_trust = float(r["final_Trust"])
            min_usi     = float(r["min_USI"])
            final_sr    = float(r.get("final_SR", 0.75))

            # KPI Cards
            c1, c2, c3, c4 = st.columns(4)
            cards = [
                (c1, "Final USI", f"{final_usi:.3f}", stability_grade(final_usi), "#58a6ff"),
                (c2, "Final Trust", f"{final_trust:.3f}",
                 '<span style="color:#8b949e">Cooperation index</span>',
                 "#3fb950" if final_trust > 0.5 else "#f85149"),
                (c3, "Consumption Gini", f"{final_gini:.4f}",
                 '<span style="color:#8b949e">Resource inequality</span>', "#d29922"),
                (c4, "Worst Month USI", f"{min_usi:.3f}", stability_grade(min_usi), "#f85149"),
            ]
            for col, label, val, delta_html, color in cards:
                with col:
                    st.markdown(
                        f'<div class="kpi-card">'
                        f'<div class="kpi-label">{label}</div>'
                        f'<div class="kpi-value" style="color:{color}">{val}</div>'
                        f'<div class="kpi-delta">{delta_html}</div>'
                        f'</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Verdict
            verdict = generate_verdict(city, "exp1_baseline", final_usi)
            st.markdown(f"**Research Verdict:** {verdict}")
            st.markdown("---")

            # Insights
            st.markdown('<div class="section-head">🧠 Insight Engine</div>', unsafe_allow_html=True)
            insights = generate_insights(
                city=city, scenario_id="exp1_baseline",
                final_usi=final_usi, min_usi=min_usi,
                final_trust=final_trust, final_gini=final_gini, final_sr=final_sr,
            )
            render_insights(insights)

            st.markdown("---")

            # Chart — use baseline_df (already loaded above)
            city_df = baseline_df[baseline_df["city"] == city].sort_values("step")
            if not city_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=city_df["step"], y=city_df["USI"], name="USI",
                    mode="lines", line=dict(color=CITY_COLORS[city], width=3),
                    fill="tozeroy",
                    fillcolor=f"rgba({int(CITY_COLORS[city][1:3],16)},"
                               f"{int(CITY_COLORS[city][3:5],16)},"
                               f"{int(CITY_COLORS[city][5:7],16)},0.1)",
                ))
                fig.add_trace(go.Scatter(
                    x=city_df["step"], y=city_df["Trust"], name="Trust",
                    mode="lines", line=dict(color="#3fb950", width=2, dash="dash"),
                ))
                fig.add_trace(go.Scatter(
                    x=city_df["step"], y=city_df["S_R"], name="S_R (Resource)",
                    mode="lines", line=dict(color="#d29922", width=2, dash="dot"),
                ))
                fig.add_trace(go.Scatter(
                    x=city_df["step"], y=city_df["Gini"], name="Gini (Inequality)",
                    mode="lines", line=dict(color="#a371f7", width=2, dash="dot"),
                ))
                fig.add_hline(y=0.5, line_dash="dot", line_color="#f85149",
                              annotation_text="Collapse threshold (0.5)")
                fig.update_layout(
                    title=f"{city} — Baseline Stability Metrics (24 Months)",
                    xaxis_title="Month", yaxis_title="Score",
                    yaxis_range=[0, 1.05], **PLOTLY_LAYOUT)
                st.plotly_chart(fig, width='stretch')

            # City profile (always shown — from config, no CSV needed)
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown('<div class="section-head">City Profile</div>', unsafe_allow_html=True)
                cfg = load_city_config(city)
                st.table(pd.DataFrame.from_dict({
                    "Population":        f"{cfg['population']:,}",
                    "Households":        f"{cfg['households']:,}",
                    "Avg. HH Size":      f"{cfg['avg_household_size']:.1f}",
                    "Literacy Rate":     f"{cfg['literacy_rate']*100:.0f}%",
                    "Simulation Agents": str(cfg["num_agents"]),
                }, orient="index", columns=["Value"]))
            with col_b:
                st.markdown('<div class="section-head">Income Group Distribution</div>',
                            unsafe_allow_html=True)
                cfg = load_city_config(city)
                groups = cfg["agent_groups"]
                fig_pie = go.Figure(go.Pie(
                    labels=[g["name"].replace("_", " ").title() for g in groups],
                    values=[g["fraction"] * 100 for g in groups],
                    hole=0.45,
                    marker=dict(colors=["#f85149", "#d29922", "#3fb950"]),
                ))
                fig_pie.update_layout(
                    showlegend=True,
                    **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")}
                )
                st.plotly_chart(fig_pie, width='stretch')


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXPERIMENT COMPARE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-head">Experiment Comparison</div>', unsafe_allow_html=True)

    col_sel1, col_sel2 = st.columns([1, 1])
    with col_sel1:
        city_cmp = st.selectbox("City", CITIES, key="t2_city")
    with col_sel2:
        scen_sel = st.multiselect(
            "Scenarios to compare",
            list(SCENARIO_LABELS.keys()),
            default=["exp1_baseline", "exp2_flood", "exp5a_shock_nopolicy", "exp5b_shock_policy"],
            format_func=lambda x: SCENARIO_LABELS[x],
        )

    if not scen_sel:
        st.info("Select at least one scenario above.")
    else:
        scen_colors = px.colors.qualitative.Plotly
        summary = load_master_summary()

        # USI comparison
        fig_usi = go.Figure()
        for i, sid in enumerate(scen_sel):
            df = load_scenario(sid)
            cdf = df[df["city"] == city_cmp].sort_values("step")
            if cdf.empty:
                continue
            fig_usi.add_trace(go.Scatter(
                x=cdf["step"], y=cdf["USI"],
                name=SCENARIO_LABELS[sid], mode="lines",
                line=dict(color=scen_colors[i % len(scen_colors)], width=2.5),
            ))
        fig_usi.add_hline(y=0.5, line_dash="dot", line_color="#f85149",
                          annotation_text="Collapse (0.5)")
        fig_usi.update_layout(
            title=f"{city_cmp} — USI Over 24 Months",
            xaxis_title="Month", yaxis_title="USI",
            yaxis_range=[0.3, 1.05], **PLOTLY_LAYOUT)
        st.plotly_chart(fig_usi, width='stretch')

        # Trust + Gini side by side
        col_t, col_g = st.columns(2)
        fig_trust = go.Figure()
        fig_gini  = go.Figure()
        for i, sid in enumerate(scen_sel):
            df  = load_scenario(sid)
            cdf = df[df["city"] == city_cmp].sort_values("step")
            if cdf.empty:
                continue
            color = scen_colors[i % len(scen_colors)]
            fig_trust.add_trace(go.Scatter(
                x=cdf["step"], y=cdf["Trust"],
                name=SCENARIO_LABELS[sid], mode="lines",
                line=dict(color=color, width=2)))
            fig_gini.add_trace(go.Scatter(
                x=cdf["step"], y=cdf["Gini"],
                name=SCENARIO_LABELS[sid], mode="lines",
                line=dict(color=color, width=2)))

        fig_trust.add_hline(y=0.5, line_dash="dot", line_color="#d29922")
        fig_trust.add_hline(y=0.3, line_dash="dot", line_color="#f85149")
        fig_trust.update_layout(title="Trust Dynamics",
                                 yaxis_range=[-0.05, 1.05], **PLOTLY_LAYOUT)
        fig_gini.update_layout(title="Consumption Inequality (Gini)", **PLOTLY_LAYOUT)
        with col_t:
            st.plotly_chart(fig_trust, width='stretch')
        with col_g:
            st.plotly_chart(fig_gini, width='stretch')

        # ── Insight Engine: scenario-aware ──
        st.markdown('<div class="section-head">🧠 Scenario Insights</div>',
                    unsafe_allow_html=True)
        # Use the most extreme selected scenario for insights
        focus_scen = scen_sel[-1]
        focus_row  = summary[
            (summary["scenario"] == focus_scen) & (summary["city"] == city_cmp)
        ]
        baseline_row = summary[
            (summary["scenario"] == "exp1_baseline") & (summary["city"] == city_cmp)
        ]
        if not focus_row.empty:
            fr = focus_row.iloc[0]
            base_usi = baseline_row.iloc[0]["final_USI"] if not baseline_row.empty else None

            verdict = generate_verdict(city_cmp, focus_scen, fr["final_USI"])
            st.markdown(f"**{SCENARIO_LABELS[focus_scen]}:** {verdict}")

            cmp_insights = generate_insights(
                city=city_cmp, scenario_id=focus_scen,
                final_usi=fr["final_USI"], min_usi=fr["min_USI"],
                final_trust=fr["final_Trust"], final_gini=fr["final_Gini"],
                final_sr=fr.get("final_SR", 0.8),
                baseline_usi=base_usi,
            )
            render_insights(cmp_insights)

        # Policy bar (if both policy scenarios selected)
        if "exp5a_shock_nopolicy" in scen_sel and "exp5b_shock_policy" in scen_sel:
            st.markdown('<div class="section-head">Policy Effectiveness</div>',
                        unsafe_allow_html=True)
            no_pol  = summary[summary["scenario"] == "exp5a_shock_nopolicy"].set_index("city")["final_USI"]
            yes_pol = summary[summary["scenario"] == "exp5b_shock_policy"].set_index("city")["final_USI"]
            deltas  = [yes_pol.get(c, 0) - no_pol.get(c, 0) for c in CITIES]
            fig_bar = go.Figure(go.Bar(
                x=CITIES, y=deltas,
                marker_color=["#3fb950" if d >= 0 else "#f85149" for d in deltas],
                text=[f"+{d:.3f}" if d >= 0 else f"{d:.3f}" for d in deltas],
                textposition="outside",
            ))
            fig_bar.add_hline(y=0, line_color="#8b949e", line_width=1)
            fig_bar.update_layout(
                title="USI Gain from Govt. Schemes (Policy ON − OFF)",
                yaxis_title="USI Delta", **PLOTLY_LAYOUT)
            st.plotly_chart(fig_bar, width='stretch')


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CROSS-CITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-head">Cross-City Stability Analysis</div>',
                unsafe_allow_html=True)

    summary = load_master_summary()
    scen_order = ["exp1_baseline","exp2_flood","exp3_drought",
                  "exp4_economic","exp5a_shock_nopolicy","exp5b_shock_policy"]
    scen_short = ["Baseline","Flood","Drought","Economic","All Shocks\nNo Policy","All Shocks\nWith Policy"]

    if not summary.empty:
        # Interactive heatmap
        pivot = (summary[summary["scenario"].isin(scen_order)]
                 .pivot(index="city", columns="scenario", values="final_USI")
                 .reindex(index=CITIES, columns=scen_order))
        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values, x=scen_short, y=CITIES,
            colorscale="RdYlGn", zmin=0.3, zmax=1.0,
            text=[[f"{v:.3f}" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=13, color="black"),
            colorbar=dict(title="Final USI"),
        ))
        fig_heat.update_layout(
            title="Urban Stability Index — City × Scenario Heatmap (Month 24)",
            **PLOTLY_LAYOUT)
        st.plotly_chart(fig_heat, width='stretch')

        # City ranking table
        st.markdown('<div class="section-head">City Stability Ranking (Baseline)</div>',
                    unsafe_allow_html=True)
        base_rows = (summary[summary["scenario"] == "exp1_baseline"]
                     .sort_values("final_USI", ascending=False)
                     [["city","final_USI","min_USI","final_Gini","final_Trust"]]
                     .copy())
        base_rows["Grade"] = base_rows["final_USI"].apply(
            lambda v: "🟢 Stable" if v >= 0.85 else ("🟡 Moderate" if v >= 0.65 else "🔴 Fragile"))
        base_rows.columns = ["City","Final USI","Min USI","Gini","Trust","Grade"]
        st.dataframe(base_rows.set_index("City"), width='stretch')

        # ── Cross-city insights ──
        st.markdown('<div class="section-head">🧠 Cross-City Research Insights</div>',
                    unsafe_allow_html=True)
        most_fragile = base_rows.iloc[-1]["City"]
        most_stable  = base_rows.iloc[0]["City"]
        best_usi     = base_rows.iloc[0]["Final USI"]
        worst_usi    = base_rows.iloc[-1]["Final USI"]
        st.markdown(
            f'<div class="insight-critical">'
            f'<div class="insight-title">🔴 Most Vulnerable: {most_fragile}</div>'
            f'<div class="insight-body">USI of {worst_usi:.3f} under baseline — lowest among all cities. '
            f'Structural income inequality combined with high non-poor resource consumption '
            f'prevents this city from reaching equitable supply distribution.</div></div>',
            unsafe_allow_html=True)
        st.markdown(
            f'<div class="insight-info">'
            f'<div class="insight-title">🟢 Most Resilient: {most_stable}</div>'
            f'<div class="insight-body">USI of {best_usi:.3f} — highest among all cities. '
            f'Equitable income distribution ensures near-equal resource satisfaction across '
            f'income groups, producing strong baseline stability and rapid shock recovery.</div></div>',
            unsafe_allow_html=True)
        st.markdown(
            '<div class="insight-warning">'
            '<div class="insight-title">⚖️ Policy impact is city-dependent</div>'
            '<div class="insight-body">Karnataka schemes raise USI by +0.14 to +0.20 in 4 of 5 cities '
            'under combined shocks. However, structurally fragile cities cannot be rescued by '
            'policy alone — income composition reform is required for lasting impact.</div></div>',
            unsafe_allow_html=True)

    # Static figures
    st.markdown('<div class="section-head">Analysis Figures</div>', unsafe_allow_html=True)
    col_f1, col_f2 = st.columns(2)
    for col, fname, cap in [
        (col_f1, "05_Vulnerability_min_USI.png", "Worst-Case Vulnerability (Min USI per Shock)"),
        (col_f2, "07_Gini_timeseries.png",        "Consumption Inequality (Gini) Over 24 Months"),
    ]:
        fp = FIGURES_DIR / fname
        if fp.exists():
            with col:
                st.image(str(fp), caption=cap, width='stretch')


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — LIVE SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-head">Live Simulation — Custom Scenario</div>',
                unsafe_allow_html=True)

    col_cfg1, col_cfg2 = st.columns([1, 2])

    with col_cfg1:
        live_city  = st.selectbox("City", CITIES, key="t4_city")
        live_steps = st.radio("Simulation Length", [12, 24],
                              index=1, horizontal=True,
                              help="12 = 1 year (faster) · 24 = 2 years (full recovery)")

        st.markdown("**🌩️ Shock Toggles**")
        en_flood    = st.checkbox("Flood Shock (Jul–Sep)",   value=False)
        en_drought  = st.checkbox("Drought Shock (Mar–May)", value=False)
        en_economic = st.checkbox("Economic Crisis",         value=False)

        st.markdown("**📜 Karnataka Policy Schemes**")
        en_ab = st.checkbox("Anna Bhagya (PDS Rice)",          value=True)
        en_gj = st.checkbox("Gruha Jyothi (Free Electricity)", value=True)
        en_gl = st.checkbox("Gruha Lakshmi (₹2000 Transfer)",  value=True)

        run_live = st.button("🚀 Run Simulation", type="primary", width='stretch')

    with col_cfg2:
        if run_live:
            with st.spinner(f"Simulating {live_city} for {live_steps} months…"):
                cfg = copy.deepcopy(load_city_config(live_city))
                cfg["num_steps"] = live_steps

                # Shock overrides
                for stype in ("flood", "drought", "economic_crisis"):
                    if stype in cfg.get("shock", {}):
                        cfg["shock"][stype]["disabled"] = True
                if en_flood    and "flood"           in cfg.get("shock", {}):
                    cfg["shock"]["flood"]["disabled"]           = False
                if en_drought  and "drought"         in cfg.get("shock", {}):
                    cfg["shock"]["drought"]["disabled"]         = False
                if en_economic and "economic_crisis" in cfg.get("shock", {}):
                    cfg["shock"]["economic_crisis"]["disabled"] = False

                # Policy overrides
                cfg["anna_bhagya"]["enabled"]   = en_ab
                cfg["gruha_jyothi"]["enabled"]  = en_gj
                cfg["gruha_lakshmi"]["enabled"] = en_gl

                model = UrbanStabilityModel(config=cfg)
                rows, prog = [], st.progress(0, text="Running…")
                for step_i in range(live_steps):
                    if not model.running:
                        break
                    model.step()
                    prog.progress((step_i + 1) / live_steps,
                                  text=f"Month {model.current_step}/{live_steps}")
                    rows.append({
                        "step":  model.current_step,
                        "USI":   model.current_usi,
                        "Trust": model.current_C,
                        "S_R":   model.current_S_R,
                        "Gini":  model.current_gini,
                    })
                prog.empty()
                sim_df = pd.DataFrame(rows)

            fr = sim_df.iloc[-1]

            # KPI cards
            k1, k2, k3, k4 = st.columns(4)
            for col_k, label, val, col_hex in [
                (k1, "Final USI",   fr["USI"],   "#58a6ff"),
                (k2, "Final Trust", fr["Trust"], "#3fb950"),
                (k3, "Final Gini",  fr["Gini"],  "#d29922"),
                (k4, "Final S_R",   fr["S_R"],   "#a371f7"),
            ]:
                with col_k:
                    st.markdown(
                        f'<div class="kpi-card">'
                        f'<div class="kpi-label">{label}</div>'
                        f'<div class="kpi-value" style="color:{col_hex}">{val:.3f}</div>'
                        f'</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Live chart
            fig_live = go.Figure()
            for metric, color in [("USI","#58a6ff"),("Trust","#3fb950"),
                                   ("S_R","#d29922"),("Gini","#a371f7")]:
                fig_live.add_trace(go.Scatter(
                    x=sim_df["step"], y=sim_df[metric],
                    name=metric, mode="lines",
                    line=dict(color=color, width=2.5)))
            fig_live.add_hline(y=0.5, line_dash="dot", line_color="#f85149",
                               annotation_text="Collapse (0.5)")
            fig_live.update_layout(
                title=f"{live_city} — Live Simulation ({live_steps} months)",
                xaxis_title="Month", yaxis_title="Score",
                yaxis_range=[-0.05, 1.05], **PLOTLY_LAYOUT)
            st.plotly_chart(fig_live, width='stretch')

            # ── Live Insight Engine ──
            st.markdown('<div class="section-head">🧠 Live Insights</div>',
                        unsafe_allow_html=True)
            scenario_id = (
                "exp5b_shock_policy" if (en_flood or en_drought or en_economic) and en_ab
                else "exp5a_shock_nopolicy" if (en_flood or en_drought or en_economic)
                else "exp1_baseline"
            )
            live_insights = generate_insights(
                city=live_city, scenario_id=scenario_id,
                final_usi=fr["USI"], min_usi=sim_df["USI"].min(),
                final_trust=fr["Trust"], final_gini=fr["Gini"], final_sr=fr["S_R"],
            )
            verdict = generate_verdict(live_city, scenario_id, fr["USI"])
            st.markdown(f"**Verdict:** {verdict}")
            render_insights(live_insights)

            # Download
            st.download_button(
                "📥 Download Run CSV",
                data=sim_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{live_city}_live_run.csv",
                mime="text/csv",
            )
        else:
            st.info("👈 Configure shocks & policies, then click **Run Simulation**.")
            st.markdown('<div class="section-head">Metric Reference</div>',
                        unsafe_allow_html=True)
            st.markdown("""
| Metric | Description | Threshold |
|---|---|---|
| **USI** | Urban Stability Index — composite score | < 0.5 = collapse |
| **Trust (C)** | Mean agent cooperation | < 0.3 = protest risk |
| **S_R** | Resource Sufficiency (food+water+elec) | < 0.7 = scarcity |
| **Gini** | Consumption inequality between income groups | > 0.01 = widening gap |

**Policies available:**
- **Anna Bhagya** — 5 kg free rice/person/month for BPL/AAY households
- **Gruha Jyothi** — Zero electricity bill for households using ≤200 units/month
- **Gruha Lakshmi** — ₹2000/month transfer to female head-of-household (BPL)
""")
