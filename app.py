"""
MediScope Health Analytics - Hospital Inpatient Discharges Dashboard
====================================================================
Streamlit entry point. Run locally with:  streamlit run app.py

Layout
------
Sidebar  : global filters (county, age group, gender, severity, payment type,
           length of stay range, outlier toggle) - they drive every page.
Pages    : Overview | Research Questions | EDA | Data Cleaning | About
Interactivity: per-chart option popovers, 3D camera presets, click-to-filter
               (2D mode) with removable filter chips, and an animated chart.
"""
from functools import partial

import numpy as np
import pandas as pd
import streamlit as st

from src import analysis as an
from src import charts as charts2d
from src import charts3d
from src import config as cfg
from src import interact as ix
from src import styles as ui
from src.cleaning import clean_pipeline, load_raw, raw_charges as get_raw_charges

st.set_page_config(page_title="MediScope | Inpatient Discharges", page_icon="🏥",
                   layout="wide", initial_sidebar_state="expanded")
ui.inject_css()
PLOT_CFG = {"displaylogo": False, "scrollZoom": True}
PLOT_CFG_2D = {"displaylogo": False}


# --------------------------------------------------------------------------- #
# Data (cached: the raw file is read and cleaned once per session/server)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading and cleaning hospital discharge data...")
def get_data():
    raw = load_raw()
    clean, report = clean_pipeline(raw)
    raw_charges = get_raw_charges(raw)
    raw_preview = raw.head(8)
    return clean, report, raw_charges, raw_preview


df_all, report, raw_charges, raw_preview = get_data()


# --------------------------------------------------------------------------- #
# Sidebar filters
# --------------------------------------------------------------------------- #
def options(col):
    vals = df_all[col].dropna().unique()
    if isinstance(df_all[col].dtype, pd.CategoricalDtype):
        return [c for c in df_all[col].cat.categories if c in set(vals)]
    return sorted(vals)


with st.sidebar:
    st.markdown('<div class="ms-side-brand">🏥 Medi<span>Scope</span></div>'
                '<div style="font-size:.8rem;opacity:.75;margin-bottom:10px">Health Analytics · Inpatient insights</div>',
                unsafe_allow_html=True)
    st.markdown("### Filters")
    st.caption("Leave a filter empty to include everything.")
    f_county = st.multiselect("Hospital county", options("county"))
    f_age = st.multiselect("Age group", options("age_group"))
    f_gender = st.multiselect("Gender", options("gender"))
    f_sev = st.multiselect("Severity of illness", options("severity"))
    f_pay = st.multiselect("Payment type", options("payment_type"))
    max_los = int(df_all["length_of_stay"].max())
    f_los = st.slider("Length of stay (days)", 1, max_los, (1, max_los))
    f_out = st.toggle("Exclude extreme charge outliers (IQR)", value=True,
                      help=f"Removes {int(df_all['is_charge_outlier'].sum()):,} records outside the Tukey "
                           f"fence on log charges (${report.outlier_fence[0]:,.0f} - ${report.outlier_fence[1]:,.0f}).")
    st.markdown("### Display")
    use_3d = st.toggle("3D charts", value=True,
                       help="Interactive 3D Plotly charts (drag to rotate, scroll to zoom). "
                            "Turn off for the classic 2D versions.")
    st.markdown("---")
    st.caption(f"Source: NY State SPARCS {cfg.SOURCE_YEAR} (de-identified), random sample of "
               f"{len(df_all):,} discharges.")


@st.cache_data(show_spinner=False)
def apply_filters(county, age, gender, sev, pay, los, drop_outliers):
    d = df_all
    m = pd.Series(True, index=d.index)
    for col, sel in (("county", county), ("age_group", age), ("gender", gender),
                     ("severity", sev), ("payment_type", pay)):
        if sel:
            m &= d[col].isin(sel)
    m &= d["length_of_stay"].between(*los)
    if drop_outliers:
        m &= ~d["is_charge_outlier"]
    return d.loc[m]


CH = charts3d if use_3d else charts2d  # same function names in both modules

