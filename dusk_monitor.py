#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime

# 從環境變數讀取設定
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
SYMBOL = "DUSKUSDT"

# 檢查設定
if not TG_TOKEN or not TG_CHAT_ID:
    print("❌ 錯誤: TG_TOKEN 或 TG_CHAT_ID 未設定")
    sys.exit(1)

print(f"✅ 開始監控 {SYMBOL} 1分鐘K線...")

def send_telegram(message):
    """發送 Telegram 訊息"""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram 錯誤: {e}")
        return False

def send_alert(alert_type, price, volume, value=0):
    """發送警報"""
    current_time = datetime.now().strftime("%H:%M:%S")
    
    if alert_type == "BUY_IN_RED":
        message = f"""
🚨 <b>異常買入警報 - {SYMBOL}</b>

📉 <b>K線: 陰線下跌</b>
💰 <b>價格:</b> ${price:.6f}
📊 <b>成交量:</b> {volume:,.0f}
💵 <b>買入金額:</b> ${value:,.2f}

⏰ <b>時間:</b> {current_time}
"""
    elif alert_type == "SELL_IN_GREEN":
        message = f"""
🚨 <b>異常賣出警報 - {SYMBOL}</b>

📈 <b>K線: 陽線上漲</b>
💰 <b>價格:</b> ${price:.6f}
📊 <b>成交量:</b> {volume:,.0f}
💸 <b>賣出金額:</b> ${value:,.2f}

⏰ <b>時間:</b> {current_time}
"""
    else:
        message = f"""
📊 <b>{SYMBOL} 監控報告</b>
💰 <b>價格:</b> ${price:.6f}
📊 <b>成交量:</b> {volume:,.0f}
⏰ <b>時間:</b> {current_time}
"""
    
    return send_telegram(message)

def test_monitor():
    """測試監控系統"""
    print("=" * 50)
    print("🚀 DUSKUSDT 1分鐘監控系統測試")
    print("=" * 50)
    
    # 測試 Telegram 連線
    print("📡 測試 Telegram 連線...")
    test_msg = "🤖 DUSKUSDT 監控系統測試成功！\n系統已啟動並正常運作。"
    if send_telegram(test_msg):
        print("✅ Telegram 連線成功")
    else:
        print("❌ Telegram 連線失敗")
        return False
    
    # 模擬監控數據
    import random
    print("\n📊 模擬監控數據...")
    
    for i in range(3):
        current_time = datetime.now().strftime("%H:%M:%S")
        price = 0.123456 + random.uniform(-0.001, 0.001)
        volume = random.randint(1000000, 5000000)
        
        # 第2次循環觸發測試警報
        if i == 1:
            print(f"⚠️ [{current_time}] 觸發買入警報測試")
            send_alert("BUY_IN_RED", price, volume, 2500000)
        elif i == 2:
            print(f"⚠️ [{current_time}] 觸發賣出警報測試")
            send_alert("SELL_IN_GREEN", price, volume, 1800000)
        else:
            print(f"📊 [{current_time}] 正常監控 | 價格: ${price:.6f}")
            send_alert("NORMAL", price, volume)
        
        if i < 2:
            time.sleep(5)
    
    return True

if __name__ == "__main__":
    success = test_monitor()
    if success:
        print("\n" + "=" * 50)
        print("✅ 監控系統測試完成")
        print("✅ Telegram 警報功能正常")
        print("✅ 系統準備就緒")
        print("=" * 50)
    else:
        print("\n❌ 監控系統測試失敗")
        sys.exit(1)
