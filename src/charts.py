"""
Plotly chart builders. Every function takes a (filtered) DataFrame and returns
a ``plotly.graph_objects.Figure`` styled with the shared "mediscope" template.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from . import config as cfg
from .analysis import group_summary, ranked, top_facilities

# --------------------------------------------------------------------------- #
# Shared template
# --------------------------------------------------------------------------- #
FONT = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
pio.templates["mediscope"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family=FONT, size=13, color="#1E293B"),
        title=dict(font=dict(size=17, color=cfg.PALETTE["navy"]), x=0.0, xanchor="left"),
        colorway=cfg.COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#CBD5E1", linecolor="#CBD5E1"),
        yaxis=dict(gridcolor="#E2E8F0", zerolinecolor="#CBD5E1", linecolor="#CBD5E1"),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, color="#0F172A"),
                        bordercolor=cfg.PALETTE["teal"]),
        legend=dict(bgcolor="rgba(0,0,0,0)", title=dict(font=dict(size=12))),
        margin=dict(l=10, r=10, t=56, b=10),
    )
)
pio.templates.default = "plotly_white+mediscope"


def _empty(msg="No data for the current filters") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=15, color="#64748B"))
    fig.update_layout(xaxis_visible=False, yaxis_visible=False, height=320)
    return fig


# --------------------------------------------------------------------------- #
# Required visuals
# --------------------------------------------------------------------------- #
def bar_avg_los_by_diagnosis(df, top_n: int = 15, metric: str = "avg_los", group: str = "diagnosis") -> go.Figure:
    """Required #1 - top-N diagnoses (or body systems) ranked by a stay/charge metric.
    ``customdata[0]`` carries the group value so a click can cross-filter the dashboard."""
    g = ranked(df, group, metric, top_n)
    if g.empty:
        return _empty()
    g = g.sort_values(metric)
    money = cfg.is_money(metric)
    mlabel = cfg.RANK_METRICS[metric]
    fig = px.bar(g, x=metric, y="label", orientation="h",
                 color=metric, color_continuous_scale=cfg.SEQ_SCALE[1:],
                 custom_data=["key", "discharges", "avg_los", "median_los", "avg_charges"],
                 labels={metric: mlabel, "label": ""},
                 title=f"Top {top_n} {cfg.GROUP_LEVELS[group].lower()} by {mlabel.split(' (')[0].lower()}")
    fig.update_traces(
        texttemplate="$%{x:,.0f}" if money else "%{x:.1f} d", textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Avg stay: %{customdata[2]:.1f} days<br>Median stay: %{customdata[3]:.0f} days"
                      "<br>Avg charges: $%{customdata[4]:,.0f}<br>Discharges: %{customdata[1]:,}"
                      "<br><i>Click to filter the dashboard</i><extra></extra>")
    fig.update_layout(coloraxis_showscale=False, height=max(420, 30 * len(g) + 90), margin=dict(r=50))
    fig.update_xaxes(range=[0, g[metric].max() * 1.22])
    if money:
        fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    return fig



def box_charges_by_severity(df, log_scale: bool = True, value: str = "total_charges") -> go.Figure:
    """Required #2 - distribution of charges / costs / charge-per-day per APR severity."""
    if df.empty:
        return _empty()
    vlabel = cfg.VALUE_COLS[value]
    fig = px.box(df, x="severity", y=value, color="severity",
                 category_orders={"severity": cfg.SEVERITY_ORDER},
                 color_discrete_map=cfg.SEVERITY_COLORS, points=False,
                 labels={"severity": "APR severity of illness", value: vlabel},
                 title=f"{vlabel.split(' (')[0]} by severity of illness")
    fig.update_traces(boxmean=True)
    fig.update_layout(showlegend=False, height=460)
    if log_scale:
        ticks = [1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 3e6]
        fig.update_yaxes(type="log", tickvals=ticks,
                         ticktext=["$100", "$300", "$1K", "$3K", "$10K", "$30K", "$100K", "$300K", "$1M", "$3M"])
    else:
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig



