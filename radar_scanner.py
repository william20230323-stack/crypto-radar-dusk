#!/usr/bin/env python3
"""
DUSKUSDT 雷達檢測系統
檢測幣種：DUSKUSDT
"""

import os
import time
import requests
from datetime import datetime

# Telegram 通知
def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    
    if not token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except:
        return False

# 價格檢測函數
def check_price(symbol):
    """檢測加密貨幣價格"""
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # 這裡添加真實的 API 調用
    # 目前為模擬數據
    import random
    price = round(random.uniform(0.12, 0.13), 4)
    change = round(random.uniform(-3, 3), 2)
    
    return {
        "symbol": symbol,
        "price": price,
        "change": change,
        "time": current_time
    }

# 主程序
def main():
    print("🚀 DUSKUSDT 雷達系統啟動")
    
    symbol = os.getenv('TRADE_SYMBOL', 'DUSKUSDT')
    scan_count = 0
    
    while True:
        scan_count += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        print(f"[{current_time}] 第{scan_count}次掃描 {symbol}")
        
        # 檢測價格
        data = check_price(symbol)
        
        # 每3次掃描發送報告
        if scan_count % 3 == 0:
            message = f"""{symbol} 價格更新
價格: {data['price']}
漲跌: {data['change']}%
時間: {data['time']}
掃描次數: {scan_count}"""
            send_telegram(message)
        
        # 等待 15 分鐘
        for i in range(900):
            if i % 300 == 0 and i > 0:
                print(f"等待中... {i//60}分鐘")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("程式結束")
