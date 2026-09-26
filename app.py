"""
SMC Scanner & Backtester - Streamlit entry point.

Run with:
    streamlit run app.py
"""
import streamlit as st

from data_access import get_strategy_results
from data_loading import load_multi_interval
from ui.sidebar import render_sidebar
from ui.right_panel import render_right_panel
from ui.style import inject_global_css, app_header
from ui.tabs import charts_tab, metrics_tab, trade_log_tab, batch_tab, score_tab
from zone_identification_multibase import NIFTY_TICKER, TIMEFRAMES

st.set_page_config(page_title="GJ1-2-37", layout="wide", page_icon=":material/candlestick_chart:")

# Bump this on every delivered zip. If this string doesn't match what you
# expect to see in the header badges, you're running stale files - re-unzip
# and replace the WHOLE folder rather than copying individual files over.
APP_BUILD = "2026-09-15"


def _run_analysis_with_status(config: dict):
    """
    Staged progress via st.status() - each stage below is a REAL step
    (not cosmetic): the two data_loading calls are the same @st.cache_data
    functions the adapter itself calls internally, so they're instant here
    if already cached, and real work otherwise. No backend logic changes -
    this only adds visibility into stages that already existed.
    """
    with st.status("Running analysis...", expanded=True) as status:
        st.write(f"Loading {config['ticker']} OHLC (CSV-first, live fallback)...")
        load_multi_interval(config["ticker"], config["start_date"], config["end_date"],
                             data_dir=config["data_dir"], intervals=tuple(TIMEFRAMES.keys()))

        st.write(f"Loading {NIFTY_TICKER} benchmark OHLC...")
        load_multi_interval(NIFTY_TICKER, config["start_date"], config["end_date"],
                             data_dir=config["data_dir"], intervals=tuple(TIMEFRAMES.keys()))

        st.write("Running zone detection, backtest & scoring (your real backend)...")
        results = get_strategy_results(
            config["ticker"], config["start_date"], config["end_date"],
            config["risk_pct"], config["initial_capital"],
            config["data_dir"], config["ratio"], config["zone_params"],
        )

        if getattr(results, "error", None):
            status.update(label="Analysis finished with an error", state="error", expanded=True)
        else:
            n_zones = sum(int(df["Zone_Created"].sum()) for df in results.zones.values() if df is not None)
            status.update(label=f"Analysis complete \u2014 {n_zones} zones across all timeframes",
                           state="complete", expanded=False)
        return results


def main():
    inject_global_css()

    config = render_sidebar()
    run_clicked = st.sidebar.button("Run Analysis", type="primary", icon=":material/play_arrow:",
                                     use_container_width=True)

    # Main content (left) + Strategy Parameters control panel (right). The
    # panel must render, and its values land in config["zone_params"],
    # BEFORE the run_clicked handling below so a click on this same rerun
    # uses whatever is currently showing in the panel's widgets.
    main_col, params_col = st.columns([4, 1.3], gap="large")

    with params_col:
        config["zone_params"] = render_right_panel()

    with main_col:
        # Reserve the header's visual slot at the very top of the page now,
        # but fill in its actual content later (after run-analysis below) so
        # the status badge reflects what just happened in THIS script run
        # rather than the previous one. st.empty() lets content appear later
        # in code while still rendering in this earlier position on screen -
        # otherwise the st.status() progress box below would render ABOVE
        # the header instead of below it.
        header_slot = st.empty()

        if run_clicked:
            if not config["ticker"]:
                st.sidebar.error("Enter a ticker first.")
            else:
                try:
                    results = _run_analysis_with_status(config)
                    st.session_state["results"] = results
                    st.session_state["config"] = config
                    if getattr(results, "error", None):
                        st.toast(f"Analysis failed for {results.ticker}", icon=":material/error:")
                    else:
                        st.toast(f"Analysis complete for {results.ticker}", icon=":material/check_circle:")
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                    st.toast("Analysis crashed - see error above", icon=":material/error:")

        results = st.session_state.get("results")
        active_config = st.session_state.get("config", config)

        status_badge = {"text": "No analysis yet", "muted": True}
        if results is not None:
            if getattr(results, "error", None):
                status_badge = {"text": f"Error \u00b7 {results.ticker}", "variant": "error"}
            else:
                status_badge = {"text": f"{results.ticker} \u00b7 {results.analysis_timestamp}", "variant": "success"}

        with header_slot.container():
            app_header(
                title="Supply & Demand Scanner",
                subtitle="Smart Money Concepts zone detection, backtesting & scoring",
                icon="candlestick_chart",
                badges=[
                    {"text": f"Jay Murlidhar", "muted": True},
                    {"text": f"Rules - Persistence - Patience", "muted": True},
                    status_badge,
                ],
            )

        with st.expander("Diagnostics", expanded=False):
            st.caption(
                f"results loaded = {results is not None}"
                + (f" for {results.ticker}" if results is not None else "")
                + (f" (error: {results.error})" if results is not None and getattr(results, "error", None) else "")
            )

        if results is not None and getattr(results, "error", None):
            st.error(f"Backend error for {results.ticker}: {results.error}")

        tab_charts, tab_metrics, tab_logs, tab_score, tab_batch = st.tabs([
            ":material/candlestick_chart: Charts",
            ":material/monitoring: Backtest Metrics",
            ":material/receipt_long: Trade Logs",
            ":material/bar_chart: Score Analysis",
            ":material/grid_view: Batch Analysis",
        ])

        with tab_charts:
            charts_tab.render(active_config, results)

        with tab_metrics:
            metrics_tab.render(active_config, results)

        with tab_logs:
            trade_log_tab.render(active_config, results)

        with tab_score:
            score_tab.render(active_config, results)

        with tab_batch:
            batch_tab.render(active_config)


if __name__ == "__main__":
    main()
