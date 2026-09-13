import streamlit as st

from charting import filter_zones, filter_trade_log
from filter_state import get_active_filters, outcome_options as shared_outcome_options
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

    use_chart_filters = st.toggle(
        "Show only trades matching current Chart Filters (Base Count, Zone Type, "
        "Pattern, Strength, Freshness, score flags, Outcome)",
        value=False, key="tradelog_use_chart_filters",
        help="Mirrors the Metrics tab's equivalent toggle - re-slices this trade log "
             "using whatever's currently set on the Charts tab, without re-running "
             "zone detection/backtest/scoring.",
    )

    trade_log_source = trade_log
    if use_chart_filters:
        zones_1d = results.zones.get("1d")
        if zones_1d is None or zones_1d.empty:
            st.info("No daily zone data available to filter against.")
            return

        active = get_active_filters(results)
        filtered_zones = filter_zones(
            zones_1d, min_base_count=active["min_base_count"], zone_types=active["zone_types"],
            pattern_types=active["pattern_types"], trade_score=results.trade_score,
            min_strength=active["min_strength"], fresh_only=active["fresh_only"],
            bool_filters=active["bool_filters"],
            trade_log=trade_log, outcome_types=active["outcome_types"],
        )
        trade_log_source = filter_trade_log(trade_log, filtered_zones.index)

        active_bool_flags = [k for k, v in active["bool_filters"].items() if v]
        all_outcomes = set(shared_outcome_options(trade_log))
        outcome_narrowed = set(active["outcome_types"]) != all_outcomes and all_outcomes
        st.caption(
            f"Chart Filters: Min Base Count \u2265 {active['min_base_count']}, "
            f"Zone Type in {list(active['zone_types'])}, Pattern in {list(active['pattern_types'])}"
            + (f", Min Strength \u2265 {active['min_strength']}" if active["min_strength"] is not None else "")
            + (", Fresh only" if active["fresh_only"] else "")
            + (f", flags: {active_bool_flags}" if active_bool_flags else "")
            + (f", Outcome in {list(active['outcome_types'])}" if outcome_narrowed else "")
            + f" \u2192 {len(trade_log_source)} of {len(trade_log)} trades match."
        )

        if trade_log_source.empty:
            st.warning("No trades match the current chart filters.")
            return

    outcome_opts, outcome_filled = _safe_options(trade_log_source["Outcome"])
    zone_opts, zone_filled = _safe_options(trade_log_source["Zone_Type"])

    c1, c2 = st.columns(2)
    with c1:
        if hasattr(st, "pills"):
            outcome_filter = st.pills("Outcome", options=outcome_opts, default=outcome_opts,
                                       selection_mode="multi", key="outcome_filter_pills")
        else:
            outcome_filter = st.multiselect("Outcome", options=outcome_opts, default=outcome_opts)
    with c2:
        if hasattr(st, "pills"):
            zone_filter = st.pills("Zone type", options=zone_opts, default=zone_opts,
                                    selection_mode="multi", key="zonetype_filter_pills")
        else:
            zone_filter = st.multiselect("Zone type", options=zone_opts, default=zone_opts)

    outcome_filter = outcome_filter or []
    zone_filter = zone_filter or []

    filtered = trade_log_source[
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
    st.caption(f"{len(filtered)} of {len(trade_log_source)} trades shown.")

    st.download_button(
        "⬇ Download trade log as CSV", filtered.to_csv(index=True).encode("utf-8"),
        file_name=f"{config.get('ticker', 'trades')}_trade_log.csv",
        mime="text/csv", key="download_trade_log",
    )
