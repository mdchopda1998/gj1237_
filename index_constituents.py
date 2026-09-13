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

# Company names for the sidebar's search-by-name ticker picker - best-effort
# for search/display convenience only, not guaranteed exact-legal-name
# accuracy (a few post-demerger/rename entities are genuinely ambiguous,
# see the NOTEs above). If a name looks wrong, the symbol itself is what
# actually drives the analysis - use "Type ticker directly" for precision.
COMPANY_NAMES = {
    "ADANIENT": "Adani Enterprises", "ADANIPORTS": "Adani Ports & SEZ",
    "APOLLOHOSP": "Apollo Hospitals", "ASIANPAINT": "Asian Paints",
    "AXISBANK": "Axis Bank", "BAJAJ-AUTO": "Bajaj Auto",
    "BAJFINANCE": "Bajaj Finance", "BAJAJFINSV": "Bajaj Finserv",
    "BEL": "Bharat Electronics", "BHARTIARTL": "Bharti Airtel",
    "CIPLA": "Cipla", "COALINDIA": "Coal India",
    "DRREDDY": "Dr Reddy's Laboratories", "EICHERMOT": "Eicher Motors",
    "ETERNAL": "Eternal (Zomato)", "GRASIM": "Grasim Industries",
    "HCLTECH": "HCL Technologies", "HDFCBANK": "HDFC Bank",
    "HDFCLIFE": "HDFC Life Insurance", "HINDALCO": "Hindalco Industries",
    "HINDUNILVR": "Hindustan Unilever", "ICICIBANK": "ICICI Bank",
    "INDIGO": "InterGlobe Aviation (IndiGo)", "INFY": "Infosys",
    "ITC": "ITC Limited", "JIOFIN": "Jio Financial Services",
    "JSWSTEEL": "JSW Steel", "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro", "M&M": "Mahindra & Mahindra",
    "MARUTI": "Maruti Suzuki India", "MAXHEALTH": "Max Healthcare",
    "NESTLEIND": "Nestle India", "NTPC": "NTPC Limited",
    "ONGC": "Oil & Natural Gas Corporation", "POWERGRID": "Power Grid Corporation",
    "RELIANCE": "Reliance Industries", "SBILIFE": "SBI Life Insurance",
    "SHRIRAMFIN": "Shriram Finance", "SBIN": "State Bank of India",
    "SUNPHARMA": "Sun Pharmaceutical Industries", "TCS": "Tata Consultancy Services",
    "TATACONSUM": "Tata Consumer Products", "TMPV": "Tata Motors Passenger Vehicles",
    "TATASTEEL": "Tata Steel", "TECHM": "Tech Mahindra",
    "TITAN": "Titan Company", "TRENT": "Trent Limited",
    "ULTRACEMCO": "UltraTech Cement", "WIPRO": "Wipro",
    "ABB": "ABB India", "ADANIENSOL": "Adani Energy Solutions",
    "ADANIGREEN": "Adani Green Energy", "ADANIPOWER": "Adani Power",
    "AMBUJACEM": "Ambuja Cements", "BAJAJHLDNG": "Bajaj Holdings & Investment",
    "BANKBARODA": "Bank of Baroda", "BPCL": "Bharat Petroleum",
    "BRITANNIA": "Britannia Industries", "BOSCHLTD": "Bosch Limited",
    "CANBK": "Canara Bank", "CGPOWER": "CG Power & Industrial Solutions",
    "CHOLAFIN": "Cholamandalam Investment & Finance", "CUMMINSIND": "Cummins India",
    "DIVISLAB": "Divi's Laboratories", "DLF": "DLF Limited",
    "DMART": "Avenue Supermarts (DMart)", "GAIL": "GAIL India",
    "GODREJCP": "Godrej Consumer Products", "HDFCAMC": "HDFC Asset Management",
    "HAL": "Hindustan Aeronautics", "HINDZINC": "Hindustan Zinc",
    "HYUNDAI": "Hyundai Motor India", "INDHOTEL": "Indian Hotels Company",
    "IOC": "Indian Oil Corporation", "IRFC": "Indian Railway Finance Corporation",
    "JINDALSTEL": "Jindal Steel & Power", "LODHA": "Macrotech Developers (Lodha)",
    "LTIM": "LTIMindtree", "MAZDOCK": "Mazagon Dock Shipbuilders",
    "MUTHOOTFIN": "Muthoot Finance", "PIDILITIND": "Pidilite Industries",
    "PFC": "Power Finance Corporation", "PNB": "Punjab National Bank",
    "RECLTD": "REC Limited", "MOTHERSON": "Samvardhana Motherson International",
    "SHREECEM": "Shree Cement", "SIEMENS": "Siemens Limited",
    "SOLARINDS": "Solar Industries India", "TATACAPITAL": "Tata Capital",
    "TATAMOTORS": "Tata Motors", "TATAPOWER": "Tata Power",
    "TORNTPHARM": "Torrent Pharmaceuticals", "TVSMOTOR": "TVS Motor Company",
    "UNIONBANK": "Union Bank of India", "UNITDSPR": "United Spirits",
    "VBL": "Varun Beverages", "VEDL": "Vedanta Limited",
    "ZYDUSLIFE": "Zydus Lifesciences",
}


def search_universe() -> list:
    """
    (ticker, display_label) pairs for every NIFTY 50 + Next 50 constituent,
    sorted by company name - feeds the sidebar's search-by-name picker.
    """
    symbols = NIFTY_50 + NIFTY_NEXT_50
    pairs = []
    for s in symbols:
        ticker = f"{s}.NS"
        name = COMPANY_NAMES.get(s, s)
        pairs.append((ticker, f"{name} ({ticker})"))
    return sorted(pairs, key=lambda pair: pair[1])


def get_ticker_list(preset_name: str) -> list:
    symbols, _ = PRESETS[preset_name]
    return [f"{s}.NS" for s in symbols]


def get_as_of(preset_name: str) -> str:
    _, as_of = PRESETS[preset_name]
    return as_of
