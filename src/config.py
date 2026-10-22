"""
Central configuration for the MediScope dashboard.

Everything that depends on the *shape* of the input file lives here, so a
different CSV (for example the course-provided extract) can be swapped in by
editing only this module:

* ``DATA_PATH``      - where the raw file lives (plain CSV or .csv.gz).
* ``COLUMN_ALIASES`` - maps the source column names (after snake_casing) to the
                       canonical names used throughout the app.
"""
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths & source metadata
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data" / "raw" / "sparcs_2016_inpatient_sample.csv.gz"

SOURCE_NAME = "Hospital Inpatient Discharges (SPARCS De-Identified): 2016"
SOURCE_URL = "https://health.data.ny.gov/Health/Hospital-Inpatient-Discharges-SPARCS-De-Identified/gnzp-ekau"
SOURCE_API = "https://health.data.ny.gov/resource/gnzp-ekau.csv"
SOURCE_YEAR = 2016

# --------------------------------------------------------------------------- #
# Column-name mapping  (source name in snake_case  ->  canonical name)
# --------------------------------------------------------------------------- #
# The raw header is first converted to snake_case (e.g. "Total Charges" ->
# "total_charges"), then renamed with this dictionary. Columns missing from the
# mapping keep their snake_case name. Add aliases here for a new file.
COLUMN_ALIASES = {
    # geography / facility
    "health_service_area": "service_area",
    "hospital_service_area": "service_area",
    "hospital_county": "county",
    "facility_name": "facility",
    "facility_id": "facility_id",
    "permanent_facility_id": "facility_id",
    # demographics
    "age_group": "age_group",
    "gender": "gender",
    "race": "race",
    "ethnicity": "ethnicity",
    # stay
    "length_of_stay": "length_of_stay",
    "type_of_admission": "admission_type",
    "patient_disposition": "disposition",
    "emergency_department_indicator": "ed_indicator",
    # clinical
    "ccs_diagnosis_code": "diagnosis_code",
    "ccs_diagnosis_description": "diagnosis",
    "ccsr_diagnosis_code": "diagnosis_code",
    "ccsr_diagnosis_description": "diagnosis",
    "ccs_procedure_description": "procedure",
    "ccsr_procedure_description": "procedure",
    "apr_mdc_description": "mdc",
    "apr_severity_of_illness_code": "severity_code",
    "apr_severity_of_illness_description": "severity",
    "apr_severity_of_illness": "severity",
    "apr_risk_of_mortality": "mortality_risk",
    "apr_medical_surgical_description": "medical_surgical",
    "apr_medical_surgical": "medical_surgical",
    # billing
    "payment_typology_1": "payment_type",
    "total_charges": "total_charges",
    "total_costs": "total_costs",
    "birth_weight": "birth_weight",
}

# Columns the dashboard cannot work without (checked after renaming).
REQUIRED_COLUMNS = [
    "county", "facility", "age_group", "gender", "length_of_stay",
    "diagnosis", "severity", "payment_type", "total_charges", "total_costs",
]

# --------------------------------------------------------------------------- #
# Cleaning parameters
# --------------------------------------------------------------------------- #
NULL_HEAVY_THRESHOLD = 0.70   # drop columns that are >70 % missing
IQR_MULTIPLIER = 1.5          # Tukey fence, applied to log10(total charges)
LOS_CAP = 120                 # SPARCS top-codes stays at "120 +"

# Canonical category orders (used for sorting and chart axes)
AGE_ORDER = ["0 to 17", "18 to 29", "30 to 49", "50 to 69", "70 or Older"]
SEVERITY_ORDER = ["Minor", "Moderate", "Major", "Extreme"]
GENDER_MAP = {"M": "Male", "F": "Female", "U": "Unknown"}
LOS_BUCKETS = [0, 2, 5, 10, 30, float("inf")]
LOS_BUCKET_LABELS = ["1-2 days", "3-5 days", "6-10 days", "11-30 days", "31+ days"]

# --------------------------------------------------------------------------- #
# Visual identity
# --------------------------------------------------------------------------- #
PALETTE = {
    "navy": "#0B1F3A",
    "indigo": "#4338CA",
    "teal": "#0EA5A4",
    "coral": "#F2707A",
    "amber": "#F4A261",
    "sky": "#38BDF8",
    "violet": "#8B5CF6",
    "slate": "#475569",
    "bg": "#F4F7FB",
    "card": "#FFFFFF",
}
# Ordered discrete colour sequence for charts
COLORWAY = ["#0EA5A4", "#4338CA", "#F2707A", "#F4A261", "#38BDF8",
            "#8B5CF6", "#0B1F3A", "#22C55E", "#EC4899", "#94A3B8"]
SEVERITY_COLORS = {"Minor": "#0EA5A4", "Moderate": "#38BDF8",
                   "Major": "#F4A261", "Extreme": "#F2707A"}
# Sequential scale for heatmaps: soft mint -> teal -> indigo -> navy
SEQ_SCALE = ["#ECFDF5", "#99F6E4", "#2DD4BF", "#0EA5A4", "#4338CA", "#0B1F3A"]

STUDENT = {
    "name": "Dhwanan Bhatt",
    "student_id": "2505556",
    "crs": "Artificial Intelligence",
    "course": "Mathematics for AI-II",
    "repo": "IADAI2022505556-DhwananBhatt",
}

# --------------------------------------------------------------------------- #
# Interactive chart options (shared by 2D and 3D chart modules and the app)
# --------------------------------------------------------------------------- #
RANK_METRICS = {"avg_los": "Average stay (days)", "median_los": "Median stay (days)",
                "avg_charges": "Average charges ($)", "median_charges": "Median charges ($)"}
VALUE_COLS = {"total_charges": "Total charges ($)", "total_costs": "Total costs ($)",
              "charge_per_day": "Charges per day ($)"}
BREAKDOWNS = {"severity": "Severity", "age_group": "Age group", "gender": "Gender"}
GROUP_LEVELS = {"diagnosis": "Diagnosis (CCS)", "body_system": "Body system"}
SHARE_BY = {"payment_type": "Payment type", "admission_type": "Admission type", "race": "Race"}
HEAT_COLUMNS = {"severity": "Severity", "age_group": "Age group", "gender": "Gender"}
HEAT_METRICS = {"length_of_stay": "Average stay (days)", "total_charges": "Average charges ($)",
                "charge_per_day": "Average charges per day ($)"}
AGE_METRICS = {"avg_charges": "Average charges ($)", "median_charges": "Median charges ($)",
               "avg_costs": "Average cost ($)", "avg_los": "Average stay (days)"}
GENDER_COLORS = {"Female": "#F2707A", "Male": "#4338CA", "Unknown": "#94A3B8"}


def is_money(metric: str) -> bool:
    return any(t in metric for t in ("charge", "cost"))


def breakdown_colors(col: str) -> dict:
    """Consistent colour per category level for any breakdown column."""
    if col == "severity":
        return SEVERITY_COLORS
    if col == "gender":
        return GENDER_COLORS
    if col == "age_group":
        return {a: COLORWAY[i] for i, a in enumerate(AGE_ORDER)}
    return {}


def level_order(col: str, present) -> list:
    present = [str(p) for p in present]
    base = {"severity": SEVERITY_ORDER, "age_group": AGE_ORDER, "gender": ["Female", "Male", "Unknown"]}.get(col)
    if base:
        return [b for b in base if b in present]
    return sorted(present)
