"""Custom CSS and small HTML components (header banner, KPI cards, insight boxes)."""
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap

from . import config as cfg

P = cfg.PALETTE

# Light colormap for pandas Styler gradients (keeps dark table text readable)
SOFT_CMAP = LinearSegmentedColormap.from_list("mediscope_soft", ["#F0FDFA", "#99F6E4", "#A5B4FC"])

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1380px; }}

/* ---------- header banner ---------- */
.ms-hero {{
  background: linear-gradient(120deg, {P['navy']} 0%, {P['indigo']} 55%, {P['teal']} 100%);
  border-radius: 20px; padding: 26px 32px; color: #fff; margin-bottom: 18px;
  box-shadow: 0 12px 30px rgba(11,31,58,.25); position: relative; overflow: hidden;
}}
.ms-hero:after {{
  content: ""; position: absolute; right: -60px; top: -60px; width: 260px; height: 260px;
  border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,.18), rgba(255,255,255,0) 70%);
}}
.ms-hero h1 {{ color: #fff; font-size: 2.0rem; font-weight: 800; margin: 0; letter-spacing: -.5px; padding: 0; }}
.ms-hero p {{ color: rgba(255,255,255,.85); margin: 6px 0 0 0; font-size: 1.0rem; }}
.ms-badge {{
  display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.3);
  color: #fff; border-radius: 999px; padding: 3px 12px; font-size: .78rem; margin: 10px 6px 0 0;
}}

/* ---------- KPI cards ---------- */
.ms-kpi {{
  background: {P['card']}; border-radius: 16px; padding: 16px 18px 14px 18px; height: 100%;
  box-shadow: 0 4px 16px rgba(15,23,42,.07); border: 1px solid #E6ECF5;
  border-top: 4px solid var(--accent); transition: transform .15s ease, box-shadow .15s ease;
}}
.ms-kpi:hover {{ transform: translateY(-2px); box-shadow: 0 10px 24px rgba(15,23,42,.12); }}
.ms-kpi .lbl {{ color: {P['slate']}; font-size: .78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .6px; }}
.ms-kpi .val {{ color: {P['navy']}; font-size: 1.7rem; font-weight: 800; margin-top: 4px; line-height: 1.15; }}
.ms-kpi .sub {{ color: #64748B; font-size: .78rem; margin-top: 2px; }}

/* ---------- insight & section boxes ---------- */
.ms-insight {{
  background: linear-gradient(90deg, rgba(14,165,164,.10), rgba(67,56,202,.06));
  border-left: 5px solid {P['teal']}; border-radius: 12px; padding: 14px 18px; margin: 6px 0 14px 0;
  color: #0F172A; font-size: .97rem;
}}
.ms-insight b, .ms-insight strong {{ color: {P['indigo']}; }}
.ms-q {{ color: {P['navy']}; font-weight: 800; font-size: 1.25rem; margin: 6px 0 2px 0; }}
.ms-qnum {{
  display: inline-block; background: {P['coral']}; color: #fff; border-radius: 8px;
  padding: 1px 9px; margin-right: 8px; font-size: .95rem;
}}
.ms-card {{
  background: #fff; border-radius: 16px; padding: 18px 22px; border: 1px solid #E6ECF5;
  box-shadow: 0 4px 16px rgba(15,23,42,.06); margin-bottom: 12px;
}}

/* ---------- containers around charts ---------- */
div[data-testid="stPlotlyChart"] {{
  background: #fff; border-radius: 16px; padding: 8px 10px; border: 1px solid #E6ECF5;
  box-shadow: 0 4px 16px rgba(15,23,42,.05);
}}

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: none; }}
.stTabs [data-baseweb="tab"] {{
  background: #fff; border-radius: 12px 12px 0 0; padding: 10px 18px; font-weight: 600;
  border: 1px solid #E6ECF5; border-bottom: none; color: {P['slate']};
}}
.stTabs [aria-selected="true"] {{ background: {P['navy']} !important; color: #fff !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {P['coral']}; }}

/* ---------- page navigation (radio styled as pills) ---------- */
.block-container [data-testid="stRadioGroup"] {{ gap: 8px; flex-wrap: wrap; margin: 4px 0 12px 0; }}
.block-container label[data-testid="stRadioOption"] {{
  background: #fff; border: 1px solid #E2E8F0; border-radius: 999px; padding: 8px 18px;
  box-shadow: 0 2px 8px rgba(15,23,42,.06); margin: 0 !important; cursor: pointer;
  transition: all .15s ease;
}}
.block-container label[data-testid="stRadioOption"]:hover {{ border-color: {P['teal']}; }}
.block-container label[data-testid="stRadioOption"][data-selected="true"] {{
  background: linear-gradient(120deg, {P['navy']}, {P['indigo']}); border-color: {P['indigo']};
  box-shadow: 0 6px 16px rgba(67,56,202,.30);
}}
.block-container label[data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {{ display: none; }}
.block-container label[data-testid="stRadioOption"] p {{ font-weight: 600; color: {P['slate']}; margin: 0; }}
.block-container label[data-testid="stRadioOption"][data-selected="true"] p {{ color: #fff !important; }}

/* ---------- click-filter chips ---------- */
.st-key-xf_chips {{ background: #fff; border: 1px solid #E6ECF5; border-radius: 14px; padding: 8px 12px;
  box-shadow: 0 4px 14px rgba(15,23,42,.06); margin-bottom: 10px; }}
.st-key-xf_chips button[kind="secondary"] {{ border-radius: 999px; background: rgba(14,165,164,.10);
  border: 1px solid {P['teal']}; color: {P['navy']}; font-weight: 600; }}
.st-key-xf_chips button[kind="primary"] {{ border-radius: 999px; background: {P['coral']}; border-color: {P['coral']}; }}
.ms-chip-label {{ font-weight: 700; color: {P['navy']}; padding-top: 8px; }}
div[data-testid="stPopover"] button {{ border-radius: 999px; font-size: .85rem; }}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, {P['navy']} 0%, #142B52 100%);
}}
section[data-testid="stSidebar"] * {{ color: #E2E8F0; }}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{ color: #fff; }}
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="input"] > div {{ background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.18); }}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{ background: {P['teal']} !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] * {{ color: #fff !important; }}
section[data-testid="stSidebar"] [data-baseweb="popover"] * {{ color: #0F172A; }}
.ms-side-brand {{ font-size: 1.25rem; font-weight: 800; color: #fff; }}
.ms-side-brand span {{ color: {P['teal']}; }}

/* dataframes */
div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, badges: list[str]) -> None:
    b = "".join(f'<span class="ms-badge">{x}</span>' for x in badges)
    st.markdown(f'<div class="ms-hero"><h1>{title}</h1><p>{subtitle}</p>{b}</div>',
                unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", accent: str = P["teal"]) -> str:
    return (f'<div class="ms-kpi" style="--accent:{accent}"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div><div class="sub">{sub}</div></div>')


def insight(md_text: str) -> None:
    """Render an insight sentence (supports **bold** markdown)."""
    import re
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md_text)
    st.markdown(f'<div class="ms-insight">💡 {html}</div>', unsafe_allow_html=True)


def question(num: int, text: str) -> None:
    st.markdown(f'<div class="ms-q"><span class="ms-qnum">Q{num}</span>{text}</div>',
                unsafe_allow_html=True)
