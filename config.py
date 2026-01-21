import os

# Telegram 設定
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# 交易對設定
SYMBOL = "DUSKUSDT"
TIMEFRAME = "1m"
CHECK_INTERVAL = 60

# 警報條件
VOLUME_THRESHOLD = 2.5
PRICE_CHANGE_THRESHOLD = 1.0

def check_config():
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ TG_TOKEN 未設定")
    if not TELEGRAM_CHAT_ID:
        print("⚠️ TG_CHAT_ID 未設定")
    print(f"✅ 監控 {SYMBOL} {TIMEFRAME} K線")
