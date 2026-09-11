"""
Static snapshots of NSE index constituents, for the Batch Analysis ticker
picker's built-in presets.

IMPORTANT: NSE rebalances Nifty 50 / Nifty Next 50 semi-annually (cutoff
dates Jan 31 and Jul 31), so these lists WILL drift out of date. Each list
below is dated. For anything where precision matters, verify against
https://www.niftyindices.com or use the "Custom list" / "Upload CSV"
options in the Batch Analysis tab instead of these presets - that's the
reliable long-term path, not re-editing this file every rebalance.

Symbols are plain NSE symbols (no .NS suffix) - get_ticker_list() below
appends .NS to match this app's ticker convention.
"""

NIFTY_50_AS_OF = "2025-12-08"
# NOTE: TMPV (Tata Motors Passenger Vehicles) reflects a 2025 demerger of
# Tata Motors into separate commercial/passenger-vehicle listings - double
# check this symbol against your broker/NSE before relying on it.
NIFTY_50 = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL",
    "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "ETERNAL",
    "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HINDALCO",
    "HINDUNILVR", "ICICIBANK", "INDIGO", "INFY", "ITC",
    "JIOFIN", "JSWSTEEL", "KOTAKBANK", "LT", "M&M",
    "MARUTI", "MAXHEALTH", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SHRIRAMFIN", "SBIN",
    "SUNPHARMA", "TCS", "TATACONSUM", "TMPV", "TATASTEEL",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]

# A couple of these (post-demerger entities) are less certain than the
# rest - verify before relying on them: TATAMOTORS (Tata Motors, post
# commercial/passenger vehicle split), TATACAPITAL, SIEMENS Energy spinoff.
# NOTE: 49, not 50 - "Siemens Energy" (source symbol uncertain, possibly
# ENRIN post-listing) was deliberately dropped rather than guessed. Add it
# yourself once confirmed, or just use Custom list / Upload CSV.
NIFTY_NEXT_50_AS_OF = "2026-04-01"
NIFTY_NEXT_50 = [
    "ABB", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM",
    "BAJAJHLDNG", "BANKBARODA", "BPCL", "BRITANNIA", "BOSCHLTD",
    "CANBK", "CGPOWER", "CHOLAFIN", "CUMMINSIND", "DIVISLAB",
    "DLF", "DMART", "GAIL", "GODREJCP", "HDFCAMC",
    "HAL", "HINDZINC", "HYUNDAI", "INDHOTEL", "IOC",
    "IRFC", "JINDALSTEL", "LODHA", "LTIM", "MAZDOCK",
    "MUTHOOTFIN", "PIDILITIND", "PFC", "PNB", "RECLTD",
    "MOTHERSON", "SHREECEM", "SIEMENS", "SOLARINDS", "TATACAPITAL",
    "TATAMOTORS", "TATAPOWER", "TORNTPHARM", "TVSMOTOR", "UNIONBANK",
    "UNITDSPR", "VBL", "VEDL", "ZYDUSLIFE",
]

PRESETS = {
    "NIFTY 50": (NIFTY_50, NIFTY_50_AS_OF),
    "NIFTY Next 50": (NIFTY_NEXT_50, NIFTY_NEXT_50_AS_OF),
    "NIFTY 100": (NIFTY_50 + NIFTY_NEXT_50, f"{NIFTY_50_AS_OF} / {NIFTY_NEXT_50_AS_OF}"),
}


def get_ticker_list(preset_name: str) -> list:
    symbols, _ = PRESETS[preset_name]
    return [f"{s}.NS" for s in symbols]


def get_as_of(preset_name: str) -> str:
    _, as_of = PRESETS[preset_name]
    return as_of
