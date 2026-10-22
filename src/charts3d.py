"""
Interactive 3D versions of every dashboard chart (Plotly ``Mesh3d`` /
``Scatter3d``). Function names and signatures mirror ``src/charts.py`` so the
app can switch between 2D and 3D with a single toggle.

Design notes
------------
* Data is always aggregated with pandas *before* plotting; the only point
  cloud (stay vs charges) is capped at ~5,000 patients.
* Bars are cuboids built by ``_bars3d`` (8 vertices / 12 triangles each) with
  flat shading, so they read as solid 3D blocks while hover still shows the
  exact value.
* Categorical axes use numeric positions with ``tickvals`` / ``ticktext``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import config as cfg
from . import charts as c2d  # re-uses the shared template and _empty()
from .analysis import group_summary, top_facilities

P = cfg.PALETTE
LIGHT = dict(ambient=0.55, diffuse=0.75, specular=0.25, roughness=0.6, fresnel=0.15)
LIGHT_POS = dict(x=1500, y=2500, z=4000)


# --------------------------------------------------------------------------- #
# Low-level builders
# --------------------------------------------------------------------------- #
def _short(s, n=22) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _cuboid(x, y, z0, z1, dx, dy):
    """Vertices + triangle indices of an axis-aligned box centred on (x, y)."""
    xs = [x - dx, x + dx, x + dx, x - dx] * 2
    ys = [y - dy, y - dy, y + dy, y + dy] * 2
    zs = [z0] * 4 + [z1] * 4
    i = [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3]
    j = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4]
    k = [2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7]
    return xs, ys, zs, i, j, k


def _bars3d(x, y, z, *, color=None, intensity=None, colorscale=None, hover=None,
            name="", dx=0.35, dy=0.35, z0=None, showlegend=False, colorbar_title=None,
            opacity=1.0, cmin=None, cmax=None) -> go.Mesh3d:
    """One Mesh3d containing a cuboid per (x, y, z) triple.

    Colour either with a single ``color`` / per-bar list of colours, or with a
    numeric ``intensity`` per bar mapped through ``colorscale`` (adds a colourbar).
    """
    X, Y, Z, I, J, K, FC, INT, TXT = [], [], [], [], [], [], [], [], []
    z0 = z0 if z0 is not None else [0] * len(z)
    for n, (xi, yi, zi) in enumerate(zip(x, y, z)):
        if zi is None or (isinstance(zi, float) and np.isnan(zi)):
            continue
        xs, ys, zs, i, j, k = _cuboid(xi, yi, z0[n], zi, dx, dy)
        off = len(X)
        X += xs; Y += ys; Z += zs
        I += [a + off for a in i]; J += [a + off for a in j]; K += [a + off for a in k]
        if isinstance(color, (list, tuple, np.ndarray, pd.Series)):
            FC += [list(color)[n]] * 12
        if intensity is not None:
            INT += [list(intensity)[n]] * 8
        TXT += [hover[n] if hover is not None else f"{zi:,.1f}"] * 8
    mesh = dict(x=X, y=Y, z=Z, i=I, j=J, k=K, name=name, showlegend=showlegend,
                flatshading=True, lighting=LIGHT, lightposition=LIGHT_POS, opacity=opacity,
                hovertext=TXT, hoverinfo="text")
    if intensity is not None:
        mesh.update(intensity=INT, colorscale=colorscale or cfg.SEQ_SCALE, cmin=cmin, cmax=cmax,
                    colorbar=dict(title=colorbar_title or "", thickness=14, len=0.7),
                    showscale=True)
    elif FC:
        mesh.update(facecolor=FC)
    else:
        mesh.update(color=color or P["teal"])
    return go.Mesh3d(**mesh)


def _axis(title, tickvals=None, ticktext=None, **kw):
    ax = dict(title=dict(text=title, font=dict(size=12, color=P["navy"])),
              backgroundcolor="rgba(232,238,247,0.55)", gridcolor="#CBD5E1",
              showbackground=True, zerolinecolor="#94A3B8",
              tickfont=dict(size=10, color="#334155"))
    if tickvals is not None:
        ax.update(tickvals=list(tickvals), ticktext=list(ticktext), tickmode="array")
    ax.update(kw)
    return ax


def _layout(fig, title, x, y, z, eye=(1.6, -1.6, 0.9), aspect=(1.6, 1, 0.7), height=520,
            legend=False):
    fig.update_layout(
        title=title, height=height, margin=dict(l=0, r=0, t=56, b=0),
        paper_bgcolor="rgba(0,0,0,0)", showlegend=legend,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.02),
        scene=dict(xaxis=x, yaxis=y, zaxis=z, bgcolor="rgba(0,0,0,0)",
                   camera=dict(eye=dict(x=eye[0], y=eye[1], z=eye[2])),
                   aspectmode="manual", aspectratio=dict(x=aspect[0], y=aspect[1], z=aspect[2])))
    return fig


# --------------------------------------------------------------------------- #
# Required visuals (3D)
# --------------------------------------------------------------------------- #
def bar_avg_los_by_diagnosis(df, top_n: int = 15) -> go.Figure:
    g = group_summary(df, ["diagnosis_code", "diagnosis"]).nlargest(top_n, "avg_los")
    if g.empty:
        return c2d._empty()
    g = g.reset_index(drop=True)
    pos = list(range(len(g)))
    hover = [f"<b>{r.diagnosis}</b> [{r.diagnosis_code}]<br>Avg stay: {r.avg_los:.1f} days"
             f"<br>Median: {r.median_los:.0f} days<br>Discharges: {r.discharges:,}"
             f"<br>Avg charges: ${r.avg_charges:,.0f}" for r in g.itertuples()]
    fig = go.Figure(_bars3d(pos, [0] * len(g), g["avg_los"], intensity=g["avg_los"],
                            colorscale=cfg.SEQ_SCALE[1:], hover=hover, colorbar_title="Days",
                            dx=0.36, dy=0.45))
    # value labels floating above each bar
    fig.add_scatter3d(x=pos, y=[0] * len(g), z=g["avg_los"] * 1.06, mode="text",
                      text=[f"{v:.1f}d" for v in g["avg_los"]], hoverinfo="skip",
                      textfont=dict(size=10, color=P["navy"]))
    return _layout(fig, f"Top {top_n} diagnoses by average length of stay (3D)",
                   _axis("", pos, [_short(d, 20) for d in g["diagnosis"]], tickangle=0),
                   _axis("", [0], [""], showbackground=False, showgrid=False),
                   _axis("Avg stay (days)"), eye=(0.25, -2.0, 0.85), aspect=(2.2, 0.45, 0.9),
                   height=520)


def box_charges_by_severity(df, log_scale: bool = True, max_points: int = 5000) -> go.Figure:
    """3D scatter: severity (x, jittered) x length of stay (y) x charges (z),
    with median diamonds and inter-quartile whiskers per severity."""
    if df.empty:
        return c2d._empty()
    d = df.sample(min(max_points, len(df)), random_state=7)
    rng = np.random.default_rng(7)
    fig = go.Figure()
    for k, sev in enumerate(cfg.SEVERITY_ORDER):
        s = d[d["severity"] == sev]
        if s.empty:
            continue
        fig.add_scatter3d(
            x=k + rng.uniform(-0.28, 0.28, len(s)), y=s["length_of_stay"], z=s["total_charges"],
            mode="markers", name=sev, marker=dict(size=2.4, color=cfg.SEVERITY_COLORS[sev], opacity=0.55),
            customdata=np.c_[s["diagnosis"].values], legendgroup=sev,
            hovertemplate=f"<b>{sev}</b><br>Stay %{{y}} d<br>Charges $%{{z:,.0f}}<br>%{{customdata[0]}}<extra></extra>")
        full = df[df["severity"] == sev]
        q1, med, q3 = full["total_charges"].quantile([.25, .5, .75])
        mlos = full["length_of_stay"].median()
        fig.add_scatter3d(x=[k, k], y=[mlos, mlos], z=[q1, q3], mode="lines", legendgroup=sev,
                          showlegend=False, line=dict(color=P["navy"], width=9), hoverinfo="skip")
        fig.add_scatter3d(x=[k], y=[mlos], z=[med], mode="markers+text", legendgroup=sev, showlegend=False,
                          marker=dict(size=7, symbol="diamond", color=P["navy"], line=dict(color="white", width=1)),
                          text=[f"${med/1000:,.0f}K"], textposition="top center",
                          textfont=dict(size=11, color=P["navy"]),
                          hovertemplate=f"<b>{sev}</b> (all {len(full):,} patients)<br>Median ${med:,.0f}"
                                        f"<br>Q1 ${q1:,.0f} - Q3 ${q3:,.0f}<extra></extra>")
    zt = dict(type="log") if log_scale else {}
    return _layout(fig, "Total charges by severity: 3D (◆ median, bar = Q1-Q3)",
                   _axis("Severity", range(4), cfg.SEVERITY_ORDER),
                   _axis("Length of stay (days)", type="log"),
                   _axis("Total charges ($)", tickprefix="$", **zt),
                   eye=(1.55, -1.55, 0.7), aspect=(1.3, 1, 0.9), height=520, legend=True)


def heatmap_facility_county(df, top_n: int = 20) -> go.Figure:
    """3D bar grid: facility (grouped by county) x severity -> average stay."""
    if df.empty:
        return c2d._empty()
    top = df["facility"].value_counts().head(top_n).index
    d = df[df["facility"].isin(top)]
    piv = pd.pivot_table(d, index=["county", "facility"], columns="severity",
                         values="length_of_stay", aggfunc="mean", observed=True)
    piv["All"] = d.groupby(["county", "facility"])["length_of_stay"].mean()
    piv = piv.sort_index(level=0)
    cols = [str(c) for c in piv.columns]
    xs, ys, zs, hv = [], [], [], []
    for yi, (county, fac) in enumerate(piv.index):
        for xi, col in enumerate(cols):
            v = piv.iloc[yi, xi]
            if pd.notna(v):
                xs.append(xi); ys.append(yi); zs.append(v)
                hv.append(f"<b>{fac}</b><br>{county} county<br>Severity: {col}<br>Avg stay: {v:.1f} days")
    fig = go.Figure(_bars3d(xs, ys, zs, intensity=zs, colorscale=cfg.SEQ_SCALE, hover=hv,
                            colorbar_title="Avg days", dx=0.32, dy=0.36))
    ylab = [f"{_short(f, 24)} ({c})" for c, f in piv.index]
    return _layout(fig, f"Average stay - top {top_n} facilities (grouped by county) x severity (3D)",
                   _axis("Severity", range(len(cols)), cols),
                   _axis("", range(len(ylab)), ylab),
                   _axis("Avg stay (days)"), eye=(1.75, -1.15, 1.0), aspect=(0.9, 2.0, 0.7),
                   height=max(620, 18 * len(ylab) + 300))


def heatmap_county_admission(df, min_n: int = 100) -> go.Figure:
    counts = df["county"].value_counts()
    d = df[df["county"].isin(counts[counts >= min_n].index)]
    if d.empty:
        return c2d._empty()
    piv = pd.pivot_table(d, index="county", columns="admission_type", values="length_of_stay",
                         aggfunc="mean", observed=True)
    piv = piv.loc[piv.mean(axis=1).sort_values().index]
    xs, ys, zs, hv = [], [], [], []
    for yi, county in enumerate(piv.index):
        for xi, col in enumerate(piv.columns):
            v = piv.iloc[yi, xi]
            if pd.notna(v):
                xs.append(xi); ys.append(yi); zs.append(v)
                hv.append(f"<b>{county}</b> / {col}<br>Avg stay {v:.1f} days")
    fig = go.Figure(_bars3d(xs, ys, zs, intensity=zs, colorscale=cfg.SEQ_SCALE, hover=hv,
                            colorbar_title="Avg days", dx=0.3, dy=0.36))
    return _layout(fig, "Average stay by county and admission type (3D)",
                   _axis("Admission type", range(len(piv.columns)), list(piv.columns)),
                   _axis("", range(len(piv.index)), list(piv.index)),
                   _axis("Avg stay (days)"), eye=(1.8, -1.0, 0.9), aspect=(0.9, 2.0, 0.6), height=640)


def donut_payment_type(df) -> go.Figure:
    """Extruded 3D donut: one Mesh3d ring segment per payment type."""
    if df.empty:
        return c2d._empty()
    s = df["payment_type"].value_counts()
    small = s[s / s.sum() < 0.015]
    if len(small) > 1:
        s = pd.concat([s.drop(small.index), pd.Series({"Other (small groups)": small.sum()})])
    share = s / s.sum()
    r_in, r_out, h, steps = 0.55, 1.0, 0.28, 48
    fig = go.Figure()
    a0 = np.pi / 2
    for n, (label, frac) in enumerate(share.items()):
        a1 = a0 - 2 * np.pi * frac
        ang = np.linspace(a0, a1, max(3, int(steps * frac) + 2))
        m = len(ang)
        pts = []  # order: outer-bottom, outer-top, inner-bottom, inner-top
        for r, z in ((r_out, 0), (r_out, h), (r_in, 0), (r_in, h)):
            pts.append(np.c_[r * np.cos(ang), r * np.sin(ang), np.full(m, z)])
        V = np.vstack(pts)
        ob, ot, ib, it = (np.arange(m) + q * m for q in range(4))
        tri = []
        for a in range(m - 1):
            for A, B in ((ob, ot), (ib, it), (ot, it), (ob, ib)):  # outer wall, inner wall, top, bottom
                tri += [(A[a], A[a + 1], B[a]), (A[a + 1], B[a + 1], B[a])]
        for e in (0, m - 1):  # end caps
            tri += [(ob[e], ot[e], it[e]), (ob[e], it[e], ib[e])]
        tri = np.array(tri)
        color = cfg.COLORWAY[n % len(cfg.COLORWAY)]
        txt = f"<b>{label}</b><br>{s[label]:,} patients ({frac:.1%})"
        fig.add_mesh3d(x=V[:, 0], y=V[:, 1], z=V[:, 2], i=tri[:, 0], j=tri[:, 1], k=tri[:, 2],
                       color=color, name=f"{label} ({frac:.1%})", showlegend=True, flatshading=True,
                       lighting=LIGHT, lightposition=LIGHT_POS, hovertext=[txt] * len(V), hoverinfo="text")
        if frac >= 0.03:
            mid = (a0 + a1) / 2
            rm = (r_in + r_out) / 2
            fig.add_scatter3d(x=[rm * np.cos(mid)], y=[rm * np.sin(mid)], z=[h + 0.06], mode="text",
                              text=[f"<b>{frac:.0%}</b>"], showlegend=False, hoverinfo="skip",
                              textfont=dict(size=13, color="#0F172A"))
        a0 = a1
    fig.add_scatter3d(x=[0], y=[0], z=[h / 2], mode="text", text=[f"<b>{s.sum():,}</b><br>patients"],
                      showlegend=False, hoverinfo="skip", textfont=dict(size=14, color=P["navy"]))
    hidden = dict(visible=False, showbackground=False)
    fig.update_layout(title="Patients by primary payment type (3D)", height=520,
                      margin=dict(l=0, r=0, t=56, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=0.0, font=dict(size=11)),
                      scene=dict(xaxis=hidden, yaxis=hidden, zaxis=hidden, bgcolor="rgba(0,0,0,0)",
                                 aspectmode="manual", aspectratio=dict(x=1, y=1, z=0.28),
                                 camera=dict(eye=dict(x=0.0, y=-1.25, z=1.05))))
    return fig


def hist_los(df, max_days: int = 30) -> go.Figure:
    """3D histogram: stay length (x) x severity (depth) -> patients (height)."""
    if df.empty:
        return c2d._empty()
    d = df[df["length_of_stay"] <= max_days]
    ct = pd.crosstab(d["length_of_stay"], d["severity"]).reindex(range(1, max_days + 1), fill_value=0)
    fig = go.Figure()
    for k, sev in enumerate(cfg.SEVERITY_ORDER):
        if sev not in ct:
            continue
        v = ct[sev]
        hv = [f"<b>{sev}</b><br>{day} day(s): {cnt:,} patients" for day, cnt in v.items()]
        fig.add_trace(_bars3d(list(v.index), [k] * len(v), list(v.values),
                              color=cfg.SEVERITY_COLORS[sev], hover=hv, name=sev, showlegend=True,
                              dx=0.42, dy=0.32))
    mean, med = df["length_of_stay"].mean(), df["length_of_stay"].median()
    return _layout(fig, f"Distribution of length of stay by severity (3D, ≤{max_days} days) · "
                        f"mean {mean:.1f} d, median {med:.0f} d",
                   _axis("Length of stay (days)"),
                   _axis("Severity", range(4), cfg.SEVERITY_ORDER),
                   _axis("Patients"), eye=(1.5, -1.7, 0.8), aspect=(1.8, 0.9, 0.75), legend=True)


# --------------------------------------------------------------------------- #
# Extra visuals (3D)
# --------------------------------------------------------------------------- #
def _grouped_bars(g, xcol, xorder, series, title, ztitle, zprefix="$", eye=(1.5, -1.7, 0.8),
                  xlabel="", short=18):
    """Bars for several numeric series side by side along the depth axis."""
    fig = go.Figure()
    for k, (col, label, color) in enumerate(series):
        hv = [f"<b>{x}</b><br>{label}: {zprefix}{v:,.0f}" for x, v in zip(g[xcol], g[col])]
        xpos = [xorder.index(x) for x in g[xcol]]
        fig.add_trace(_bars3d(xpos, [k] * len(g), list(g[col]), color=color, hover=hv,
                              name=label, showlegend=True, dx=0.3, dy=0.3))
    return _layout(fig, title, _axis(xlabel, range(len(xorder)), [_short(x, short) for x in xorder]),
                   _axis("", range(len(series)), [s[1] for s in series]),
                   _axis(ztitle, tickprefix=zprefix if zprefix else None), eye=eye, legend=True)


def bar_charges_age_gender(df) -> go.Figure:
    g = group_summary(df[df["gender"] != "Unknown"], ["age_group", "gender"], min_n=1)
    if g.empty:
        return c2d._empty()
    g["age_group"] = g["age_group"].astype(str)
    ages = [a for a in cfg.AGE_ORDER if a in set(g["age_group"])]
    genders = [x for x in ["Female", "Male"] if x in set(g["gender"])]
    gcol = {"Female": P["coral"], "Male": P["indigo"]}
    fig = go.Figure()
    for k, gen in enumerate(genders):
        s = g[g["gender"] == gen]
        hv = [f"<b>{a}, {gen}</b><br>Avg charges ${v:,.0f}<br>n={n:,}"
              for a, v, n in zip(s["age_group"], s["avg_charges"], s["discharges"])]
        fig.add_trace(_bars3d([ages.index(a) for a in s["age_group"]], [k] * len(s), list(s["avg_charges"]),
                              color=gcol[gen], hover=hv, name=gen, showlegend=True, dx=0.32, dy=0.3))
    return _layout(fig, "Average total charges by age group and gender (3D)",
                   _axis("Age group", range(len(ages)), ages), _axis("Gender", range(len(genders)), genders),
                   _axis("Avg charges ($)", tickprefix="$"), eye=(1.5, -1.8, 0.75), aspect=(1.6, 0.8, 0.8),
                   legend=True)


def bar_top_facilities(df, n: int = 10) -> go.Figure:
    g = top_facilities(df, n).reset_index(drop=True)
    if g.empty:
        return c2d._empty()
    hv = [f"<b>{r.facility}</b> ({r.county})<br>Patient-days {r.patient_days:,}<br>Discharges {r.discharges:,}"
          f"<br>Avg stay {r.avg_los:.1f} d<br>Total charges ${r.total_charges:,.0f}" for r in g.itertuples()]
    fig = go.Figure(_bars3d(list(range(len(g))), [0] * len(g), list(g["patient_days"]), intensity=g["avg_los"],
                            colorscale=[P["sky"], P["indigo"], P["navy"]], colorbar_title="Avg stay",
                            hover=hv, dx=0.36, dy=0.45))
    return _layout(fig, f"Top {n} high-utilisation facilities (patient-days, 3D)",
                   _axis("", range(len(g)), [_short(f, 18) for f in g["facility"]]),
                   _axis("", [0], [""], showbackground=False, showgrid=False),
                   _axis("Patient-days"), eye=(0.3, -2.0, 0.85), aspect=(2.0, 0.45, 0.9))


def bar_severity_cost(df) -> go.Figure:
    g = group_summary(df, "severity", min_n=1)
    if g.empty:
        return c2d._empty()
    g["severity"] = g["severity"].astype(str)
    order = [s for s in cfg.SEVERITY_ORDER if s in set(g["severity"])]
    fig = _grouped_bars(g, "severity", order,
                        [("median_charges", "Median charges", P["indigo"]),
                         ("avg_costs", "Average cost of care", P["teal"])],
                        "Charges and cost of care by severity (3D)", "US$", xlabel="Severity")
    # average stay shown as labels on the charges bars
    fig.add_scatter3d(x=list(range(len(order))), y=[0] * len(order), z=g["median_charges"] * 1.08,
                      mode="text", text=[f"{v:.1f} d stay" for v in g["avg_los"]], showlegend=False,
                      hoverinfo="skip", textfont=dict(size=11, color=P["coral"]))
    return fig


def bar_county_los(df, min_n: int = 100, n: int = 15) -> go.Figure:
    g = group_summary(df, "county", min_n=min_n).sort_values("avg_los", ascending=False).head(n)
    if g.empty:
        return c2d._empty("No county has enough discharges for the current filters")
    g = g.reset_index(drop=True)
    mean = df["length_of_stay"].mean()
    colors = [P["coral"] if v > mean else P["teal"] for v in g["avg_los"]]
    hv = [f"<b>{c}</b><br>Avg stay {v:.1f} d<br>n={k:,}" for c, v, k in zip(g["county"], g["avg_los"], g["discharges"])]
    pos = list(range(len(g)))
    fig = go.Figure(_bars3d(pos, [0] * len(g), list(g["avg_los"]), color=colors, hover=hv, dx=0.36, dy=0.45))
    # translucent plane at the state mean
    fig.add_mesh3d(x=[-0.6, len(g) - 0.4, len(g) - 0.4, -0.6], y=[-0.8, -0.8, 0.8, 0.8], z=[mean] * 4,
                   i=[0, 0], j=[1, 2], k=[2, 3], color=P["navy"], opacity=0.18, hoverinfo="text",
                   hovertext=[f"State mean {mean:.1f} days"] * 4, name="State mean")
    return _layout(fig, f"Counties with the longest average stays (3D; plane = state mean {mean:.1f} d)",
                   _axis("", pos, list(g["county"])), _axis("", [0], [""], showbackground=False, showgrid=False),
                   _axis("Avg stay (days)"), eye=(0.35, -2.0, 0.8), aspect=(2.0, 0.45, 0.85))


def bar_payment_billing(df) -> go.Figure:
    g = group_summary(df, "payment_type").sort_values("avg_charges", ascending=False)
    if g.empty:
        return c2d._empty()
    order = list(g["payment_type"])
    return _grouped_bars(g, "payment_type", order,
                         [("avg_charges", "Average charges", P["indigo"]), ("avg_costs", "Average cost", P["teal"])],
                         "Average billed charges vs actual cost by payment type (3D)", "US$",
                         eye=(1.2, -1.9, 0.8), short=16)


def bar_body_system(df) -> go.Figure:
    g = group_summary(df, "body_system").sort_values("discharges", ascending=False).reset_index(drop=True)
    if g.empty:
        return c2d._empty()
    hv = [f"<b>{b}</b><br>{n:,} discharges<br>Avg stay {v:.1f} d"
          for b, n, v in zip(g["body_system"], g["discharges"], g["avg_los"])]
    fig = go.Figure(_bars3d(list(range(len(g))), [0] * len(g), list(g["discharges"]), intensity=g["avg_los"],
                            colorscale=cfg.SEQ_SCALE[1:], colorbar_title="Avg stay", hover=hv, dx=0.36, dy=0.45))
    return _layout(fig, "Discharges by body system (3D, colour = average stay)",
                   _axis("", range(len(g)), [_short(b, 16) for b in g["body_system"]]),
                   _axis("", [0], [""], showbackground=False, showgrid=False),
                   _axis("Discharges"), eye=(0.3, -2.0, 0.85), aspect=(2.2, 0.45, 0.85))


def scatter_los_charges(df, sample: int = 4000) -> go.Figure:
    if df.empty:
        return c2d._empty()
    d = df.sample(min(sample, len(df)), random_state=1)
    fig = go.Figure()
    for sev in cfg.SEVERITY_ORDER:
        s = d[d["severity"] == sev]
        fig.add_scatter3d(x=s["length_of_stay"], y=s["total_charges"], z=s["total_costs"], mode="markers",
                          name=sev, marker=dict(size=2.5, color=cfg.SEVERITY_COLORS[sev], opacity=0.6),
                          customdata=s[["diagnosis", "facility"]].values,
                          hovertemplate="Stay %{x} d<br>Charges $%{y:,.0f}<br>Cost $%{z:,.0f}"
                                        "<br>%{customdata[0]}<br>%{customdata[1]}<extra>" + sev + "</extra>")
    return _layout(fig, f"Stay vs charges vs cost (3D, {len(d):,} sampled patients)",
                   _axis("Stay (days, log)", type="log"), _axis("Charges ($, log)", type="log", tickprefix="$"),
                   _axis("Cost ($, log)", type="log", tickprefix="$"), eye=(1.6, -1.5, 0.9),
                   aspect=(1, 1, 0.8), legend=True)


def bar_missing(missing: pd.Series) -> go.Figure:
    m = (missing[missing > 0] * 100).sort_values(ascending=False)
    if m.empty:
        return c2d._empty("No missing values in the raw file")
    colors = [P["coral"] if v > 70 else P["sky"] for v in m.values]
    hv = [f"<b>{c}</b><br>{v:.1f}% missing" for c, v in m.items()]
    fig = go.Figure(_bars3d(list(range(len(m))), [0] * len(m), list(m.values), color=colors, hover=hv,
                            dx=0.36, dy=0.45))
    return _layout(fig, "Missing values in the raw file (% of rows, 3D)",
                   _axis("", range(len(m)), [_short(c, 16) for c in m.index]),
                   _axis("", [0], [""], showbackground=False, showgrid=False),
                   _axis("% missing"), eye=(0.3, -2.0, 0.85), aspect=(1.8, 0.45, 0.8), height=440)


def hist_before_after(raw_charges: pd.Series, clean_charges: pd.Series) -> go.Figure:
    before = np.log10(raw_charges[raw_charges > 0].dropna())
    after = np.log10(clean_charges)
    edges = np.linspace(before.min(), before.max(), 41)
    centers = (edges[:-1] + edges[1:]) / 2
    fig = go.Figure()
    w = (edges[1] - edges[0]) * 0.42
    for k, (vals, label, color) in enumerate(((before, "Before (all rows)", P["coral"]),
                                              (after, "After (outliers excluded)", P["teal"]))):
        cnt, _ = np.histogram(vals, bins=edges)
        hv = [f"<b>{label}</b><br>${10**c:,.0f}: {n:,} patients" for c, n in zip(centers, cnt)]
        fig.add_trace(_bars3d(list(centers), [k] * len(cnt), list(cnt), color=color, hover=hv, name=label,
                              showlegend=True, dx=w, dy=0.3))
    ticks = [3, 4, 5, 6]
    return _layout(fig, "Total charges before vs after outlier handling (3D)",
                   _axis("Total charges", ticks, ["$1K", "$10K", "$100K", "$1M"]),
                   _axis("", [0, 1], ["Before", "After"]), _axis("Patients"),
                   eye=(1.4, -1.8, 0.8), aspect=(1.8, 0.7, 0.7), height=440, legend=True)
