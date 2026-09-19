"""
Pure plotting - takes already-computed zone/trade-score data and renders a
figure. Deliberately has ZERO dependency on smc_backend.py or
data_loading.py: nothing in here re-runs zone detection, backtesting, or
scoring. Call this as many times as you like (e.g. every time a filter
widget changes) without touching the cached analysis in data_access.py.
"""
import html as _html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.style import PALETTE

FONT_STACK = "Inter, -apple-system, sans-serif"


def _theme_layout(fig: go.Figure, **overrides) -> go.Figure:
    """
    Shared visual theme for every chart in the app - transparent
    background (blends with the white card it sits in), consistent font,
    and thin light-grey gridlines (Kite/Groww convention: gridlines
    provide structure without competing with the data). Called at the
    end of every figure-building function below so charts look like one
    coherent system rather than each using Plotly's default styling.
    """
    p = PALETTE
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, color=p["text"], size=12),
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    layout.update(overrides)
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor="rgba(15,23,41,0.06)", zerolinecolor="rgba(15,23,41,0.10)")
    fig.update_yaxes(gridcolor="rgba(15,23,41,0.06)", zerolinecolor="rgba(15,23,41,0.10)")
    return fig


def _zone_bounds(zone_df: pd.DataFrame, zdate, zone: pd.Series, trim_at_breach: bool):
    """
    Mirrors your real plot_stock_zones / plot_stock_zones_monthly exactly:

    x0 = the first BASE candle's date (zone_df.index[Base_Start_Idx]), not
    the explosive candle that triggered Zone_Created - matching how your
    backend's own plotting functions draw zones (multibase=True path).

    x1 = the first candle AFTER zone creation whose Close breaches Distal
    (demand: Close <= Distal, supply: Close >= Distal) when trim_at_breach
    is True, else the last candle in the chart (zone drawn as still
    active/unresolved). Same Close-based rule your backend's plot
    functions use (the High/Low variant is commented out in your source).

    Returns (x0, x1, is_breached: bool, breach_date_or_None).
    """
    base_start_idx = zone.get("Base_Start_Idx", None)
    if base_start_idx is not None and pd.notna(base_start_idx) and int(base_start_idx) >= 0:
        x0 = zone_df.index[int(base_start_idx)]
    else:
        # No multi-base tracking on this row (shouldn't normally happen) -
        # fall back to the zone-created row itself rather than guessing.
        x0 = zdate

    x1 = zone_df.index[-1]
    is_breached = False
    breach_date = None
    if trim_at_breach:
        idx_pos = zone_df.index.get_loc(zdate)
        closes = zone_df["Close"].values
        distal = zone["Distal"]
        is_demand = bool(zone["Is Demand"])
        future_closes = closes[idx_pos + 1:]
        breach_mask = (future_closes <= distal) if is_demand else (future_closes >= distal)
        breach_positions = np.where(breach_mask)[0]
        if breach_positions.size > 0:
            breach_date = zone_df.index[breach_positions[0] + idx_pos + 1]
            x1 = breach_date
            is_breached = True

        # if not pd.isna(zone_df["Exit Date"]):
        #     x1 = zone_df["Exit Date"]
        #     breach_date = zone_df["Exit Date"]
        #     is_breached = True



    return x0, x1, is_breached, breach_date


