"""
Adapter between the Streamlit UI and your REAL backend (smc_backend.py).

This is the ANALYSIS half only - zone detection, backtesting, scoring.
It does NOT build any figures. Plotting is deliberately split out into
charting.py, which is called from ui/tabs/charts_tab.py at render time
(cheap, reruns on every filter-widget interaction) rather than baked in
here (expensive, cached via data_access.py, only reruns when you click
"Run Analysis"). That split is what lets you re-filter which zones are
drawn (by Base Count, Strength, Demand/Supply, etc.) without re-running
zone detection/backtesting/scoring.

One bridging fix applied HERE (not inside smc_backend.py - see the comment
at BRIDGE FIX below): your real run_risk_management_simulation() drops the
'Outcome' and 'Date Created' columns that evaluate_strategy_metrics()
requires, even though they're present one step earlier in df_bt (backtest_zones
output) and share the same index. Confirmed empirically: df_bt and df_rm
share the same DatetimeIndex (zone creation date), df_rm is a row-subset of
df_bt (rows where a trade was never triggered are dropped). So we rejoin
those two columns from df_bt onto df_rm by index before calling
evaluate_strategy_metrics(). This is a workaround at the integration layer;
the cleaner long-term fix is for run_risk_management_simulation() to carry
those columns through itself.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

import smc_backend as be
from data_loading import load_multi_interval
from ratio_config import default_ratio, resolve_gen_ratio

NIFTY_TICKER = "^NSEI"
TIMEFRAMES = {"1d": "Daily", "1wk": "Weekly", "1mo": "Monthly"}


def _synthetic_ohlc(ticker: str, start: date, end: date) -> pd.DataFrame:
    """Last-resort fallback: used only if neither a saved CSV nor a live
    yfinance fetch produced data (e.g. no network, bad ticker)."""
    idx = pd.date_range(start, end, freq="B")
    rng = np.random.default_rng(abs(hash(ticker)) % (2**32))
    price = 100 + np.cumsum(rng.normal(0, 1.5, len(idx)))
    df = pd.DataFrame(index=idx)
    df.index.name = "Date"
    df["Open"] = price + rng.normal(0, 0.5, len(idx))
    df["Close"] = price
    df["High"] = df[["Open", "Close"]].max(axis=1) + rng.uniform(0, 1, len(idx))
    df["Low"] = df[["Open", "Close"]].min(axis=1) - rng.uniform(0, 1, len(idx))
    df["Volume"] = rng.integers(1_000, 100_000, len(idx))
    return df


def _ensure_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Several of your real functions (compute_volume_zscore, etc.) expect
    a Volume column - some saved CSVs may not have one."""
    if "Volume" not in df.columns:
        df = df.copy()
        df["Volume"] = 0
    return df


def _load_ticker_across_timeframes(ticker: str, start_date, end_date, data_dir: str):
    """Returns ({interval: df}, {interval: source}) for one ticker."""
    loaded = load_multi_interval(ticker, start_date, end_date, data_dir=data_dir,
                                  intervals=tuple(TIMEFRAMES.keys()))
    dfs, sources = {}, {}
    for tf, (df, source) in loaded.items():
        if df is None:
            df = _synthetic_ohlc(f"{ticker}-{tf}", start_date, end_date)
            source = "synthetic"
        dfs[tf] = _ensure_volume(df)
        sources[tf] = source
    return dfs, sources


@st.cache_data(show_spinner=False)
def _build_nifty_zone_dfs(start_date, end_date, data_dir: str, ratio: dict):
    """
    Mirrors your driver script's:
        nifty_1d_df = identity_zones_with_multibase(data['^NSEI']['1d'], ratio['GEN.NS']['1d'])
    Returns (dict_of_dfs, dict_of_sources); any timeframe that errors out
    is set to None (calculate_trade_score already handles None gracefully).
    """
    dfs, sources = _load_ticker_across_timeframes(NIFTY_TICKER, start_date, end_date, data_dir)
    nifty_zones = {}
    for tf in TIMEFRAMES:
        try:
            nifty_zones[tf] = be.identity_zones_with_multibase(dfs[tf].copy(), resolve_gen_ratio(tf, ratio))
        except Exception:
            nifty_zones[tf] = None
    return nifty_zones, sources


