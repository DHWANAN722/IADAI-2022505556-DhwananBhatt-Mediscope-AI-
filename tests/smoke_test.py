"""Smoke test: pipeline, analysis, every chart, and a full headless app run.
Run:  python tests/smoke_test.py
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.simplefilter("error")  # treat any warning as a failure

from src import analysis as an, charts as ch2d, charts3d as ch3d
from src.cleaning import clean_pipeline, load_raw

raw = load_raw()
df, rep = clean_pipeline(raw)
assert len(df) > 0 and df["length_of_stay"].min() >= 1 and df["total_charges"].min() > 0
print("clean:", rep.raw_shape, "->", rep.clean_shape)

for fn in (an.rq1_diagnosis_long_stays, an.rq2_age_charges, an.rq3_severity_cost,
           an.rq4_county_stays, an.rq5_payment_billing):
    _, txt = fn(df)
    print(f"{fn.__name__}: {txt}\n")
an.numeric_summary(df); an.diagnosis_severity_pivot(df); an.region_payment_pivot(df)
an.age_gender_pivot(df); an.top_facilities(df)

figs = []
for ch in (ch2d, ch3d):
    figs += [ch.bar_avg_los_by_diagnosis(df), ch.box_charges_by_severity(df), ch.heatmap_facility_county(df),
             ch.heatmap_county_admission(df), ch.donut_payment_type(df), ch.hist_los(df),
             ch.bar_charges_age_gender(df), ch.bar_top_facilities(df), ch.bar_severity_cost(df),
             ch.bar_county_los(df), ch.bar_payment_billing(df), ch.bar_body_system(df),
             ch.scatter_los_charges(df), ch.bar_missing(rep.raw_missing),
             ch.hist_before_after(df["total_charges"], df["total_charges"]),
             ch.bar_avg_los_by_diagnosis(df.iloc[:0]), ch.box_charges_by_severity(df, log_scale=False)]
for f in figs:
    f.to_json()
print(f"{len(figs)} figures built OK")

warnings.simplefilter("default")
from streamlit.testing.v1 import AppTest
at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=120).run()
assert not at.exception, at.exception
pages = at.radio(key="page").options
for pg in pages:  # render every page
    at.radio(key="page").set_value(pg).run()
    assert not at.exception, (pg, at.exception)
print("AppTest: every page renders without exceptions:", pages)
# exercise a filter
at.sidebar.multiselect[3].set_value(["Extreme"]).run()
assert not at.exception, at.exception
print("AppTest with severity=Extreme filter: OK")
at.sidebar.toggle[1].set_value(False).run()   # 3D off -> 2D fallback
assert not at.exception, at.exception
print("AppTest with 2D fallback: OK")
