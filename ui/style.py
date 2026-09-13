"""
Design system for the dashboard - a single source of truth for colors,
typography, and small styled HTML components, so every tab looks
consistent instead of each one reinventing spacing/colors ad hoc.

Nothing here touches analysis or backend logic - this module only ever
produces CSS strings and HTML markup for st.markdown(unsafe_allow_html=True).

Color language (used consistently everywhere - charts, tables, cards):
    green  (BULL)  -> demand zones, profitable trades, "True"/"OK", positive deltas
    red    (BEAR)  -> supply zones, losing trades, errors, negative deltas
    amber  (WARN)  -> breached zones, "No Trades" status, caution
    blue   (BRAND) -> primary actions, neutral emphasis, equity/score lines
    cyan   (ACCENT)-> secondary highlights (volume, gauge ticks)
"""
import html as _html
import streamlit as st

PALETTE = {
    "bg": "#0B0F19",
    "bg_elevated": "#141A26",
    "bg_card": "#171E2C",
    "border": "#26304A",
    "text": "#E7EAF0",
    "text_muted": "#8B93A7",
    "brand": "#4F8CFF",
    "brand_soft": "rgba(79,140,255,0.14)",
    "accent": "#22D3EE",
    "bull": "#22C55E",
    "bull_soft": "rgba(34,197,94,0.14)",
    "bear": "#EF4460",
    "bear_soft": "rgba(239,68,96,0.14)",
    "warn": "#F5A623",
    "warn_soft": "rgba(245,166,35,0.14)",
}

FONT_STACK = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def inject_global_css():
    p = PALETTE
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: {FONT_STACK};
    }}

    /* Tighten default top padding, our own header banner replaces it */
    .block-container {{
        padding-top: 1.6rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }}

    /* Header banner */
    .app-header {{
        background: linear-gradient(135deg, {p['bg_card']} 0%, {p['bg_elevated']} 100%);
        border: 1px solid {p['border']};
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.75rem;
    }}
    .app-header h1 {{
        font-size: 1.55rem;
        font-weight: 800;
        margin: 0;
        color: {p['text']};
        letter-spacing: -0.02em;
    }}
    .app-header .subtitle {{
        color: {p['text_muted']};
        font-size: 0.88rem;
        margin-top: 2px;
    }}
    .badge-row {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
    .badge {{
        display: inline-flex; align-items: center; gap: 0.35rem;
        background: {p['brand_soft']}; color: {p['brand']};
        border: 1px solid rgba(79,140,255,0.35);
        border-radius: 999px; padding: 0.28rem 0.75rem;
        font-size: 0.76rem; font-weight: 600;
    }}
    .badge.muted {{ background: rgba(139,147,167,0.12); color: {p['text_muted']}; border-color: {p['border']}; }}

    /* Section headers used inside tabs */
    .section-header {{
        display: flex; align-items: center; gap: 0.5rem;
        font-size: 1.05rem; font-weight: 700; color: {p['text']};
        margin: 0.25rem 0 0.15rem 0;
    }}
    .section-sub {{ color: {p['text_muted']}; font-size: 0.85rem; margin-bottom: 0.75rem; }}

    /* Stat cards (replaces plain st.metric where used) */
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.7rem; margin-bottom: 0.5rem; }}
    .stat-card {{
        background: {p['bg_card']}; border: 1px solid {p['border']};
        border-left: 3px solid var(--accent-color, {p['brand']});
        border-radius: 12px; padding: 0.85rem 1rem;
    }}
    .stat-card .stat-label {{ color: {p['text_muted']}; font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
    .stat-card .stat-value {{ color: {p['text']}; font-size: 1.5rem; font-weight: 800; margin-top: 0.15rem; letter-spacing: -0.02em; }}
    .stat-card .stat-delta {{ font-size: 0.8rem; font-weight: 600; margin-top: 0.1rem; }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {p['border']}; }}
    .stTabs [data-baseweb="tab"] {{
        height: 42px; white-space: pre-wrap; border-radius: 10px 10px 0 0;
        font-weight: 600; font-size: 0.92rem; color: {p['text_muted']};
    }}
    .stTabs [aria-selected="true"] {{ color: {p['brand']} !important; }}

    /* Buttons */
    .stButton > button, .stDownloadButton > button {{
        border-radius: 10px; font-weight: 600; border: 1px solid {p['border']};
    }}
    .stButton > button[kind="primary"] {{
        background: {p['brand']}; border: none;
    }}

    /* Containers with border (filter boxes etc.) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{ border-right: 1px solid {p['border']}; }}

    /* Hide Streamlit chrome for a cleaner look */
    footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)


def app_header(title: str, subtitle: str, badges: list):
    """
    title/subtitle/badge text are HTML-escaped before insertion - these
    often include dynamic data (the ticker, e.g. 'M&M.NS' from our own
    NIFTY 50 preset list, or whatever a person typed into the Ticker box),
    and this renders via unsafe_allow_html, so an un-escaped '&', '<', etc.
    would produce broken or unexpected markup.

    Built as a single concatenated string with NO leading whitespace on
    any line - a multi-line f-string indented to match the surrounding
    Python code (as this used to be) puts 4+ literal leading spaces on
    each HTML line, and Markdown renders any line indented 4+ spaces as a
    literal code block instead of parsing it as HTML.
    """
    badge_html = "".join(
        f'<span class="badge{" muted" if b.get("muted") else ""}">{_html.escape(str(b["text"]))}</span>'
        for b in badges
    )
    html_out = (
        '<div class="app-header">'
        f'<div><h1>{_html.escape(title)}</h1>'
        f'<div class="subtitle">{_html.escape(subtitle)}</div></div>'
        f'<div class="badge-row">{badge_html}</div>'
        '</div>'
    )
    st.markdown(html_out, unsafe_allow_html=True)


def section_header(icon: str, title: str, subtitle: str = ""):
    """title/subtitle are HTML-escaped - see app_header()'s docstring for why."""
    st.markdown(f'<div class="section-header">{icon} {_html.escape(title)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-sub">{_html.escape(subtitle)}</div>', unsafe_allow_html=True)


def stat_cards(cards: list):
    """
    cards: list of dicts with keys: label, value, color ('bull'/'bear'/'warn'/'brand'/'accent'),
    optional 'delta' (str, already formatted, e.g. '+2.4%').
    Renders a responsive grid of styled cards in one st.markdown call.
    label/value/delta are HTML-escaped - see app_header()'s docstring for why.

    Built as single-line concatenated strings with NO leading whitespace -
    see app_header()'s docstring for why that matters (this was the actual
    bug: raw "<div..." text was showing up instead of rendered cards,
    because the previous version used an indented multi-line f-string).
    """
    p = PALETTE
    parts = ['<div class="stat-grid">']
    for c in cards:
        color = p.get(c.get("color", "brand"), p["brand"])
        delta_html = ""
        if c.get("delta"):
            delta_color = c.get("delta_color", color)
            delta_html = f'<div class="stat-delta" style="color:{delta_color}">{_html.escape(str(c["delta"]))}</div>'
        parts.append(
            f'<div class="stat-card" style="--accent-color:{color}">'
            f'<div class="stat-label">{_html.escape(str(c["label"]))}</div>'
            f'<div class="stat-value">{_html.escape(str(c["value"]))}</div>'
            f'{delta_html}'
            '</div>'
        )
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)
