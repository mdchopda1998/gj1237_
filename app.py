# app.py
import streamlit as st
from ui.sidebar import render_sidebar
from ui.tabs import charts_tab, metrics_tab, trade_log_tab
#from data_access import get_strategy_results

st.set_page_config(page_title="SMC Scanner & Backtester", layout="wide")

def main():
    st.title("Supply & Demand Scanner")

    config = render_sidebar()  # dict/dataclass: ticker, dates, risk_pct, capital

    run_clicked = st.sidebar.button("Run Analysis", type="primary")

    if run_clicked:
        st.session_state["config"] = config
        st.session_state["should_run"] = True

    # if run_clicked:
    #     with st.spinner("Fetching data and computing zones..."):
    #         try:
    #             results = get_strategy_results(
    #                 config["ticker"],
    #                 config["start_date"],
    #                 config["end_date"],
    #                 config["risk_pct"],
    #                 config["initial_capital"],
    #             )
    #             st.session_state["results"] = results
    #         except Exception as e:
    #             st.error(f"Analysis failed: {e}")    

    tab_charts, tab_metrics, tab_logs = st.tabs(
        ["Charts", "Backtest Metrics", "Trade Logs"]
    )

    results = st.session_state.get("results")

    with tab_charts:
        charts_tab.render(config, results)

    with tab_metrics:
        metrics_tab.render(config, results)

    with tab_logs:
        trade_log_tab.render(config, results)

if __name__ == "__main__":
    main()

# app.py  (only the changed part)

