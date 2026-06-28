import os

# --- Universe ---
MIN_MARKET_CAP_CR = 500              # crores; only stocks above this go into universe_500cr.csv
UNIVERSE_FILE = "universe_500cr.csv"  # refreshed every few weeks, NOT every hour (see universe.py)

# --- Trend template (Minervini conditions 1-7; RS rank is condition 8, handled separately) ---
RS_RANK_MIN = 70                      # percentile, cross-sectional across the universe

# --- VCP detection ---
ZIGZAG_THRESHOLD = 0.05               # min % move to register as a new swing leg
MIN_CONTRACTIONS = 2
MAX_CONTRACTIONS = 5
CONTRACTION_DECAY_TOLERANCE = 0.15    # leg[j+1] must be < leg[j] * (1 - this) to count as "decreasing"
LOOKBACK_DAYS = 260                   # daily bars needed for 200dma + base detection

# --- Breakout / alert ---
BREAKOUT_VOL_MULTIPLIER = 1.4         # relative volume needed to confirm a breakout
WATCHLIST_FILE = "watchlist.json"     # written daily, read hourly
ALERTED_TODAY_FILE = "alerted_today.json"  # de-dupe so each setup only alerts once per day

# --- Market hours (IST) ---
TOTAL_MARKET_MINUTES = 375            # 09:15-15:30 IST

# --- Telegram (set as repo secrets / env vars, never hardcode) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
