# SMC Scanner & Backtester (Streamlit prototype)

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

This will work immediately with the **placeholder** backend
(`zone_identification_multibase.py`) so you can confirm the UI/layout first.

## Wiring in your real backend

1. Delete the placeholder `zone_identification_multibase.py` at the repo root.
2. Drop your real file (same filename) in its place.
3. Confirm `run_strategy_for_ticker(ticker, start_date, end_date, risk_pct, initial_capital)`
   is the actual entry point signature. If it differs, update the call in
   `data_access.py` only — nothing else needs to change.
4. Confirm the return shape. `data_access.py` currently assumes an object/dict
   with `.figure` (Plotly), `.metrics` (dict), `.trades` (DataFrame). If your
   backend returns something else, adjust the three `render()` functions in
   `ui/tabs/` to match — each is intentionally isolated so a shape change in
   one tab doesn't ripple into the others.

## Structure

```
app.py                  entry point: page config, sidebar, tab router
state.py                 session_state key helpers
data_access.py            cached wrapper around the backend (only file that imports it)
ui/sidebar.py             sidebar inputs -> config dict
ui/tabs/charts_tab.py     Plotly chart rendering
ui/tabs/metrics_tab.py    KPI cards / summary table
ui/tabs/trade_log_tab.py  trade-by-trade dataframe
zone_identification_multibase.py   <- YOUR backend goes here
```

## Status

- [x] Step 1: sidebar inputs, tab shell, cached call to `run_strategy_for_ticker`
- [ ] Step 2: unpack `results.figure` into the Charts tab
- [ ] Step 3: unpack `results.metrics` into KPI cards
- [ ] Step 4: unpack `results.trades` into the Trade Log table
