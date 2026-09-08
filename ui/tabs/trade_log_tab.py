import streamlit as st


def render(config: dict, results):
    if results is None:
        st.info("Run an analysis to see trade-by-trade logs.")
        return

    st.subheader("Trade Log")
    # Step 4 (later): st.dataframe(results.trades, use_container_width=True)
    st.write("Trade log table wired in a later step.")
