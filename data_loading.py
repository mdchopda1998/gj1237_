"""
CSV-first, yfinance-fallback OHLC loading.

Mirrors the two data paths already in your real my_backend.py:
  - load_data()      -> saved CSVs on disk, named like 'ABB_NS_1d.csv'
  - download_data()  -> live yfinance pull

Resolution order per (ticker, interval):
  1. Saved CSV at <data_dir>/<TICKER_with_.->_>_<interval>.csv
  2. Live yfinance download
  3. Neither available -> DataUnavailableError, caught upstream so the UI
     can show a clear message instead of crashing.
"""
import os
import time
from typing import Optional

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except ImportError:
    yf = None


class DataUnavailableError(RuntimeError):
    pass


def _csv_path(data_dir: str, ticker: str, interval: str) -> str:
    # Matches your load_data() naming convention: 'ABB.NS' -> 'ABB_NS_1d.csv'
    safe_ticker = ticker.replace(".", "_")
    return os.path.join(data_dir, f"{safe_ticker}_{interval}.csv")


def _load_from_csv(data_dir: str, ticker: str, interval: str) -> Optional[pd.DataFrame]:
    path = _csv_path(data_dir, ticker, interval)
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, index_col="Date", parse_dates=True)
        return df if not df.empty else None
    except Exception:
        return None


def _fetch_from_yfinance(ticker: str, interval: str, start_date, end_date) -> Optional[pd.DataFrame]:
    if yf is None:
        return None
    try:
        time.sleep(0.2)  # avoid rate limiting, same spirit as your download_data()
        df = yf.download(ticker, start=start_date, end=end_date, interval=interval,
                          progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        return df
    except Exception:
        return None


def load_ohlc(ticker: str, interval: str, start_date, end_date, data_dir: str = "data"):
    """Returns (df, source) with source in {'csv', 'live'}, or raises DataUnavailableError."""
    df = _load_from_csv(data_dir, ticker, interval)
    if df is not None:
        return df, "csv"

    df = _fetch_from_yfinance(ticker, interval, start_date, end_date)
    if df is not None:
        return df, "live"

    raise DataUnavailableError(
        f"No saved CSV for {ticker} ({interval}) in '{data_dir}/', and the live "
        f"yfinance fetch also failed or returned no data."
    )


@st.cache_data(show_spinner=False)
def load_multi_interval(ticker: str, start_date, end_date, data_dir: str = "data",
                         intervals=("1d", "1wk", "1mo")) -> dict:
    """
    {interval: (df_or_None, source)} for the given ticker across all intervals.
    source is 'csv', 'live', or 'unavailable'.

    Cached on (ticker, start_date, end_date, data_dir, intervals) so tweaking
    only risk%/capital in the sidebar doesn't re-hit disk or the network.
    """
    out = {}
    for interval in intervals:
        try:
            df, source = load_ohlc(ticker, interval, start_date, end_date, data_dir)
            out[interval] = (df, source)
        except DataUnavailableError:
            out[interval] = (None, "unavailable")
    return out