df = apply_filters(tuple(f_county), tuple(f_age), tuple(f_gender), tuple(f_sev), tuple(f_pay),
                   tuple(f_los), f_out)

# --------------------------------------------------------------------------- #
# Click-to-filter state (see src/interact.py)
# --------------------------------------------------------------------------- #
st.session_state.setdefault(ix.XF_KEY, {})
st.session_state.setdefault("_xf_keys", {})


def _forget_chart_selections(cols):
    """Drop the stored selection of charts bound to these columns so they reset."""
    for col in cols:
        for key in st.session_state["_xf_keys"].pop(col, set()):
            if key in st.session_state:
                try:
                    del st.session_state[key]
                except Exception:  # widget state may be read-only during a run
                    pass


def _on_select(chart_key, col):
    event = st.session_state.get(chart_key)
    points = event["selection"]["points"] if event else []
    vals = ix.points_to_values(points)
    xf = dict(st.session_state[ix.XF_KEY])
    if vals:
        xf[col] = vals
    else:
        xf.pop(col, None)
    st.session_state[ix.XF_KEY] = xf


def _remove_xf(col):
    xf = dict(st.session_state[ix.XF_KEY])
    xf.pop(col, None)
    st.session_state[ix.XF_KEY] = xf
    _forget_chart_selections([col])


def _clear_xf():
    _forget_chart_selections(list(st.session_state[ix.XF_KEY]))
    st.session_state[ix.XF_KEY] = {}


df = ix.apply_cross_filters(df, st.session_state[ix.XF_KEY])

# --------------------------------------------------------------------------- #
# Header + KPIs
# --------------------------------------------------------------------------- #
ui.hero("MediScope Health Analytics",
        "Hospital inpatient discharges dashboard - length of stay, charges and utilisation patterns "
        "to support administrators, clinicians and operations managers.",
        [f"NY SPARCS {cfg.SOURCE_YEAR}", f"{len(df):,} of {len(df_all):,} discharges in view",
         f"{df['facility'].nunique()} facilities · {df['county'].nunique()} counties"])

xf_now = st.session_state[ix.XF_KEY]
if xf_now:
    with st.container(key="xf_chips"):
        cols = st.columns([1.1] + [2.2] * len(xf_now) + [1.3, max(0.5, 8 - 2.2 * len(xf_now))])
        cols[0].markdown('<div class="ms-chip-label">🎯 Click filters</div>', unsafe_allow_html=True)
        for c, (col, vals) in zip(cols[1:], xf_now.items()):
            c.button(f"✕  {ix.describe(col, vals)}", key=f"chip_{col}", on_click=_remove_xf, args=(col,),
                     help="Remove this click filter", width="stretch")
        cols[len(xf_now) + 1].button("Clear selection", key="xf_clear", on_click=_clear_xf, type="primary",
                                     width="stretch")

if df.empty:
    st.warning("No discharges match the selected filters. Widen the filters in the sidebar or clear the click filters.")
    st.stop()

k = an.kpis(df)
cards = [
    ("Discharges", f"{k['discharges']:,}", f"{k['facilities']} facilities", cfg.PALETTE["teal"]),
    ("Avg length of stay", f"{k['avg_los']:.1f} d", f"median {k['median_los']:.0f} days", cfg.PALETTE["indigo"]),
    ("Median charges", an._money(k["median_charges"]), "per discharge", cfg.PALETTE["coral"]),
    ("Total billed", an._money(k["total_charges"]), "sum of total charges", cfg.PALETTE["amber"]),
    ("Cost-to-charge", f"{k['avg_ccr']:.2f}", "avg cost / billed charge", cfg.PALETTE["sky"]),
    ("Long stays", f"{k['pct_long']:.1%}", f"> 10 days · {k['pct_emergency']:.0%} via ED", cfg.PALETTE["violet"]),
]
for col, (lbl, val, sub, acc) in zip(st.columns(len(cards)), cards):
    col.markdown(ui.kpi_card(lbl, val, sub, acc), unsafe_allow_html=True)
st.write("")