def filter_zones(zone_df: pd.DataFrame, min_base_count: int = 1,
                  zone_types=("Demand", "Supply"), pattern_types=("Continuous", "Reversal"),
                  trade_score: pd.DataFrame = None, min_strength: int = None,
                  fresh_only: bool = False, bool_filters: dict = None,
                  trade_log: pd.DataFrame = None, outcome_types=None) -> pd.DataFrame:
    """
    Returns the subset of zone_df's Zone_Created rows matching the given
    filters.

    `pattern_types` filters on zone_df's own 'Is Continuous' column, so it
    works on every timeframe (not just daily).

    `trade_score` (your df_ts / out['anal']['ts']) is only available for
    the daily timeframe in your real backend - min_strength, fresh_only,
    and bool_filters are silently ignored (or a no-op) for zones that were
    never scored (e.g. weekly/monthly).

    `bool_filters` is a {column_name: True} dict for ANY boolean column in
    trade_score (Gapped, Trending, High Volume, Swing Point, BOS, OB,
    Sweep, Trend/ITF/HTF Support, N_LTF/N_ITF/N_HTF Support, etc.) - a
    zone is kept only if that column is True for it. See filter_state.py
    for how the UI builds this dict dynamically from whatever boolean
    columns your backend's calculate_trade_score actually produced.

    `trade_log` + `outcome_types`: filters zones down to ones whose
    resulting trade's Outcome (Profit/Stop Loss/etc, from your real
    run_risk_management_simulation output) is in `outcome_types`. Like
    trade_score, trade_log only exists for the daily timeframe. A zone
    with no matching trade_log row (never triggered) is excluded whenever
    this filter is active, since there's no outcome to match against.
    """
    if zone_df is None or zone_df.empty or "Zone_Created" not in zone_df.columns:
        return pd.DataFrame()

    zones = zone_df[zone_df["Zone_Created"] == True].copy()  # noqa: E712

    if "Base Count" in zones.columns:
        zones = zones[zones["Base Count"] >= min_base_count]

    if "Is Demand" in zones.columns and zone_types:
        wanted_is_demand = {"Demand": True, "Supply": False}
        allowed = {wanted_is_demand[z] for z in zone_types if z in wanted_is_demand}
        zones = zones[zones["Is Demand"].isin(allowed)]

    if "Is Continuous" in zones.columns and pattern_types:
        wanted_pattern = {"Continuous": True, "Reversal": False}
        allowed = {wanted_pattern[p] for p in pattern_types if p in wanted_pattern}
        zones = zones[zones["Is Continuous"].isin(allowed)]

    if trade_score is not None and not trade_score.empty:
        if min_strength is not None:
            strength = zones.index.map(trade_score["Strength"]).to_series(index=zones.index)
            zones = zones[strength.fillna(-1) >= min_strength]
        if fresh_only:
            fresh = zones.index.map(trade_score["Freshness"]).to_series(index=zones.index)
            zones = zones[fresh.fillna(False) == True]  # noqa: E712
        if bool_filters:
            for col, want_true in bool_filters.items():
                if not want_true or col not in trade_score.columns:
                    continue
                flag = zones.index.map(trade_score[col]).to_series(index=zones.index)
                zones = zones[flag.fillna(False) == True]  # noqa: E712

    if trade_log is not None and not trade_log.empty and outcome_types:
        all_outcomes = set(trade_log["Outcome"].dropna().unique().tolist())
        # No-op if every available outcome is selected (nothing to exclude) -
        # avoids dropping untriggered zones just because the filter widget
        # happens to be rendered with its full default selection.
        if set(outcome_types) != all_outcomes:
            outcomes = zones.index.map(trade_log["Outcome"]).to_series(index=zones.index)
            zones = zones[outcomes.isin(outcome_types)]

    return zones


def filter_trade_log(trade_log: pd.DataFrame, filtered_zone_dates) -> pd.DataFrame:
    """
    Narrows an already-computed trade_log down to just the rows whose zone
    creation date (the trade_log's index) is in filtered_zone_dates - i.e.
    the same subset filter_zones() just picked for the chart. Pure pandas
    row selection, no analysis re-run.
    """
    if trade_log is None or trade_log.empty:
        return pd.DataFrame()
    return trade_log[trade_log.index.isin(filtered_zone_dates)]


