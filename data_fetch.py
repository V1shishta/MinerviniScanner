"""
OHLCV data access.

Daily bars: jugaad-data's NSE historical endpoint (same source as your
gap-fill scanner / IPO breakout pipeline) -- used for trend template,
RS rank, and VCP/contraction detection.

Intraday bars: yfinance 60m interval. jugaad-data doesn't expose free
historical intraday data, so this is the practical fallback for the
live breakout check.
"""
import datetime as dt

import pandas as pd
import yfinance as yf
from jugaad_data.nse import stock_df


def get_daily_history(symbol: str, lookback_days: int) -> pd.DataFrame:
    to_date = dt.date.today()
    from_date = to_date - dt.timedelta(days=int(lookback_days * 1.6))  # buffer for weekends/holidays
    raw = stock_df(symbol=symbol, from_date=from_date, to_date=to_date, series="EQ")
    df = raw.rename(columns={
        "DATE": "date", "OPEN": "open", "HIGH": "high",
        "LOW": "low", "CLOSE": "close", "VOLUME": "volume",
    })[["date", "open", "high", "low", "close", "volume"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True).tail(lookback_days)


def get_intraday_today(symbol: str) -> pd.DataFrame:
    raw = yf.download(f"{symbol}.NS", period="2d", interval="60m", progress=False)
    if raw.empty:
        return raw
    raw.index = raw.index.tz_convert("Asia/Kolkata")
    today = pd.Timestamp.now(tz="Asia/Kolkata").date()
    return raw[raw.index.date == today]