# Page navigation. A radio (styled as pills) is used instead of st.tabs so that only the
# selected page is rendered: faster, and it keeps the number of live WebGL (3D) charts
# within browser limits.
PAGES = ["📊 Overview", "❓ Research Questions", "🔬 EDA", "🧹 Data Cleaning", "ℹ️ About"]
page = st.radio("Page", PAGES, horizontal=True, label_visibility="collapsed", key="page")


_chart_ids = iter(range(10_000))


def style_pivot(piv, fmt):
    """Pre-formatted text cells with a soft theme gradient computed from the numbers.
    Empty combinations show an em dash on a neutral grey background (no black cells)."""
    import matplotlib.colors as mcolors
    vals = piv.astype(float)
    lo, hi = np.nanmin(vals.values), np.nanmax(vals.values)
    span = (hi - lo) or 1.0
    text = vals.map(lambda v: "—" if pd.isna(v) else fmt.format(v))

    def colour(col):
        out = []
        for v in vals[col.name]:
            if pd.isna(v):
                out.append("background-color: #F1F5F9; color: #94A3B8")
            else:
                out.append(f"background-color: {mcolors.to_hex(ui.SOFT_CMAP((v - lo) / span))}; color: #0F172A")
        return out

    return text.style.apply(colour, axis=0)


def plot(fig, key=None, select=None):
    """Render a Plotly figure full-width.

    ``select`` names the DataFrame column a click / box / lasso selection should
    filter on. Selection is only wired up for 2D charts (Plotly 3D traces do not
    emit selection events in Streamlit).
    """
    key = key or f"chart_{next(_chart_ids)}"
    if select and not use_3d:
        st.session_state["_xf_keys"].setdefault(select, set()).add(key)
        st.plotly_chart(fig, width="stretch", config=PLOT_CFG_2D, key=key,
                        on_select=partial(_on_select, key, select),
                        selection_mode=("points", "box", "lasso"))
    else:
        st.plotly_chart(fig, width="stretch", config=PLOT_CFG if use_3d else PLOT_CFG_2D, key=key)


def options_popover(label="⚙️ Options"):
    """Compact right-aligned popover that holds a chart's controls."""
    _, right = st.columns([3.2, 1.3])
    return right.popover(label, width="stretch")


def interaction_hint():
    if use_3d:
        st.caption("🖱️ 3D: drag to rotate · scroll to zoom · camera buttons (Isometric / Front / Top / Side / Reset) "
                   "above each chart · ⚙️ for chart options · click legend items to show/hide series. "
                   "Click-to-filter works in 2D mode (Plotly 3D charts do not send selection events).")
    else:
        st.caption("🖱️ 2D: **click a bar** (or box/lasso-select several) to filter the whole dashboard · "
                   "⚙️ for chart options · click legend items to show/hide series.")


