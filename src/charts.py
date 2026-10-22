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
from .analysis import group_summary, top_facilities

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
def bar_avg_los_by_diagnosis(df, top_n: int = 15) -> go.Figure:
    """Required #1 - average length of stay per diagnosis (CCS code)."""
    g = group_summary(df, ["diagnosis_code", "diagnosis"]).nlargest(top_n, "avg_los")
    if g.empty:
        return _empty()
    g = g.sort_values("avg_los")
    g["label"] = g["diagnosis"] + "  [" + g["diagnosis_code"].astype(str) + "]"
    fig = px.bar(g, x="avg_los", y="label", orientation="h",
                 color="avg_los", color_continuous_scale=cfg.SEQ_SCALE[1:],
                 custom_data=["discharges", "median_los", "avg_charges"],
                 labels={"avg_los": "Average stay (days)", "label": ""},
                 title=f"Top {top_n} diagnoses by average length of stay")
    fig.update_traces(
        texttemplate="%{x:.1f} d", textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Avg stay: %{x:.1f} days<br>Median: %{customdata[1]:.0f} days"
                      "<br>Discharges: %{customdata[0]:,}<br>Avg charges: $%{customdata[2]:,.0f}<extra></extra>")
    fig.update_layout(coloraxis_showscale=False, height=max(420, 30 * len(g) + 90))
    fig.update_xaxes(range=[0, g["avg_los"].max() * 1.22])  # room for the value labels
    fig.update_layout(margin=dict(r=40))
    return fig


def box_charges_by_severity(df, log_scale: bool = True) -> go.Figure:
    """Required #2 - distribution of total charges per APR severity."""
    if df.empty:
        return _empty()
    fig = px.box(df, x="severity", y="total_charges", color="severity",
                 category_orders={"severity": cfg.SEVERITY_ORDER},
                 color_discrete_map=cfg.SEVERITY_COLORS, points=False,
                 labels={"severity": "APR severity of illness", "total_charges": "Total charges ($)"},
                 title="Total charges by severity of illness")
    fig.update_traces(boxmean=True)
    fig.update_layout(showlegend=False, height=460)
    if log_scale:
        ticks = [1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 3e6]
        fig.update_yaxes(type="log", tickvals=ticks,
                         ticktext=["$1K", "$3K", "$10K", "$30K", "$100K", "$300K", "$1M", "$3M"])
    else:
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    return fig


def heatmap_facility_county(df, top_n: int = 20) -> go.Figure:
    """Required #3 - average stay by facility (grouped by county) x severity.

    Each facility belongs to exactly one county, so a plain facility x county
    grid would be almost empty. Facilities are therefore labelled and ordered by
    county, and the columns break the stay down by severity plus an overall
    column - showing facility *and* county differences in one view.
    """
    if df.empty:
        return _empty()
    top = df["facility"].value_counts().head(top_n).index
    d = df[df["facility"].isin(top)]
    piv = pd.pivot_table(d, index=["county", "facility"], columns="severity",
                         values="length_of_stay", aggfunc="mean", observed=True)
    piv["All"] = d.groupby(["county", "facility"])["length_of_stay"].mean()
    piv = piv.sort_index(level=0, ascending=False)
    ylabels = [f"{f[:38]} ({c})" for c, f in piv.index]
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=[str(c) for c in piv.columns], y=ylabels,
        colorscale=cfg.SEQ_SCALE, colorbar=dict(title="Avg days"),
        text=np.round(piv.values, 1), texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>Severity: %{x}<br>Avg stay: %{z:.1f} days<extra></extra>",
        xgap=2, ygap=2))
    fig.update_layout(title=f"Average stay (days) - top {top_n} facilities by volume, grouped by county",
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


def donut_payment_type(df) -> go.Figure:
    """Required #4 - patient distribution by primary payment type."""
    if df.empty:
        return _empty()
    s = df["payment_type"].value_counts()
    # fold tiny slices into "Other" for readability
    small = s[s / s.sum() < 0.015]
    if len(small) > 1:
        s = pd.concat([s.drop(small.index), pd.Series({"Other (small groups)": small.sum()})])
    fig = go.Figure(go.Pie(labels=s.index, values=s.values, hole=0.55, sort=True,
                           marker=dict(colors=cfg.COLORWAY, line=dict(color="white", width=2)),
                           textinfo="percent", textposition="inside",
                           hovertemplate="<b>%{label}</b><br>%{value:,} patients (%{percent})<extra></extra>"))
    fig.update_layout(title="Patients by primary payment type", height=440,
                      annotations=[dict(text=f"<b>{s.sum():,}</b><br>patients", showarrow=False,
                                        font=dict(size=16, color=cfg.PALETTE["navy"]))],
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.08,
                                  entrywidth=0.5, entrywidthmode="fraction", font=dict(size=12)))
    return fig


