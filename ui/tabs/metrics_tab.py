import math

import streamlit as st
import plotly.graph_objects as go

from charting import filter_zones, filter_trade_log, _theme_layout, FONT_STACK
from filter_state import get_active_filters
from zone_identification_multibase import recompute_metrics_for_subset
from ui.style import PALETTE, section_header, stat_cards


def _safe_num(x, default=0.0):
    """
    Returns `default` for None OR NaN, otherwise x unchanged.

    Guards against the common `x or default` idiom silently doing the
    wrong thing: NaN is truthy in Python, so `float('nan') or 0` evaluates
    to NaN, not 0 - meaning a NaN metric (which can legitimately occur,
    e.g. Profit Factor when trades are too few/one-sided) would previously
    slip past that guard, then fail a numeric comparison (NaN compares
    False to everything) and get colored/labeled as if it were a real bad
    number rather than "no data". Doesn't fix any calculation - purely
    protects display logic below from mislabeling NaN as a normal value.
    """
    if x is None:
        return default
    if isinstance(x, float) and math.isnan(x):
        return default
    return x


def _composite_gauge(score) -> go.Figure:
    p = PALETTE
    score = _safe_num(score, 0)
    color = p["bear"] if score < 30 else (p["warn"] if score < 60 else p["bull"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"color": p["text"], "family": FONT_STACK, "size": 36}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": p["text_muted"]},
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": p["bear_soft"]},
                {"range": [30, 60], "color": p["warn_soft"]},
                {"range": [60, 100], "color": p["bull_soft"]},
            ],
        },
        title={"text": "Composite Score", "font": {"color": p["text_muted"], "family": FONT_STACK, "size": 13}},
    ))
    _theme_layout(fig, height=220, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def _equity_curve(trade_log) -> go.Figure:
    """
    Plots your backend's own Capital_After_Trade column, sorted by Exit
    Date - pure presentation of numbers your real run_risk_management_simulation
    already computed, no new calculation.
    """
    p = PALETTE
    ordered = trade_log.dropna(subset=["Exit Date"]).sort_values("Exit Date")
    fig = go.Figure(go.Scatter(
        x=ordered["Exit Date"], y=ordered["Capital_After_Trade"],
        mode="lines+markers", line=dict(color=p["brand"], width=2.5),
        marker=dict(size=5, color=p["brand"]),
        fill="tozeroy", fillcolor="rgba(79,140,255,0.10)",
    ))
    _theme_layout(
        fig,
        title=dict(text="Equity Curve (Capital After Trade)", font=dict(size=14, family=FONT_STACK, color=p["text"])),
        height=300, xaxis_title=None, yaxis_title="₹", margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def _render_metric_cards(m: dict, trade_log=None):
    left, right = st.columns([1, 2])
    with left:
        st.plotly_chart(_composite_gauge(m.get("Composite Score")), use_container_width=True, key="composite_gauge_chart")
    with right:
        pf = m.get("Profit Factor")
        is_pf_nan = isinstance(pf, float) and math.isnan(pf)
        pf_display = "∞" if pf in (None, float("inf")) else ("N/A" if is_pf_nan else f"{pf:.2f}")
        win_rate = _safe_num(m.get("Win Rate"), 0)
        expectancy = _safe_num(m.get("System Expectancy"), 0)
        stat_cards([
            {"label": "Win Rate", "value": f"{win_rate:.1f}%",
             "color": "bull" if win_rate >= 50 else "bear"},
            {"label": "Profit Factor", "value": pf_display,
             "color": "bull" if _safe_num(pf, 0) >= 1 else "bear"},
            {"label": "System Expectancy", "value": f"{expectancy:,.1f}",
             "color": "bull" if expectancy >= 0 else "bear"},
        ])
        stat_cards([
            {"label": "Total Trades", "value": m.get("Total Trades", 0), "color": "brand"},
            {"label": "Demand / Supply Zones", "value": f"{m.get('Demand Zones', 0)} / {m.get('Supply Zones', 0)}",
             "color": "accent"},
            {"label": "Net PNL", "value": f"₹{m.get('Net PNL', 0):,.0f}",
             "color": "bull" if m.get("Net PNL", 0) >= 0 else "bear"},
        ])

    if trade_log is not None and not trade_log.empty and "Exit Date" in trade_log.columns:
        st.plotly_chart(_equity_curve(trade_log), use_container_width=True, key="equity_curve_chart")

    with st.expander("Timing, fill-quality & scaled expectancy detail"):
        st.write(
            {
                "Winning Trades": m.get("Winning Trades"),
                "Avg PnL / Trade": m.get("Avg PnL"),
                "Expectancy Score (annualized)": m.get("Expectancy Score"),
                "Avg Days: Zone Creation -> Entry": m.get("Avg Time Creation_Entry"),
                "Avg Hold Time (Profitable, days)": m.get("Avg Hold Time (Profitable)"),
                "Avg Hold Time (Losing, days)": m.get("Avg Hold Time (Losing)"),
                "Avg Piercing %": m.get("Avg Piercing %"),
                "Profitable Demand Zones": m.get("Profitable Demand Zones"),
                "Profitable Supply Zones": m.get("Profitable Supply Zones"),
            }
        )

    import json
    st.download_button(
        "⬇ Download metrics as JSON", json.dumps(m, indent=2, default=str).encode("utf-8"),
        file_name="backtest_metrics.json", mime="application/json", key="download_metrics_json",
    )


def render(config: dict, results):
    if results is None:
        st.info("Run an analysis to see backtest metrics.")
        return
    if getattr(results, "error", None):
        st.info("No metrics to show - see the error above.")
        return

    m = results.metrics
    if not m:
        metrics_error = results.trade_log.attrs.get("metrics_error") if hasattr(results.trade_log, "attrs") else None
        if metrics_error:
            st.warning(f"Trades were taken but metrics couldn't be computed: {metrics_error}")
        else:
            st.warning("No resolved trades to compute metrics from.")
        return

    section_header("📈", "Backtest Metrics",
                    f"Analysis last computed: {results.analysis_timestamp}" if results.analysis_timestamp else "")

    use_filtered = st.toggle(
        "Compute metrics for currently filtered zones only (mirrors Chart Filters tab)",
        value=False, key="metrics_use_filtered",
    )

    if not use_filtered:
        _render_metric_cards(m, trade_log=results.trade_log)
        return

    # Mirror the exact same filter state the Charts tab set in session_state -
    # this is a re-slice + re-aggregate of the existing trade_log, not a
    # re-run of zone detection/backtest/scoring.
    zones_1d = results.zones.get("1d")
    if zones_1d is None or zones_1d.empty:
        st.info("No daily zone data available to filter against.")
        return

    active = get_active_filters(results)

    filtered_zones = filter_zones(
        zones_1d, min_base_count=active["min_base_count"], zone_types=active["zone_types"],
        pattern_types=active["pattern_types"], trade_score=results.trade_score,
        min_strength=active["min_strength"], fresh_only=active["fresh_only"],
        bool_filters=active["bool_filters"],
    )
    filtered_trade_log = filter_trade_log(results.trade_log, filtered_zones.index)

    active_bool_flags = [k for k, v in active["bool_filters"].items() if v]
    st.caption(
        f"Filters currently set on the Charts tab: Min Base Count \u2265 {active['min_base_count']}, "
        f"Zone Type in {list(active['zone_types'])}, Pattern in {list(active['pattern_types'])}"
        + (f", Min Strength \u2265 {active['min_strength']}" if active["min_strength"] is not None else "")
        + (", Fresh only" if active["fresh_only"] else "")
        + (f", flags: {active_bool_flags}" if active_bool_flags else "")
        + f" \u2192 {len(filtered_trade_log)} of {len(results.trade_log)} trades match."
    )

    if filtered_trade_log.empty:
        st.warning("No trades match the current chart filters.")
        return

    filtered_metrics = recompute_metrics_for_subset(filtered_trade_log)
    if "_error" in filtered_metrics:
        st.warning(f"Couldn't compute filtered metrics: {filtered_metrics['_error']}")
        return

    _render_metric_cards(filtered_metrics, trade_log=filtered_trade_log)