# --------------------------------------------------------------------------- #
# Overview: the five required visuals
# --------------------------------------------------------------------------- #
if page == "📊 Overview":
    interaction_hint()
    c1, c2 = st.columns([1.25, 1])
    with c1:
        with options_popover():
            ov_metric = st.selectbox("Rank by", list(cfg.RANK_METRICS), format_func=cfg.RANK_METRICS.get, key="ov_metric")
            ov_group = st.radio("Group", list(cfg.GROUP_LEVELS), format_func=cfg.GROUP_LEVELS.get,
                                horizontal=True, key="ov_group")
            ov_n = st.slider("Top N", 5, 25, 12, key="ov_n")
        plot(CH.bar_avg_los_by_diagnosis(df, top_n=ov_n, metric=ov_metric, group=ov_group),
             key="sel_ov_diag", select=ov_group)
    with c2:
        with options_popover():
            pie_by = st.selectbox("Split by", list(cfg.SHARE_BY), format_func=cfg.SHARE_BY.get, key="pie_by")
            pie_val = st.radio("Measure", ["patients", "total_charges"], horizontal=True, key="pie_val",
                               format_func={"patients": "Patients", "total_charges": "Total charges"}.get)
        plot(CH.donut_payment_type(df, by=pie_by, value=pie_val))
    c3, c4 = st.columns(2)
    with c3:
        with options_popover():
            box_val = st.selectbox("Measure", list(cfg.VALUE_COLS), format_func=cfg.VALUE_COLS.get, key="box_val")
            log_y = st.toggle("Log scale", value=True, key="box_log")
        plot(CH.box_charges_by_severity(df, log_scale=log_y, value=box_val))
    with c4:
        with options_popover():
            hist_by = st.selectbox("Break down by", list(cfg.BREAKDOWNS), format_func=cfg.BREAKDOWNS.get, key="hist_by")
            hist_max = st.slider("Max days shown", 10, 60, 30, key="hist_max")
        plot(CH.hist_los(df, max_days=hist_max, breakdown=hist_by))
    with options_popover("⚙️ Heatmap options"):
        top_n = st.slider("Facilities", 5, 30, 18, key="hm_n")
        hm_metric = st.selectbox("Measure", list(cfg.HEAT_METRICS), format_func=cfg.HEAT_METRICS.get, key="hm_metric")
        hm_cols = st.selectbox("Columns", list(cfg.HEAT_COLUMNS), format_func=cfg.HEAT_COLUMNS.get, key="hm_cols")
    plot(CH.heatmap_facility_county(df, top_n=top_n, metric=hm_metric, columns=hm_cols))
    st.caption("Each facility sits in one county, so facilities are labelled and grouped by county and "
               "the columns break the measure down by the chosen dimension. See EDA for a county x admission-type view.")
    with options_popover("⚙️ Animation options"):
        an_metric = st.selectbox("Measure", list(cfg.AGE_METRICS), format_func=cfg.AGE_METRICS.get, key="an_metric")
    plot(charts2d.animated_age_charges(df, metric=an_metric))
    st.caption("Press ▶ Play (or drag the slider) to watch charges by age and gender change from Minor to Extreme severity.")

# --------------------------------------------------------------------------- #
# Research questions
# --------------------------------------------------------------------------- #
if page == "❓ Research Questions":
    st.markdown("Each answer below is **computed live from the filtered data** - change the sidebar "
                "filters (or click chart bars in 2D mode) and the insights update.")
    interaction_hint()

    ui.question(1, "Which diagnosis codes are linked to long stays?")
    g1, t1 = an.rq1_diagnosis_long_stays(df)
    ui.insight(t1)
    with options_popover():
        rq_metric = st.selectbox("Rank by", list(cfg.RANK_METRICS), format_func=cfg.RANK_METRICS.get, key="rq_metric")
        rq_n = st.slider("Top N", 5, 25, 15, key="rq_n")
    plot(CH.bar_avg_los_by_diagnosis(df, top_n=rq_n, metric=rq_metric), key="sel_rq_diag", select="diagnosis")
    with st.expander("Diagnosis x severity pivot table (average stay, days)"):
        st.dataframe(style_pivot(an.diagnosis_severity_pivot(df), "{:.1f}"), width="stretch")

    ui.question(2, "Which age groups incur the highest charges?")
    g2, t2 = an.rq2_age_charges(df)
    ui.insight(t2)
    with options_popover():
        age_metric = st.selectbox("Measure", list(cfg.AGE_METRICS), format_func=cfg.AGE_METRICS.get, key="age_metric")
        age_by = st.radio("Colour by", ["gender", "severity"], format_func=cfg.BREAKDOWNS.get, horizontal=True,
                          key="age_by")
    plot(CH.bar_charges_age_gender(df, metric=age_metric, breakdown=age_by), key="sel_rq_age", select="age_group")

    ui.question(3, "How does patient severity affect total cost?")
    g3, t3 = an.rq3_severity_cost(df)
    ui.insight(t3)
    a, b = st.columns(2)
    with a:
        st.write("")
        plot(CH.bar_severity_cost(df), key="sel_rq_sev", select="severity")
    with b:
        with options_popover():
            rq_box_val = st.selectbox("Measure", list(cfg.VALUE_COLS), format_func=cfg.VALUE_COLS.get, key="rq_box_val")
        plot(CH.box_charges_by_severity(df, value=rq_box_val))

    ui.question(4, "Are there counties with longer average stays?")
    g4, t4 = an.rq4_county_stays(df)
    ui.insight(t4)
    with options_popover():
        cty_n = st.slider("Counties shown", 5, 40, 15, key="cty_n")
        cty_min = st.slider("Min. discharges per county", 30, 500, 100, step=10, key="cty_min")
    plot(CH.bar_county_los(df, min_n=cty_min, n=cty_n), key="sel_rq_county", select="county")

    ui.question(5, "How do different payment types affect the final billing?")
    g5, t5 = an.rq5_payment_billing(df)
    ui.insight(t5)
    plot(CH.bar_payment_billing(df), key="sel_rq_pay", select="payment_type")
    with st.expander("Payment type summary table"):
        st.dataframe(g5.style.format({"avg_los": "{:.1f}", "median_los": "{:.0f}", "avg_charges": "${:,.0f}",
                                      "median_charges": "${:,.0f}", "avg_costs": "${:,.0f}",
                                      "avg_charge_per_day": "${:,.0f}", "cost_to_charge": "{:.2f}",
                                      "discharges": "{:,}"}),
                     width="stretch", hide_index=True)

