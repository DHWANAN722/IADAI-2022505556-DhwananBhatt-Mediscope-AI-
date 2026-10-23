"""Custom CSS and small HTML components (header banner, KPI cards, insight boxes)."""
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap

from . import config as cfg

P = cfg.PALETTE

# Light colormap for pandas Styler gradients (keeps dark table text readable)
SOFT_CMAP = LinearSegmentedColormap.from_list("mediscope_soft", ["#FFF6D6", "#B9F5C6", "#D8C5F8"])
PS = cfg.PASTELS
# KPI accent colour -> pastel card fill (as in the reference infographic's cards)
CARD_FILL = {P["teal"]: PS["mint"], P["indigo"]: PS["lavender"], P["coral"]: PS["pink"],
             P["amber"]: PS["yellow"], P["sky"]: PS["cyan"], P["violet"]: PS["peach"]}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1380px; }}
.stApp {{ background: {P['bg']}; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: #E7DDFB !important; }}
.block-container h1, .block-container h2, .block-container h3, .block-container h4 {{ color: #FFFFFF; }}

/* ---------- header banner (orange poster header + yellow band) ---------- */
.ms-hero {{
  background: {P['orange']};
  border-radius: 20px; padding: 26px 32px 22px 32px; color: {P['ink']}; margin-bottom: 18px;
  border-bottom: 12px solid {P['amber']};
  box-shadow: 0 12px 30px rgba(20,16,70,.35); position: relative; overflow: hidden;
}}
.ms-hero:after {{
  content: ""; position: absolute; right: -60px; top: -60px; width: 260px; height: 260px;
  border-radius: 50%; background: radial-gradient(circle, rgba(255,229,90,.55), rgba(255,229,90,0) 70%);
}}
.ms-hero h1 {{ color: {P['ink']}; font-size: 2.0rem; font-weight: 800; margin: 0; letter-spacing: -.5px; padding: 0; }}
.ms-hero p {{ color: {P['ink']}; opacity: .88; margin: 6px 0 0 0; font-size: 1.0rem; }}
.ms-badge {{
  display: inline-block; background: {P['amber']}; border: 1px solid {P['ink']};
  color: {P['ink']}; font-weight: 600; border-radius: 999px; padding: 3px 12px; font-size: .78rem; margin: 10px 6px 0 0;
}}

/* ---------- KPI cards (pastel fills) ---------- */
.ms-kpi {{
  background: var(--fill, {P['card']}); border-radius: 16px; padding: 16px 18px 14px 18px; height: 100%;
  box-shadow: 0 6px 18px rgba(20,16,70,.25); border: none;
  border-top: 5px solid var(--accent); transition: transform .15s ease, box-shadow .15s ease;
}}
.ms-kpi:hover {{ transform: translateY(-2px); box-shadow: 0 12px 26px rgba(20,16,70,.35); }}
.ms-kpi .lbl {{ color: {P['ink']}; font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; }}
.ms-kpi .val {{ color: {P['ink']}; font-size: 1.7rem; font-weight: 800; margin-top: 4px; line-height: 1.15; }}
.ms-kpi .sub {{ color: {P['slate']}; font-size: .78rem; margin-top: 2px; }}

/* ---------- insight & section boxes ---------- */
.ms-insight {{
  background: {cfg.PASTELS['cream']};
  border-left: 6px solid {P['orange']}; border-radius: 12px; padding: 14px 18px; margin: 6px 0 14px 0;
  color: {P['ink']}; font-size: .97rem;
}}
.ms-insight b, .ms-insight strong {{ color: {P['violet']}; }}
.ms-q {{ color: #FFFFFF; font-weight: 800; font-size: 1.25rem; margin: 6px 0 2px 0; }}
.ms-qnum {{
  display: inline-block; background: {P['amber']}; color: {P['ink']}; border-radius: 8px;
  padding: 1px 9px; margin-right: 8px; font-size: .95rem;
}}
.ms-card {{
  background: #fff; color: {P['ink']}; border-radius: 16px; padding: 18px 22px; border: none;
  box-shadow: 0 6px 18px rgba(20,16,70,.25); margin-bottom: 12px;
}}
.ms-card td, .ms-card li, .ms-card b {{ color: {P['ink']}; }}
.ms-card a {{ color: {P['violet']}; }}
.ms-card code {{ color: {P['coral']}; background: #F3F0FB; }}

/* ---------- containers around charts ---------- */
div[data-testid="stPlotlyChart"] {{
  background: #fff; border-radius: 16px; padding: 8px 10px; border: none;
  box-shadow: 0 6px 18px rgba(20,16,70,.22);
}}

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: none; }}
.stTabs [data-baseweb="tab"] {{
  background: #fff; border-radius: 12px 12px 0 0; padding: 10px 18px; font-weight: 600;
  border: none; color: {P['ink']};
}}
.stTabs [aria-selected="true"] {{ background: {P['amber']} !important; color: {P['ink']} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {P['orange']}; }}

/* ---------- page navigation (radio styled as pills) ---------- */
.block-container [data-testid="stRadioGroup"] {{ gap: 8px; flex-wrap: wrap; margin: 4px 0 12px 0; }}
.block-container label[data-testid="stRadioOption"] {{
  background: #fff; border: 2px solid transparent; border-radius: 999px; padding: 8px 18px;
  box-shadow: 0 4px 12px rgba(20,16,70,.22); margin: 0 !important; cursor: pointer;
  transition: all .15s ease;
}}
.block-container label[data-testid="stRadioOption"]:hover {{ border-color: {P['amber']}; }}
.block-container label[data-testid="stRadioOption"][data-selected="true"] {{
  background: {P['amber']}; border-color: {P['ink']};
  box-shadow: 0 6px 16px rgba(20,16,70,.35);
}}
.block-container label[data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {{ display: none; }}
.block-container label[data-testid="stRadioOption"] p {{ font-weight: 600; color: {P['ink']}; margin: 0; }}
.block-container label[data-testid="stRadioOption"][data-selected="true"] p {{ color: {P['ink']} !important; font-weight: 800; }}

/* ---------- click-filter chips ---------- */
.st-key-xf_chips {{ background: {cfg.PASTELS['lightgreen']}; border: none; border-radius: 14px; padding: 8px 12px;
  box-shadow: 0 4px 14px rgba(20,16,70,.22); margin-bottom: 10px; }}
.st-key-xf_chips button[kind="secondary"] {{ border-radius: 999px; background: {cfg.PASTELS['mint']};
  border: 1px solid {P['teal']}; color: {P['ink']}; font-weight: 600; }}
.st-key-xf_chips button[kind="secondary"] p {{ color: {P['ink']}; }}
.st-key-xf_chips button[kind="primary"] {{ border-radius: 999px; background: {P['orange']}; border-color: {P['orange']}; }}
.st-key-xf_chips button[kind="primary"] p {{ color: {P['ink']}; font-weight: 700; }}
.ms-chip-label {{ font-weight: 700; color: {P['ink']}; padding-top: 8px; }}
div[data-testid="stPopover"] button {{ border-radius: 999px; font-size: .85rem; background: {P['amber']};
  color: {P['ink']}; border: none; font-weight: 600; }}
div[data-testid="stPopover"] button p, div[data-testid="stPopover"] button svg {{ color: {P['ink']}; fill: {P['ink']}; }}

/* ---------- buttons on the indigo canvas ---------- */
.block-container [data-testid="stDownloadButton"] button {{ background: {P['amber']}; color: {P['ink']}; border: none; font-weight: 700; }}
.block-container [data-testid="stDownloadButton"] button p {{ color: {P['ink']}; }}
.block-container [data-testid="stExpander"] details {{ border-color: rgba(255,255,255,.35); }}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {{ background: {P['navy']}; }}
section[data-testid="stSidebar"] * {{ color: #F1EEFF; }}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{ color: {P['amber']}; }}
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="input"] > div {{ background: #253650; border-color: rgba(255,255,255,.18); }}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{ background: {P['amber']} !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] * {{ color: {P['ink']} !important; }}
section[data-testid="stSidebar"] [data-baseweb="popover"] * {{ color: {P['ink']}; }}
.ms-side-brand {{ font-size: 1.25rem; font-weight: 800; color: #fff; }}
.ms-side-brand span {{ color: {P['amber']}; }}

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
    fill = CARD_FILL.get(accent, PS["lightgreen"])
    return (f'<div class="ms-kpi" style="--accent:{accent};--fill:{fill}"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div><div class="sub">{sub}</div></div>')


def insight(md_text: str) -> None:
    """Render an insight sentence (supports **bold** markdown)."""
    import re
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md_text)
    st.markdown(f'<div class="ms-insight">💡 {html}</div>', unsafe_allow_html=True)


def question(num: int, text: str) -> None:
    st.markdown(f'<div class="ms-q"><span class="ms-qnum">Q{num}</span>{text}</div>',
                unsafe_allow_html=True)
