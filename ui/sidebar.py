import streamlit as st
from datetime import date

from ratio_config import default_ratio, resolve_gen_ratio, DAILY_PRESETS
from index_constituents import search_universe


def _apply_preset_to_session_state(preset_name: str):
    """
    Pushes a named daily preset's values into the slider session_state
    keys BEFORE those sliders are instantiated below. This matters because
    Streamlit widgets ignore their `value=` argument once session_state
    already holds that key - so without this, switching the preset
    dropdown would change `ratio` internally but the sliders would keep
    showing whatever was there before, which is the bug being fixed here.
    """
    preset = DAILY_PRESETS[preset_name]
    for candle_type, vals in preset.items():
        st.session_state[f"tr_atr_1d_{candle_type}"] = float(vals["TR_ATR"])
        st.session_state[f"bs_tr_1d_{candle_type}"] = float(vals["BS_TR"])


def _mark_custom():
    """
    on_change callback for the Daily sliders: the moment you edit one by
    hand, the preset label no longer describes what's actually configured,
    so the dropdown switches itself to Custom. Streamlit already commits
    the slider's new value to session_state before this callback runs, so
    your edit is what's used either way - this only fixes the *label*.
    """
    st.session_state["ratio_preset_select"] = "Custom"


def _render_ratio_controls(ratio: dict) -> dict:
    st.sidebar.markdown("##### 🧮 Zone Detection Ratios")
    st.sidebar.caption(
        "Your real backend currently only reads ratio['GEN.NS'][interval] "
        "regardless of ticker - these controls edit that shared config."
    )

    preset_options = ["Custom"] + list(DAILY_PRESETS.keys())
    preset_kwargs = {} if "ratio_preset_select" in st.session_state else {"index": 1}
    preset_name = st.sidebar.selectbox(
        "Daily (1d) preset", options=preset_options,
        key="ratio_preset_select", **preset_kwargs,
        help="Selecting a preset fills in the Daily sliders below with its exact "
             "values. Editing any slider afterwards switches this back to Custom "
             "automatically - whatever the sliders show is always what's actually "
             "used, regardless of which label is selected.",
    )

    # Only push preset values into slider state on a genuine change (not
    # every rerun) - otherwise user edits would get silently overwritten
    # back to the preset on the very next interaction.
    if preset_name != "Custom" and st.session_state.get("_last_ratio_preset") != preset_name:
        _apply_preset_to_session_state(preset_name)
    st.session_state["_last_ratio_preset"] = preset_name

    if preset_name != "Custom":
        ratio["GEN.NS"]["1d"] = {k: dict(v) for k, v in DAILY_PRESETS[preset_name].items()}

    with st.sidebar.expander("Advanced: edit TR/ATR & Body/TR thresholds", expanded=False):
        st.caption(
            f"Showing **{preset_name}** values below."
            if preset_name != "Custom" else
            "Showing **Custom** values below (edited from whichever preset was last selected)."
        )
        for tf, tf_label in [("1d", "Daily"), ("1wk", "Weekly"), ("1mo", "Monthly")]:
            st.markdown(f"**{tf_label}**")
            tf_ratio = resolve_gen_ratio(tf, ratio)
            cols = st.columns(3)
            for col, candle_type in zip(cols, ["Exciting", "Base", "Explosive"]):
                with col:
                    st.caption(candle_type)
                    # Presets only cover the daily timeframe, so only Daily
                    # sliders need to flip the dropdown back to Custom.
                    on_change = _mark_custom if tf == "1d" else None

                    tr_key = f"tr_atr_{tf}_{candle_type}"
                    tr_kwargs = {} if tr_key in st.session_state else \
                        {"value": float(tf_ratio[candle_type]["TR_ATR"])}
                    tr_atr = st.slider(
                        f"TR/ATR ({candle_type[:3]}, {tf})", min_value=0.1, max_value=2.0, step=0.1,
                        key=tr_key, on_change=on_change, **tr_kwargs,
                    )

                    bs_key = f"bs_tr_{tf}_{candle_type}"
                    bs_kwargs = {} if bs_key in st.session_state else \
                        {"value": float(tf_ratio[candle_type]["BS_TR"])}
                    bs_tr = st.slider(
                        f"Body/TR ({candle_type[:3]}, {tf})", min_value=0.1, max_value=1.0, step=0.05,
                        key=bs_key, on_change=on_change, **bs_kwargs,
                    )
                    ratio["GEN.NS"].setdefault(tf, {})[candle_type] = {"TR_ATR": tr_atr, "BS_TR": bs_tr}
    return ratio


def _render_ticker_picker() -> str:
    """
    Two ways to pick a stock: search by company name (covers NIFTY 50 +
    Next 50 - about 99 well-known names, so most people never need to
    know the exact NSE symbol), or type a ticker directly for anything
    else (e.g. SAIL.NS, or any symbol outside that universe). Streamlit's
    selectbox already supports type-to-filter, so "search by name" is a
    real search, not just a long dropdown to scroll through.
    """
    mode = st.sidebar.radio(
        "Find stock by", ["Search company name", "Type ticker directly"],
        horizontal=True, key="ticker_input_mode",
    )

    if mode == "Search company name":
        universe = search_universe()  # [(ticker, "Company Name (TICKER.NS)"), ...]
        tickers = [t for t, _label in universe]
        label_map = dict(universe)
        default_ticker = "RELIANCE.NS" if "RELIANCE.NS" in tickers else tickers[0]
        default_index = tickers.index(default_ticker)
        selected = st.sidebar.selectbox(
            "Company", options=tickers, index=default_index,
            format_func=lambda t: label_map.get(t, t),
            help="Covers NIFTY 50 + NIFTY Next 50 (~99 companies) - start typing "
                 "a company name to filter. For anything outside that list (e.g. "
                 "SAIL.NS), switch to 'Type ticker directly'.",
        )
        return selected

    return st.sidebar.text_input(
        "Ticker", value="SAIL.NS",
        help="Any NSE symbol in Yahoo Finance format, e.g. SAIL.NS, RELIANCE.NS.",
    )


def render_sidebar() -> dict:
    st.sidebar.markdown(
        """
        <div style="display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0 1rem 0;">
            <span style="font-size:1.4rem;">📈</span>
            <span style="font-size:1.05rem;font-weight:800;letter-spacing:-0.01em;">SMC Scanner</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("##### ⚙️ Configuration")

    ticker = _render_ticker_picker()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(date(2021, 1, 1), date.today()),
        help="Defaults to 2021-01-01 through today.",
    )
    start_date, end_date = (date_range if len(date_range) == 2 else (None, None))

    risk_pct = st.sidebar.slider(
        "Risk per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1,
        help="Fraction of capital risked per trade, passed to your backend as e.g. 0.01 for 1%.",
    ) / 100.0

    initial_capital = st.sidebar.number_input(
        "Initial Capital (₹)", min_value=10_000, value=100_000, step=10_000
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
                                "ts_bool_", "outcome_types", "tradelog_use_chart_filters")):
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
