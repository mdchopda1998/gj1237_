"""
*** PLACEHOLDER BACKEND ***

Delete this file and drop your real `zone_identification_multibase.py`
(the one with yfinance loading, multi-base zone ID, Kalman trend
detection, risk sim, and Plotly viz) in its place at the repo root.

This stub exists ONLY so `streamlit run app.py` works immediately after
unzipping, so you can confirm the UI wiring before swapping in your
real logic. It returns fake-but-shaped data matching what data_access.py
expects: something with .figure / .metrics / .trades (adjust in
data_access.py + the tab files if your real return shape differs).
"""
from dataclasses import dataclass
from datetime import date
import pandas as pd
import plotly.graph_objects as go


@dataclass
class StrategyResults:
    figure: go.Figure
    metrics: dict
    trades: pd.DataFrame


def run_strategy_for_ticker(ticker: str, start_date: date, end_date: date,
                             risk_pct: float, initial_capital: float) -> StrategyResults:
    """Fake implementation - replace with your real backend entry point."""
    fig = go.Figure()
    fig.add_annotation(text=f"Placeholder chart for {ticker}", showarrow=False)

    metrics = {
        "total_trades": 0,
        "win_rate": 0.0,
        "expectancy_r": 0.0,
        "final_capital": initial_capital,
    }

    trades = pd.DataFrame(columns=["date", "direction", "proximal", "distal", "target", "outcome", "r_multiple"])

    return StrategyResults(figure=fig, metrics=metrics, trades=trades)
