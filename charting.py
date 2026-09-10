"""
Pure plotting - takes already-computed zone/trade-score data and renders a
figure. Deliberately has ZERO dependency on smc_backend.py or
data_loading.py: nothing in here re-runs zone detection, backtesting, or
scoring. Call this as many times as you like (e.g. every time a filter
widget changes) without touching the cached analysis in data_access.py.
"""
import pandas as pd
import plotly.graph_objects as go


def filter_zones(zone_df: pd.DataFrame, min_base_count: int = 1,
                  zone_types=("Demand", "Supply"), trade_score: pd.DataFrame = None,
                  min_strength: int = None, fresh_only: bool = False) -> pd.DataFrame:
    """
    Returns the subset of zone_df's Zone_Created rows matching the given
    filters. `trade_score` (your df_ts / out['anal']['ts']) is only
    available for the daily timeframe in your real backend - min_strength
    and fresh_only are silently ignored if it's None/empty, or for zones
    that were never scored (e.g. weekly/monthly).
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

    if trade_score is not None and not trade_score.empty:
        if min_strength is not None:
            strength = zones.index.map(trade_score["Strength"]).to_series(index=zones.index)
            zones = zones[strength.fillna(-1) >= min_strength]
        if fresh_only:
            fresh = zones.index.map(trade_score["Freshness"]).to_series(index=zones.index)
            zones = zones[fresh.fillna(False) == True]  # noqa: E712

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
                       trade_score: pd.DataFrame = None, show_volume: bool = True) -> go.Figure:
    """
    Candlestick + shaded rectangles for whichever zones are in
    `filtered_zones` (pass the output of filter_zones()). If not given,
    plots every Zone_Created row unfiltered. Each zone gets a small label
    (Base Count, plus Strength when trade_score is available - daily only)
    so you can eyeball which zones passed the filter without a separate
    table. Optionally adds a volume bar subplot underneath.
    """
    from plotly.subplots import make_subplots

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
    )
    if has_volume:
        fig.add_trace(candle, row=1, col=1)
        colors = ["rgba(0,180,0,0.5)" if c >= o else "rgba(200,0,0,0.5)"
                  for o, c in zip(zone_df["Open"], zone_df["Close"])]
        fig.add_trace(go.Bar(x=zone_df.index, y=zone_df["Volume"], marker_color=colors,
                              name="Volume", showlegend=False), row=2, col=1)
    else:
        fig.add_trace(candle)

    for zdate, zone in zones.iterrows():
        is_demand = bool(zone["Is Demand"])
        color = "rgba(0,180,0,0.15)" if is_demand else "rgba(200,0,0,0.15)"
        label_parts = []
        if "Base Count" in zone.index and pd.notna(zone["Base Count"]):
            label_parts.append(f"BC{int(zone['Base Count'])}")
        if trade_score is not None and not trade_score.empty and zdate in trade_score.index:
            strength = trade_score.loc[zdate, "Strength"]
            if pd.notna(strength):
                label_parts.append(f"S{int(strength)}")
        label = " ".join(label_parts)

        shape_kwargs = dict(row=1, col=1) if has_volume else {}
        fig.add_shape(
            type="rect", x0=zdate, x1=zone_df.index[-1],
            y0=zone["Distal"], y1=zone["Proximal"],
            fillcolor=color, line=dict(width=0), layer="below",
            **shape_kwargs,
        )
        if label:
            fig.add_annotation(
                x=zdate, y=zone["Proximal"], text=label, showarrow=False,
                font=dict(size=9, color="green" if is_demand else "red"),
                xanchor="left", yanchor="bottom",
                **shape_kwargs,
            )

    fig.update_layout(
        title=f"{ticker} - {timeframe_label} zones ({len(zones)} shown)",
        xaxis_rangeslider_visible=False, height=560 if has_volume else 520,
        showlegend=False,
    )
    return fig


def zones_display_table(filtered_zones: pd.DataFrame, trade_score: pd.DataFrame = None) -> pd.DataFrame:
    """
    A tidy, display-ready table of the currently filtered zones - date,
    type, base count, price levels, and (daily only) Strength/Freshness
    from trade_score if available. Pure formatting, no analysis.
    """
    if filtered_zones is None or filtered_zones.empty:
        return pd.DataFrame()

    cols = {}
    cols["Date"] = filtered_zones.index
    cols["Type"] = filtered_zones["Is Demand"].map({True: "Demand", False: "Supply"})
    if "Base Count" in filtered_zones.columns:
        cols["Base Count"] = filtered_zones["Base Count"]
    if "Is Continuous" in filtered_zones.columns:
        cols["Pattern"] = filtered_zones["Is Continuous"].map({True: "Continuous", False: "Reversal"})
    cols["Proximal"] = filtered_zones["Proximal"]
    cols["Distal"] = filtered_zones["Distal"]
    cols["Target"] = filtered_zones["Target"]

    table = pd.DataFrame(cols).reset_index(drop=True)

    if trade_score is not None and not trade_score.empty:
        table["Strength"] = table["Date"].map(trade_score["Strength"])
        table["Fresh"] = table["Date"].map(trade_score["Freshness"])

    return table.sort_values("Date", ascending=False).reset_index(drop=True)