@dataclass
class StrategyResults:
    ticker: str
    zones: dict                          # {'1d': df, '1wk': df, '1mo': df} - real columns, for plotting
    trade_log: pd.DataFrame              # df_rm, bridged with Outcome/Date Created
    trade_score: pd.DataFrame = field(default_factory=pd.DataFrame)  # df_ts (1d only) - Strength/Freshness/BOS/OB/...
    data_sources: dict = field(default_factory=dict)       # ticker OHLC sources
    nifty_data_sources: dict = field(default_factory=dict)  # nifty OHLC sources
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None          # set if the real backend raised
    analysis_timestamp: Optional[str] = None  # when this StrategyResults was computed


def recompute_metrics_for_subset(trade_log: pd.DataFrame) -> dict:
    """
    Re-runs your real evaluate_strategy_metrics/calculate_composite_score
    on an already-filtered SLICE of an existing trade_log. This is NOT
    re-analysis - no zone detection, no backtest, no data fetch - just the
    same pure-pandas aggregation your functions already do, over fewer
    rows. Used to show "metrics for the currently filtered zones" without
    re-running "Run Analysis". Returns {} for an empty/None input.
    """
    if trade_log is None or trade_log.empty:
        return {}
    try:
        metrics = be.evaluate_strategy_metrics(trade_log.copy())
        metrics["Composite Score"] = be.calculate_composite_score(metrics)
        return metrics
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def run_strategy_for_ticker(ticker: str, start_date: date, end_date: date,
                             risk_pct: float, initial_capital: float,
                             data_dir: str = "data", ratio: dict = None) -> StrategyResults:
    """
    Real integration: loads OHLC (CSV-first/live-fallback/synthetic-last-resort)
    for both `ticker` and the Nifty benchmark, then calls your actual
    smc_backend.run_strategy_for_ticker(). Any exception from your backend
    is caught and returned via StrategyResults.error rather than crashing
    the app. Returns raw zone/trade-score/trade-log data only - no
    figures; see charting.py for that.
    """
    ratio = ratio or default_ratio()
    ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ticker_dfs, ticker_sources = _load_ticker_across_timeframes(ticker, start_date, end_date, data_dir)
    nifty_zones, nifty_sources = _build_nifty_zone_dfs(start_date, end_date, data_dir, ratio)

    data = {ticker: ticker_dfs}
    try:
        out = be.run_strategy_for_ticker(
            ticker, data, ratio,
            nifty_zones.get("1d"), nifty_zones.get("1wk"), nifty_zones.get("1mo"),
            C=initial_capital, risk=risk_pct,
        )
    except Exception as e:
        return StrategyResults(
            ticker=ticker, zones={}, trade_log=pd.DataFrame(),
            data_sources=ticker_sources, nifty_data_sources=nifty_sources,
            error=f"Backend raised {type(e).__name__}: {e}",
            analysis_timestamp=ts_now,
        )

    zones = out.get("zones") or {}
    if not zones or zones.get("1d") is None:
        return StrategyResults(
            ticker=ticker, zones={}, trade_log=pd.DataFrame(),
            data_sources=ticker_sources, nifty_data_sources=nifty_sources,
            error=f"No zones were identified for {ticker} with the current ratio settings.",
            analysis_timestamp=ts_now,
        )

    trade_score = out.get("anal", {}).get("ts")
    if trade_score is None:
        trade_score = pd.DataFrame()

    df_bt = out.get("anal", {}).get("bt")
    df_rm = out.get("anal", {}).get("rm")

    metrics = {}
    trade_log = pd.DataFrame()
    if df_rm is not None and not df_rm.empty:
        trade_log = df_rm.copy()

        # --- BRIDGE FIX: rejoin columns your real run_risk_management_simulation drops ---
        if "Outcome" not in trade_log.columns and df_bt is not None and "Outcome" in df_bt.columns:
            trade_log["Outcome"] = df_bt.loc[trade_log.index, "Outcome"]
        if "Date Created" not in trade_log.columns:
            trade_log["Date Created"] = trade_log.index
        if "Zone_Type" not in trade_log.columns and "Zone_Type" in (df_bt.columns if df_bt is not None else []):
            trade_log["Zone_Type"] = df_bt.loc[trade_log.index, "Zone_Type"]
        # --- end bridge fix ---

        try:
            metrics = be.evaluate_strategy_metrics(trade_log.copy())
            metrics["Composite Score"] = be.calculate_composite_score(metrics)
        except Exception as e:
            metrics = {}
            trade_log.attrs["metrics_error"] = f"{type(e).__name__}: {e}"

    return StrategyResults(
        ticker=ticker, zones=zones, trade_log=trade_log, trade_score=trade_score,
        data_sources=ticker_sources, nifty_data_sources=nifty_sources,
        metrics=metrics, analysis_timestamp=ts_now,
    )
