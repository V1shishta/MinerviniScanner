"""
OHLCV data access.

Daily bars (bulk): yfinance batch download, chunked across all symbols in
one shot. Hits Yahoo Finance, not NSE directly -- so GitHub Actions' cloud
IPs aren't blocked. jugaad-data's stock_df is NOT used here because it
makes one per-symbol HTTP call to nseindia.com, which hangs/times out from
cloud IPs causing the watchlist build to run for 60 minutes and produce
nothing.

Intraday bars: yfinance 60m -- same reasoning, no NSE dependency.
"""
import pandas as pd
import yfinance as yf

CHUNK_SIZE = 100   # yfinance handles up to ~200 per call; 100 is conservative


def get_daily_history_batch(symbols: list[str], lookback_days: int = 260) -> dict[str, pd.DataFrame]:
    """
    Returns {symbol: DataFrame} for every symbol that came back with
    enough bars. Symbols that yfinance can't resolve or that have too
    few bars are silently dropped -- the caller handles missing keys.
    """
    all_data: dict[str, pd.DataFrame] = {}

    for i in range(0, len(symbols), CHUNK_SIZE):
        chunk = symbols[i: i + CHUNK_SIZE]
        tickers = [f"{s}.NS" for s in chunk]

        try:
            raw = yf.download(
                tickers,
                period="1y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            print(f"  yf.download chunk {i}–{i+CHUNK_SIZE} failed: {e}")
            continue

        if raw.empty:
            continue

        # yfinance returns a MultiIndex (field, ticker) when >1 ticker
        for sym, ticker in zip(chunk, tickers):
            try:
                if len(tickers) == 1:
                    df = raw.copy()
                else:
                    df = raw.xs(ticker, axis=1, level=1).copy()

                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df.columns = ["open", "high", "low", "close", "volume"]
                df.index = pd.to_datetime(df.index)
                df.index.name = "date"
                df = df.dropna(subset=["close"]).reset_index()

                if len(df) >= 210:   # need 200 bars for MA200, a little extra
                    all_data[sym] = df.tail(lookback_days).reset_index(drop=True)
            except Exception:
                pass

        print(f"  batch {i // CHUNK_SIZE + 1}: {len(chunk)} symbols fetched, "
              f"{sum(1 for s in chunk if s in all_data)} usable so far")

    return all_data


def get_intraday_today(symbol: str) -> pd.DataFrame:
    raw = yf.download(f"{symbol}.NS", period="2d", interval="60m",
                      progress=False, auto_adjust=True)
    if raw.empty:
        return raw
    raw.index = raw.index.tz_convert("Asia/Kolkata")
    today = pd.Timestamp.now(tz="Asia/Kolkata").date()
    return raw[raw.index.date == today]
