"""
Swing detection (ZigZag) + contraction validation + pivot calculation.

This is the heuristic part of the whole system -- ZIGZAG_THRESHOLD and
CONTRACTION_DECAY_TOLERANCE in config.py are the two knobs that decide
how strict "decreasing contractions" means. Tighten them if you're
getting too many marginal setups, loosen if you're missing obvious ones.
"""
from dataclasses import dataclass

import pandas as pd

from config import (
    ZIGZAG_THRESHOLD,
    MIN_CONTRACTIONS,
    MAX_CONTRACTIONS,
    CONTRACTION_DECAY_TOLERANCE,
)


@dataclass
class Swing:
    idx: int
    date: pd.Timestamp
    price: float
    is_high: bool


def zigzag(daily: pd.DataFrame, threshold: float = ZIGZAG_THRESHOLD) -> list[Swing]:
    highs, lows = daily["high"], daily["low"]
    swings: list[Swing] = []
    direction = None  # None -> "up" -> "down" -> "up" ...
    extreme_idx = 0
    extreme_price = highs.iloc[0]

    for i in range(1, len(daily)):
        h, l = highs.iloc[i], lows.iloc[i]

        if direction in (None, "up"):
            if h > extreme_price:
                extreme_price, extreme_idx = h, i
            elif l < extreme_price * (1 - threshold):
                swings.append(Swing(extreme_idx, daily["date"].iloc[extreme_idx], extreme_price, True))
                direction, extreme_price, extreme_idx = "down", l, i
                continue

        if direction == "down":
            if l < extreme_price:
                extreme_price, extreme_idx = l, i
            elif h > extreme_price * (1 + threshold):
                swings.append(Swing(extreme_idx, daily["date"].iloc[extreme_idx], extreme_price, False))
                direction, extreme_price, extreme_idx = "up", h, i

    return swings


def detect_vcp(daily: pd.DataFrame):
    """Returns (is_valid, pivot_price, contractions_pct, avg_vol_50).
    If no valid pattern is found, returns (False, None, None, None)."""
    swings = zigzag(daily)
    if len(swings) < MIN_CONTRACTIONS * 2:
        return False, None, None, None

    recent = swings[-(MAX_CONTRACTIONS * 2):]
    highs = [s for s in recent if s.is_high]
    lows = [s for s in recent if not s.is_high]
    legs = list(zip(highs, lows))[-MAX_CONTRACTIONS:]
    if len(legs) < MIN_CONTRACTIONS:
        return False, None, None, None

    contractions = [(h.price - l.price) / h.price for h, l in legs]
    decreasing = all(
        contractions[i + 1] < contractions[i] * (1 - CONTRACTION_DECAY_TOLERANCE)
        for i in range(len(contractions) - 1)
    )
    if not decreasing:
        return False, None, None, None

    vol_legs = [
        daily.loc[(daily["date"] >= h.date) & (daily["date"] <= l.date), "volume"].mean()
        for h, l in legs
    ]
    # Volume should contract alongside price, leg over leg -- this is more
    # robust than comparing the final leg to a trailing 50d average, since
    # that average can itself sit entirely inside a long base and give a
    # misleadingly strict (or lenient) threshold depending on where it lands.
    vol_decreasing = all(vol_legs[i + 1] < vol_legs[i] for i in range(len(vol_legs) - 1))
    if not vol_decreasing:
        return False, None, None, None

    pivot = max(h.price for h, _ in legs)
    avg_vol_50 = daily["volume"].tail(50).mean()
    return True, float(pivot), [round(float(c) * 100, 1) for c in contractions], float(avg_vol_50)