# --------------------------------------------------------------------------- #
# EDA
# --------------------------------------------------------------------------- #
if page == "🔬 EDA":
    interaction_hint()
    st.markdown("#### Statistical summary of key measures")
    st.dataframe(an.numeric_summary(df).style.format("{:,.2f}"), width="stretch")

    a, b = st.columns(2)
    with a:
        with options_popover():
            fac_n = st.slider("Facilities", 5, 25, 10, key="fac_n")
        plot(CH.bar_top_facilities(df, n=fac_n), key="sel_eda_fac", select="facility")
    with b:
        st.write(""); st.write("")
        plot(CH.bar_body_system(df), key="sel_eda_body", select="body_system")
    a, b = st.columns(2)
    with a:
        plot(CH.scatter_los_charges(df))
    with b:
        plot(CH.heatmap_county_admission(df))

    st.markdown("#### Pivot tables")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Median charges by region x payment type ($)**")
        st.dataframe(style_pivot(an.region_payment_pivot(df), "${:,.0f}"), width="stretch")
    with p2:
        st.markdown("**Average charges by age group x gender ($)**")
        st.dataframe(style_pivot(an.age_gender_pivot(df), "${:,.0f}"), width="stretch")
    st.markdown("**Average stay by diagnosis x severity (days, 15 most common diagnoses)**")
    st.dataframe(style_pivot(an.diagnosis_severity_pivot(df), "{:.1f}"), width="stretch")
    st.markdown("**High-utilisation facilities**")
    st.dataframe(an.top_facilities(df, 15), width="stretch", hide_index=True,
                 column_config={"total_charges": st.column_config.NumberColumn("Total charges", format="$%.0f"),
                                "median_charges": st.column_config.NumberColumn("Median charges", format="$%.0f"),
                                "avg_los": st.column_config.NumberColumn("Avg stay", format="%.1f")})

