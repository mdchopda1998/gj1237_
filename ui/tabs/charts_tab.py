# ui/tabs/charts_tab.py
import streamlit as st

def render(config: dict, results):
    if results is None:
        st.info("Set your parameters and click **Run Analysis** to see charts.")
        return
    # st.plotly_chart(results.figure, use_container_width=True)   # <- Step 2/3