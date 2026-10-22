"""
Stand-alone EDA script (no Streamlit needed): runs the cleaning pipeline and
prints the statistical summaries, groupby/agg tables, pivot tables and the five
research-question insights used in the dashboard.

Run from the repo root:  python notebooks/eda.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import analysis as an  # noqa: E402
from src.cleaning import clean_pipeline, load_raw  # noqa: E402

pd.set_option("display.width", 160, "display.max_columns", 20)

raw = load_raw()
df, report = clean_pipeline(raw)
df = df[~df["is_charge_outlier"]]  # same default as the dashboard

print("=== Cleaning log ===")
print(report.as_frame().to_string(index=False))
print("\n=== Numeric summary ===")
print(an.numeric_summary(df).round(2))
print("\n=== Diagnosis x severity: average stay (pivot_table) ===")
print(an.diagnosis_severity_pivot(df))
print("\n=== Region x payment type: median charges (pivot_table) ===")
print(an.region_payment_pivot(df))
print("\n=== Age group x gender: average charges ===")
print(an.age_gender_pivot(df))
print("\n=== Top high-utilisation facilities ===")
print(an.top_facilities(df).to_string(index=False))
print("\n=== Research questions ===")
for i, fn in enumerate([an.rq1_diagnosis_long_stays, an.rq2_age_charges, an.rq3_severity_cost,
                        an.rq4_county_stays, an.rq5_payment_billing], 1):
    print(f"Q{i}: {fn(df)[1].replace('**', '')}")