# --------------------------------------------------------------------------- #
# Data cleaning
# --------------------------------------------------------------------------- #
if page == "🧹 Data Cleaning":
    a, b, c, d = st.columns(4)
    a.markdown(ui.kpi_card("Raw shape", f"{report.raw_shape[0]:,} × {report.raw_shape[1]}", "rows × columns"),
               unsafe_allow_html=True)
    b.markdown(ui.kpi_card("Clean shape", f"{report.clean_shape[0]:,} × {report.clean_shape[1]}",
                           "after cleaning + features", cfg.PALETTE["indigo"]), unsafe_allow_html=True)
    c.markdown(ui.kpi_card("Columns dropped", f"{len(report.dropped_columns)}", "null-heavy / not useful",
                           cfg.PALETTE["coral"]), unsafe_allow_html=True)
    d.markdown(ui.kpi_card("Outliers flagged", f"{int(df_all['is_charge_outlier'].sum()):,}",
                           f"{df_all['is_charge_outlier'].mean():.1%} of records", cfg.PALETTE["amber"]),
               unsafe_allow_html=True)
    st.write("")
    st.markdown("#### Cleaning pipeline (src/cleaning.py)")
    st.dataframe(report.as_frame(), width="stretch", hide_index=True,
                 column_config={"Step": st.column_config.TextColumn(width="medium"),
                                "What was done": st.column_config.TextColumn(width="large")})

    a, b = st.columns(2)
    with a:
        plot(CH.bar_missing(report.raw_missing))
    with b:
        plot(CH.hist_before_after(raw_charges, df_all.loc[~df_all["is_charge_outlier"], "total_charges"]))

    st.markdown("#### Dropped columns")
    st.dataframe(pd.DataFrame(report.dropped_columns, columns=["Column", "Reason"]),
                 width="stretch", hide_index=True)

    a, b = st.columns(2)
    with a:
        st.markdown("**Before - raw records (all text)**")
        st.dataframe(raw_preview, width="stretch", hide_index=True)
    with b:
        st.markdown("**After - clean, typed records with engineered features**")
        st.dataframe(df_all[["age_group", "gender", "severity", "diagnosis", "body_system", "length_of_stay",
                             "total_charges", "charge_per_day", "cost_to_charge_ratio", "los_bucket",
                             "is_charge_outlier"]].head(8), width="stretch", hide_index=True)

    st.markdown("#### Data types after cleaning")
    st.dataframe(pd.DataFrame({"dtype": df_all.dtypes.astype(str),
                               "non-null": df_all.notna().sum(),
                               "unique": df_all.nunique()}), width="stretch")
    st.download_button("⬇️ Download filtered clean data (CSV)", df.to_csv(index=False).encode(),
                       "mediscope_filtered.csv", "text/csv")

# --------------------------------------------------------------------------- #
# About
# --------------------------------------------------------------------------- #
if page == "ℹ️ About":
    s = cfg.STUDENT
    st.markdown(f"""
<div class="ms-card">
<h3 style="margin-top:0;color:{cfg.PALETTE['navy']}">About this project</h3>
<b>MediScope Health Analytics</b> - Hospital Inpatient Discharges Dashboard (Scenario 2).<br>
Built with Streamlit, pandas and Plotly to help hospital administrators, clinicians and operations
managers explore length of stay, charges, severity and payer patterns.
<br><br>
<table>
<tr><td><b>Student</b></td><td>{s['name']}</td></tr>
<tr><td><b>Student ID</b></td><td>{s['student_id']}</td></tr>
<tr><td><b>CRS</b></td><td>{s['crs']}</td></tr>
<tr><td><b>Course</b></td><td>{s['course']}</td></tr>
<tr><td><b>Repository</b></td><td>{s['repo']}</td></tr>
</table>
</div>
""", unsafe_allow_html=True)
    st.markdown(f"""
<div class="ms-card">
<h4 style="margin-top:0;color:{cfg.PALETTE['navy']}">Data source</h4>
New York State Department of Health - <a href="{cfg.SOURCE_URL}" target="_blank">{cfg.SOURCE_NAME}</a>
(Statewide Planning and Research Cooperative System, SPARCS). A seeded random sample of
{report.raw_shape[0]:,} discharges was pulled from the public Socrata API (<code>{cfg.SOURCE_API}</code>)
and stored in <code>data/raw/</code>. To use a different extract, replace the file and adjust
<code>src/config.py</code> (path + column-name aliases).
<br><br>
<h4 style="color:{cfg.PALETTE['navy']}">How to read the dashboard</h4>
<ul>
<li><b>Sidebar filters</b> apply to every page, KPI and chart. The <b>3D charts</b> toggle switches between interactive 3D (drag to rotate, scroll to zoom) and classic 2D charts.</li>
<li><b>Overview</b> holds the five core visuals; <b>Research Questions</b> answers Q1-Q5 with live insights.</li>
<li><b>EDA</b> shows statistical summaries, pivot tables and extra charts; <b>Data Cleaning</b> documents every step.</li>
<li>Charges are hospital list prices; costs are the hospital's estimated cost of care.</li>
</ul>
</div>
""", unsafe_allow_html=True)