def heatmap_facility_county(df, top_n: int = 20, metric: str = "length_of_stay",
                            columns: str = "severity") -> go.Figure:
    """Required #3 - facility (grouped by county) x severity/age/gender heatmap.

    Each facility belongs to exactly one county, so a plain facility x county
    grid would be almost empty. Facilities are therefore labelled and ordered by
    county, and the columns break the metric down by a chosen dimension.
    """
    if df.empty:
        return _empty()
    top = df["facility"].value_counts().head(top_n).index
    d = df[df["facility"].isin(top)]
    piv = pd.pivot_table(d, index=["county", "facility"], columns=columns,
                         values=metric, aggfunc="mean", observed=True)
    piv = piv[[c for c in cfg.level_order(columns, piv.columns)]]
    piv["All"] = d.groupby(["county", "facility"])[metric].mean()
    piv = piv.sort_index(level=0, ascending=False)
    ylabels = [f"{f[:38]} ({c})" for c, f in piv.index]
    money = cfg.is_money(metric)
    mlabel = cfg.HEAT_METRICS[metric]
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=[str(c) for c in piv.columns], y=ylabels,
        colorscale=cfg.SEQ_SCALE, colorbar=dict(title="$" if money else "Days"),
        text=[[("" if pd.isna(v) else (f"${v/1000:,.0f}K" if money else f"{v:.1f}")) for v in row] for row in piv.values],
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>%{x}<br>" + mlabel + ": %{z:,.1f}<extra></extra>",
        xgap=2, ygap=2))
    fig.update_layout(title=f"{mlabel} - top {top_n} facilities (grouped by county) x {cfg.HEAT_COLUMNS[columns].lower()}",
                      height=max(460, 26 * len(piv) + 140), margin=dict(t=90))
    fig.update_xaxes(side="top")
    return fig



def heatmap_county_admission(df, min_n: int = 100) -> go.Figure:
    """Companion heatmap: avg stay by county x type of admission."""
    counts = df["county"].value_counts()
    keep = counts[counts >= min_n].index
    d = df[df["county"].isin(keep)]
    if d.empty:
        return _empty()
    piv = pd.pivot_table(d, index="county", columns="admission_type", values="length_of_stay",
                         aggfunc="mean", observed=True)
    piv = piv.loc[piv.mean(axis=1).sort_values().index]
    fig = go.Figure(go.Heatmap(z=piv.values, x=list(piv.columns), y=list(piv.index),
                               colorscale=cfg.SEQ_SCALE, colorbar=dict(title="Avg days"),
                               hovertemplate="%{y} / %{x}<br>Avg stay %{z:.1f} days<extra></extra>",
                               xgap=2, ygap=1))
    fig.update_layout(title="Average stay by county and admission type",
                      height=max(460, 16 * len(piv) + 120))
    return fig


def donut_payment_type(df, by: str = "payment_type", value: str = "patients") -> go.Figure:
    """Required #4 - share of patients (or of total charges) by payment type."""
    if df.empty:
        return _empty()
    s = (df[by].value_counts() if value == "patients"
         else df.groupby(by)["total_charges"].sum().sort_values(ascending=False))
    small = s[s / s.sum() < 0.015]
    if len(small) > 1:
        s = pd.concat([s.drop(small.index), pd.Series({"Other (small groups)": small.sum()})])
    unit = "patients" if value == "patients" else "billed"
    fmt = "%{value:,}" if value == "patients" else "$%{value:,.0f}"
    centre = f"{s.sum():,}" if value == "patients" else f"${s.sum()/1e9:,.2f}B"
    fig = go.Figure(go.Pie(labels=s.index, values=s.values, hole=0.55, sort=True,
                           marker=dict(colors=cfg.COLORWAY, line=dict(color="white", width=2)),
                           textinfo="percent", textposition="inside", pull=[0.04] + [0] * (len(s) - 1),
                           hovertemplate="<b>%{label}</b><br>" + fmt + " " + unit + " (%{percent})<extra></extra>"))
    fig.update_layout(title=f"{'Patients' if value == 'patients' else 'Total charges'} by {cfg.SHARE_BY[by].lower()}",
                      height=440,
                      annotations=[dict(text=f"<b>{centre}</b><br>{unit}", showarrow=False,
                                        font=dict(size=16, color=cfg.PALETTE["navy"]))],
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.08,
                                  entrywidth=0.5, entrywidthmode="fraction", font=dict(size=12)))
    return fig