def build_zone_figure(zone_df: pd.DataFrame, ticker: str, timeframe_label: str,
                       filtered_zones: pd.DataFrame = None,
                       trade_score: pd.DataFrame = None, show_volume: bool = True,
                       trim_at_breach: bool = True) -> go.Figure:
    """
    Candlestick + shaded rectangles for whichever zones are in
    `filtered_zones` (pass the output of filter_zones()). If not given,
    plots every Zone_Created row unfiltered. Each zone starts at its first
    base candle (matching your backend's plot_stock_zones) and, when
    trim_at_breach is True, ends at the candle whose Close first breaches
    Distal - otherwise it's drawn out to the edge of the chart as still
    active. Each zone gets a small label (Base Count, plus Strength when
    trade_score is available - daily only) so you can eyeball which zones
    passed the filter without a separate table. Optionally adds a volume
    bar subplot underneath.
    """
    from plotly.subplots import make_subplots

    p = PALETTE
    zones = filtered_zones if filtered_zones is not None else \
        zone_df[zone_df.get("Zone_Created", pd.Series(dtype=bool)) == True]  # noqa: E712

    has_volume = show_volume and "Volume" in zone_df.columns
    if has_volume:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22],
                             vertical_spacing=0.03)
    else:
        fig = go.Figure()

    candle = go.Candlestick(
        x=zone_df.index, open=zone_df["Open"], high=zone_df["High"],
        low=zone_df["Low"], close=zone_df["Close"], name=ticker,
        increasing_line_color=p["bull"], increasing_fillcolor=p["bull"],
        decreasing_line_color=p["bear"], decreasing_fillcolor=p["bear"],
    )
    if has_volume:
        fig.add_trace(candle, row=1, col=1)
        vol_colors = ["rgba(22,163,74,0.55)" if c >= o else "rgba(229,72,77,0.55)"
                      for o, c in zip(zone_df["Open"], zone_df["Close"])]
        fig.add_trace(go.Bar(x=zone_df.index, y=zone_df["Volume"], marker_color=vol_colors,
                              name="Volume", showlegend=False), row=2, col=1)
        fig.update_yaxes(title_text="VOL", row=2, col=1, title_font=dict(size=10, color=p["text_muted"]))
    else:
        fig.add_trace(candle)

    for zdate, zone in zones.iterrows():
        is_demand = bool(zone["Is Demand"])
        x0, x1, is_breached, _ = _zone_bounds(zone_df, zdate, zone, trim_at_breach)
        color = p["bull_overlay"] if is_demand else p["bear_overlay"]
        # Short label: Type initial + Base Count (e.g. "D3", "S2"), matching
        # a compact chart-tag convention - Strength is appended only when
        # meaningfully available (daily timeframe).
        type_letter = "D" if is_demand else "S"
        base_count = int(zone["Base Count"]) if "Base Count" in zone.index and pd.notna(zone["Base Count"]) else None
        label = f"{type_letter}{base_count}" if base_count is not None else type_letter
        if trade_score is not None and not trade_score.empty and zdate in trade_score.index:
            strength = trade_score.loc[zdate, "Strength"]
            if pd.notna(strength):
                label += f" \u00b7 S{int(strength)}"
        if is_breached:
            label += " \u2715"

        shape_kwargs = dict(row=1, col=1) if has_volume else {}
        fig.add_shape(
            type="rect", x0=x0, x1=x1,
            y0=zone["Distal"], y1=zone["Proximal"],
            fillcolor=color, line=dict(width=1, color=(p["bull"] if is_demand else p["bear"])),
            layer="below",
            **shape_kwargs,
        )
        if label:
            fig.add_annotation(
                x=x0, y=zone["Proximal"], text=label, showarrow=False,
                font=dict(size=9, family=FONT_STACK, color=p["bull"] if is_demand else p["bear"]),
                xanchor="left", yanchor="bottom",
                **shape_kwargs,
            )

    _theme_layout(
        fig,
        xaxis_rangeslider_visible=False, height=560 if has_volume else 520,
        showlegend=False,
    )
    return fig


def chart_heading(ticker: str, timeframe_label: str, n_zones: int):
    """
    A card-style heading above the chart - ticker/timeframe + a zone-count
    pill + a Demand/Supply color legend - separate from the Plotly figure
    itself (the chart used to carry its own in-figure title; this reads
    more like a product header, matching the rest of the app's card
    language).
    """
    p = PALETTE
    html_out = (
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        f'background:{p["bg_card"]};border:1px solid {p["border"]};border-radius:12px 12px 0 0;'
        'padding:0.7rem 1rem;border-bottom:none;">'
        '<div style="display:flex;align-items:center;gap:0.6rem;">'
        f'<span style="font-weight:700;color:{p["text"]};">{_html.escape(ticker)} \u00b7 {_html.escape(timeframe_label)}</span>'
        f'<span class="badge muted">{n_zones} zone{"s" if n_zones != 1 else ""}</span>'
        '</div>'
        '<div style="display:flex;align-items:center;gap:1rem;font-size:0.8rem;color:'
        f'{p["text_secondary"]};">'
        f'<span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
        f'background:{p["bull"]};margin-right:0.3rem;"></span>Demand</span>'
        f'<span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
        f'background:{p["bear"]};margin-right:0.3rem;"></span>Supply</span>'
        '</div></div>'
    )
    st.markdown(html_out, unsafe_allow_html=True)


