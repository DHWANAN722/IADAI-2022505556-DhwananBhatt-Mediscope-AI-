"""
Exploratory analysis helpers: groupby/agg summaries, pivot tables and the
five research questions. Every insight sentence is computed from the
(filtered) data passed in - no hard-coded numbers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_GROUP = 30  # minimum records for a group to be ranked (avoids tiny-n noise)


def _money(x: float) -> str:
    if pd.isna(x):
        return "n/a"
    if abs(x) >= 1e9:
        return f"${x/1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"${x/1e6:,.1f}M"
    return f"${x:,.0f}"


# --------------------------------------------------------------------------- #
# KPIs & summaries
# --------------------------------------------------------------------------- #
def kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    return {
        "discharges": len(df),
        "avg_los": df["length_of_stay"].mean(),
        "median_los": df["length_of_stay"].median(),
        "median_charges": df["total_charges"].median(),
        "total_charges": df["total_charges"].sum(),
        "avg_ccr": df["cost_to_charge_ratio"].mean(),
        "pct_emergency": df["is_emergency"].mean(),
        "pct_long": df["is_long_stay"].mean(),
        "facilities": df["facility"].nunique(),
    }


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    """describe() plus skewness for the key numeric measures."""
    cols = ["length_of_stay", "total_charges", "total_costs", "charge_per_day",
            "cost_to_charge_ratio"]
    desc = df[cols].describe(percentiles=[.25, .5, .75, .9, .99]).T
    desc["skew"] = df[cols].skew()
    return desc


def group_summary(df: pd.DataFrame, by, min_n: int = MIN_GROUP) -> pd.DataFrame:
    """Standard groupby/agg block reused by several pages."""
    g = (df.groupby(by, observed=True)
           .agg(discharges=("length_of_stay", "size"),
                avg_los=("length_of_stay", "mean"),
                median_los=("length_of_stay", "median"),
                avg_charges=("total_charges", "mean"),
                median_charges=("total_charges", "median"),
                avg_costs=("total_costs", "mean"),
                avg_charge_per_day=("charge_per_day", "mean"),
                cost_to_charge=("cost_to_charge_ratio", "mean"))
           .reset_index())
    return g[g["discharges"] >= min_n]


def diagnosis_severity_pivot(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Average stay by diagnosis (rows) x severity (columns)."""
    top = df["diagnosis"].value_counts().head(top_n).index
    return pd.pivot_table(df[df["diagnosis"].isin(top)], index="diagnosis",
                          columns="severity", values="length_of_stay",
                          aggfunc="mean", observed=True).round(1)


def region_payment_pivot(df: pd.DataFrame, value="total_charges", aggfunc="median") -> pd.DataFrame:
    """Charges by service region (rows) x payment type (columns)."""
    return pd.pivot_table(df, index="service_area", columns="payment_type",
                          values=value, aggfunc=aggfunc, observed=True).round(0)


def age_gender_pivot(df: pd.DataFrame) -> pd.DataFrame:
    return pd.pivot_table(df[df["gender"] != "Unknown"], index="age_group", columns="gender", values="total_charges",
                          aggfunc="mean", observed=True).round(0)


