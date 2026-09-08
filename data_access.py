import streamlit as st
from zone_identification_multibase import run_strategy_for_ticker
@st.cache_data(show_spinner=False)
def get_strategy_results(ticker,start_date,end_date,risk_pct,initial_capital,show_swing=False,show_bos=False):
    return run_strategy_for_ticker(ticker,start_date,end_date,risk_pct,initial_capital,show_swing,show_bos)
