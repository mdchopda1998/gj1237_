import streamlit as st
import plotly.graph_objects as go

from score_analysis import merge_trade_log_with_score, numeric_breakdown, boolean_flag_summary
from filter_state import trade_score_bool_columns
from charting import _theme_layout, FONT_STACK
from ui.style import PALETTE, section_header


def _breakdown_chart(breakdown, column_label: str) -> go.Figure:
    p = PALETTE
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=breakdown[breakdown.columns[0]].astype(str), y=breakdown["Win Rate"],
        name="Win Rate (%)", marker_color=p["brand"], yaxis="y1", opacity=0.85,
        text=breakdown["Trades"].apply(lambda n: f"n={n}"), textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=breakdown[breakdown.columns[0]].astype(str), y=breakdown["Avg PnL"],
        name="Avg PnL (₹)", mode="lines+markers", line=dict(color=p["accent"], width=2.5),
        marker=dict(size=7, color=p["accent"]), yaxis="y2",
    ))
    _theme_layout(
        fig,
        title=dict(text=f"Win Rate & Avg PnL by {column_label}", font=dict(size=14, family=FONT_STACK, color=p["text"])),
        xaxis_title=column_label,
        yaxis=dict(title="Win Rate (%)", side="left"),
        yaxis2=dict(title="Avg PnL (₹)", overlaying="y", side="right", gridcolor="rgba(0,0,0,0)"),
        height=380, legend=dict(orientation="h", y=1.15),
    )
    return fig


def _tornado_chart(summary) -> go.Figure:
    p = PALETTE
    ordered = summary.dropna(subset=["Win Rate Delta"]).sort_values("Win Rate Delta")
    colors = [p["bull"] if d >= 0 else p["bear"] for d in ordered["Win Rate Delta"]]
    fig = go.Figure(go.Bar(
        x=ordered["Win Rate Delta"], y=ordered["Flag"], orientation="h",
        marker_color=colors,
        text=[f"{d:+.1f} pts" for d in ordered["Win Rate Delta"]], textposition="outside",
    ))
    _theme_layout(
        fig,
        title=dict(text="Win Rate Delta: flag = True vs flag = False", font=dict(size=14, family=FONT_STACK, color=p["text"])),
        xaxis_title="Win Rate difference (percentage points)",
        height=max(320, 28 * len(ordered)), margin=dict(l=140, t=45),
    )
    return fig


def render(config: dict, results):
    if results is None:
        st.info("Run an analysis to see how metrics vary with trade score.")
        return
    if getattr(results, "error", None):
        st.info("No data to analyze - see the error above.")
        return
    if results.trade_log is None or results.trade_log.empty:
        st.warning("No resolved trades to analyze.")
        return
    if results.trade_score is None or results.trade_score.empty:
        st.warning(
            "No trade-score data available (your real calculate_trade_score output is "
            "daily-only, and this run may not have produced any daily zones/trades)."
        )
        return

    section_header(
        "📐", "How Metrics Vary With Trade Score",
        "Re-aggregates your already-computed trade_log joined with trade_score (df_ts) - "
        "Strength, Base Count, and every boolean score flag (Gapped, BOS, OB, Sweep, HTF "
        "Support, etc.) - to show which factors actually correlate with Win Rate and PnL. "
        "No re-analysis.",
    )

    merged = merge_trade_log_with_score(results.trade_log, results.trade_score)
    if merged.empty or "Outcome" not in merged.columns:
        st.warning("Couldn't merge trade log with trade score - no overlapping data.")
        return

    st.markdown("##### Numeric factors")
    n1, n2 = st.columns(2)
    with n1:
        strength_breakdown = numeric_breakdown(merged, "Strength")
        if not strength_breakdown.empty:
            st.plotly_chart(_breakdown_chart(strength_breakdown, "Strength"), use_container_width=True, key="strength_breakdown_chart")
        else:
            st.caption("No Strength data to show.")
    with n2:
        basecount_breakdown = numeric_breakdown(merged, "Base Count")
        if not basecount_breakdown.empty:
            st.plotly_chart(_breakdown_chart(basecount_breakdown, "Base Count"), use_container_width=True, key="basecount_breakdown_chart")
        else:
            st.caption("No Base Count data to show.")

    st.markdown("##### Boolean score flags")
    st.caption(
        "Every flag your backend's calculate_trade_score produces, ranked by how much "
        "difference it makes to Win Rate when True vs False. Small sample sizes (low N) "
        "can produce large-looking deltas that aren't reliable - check N before trusting a flag."
    )
    bool_cols = trade_score_bool_columns(results.trade_score)
    summary = boolean_flag_summary(merged, bool_cols)

    if summary.empty:
        st.caption("Not enough data to compare flags.")
    else:
        st.plotly_chart(_tornado_chart(summary), use_container_width=True, key="tornado_chart")

        with st.expander("Full comparison table", expanded=False):
            column_config = {
                "Win Rate (True)": st.column_config.NumberColumn(format="%.1f%%"),
                "Win Rate (False)": st.column_config.NumberColumn(format="%.1f%%"),
                "Avg PnL (True)": st.column_config.NumberColumn(format="₹%.2f"),
                "Avg PnL (False)": st.column_config.NumberColumn(format="₹%.2f"),
                "Win Rate Delta": st.column_config.NumberColumn(format="%.1f pts"),
            }
            st.dataframe(summary, use_container_width=True, hide_index=True, column_config=column_config)
            st.download_button(
                "⬇ Download flag comparison as CSV",
                summary.to_csv(index=False).encode("utf-8"),
                file_name=f"{config.get('ticker', 'score')}_flag_comparison.csv",
                mime="text/csv", key="download_flag_comparison",
            )