def hist_los(df, max_days: int = 40, breakdown: str = "severity") -> go.Figure:
    """Required #5 - length-of-stay distribution, stacked by a breakdown dimension."""
    if df.empty:
        return _empty()
    d = df[df["length_of_stay"] <= max_days].copy()
    d[breakdown] = d[breakdown].astype(str)
    order = cfg.level_order(breakdown, d[breakdown].unique())
    fig = px.histogram(d, x="length_of_stay", color=breakdown, nbins=max_days, barmode="stack",
                       category_orders={breakdown: order}, color_discrete_map=cfg.breakdown_colors(breakdown),
                       labels={"length_of_stay": "Length of stay (days)", breakdown: cfg.BREAKDOWNS[breakdown]},
                       title=f"Distribution of length of stay by {cfg.BREAKDOWNS[breakdown].lower()} "
                             f"(stays up to {max_days} days)")
    mean, med = df["length_of_stay"].mean(), df["length_of_stay"].median()
    fig.add_vline(x=mean, line=dict(color=cfg.PALETTE["coral"], dash="dash", width=2),
                  annotation_text=f"Mean {mean:.1f}", annotation_font_color=cfg.PALETTE["coral"])
    fig.add_vline(x=med, line=dict(color=cfg.PALETTE["indigo"], dash="dot", width=2),
                  annotation_text=f"Median {med:.0f}", annotation_position="top left",
                  annotation_font_color=cfg.PALETTE["indigo"])
    fig.update_traces(marker_line_color="white", marker_line_width=0.5,
                      hovertemplate="%{x} days · %{fullData.name}: %{y:,} patients<extra></extra>")
    fig.update_layout(yaxis_title="Patients", bargap=0.05, height=420,
                      legend=dict(orientation="h", y=-0.2, title=None))
    return fig



# --------------------------------------------------------------------------- #
# Extra visuals
# --------------------------------------------------------------------------- #
def bar_charges_age_gender(df, metric: str = "avg_charges", breakdown: str = "gender") -> go.Figure:
    """Charges (or cost / stay) by age group, split by gender or severity. Click a bar to filter by age."""
    d = df[df["gender"] != "Unknown"]
    g = group_summary(d, ["age_group", breakdown], min_n=1)
    if g.empty:
        return _empty()
    g[breakdown] = g[breakdown].astype(str)
    g["age_group"] = g["age_group"].astype(str)
    mlabel = cfg.AGE_METRICS[metric]
    fig = px.bar(g, x="age_group", y=metric, color=breakdown, barmode="group",
                 category_orders={"age_group": cfg.AGE_ORDER, breakdown: cfg.level_order(breakdown, g[breakdown].unique())},
                 color_discrete_map=cfg.breakdown_colors(breakdown), custom_data=["age_group", "discharges"],
                 labels={"age_group": "Age group", metric: mlabel, breakdown: cfg.BREAKDOWNS[breakdown]},
                 title=f"{mlabel.split(' (')[0]} by age group and {cfg.BREAKDOWNS[breakdown].lower()}")
    if cfg.is_money(metric):
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        ht = "$%{y:,.0f}"
    else:
        ht = "%{y:.1f} days"
    fig.update_traces(hovertemplate="<b>%{x}</b> · %{fullData.name}<br>" + mlabel.split(" (")[0] + ": " + ht +
                                    "<br>n=%{customdata[1]:,}<br><i>Click to filter by age group</i><extra></extra>")
    fig.update_layout(height=420)
    return fig



def bar_top_facilities(df, n: int = 10) -> go.Figure:
    g = top_facilities(df, n)
    if g.empty:
        return _empty()
    g = g.sort_values("patient_days")
    g["label"] = g["facility"].str.slice(0, 42)
    fig = px.bar(g, x="patient_days", y="label", orientation="h", color="avg_los",
                 color_continuous_scale=[cfg.PALETTE["sky"], cfg.PALETTE["indigo"], cfg.PALETTE["navy"]],
                 custom_data=["facility", "county", "discharges", "avg_los", "total_charges"],
                 labels={"patient_days": "Patient-days (discharges x stay)", "label": "", "avg_los": "Avg stay"},
                 title=f"Top {n} high-utilisation facilities (patient-days)")
    fig.update_traces(hovertemplate="<b>%{y}</b> (%{customdata[1]})<br>Patient-days %{x:,}"
                                    "<br>Discharges %{customdata[2]:,}<br>Avg stay %{customdata[3]:.1f} d"
                                    "<br>Total charges $%{customdata[4]:,.0f}<br><i>Click to filter</i><extra></extra>")
    fig.update_layout(height=440)
    return fig



