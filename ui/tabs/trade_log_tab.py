import streamlit as st

from ui.style import section_header, stat_cards


def _safe_options(series):
    """Sorted unique values as strings, NaN mapped to 'Unknown' - avoids
    TypeError: '<' not supported between float (NaN) and str when a
    column has mixed real values and NaN (seen in real Zone_Type data)."""
    filled = series.fillna("Unknown").astype(str)
    return sorted(filled.unique()), filled


def render(config: dict, results):
    if results is None:
        st.info("Run an analysis to see trade-by-trade logs.")
        return
    if getattr(results, "error", None):
        st.info("No trade log to show - see the error above.")
        return

    section_header("🧾", "Trade Log")

    trade_log = results.trade_log
    if trade_log is None or trade_log.empty:
        st.warning("No trades were taken for the selected parameters.")
        return

    outcome_options, outcome_filled = _safe_options(trade_log["Outcome"])
    zone_options, zone_filled = _safe_options(trade_log["Zone_Type"])

    c1, c2 = st.columns(2)
    with c1:
        if hasattr(st, "pills"):
            outcome_filter = st.pills("Outcome", options=outcome_options, default=outcome_options,
                                       selection_mode="multi", key="outcome_filter_pills")
        else:
            outcome_filter = st.multiselect("Outcome", options=outcome_options, default=outcome_options)
    with c2:
        if hasattr(st, "pills"):
            zone_filter = st.pills("Zone type", options=zone_options, default=zone_options,
                                    selection_mode="multi", key="zonetype_filter_pills")
        else:
            zone_filter = st.multiselect("Zone type", options=zone_options, default=zone_options)

    outcome_filter = outcome_filter or []
    zone_filter = zone_filter or []

    filtered = trade_log[
        outcome_filled.isin(outcome_filter) & zone_filled.isin(zone_filter)
    ]

    if not filtered.empty:
        net_pnl = filtered["Trade_PnL"].sum()
        win_rate = 100 * (filtered["Outcome"] == "Profit").sum() / len(filtered)
        stat_cards([
            {"label": "Trades Shown", "value": len(filtered), "color": "brand"},
            {"label": "Net PNL (shown)", "value": f"₹{net_pnl:,.0f}", "color": "bull" if net_pnl >= 0 else "bear"},
            {"label": "Win Rate (shown)", "value": f"{win_rate:.1f}%", "color": "bull" if win_rate >= 50 else "bear"},
        ])

    column_config = {
        "Trade_PnL": st.column_config.NumberColumn("Trade P&L", format="₹%.2f"),
        "Capital_At_Entry": st.column_config.NumberColumn(format="₹%.2f"),
        "Capital_After_Trade": st.column_config.NumberColumn(format="₹%.2f"),
        "Risk_Amount_Per_Trade": st.column_config.NumberColumn(format="₹%.2f"),
        "Piercing_Depth": st.column_config.NumberColumn(
            format="%.2f",
            help="Fraction of the zone pierced before exit. Blank = trade never entered "
                 "(target/stop unresolved), so there's nothing to measure.",
        ),
        "Entry Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Exit Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Date Created": st.column_config.DateColumn(format="YYYY-MM-DD"),
    }
    st.dataframe(filtered, use_container_width=True, hide_index=True, column_config=column_config)
    st.caption(f"{len(filtered)} of {len(trade_log)} trades shown.")

    st.download_button(
        "⬇ Download trade log as CSV", filtered.to_csv(index=True).encode("utf-8"),
        file_name=f"{config.get('ticker', 'trades')}_trade_log.csv",
        mime="text/csv", key="download_trade_log",
    )
