#!/usr/bin/env python3
import os
import sys
import time
import asyncio
import random
import traceback
from datetime import datetime, timedelta

# 正確導入
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOL, TIMEFRAME,
    BUY_SELL_THRESHOLD, ALERT_COOLDOWN,
    API_TIMEOUT, SCAN_SECONDS,
    EXCHANGES, EXCHANGE_LIST,
    get_taiwan_time, format_taiwan_time, check_config
)

# 檢查是否有multi_exchange_scanner
try:
    from multi_exchange_scanner import SimpleExchangeScanner
    HAS_SCANNER = True
except ImportError:
    HAS_SCANNER = False
    print("⚠️  multi_exchange_scanner不可用，使用模擬模式")

# 狀態追蹤
last_alert_time = {"BUY_IN_RED": 0, "SELL_IN_GREEN": 0}
alert_minute_tracker = {}
scan_count = 0
alert_count = 0
error_count = 0

def send_telegram(message):
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=API_TIMEOUT)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram錯誤: {e}")
        return False

def check_single_kline_alert(kline_data, exchange_id, minute_key):
    exchange_name = EXCHANGES.get(exchange_id, {}).get('name', exchange_id)
    
    triggered = alert_minute_tracker.get(minute_key, [])
    if exchange_id in triggered:
        return False, None, None, f"{exchange_name}已觸發"
    
    simulated_buy_ratio = random.uniform(1.0, 3.0)
    
    # 模擬kline屬性
    is_red = random.choice([True, False])
    price = random.uniform(0.2, 0.3)
    volume = random.uniform(10000, 50000)
    
    if is_red and simulated_buy_ratio > BUY_SELL_THRESHOLD:
        if minute_key not in alert_minute_tracker:
            alert_minute_tracker[minute_key] = []
        alert_minute_tracker[minute_key].append(exchange_id)
        
        alert_data = {
            "exchange": exchange_name,
            "symbol": SYMBOL,
            "price": price,
            "buy_ratio": simulated_buy_ratio,
            "kline_time": format_taiwan_time(datetime.now(), "%H:%M:%S"),
            "volume": volume
        }
        return True, "BUY_IN_RED", alert_data, f"{exchange_name}陰線買入"
    
    elif not is_red and (1/simulated_buy_ratio) > BUY_SELL_THRESHOLD:
        if minute_key not in alert_minute_tracker:
            alert_minute_tracker[minute_key] = []
        alert_minute_tracker[minute_key].append(exchange_id)
        
        alert_data = {
            "exchange": exchange_name,
            "symbol": SYMBOL,
            "price": price,
            "sell_ratio": 1/simulated_buy_ratio,
            "kline_time": format_taiwan_time(datetime.now(), "%H:%M:%S"),
            "volume": volume
        }
        return True, "SELL_IN_GREEN", alert_data, f"{exchange_name}陽線賣出"
    
    return False, None, None, "無警報"

def main():
    print("=" * 60)
    print("🚀 DUSK/USDT多交易所監控系統")
    print("=" * 60)
    print(f"📊 交易對: {SYMBOL}")
    print(f"🌍 交易所: {len(EXCHANGES)}家")
    print(f"⏰ 時間: {format_taiwan_time()}")
    print("=" * 60)
    
    # 發送啟動通知
    start_msg = f"🤖 {SYMBOL}監控系統啟動\n⏰ {format_taiwan_time()}"
    send_telegram(start_msg)
    
    # 主循環
    try:
        for i in range(10):  # 運行10次循環
            taiwan_now = get_taiwan_time()
            minute_key = taiwan_now.strftime("%Y%m%d%H%M")
            
            print(f"\n🔄 掃描 #{i+1} - {format_taiwan_time(taiwan_now, '%H:%M:%S')}")
            
            for exchange_id in EXCHANGE_LIST[:3]:  # 只測試前3個
                should_alert, alert_type, alert_data, info = check_single_kline_alert(
                    {}, exchange_id, minute_key
                )
                
                if should_alert:
                    print(f"⚠️  {info}")
                    message = f"🚨警報: {info}\n價格: ${alert_data['price']:.4f}\n時間: {format_taiwan_time()}"
                    send_telegram(message)
                    alert_count += 1
            
            time.sleep(15)  # 15秒間隔
            
    except KeyboardInterrupt:
        print("\n⏹️ 手動停止")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        traceback.print_exc()
    
    # 發送結束通知
    stop_msg = f"🛑 {SYMBOL}監控完成\n掃描: {10}次\n警報: {alert_count}次\n時間: {format_taiwan_time()}"
    send_telegram(stop_msg)
    
    print("\n" + "=" * 60)
    print(f"✅ 監控完成")
    print(f"📊 總警報: {alert_count}次")
    print(f"⏰ 結束: {format_taiwan_time()}")
    print("=" * 60)

if __name__ == "__main__":
    if not check_config():
        print("❌ 配置檢查失敗")
        sys.exit(1)
    main()
