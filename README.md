# gj1237_
Hi hello bye bye
smc_dashboard/
├── app.py                  # entry point: page config, sidebar, tab router
├── state.py                 # st.session_state helpers (typed getters/setters)
├── data_access.py            # cached wrappers around your backend calls
├── ui/
│   ├── sidebar.py            # renders inputs, returns a config dict/dataclass
│   └── tabs/
│       ├── charts_tab.py     # renders Plotly figures from backend
│       ├── metrics_tab.py    # renders backtest KPI cards/tables
│       └── trade_log_tab.py  # renders trade-by-trade dataframe
└── zone_identification_multibase.py   # your existing backend, untouched