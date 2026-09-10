# SMC Scanner & Backtester (Streamlit)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Status: real backend is now wired in

This is no longer a placeholder. `smc_backend.py` is your actual
`my_backend.py`, library portion only (every function verbatim - see the
docstring at the top of that file for the exact, minimal edits made:
optional-import guards, nothing behavioral). Zone detection, backtesting,
and metrics all run your real code:

```
data_loading.py                 CSV-first / live yfinance / synthetic-fallback OHLC
        |
ratio_config.py                  your real ratio defaults + presets
        |
zone_identification_multibase.py  ANALYSIS adapter: zone detection, backtest, scoring
        |                          (cached - only reruns on "Run Analysis")
smc_backend.py                    your real identity_zones_with_multibase,
                                    run_strategy_for_ticker, evaluate_strategy_metrics,
                                    calculate_composite_score
        |
charting.py                       PLOTTING only - filters + draws figures
        |                          (cheap - reruns on every filter widget change,
        |                           does NOT touch cached analysis)
ui/tabs/*.py                     render zones / metrics / trade log
```

### Analysis vs. plotting are now separate

`zone_identification_multibase.py` (cached via `@st.cache_data` in
`data_access.py`) only produces data: `zones` (per timeframe, with `Base
Count`, `Is Demand`, `Proximal`/`Distal`/`Target`), `trade_score` (your
`df_ts` / `out['anal']['ts']` - `Strength`, `Freshness`, `BOS`, `OB`,
`Sweep`, HTF-support flags; **daily timeframe only**, since that's the
only one your `calculate_trade_score` scores), and `trade_log` (`df_rm`).
It builds no figures.

`charting.py` is pure plotting: `filter_zones()` narrows a zone dataframe
by Base Count / Demand-Supply / Strength / Freshness, and
`build_zone_figure()` draws the candlestick + shaded rectangles for
whatever subset you pass it. The Charts tab calls both at render time, so
adjusting a filter slider (min Base Count, min Strength, Fresh-only,
Zone Type) only re-runs cheap plotting code - it never re-triggers zone
detection, the backtest, or scoring. Metrics and Trade Log tabs are **not** affected by chart filters by
default - they show the full backtest. The Metrics tab has an explicit
**"Compute metrics for currently filtered zones only"** checkbox that
mirrors whatever's set on the Charts tab (same Base Count / Zone Type /
Strength / Freshness) and re-slices + re-aggregates the existing
`trade_log` - still no re-analysis, since `evaluate_strategy_metrics` is
pure pandas aggregation over however many rows you hand it.

### Making the split visible in the UI

The Charts tab's filter controls sit inside a bordered container labeled
**"🔍 Chart Filters — instant, does *not* re-run analysis"**, with a
caption pointing at the analysis timestamp shown just above it. That
timestamp (`results.analysis_timestamp`, set once per "Run Analysis"
click) is also shown on the Metrics tab, so it's visible at a glance that
moving a filter slider doesn't change when the underlying analysis ran.
### Two things worth knowing about your real code, found while integrating

1. **`run_strategy_for_ticker` ignores the `ticker` argument for ratio
   lookup.** It calls `identity_zones_with_multibase(data[ticker][interval],
   ratio['GEN.NS'][interval])` unconditionally - so even though your `ratio`
   dict has room for ticker-specific entries (e.g. `'ORG.NS'`), only
   `ratio['GEN.NS']` ever has any effect today. The sidebar's ratio controls
   edit `ratio['GEN.NS']` accordingly - see `ratio_config.py`'s docstring.
   If you want per-ticker ratios to actually take effect, that lookup line
   in `smc_backend.py` would need to change to something like
   `ratio.get(ticker, ratio['GEN.NS'])[interval]`.

2. **`run_risk_management_simulation()` drops `'Outcome'` and
   `'Date Created'`**, columns `evaluate_strategy_metrics()` requires, even
   though they exist one step earlier in `backtest_zones()`'s output
   (`df_bt`) and share the same index. Confirmed empirically: `df_bt` and
   `df_rm` share the same `DatetimeIndex` (zone creation date), and `df_rm`
   is just a row-subset of `df_bt`. The adapter
   (`zone_identification_multibase.py`, see the "BRIDGE FIX" comment)
   rejoins those two columns from `df_bt` onto `df_rm` by index before
   calling `evaluate_strategy_metrics()`, rather than editing your real
   function. Worth fixing at the source eventually so any other caller of
   `run_risk_management_simulation()` doesn't hit the same gap.

### Nifty (^NSEI) benchmark

Computed the same way your driver script did it: OHLC loaded via the same
CSV-first/live-fallback path as the main ticker, then
`identity_zones_with_multibase(nifty_ohlc, ratio['GEN.NS'][interval])` per
timeframe, fed into `calculate_trade_score`'s HTF-support checks.

### Data loading (CSV-first, live fallback, synthetic last resort)

For each of the three timeframes (1d/1wk/1mo), and for both the main
ticker and `^NSEI`, `data_loading.py` resolves data in this order:

1. **Saved CSV** at `<data folder>/<TICKER_with_.->_>_<interval>.csv`
   (e.g. `data/SAIL_NS_1d.csv`) - matches your `load_data()` naming.
2. **Live yfinance fetch** if no CSV is found.
3. **Synthetic placeholder** only if both fail (no network, bad ticker,
   delisted index symbol, etc.) - so the app never crashes; a caption
   under each chart says which source was actually used.

Set the folder in the sidebar's "Data source" expander (defaults to
`data/`).

### Ratio config & sidebar

