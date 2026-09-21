import streamlit as st

from charting import filter_zones, build_zone_figure, zones_display_table, chart_heading, TRIM_MODE_LABELS
from filter_state import get_active_filters, trade_score_bool_columns, bool_filter_key, outcome_options
from ui.style import section_header, icon_span

TF_LABELS = {"1d": "Daily", "1wk": "Weekly", "1mo": "Monthly"}
SOURCE_NOTES = {
    "csv": "local saved CSV",
    "live": "Yahoo Finance (yfinance)",
    "synthetic": "synthetic placeholder - no CSV found and live fetch failed",
}


def render(config: dict, results):
    if results is None:
        st.info("Set your parameters and click **Run Analysis** to see charts.")
        return
    if getattr(results, "error", None) or not results.zones:
        st.info("No charts to show - see the error above, or try different settings.")
        return

    section_header(
        "candlestick_chart", f"{config['ticker']} \u2014 Zones & Price Action",
        f"Analysis last computed: {results.analysis_timestamp}" if results.analysis_timestamp else "",
    )

    # --- Chart Filters: clearly separated from the analysis above ---------
    st.markdown("---")
    try:
        filter_box = st.container(border=True)
    except TypeError:
        # Older Streamlit (<1.28) doesn't support container(border=...)
        filter_box = st.container()
    with filter_box:
        st.markdown(f"##### {icon_span('filter_alt', size=16)} Chart Filters — instant, does *not* re-run analysis", unsafe_allow_html=True)
        st.caption(
            "These only change which zones are drawn below. Zone detection, the "
            "backtest, and scoring stay exactly as they were at the timestamp "
            "above until you click **Run Analysis** again in the sidebar. "
            "The Metrics tab has a matching toggle to see numbers for just "
            "this filtered subset. Use **Reset all filters** in the sidebar "
            "to clear everything below."
        )

        f1, f2, f3 = st.columns([2, 2, 2])
        with f1:
            st.slider("Min Base Count", 1, 10, 1, key="min_base_count")
        with f2:
            if hasattr(st, "pills"):
                st.pills("Zone Type", ["Demand", "Supply"], default=["Demand", "Supply"],
                         selection_mode="multi", key="zone_types")
            else:
                st.multiselect("Zone Type", ["Demand", "Supply"], default=["Demand", "Supply"], key="zone_types")
        with f3:
            # 'Is Continuous' lives on the zone dataframe itself, not just
            # trade_score, so this filter works on all three timeframes.
            if hasattr(st, "pills"):
                st.pills("Pattern", ["Continuous", "Reversal"], default=["Continuous", "Reversal"],
                         selection_mode="multi", key="pattern_types")
            else:
                st.multiselect("Pattern", ["Continuous", "Reversal"], default=["Continuous", "Reversal"],
                                key="pattern_types")

        trim_options = list(TRIM_MODE_LABELS.values())
        trim_option_to_mode = {v: k for k, v in TRIM_MODE_LABELS.items()}
        if hasattr(st, "pills"):
            st.pills(
                "Zone rectangle length", trim_options, default="Trim at exit date",
                key="trim_mode_choice",
                help="Full rectangle: every zone extends to the edge of the chart, no trimming. "
                     "Trim at breach: stops at the first candle whose Close crosses Distal "
                     "(price-based invalidation check - matches your backend's plot_stock_zones). "
                     "Trim at exit date: stops at that zone's actual trade Exit Date from your "
                     "real run_risk_management_simulation output (target hit, stop hit, or "
                     "otherwise) - only zones that actually produced a trade have one.",
            )
        else:
            st.radio(
                "Zone rectangle length", trim_options, index=2,
                key="trim_mode_choice", horizontal=True,
            )

        has_trade_score = results.trade_score is not None and not results.trade_score.empty
        has_trade_log = results.trade_log is not None and not results.trade_log.empty
        available_outcomes = outcome_options(results.trade_log)

        if has_trade_score or available_outcomes:
            bool_cols = trade_score_bool_columns(results.trade_score)
            n_daily_filters = 2 + len(bool_cols) + (1 if available_outcomes else 0)
            with st.expander(
                f"Daily-only filters — every trade-score column ({n_daily_filters} total)",
                expanded=False,
            ):
                st.caption(
                    "All of these come from your real calculate_trade_score / "
                    "run_risk_management_simulation output - only computed for the "
                    "daily timeframe, so they have no effect on the Weekly/Monthly charts."
                )
                st.toggle("Filter by minimum Strength", value=False, key="use_strength",
                          disabled=not has_trade_score)
                if has_trade_score and st.session_state.get("use_strength"):
                    max_strength = int(results.trade_score["Strength"].max())
                    st.slider("Min Strength", 0, max(max_strength, 1), 0, key="min_strength")
                st.toggle("Fresh zones only", value=False, key="fresh_only", disabled=not has_trade_score)

                if available_outcomes:
                    st.markdown("**Trade outcome** (zones whose resulting trade matches):")
                    if hasattr(st, "pills"):
                        st.pills("Outcome", available_outcomes, default=available_outcomes,
                                 selection_mode="multi", key="outcome_types")
                    else:
                        st.multiselect("Outcome", available_outcomes, default=available_outcomes,
                                       key="outcome_types")
                    st.caption(
                        "Only affects zones that actually triggered a trade - zones "
                        "never entered have no outcome to match, so they're excluded "
                        "whenever this filter narrows the selection below 'all'."
                    )

                if bool_cols:
                    st.markdown("**Score flags** (zone must be True for each one enabled):")
                    n_per_row = 3
                    for i in range(0, len(bool_cols), n_per_row):
                        row_cols = st.columns(n_per_row)
                        for col_widget, ts_col in zip(row_cols, bool_cols[i:i + n_per_row]):
                            with col_widget:
                                st.toggle(ts_col, value=False, key=bool_filter_key(ts_col))
    # --- end Chart Filters --------------------------------------------------

    active = get_active_filters(results)

    tf_tabs = st.tabs(list(TF_LABELS.values()))
    for (tf_key, tf_label), tf_tab in zip(TF_LABELS.items(), tf_tabs):
        with tf_tab:
            zone_df = results.zones.get(tf_key)
            if zone_df is None or zone_df.empty:
                st.info(f"No {tf_label.lower()} data available.")
                continue

            # Strength/Freshness/bool score flags/Outcome only apply to the
            # daily tab, since that's the only timeframe your backend
            # scores and backtests.
            is_daily = tf_key == "1d"
            score_df = results.trade_score if is_daily else None
            log_df = results.trade_log if is_daily else None

            trim_mode = trim_option_to_mode.get(st.session_state.get("trim_mode_choice"), "exit")

            filtered = filter_zones(
                zone_df,
                min_base_count=active["min_base_count"],
                zone_types=active["zone_types"],
                pattern_types=active["pattern_types"],
                trade_score=score_df,
                min_strength=active["min_strength"] if is_daily else None,
                fresh_only=active["fresh_only"] if is_daily else False,
                bool_filters=active["bool_filters"] if is_daily else None,
                trade_log=log_df,
                outcome_types=active["outcome_types"] if is_daily else None,
            )
            fig = build_zone_figure(zone_df, config["ticker"], tf_label,
                                     filtered_zones=filtered, trade_score=score_df,
                                     trim_mode=trim_mode, trade_log=log_df)
            chart_heading(config["ticker"], tf_label, len(filtered))
            st.plotly_chart(fig, use_container_width=True, key=f"zone_chart_{tf_key}")

            total_zones = int(zone_df["Zone_Created"].sum()) if "Zone_Created" in zone_df.columns else 0
            source = results.data_sources.get(tf_key, "unknown")
            source_note = SOURCE_NOTES.get(source, source)
            st.caption(
                f"{len(filtered)} of {total_zones} zone(s) shown after filters "
                f"\u00b7 Data source: {source_note}"
            )

            with st.expander(f"View {len(filtered)} filtered zone(s) as a table", expanded=False):
                table = zones_display_table(filtered, trade_score=score_df, zone_df=zone_df,
                                             trade_log=log_df, trim_mode=trim_mode)
                if table.empty:
                    st.caption("No zones match the current filters.")
                else:
                    # Most useful columns first (matches a curated scanner-results
                    # look) - nothing is hidden, any remaining detail columns
                    # (individual boolean flags, raw Zone Created date, etc.)
                    # still follow after, so the table stays scrollable-complete.
                    preferred_order = ["Type", "Pattern", "Price Range", "Base Count", "Strength",
                                        "Status", "Flags", "Zone Created", "Base Start Date",
                                        "Exit/Breach Date", "Proximal", "Distal", "Target"]
                    ordered_cols = [c for c in preferred_order if c in table.columns]
                    ordered_cols += [c for c in table.columns if c not in ordered_cols]
                    table = table[ordered_cols]

                    column_config = {
                        "Proximal": st.column_config.NumberColumn(format="₹%.2f"),
                        "Distal": st.column_config.NumberColumn(format="₹%.2f"),
                        "Target": st.column_config.NumberColumn(format="₹%.2f"),
                        "Zone Created": st.column_config.DateColumn(format="YYYY-MM-DD"),
                        "Base Start Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                        "Exit/Breach Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                    }
                    st.dataframe(table, use_container_width=True, hide_index=True,
                                 column_config=column_config)
                    st.download_button(
                        f"Download {tf_label.lower()} zones as CSV",
                        table.to_csv(index=False).encode("utf-8"),
                        file_name=f"{config['ticker']}_{tf_key}_zones.csv",
                        mime="text/csv", key=f"download_zones_{tf_key}", icon=":material/download:",
                    )
