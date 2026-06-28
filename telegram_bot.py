"""
Minimal Telegram alert sender.

Setup:
  1. Message @BotFather on Telegram, send /newbot, follow the prompts.
     You'll get a token that looks like 123456789:AAH...  -> TELEGRAM_BOT_TOKEN
  2. Send any message to your new bot (it stays silent, that's fine).
  3. Visit https://api.telegram.org/bot<token>/getUpdates in a browser
     and read off "chat":{"id": ...} -> TELEGRAM_CHAT_ID
  4. Store both as GitHub repo secrets (Settings -> Secrets and variables
     -> Actions). Never commit them.
"""
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_alert(symbol: str, price: float, pivot: float, rel_vol: float, rs_rank: float):
    msg = (
        f"\U0001F514 VCP breakout: {symbol}\n"
        f"Price: {price:.2f}  |  Pivot: {pivot:.2f}\n"
        f"Relative volume: {rel_vol:.2f}x  |  RS rank: {rs_rank:.0f}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    if not resp.ok:
        print(f"Telegram send failed: {resp.text}")
