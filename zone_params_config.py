"""
Zone-detection / scoring "hard constants" config.

Every value in DEFAULT_ZONE_PARAMS below was previously a hard-coded
literal buried inside smc_backend.py (identity_zones_with_multibase and
the helper functions it calls: calculate_atr, compute_gap_flags,
compute_volume_zscore, compute_choppiness_index, detect_swing_points,
compute_bos_flags_n_liquidity_sweep, detect_order_blocks, and the
weekly-trend window used inside calculate_trade_score). The values here
are copied verbatim from those call sites, so behavior is unchanged
until someone actually moves a control in the Strategy Parameters panel.

PARAM_META drives the right-side control panel (ui/right_panel.py):
one row per constant, with a human-meaningful label, help text, and
widget bounds, so the panel and this default set can never drift apart.
"""
import copy

DEFAULT_ZONE_PARAMS = {
    "atr_period": 14,
    "gap_threshold": 0.5,
    "vol_zscore_lookback": 22,
    "vol_zscore_threshold": 1.5,
    "choppiness_period": 22,
    "choppiness_threshold": 38.2,
    "swing_lookback": 5,
    "structure_swing_lookback": 22,
    "sweep_wick_ratio": 3.0,
    "max_base_candles": 10,
    "require_bos_for_order_block": False,
    "weekly_trend_window": 52,
    "wick2wick": False,
    "distal_pct_from_zone": 0.0
}

# (key, label, help, min, max, step, kind)
# kind: "slider_float" | "slider_int" | "number_int" | "checkbox"
PARAM_META = [
    (
        "atr_period", "ATR Period",
        "Bars used for the Average True Range (EMA span). Drives candle "
        "classification (Exciting/Base/Explosive), gap sizing, and every "
        "TR/ATR ratio downstream.",
        2, 100, 1, "slider_int",
    ),
    (
        "gap_threshold", "Gap Threshold (x ATR)",
        "An opening gap vs. the prior close is flagged 'Gapped' once it "
        "exceeds this multiple of ATR.",
        0.1, 5.0, 0.1, "slider_float",
    ),
    (
        "vol_zscore_lookback", "Volume Z-Score Lookback",
        "Rolling window (bars) used for the volume mean/std when computing "
        "the volume z-score.",
        5, 120, 1, "slider_int",
    ),
    (
        "vol_zscore_threshold", "Volume Z-Score Threshold",
        "A bar is flagged 'High Volume' once its volume z-score exceeds "
        "this value.",
        0.5, 5.0, 0.1, "slider_float",
    ),
    (
        "choppiness_period", "Choppiness Index Period",
        "Bars used for the Choppiness Index (high/low span and TR sum).",
        5, 100, 1, "slider_int",
    ),
    (
        "choppiness_threshold", "Choppiness Trending Threshold",
        "A bar is flagged 'Trending' when the Choppiness Index is below "
        "this value (lower = trending, higher = choppy/sideways).",
        0.0, 100.0, 0.1, "slider_float",
    ),
    (
        "swing_lookback", "Swing Point Lookback",
        "Bars on each side of a candle required for it to register as a "
        "fractal Swing High/Low.",
        1, 30, 1, "slider_int",
    ),
    (
        "structure_swing_lookback", "Structure (BOS) Swing Lookback",
        "Lookback passed to the confirmed-swing-level logic used for Break "
        "of Structure (BOS) and Liquidity Sweep detection.",
        1, 60, 1, "slider_int",
    ),
    (
        "sweep_wick_ratio", "Sweep Wick Ratio",
        "A wick beyond a swing level counts as a Liquidity Sweep only once "
        "the wick is at least this fraction of the candle's full range.",
        0.1, 5.0, 0.1, "slider_float",
    ),
    (
        "distal_pct_from_zone", "Distal Percentage from Zone",
        "The percentage by which the distal level should be from the zone.",
        0.0, 2.0, 0.1, "slider_float",
    ),
    (
        "max_base_candles", "Max Base Candles",
        "Longest run of consecutive 'Base' candles allowed between the "
        "leg-in and leg-out candles of a zone.",
        1, 30, 1, "slider_int",
    ),
    (
        "require_bos_for_order_block", "Require BOS for Order Block",
        "Off (default): an Order Block only needs an opposite-colored "
        "candle followed by an Explosive move. On: it also requires a "
        "confirmed Break of Structure.",
        None, None, None, "checkbox",
    ),
    (
            "wick2wick", " Wick-to-Wick Marking",
            "Off (default): It will mark body to wick. On: It will mark wick to wick. "
            "This is useful for identifying order blocks that are formed by a"
            " wick to wick move, which is often the case in volatile markets.",
            None, None, None, "checkbox",
    ),
    (
        "weekly_trend_window", "Weekly Trend Window",
        "Bars used for the weekly market-trend/regime classification that "
        "feeds Trend Support and ITF Support scoring.",
        10, 200, 1, "slider_int",
    ),
]


def default_zone_params() -> dict:
    """A fresh copy - callers can mutate freely without touching DEFAULT_ZONE_PARAMS."""
    return copy.deepcopy(DEFAULT_ZONE_PARAMS)
