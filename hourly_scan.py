"""
Hourly job: for every symbol on today's watchlist, check the latest
intraday price/volume against its pivot. Sends a Telegram alert on a
fresh breakout and records it so the same setup doesn't alert twice
in one day.

Run this every hour during market hours (see .github/workflows/hourly_scan.yml).
"""
import json
import os
import datetime as dt

import pandas as pd

from config import WATCHLIST_FILE, ALERTED_TODAY_FILE, TOTAL_MARKET_MINUTES, BREAKOUT_VOL_MULTIPLIER
from data_fetch import get_intraday_today
from telegram_bot import send_alert


def load_alerted_today() -> set:
    if not os.path.exists(ALERTED_TODAY_FILE):
        return set()
    data = json.load(open(ALERTED_TODAY_FILE))
    if data.get("date") != str(dt.date.today()):
        return set()  # stale -- new trading day, reset
    return set(data.get("symbols", []))


def save_alerted_today(symbols: set):
    json.dump({"date": str(dt.date.today()), "symbols": sorted(symbols)}, open(ALERTED_TODAY_FILE, "w"))


def elapsed_market_minutes() -> int:
    now = pd.Timestamp.now(tz="Asia/Kolkata")
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    return max(1, int((now - market_open).total_seconds() / 60))


def run_scan():
    if not os.path.exists(WATCHLIST_FILE):
        print(f"{WATCHLIST_FILE} not found -- run build_watchlist.py first.")
        return
    watchlist = json.load(open(WATCHLIST_FILE))
    if not watchlist:
        print("Watchlist is empty -- nothing to scan this run.")
        return

    already_alerted = load_alerted_today()
    time_fraction = min(1.0, elapsed_market_minutes() / TOTAL_MARKET_MINUTES)

    for setup in watchlist:
        symbol = setup["symbol"]
        if symbol in already_alerted:
            continue

        try:
            intraday = get_intraday_today(symbol)
        except Exception as e:
            print(f"  skip {symbol}: {e}")
            continue
        if intraday.empty:
            continue

        last_price = float(intraday["Close"].iloc[-1])
        cum_volume = float(intraday["Volume"].sum())
        expected_vol_so_far = setup["avg_vol_50"] * time_fraction
        relative_volume = cum_volume / expected_vol_so_far if expected_vol_so_far else 0.0

        breakout = last_price > setup["pivot"] and relative_volume >= BREAKOUT_VOL_MULTIPLIER
        print(f"  {symbol:<15} price={last_price:<9.2f} pivot={setup['pivot']:<9.2f} relvol={relative_volume:<6.2f} breakout={breakout}")

        if breakout:
            send_alert(symbol, last_price, setup["pivot"], relative_volume, setup["rs_rank"])
            already_alerted.add(symbol)

    save_alerted_today(already_alerted)


if __name__ == "__main__":
    run_scan()
