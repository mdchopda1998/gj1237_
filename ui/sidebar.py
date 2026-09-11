import streamlit as st
from datetime import date, timedelta

from ratio_config import default_ratio, resolve_gen_ratio, DAILY_PRESETS


def _render_ratio_controls(ratio: dict) -> dict:
    st.sidebar.subheader("🧮 Zone Detection Ratios")
    st.sidebar.caption(
        "Your real backend currently only reads ratio['GEN.NS'][interval] "
        "regardless of ticker - these controls edit that shared config."
    )

    preset_name = st.sidebar.selectbox(
        "Daily (1d) preset", options=["Custom"] + list(DAILY_PRESETS.keys()), index=1,
        help="One-click starting points (your original test_scenarios dict). "
             "Switch to Custom to fine-tune manually below.",
    )
    if preset_name != "Custom":
        ratio["GEN.NS"]["1d"] = {k: dict(v) for k, v in DAILY_PRESETS[preset_name].items()}

    with st.sidebar.expander("Advanced: edit TR/ATR & Body/TR thresholds", expanded=False):
        for tf, tf_label in [("1d", "Daily"), ("1wk", "Weekly"), ("1mo", "Monthly")]:
            st.markdown(f"**{tf_label}**")
            tf_ratio = resolve_gen_ratio(tf, ratio)
            cols = st.columns(3)
            for col, candle_type in zip(cols, ["Exciting", "Base", "Explosive"]):
                with col:
                    st.caption(candle_type)
                    tr_atr = st.slider(
                        f"TR/ATR ({candle_type[:3]}, {tf})", 0.1, 2.0,
                        float(tf_ratio[candle_type]["TR_ATR"]), 0.1,
                        key=f"tr_atr_{tf}_{candle_type}",
                    )
                    bs_tr = st.slider(
                        f"Body/TR ({candle_type[:3]}, {tf})", 0.1, 1.0,
                        float(tf_ratio[candle_type]["BS_TR"]), 0.05,
                        key=f"bs_tr_{tf}_{candle_type}",
                    )
                    ratio["GEN.NS"].setdefault(tf, {})[candle_type] = {"TR_ATR": tr_atr, "BS_TR": bs_tr}
    return ratio


def render_sidebar() -> dict:
    st.sidebar.header("⚙️ Configuration")

    ticker = st.sidebar.text_input("Ticker", value="SAIL.NS", help="NSE symbol, e.g. SAIL.NS, RELIANCE.NS")

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(date.today() - timedelta(days=365 * 3), date.today()),
    )
    start_date, end_date = (date_range if len(date_range) == 2 else (None, None))

    risk_pct = st.sidebar.slider(
        "Risk per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1,
        help="Fraction of capital risked per trade, passed to your backend as e.g. 0.01 for 1%.",
    ) / 100.0

    initial_capital = st.sidebar.number_input(
        "Initial Capital (₹)", min_value=10_000, value=500_000, step=10_000
    )

    st.sidebar.divider()

    with st.sidebar.expander("📁 Data source", expanded=False):
        data_dir = st.text_input(
            "Local CSV folder", value="data",
            help="Checked first, per ticker/interval (e.g. data/SAIL_NS_1d.csv). "
                 "Falls back to a live yfinance fetch if a file isn't found there "
                 "(also used to fetch the ^NSEI Nifty benchmark).",
        )

    ratio = _render_ratio_controls(default_ratio())

    st.sidebar.divider()
    if st.sidebar.button("↺ Reset all filters", use_container_width=True,
                          help="Clears chart/table filter selections (Base Count, Zone Type, Strength, etc). "
                               "Does not re-run analysis or change these sidebar settings."):
        for key in list(st.session_state.keys()):
            if key.startswith(("min_base_count", "zone_types", "pattern_types", "trim_at_breach", "use_strength", "min_strength",
                                "fresh_only", "metrics_use_filtered", "outcome_filter_", "zonetype_filter_",
                                "ts_bool_")):
                del st.session_state[key]
        st.rerun()

    with st.sidebar.expander("ℹ️ About this app", expanded=False):
        st.caption(
            "SMC (Smart Money Concepts) demand/supply zone scanner and backtester "
            "for NSE equities. Zone detection, backtesting, and scoring run your "
            "real backend logic unchanged - this UI only adds filtering, charting, "
            "and presentation on top."
        )

    return {
        "ticker": ticker.strip().upper() if ticker else "",
        "start_date": start_date,
        "end_date": end_date,
        "risk_pct": risk_pct,
        "initial_capital": initial_capital,
        "data_dir": data_dir,
        "ratio": ratio,
    }