def bar_severity_cost(df) -> go.Figure:
    g = group_summary(df, "severity", min_n=1)
    if g.empty:
        return _empty()
    sev = g["severity"].astype(str)
    fig = go.Figure()
    fig.add_bar(x=sev, y=g["median_charges"], name="Median charges", customdata=sev,
                marker_color=cfg.PALETTE["indigo"], hovertemplate="%{x}: median charges $%{y:,.0f}<extra></extra>")
    fig.add_bar(x=sev, y=g["avg_costs"], name="Average cost of care", customdata=sev,
                marker_color=cfg.PALETTE["teal"], hovertemplate="%{x}: average cost $%{y:,.0f}<extra></extra>")
    fig.add_scatter(x=sev, y=g["avg_los"], name="Average stay (days)", customdata=sev,
                    yaxis="y2", mode="lines+markers", line=dict(color=cfg.PALETTE["coral"], width=3),
                    marker=dict(size=10), hovertemplate="%{x}: %{y:.1f} days<extra></extra>")
    fig.update_layout(title="Charges, cost and stay by severity", barmode="group", height=420,
                      yaxis=dict(title="US$", tickprefix="$", tickformat=",.0f"),
                      yaxis2=dict(title="Days", overlaying="y", side="right", showgrid=False),
                      legend=dict(orientation="h", y=-0.15))
    return fig



def bar_county_los(df, min_n: int = 100, n: int = 15) -> go.Figure:
    g = group_summary(df, "county", min_n=min_n).sort_values("avg_los", ascending=False).head(n)
    if g.empty:
        return _empty("No county has enough discharges for the current filters")
    mean = df["length_of_stay"].mean()
    g = g.sort_values("avg_los")
    colors = [cfg.PALETTE["coral"] if v > mean else cfg.PALETTE["teal"] for v in g["avg_los"]]
    fig = go.Figure(go.Bar(x=g["avg_los"], y=g["county"], orientation="h", marker_color=colors,
                           customdata=np.c_[g["county"].values, g["discharges"].values],
                           hovertemplate="<b>%{y}</b><br>Avg stay %{x:.1f} d<br>n=%{customdata[1]:,}"
                                         "<br><i>Click to filter</i><extra></extra>"))
    fig.add_vline(x=mean, line=dict(color=cfg.PALETTE["navy"], dash="dash"),
                  annotation_text=f"State mean {mean:.1f}")
    fig.update_layout(title=f"Counties with the longest average stays (n >= {min_n})",
                      xaxis_title="Average stay (days)", height=max(420, 26 * len(g) + 100))
    return fig



def bar_payment_billing(df) -> go.Figure:
    g = group_summary(df, "payment_type").sort_values("avg_charges")
    if g.empty:
        return _empty()
    fig = go.Figure()
    for col, name, color in (("avg_charges", "Average charges", cfg.PALETTE["indigo"]),
                             ("avg_costs", "Average cost", cfg.PALETTE["teal"])):
        fig.add_bar(y=g["payment_type"], x=g[col], orientation="h", name=name, marker_color=color,
                    customdata=g["payment_type"],
                    hovertemplate="<b>%{y}</b><br>" + name + ": $%{x:,.0f}<br><i>Click to filter</i><extra></extra>")
    fig.update_layout(title="Average billed charges vs actual cost by payment type", barmode="group",
                      height=460, xaxis=dict(tickprefix="$", tickformat=",.0f"),
                      legend=dict(orientation="h", y=-0.12))
    return fig



def bar_body_system(df) -> go.Figure:
    g = group_summary(df, "body_system").sort_values("discharges")
    if g.empty:
        return _empty()
    fig = px.bar(g, x="discharges", y="body_system", orientation="h", color="avg_los",
                 color_continuous_scale=cfg.SEQ_SCALE[1:], custom_data=["body_system", "avg_los"],
                 labels={"discharges": "Discharges", "body_system": "", "avg_los": "Avg stay"},
                 title="Discharges by body system (colour = average stay)")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>%{x:,} discharges<br>Avg stay %{customdata[1]:.1f} d"
                                    "<br><i>Click to filter</i><extra></extra>")
    fig.update_layout(height=520)
    return fig



def scatter_los_charges(df, sample: int = 4000) -> go.Figure:
    if df.empty:
        return _empty()
    d = df.sample(min(sample, len(df)), random_state=1)
    fig = px.scatter(d, x="length_of_stay", y="total_charges", color="severity",
                     category_orders={"severity": cfg.SEVERITY_ORDER},
                     color_discrete_map=cfg.SEVERITY_COLORS, opacity=0.55, log_x=True, log_y=True,
                     hover_data={"diagnosis": True, "facility": True},
                     labels={"length_of_stay": "Length of stay (days, log)", "total_charges": "Total charges ($, log)"},
                     title=f"Stay vs charges (random sample of {len(d):,} patients)")
    fig.update_layout(height=460, legend=dict(orientation="h", y=-0.18))
    return fig


