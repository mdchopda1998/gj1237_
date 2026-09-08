import streamlit as st


def render(config: dict, results):
    if results is None:
        st.info("Set your parameters and click **Run Analysis** to see charts.")
        return

    st.subheader(f"{config['ticker']} - Zones & Price Action")
    # Step 2 (next): unpack results.figure (Plotly) and render it, e.g.
    # st.plotly_chart(results.figure, use_container_width=True)
    st.write("Chart rendering wired in Step 2.")
