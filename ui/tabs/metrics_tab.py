import streamlit as st
import plotly.graph_objects as go

from charting import filter_zones, filter_trade_log
from filter_state import get_active_filters
from zone_identification_multibase import recompute_metrics_for_subset


def _composite_gauge(score) -> go.Figure:
    score = score or 0
    color = "#d62728" if score < 30 else ("#ff7f0e" if score < 60 else "#2ca02c")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 30], "color": "rgba(214,39,40,0.15)"},
                {"range": [30, 60], "color": "rgba(255,127,14,0.15)"},
                {"range": [60, 100], "color": "rgba(44,160,44,0.15)"},
            ],
        },
        title={"text": "Composite Score"},
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def _equity_curve(trade_log) -> go.Figure:
    """
    Plots your backend's own Capital_After_Trade column, sorted by Exit
    Date - pure presentation of numbers your real run_risk_management_simulation
    already computed, no new calculation.
    """
    ordered = trade_log.dropna(subset=["Exit Date"]).sort_values("Exit Date")
    fig = go.Figure(go.Scatter(
        x=ordered["Exit Date"], y=ordered["Capital_After_Trade"],
        mode="lines+markers", line=dict(color="#1f77b4"),
    ))
    fig.update_layout(title="Equity Curve (Capital After Trade)", height=300,
                       xaxis_title=None, yaxis_title="₹", margin=dict(l=20, r=20, t=40, b=20))
    return fig


def _render_metric_cards(m: dict, trade_log=None):
    left, right = st.columns([1, 2])
    with left:
        st.plotly_chart(_composite_gauge(m.get("Composite Score")), use_container_width=True)
    with right:
        top = st.columns(3)
        top[0].metric("Win Rate", f"{m.get('Win Rate', 0):.1f}%")
        top[1].metric("Profit Factor", round(m.get("Profit Factor"), 2) if m.get("Profit Factor") not in (None, float("inf")) else "∞")
        top[2].metric("System Expectancy", round(m.get("System Expectancy", 0), 2))

        mid = st.columns(3)
        mid[0].metric("Total Trades", m.get("Total Trades"))
        mid[1].metric("Demand / Supply Zones", f"{m.get('Demand Zones', 0)} / {m.get('Supply Zones', 0)}")
        mid[2].metric("Net PNL", f"₹{m.get('Net PNL', 0):,.2f}")

    if trade_log is not None and not trade_log.empty and "Exit Date" in trade_log.columns:
        st.plotly_chart(_equity_curve(trade_log), use_container_width=True)

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

    st.subheader("Backtest Metrics")
    if results.analysis_timestamp:
        st.caption(f"Analysis last computed: {results.analysis_timestamp}")

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