def bar_missing(missing: pd.Series) -> go.Figure:
    m = (missing[missing > 0] * 100).sort_values()
    if m.empty:
        return _empty("No missing values in the raw file")
    fig = go.Figure(go.Bar(x=m.values, y=m.index, orientation="h",
                           marker_color=[cfg.PALETTE["coral"] if v > 70 else cfg.PALETTE["sky"] for v in m.values],
                           hovertemplate="%{y}: %{x:.1f}% missing<extra></extra>"))
    fig.update_layout(title="Missing values in the raw file (% of rows)", xaxis_title="% missing",
                      height=max(300, 28 * len(m) + 100))
    return fig


def hist_before_after(raw_charges: pd.Series, clean_charges: pd.Series) -> go.Figure:
    before = np.log10(raw_charges[raw_charges > 0].dropna())
    after = np.log10(clean_charges)
    bins = dict(start=float(before.min()), end=float(before.max()), size=(before.max() - before.min()) / 70)
    fig = go.Figure()
    fig.add_histogram(x=before, name="Before (all rows)", xbins=bins,
                      marker_color=cfg.PALETTE["coral"], opacity=0.55)
    fig.add_histogram(x=after, name="After (outliers excluded)", xbins=bins,
                      marker_color=cfg.PALETTE["teal"], opacity=0.75)
    fig.update_layout(barmode="overlay", title="Total charges before vs after outlier handling (log10 $)",
                      xaxis_title="log10(total charges)", yaxis_title="Patients", height=380,
                      legend=dict(orientation="h", y=-0.2))
    return fig



def animated_age_charges(df, metric: str = "avg_charges") -> go.Figure:
    """Animated bar chart: the metric by age group and gender, one frame per severity
    level (press Play or drag the slider)."""
    d = df[df["gender"].isin(["Female", "Male"])]
    g = group_summary(d, ["severity", "age_group", "gender"], min_n=1)
    if g.empty or g["severity"].nunique() < 2:
        return _empty("Animation needs at least two severity levels in the current filter")
    for c in ("severity", "age_group"):
        g[c] = g[c].astype(str)
    sev_order = cfg.level_order("severity", g["severity"].unique())
    g["severity"] = pd.Categorical(g["severity"], sev_order, ordered=True)
    g = g.sort_values(["severity", "age_group"])
    g["severity"] = g["severity"].astype(str)
    mlabel = cfg.AGE_METRICS[metric]
    fig = px.bar(g, x="age_group", y=metric, color="gender", barmode="group", animation_frame="severity",
                 category_orders={"age_group": cfg.AGE_ORDER, "severity": sev_order, "gender": ["Female", "Male"]},
                 color_discrete_map=cfg.GENDER_COLORS, range_y=[0, g[metric].max() * 1.1],
                 custom_data=["discharges"],
                 labels={"age_group": "Age group", metric: mlabel, "gender": "Gender", "severity": "Severity"},
                 title=f"▶ Animated: {mlabel.split(' (')[0].lower()} by age and gender as severity increases")
    money = cfg.is_money(metric)
    ht = "$%{y:,.0f}" if money else "%{y:.1f} days"
    fig.update_traces(hovertemplate="<b>%{x}</b> · %{fullData.name}<br>" + ht + "<br>n=%{customdata[0]:,}<extra></extra>")
    for fr in fig.frames:
        for tr in fr.data:
            tr.hovertemplate = "<b>%{x}</b> · %{fullData.name}<br>" + ht + "<br>n=%{customdata[0]:,}<extra></extra>"
    if money:
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    fig.update_layout(height=480, legend=dict(orientation="h", y=1.02, x=1, xanchor="right", title=None))
    # theme the play controls and slow the transition slightly
    if fig.layout.updatemenus:
        fig.layout.updatemenus[0].update(bgcolor="white", bordercolor=cfg.PALETTE["teal"],
                                         font=dict(color=cfg.PALETTE["navy"]))
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 1100
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 500
    if fig.layout.sliders:
        fig.layout.sliders[0].update(currentvalue=dict(prefix="Severity: ", font=dict(color=cfg.PALETTE["indigo"])),
                                     activebgcolor=cfg.PALETTE["teal"])
    return fig
