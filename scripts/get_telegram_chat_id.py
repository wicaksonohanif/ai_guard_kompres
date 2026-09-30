"""Print recent Telegram updates and chat IDs for the configured bot.

Usage:
1. Put TELEGRAM_BOT_TOKEN in .env.
2. Send /start (or any message) to your bot in Telegram.
3. Run: python scripts/get_telegram_chat_id.py
"""
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    raise SystemExit("TELEGRAM_BOT_TOKEN belum ada di .env")

url = f"https://api.telegram.org/bot{token}/getUpdates"
try:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
except requests.RequestException as e:
    raise SystemExit(f"Gagal menghubungi Telegram: {e}")

if not data.get("ok"):
    raise SystemExit(f"Telegram API error: {data}")

updates = data.get("result", [])
if not updates:
    print("Belum ada update. Kirim /start ke bot Telegram dulu, lalu jalankan script ini lagi.")
    raise SystemExit(0)

seen = set()
for update in updates:
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id in seen:
        continue
    seen.add(chat_id)
    print(f"chat_id={chat_id} | type={chat.get('type')} | name={chat.get('title') or chat.get('first_name','')}")
