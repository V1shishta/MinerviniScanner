"""
Minervini's 8-condition Stage 2 trend template (conditions 1-7 here;
condition 8, RS rank, needs the whole universe so it's handled in
build_watchlist.py after this returns a raw score per stock).
"""
import pandas as pd


def passes_trend_template(daily: pd.DataFrame) -> bool:
    if len(daily) < 210:
        return False

    close = daily["close"]
    ma50 = close.rolling(50).mean()
    ma150 = close.rolling(150).mean()
    ma200 = close.rolling(200).mean()
    p = close.iloc[-1]
    hi52 = close.tail(252).max()
    lo52 = close.tail(252).min()

    conditions = [
        p > ma150.iloc[-1] and p > ma200.iloc[-1],          # 1
        ma150.iloc[-1] > ma200.iloc[-1],                     # 2
        ma200.iloc[-1] > ma200.iloc[-22],                    # 3: 200dma up over ~1 month
        ma50.iloc[-1] > ma150.iloc[-1] > ma200.iloc[-1],     # 4
        p > ma50.iloc[-1],                                   # 5
        p >= 1.25 * lo52,                                    # 6
        p >= 0.75 * hi52,                                    # 7
    ]
    return all(conditions)


def rs_score(daily: pd.DataFrame) -> float:
    """IBD-style weighted return. Only meaningful as a RANK against other
    stocks in the universe -- percentile-rank this across the universe
    before applying the RS >= 70 cutoff (done in build_watchlist.py)."""
    close = daily["close"]

    def ret(n):
        return close.iloc[-1] / close.iloc[-n] - 1 if len(close) > n else 0.0

    return 0.4 * ret(63) + 0.2 * ret(126) + 0.2 * ret(189) + 0.2 * ret(252)
