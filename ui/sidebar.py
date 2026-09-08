# ui/sidebar.py
import streamlit as st
from datetime import date, timedelta

def render_sidebar() -> dict:
    st.sidebar.header("Configuration")

    ticker = st.sidebar.text_input("Ticker", value="SAIL.NS")

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(date.today() - timedelta(days=365 * 3), date.today()),
    )

    risk_pct = st.sidebar.slider(
        "Risk per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1
    )

    initial_capital = st.sidebar.number_input(
        "Initial Capital (₹)", min_value=10_000, value=500_000, step=10_000
    )

    return {
        "ticker": ticker,
        "start_date": date_range[0] if len(date_range) == 2 else None,
        "end_date": date_range[1] if len(date_range) == 2 else None,
        "risk_pct": risk_pct,
        "initial_capital": initial_capital,
    }