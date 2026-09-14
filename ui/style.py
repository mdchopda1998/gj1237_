"""
Design system for the dashboard - a single source of truth for colors,
typography, icons, and small styled HTML components, so every tab looks
consistent instead of each one reinventing spacing/colors ad hoc.

Light "Kite Web + Groww Web" fintech aesthetic: white/off-white surfaces,
hairline borders for structural depth, soft shadows only on elevated
cards, a strict green=bull/red=bear color language, and Google's Material
Symbols icon font in place of emoji (both in native Streamlit widgets via
the ":material/name:" shortcode, and in this module's custom HTML via a
loaded <span class="material-symbols-outlined"> font).

Nothing here touches analysis or backend logic - this module only ever
produces CSS strings and HTML markup for st.markdown(unsafe_allow_html=True).

Color language (used consistently everywhere - charts, tables, cards,
badges):
    green (BULL)  -> demand zones, profitable trades, "True"/"OK", positive deltas
    red   (BEAR)  -> supply zones, losing trades, errors, negative deltas
    amber (WARN)  -> breached zones, "No Trades" status, caution
    blue  (BRAND) -> primary actions, neutral emphasis, equity/score lines
    teal  (ACCENT)-> secondary chart highlights (volume, gauge ticks) - kept
                     visually distinct from BULL green so it's never
                     mistaken for a profit/positive signal
"""
import html as _html
import streamlit as st

PALETTE = {
    "bg": "#F6F8FB",              # surface/page
    "bg_elevated": "#FAFBFD",     # surface/sidebar
    "bg_card": "#FFFFFF",         # surface/card
    "bg_card_hover": "#FBFCFE",   # surface/card-hover
    "border": "#E4E8F0",         # border/default
    "border_strong": "#D3D9E3",  # border/strong
    "text": "#0F1729",           # text/primary
    "text_secondary": "#4B5568", # text/secondary
    "text_muted": "#8A93A6",     # text/muted
    "brand": "#3861FB",           # brand/primary
    "brand_soft": "#EAF0FF",     # brand/primary-soft
    "accent": "#00C896",          # accent/teal
    "bull": "#16A34A",            # bull/green
    "bull_soft": "#E7F8ED",      # bull/green-soft (solid - badges, cell backgrounds)
    "bull_overlay": "rgba(22,163,74,0.12)",   # translucent - chart zone fills specifically
    "bear": "#E5484D",            # bear/red
    "bear_soft": "#FCEBEC",      # bear/red-soft (solid - badges, cell backgrounds)
    "bear_overlay": "rgba(229,72,77,0.12)",   # translucent - chart zone fills specifically
    "warn": "#F5A623",            # warn/amber
    "warn_soft": "#FDF3E1",      # warn/amber-soft
}

FONT_STACK = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# Suggested icon mapping (Google Material Symbols names) - kept in one
# place so every call site uses the same vocabulary. Pass these names to
# icon_span()/section_header(), or prefix with ':material/' for native
# Streamlit widgets (st.button(icon=...), st.tabs labels).
ICONS = {
    "app": "candlestick_chart",
    "charts": "candlestick_chart",
    "metrics": "monitoring",
    "trade_log": "receipt_long",
    "score": "bar_chart",
    "batch": "grid_view",
    "run": "play_arrow",
    "reset": "restart_alt",
    "download": "download",
    "search": "search",
    "data_source": "folder_open",
    "ratios": "tune",
    "about": "info",
    "success": "check_circle",
    "error": "error",
    "warning": "warning",
    "filter": "filter_alt",
}


def icon_span(name: str, size: int = 18, color: str = None) -> str:
    """A Material Symbols icon as an inline HTML span - for use inside
    this module's own HTML strings (section headers, badges). Native
    Streamlit widgets (buttons, tabs) use the ':material/name:' shortcode
    instead; this covers everywhere that syntax doesn't reach."""
    style = f"font-size:{size}px;vertical-align:middle;"
    if color:
        style += f"color:{color};"
    return f'<span class="material-symbols-outlined" style="{style}">{name}</span>'


