"""
Click-to-filter (cross-filtering) helpers.

2D Plotly charts are rendered with ``st.plotly_chart(on_select=...)``. Each
selectable trace stores the category it represents in ``customdata[0]`` so a
clicked / box- / lasso-selected point can be translated into a dashboard filter.
Active cross-filters live in ``st.session_state["xf"]`` as
``{column: [values, ...]}`` and are shown as removable chips.

Plotly 3D traces (Mesh3d / Scatter3d) do not emit selection events in
Streamlit, so in 3D mode the per-chart option controls and camera presets are
the interaction model.
"""
from __future__ import annotations

import pandas as pd

XF_KEY = "xf"
XF_LABELS = {
    "diagnosis": "Diagnosis", "body_system": "Body system", "county": "County",
    "payment_type": "Payment", "facility": "Facility", "severity": "Severity",
    "age_group": "Age group",
}


def points_to_values(points) -> list[str]:
    """Extract the filter values (customdata[0]) from Plotly selection points."""
    vals = []
    for p in points or []:
        cd = p.get("customdata") if hasattr(p, "get") else None
        if cd is None:
            continue
        v = cd[0] if isinstance(cd, (list, tuple)) else cd
        if v is not None and str(v) != "":
            vals.append(str(v))
    return sorted(set(vals))


def apply_cross_filters(df: pd.DataFrame, xf: dict) -> pd.DataFrame:
    """Keep rows whose column value is in every active cross-filter."""
    for col, vals in (xf or {}).items():
        if vals and col in df.columns:
            df = df[df[col].astype(str).isin(vals)]
    return df


def describe(col: str, vals: list[str], max_items: int = 2) -> str:
    shown = ", ".join(v if len(v) <= 28 else v[:27] + "…" for v in vals[:max_items])
    more = f" +{len(vals) - max_items}" if len(vals) > max_items else ""
    return f"{XF_LABELS.get(col, col)}: {shown}{more}"
