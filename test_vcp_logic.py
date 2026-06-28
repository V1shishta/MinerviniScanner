import numpy as np
import pandas as pd
from vcp_detect import detect_vcp, zigzag

def make_vcp_series():
    """Synthetic daily bars: uptrend -> 3 decreasing contractions -> breakout."""
    dates = pd.bdate_range("2025-01-01", periods=240)
    closes = []
    base = 100
    # prior uptrend
    closes += list(np.linspace(base, 150, 60))
    # T1: -28%
    closes += list(np.linspace(150, 108, 15))
    closes += list(np.linspace(108, 148, 15))
    # T2: -15%
    closes += list(np.linspace(148, 125.8, 12))
    closes += list(np.linspace(125.8, 149, 12))
    # T3: -7%
    closes += list(np.linspace(149, 138.6, 10))
    closes += list(np.linspace(138.6, 151, 10))
    # tight coil + breakout
    closes += list(np.linspace(151, 149.5, 8))
    closes += list(np.linspace(149.5, 175, 98))
    closes = np.array(closes[:240])

    high = closes * 1.01
    low = closes * 0.99
    # volume: high during T1, decaying through T2/T3, spike on breakout
    volume = np.concatenate([
        np.full(60, 500_000),
        np.full(30, 800_000),   # T1 leg (high volume selloff)
        np.full(24, 500_000),   # T2 leg
        np.full(20, 300_000),   # T3 leg
        np.full(8, 150_000),    # tight coil, volume dry-up
        np.full(98, 200_000),
    ])[:240]
    volume[-10:] = 900_000  # breakout volume surge

    return pd.DataFrame({"date": dates, "open": closes, "high": high, "low": low,
                          "close": closes, "volume": volume})

def make_noise_series():
    dates = pd.bdate_range("2025-01-01", periods=240)
    rng = np.random.default_rng(42)
    closes = 100 + np.cumsum(rng.normal(0, 1.5, 240))
    closes = np.clip(closes, 50, None)
    high = closes * 1.01
    low = closes * 0.99
    volume = rng.integers(100_000, 900_000, 240)
    return pd.DataFrame({"date": dates, "open": closes, "high": high, "low": low,
                          "close": closes, "volume": volume})

vcp_df_full = make_vcp_series()

# build_watchlist.py would run BEFORE the breakout -- truncate to the day
# the tight coil finishes, before any breakout candles exist.
PRE_BREAKOUT_CUTOFF = 142
vcp_df = vcp_df_full.iloc[:PRE_BREAKOUT_CUTOFF].reset_index(drop=True)

swings = zigzag(vcp_df)
print(f"Synthetic VCP series (pre-breakout, {len(vcp_df)} bars): {len(swings)} swings detected")
for s in swings:
    print(f"  {'HIGH' if s.is_high else 'LOW '} idx={s.idx:3d} price={s.price:7.2f} date={s.date.date()}")

is_valid, pivot, contractions, avg_vol_50 = detect_vcp(vcp_df)
print(f"\ndetect_vcp on pre-breakout series -> valid={is_valid}, pivot={pivot}, contractions%={contractions}, avg_vol_50={avg_vol_50}")
assert is_valid, "FAIL: should have detected a valid VCP on the constructed series"
assert pivot is not None and 148 <= pivot <= 152, f"FAIL: pivot {pivot} not near expected ~150"
print("PASS: valid VCP detected with sane pivot, before any breakout occurred")

noise_df = make_noise_series()
is_valid_n, pivot_n, contractions_n, _ = detect_vcp(noise_df)
print(f"\ndetect_vcp on random noise series -> valid={is_valid_n}, contractions%={contractions_n}")
assert not is_valid_n, "FAIL: should NOT detect a valid VCP on pure random noise"
print("PASS: random noise correctly rejected")

# Breakout check arithmetic sanity (mirrors hourly_scan.py, run on LIVE
# data separate from the watchlist build -- never on data the watchlist
# build already saw).
live_price = float(vcp_df_full["close"].iloc[-1])
print(f"\nLive price after breakout: {live_price:.2f} vs pivot {pivot:.2f} -> breakout={live_price > pivot}")
assert live_price > pivot, "FAIL: synthetic post-cutoff series should have broken out above pivot"
print("PASS: breakout condition holds on live data after the watchlist's pivot was set")