def inject_global_css():
    p = PALETTE
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20,400,0,0&display=swap');

    html, body, [class*="css"] {{
        font-family: {FONT_STACK};
    }}
    .material-symbols-outlined {{
        font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 20;
    }}

    /* Tabular figures for every number in the app - table columns and
       stat-card values align vertically instead of jittering per digit. */
    body, .stDataFrame, .stat-value, .badge, .stMetric {{
        font-variant-numeric: tabular-nums;
    }}

    .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 2.5rem;
        max-width: 1400px;
    }}

    /* Header banner - quiet light card (elevation/1), not a dark gradient */
    .app-header {{
        background: {p['bg_card']};
        border: 1px solid {p['border']};
        border-radius: 16px;
        padding: 1.1rem 1.5rem;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.75rem;
        box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 1px 3px rgba(16,24,40,0.06);
    }}
    .app-header h1 {{
        font-size: 1.4rem;
        font-weight: 800;
        margin: 0;
        color: {p['text']};
        letter-spacing: -0.02em;
        display: flex; align-items: center; gap: 0.5rem;
    }}
    .app-header .subtitle {{
        color: {p['text_muted']};
        font-size: 0.85rem;
        margin-top: 2px;
    }}
    .badge-row {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
    .badge {{
        display: inline-flex; align-items: center; gap: 0.3rem;
        background: {p['brand_soft']}; color: {p['brand']};
        border: 1px solid rgba(56,97,251,0.25);
        border-radius: 999px; padding: 0.28rem 0.75rem;
        font-size: 0.76rem; font-weight: 600;
    }}
    .badge.muted {{ background: {p['bg']}; color: {p['text_muted']}; border-color: {p['border']}; }}
    .badge.success {{ background: {p['bull_soft']}; color: {p['bull']}; border-color: rgba(22,163,74,0.25); }}
    .badge.error {{ background: {p['bear_soft']}; color: {p['bear']}; border-color: rgba(229,72,77,0.25); }}
    .badge.warning {{ background: {p['warn_soft']}; color: {p['warn']}; border-color: rgba(245,166,35,0.3); }}

    /* Section headers used inside tabs */
    .section-header {{
        display: flex; align-items: center; gap: 0.45rem;
        font-size: 1.1rem; font-weight: 700; color: {p['text']};
        margin: 0.25rem 0 0.15rem 0;
    }}
    .section-sub {{ color: {p['text_muted']}; font-size: 0.85rem; margin-bottom: 0.75rem; }}

    /* Stat cards - white surface + left accent stripe (Groww pattern),
       never a colored card background. */
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 0.6rem; }}
    .stat-card {{
        background: {p['bg_card']};
        border: 1px solid {p['border']};
        border-left: 3px solid var(--accent-color, {p['brand']});
        border-radius: 14px; padding: 0.9rem 1.05rem;
        box-shadow: 0 1px 2px rgba(16,24,40,0.03);
    }}
    .stat-card .stat-label {{
        color: {p['text_muted']}; font-size: 0.72rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.045em;
    }}
    .stat-card .stat-value {{
        color: {p['text']}; font-size: 1.55rem; font-weight: 800;
        margin-top: 0.2rem; letter-spacing: -0.02em;
    }}
    .stat-card .stat-delta {{ font-size: 0.8rem; font-weight: 600; margin-top: 0.15rem; }}

    /* Tabs - flat underline indicator, Kite-style (not pill/card tabs) */
    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid {p['border']}; }}
    .stTabs [data-baseweb="tab"] {{
        height: 44px; white-space: pre-wrap; border-radius: 0;
        font-weight: 600; font-size: 0.92rem; color: {p['text_muted']};
    }}
    .stTabs [aria-selected="true"] {{
        color: {p['brand']} !important;
        border-bottom: 2px solid {p['brand']} !important;
    }}

    /* Buttons - filled primary, outline secondary */
    .stButton > button, .stDownloadButton > button {{
        border-radius: 10px; font-weight: 600; border: 1px solid {p['border']};
        background: {p['bg_card']}; color: {p['text']};
    }}
    .stButton > button[kind="primary"] {{
        background: {p['brand']}; border: none; color: #FFFFFF;
    }}

    /* Bordered containers (filter boxes etc.) - hairline + soft shadow */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important;
        border-color: {p['border']} !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {p['bg_elevated']};
        border-right: 1px solid {p['border']};
    }}

    /* Hide Streamlit's default footer for a cleaner, product-like look */
    footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)


def app_header(title: str, subtitle: str, badges: list, icon: str = None):
    """
    title/subtitle/badge text are HTML-escaped before insertion - these
    often include dynamic data (the ticker, e.g. 'M&M.NS' from our own
    NIFTY 50 preset list, or whatever a person typed into the Ticker box),
    and this renders via unsafe_allow_html, so an un-escaped '&', '<', etc.
    would produce broken or unexpected markup.

    `icon`: a Material Symbols icon name (see ICONS dict) shown before the
    title, replacing the emoji this used to take directly in the string.

    Built as a single concatenated string with NO leading whitespace on
    any line - a multi-line f-string indented to match the surrounding
    Python code (as this used to be) puts 4+ literal leading spaces on
    each HTML line, and Markdown renders any line indented 4+ spaces as a
    literal code block instead of parsing it as HTML.
    """
    badge_html = "".join(
        f'<span class="badge{" " + b["variant"] if b.get("variant") else (" muted" if b.get("muted") else "")}">'
        f'{_html.escape(str(b["text"]))}</span>'
        for b in badges
    )
    icon_html = icon_span(icon, size=22) if icon else ""
    html_out = (
        '<div class="app-header">'
        f'<div><h1>{icon_html}{_html.escape(title)}</h1>'
        f'<div class="subtitle">{_html.escape(subtitle)}</div></div>'
        f'<div class="badge-row">{badge_html}</div>'
        '</div>'
    )
    st.markdown(html_out, unsafe_allow_html=True)


def section_header(icon: str, title: str, subtitle: str = ""):
    """
    title/subtitle are HTML-escaped - see app_header()'s docstring for why.
    `icon` is a Material Symbols icon name (e.g. 'candlestick_chart'), not
    an emoji - rendered via the Material Symbols font loaded in
    inject_global_css().
    """
    st.markdown(
        f'<div class="section-header">{icon_span(icon)} {_html.escape(title)}</div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(f'<div class="section-sub">{_html.escape(subtitle)}</div>', unsafe_allow_html=True)


def stat_cards(cards: list):
    """
    cards: list of dicts with keys: label, value, color ('bull'/'bear'/'warn'/'brand'/'accent'),
    optional 'delta' (str, already formatted, e.g. '+2.4%').
    Renders a responsive grid of styled white cards with a colored left
    accent stripe (Groww pattern) - never a colored card background.
    label/value/delta are HTML-escaped - see app_header()'s docstring for why.

    Built as single-line concatenated strings with NO leading whitespace -
    see app_header()'s docstring for why that matters.
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