def zones_display_table(filtered_zones: pd.DataFrame, trade_score: pd.DataFrame = None,
                         zone_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    A tidy, display-ready table of the currently filtered zones - dates,
    type, base count, price levels, breach status, and (daily only) EVERY
    trade_score column (Strength, Freshness, Gapped, Trending, BOS, OB,
    Sweep, Trend/ITF/HTF Support, N_LTF/N_ITF/N_HTF Support, etc.) merged
    in when available. Pure formatting, no analysis.

    `zone_df` (the full timeframe dataframe, not just the filtered zones)
    is needed to compute Base Start Date / breach status via the same
    logic as build_zone_figure - pass it to get those two columns;
    without it they're omitted.
    """
    if filtered_zones is None or filtered_zones.empty:
        return pd.DataFrame()

    cols = {}
    cols["Zone Created"] = filtered_zones.index
    cols["Type"] = filtered_zones["Is Demand"].map({True: "Demand", False: "Supply"})
    if "Base Count" in filtered_zones.columns:
        cols["Base Count"] = filtered_zones["Base Count"]
    if "Is Continuous" in filtered_zones.columns:
        cols["Pattern"] = filtered_zones["Is Continuous"].map({True: "Continuous", False: "Reversal"})

    # "Price Range" - a single min-to-max string combining Proximal/Distal,
    # easier to scan than three separate price columns. The individual
    # Proximal/Distal/Target columns are still included below for anyone
    # who wants the exact zone boundary values.
    lo = filtered_zones[["Proximal", "Distal"]].min(axis=1)
    hi = filtered_zones[["Proximal", "Distal"]].max(axis=1)
    cols["Price Range"] = [f"\u20b9{a:,.2f} \u2013 \u20b9{b:,.2f}" for a, b in zip(lo.values, hi.values)]

    cols["Proximal"] = filtered_zones["Proximal"]
    cols["Distal"] = filtered_zones["Distal"]
    cols["Target"] = filtered_zones["Target"]

    table = pd.DataFrame(cols).reset_index(drop=True)

    if zone_df is not None and not zone_df.empty:
        base_starts, statuses, breach_dates = [], [], []
        for zdate, zone in filtered_zones.iterrows():
            x0, _, is_breached, breach_date = _zone_bounds(zone_df, zdate, zone, trim_at_breach=True)
            base_starts.append(x0)
            statuses.append("Breached" if is_breached else "Active")
            breach_dates.append(breach_date)
        table["Base Start Date"] = base_starts
        table["Status"] = statuses
        table["Breach Date"] = breach_dates

    if trade_score is not None and not trade_score.empty:
        # "Flags" - every True boolean trade-score column for this zone,
        # summarized as one comma-separated string (Strength/Freshness and
        # the individual boolean columns are still added below too, for
        # anyone who wants to filter/sort on a specific one).
        from filter_state import trade_score_bool_columns
        flag_cols = trade_score_bool_columns(trade_score)
        flags_list = []
        for zdate in filtered_zones.index:
            if zdate in trade_score.index:
                active = [c for c in flag_cols if bool(trade_score.loc[zdate, c])]
                flags_list.append(", ".join(active) if active else "\u2014")
            else:
                flags_list.append("\u2014")
        table["Flags"] = flags_list

        skip = {"Ticker", "Is Demand", "Is Continuous", "Base Count"}  # already have these above
        for col in trade_score.columns:
            if col in skip:
                continue
            table[col] = table["Zone Created"].map(trade_score[col])

    return table.sort_values("Zone Created", ascending=False).reset_index(drop=True)
