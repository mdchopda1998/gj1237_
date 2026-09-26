"""
Thin, cached wrapper around zone_identification_multibase.py (the adapter
that calls your real smc_backend.py). This is the ONLY file that should
import the adapter directly - every UI module goes through here.
"""
import streamlit as st

from zone_identification_multibase import run_strategy_for_ticker


@st.cache_data(show_spinner="Running zone detection & backtest...")
def get_strategy_results(ticker: str, start_date, end_date, risk_pct: float,
                          initial_capital: float, data_dir: str, ratio: dict,
                          zone_params: dict = None):
    """
    Cache key = the function args (ratio and zone_params included, since
    both are real inputs to zone detection) - so re-running with identical
    settings is instant on repeat clicks. The expensive CSV-or-live OHLC
    load itself is cached separately, one level down, in
    data_loading.load_multi_interval().
    """
    return run_strategy_for_ticker(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        risk_pct=risk_pct,
        initial_capital=initial_capital,
        data_dir=data_dir,
        ratio=ratio,
        zone_params=zone_params,
    )
