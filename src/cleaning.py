"""
Data loading, cleaning and feature engineering for the SPARCS inpatient data.

The pipeline is a sequence of small, pure functions (DataFrame in, DataFrame
out). ``clean_pipeline`` runs them in order and records a step-by-step audit
log that the "Data Cleaning" page of the app displays.

Steps
-----
1.  standardise_column_names   - snake_case + alias mapping from config
2.  parse_length_of_stay       - "120 +" -> 120, coerce to numeric
3.  parse_money                - "$1,234.50" -> 1234.5 for charges/costs
4.  drop_invalid_rows          - negative / zero / missing stays & charges
5.  standardise_categoricals   - age, gender, race, severity, payment labels
6.  map_diagnosis_categories   - CCS code -> body-system category
7.  drop_null_heavy_columns    - e.g. birth weight (mostly 0 / empty)
8.  flag_charge_outliers       - Tukey IQR fence on log10(total charges)
9.  engineer_features          - charge/day, cost-to-charge, LOS bucket ...
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config as cfg


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #
@dataclass
class CleaningReport:
    """Collects what each cleaning step did, for display in the app."""
    raw_shape: tuple = (0, 0)
    clean_shape: tuple = (0, 0)
    steps: list = field(default_factory=list)
    dropped_columns: list = field(default_factory=list)
    raw_missing: pd.Series | None = None
    raw_dtypes: pd.Series | None = None
    outlier_fence: tuple = (np.nan, np.nan)

    def log(self, step: str, detail: str, rows_before: int, rows_after: int) -> None:
        self.steps.append({
            "Step": step,
            "What was done": detail,
            "Rows before": rows_before,
            "Rows after": rows_after,
            "Rows removed": rows_before - rows_after,
        })

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.steps)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_raw(path=cfg.DATA_PATH) -> pd.DataFrame:
    """Read the raw extract exactly as delivered (every column as text)."""
    return pd.read_csv(path, dtype=str, keep_default_na=True, low_memory=False)


# --------------------------------------------------------------------------- #
# Individual cleaning steps
# --------------------------------------------------------------------------- #
def _to_snake(name: str) -> str:
    """'APR Severity of Illness Description' -> 'apr_severity_of_illness_description'."""
    name = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip())
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.strip("_").lower()


def standardise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """snake_case every header, then apply the alias map from config."""
    out = df.copy()
    out.columns = [_to_snake(c) for c in out.columns]
    out = out.rename(columns=cfg.COLUMN_ALIASES)
    # If two source columns map to the same name keep the first one
    out = out.loc[:, ~out.columns.duplicated()]
    missing = [c for c in cfg.REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise KeyError(f"Input file is missing required columns {missing}. "
                       "Add aliases for them in src/config.py::COLUMN_ALIASES.")
    return out


def parse_length_of_stay(df: pd.DataFrame) -> pd.DataFrame:
    """SPARCS top-codes long stays as '120 +'. Strip non-digits and cast."""
    out = df.copy()
    los = out["length_of_stay"].astype(str).str.replace(r"[^\d.\-]", "", regex=True)
    out["length_of_stay"] = pd.to_numeric(los, errors="coerce")
    out["los_top_coded"] = df["length_of_stay"].astype(str).str.contains(r"\+", na=False)
    return out


def _money_to_float(s: pd.Series) -> pd.Series:
    """'$12,345.67' / '12345.67' / ' (12.0) ' -> float. Unparseable -> NaN."""
    txt = s.astype(str).str.strip()
    negative = txt.str.startswith("(") & txt.str.endswith(")")
    num = pd.to_numeric(txt.str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")
    return num.where(~negative, -num)


def parse_money(df: pd.DataFrame) -> pd.DataFrame:
    """Convert the currency-formatted billing columns to floats."""
    out = df.copy()
    for col in ("total_charges", "total_costs"):
        out[col] = _money_to_float(out[col])
    return out


def raw_charges(raw: pd.DataFrame) -> pd.Series:
    """Total charges from the *raw* file as floats (used for before/after plots)."""
    return _money_to_float(standardise_column_names(raw)["total_charges"])


def drop_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove records that cannot be analysed: missing/<=0 stay or charges."""
    valid = (
        df["length_of_stay"].notna() & (df["length_of_stay"] >= 1)
        & df["total_charges"].notna() & (df["total_charges"] > 0)
        & df["total_costs"].notna() & (df["total_costs"] > 0)
    )
    return df.loc[valid].copy()


