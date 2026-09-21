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

## Fixes and additions after real-world testing

### Fixed: crash on Streamlit Cloud (`ProgressColumn` + `NaN`)

`st.column_config.ProgressColumn` requires every cell to be a bounded
numeric value - it can't render `NaN`. Your real `Piercing_Depth` column
is `NaN` for any trade whose target/stop was never actually hit (confirmed:
26 of 37 trades on a 5-year SAIL.NS run), which is normal, valid data, not
a bug. `ProgressColumn` choked on that and Streamlit's column-config JSON
serializer surfaced it as `StreamlitAPIException: ... Out of range float
values are not JSON compliant: nan`. Fixed by switching that column to a
plain `NumberColumn` (handles `NaN` as a blank cell, which is the correct
representation for "not applicable").

### Added: every trade-score column is now a chart filter

`filter_state.py` is new: it inspects `results.trade_score` (your real
`df_ts` / `calculate_trade_score` output) and auto-generates a toggle
filter for every boolean column that isn't already covered by a dedicated
control - currently `Gapped`, `Trending`, `High Volume`, `Swing Point`,
`BOS`, `OB`, `Sweep`, `Trend Support`, `ITF Support`, `HTF Support`,
`N_LTF Support`, `N_ITF Support`, `N_HTF Support`. This is fully dynamic:
if your backend's `calculate_trade_score` ever adds another `True`/`False`
column, a filter for it shows up automatically, no UI changes needed.

Also added a **Pattern (Continuous/Reversal)** filter next to Zone Type -
this one reads `Is Continuous` directly off the zone dataframe (not
`trade_score`), so unlike the other new filters it works on all three
timeframes, not just daily.

`filter_state.get_active_filters()` is the single source of truth for
"what's currently selected" - both the Charts tab (which owns the widgets)
and the Metrics tab's "filtered zones only" toggle read from it, so they
can't drift out of sync with each other.

