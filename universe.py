"""
Build the tradable universe: every NSE equity with market cap > config.MIN_MARKET_CAP_CR.

Run this manually every few weeks -- it is NOT part of the hourly pipeline.
Market cap doesn't move the qualifying set fast enough to justify refetching
it every hour, and per-symbol yfinance lookups across ~2000 names is slow
and rate-limit-prone, which is exactly why this is split out as its own job.

    python universe.py

ALTERNATIVE: if you have Bloomberg Terminal access, BDP(<ticker> Equity,
CUR_MKT_CAP) across the full NSE ticker list and exporting to a CSV with
columns [symbol, market_cap_cr] will be faster and more reliable than this
script. Just produce universe_500cr.csv in that shape and skip running this
file entirely.
"""
import time
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

from config import MIN_MARKET_CAP_CR, UNIVERSE_FILE

NSE_EQUITY_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"


def get_nse_symbol_list() -> list[str]:
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(NSE_EQUITY_LIST_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    return df["SYMBOL"].dropna().unique().tolist()


def fetch_market_cap_cr(symbol: str) -> float | None:
    """yfinance reports market cap in rupees for NSE tickers; 1 crore = 1e7 rupees."""
    try:
        info = yf.Ticker(f"{symbol}.NS").info
        mcap = info.get("marketCap")
        return mcap / 1e7 if mcap else None
    except Exception:
        return None


def build_universe():
    symbols = get_nse_symbol_list()
    print(f"Fetched {len(symbols)} NSE symbols. Pulling market cap (slow part)...")

    rows = []
    for i, sym in enumerate(symbols):
        mcap = fetch_market_cap_cr(sym)
        if mcap and mcap > MIN_MARKET_CAP_CR:
            rows.append({"symbol": sym, "market_cap_cr": round(mcap, 1)})
        if i % 100 == 0:
            print(f"  ...{i}/{len(symbols)} checked, {len(rows)} qualify so far")
        time.sleep(0.3)  # be polite to Yahoo's API

    out = pd.DataFrame(rows).sort_values("market_cap_cr", ascending=False)
    out.to_csv(UNIVERSE_FILE, index=False)
    print(f"Universe built: {len(out)} stocks above Rs.{MIN_MARKET_CAP_CR}cr -> {UNIVERSE_FILE}")
    print("Sanity check a few rows before trusting this, e.g. RELIANCE / TCS market cap:")
    print(out.head(5).to_string(index=False))


if __name__ == "__main__":
    build_universe()
