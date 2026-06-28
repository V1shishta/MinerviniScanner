"""
Daily job: scan the >500cr universe, apply the trend template + VCP
detector, and write a watchlist of valid setups with their pivot and
volume baseline. The hourly scanner only checks symbols in this file --
it does NOT redo full daily-bar VCP detection every hour.

Run this once, before market open (see .github/workflows/daily_watchlist.yml).
"""
import json

import pandas as pd

from config import UNIVERSE_FILE, LOOKBACK_DAYS, RS_RANK_MIN, WATCHLIST_FILE
from data_fetch import get_daily_history
from trend_template import passes_trend_template, rs_score
from vcp_detect import detect_vcp


def build_watchlist():
    universe = pd.read_csv(UNIVERSE_FILE)["symbol"].tolist()
    print(f"Scanning {len(universe)} stocks above the market cap cutoff...")

    candidates = []
    for symbol in universe:
        try:
            daily = get_daily_history(symbol, LOOKBACK_DAYS)
        except Exception as e:
            print(f"  skip {symbol}: {e}")
            continue
        if daily.empty or not passes_trend_template(daily):
            continue
        candidates.append({"symbol": symbol, "daily": daily, "rs_raw": rs_score(daily)})

    print(f"{len(candidates)} stocks passed the trend template.")

    if not candidates:
        json.dump([], open(WATCHLIST_FILE, "w"))
        print(f"No candidates -> empty {WATCHLIST_FILE} written.")
        return

    rs_values = pd.Series([c["rs_raw"] for c in candidates])
    rs_pct = rs_values.rank(pct=True) * 100  # cross-sectional RS rank, condition 8

    watchlist = []
    for c, rs in zip(candidates, rs_pct):
        if rs < RS_RANK_MIN:
            continue
        is_valid, pivot, contractions, avg_vol_50 = detect_vcp(c["daily"])
        if not is_valid:
            continue
        last_close = float(c["daily"]["close"].iloc[-1])
        if last_close > pivot:
            # already broken out in yesterday's daily bar -- not a fresh
            # setup for the hourly scanner to watch for
            continue
        watchlist.append({
            "symbol": c["symbol"],
            "pivot": round(float(pivot), 2),
            "rs_rank": round(float(rs), 1),
            "contractions_pct": contractions,
            "avg_vol_50": avg_vol_50,
        })

    json.dump(watchlist, open(WATCHLIST_FILE, "w"), indent=2)
    print(f"Watchlist built: {len(watchlist)} valid VCP setups -> {WATCHLIST_FILE}")
    for w in watchlist:
        print(f"  {w['symbol']:<15} pivot={w['pivot']:<10} RS={w['rs_rank']:<6} contractions%={w['contractions_pct']}")


if __name__ == "__main__":
    build_watchlist()