The zone data table (under each timeframe's chart) now also shows every
available trade-score column for that zone, not just Strength/Freshness.

Verified with `streamlit.testing.v1.AppTest` end-to-end: ran with the
default 3-year date range (which does include `NaN` `Piercing_Depth`
trades) - zero exceptions. Toggled the new `OB` filter (10 \u2192 6 daily
zones), combined with Pattern=Reversal (\u2192 3 daily zones), then
confirmed the Metrics tab's filtered toggle reproduces the exact same
"3 of 10 trades match" - filters and metrics agree.

## Batch Analysis (new tab)

A 4th tab, **🗂️ Batch Analysis**, runs the identical per-ticker pipeline
(`zone_identification_multibase.run_strategy_for_ticker`, same as the
single-ticker tabs, via the same cached `data_access.get_strategy_results`)
once per selected ticker, using whatever's currently set in the sidebar
(date range, risk %, capital, ratio config). No backend logic changed -
this is the same call, looped, with results combined into one table with
**Ticker as a column**.

### Ticker sources
- **NIFTY 50 / NIFTY Next 50 / NIFTY 100** - built-in presets from
  `index_constituents.py`, static snapshots (dated Dec 2025 / Apr 2026).
  NSE rebalances these semi-annually, so they'll drift - the tab shows the
  "as of" date, and there's a note pointing at niftyindices.com for
  verification. Two symbols were deliberately left out rather than
  guessed (see the file's comments) - add them yourself once confirmed.
- **Custom list** - comma or newline separated tickers, typed directly.
- **Upload CSV** - any CSV with tickers in its first column.

### What you get back
One row per ticker: Status (OK / No Trades / Error), Composite Score, Win
Rate, Profit Factor, System Expectancy, Total Trades, Net PNL, Demand/Supply
Zone counts. Sortable by any of those, filterable by minimum Composite
Score, downloadable as CSV. Tickers that errored get their own expander
with the actual exception message - a bad ticker never aborts the whole
batch (each one is wrapped individually, on top of the adapter's existing
CSV/live/synthetic fallback, which already means most "bad" tickers
resolve to "No Trades" rather than a hard error).

### Drilling into a single ticker
Since batch mode already computed the *full* `StrategyResults` (zones,
trade_score, trade_log, not just the summary metrics) for every successful
ticker, "Load into single-ticker tabs" just points the Charts/Metrics/Trade
Log tabs at an already-computed result - no re-run, no extra backend call.

### Performance note
Batch mode calls the same cached function per ticker, so re-running a
batch with overlapping tickers/settings is instant for anything already
seen. The Nifty (^NSEI) benchmark computation - previously recomputed on
every single call - is now cached on `(start_date, end_date, data_dir,
ratio)` in the adapter, so a 50-ticker batch computes it once, not fifty
times (measured: ~1.0s first call \u2192 ~0.002s on repeat). Large batches
using live yfinance fetches (no local CSVs) can still take several
minutes; the tab warns above 25 tickers and suggests local CSVs.

Verified with `AppTest`: ran the actual NIFTY 50 preset (50 tickers, zero
exceptions), then a custom 3-ticker batch including one deliberately
invalid ticker (fell back to synthetic \u2192 "No Trades", not a crash),
tested sort/filter/download, and confirmed "Load into single-ticker tabs"
correctly switches the other tabs to the picked ticker's results.

## Zone plotting fixes + Score Analysis tab

### Fixed: zones now start at the first base candle, not the explosive candle

Your real `plot_stock_zones`/`plot_stock_zones_monthly` (in `smc_backend.py`)
draw each zone rectangle starting at `df.index[Base_Start_Idx]` - the first
base candle - not at the row where `Zone_Created` is True (the explosive
breakout candle). Our chart was using the latter. Fixed in
`charting._zone_bounds()`, which reads the same `Base_Start_Idx` column
your real `identity_zones_with_multibase` already puts on the zone
dataframe - confirmed the fix moves x0 earlier than the zone-created date,
as it should.

### Added: trim zone rectangle at breach (toggle, default on)

Also matches your real plotting functions exactly: a zone's rectangle now
stops at the first candle whose **Close** crosses `Distal` (demand: Close
\u2264 Distal, supply: Close \u2265 Distal) - the same rule from your
source (the High/Low variant is commented out there too, Close is what's
actually used). New toggle in Chart Filters: **"Trim zone rectangle at
breach"**, on by default since that's what your backend's own plot
functions always do; turn it off to extend every rectangle to the edge of
the chart regardless of breach, if you want the old behavior back.

Breach status now also shows in the zone data table (`Status`: Active /
Breached, plus `Breach Date`), and `Base Start Date` is a new column
alongside `Zone Created` (the old single "Date" column was the explosive
candle's date - kept, just relabeled for clarity now that there's a
separate start date).

### New tab: 📐 Score Analysis

Answers "how do metrics vary with trade score" - re-aggregates your
already-computed `trade_log` joined with `trade_score` (`df_ts`), no
re-analysis:

- **Numeric factors** (Strength, Base Count): bar + line chart of Win Rate
  and Avg PnL at each value, with trade counts labeled so you can spot
  small-sample buckets.
- **Boolean score flags** (every one from `calculate_trade_score` - Gapped,
  Trending, BOS, OB, Sweep, Trend/ITF/HTF Support, N_LTF/N_ITF/N_HTF
  Support, etc.): a tornado chart of the Win Rate delta between flag=True
  and flag=False, ranked by |delta| so the most outcome-correlated factors
  surface first, plus a full comparison table (N, Win Rate, Avg PnL for
  both sides) and CSV export.

New `score_analysis.py` holds the pure aggregation logic (`merge_trade_log_with_score`,
`numeric_breakdown`, `boolean_flag_summary`) - no Streamlit, no backend
calls, just pandas, so it's independently testable.

Verified end-to-end: confirmed `Base_Start_Idx` date is chronologically
before the zone-created date (the actual bug), confirmed breach detection
runs without error, and confirmed the Score Analysis tab surfaces a real,
sensible signal on the SAIL.NS data (e.g. `BOS=True` zones showing a
32-point lower win rate than `BOS=False` in this particular run - not a
claim about what's generally true, just evidence the computation works).
All 5 tabs checked via `AppTest` with zero exceptions, including toggling
the new breach-trim control off and back on.

## Fixed: ratio preset dropdown didn't actually update the sliders

### The bug

Once a Streamlit widget's `key` exists in `session_state` (which happens
after its first render), the widget **ignores its `value=`/`index=`
argument on every subsequent rerun** - only `session_state[key]` matters
from then on. The "Advanced: edit TR/ATR" sliders were computing their
displayed default from the currently-selected preset (`float(tf_ratio[...])`)
every render, but since their `key`s already existed in `session_state`
after the first render, that computed value was silently ignored - so
switching from "Standard" to "SAIL_Backtested" (or any other preset) never
actually changed what the sliders showed or what got sent to your backend.

### The fix

`ui/sidebar.py` now explicitly writes the selected preset's values into
the sliders' `session_state` keys **before** the sliders are instantiated,
but only on a genuine preset change (tracked via `_last_ratio_preset`) -
not on every rerun, which would otherwise silently overwrite any manual
edits you'd made. Two related pieces:

- **Editing any Daily slider by hand automatically switches the preset
  dropdown to "Custom"** via an `on_change` callback - visible
  confirmation that your edited values, not the named preset, are what's
  now in effect. This is the "updated values are considered final" part:
  whatever the sliders show is always what's sent to `run_strategy_for_ticker`,
  regardless of which label happens to be selected.
- The Advanced expander now shows a caption stating which preset (or
  "Custom") the visible values reflect.

Also cleaned up two related Streamlit policy warnings ("widget was created
with a default value but also had its value set via the Session State
API") that the above change surfaced - both the ratio-preset selectbox and
the sliders now only pass `index=`/`value=` on their very first render,
relying on `session_state` afterward, which is Streamlit's recommended
pattern for programmatically-controlled widgets.

Verified with `AppTest`: confirmed switching to `SAIL_Backtested` actually
changes the Base TR/ATR slider to 1.2 and Explosive Body/TR to 0.6 (previously
these NEVER changed regardless of preset - the core bug); confirmed manually
editing a slider to 0.9 both keeps 0.9 and flips the dropdown to "Custom";
confirmed switching to a different preset afterward (`Tight_Base`) still
correctly re-syncs; and ran a full analysis end-to-end with the edited
ratio with zero exceptions and zero warnings.

## UI/UX Redesign — modern dark "quant dashboard" theme

Complete visual overhaul. **Zero changes to analysis logic** - every file
touched here is presentation-only (`ui/`, `charting.py`'s color/layout
code, `app.py`'s layout). `smc_backend.py`, `zone_identification_multibase.py`'s
computation, `ratio_config.py`, `data_loading.py`, `filter_state.py`, and
`score_analysis.py` are untouched in behavior.

### Design system (`ui/style.py`)

A single source of truth for color, typography, and reusable components,
so every tab looks like one coherent product instead of five separately
styled pages:

**Palette** — consistent semantic color language used everywhere (charts,
tables, cards, badges):
| Color | Hex | Meaning |
|---|---|---|
| Green (`bull`) | `#22C55E` | demand zones, profitable trades, bullish candles, "True"/OK |
| Red (`bear`) | `#EF4460` | supply zones, losing trades, bearish candles, errors |
| Amber (`warn`) | `#F5A623` | breached zones, "No Trades" status, caution |
| Blue (`brand`) | `#4F8CFF` | primary actions, equity curve, neutral emphasis |
| Cyan (`accent`) | `#22D3EE` | secondary chart highlights |

Background is a deep charcoal/navy (`#0B0F19` page, `#171E2C` cards) -
typography is **Inter** (via Google Fonts), a font built for dashboard/UI
legibility at small sizes.

**Components** (`ui/style.py`): `inject_global_css()` (fonts, card styling,
tab styling, button styling, hides Streamlit's footer), `app_header()`
(the gradient banner replacing the plain title), `section_header()`
(consistent icon+title+subtitle used at the top of every tab), `stat_cards()`
(color-accented card grid replacing plain `st.metric` calls throughout).

**`.streamlit/config.toml`** sets the native Streamlit theme (this is what
themes buttons, sliders, checkboxes, the sidebar, etc. - CSS alone can't
reach all of that reliably).

### Chart theming (`charting.py`)

New `_theme_layout()` helper applied to every chart in the app:
transparent background (blends into the dark card behind it), Inter font,
subtle gridlines. Specific changes:
- Candlesticks: green/red now match the same `bull`/`bear` used for zones
  and P&L everywhere else, instead of Plotly's default blue/orange - the
  whole app now reads with one consistent color language.
- Zone rectangles: added a colored border (not just fill) matching
  demand/supply, and breached zones are labeled "✕ breached" instead of
  "(breached)".
- Volume bars, equity curve (now with a soft gradient fill under the
  line), composite score gauge, tornado chart, breakdown charts - all
  recolored to the same palette.

### Layout changes

- **Header banner**: gradient card replacing the plain `st.title`, with
  live status badges (build version, Streamlit version, last-analysis
  ticker/timestamp or "No analysis yet").
- **Sidebar**: small brand mark at the top, section labels standardized.
- **Metric displays**: `st.metric` grids replaced with `stat_cards()` -
  color-coded left border (green/red based on whether the number is
  good/bad, e.g. Net PNL negative shows red) across Metrics, Trade Log,
  and Batch Analysis tabs.
- Diagnostics expander demoted (still there, just less visually
  prominent now that the header badges show status at a glance).

### Bugs found and fixed while verifying the redesign

Large multi-line edits during the restyle left duplicated function bodies
in three files (`metrics_tab.py`, `score_tab.py`, `trade_log_tab.py`) -
each had its entire render logic appear twice, which is invisible in a
code review but crashes at runtime with `StreamlitDuplicateElementKey` the
moment both copies of a same-keyed widget actually execute in one script
run. One instance (`metrics_tab.py`'s duplicate) only surfaced when
specifically testing the "filtered metrics" toggle - a normal smoke test
never reached the duplicated code path. Also hardened every `st.plotly_chart`
call app-wide with an explicit unique `key=`, since Streamlit's
auto-generated chart IDs can collide when two charts have similar
structure (this is what surfaced the score_tab duplication in the first
place).

Verified with `streamlit.testing.v1.AppTest` end-to-end: initial load,
Run Analysis, ratio preset switch, manual slider edit, filtered-metrics
toggle on/off, breach-trim toggle, chart filter interaction, batch
analysis run, and drill-down - ten checks, zero exceptions across all of
them.

## Rendering-bug audit + defaults/ticker-picker update

### Systematic rendering-bug sweep

Built a precise duplicate-block detector (distinguishes genuine distant
repeats from trivial overlapping-window noise) and ran it across every
file. Confirmed **zero remaining duplicate-block bugs** in any of our own
code (the three found and fixed previously were the only instances); the
only hits were legitimate, original, untouched patterns inside
`smc_backend.py` itself (e.g. `identify_zones()` and
`identity_zones_with_multibase()` sharing a similar preprocessing
pipeline header by original design).

Also checked and confirmed safe (no crash): `NumberColumn` with `inf`/`NaN`
values, `DateColumn` with mixed `None`/`Timestamp` values - unlike
`ProgressColumn` (fixed earlier), these don't have strict bounds
validation.

**Two real bugs found and fixed:**

1. **HTML injection via ticker names.** `app_header()`, `section_header()`,
   and `stat_cards()` interpolated dynamic text (ticker names, e.g. our
   own `M&M.NS` from the NIFTY 50 preset, or anything typed into the
   ticker box) directly into raw HTML via `unsafe_allow_html=True`, with
   no escaping. Fixed: all dynamic content now goes through
   `html.escape()` before insertion. Verified `M&M.NS` now renders as the
   properly-escaped `M&amp;M.NS` in the markup.

2. **Header status badge was one run behind.** The header banner's status
   badge (analysis success/error/ticker) was computed and rendered
   *before* the "Run Analysis" logic executed in the same script run, so
   it always showed the *previous* run's state rather than the one that
   just completed. Fixed using `st.empty()` as a placeholder: the header's
   visual slot is reserved at the top of the page immediately, but its
   content is filled in *after* the analysis logic runs later in the same
   script - so the `st.status()` progress box still appears in its
   correct position (below the header, above the tabs) while the badge
   itself is always current. Verified: badge now shows `✓ SAIL.NS · <fresh
   timestamp>` immediately after clicking Run Analysis, in the same run.

3. **Synthetic fallback OHLC could go non-positive over long date ranges**
   (found incidentally while testing the new default date range below).
   The synthetic-data generator used an *additive* random walk
   (`100 + cumsum(normal)`); over ~1,500 trading days (the new 2021-present
   default), its cumulative standard deviation is large enough that
   hitting zero or negative prices isn't even rare. A non-positive Close
   then fails `np.log()` in your backend's Kalman filter
   (`KalmanTrendFilter` runs on `log(Close)`) - not a crash, but a silent
   `RuntimeWarning` and garbage trend output. Fixed by switching to a
   *geometric* (multiplicative) random walk, which is positive by
   construction and also just a more standard synthetic-price model.
   Verified: 1,486 rows generated over the full default range, zero
   non-positive prices, and the `RuntimeWarning` no longer appears.

### Sidebar defaults

- **Date Range** default changed to **2021-01-01 → today** (was "3 years
  ago → today").
- **Initial Capital** default changed to **₹100,000** (was ₹500,000).

### New: search-by-company-name ticker picker

`index_constituents.py` now also ships a `COMPANY_NAMES` map (NIFTY 50 +
Next 50, ~99 companies - best-effort names for search convenience, not
guaranteed exact legal names for the handful of recently-renamed/demerged
entities already flagged elsewhere in that file).

The sidebar's ticker field is now a **"Find stock by"** choice:
- **Search company name** (default) - a searchable dropdown
  (Streamlit's `selectbox` supports type-to-filter) showing
  "Company Name (TICKER.NS)", defaulting to Reliance Industries. Covers
  the ~99 largest NSE-listed companies without needing to know any ticker
  symbol at all.
- **Type ticker directly** - the original free-text field (defaults to
  `SAIL.NS`), for anything outside that universe.

Verified both modes end-to-end with `AppTest`: default search mode
resolves to `RELIANCE.NS` and runs cleanly; switching to direct-entry mode
correctly shows/uses `SAIL.NS`; both produce zero exceptions through a
full Run Analysis.

## Fixed: stat cards showing raw HTML text instead of rendering

### Root cause

`stat_cards()` (and `app_header()`, same pattern) built their HTML using
a **multi-line f-string indented to match the surrounding Python code**:

```python
html_out += f"""
        <div class="stat-card" ...>
            <div class="stat-label">...
```

Every generated HTML line inherited 8+ literal leading spaces from the
source code's own indentation. Markdown treats any line indented 4+
spaces as a **literal code block**, not something to parse as HTML - so
instead of rendering styled cards, the browser showed the raw
`<div class="stat-card">...` tags as plain text. This is exactly why it
appeared next to "Win Rate" and "Total Trades" in the Metrics tab, and
next to "Trades Shown" in the Trade Log tab - both use `stat_cards()`.
`section_header()` was unaffected because it was already a single-line
string with no indentation.

This bug existed from the moment `stat_cards()`/`app_header()` were first
introduced, but `AppTest` only checks for *exceptions*, not visual
correctness - a malformed-but-non-crashing render like this doesn't throw,
so automated testing never caught it. Confirms the automated test suite
catches crashes, not "renders but looks wrong."

### Fix

Both functions now build their HTML as **single-line concatenated
strings with zero leading whitespace** (string concatenation instead of
an indented triple-quoted f-string). Verified directly: every stat-card
`st.markdown()` call now produces one unbroken line with no leading
spaces on any line.

### Also restored/added the requested metrics

- **Net PNL** was actually still present in the code the whole time - it
  was just unreadable, buried in the broken HTML text alongside
  everything else. Now displays correctly.
- **Final Capital** is a genuinely new card: reads the last
  `Capital_After_Trade` value from your real `run_risk_management_simulation`
  output (sorted by Exit Date) - no new calculation, just surfacing a
  number your backend already computes but that wasn't shown anywhere as
  its own metric before.
- Metrics tab layout is now three rows: Win Rate / Profit Factor / System
  Expectancy, then **Final Capital / Net PNL / Total Trades**, then
  Demand Zones / Supply Zones (split into two cards instead of one
  combined "X / Y" card, for clearer at-a-glance reading).

Verified with `AppTest`: ran a full analysis, inspected every rendered
`stat-card` markdown block directly, confirmed each is a single line with
no leading whitespace (the only "indented" match left in the whole page
is the global CSS `<style>` block, which is supposed to have indentation
- that's normal CSS, not a bug), and confirmed "Final Capital", "Net
PNL", "Total Trades", and "Win Rate" all appear as expected text in the
rendered output.

## Outcome (Profit/Loss) joins the shared filter system + Trade Log mirrors it

### Outcome is now a shared Chart Filter

`filter_state.py` gained `outcome_options(trade_log)` - every distinct
value actually present in your real `run_risk_management_simulation`
output (not hardcoded to "Profit"/"Stop Loss"; it reads whatever's really
there, so it'd pick up something like "Invalidated (Gap Through Zone)"
too if your backend ever produces it) - and `get_active_filters()` now
includes `outcome_types`.

`charting.filter_zones()` gained `trade_log`/`outcome_types` parameters:
a zone is kept only if its resulting trade's Outcome is in the selected
set. Like Strength/Freshness/score flags, this only has an effect on the
daily timeframe (trade_log doesn't exist for weekly/monthly) - and a zone
that never triggered a trade is excluded whenever this filter is actively
narrowing the selection (there's no outcome to match against an
untriggered zone).

The Charts tab's "Daily-only filters" expander now has an **Outcome**
pills control alongside Strength/Freshness/score flags - narrowing it
(e.g. to "Profit" only) changes which zones are drawn on the chart, same
as every other filter there.

### Trade Log tab now mirrors the shared filters

New toggle: **"Show only trades matching current Chart Filters"** - reads
the exact same `get_active_filters()` state the Charts tab set (Base
Count, Zone Type, Pattern, Strength, Freshness, score flags, and now
Outcome), re-slices the trade log accordingly, and shows a caption
describing exactly which filters are active and how many trades matched -
same pattern as the Metrics tab's existing "filtered metrics" toggle, so
all three tabs (Charts/Metrics/Trade Log) can now show a consistent view
of "just this subset" without ever re-running analysis.

The tab's own local Outcome/Zone Type pills (for quick ad-hoc browsing)
still work on top of whichever set this toggle produces - both layers of
filtering compose rather than conflict.

Verified with `AppTest`: narrowed the shared Outcome filter to "Profit"
only (10 \u2192 2 zones on the Charts tab), then enabled the Trade Log
toggle and confirmed it independently arrived at the identical "2 of 10
trades match" with a caption explicitly listing `Outcome in ['Profit']` -
the three tabs can't drift out of sync since they all read from the same
`get_active_filters()` function. Also re-ran the full regression suite
(Run Analysis, Metrics filtered toggle, ratio preset switch, Reset all
filters, Batch Analysis) - zero exceptions across all of it.

## Light "Kite Web + Groww Web" theme (per Figma design brief)

A full visual-language redesign was requested via a detailed Figma design
brief (light fintech aesthetic inspired by Zerodha Kite Web + Groww Web).
**No Figma file was produced** - there's no design-file tool available in
this environment - but the brief's actual design system (color tokens,
typography, component patterns, icon language) was translated directly
into the working app's CSS/theme/charts, which is the more useful
deliverable for an iterating Streamlit product than a static mockup would
be. Zero changes to `smc_backend.py` or any analysis logic.

### What changed

- **Theme flipped from dark to light.** `.streamlit/config.toml` and
  `ui/style.py`'s `PALETTE` now use the brief's exact color tokens:
  `surface/page #F6F8FB`, `surface/card #FFFFFF`, `border/default #E4E8F0`,
  `text/primary #0F1729`, `brand/primary #3861FB` (Kite-blue), `bull/green
  #16A34A`, `bear/red #E5484D`, `warn/amber #F5A623`, `accent/teal
  #00C896` - kept visually distinct from bull-green so it's never
  mistaken for a profit signal, per the brief.
- **Stat cards are now white with a colored left-border accent**, not a
  colored card background - the single biggest visual shift the brief
  called out explicitly. Caught a real bug fixing this: the old
  `bull_soft`/`bear_soft` tokens were solid dark-theme badge colors;
  reused directly as chart zone *fill* colors they'd have painted opaque
  boxes over the candlesticks. Added separate `bull_overlay`/`bear_overlay`
  tokens (true ~12% alpha, per the brief's spec) specifically for chart
  fills, keeping the solid tokens for badges/cells as intended.
- **All emoji replaced with Google's Material Symbols icon font** - the
  brief's #1 "remove this" item ("emoji read as prototype, not product").
  Two mechanisms, same icon family throughout: native Streamlit widgets
  (tabs, buttons, expanders) use the `:material/name:` shortcode
  Streamlit itself renders; custom HTML (section headers, the header
  banner, the sidebar brand mark) uses a loaded
  `<span class="material-symbols-outlined">` font via a new `icon_span()`
  helper. Verified with a full-codebase Unicode sweep: zero emoji or
  symbol characters remain outside `smc_backend.py`.
- **Charts re-themed for light backgrounds**: thin light-grey gridlines
  (`rgba(15,23,41,0.06)`) instead of the previous light-on-dark scheme,
  candlesticks/volume bars recolored to the new bull/bear hex, equity
  curve fill recolored to the new brand blue.
- **Segmented control**: the sidebar's "Find stock by" picker now uses
  `st.pills` (single-select) instead of a radio button, matching the
  brief's Groww-style pill segmented control pattern.
- **Tabs**: flat underline indicator in brand blue (Kite convention),
  rather than a pill/card tab style.
- **Tabular figures**: `font-variant-numeric: tabular-nums` applied
  globally so numbers in tables and stat cards align on their digits.

### What wasn't (and mostly can't be) done

The brief also specifies things that are genuine Figma-file deliverables
rather than app features, or that Streamlit's component model doesn't
support without a custom frontend component (out of scope for a
reskin): a literal Figma file with token/component/screen pages; tablet
(1024px) and mobile (390px) specific frames with a collapsible drawer
sidebar; frozen/sticky table columns; skeleton-shimmer loading transitions
on filter changes (Streamlit reruns are already near-instant for these,
so a spinner would be counterproductive); and a fully custom
segmented-control/toggle component set beyond what `st.pills`/`st.toggle`
already provide. If any of these matter enough to invest in, the
concrete next step for the responsive/mobile piece would be checking
Streamlit's mobile rendering behavior directly rather than assuming it
needs a custom drawer.

Verified with `streamlit.testing.v1.AppTest`: a 7-step interactive
regression (Run Analysis, ratio preset switch, Metrics filtered toggle,
Outcome filter narrowing, Trade Log chart-filter toggle, Reset all
filters, Batch Analysis) - zero exceptions throughout - plus a direct
inspection of every icon-bearing markdown block confirming single-line,
non-indented, correctly-escaped HTML (the same class of bug fixed
earlier in `stat_cards()`).

## Mockup-driven polish pass (per updates.txt + screenshots)

Every point below maps to a specific callout from the uploaded mockup
screenshots. Zero changes to `smc_backend.py` or any analysis/backtest
logic - everything here is either a new presentation-layer computation
on data your backend already produces, or pure restyling.

### Sidebar (charts_1.png)
- **Date Range** split into two separate Start Date / End Date inputs
  side by side, instead of one combined range picker.
- **Ticker selection** now shows a colored chip confirming the selected
  ticker (e.g. `RELIANCE.NS`) right under the company search box.
- Ratio sliders (Advanced expander) relabeled without the redundant
  `(candle, timeframe)` suffix - the surrounding section headers/captions
  already establish that context, so the sliders themselves read cleaner.

### Charts tab (charts_2.png)
- **Chart heading card**: ticker + timeframe + a zone-count pill +
  Demand/Supply color legend, above each candlestick chart (previously
  this info was only in a caption below).
- **Zone labels simplified** to `D3`/`S2` style (type letter + Base
  Count, plus `· S{strength}` on the daily tab) instead of `BC3 S2`.
- Volume subplot now has a `VOL` axis label.
- Data-source caption rewords the live-fetch case as "Yahoo Finance
  (yfinance)" to match the mockup's phrasing.
- **Zone table redesigned**: added a combined `Price Range` column
  (`₹X – ₹Y`, from Proximal/Distal) and a `Flags` column (comma-separated
  list of whichever trade-score boolean columns are True for that zone) -
  the individual Proximal/Distal/Target and per-flag boolean columns are
  still present further along in the table, nothing is hidden, just
  reordered so the curated/summary view comes first.

### Backtest Metrics tab (backtest_matrics.png)
- **Stat cards now show a "small key info" delta line**, all computed
  from real numbers your backend already produces - nothing fabricated:
  - Win Rate -> "`{wins}` wins / `{losses}` losses"
  - Profit Factor -> "Above/Below breakeven (1.0)"
  - System Expectancy -> "Avg PnL `{value}`"
  - Net PNL -> "`{return%}` return" (computed from Final Capital vs.
    Initial Capital - both real)
  - Demand/Supply Zones -> "`{Profitable Demand/Supply Zones}` wins"
    (this metric already existed in `evaluate_strategy_metrics`'s output,
    just wasn't surfaced before)
- **Indian-convention currency formatting** (`₹5.96L`, `₹96.3K`, `₹1.24Cr`)
  via a new shared `format_inr()` helper, replacing raw full numbers.
- **"Edge quality" badge** under the Composite Score gauge - a labeled
  threshold on your real `calculate_composite_score` output (\u226570
  "Strong Edge" / \u226540 "Moderate Edge" / below "Weak Edge"), not a new
  calculation.

### Trade Log tab (trade_log.png)
- **New derived columns**, all pure arithmetic/joins on data your backend
  already computed - no new analysis: `Days` (Exit - Entry date), `R
  Multiple` (Trade_PnL / Risk_Amount_Per_Trade), `% Return` (Trade_PnL /
  Capital_At_Entry), `Zone Score` (Strength, joined from trade_score by
  the same index trade_log already uses).
- **`Zone Proximal` / `Zone Distal` / `Zone Target`** columns, joined from
  the daily zones dataframe by index. Deliberately labeled "Zone ..." and
  not "Entry/Exit Price" - your backend doesn't log an actual fill price
  anywhere, so showing the zone's real boundary levels under an honest
  label is safer than implying a logged price that doesn't exist.
- **Colored Outcome/PnL cells** via a pandas Styler (green/red, consistent
  with the rest of the app) - confirmed `Styler` + `column_config` compose
  correctly in this Streamlit version before relying on it.

### Score Analysis tab (score_anal.png)
- Numeric-factor charts (Strength, Base Count) now sit inside bordered
  card containers with their own heading + one-line description.
- **New "Flag Impact on Win Rate" list**: a clean custom HTML
  label-bar-value-n° row per flag (replacing the Plotly tornado chart as
  the primary view) - same `boolean_flag_summary()` data, just a more
  minimal presentation matching the mockup. The Plotly tornado chart and
  full comparison table are still available in a "Chart view + full
  comparison table" expander for anyone who wants the interactive
  version.

### Batch Analysis tab (batch_anal.png)
- **Ticker universe picker** switched from a radio row to a proper
  segmented-pill control (`st.pills`).
- **Company column** added (from `index_constituents.COMPANY_NAMES`,
  blank for tickers outside the NIFTY 50/Next 50 universe).
- **Composite Score now renders as an inline progress bar**
  (`ProgressColumn`) - this is exactly the column type that crashed the
  app on NaN values earlier in this project. Fixed safely this time: NaN
  is filled to 0 only in a *display-only* copy of the table (the
  underlying data used for CSV export and the errored-tickers list keeps
  the real NaN, so nothing is misrepresented in exported data). Stress-
  tested directly: ran the full NIFTY 50 batch (49 tickers, guaranteed
  many NaN scores in this offline sandbox) - zero exceptions.
- Colored Status (green/amber/red) and Net PNL (bull/bear) cells via the
  same Styler pattern used in Trade Log.

### Bug found during this pass
A stopwatch emoji (`\u23f1\ufe0f`) in `batch_tab.py` had slipped past the
previous emoji-removal sweep - it uses a Unicode block (Miscellaneous
Technical) the earlier regex didn't cover. Widened the sweep's Unicode
ranges and re-scanned the whole codebase; confirmed zero emoji/symbol
characters remain outside `smc_backend.py`.

Verified with a 7-step `AppTest` regression covering every tab and the
riskiest change specifically (the batch table's `ProgressColumn`, tested
against a full 49-ticker run with guaranteed NaN scores) - zero
exceptions throughout.
