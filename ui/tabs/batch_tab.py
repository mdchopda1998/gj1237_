"""
Batch Analysis - runs the SAME per-ticker adapter (zone_identification_multibase
.run_strategy_for_ticker, via the cached data_access.get_strategy_results)
once per selected ticker, using whatever sidebar settings (date range,
risk %, capital, ratio config) are currently set. Results are combined
into one table with Ticker as a column. No backend logic is different
here - it's the identical call the single-ticker tabs make, just looped.
"""
import streamlit as st
import pandas as pd

from data_access import get_strategy_results
from index_constituents import PRESETS, get_ticker_list, get_as_of


def _tickers_from_source(source: str, custom_text: str, uploaded_file) -> list:
    if source in PRESETS:
        return get_ticker_list(source)
    if source == "Upload CSV":
        if uploaded_file is None:
            return []
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            return []
        if df.empty:
            return []
        col = df.columns[0]
        return [str(t).strip().upper() for t in df[col].dropna().tolist()]
    # Custom list
    raw = (custom_text or "").replace(",", "\n")
    return [t.strip().upper() for t in raw.splitlines() if t.strip()]


def render(config: dict):
    st.subheader("🗂️ Batch Analysis")
    st.caption(
        "Runs the exact same analysis as the single-ticker tabs, once per "
        "selected ticker, using the current sidebar settings (date range, "
        "risk %, capital, ratio config). Results combine into one table "
        "with Ticker as a column - your real backend logic is unchanged, "
        "this just loops the same call."
    )

    source = st.radio(
        "Ticker source",
        ["NIFTY 50", "NIFTY Next 50", "NIFTY 100", "Custom list", "Upload CSV"],
        horizontal=True, key="batch_source",
    )

    custom_text, uploaded_file = "", None
    if source == "Custom list":
        custom_text = st.text_area(
            "Tickers (comma or newline separated)",
            value="SAIL.NS, TATASTEEL.NS, JSWSTEEL.NS",
            key="batch_custom_text",
        )
    elif source == "Upload CSV":
        uploaded_file = st.file_uploader(
            "CSV with a column of tickers (first column is used)",
            type=["csv"], key="batch_csv_upload",
        )
    else:
        st.caption(
            f"Static snapshot as of {get_as_of(source)} - NSE rebalances these "
            f"semi-annually. Verify against niftyindices.com if precision "
            f"matters, or use Custom list / Upload CSV instead."
        )

    tickers = _tickers_from_source(source, custom_text, uploaded_file)
    tickers = list(dict.fromkeys(tickers))  # de-dupe, keep order

    if tickers:
        preview = ", ".join(tickers[:10]) + (f", ... (+{len(tickers) - 10} more)" if len(tickers) > 10 else "")
        st.write(f"**{len(tickers)} ticker(s) selected:** {preview}")
    else:
        st.write("**0 tickers selected**")

    if len(tickers) > 25:
        st.caption(
            f"⏱️ {len(tickers)} tickers is a lot for a single run - each one repeats the full "
            "zone detection/backtest/scoring pipeline. Local CSVs in your data folder are much "
            "faster than live yfinance fetches; large batches with live fetches can take several minutes."
        )

    b1, b2 = st.columns([1, 1])
    run_batch = b1.button("▶ Run Batch Analysis", type="primary", disabled=(len(tickers) == 0),
                           use_container_width=True)
    if b2.button("🗑 Clear batch results", use_container_width=True):
        for key in ("batch_results", "batch_table", "batch_timestamp"):
            st.session_state.pop(key, None)
        st.rerun()

    if run_batch:
        progress = st.progress(0.0, text="Starting batch analysis...")
        batch_results = {}
        rows = []
        for i, ticker in enumerate(tickers):
            progress.progress(i / len(tickers), text=f"Analyzing {ticker} ({i + 1}/{len(tickers)})...")
            err = None
            res = None
            try:
                res = get_strategy_results(
                    ticker, config["start_date"], config["end_date"],
                    config["risk_pct"], config["initial_capital"],
                    config["data_dir"], config["ratio"],
                )
                err = getattr(res, "error", None)
            except Exception as e:
                err = f"{type(e).__name__}: {e}"

            batch_results[ticker] = res
            m = (res.metrics if res is not None else {}) or {}
            status = "Error" if err else ("No Trades" if not m else "OK")
            rows.append({
                "Ticker": ticker, "Status": status, "Error": err,
                "Composite Score": m.get("Composite Score"),
                "Win Rate": m.get("Win Rate"),
                "Profit Factor": m.get("Profit Factor"),
                "System Expectancy": m.get("System Expectancy"),
                "Total Trades": m.get("Total Trades"),
                "Net PNL": m.get("Net PNL"),
                "Demand Zones": m.get("Demand Zones"),
                "Supply Zones": m.get("Supply Zones"),
            })
        progress.progress(1.0, text="Batch analysis complete.")

        st.session_state["batch_results"] = batch_results
        st.session_state["batch_table"] = pd.DataFrame(rows)
        import datetime
        st.session_state["batch_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.toast(f"Batch analysis complete: {len(tickers)} ticker(s)", icon="✅")

    table = st.session_state.get("batch_table")
    if table is None or table.empty:
        st.info("Select tickers and click Run Batch Analysis to see combined results.")
        return

    st.markdown("---")
    st.caption(f"Batch last run: {st.session_state.get('batch_timestamp', '?')}")

    ok_count = int((table["Status"] == "OK").sum())
    no_trade_count = int((table["Status"] == "No Trades").sum())
    err_count = int((table["Status"] == "Error").sum())
    s1, s2, s3 = st.columns(3)
    s1.metric("Successful", ok_count)
    s2.metric("No trades", no_trade_count)
    s3.metric("Errors", err_count)

    f1, f2 = st.columns([2, 2])
    with f1:
        use_score_filter = st.toggle("Filter by minimum Composite Score", value=False, key="batch_use_score_filter")
        min_score = st.slider("Min Composite Score", 0, 100, 0, key="batch_min_score",
                               disabled=not use_score_filter)
    with f2:
        sort_by = st.selectbox(
            "Sort by", ["Composite Score", "Win Rate", "Profit Factor", "Net PNL", "Total Trades", "Ticker"],
            key="batch_sort_by",
        )

    display_table = table.copy()
    if use_score_filter:
        display_table = display_table[display_table["Composite Score"].fillna(-1) >= min_score]
    display_table = display_table.sort_values(sort_by, ascending=(sort_by == "Ticker"), na_position="last")

    column_config = {
        "Win Rate": st.column_config.NumberColumn(format="%.1f%%"),
        "Net PNL": st.column_config.NumberColumn(format="₹%.2f"),
        "Composite Score": st.column_config.NumberColumn(format="%.1f"),
        "Profit Factor": st.column_config.NumberColumn(format="%.2f"),
    }
    st.dataframe(display_table.drop(columns=["Error"]), use_container_width=True, hide_index=True,
                 column_config=column_config)
    st.caption(f"{len(display_table)} of {len(table)} tickers shown.")

    errored = table[table["Status"] == "Error"]
    if not errored.empty:
        with st.expander(f"⚠️ {len(errored)} ticker(s) with errors"):
            st.dataframe(errored[["Ticker", "Error"]], use_container_width=True, hide_index=True)

    st.download_button(
        "⬇ Download batch results as CSV",
        display_table.to_csv(index=False).encode("utf-8"),
        file_name="batch_analysis_results.csv", mime="text/csv", key="download_batch_csv",
    )

    st.markdown("---")
    st.markdown("##### Drill into a single ticker")
    st.caption("Loads that ticker's full analysis (already computed above) into the Charts/Metrics/Trade Log tabs - no re-run.")
    ok_tickers = table[table["Status"] == "OK"]["Ticker"].tolist()
    if ok_tickers:
        pick = st.selectbox("Ticker", ok_tickers, key="batch_drill_pick", label_visibility="collapsed")
        if st.button("Load into single-ticker tabs", key="batch_drill_load"):
            st.session_state["results"] = st.session_state["batch_results"][pick]
            loaded_config = dict(config)
            loaded_config["ticker"] = pick
            st.session_state["config"] = loaded_config
            st.toast(f"Loaded {pick} into Charts/Metrics/Trade Log tabs", icon="📊")
            st.rerun()
    else:
        st.caption("No successfully analyzed tickers to drill into yet.")