def _title(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def standardise_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonise labels and make ordered categoricals for sensible sorting."""
    out = df.copy()

    # Age group: unify spacing/case, then ordered category
    age = _title(out["age_group"]).str.replace(r"(?i)or older", "or Older", regex=True)
    out["age_group"] = pd.Categorical(age, categories=cfg.AGE_ORDER, ordered=True)

    # Gender: M/F/U -> readable words
    g = _title(out["gender"]).str.upper().str[:1]
    out["gender"] = g.map(cfg.GENDER_MAP).fillna("Unknown")

    # Race: tidy labels
    if "race" in out:
        race = _title(out["race"]).replace({
            "Black/African American": "Black / African American",
            "Multi-racial": "Multi-racial", "Other Race": "Other",
            "nan": "Unknown"})
        out["race"] = race

    # Severity: prefer the description, fall back to the numeric code
    sev = _title(out["severity"]).str.capitalize()
    if "severity_code" in out:
        code_map = {"1": "Minor", "2": "Moderate", "3": "Major", "4": "Extreme"}
        sev = sev.where(sev.isin(cfg.SEVERITY_ORDER), out["severity_code"].map(code_map))
    out["severity"] = pd.Categorical(sev, categories=cfg.SEVERITY_ORDER, ordered=True)
    # A handful of records carry severity code 0 ("not assigned"); they cannot be
    # used in severity comparisons, so they are removed (logged in the report).
    out = out[out["severity"].notna()].copy()
    out["severity_level"] = out["severity"].cat.codes.replace(-1, np.nan) + 1

    # Payment type, county, facility, diagnosis: whitespace + missing labels
    for col in ("payment_type", "county", "facility", "diagnosis", "admission_type",
                "disposition", "mdc", "medical_surgical", "mortality_risk", "ethnicity"):
        if col in out:
            out[col] = _title(out[col]).replace({"nan": "Unknown", "": "Unknown"})
    if "mdc" in out:
        out["mdc"] = out["mdc"].str.title().str.replace(" And ", " & ").str.replace(" Of ", " of ")
    return out


# CCS single-level diagnosis codes -> body-system chapter (AHRQ CCS multi-level 1)
_CCS_CHAPTERS = [
    ((1, 10), "Infectious & Parasitic"),
    ((11, 47), "Neoplasms (Cancer)"),
    ((48, 58), "Endocrine & Metabolic"),
    ((59, 64), "Blood Disorders"),
    ((65, 75), "Mental & Behavioral"),
    ((76, 95), "Nervous System"),
    ((96, 121), "Circulatory (Heart & Vessels)"),
    ((122, 134), "Respiratory"),
    ((135, 155), "Digestive"),
    ((156, 175), "Genitourinary"),
    ((176, 196), "Pregnancy & Childbirth"),
    ((197, 200), "Skin"),
    ((201, 212), "Musculoskeletal"),
    ((213, 217), "Congenital Anomalies"),
    ((218, 224), "Perinatal (Newborn)"),
    ((225, 244), "Injury & Poisoning"),
    ((245, 259), "Symptoms & Other Factors"),
    ((650, 670), "Mental & Behavioral"),
    ((2601, 2621), "Injury & Poisoning"),
]


def ccs_to_body_system(code) -> str:
    """Return the body-system category for a CCS diagnosis code."""
    try:
        c = int(float(code))
    except (TypeError, ValueError):
        return "Unclassified"
    for (lo, hi), label in _CCS_CHAPTERS:
        if lo <= c <= hi:
            return label
    return "Unclassified"


def map_diagnosis_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Readable diagnosis label (code + description) and a broad body system."""
    out = df.copy()
    if "diagnosis_code" in out:
        out["body_system"] = out["diagnosis_code"].map(ccs_to_body_system)
        # Codes outside the CCS chapter ranges (or non-numeric CCSR codes such as
        # 'CIR007' in newer SPARCS years) are grouped as "Other / Unclassified".
        out["body_system"] = out["body_system"].replace("Unclassified", "Other / Unclassified")
    else:
        out["body_system"] = out.get("mdc", "Unclassified")
    # Short display label, e.g. "Septicemia (except in labor)"
    out["diagnosis"] = out["diagnosis"].str.slice(0, 60)
    return out


def drop_null_heavy_columns(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Drop columns that are mostly empty. Birth weight is recorded as 0 for
    every non-newborn, so zeros are treated as missing for that column."""
    out = df.copy()
    if "birth_weight" in out:
        bw = pd.to_numeric(out["birth_weight"], errors="coerce")
        out["birth_weight"] = bw.where(bw > 0)
    share_missing = out.isna().mean()
    # Also treat ID-like/free-text columns that add nothing analytically
    to_drop = share_missing[share_missing > cfg.NULL_HEAVY_THRESHOLD].index.tolist()
    to_drop += [c for c in ("abortion_edit_indicator", "operating_certificate_number",
                            "zip_code_3_digits", "discharge_year") if c in out]
    to_drop = sorted(set(to_drop))
    report.dropped_columns = [
        (c, f"{share_missing.get(c, 0):.1%} missing" if share_missing.get(c, 0) > cfg.NULL_HEAVY_THRESHOLD
         else "not analytically useful") for c in to_drop]
    return out.drop(columns=to_drop)


def flag_charge_outliers(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Flag extreme charges with a Tukey IQR fence on log10(charges).

    Hospital charges are strongly right-skewed, so a fence on the raw values
    would flag ~10 % of legitimate high-acuity stays. Working on the log scale
    flags only the genuinely extreme records. They are *flagged*, not deleted;
    the sidebar lets the user exclude them.
    """
    out = df.copy()
    logc = np.log10(out["total_charges"])
    q1, q3 = logc.quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - cfg.IQR_MULTIPLIER * iqr, q3 + cfg.IQR_MULTIPLIER * iqr
    out["is_charge_outlier"] = (logc < lo) | (logc > hi)
    report.outlier_fence = (10 ** lo, 10 ** hi)
    return out


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derived metrics used across the dashboard."""
    out = df.copy()
    out["charge_per_day"] = out["total_charges"] / out["length_of_stay"]
    out["cost_per_day"] = out["total_costs"] / out["length_of_stay"]
    out["cost_to_charge_ratio"] = out["total_costs"] / out["total_charges"]
    out["markup"] = out["total_charges"] / out["total_costs"]
    out["los_bucket"] = pd.cut(out["length_of_stay"], bins=cfg.LOS_BUCKETS,
                               labels=cfg.LOS_BUCKET_LABELS, right=True)
    out["is_long_stay"] = out["length_of_stay"] > 10
    out["is_emergency"] = out.get("ed_indicator", pd.Series("N", index=out.index)).eq("Y")
    out["is_surgical"] = out.get("medical_surgical", pd.Series("", index=out.index)).str.lower().eq("surgical")
    out["charge_band"] = pd.qcut(out["total_charges"], 4,
                                 labels=["Low", "Medium", "High", "Very high"])
    return out


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def clean_pipeline(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Run every step in order and return (clean_df, report)."""
    rep = CleaningReport(raw_shape=raw.shape)
    rep.raw_missing = raw.isna().mean().sort_values(ascending=False)
    rep.raw_dtypes = raw.dtypes.astype(str)

    df = standardise_column_names(raw)
    rep.log("1. Rename columns", "Converted headers to snake_case and applied the alias map",
            len(raw), len(df))

    n = len(df); df = parse_length_of_stay(df)
    rep.log("2. Parse length of stay", f"'120 +' -> 120; {int(df['los_top_coded'].sum())} stays were top-coded",
            n, len(df))

    n = len(df); df = parse_money(df)
    rep.log("3. Parse currency", "Total charges / costs text -> float (removed $ and commas)", n, len(df))

    n = len(df); df = drop_invalid_rows(df)
    rep.log("4. Drop invalid records", "Removed missing, zero or negative stays / charges / costs", n, len(df))

    n = len(df); df = standardise_categoricals(df)
    rep.log("5. Standardise categories",
            "Age, gender (M/F/U -> words), race, severity, payment labels; dropped unassigned severity",
            n, len(df))

    n = len(df); df = map_diagnosis_categories(df)
    rep.log("6. Map diagnosis codes", f"CCS codes -> {df['body_system'].nunique()} body-system categories", n, len(df))

    n = len(df); df = drop_null_heavy_columns(df, rep)
    rep.log("7. Drop null-heavy columns", ", ".join(c for c, _ in rep.dropped_columns) or "none", n, len(df))

    n = len(df); df = flag_charge_outliers(df, rep)
    rep.log("8. Flag charge outliers",
            f"IQR fence on log10 charges: ${rep.outlier_fence[0]:,.0f} - ${rep.outlier_fence[1]:,.0f}; "
            f"{int(df['is_charge_outlier'].sum())} flagged", n, len(df))

    n = len(df); df = engineer_features(df)
    rep.log("9. Feature engineering",
            "charge_per_day, cost_per_day, cost_to_charge_ratio, markup, los_bucket, "
            "is_long_stay, is_emergency, is_surgical, charge_band", n, len(df))

    df = df.reset_index(drop=True)
    rep.clean_shape = df.shape
    return df, rep
