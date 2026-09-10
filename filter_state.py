"""
Reads the current filter widget values out of st.session_state into a
plain dict. Both charts_tab.py (which owns the widgets) and metrics_tab.py
(which needs to reproduce the exact same subset for "filtered metrics")
call this, so the two can never drift out of sync with each other.

TS_BOOL_EXCLUDE columns are left out of the auto-generated boolean filter
list because they already have dedicated, differently-named controls
elsewhere (Freshness -> "Fresh zones only", Is Demand -> Zone Type pills,
Is Continuous -> Pattern pills, Ticker isn't a real flag).
"""
import streamlit as st

TS_BOOL_EXCLUDE = {"Ticker", "Is Demand", "Is Continuous", "Freshness"}


def trade_score_bool_columns(trade_score) -> list:
    """Every boolean column in df_ts (your real calculate_trade_score
    output) except the ones already covered by a dedicated control.
    Fully dynamic - if your backend adds a new True/False score column
    later, a filter for it appears automatically, no UI code changes."""
    if trade_score is None or trade_score.empty:
        return []
    return [c for c in trade_score.columns
            if trade_score[c].dtype == bool and c not in TS_BOOL_EXCLUDE]


def bool_filter_key(col: str) -> str:
    return f"ts_bool_{col}"


def get_active_filters(results) -> dict:
    """Everything filter_zones() needs, read from session_state as the
    Charts tab widgets last left it."""
    trade_score = getattr(results, "trade_score", None) if results is not None else None

    bool_filters = {}
    for col in trade_score_bool_columns(trade_score):
        if st.session_state.get(bool_filter_key(col)):
            bool_filters[col] = True

    return dict(
        min_base_count=st.session_state.get("min_base_count", 1),
        zone_types=tuple(st.session_state.get("zone_types") or ["Demand", "Supply"]),
        pattern_types=tuple(st.session_state.get("pattern_types") or ["Continuous", "Reversal"]),
        min_strength=st.session_state.get("min_strength") if st.session_state.get("use_strength") else None,
        fresh_only=st.session_state.get("fresh_only", False),
        bool_filters=bool_filters,
    )
