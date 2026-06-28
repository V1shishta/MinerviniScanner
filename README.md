# VCP breakout scanner (NSE, >₹500cr market cap)

Daily watchlist build (trend template + VCP detection) + hourly breakout
check + Telegram alert. Deployed on GitHub Actions, same pattern as the
gap-fill scanner.

## How it's split (and why)

- **`universe.py`** -- run every few weeks, not part of the cron pipeline.
  Builds `universe_500cr.csv` (symbol, market_cap_cr). If you have
  Bloomberg access, a `BDP(<ticker> Equity, CUR_MKT_CAP)` pull exported
  to that same two-column CSV is more reliable than this script's
  per-symbol yfinance loop -- use whichever, the rest of the pipeline
  only cares about the CSV.
- **`build_watchlist.py`** -- runs once daily before market open. Applies
  the 8-condition trend template + cross-sectional RS rank + VCP/contraction
  detection to the universe, writes `watchlist.json` (symbol, pivot,
  RS rank, contraction %s, volume baseline) for setups that are valid
  but **haven't broken out yet**.
- **`hourly_scan.py`** -- runs hourly during market hours. Only checks
  symbols already on the watchlist (fast) against live intraday
  price/volume. Sends a Telegram alert on a fresh breakout and writes
  `alerted_today.json` so the same setup doesn't fire twice in one day.

## One-time setup

```bash
pip install -r requirements.txt
python universe.py              # builds universe_500cr.csv (or supply your own)
```

**Telegram bot:**
1. Message **@BotFather** -> `/newbot` -> follow prompts -> copy the token.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<token>/getUpdates` in a browser,
   read off `"chat":{"id": ...}`.
4. In your GitHub repo: Settings -> Secrets and variables -> Actions ->
   add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

Push to GitHub with Actions enabled. The two workflows in
`.github/workflows/` take over from there.

## Tested

`test_vcp_logic.py` runs the zigzag + contraction + volume logic against
a synthetic 3-contraction VCP series and a random-noise series (no
network needed). Run it after any change to `vcp_detect.py`:

```bash
python test_vcp_logic.py
```

## Tunable knobs (`config.py`)

| Setting | What it controls |
|---|---|
| `ZIGZAG_THRESHOLD` | Min % move to register as a swing leg. Lower = more, noisier legs. |
| `CONTRACTION_DECAY_TOLERANCE` | How strictly each leg must shrink vs. the last. |
| `MIN_CONTRACTIONS` / `MAX_CONTRACTIONS` | How many legs count as a base. |
| `RS_RANK_MIN` | Minervini's condition 8 cutoff (70, ideally 80-90). |
| `BREAKOUT_VOL_MULTIPLIER` | Relative volume needed to confirm a breakout (1.4-1.5 typical). |

## Known gaps (read before trusting this with real money)

- **Market cap** via yfinance is occasionally flaky/wrong. Sanity check
  `universe_500cr.csv` against a couple of known names before relying on it.
- **No NSE holiday calendar.** On holidays the scanner just finds no
  fresh data and skips -- it won't crash, but it'll waste a few cron
  cycles. Add a holiday list if that bothers you.
- **GitHub Actions schedules get disabled after ~60 days of repo
  inactivity** -- a no-op commit periodically keeps it alive (you've
  likely hit this already with the gap-fill scanner).
- **This only detects and alerts.** It does not place orders, size
  positions, or manage stops -- that's deliberately left to you.
- The zigzag/contraction thresholds are heuristic by nature (this is a
  visual pattern being forced into rules). Expect to tune them after
  watching real output for a couple of weeks.
