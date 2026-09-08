# data_access.py
import streamlit as st
from zone_identification_multibase import run_strategy_for_ticker

@st.cache_data(show_spinner="Running zone detection & backtest...")
def get_strategy_results(ticker: str, start_date, end_date, risk_pct: float, initial_capital: float):
    """
    Thin, cached wrapper around the backend entry point.
    Cache key = the function args, so re-running with the same
    ticker/date range/risk/capital is instant on repeat clicks.
    """
    return run_strategy_for_ticker(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        risk_pct=risk_pct,
        initial_capital=initial_capital,
    )