def top_facilities(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """High-utilisation facilities: most patient-days (discharges x LOS)."""
    g = (df.groupby(["facility", "county"], observed=True)
           .agg(discharges=("length_of_stay", "size"),
                patient_days=("length_of_stay", "sum"),
                avg_los=("length_of_stay", "mean"),
                total_charges=("total_charges", "sum"),
                median_charges=("total_charges", "median"))
           .reset_index()
           .sort_values("patient_days", ascending=False)
           .head(n))
    return g


# --------------------------------------------------------------------------- #
# Research questions
# --------------------------------------------------------------------------- #
def rq1_diagnosis_long_stays(df):
    g = group_summary(df, "diagnosis").sort_values("avg_los", ascending=False)
    if g.empty:
        return g, "Not enough data for the current filters."
    top = g.iloc[0]
    overall = df["length_of_stay"].mean()
    top3 = ", ".join(g["diagnosis"].head(3))
    txt = (f"**{top['diagnosis']}** has the longest average stay at **{top['avg_los']:.1f} days** "
           f"({top['avg_los']/overall:.1f}x the overall mean of {overall:.1f} days, n={int(top['discharges']):,}). "
           f"The top three long-stay diagnoses are {top3}.")
    return g, txt


def rq2_age_charges(df):
    g = group_summary(df, "age_group", min_n=1).sort_values("age_group")
    if g.empty:
        return g, "Not enough data for the current filters."
    hi = g.loc[g["avg_charges"].idxmax()]
    lo = g.loc[g["avg_charges"].idxmin()]
    txt = (f"Patients aged **{hi['age_group']}** incur the highest average charges "
           f"(**{_money(hi['avg_charges'])}**, median {_money(hi['median_charges'])}), "
           f"**{hi['avg_charges']/lo['avg_charges']:.1f}x** the **{lo['age_group']}** group "
           f"({_money(lo['avg_charges'])}).")
    return g, txt


def rq3_severity_cost(df):
    g = group_summary(df, "severity", min_n=1).sort_values("severity")
    if len(g) < 2:
        return g, "Not enough severity levels in the current filter."
    first, last = g.iloc[0], g.iloc[-1]
    rho = df[["severity_level", "total_costs"]].corr(method="spearman").iloc[0, 1]
    txt = (f"Cost rises steadily with severity: median charges go from **{_money(first['median_charges'])}** "
           f"({first['severity']}) to **{_money(last['median_charges'])}** ({last['severity']}), "
           f"a **{last['median_charges']/first['median_charges']:.1f}x** jump. Average cost to the hospital "
           f"rises from {_money(first['avg_costs'])} to {_money(last['avg_costs'])}. "
           f"Spearman correlation between severity level and total cost: **rho = {rho:.2f}**.")
    return g, txt


def rq4_county_stays(df, min_n: int = 100):
    g = group_summary(df, "county", min_n=min_n).sort_values("avg_los", ascending=False)
    if g.empty:
        return g, "Not enough data for the current filters."
    overall = df["length_of_stay"].mean()
    top, bottom = g.iloc[0], g.iloc[-1]
    above = int((g["avg_los"] > overall).sum())
    txt = (f"**{top['county']}** county has the longest average stay (**{top['avg_los']:.1f} days**, "
           f"n={int(top['discharges']):,}) vs **{bottom['county']}** at the low end ({bottom['avg_los']:.1f} days). "
           f"{above} of {len(g)} counties (with >= {min_n} discharges) sit above the state mean of {overall:.1f} days.")
    return g, txt


def rq5_payment_billing(df):
    g = group_summary(df, "payment_type").sort_values("avg_charges", ascending=False)
    if g.empty:
        return g, "Not enough data for the current filters."
    hi, lo = g.iloc[0], g.iloc[-1]
    ccr_hi = g.loc[g["cost_to_charge"].idxmax()]
    ccr_lo = g.loc[g["cost_to_charge"].idxmin()]
    txt = (f"**{hi['payment_type']}** patients carry the highest average bill (**{_money(hi['avg_charges'])}**, "
           f"avg stay {hi['avg_los']:.1f} days) while **{lo['payment_type']}** has the lowest "
           f"({_money(lo['avg_charges'])}). Cost-to-charge ratio ranges from {ccr_lo['cost_to_charge']:.2f} "
           f"({ccr_lo['payment_type']}) to {ccr_hi['cost_to_charge']:.2f} ({ccr_hi['payment_type']}), so billed "
           f"charges are typically {1/g['cost_to_charge'].mean():.1f}x the actual cost of care.")
    return g, txt


def ranked(df: pd.DataFrame, group: str = "diagnosis", metric: str = "avg_los", top_n: int = 15) -> pd.DataFrame:
    """Top-N groups by a metric. Adds ``key`` (the filter value for cross-filtering)
    and ``label`` (display text)."""
    by = ["diagnosis_code", "diagnosis"] if group == "diagnosis" else [group]
    g = group_summary(df, by).nlargest(top_n, metric).reset_index(drop=True)
    g["key"] = g[group].astype(str)
    if group == "diagnosis":
        g["label"] = g["diagnosis"] + "  [" + g["diagnosis_code"].astype(str) + "]"
    else:
        g["label"] = g[group].astype(str)
    return g