`ratio_config.py` ships your real `ratio` dict defaults (`'GEN.NS'` /
`'ORG.NS'`) and your `test_scenarios` as four one-click daily presets
(`Standard`, `Aggressive_Explosive`, `Tight_Base`, plus `SAIL_Backtested` -
the ratio we grid-searched and validated on `SAIL_NS_1d.csv` earlier in
this project). An "Advanced" expander exposes raw TR/ATR and Body/TR
sliders per candle type per timeframe.

### Known rough edges to expect

- Your backend's SMC enrichments (BOS, order blocks, volume z-score,
  choppiness, swing points) all run on every request - this can be slow on
  first load per ticker/date-range combo. `@st.cache_data` means repeat
  runs with identical inputs are instant.
- If a request errors (e.g. an edge case in one of the enrichment
  functions on unusual data), the adapter catches it and surfaces
  `results.error` as a banner instead of crashing the app - check that
  banner first if a run looks empty.
- Charts are built by our own lightweight Plotly function, not your
  `plot_stock_zones`/`plot_stock_zones_monthly` (those call `fig.show()`
  internally instead of returning `fig`, so they can't be embedded in
  Streamlit without a small edit on your end).

## Structure

```
app.py                              entry point: page config, sidebar, tab router, error banner
state.py                             session_state key helpers
data_loading.py                      CSV-first, yfinance-fallback OHLC loading (cached)
ratio_config.py                      your real ratio defaults + presets + GEN.NS resolution
data_access.py                       cached wrapper around the adapter
zone_identification_multibase.py     ANALYSIS adapter: data prep, Nifty benchmark, bridge fix, error handling (no plotting)
smc_backend.py                       your real backend logic (library-only extract)
charting.py                          PLOTTING only: filter_zones() + build_zone_figure(), no analysis
ui/sidebar.py                        sidebar inputs incl. ratio controls -> config dict
ui/tabs/charts_tab.py                filter widgets + per-timeframe charts (calls charting.py at render time)
ui/tabs/metrics_tab.py                KPI cards from evaluate_strategy_metrics + composite score
ui/tabs/trade_log_tab.py              filterable trade-by-trade dataframe
```

### Debugging aids added after a real bug hunt

If filters (or anything else) seem to silently not appear, check two things
first:

1. **The build caption under the title** (`Build: 2026-09-09-chart-filters-v1 · Streamlit X.X.X`).
   If this doesn't match what you expect, you're running stale files -
   delete your old extracted folder entirely and re-unzip, rather than
   copying individual files over it.
2. **The "Debug: results loaded = ..." caption** just above the tabs -
   confirms whether `Run Analysis` actually populated results, and shows
   `results.error` inline if the backend raised.

These two lines are exactly how a real bug got caught while verifying this
feature: `trade_log_tab.py` was crashing on *every single rerun* (including
when moving a filter slider) with `TypeError: '<' not supported between
instances of 'float' and 'str'` - your real `Zone_Type` column had `NaN`
mixed with strings, and `sorted()` can't compare the two. Since Streamlit
reruns the entire script - all three tabs' code, not just the visible one -
on every widget interaction, this exception fired constantly, which is
consistent with filters appearing to not work at all. Fixed by filling
`NaN` as `"Unknown"` before building filter options. Caught via
`streamlit.testing.v1.AppTest`, which runs the real script and inspects
the resulting element tree without a browser - confirmed zero exceptions
and all filter widgets present after clicking Run Analysis and moving the
Min Base Count slider.

## UI refresh (backend logic untouched)

Everything below is presentation-layer only - `smc_backend.py` was not
touched, and no analysis behavior changed.

- **Staged progress**: `Run Analysis` now shows a live `st.status()` log
  (loading ticker OHLC → loading Nifty benchmark → running your backend →
  done), instead of a plain spinner. The first two stages are the same
  `@st.cache_data`-wrapped calls the adapter makes internally, so they're
  real steps, not cosmetic text - instant on repeat runs, real work on
  first run.
- **Toasts**: a small success/failure notification (`st.toast`) fires when
  analysis finishes.
- **`st.pills`** replace plain multiselects for Zone Type / Outcome
  filters (falls back to `st.multiselect` automatically on older
  Streamlit without `st.pills`).
- **`st.toggle`** replaces checkboxes for Strength/Freshness/filtered-metrics
  switches.
- **Zone chart annotations**: each shaded zone rectangle is now labeled
  with its Base Count (and Strength, daily only) directly on the chart.
- **Volume subplot** under each price chart.
- **Zone data table**: an expander under each timeframe chart showing the
  currently filtered zones as a formatted, downloadable table (₹-formatted
  price columns, CSV export).
- **Equity curve**: Metrics tab now plots your backend's own
  `Capital_After_Trade` column over `Exit Date` - a straight plot of
  numbers your `run_risk_management_simulation` already computes, no new
  calculation.
- **Composite Score gauge**: a color-coded (red/orange/green) Plotly
  indicator instead of a plain number.
- **Downloads everywhere**: metrics as JSON, zones as CSV (per timeframe),
  trade log as CSV.
- **Trade Log quick stats**: Trades shown / Net PNL / Win Rate for
  whatever's currently filtered, computed directly from the visible rows
  (not a call into your backend).
- **Sidebar polish**: icons, dividers, an About expander, and a
  **"↺ Reset all filters"** button that clears filter-related session
  state (Base Count, Zone Type, Strength, etc.) without touching your
  sidebar settings or re-running analysis.

All of the above was verified with `streamlit.testing.v1.AppTest` -
clicking Run Analysis, moving the Min Base Count slider, toggling the
filtered-metrics switch, and clicking Reset all filters, checking for zero
exceptions at each step (this caught and fixed one real bug during
development: `zones_display_table` hit a "'Date' is both an index level
and a column label" error from a `Date`-named index colliding with a
`Date` column - fixed with an explicit `reset_index(drop=True)`).
