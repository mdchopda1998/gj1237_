"""
Zone-detection ratio config.

DEFAULT_RATIO is copied verbatim from the `ratio` dict in your real
my_backend.py (the 'ORG.NS' and 'GEN.NS' entries near the bottom of the
file). Kept as the shipped default so behavior matches what you already
had, before any sidebar tuning.

IMPORTANT - confirmed by reading your real run_strategy_for_ticker: it
currently calls identity_zones_with_multibase(..., ratio['GEN.NS'][interval])
unconditionally - the `ticker` argument passed to run_strategy_for_ticker
is NOT used to look up a ticker-specific ratio, even though your `ratio`
dict has room for one (e.g. 'ORG.NS'). So today, ONLY ratio['GEN.NS'] has
any effect, regardless of which ticker you run. The sidebar below reflects
that reality: it edits ratio['GEN.NS'] for all three timeframes. If you'd
like ticker-specific ratios to actually take effect, that one line in your
real run_strategy_for_ticker (in smc_backend.py) would need to change to
something like ratio.get(ticker, ratio['GEN.NS'])[interval] - flagging
this rather than changing it silently.

PRESETS below are your `test_scenarios` dict from the same file - useful
as one-click starting points for the daily (1d) ratio specifically, since
that's what you were using them for.
"""
import copy

DEFAULT_RATIO = {
    "ORG.NS": {
        "1d": {
            "Exciting": {"TR_ATR": 0.5, "BS_TR": 0.5},
            "Base": {"TR_ATR": 1.0, "BS_TR": 0.4},
            "Explosive": {"TR_ATR": 1.2, "BS_TR": 0.7},
        },
    },
    "GEN.NS": {
        "1d": {
            "Exciting": {"TR_ATR": 0.5, "BS_TR": 0.6},
            "Base": {"TR_ATR": 1.2, "BS_TR": 0.5},
            "Explosive": {"TR_ATR": 1.2, "BS_TR": 0.6},
        },
        "1wk": {
            "Exciting": {"TR_ATR": 0.4, "BS_TR": 0.5},
            "Base": {"TR_ATR": 1.3, "BS_TR": 0.4},
            "Explosive": {"TR_ATR": 0.8, "BS_TR": 0.5},
        },
        "1mo": {
            "Exciting": {"TR_ATR": 0.4, "BS_TR": 0.5},
            "Base": {"TR_ATR": 1.3, "BS_TR": 0.4},
            "Explosive": {"TR_ATR": 0.4, "BS_TR": 0.5},
        },
    },
}

# Your test_scenarios dict, for the daily (1d) GEN.NS ratio specifically.
DAILY_PRESETS = {
    "Standard": {
        "Exciting": {"TR_ATR": 0.5, "BS_TR": 0.5},
        "Base": {"TR_ATR": 1.0, "BS_TR": 0.4},
        "Explosive": {"TR_ATR": 1.2, "BS_TR": 0.7},
    },
    "Aggressive_Explosive": {
        "Exciting": {"TR_ATR": 0.5, "BS_TR": 0.5},
        "Base": {"TR_ATR": 1.0, "BS_TR": 0.4},
        "Explosive": {"TR_ATR": 1.5, "BS_TR": 0.8},
    },
    "Tight_Base": {
        "Exciting": {"TR_ATR": 0.5, "BS_TR": 0.5},
        "Base": {"TR_ATR": 0.8, "BS_TR": 0.3},
        "Explosive": {"TR_ATR": 1.2, "BS_TR": 0.7},
    },
    # Backtested against SAIL_NS_1d.csv earlier in this project (41 zones,
    # 63.9% win rate, +0.92R expectancy) - included as a fourth preset.
    "SAIL_Backtested": {
        "Exciting": {"TR_ATR": 0.5, "BS_TR": 0.6},
        "Base": {"TR_ATR": 1.2, "BS_TR": 0.5},
        "Explosive": {"TR_ATR": 1.2, "BS_TR": 0.6},
    },
}


def default_ratio() -> dict:
    """A fresh deep copy - callers can mutate freely without touching DEFAULT_RATIO."""
    return copy.deepcopy(DEFAULT_RATIO)


def resolve_gen_ratio(interval: str, ratio: dict = None) -> dict:
    """
    Looks up ratio['GEN.NS'][interval], the ONLY entry your real
    run_strategy_for_ticker actually reads today (see module docstring).
    Falls back to DEFAULT_RATIO if the interval is missing.
    """
    ratio = ratio or DEFAULT_RATIO
    gen = ratio.get("GEN.NS", {})
    if interval in gen:
        return gen[interval]
    return DEFAULT_RATIO["GEN.NS"][interval]
