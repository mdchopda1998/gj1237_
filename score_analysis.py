"""
Pure analysis of how trade outcomes (Win Rate, PnL) vary with trade-score
attributes (Strength, Base Count, and every boolean flag from your real
calculate_trade_score output). No backend calls, no re-analysis - this
re-slices/re-aggregates data that's already been computed (trade_log +
trade_score), the same way filter_state.py and charting.py do.
"""
import numpy as np
import pandas as pd


def merge_trade_log_with_score(trade_log: pd.DataFrame, trade_score: pd.DataFrame) -> pd.DataFrame:
    """
    Left-joins trade_log with trade_score on their shared index (zone
    creation date). Every trade keeps its Outcome/Trade_PnL; score columns
    (Strength, Base Count, Gapped, BOS, ...) are attached where available.
    Trades with no matching trade_score row (shouldn't normally happen -
    both derive from the same daily zones) get NaN score columns rather
    than being dropped.
    """
    if trade_log is None or trade_log.empty:
        return pd.DataFrame()
    if trade_score is None or trade_score.empty:
        return trade_log.copy()
    score_only_cols = [c for c in trade_score.columns if c not in trade_log.columns]
    return trade_log.join(trade_score[score_only_cols], how="left")


def _win_rate(outcomes: pd.Series) -> float:
    if len(outcomes) == 0:
        return np.nan
    return 100 * (outcomes == "Profit").sum() / len(outcomes)


def numeric_breakdown(merged: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Groups trades by a numeric score column (e.g. Strength, Base Count)
    and computes Trades / Win Rate / Avg PnL / Net PnL per value. Rows
    with NaN in that column are excluded (not every trade has every
    score dimension).
    """
    if column not in merged.columns:
        return pd.DataFrame()
    df = merged.dropna(subset=[column, "Outcome", "Trade_PnL"])
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby(column).agg(
        Trades=("Trade_PnL", "count"),
        **{"Win Rate": ("Outcome", _win_rate)},
        **{"Avg PnL": ("Trade_PnL", "mean")},
        **{"Net PnL": ("Trade_PnL", "sum")},
    ).reset_index()
    return grouped.sort_values(column)


def boolean_flag_summary(merged: pd.DataFrame, flag_columns: list) -> pd.DataFrame:
    """
    One row per boolean flag: Win Rate / Avg PnL / trade count with the
    flag True vs False, and the Win Rate delta between them - sorted by
    |delta| descending so the most outcome-correlated factors surface
    first. This is the "how do all the important factors vary" table.
    """
    rows = []
    for col in flag_columns:
        if col not in merged.columns:
            continue
        sub = merged.dropna(subset=[col, "Outcome", "Trade_PnL"])
        if sub.empty:
            continue
        true_g = sub[sub[col] == True]  # noqa: E712
        false_g = sub[sub[col] == False]  # noqa: E712
        if true_g.empty and false_g.empty:
            continue

        n_t, wr_t = len(true_g), _win_rate(true_g["Outcome"])
        n_f, wr_f = len(false_g), _win_rate(false_g["Outcome"])
        pnl_t = true_g["Trade_PnL"].mean() if n_t else np.nan
        pnl_f = false_g["Trade_PnL"].mean() if n_f else np.nan
        delta = wr_t - wr_f if (n_t and n_f) else np.nan

        rows.append({
            "Flag": col,
            "N (True)": n_t, "Win Rate (True)": wr_t, "Avg PnL (True)": pnl_t,
            "N (False)": n_f, "Win Rate (False)": wr_f, "Avg PnL (False)": pnl_f,
            "Win Rate Delta": delta,
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.reindex(result["Win Rate Delta"].abs().sort_values(ascending=False).index).reset_index(drop=True)
