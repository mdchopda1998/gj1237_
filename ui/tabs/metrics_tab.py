import streamlit as st


def render(config: dict, results):
    if results is None:
        st.info("Run an analysis to see backtest metrics.")
        return

    st.subheader("Backtest Metrics")
    # Step 3 (later): pull KPIs from results.metrics and render as
    # st.metric(...) cards + a summary table.
    st.write("KPI cards wired in a later step.")