def hist_los(df, max_days: int = 40) -> go.Figure:
    """Required #5 - overall length-of-stay distribution."""
    if df.empty:
        return _empty()
    d = df[df["length_of_stay"] <= max_days]
    fig = px.histogram(d, x="length_of_stay", nbins=max_days, color_discrete_sequence=[cfg.PALETTE["teal"]],
                       labels={"length_of_stay": "Length of stay (days)"},
                       title=f"Distribution of length of stay (stays up to {max_days} days shown)")
    mean, med = df["length_of_stay"].mean(), df["length_of_stay"].median()
    fig.add_vline(x=mean, line=dict(color=cfg.PALETTE["coral"], dash="dash", width=2),
                  annotation_text=f"Mean {mean:.1f}", annotation_font_color=cfg.PALETTE["coral"])
    fig.add_vline(x=med, line=dict(color=cfg.PALETTE["indigo"], dash="dot", width=2),
                  annotation_text=f"Median {med:.0f}", annotation_position="top left",
                  annotation_font_color=cfg.PALETTE["indigo"])
    fig.update_traces(marker_line_color="white", marker_line_width=1,
                      hovertemplate="%{x} days: %{y:,} patients<extra></extra>")
    fig.update_layout(yaxis_title="Patients", bargap=0.05, height=420)
    return fig


# --------------------------------------------------------------------------- #
# Extra visuals
# --------------------------------------------------------------------------- #
def bar_charges_age_gender(df) -> go.Figure:
    g = group_summary(df[df["gender"] != "Unknown"], ["age_group", "gender"], min_n=1)
    if g.empty:
        return _empty()
    fig = px.bar(g, x="age_group", y="avg_charges", color="gender", barmode="group",
                 category_orders={"age_group": cfg.AGE_ORDER},
                 color_discrete_map={"Female": cfg.PALETTE["coral"], "Male": cfg.PALETTE["indigo"]},
                 labels={"age_group": "Age group", "avg_charges": "Average charges ($)", "gender": "Gender"},
                 title="Average total charges by age group and gender")
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    fig.update_traces(hovertemplate="%{x} - %{fullData.name}<br>Avg charges $%{y:,.0f}<extra></extra>")
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
                 custom_data=["county", "discharges", "avg_los", "total_charges"],
                 labels={"patient_days": "Patient-days (discharges x stay)", "label": "", "avg_los": "Avg stay"},
                 title=f"Top {n} high-utilisation facilities (patient-days)")
    fig.update_traces(hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>Patient-days %{x:,}"
                                    "<br>Discharges %{customdata[1]:,}<br>Avg stay %{customdata[2]:.1f} d"
                                    "<br>Total charges $%{customdata[3]:,.0f}<extra></extra>")
    fig.update_layout(height=440)
    return fig


def bar_severity_cost(df) -> go.Figure:
    g = group_summary(df, "severity", min_n=1)
    if g.empty:
        return _empty()
    fig = go.Figure()
    fig.add_bar(x=g["severity"].astype(str), y=g["median_charges"], name="Median charges",
                marker_color=cfg.PALETTE["indigo"])
    fig.add_bar(x=g["severity"].astype(str), y=g["avg_costs"], name="Average cost of care",
                marker_color=cfg.PALETTE["teal"])
    fig.add_scatter(x=g["severity"].astype(str), y=g["avg_los"], name="Average stay (days)",
                    yaxis="y2", mode="lines+markers", line=dict(color=cfg.PALETTE["coral"], width=3),
                    marker=dict(size=10))
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
                           customdata=g["discharges"],
                           hovertemplate="<b>%{y}</b><br>Avg stay %{x:.1f} d<br>n=%{customdata:,}<extra></extra>"))
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
    fig.add_bar(y=g["payment_type"], x=g["avg_charges"], orientation="h", name="Average charges",
                marker_color=cfg.PALETTE["indigo"])
    fig.add_bar(y=g["payment_type"], x=g["avg_costs"], orientation="h", name="Average cost",
                marker_color=cfg.PALETTE["teal"])
    fig.update_layout(title="Average billed charges vs actual cost by payment type", barmode="group",
                      height=460, xaxis=dict(tickprefix="$", tickformat=",.0f"),
                      legend=dict(orientation="h", y=-0.12))
    return fig


def bar_body_system(df) -> go.Figure:
    g = group_summary(df, "body_system").sort_values("discharges")
    if g.empty:
        return _empty()
    fig = px.bar(g, x="discharges", y="body_system", orientation="h", color="avg_los",
                 color_continuous_scale=cfg.SEQ_SCALE[1:],
                 labels={"discharges": "Discharges", "body_system": "", "avg_los": "Avg stay"},
                 title="Discharges by body system (colour = average stay)")
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
