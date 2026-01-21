import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_alert(self, alert_type, data):
        symbol = data.get('symbol', 'DUSKUSDT')
        price = data.get('price', 0)
        volume = data.get('volume', 0)
        buy_value = data.get('buy_value', 0)
        
        if alert_type == "BUY_IN_RED":
            message = f"""
🚨 異常買入警報 - {symbol}
📉 K線: 陰線下跌
💰 價格: ${price:.6f}
💵 買入金額: ${buy_value:,.2f}
🕐 時間: {time.strftime('%H:%M:%S')}
"""
        elif alert_type == "SELL_IN_GREEN":
            message = f"""
🚨 異常賣出警報 - {symbol}
📈 K線: 陽線上漲
💰 價格: ${price:.6f}
💸 賣出金額: ${data.get('sell_value', 0):,.2f}
🕐 時間: {time.strftime('%H:%M:%S')}
"""
        
        return self.send_message(message)
    
    def send_message(self, text):
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Telegram 發送失敗: {e}")
            return False

bot = TelegramBot()
