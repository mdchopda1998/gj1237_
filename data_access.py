"""
Thin, cached wrappers around zone_identification_multibase.py.
This is the ONLY file that should import the backend directly -
every UI module goes through here.
"""
import streamlit as st

from zone_identification_multibase import run_strategy_for_ticker


@st.cache_data(show_spinner="Running zone detection & backtest...")
def get_strategy_results(ticker: str, start_date, end_date, risk_pct: float, initial_capital: float):
    """
    Cache key = the function args, so re-running with identical
    ticker/date range/risk/capital is instant on repeat clicks.

    NOTE: only cache_data-safe here because run_strategy_for_ticker is
    assumed to return plain data (DataFrames/dicts/dataclasses). If it
    ever returns something non-picklable (e.g. a live yfinance session,
    an open DB connection), pull that piece into a separate
    @st.cache_resource function instead.
    """
    return run_strategy_for_ticker(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        risk_pct=risk_pct,
        initial_capital=initial_capital,
    )
