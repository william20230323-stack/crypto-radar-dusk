#!/usr/bin/env python3
import os
import sys
import time
import asyncio
import random
import traceback
from datetime import datetime, timedelta

from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOL, TIMEFRAME,
    CHECK_INTERVAL, BUY_SELL_THRESHOLD, ALERT_COOLDOWN,
    API_TIMEOUT, MAX_RETRIES, SCAN_SECONDS,
    EXCHANGES, EXCHANGE_LIST,
    get_taiwan_time, format_taiwan_time, TAIWAN_TZ, check_config
)
from multi_exchange_scanner import SimpleExchangeScanner, SimpleKlineData

# 狀態追蹤
last_alert_time = {"BUY_IN_RED": 0, "SELL_IN_GREEN": 0}
alert_minute_tracker = {}  # 格式: {"YYYYMMDDHHMM": [exchange1_id, exchange2_id]}
scan_count = 0
alert_count = 0
error_count = 0

def send_telegram(message):
    """發送 Telegram 訊息（臨時函數，稍後會被 telegram_bot.py 替換）"""
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
        print(f"❌ Telegram 錯誤: {type(e).__name__}: {e}")
        return False

def can_send_alert(alert_type):
    """檢查是否可以發送警報（冷卻時間）"""
    current_time = time.time()
    last_time = last_alert_time.get(alert_type, 0)
    
    if current_time - last_time < ALERT_COOLDOWN:
        remaining = ALERT_COOLDOWN - (current_time - last_time)
        print(f"⏳ {alert_type} 警報在冷卻中，還需 {remaining:.0f}秒")
        return False
    
    last_alert_time[alert_type] = current_time
    return True

def get_current_minute_key():
    """獲取當前分鐘的鍵值（用於警報去重）"""
    taiwan_now = get_taiwan_time()
    return taiwan_now.strftime("%Y%m%d%H%M")

def check_single_kline_alert(kline, exchange_id, minute_key):
    """
    檢查單一K線的警報條件
    返回: (should_alert, alert_type, alert_data, message)
    """
    exchange_name = EXCHANGES[exchange_id]['name']
    
    # 檢查是否已經在這分鐘內觸發過
    triggered = alert_minute_tracker.get(minute_key, [])
    if exchange_id in triggered:
        return False, None, None, f"{exchange_name} 本分鐘已觸發過警報"
    
    # 模擬買賣數據
    simulated_buy_ratio = random.uniform(1.0, 3.0)
    
    # 條件1: 陰線但大量買入（買/賣比 > 1.8）
    if kline.is_red and simulated_buy_ratio > BUY_SELL_THRESHOLD:
        if minute_key not in alert_minute_tracker:
            alert_minute_tracker[minute_key] = []
        alert_minute_tracker[minute_key].append(exchange_id)
        
        alert_data = {
            "exchange": exchange_name,
            "symbol": SYMBOL,
            "price": kline.close,
            "buy_ratio": simulated_buy_ratio,
            "kline_time": format_taiwan_time(kline.fetch_time, "%H:%M:%S"),
            "volume": kline.volume
        }
        
        return True, "BUY_IN_RED", alert_data, f"{exchange_name} 陰線大量買入"
    
    # 條件2: 陽線但大量賣出（賣/買比 > 1.8）
    elif kline.is_green and (1/simulated_buy_ratio) > BUY_SELL_THRESHOLD:
        if minute_key not in alert_minute_tracker:
            alert_minute_tracker[minute_key] = []
        alert_minute_tracker[minute_key].append(exchange_id)
        
        alert_data = {
            "exchange": exchange_name,
            "symbol": SYMBOL,
            "price": kline.close,
            "sell_ratio": 1/simulated_buy_ratio,
            "kline_time": format_taiwan_time(kline.fetch_time, "%H:%M:%S"),
            "volume": kline.volume
        }
        
        return True, "SELL_IN_GREEN", alert_data, f"{exchange_name} 陽線大量賣出"
    
    return False, None, None, "無警報條件"

def create_alert_message(alert_type, alert_data, minute_key):
    """創建警報訊息"""
    taiwan_now = get_taiwan_time()
    current_time_str = format_taiwan_time(taiwan_now, "%H:%M:%S")
    
    if alert_type == "BUY_IN_RED":
        message = f"""
🚨 <b>異常買入警報 - {alert_data['symbol']}</b>

🏦 <b>交易所:</b> {alert_data['exchange']}
📉 <b>K線類型:</b> 陰線下跌
💰 <b>當前價格:</b> ${alert_data['price']:.6f}
📊 <b>買入比率:</b> {alert_data['buy_ratio']:.2f}
📦 <b>成交量:</b> {alert_data['volume']:,.0f}

⚠️ <b>檢測到陰線中出現異常買單！</b>

⏰ <b>數據時間:</b> {alert_data['kline_time']}
📡 <b>警報時間:</b> {current_time_str} (台灣時間)
🌍 <b>多交易所監控系統</b>
"""
    elif alert_type == "SELL_IN_GREEN":
        message = f"""
🚨 <b>異常賣出警報 - {alert_data['symbol']}</b>

🏦 <b>交易所:</b> {alert_data['exchange']}
📈 <b>K線類型:</b> 陽線上漲
💰 <b>當前價格:</b> ${alert_data['price']:.6f}
📊 <b>賣出比率:</b> {alert_data['sell_ratio']:.2f}
📦 <b>成交量:</b> {alert_data['volume']:,.0f}

⚠️ <b>檢測到陽線中出現異常賣單！</b>

⏰ <b>數據時間:</b> {alert_data['kline_time']}
📡 <b>警報時間:</b> {current_time_str} (台灣時間)
🌍 <b>多交易所監控系統</b>
"""
    else:
        message = ""
    
    return message

def print_banner():
    """顯示啟動橫幅"""
    taiwan_now = get_taiwan_time()
    
    print("=" * 70)
    print("🚀 DUSK/USDT 多交易所實時監控系統")
    print("=" * 70)
    print(f"📊 交易對: {SYMBOL}")
    print(f"⏰ 時間框架: {TIMEFRAME}")
    print(f"🔄 檢查間隔: 每15秒掃描一次")
    print(f"⏱️  掃描時間點: 台灣時間的 {SCAN_SECONDS} 秒")
    print(f"🔔 通知模式: 僅異常時發送")
    print(f"⏳ 警報冷卻: {ALERT_COOLDOWN}秒")
    print(f"🌍 交易所數量: {len(EXCHANGES)} 家")
    print("=" * 70)
    print(f"📈 警報閾值設定:")
    print(f"   買賣比率: >{BUY_SELL_THRESHOLD:.1f}")
    print("=" * 70)
    print(f"🌐 監控交易所:")
    for i, exchange_id in enumerate(EXCHANGE_LIST, 1):
        print(f"   {i}. {EXCHANGES[exchange_id]['name']}")
    print("=" * 70)
    print(f"⏰ 當前台灣時間: {format_taiwan_time(taiwan_now)}")
    print("=" * 70)

def wait_until_next_scan_point():
    """等待到下一個掃描時間點（00、15、30、45秒）"""
    taiwan_now = get_taiwan_time()
    current_second = taiwan_now.second
    
    next_seconds = [s for s in SCAN_SECONDS if s > current_second]
    
    if next_seconds:
        seconds_to_wait = next_seconds[0] - current_second
    else:
        seconds_to_wait = 60 - current_second + SCAN_SECONDS[0]
    
    if seconds_to_wait < 1:
        seconds_to_wait += 60
    
    next_time = (taiwan_now + timedelta(seconds=seconds_to_wait)).strftime("%H:%M:%S")
    print(f"⏳ 等待 {seconds_to_wait}秒 直到 {next_time} (台灣時間)")
    
    if seconds_to_wait > 0:
        time.sleep(seconds_to_wait)
    
    time.sleep(0.1)

async def single_scan_cycle(scanner):
    """單次掃描循環"""
    global scan_count, alert_count, error_count
    
    taiwan_now = get_taiwan_time()
    minute_key = get_current_minute_key()
    
    print(f"\n{'='*60}")
    print(f"🔄 掃描 #{scan_count + 1} - {format_taiwan_time(taiwan_now, '%H:%M:%S')}")
    print(f"📅 分鐘鍵值: {minute_key}")
    print(f"{'='*60}")
    
    try:
        kline_data = await scanner.scan_all_exchanges()
        scan_count += 1
        
        if not kline_data:
            error_count += 1
            print("❌ 所有交易所掃描失敗")
            return
        
        for exchange_id, kline in kline_data.items():
            should_alert, alert_type, alert_data, info = check_single_kline_alert(
                kline, exchange_id, minute_key
            )
            
            if should_alert:
                print(f"⚠️  {info}")
                
                if can_send_alert(alert_type):
                    alert_message = create_alert_message(alert_type, alert_data, minute_key)
                    
                    if send_telegram(alert_message):
                        alert_count += 1
                        print(f"✅ 警報發送成功 (總計: {alert_count})")
                    else:
                        print("❌ 警報發送失敗")
                else:
                    print(f"⏳ 警報跳過（冷卻中）")
            else:
                if "debug" in sys.argv:
                    print(f"📊 {EXCHANGES[exchange_id]['name']}: {info}")
        
        print(f"\n📈 本次掃描:")
        print(f"   成功交易所: {len(kline_data)}/{len(EXCHANGES)}")
        print(f"   觸發警報: {len([x for x in alert_minute_tracker.get(minute_key, [])])}")
        
    except Exception as e:
        error_count += 1
        print(f"❌ 掃描錯誤: {type(e).__name__}: {e}")
        traceback.print_exc()

async def real_time_monitor():
    """實時監控主函數"""
    print_banner()
    
    if not check_config():
        print("❌ 配置檢查失敗，停止監控")
        return False
    
    taiwan_now = get_taiwan_time()
    start_msg = f"""
🤖 <b>{SYMBOL} 多交易所監控系統啟動</b>

✅ 系統已啟動並開始實時監控
📊 交易對: {SYMBOL}
⏰ 時間框架: {TIMEFRAME}
🔄 檢查間隔: 每15秒掃描一次
🔔 通知模式: 僅異常時發送
⏱️  警報冷卻: {ALERT_COOLDOWN}秒
🌍 交易所數量: {len(EXCHANGES)} 家

📈 <b>警報條件:</b>
1. 陰線但大量買入（買/賣比 > {BUY_SELL_THRESHOLD}）
2. 陽線但大量賣出（賣/買比 > {BUY_SELL_THRESHOLD}）

⏰ <b>啟動時間:</b> {format_taiwan_time(taiwan_now)} (台灣時間)
"""
    send_telegram(start_msg)
    print("✅ 啟動通知已發送")
    
    async with SimpleExchangeScanner() as scanner:
        try:
            while True:
                await single_scan_cycle(scanner)
                
                if scan_count % 10 == 0:
                    print(f"\n📊 系統統計:")
                    print(f"   總掃描次數: {scan_count}")
                    print(f"   總警報次數: {alert_count}")
                    print(f"   總錯誤次數: {error_count}")
                    success_rate = ((scan_count * len(EXCHANGES) - error_count) / 
                                   (scan_count * len(EXCHANGES)) * 100) if scan_count > 0 else 0
                    print(f"   平均成功率: {success_rate:.1f}%")
                    print(f"   運行時間: {timedelta(seconds=scan_count * 15)}")
                    print(f"   當前台灣時間: {format_taiwan_time()}")
                
                wait_until_next_scan_point()
                
        except KeyboardInterrupt:
            print("\n\n⏹️  監控手動停止")
        except Exception as e:
            print(f"\n❌ 監控錯誤: {type(e).__name__}: {e}")
            traceback.print_exc()
            
            error_msg = f"""
⚠️ <b>{SYMBOL} 監控系統錯誤</b>

❌ 系統發生錯誤: {str(e)[:100]}
⏰ 錯誤時間: {format_taiwan_time()} (台灣時間)

系統將嘗試繼續運行...
"""
            send_telegram(error_msg)
            
            print("⏳ 等待30秒後繼續...")
            time.sleep(30)
            return True
    
    return True

async def main_async():
    """異步主函數"""
    print("🚀 啟動多交易所實時監控系統...")
    print(f"⏰ 當前台灣時間: {format_taiwan_time()}")
    
    max_restarts = 3
    restarts = 0
    
    while restarts < max_restarts:
        try:
            success = await real_time_monitor()
            if success:
                return True
            else:
                restarts += 1
                print(f"🔄 嘗試重啟 ({restarts}/{max_restarts})...")
                time.sleep(30)
        except Exception as e:
            print(f"❌ 系統嚴重錯誤: {type(e).__name__}: {e}")
            restarts += 1
            if restarts < max_restarts:
                print(f"🔄 等待後重啟 ({restarts}/{max_restarts})...")
                time.sleep(30)
    
    print("❌ 達到最大重啟次數，停止系統")
    return False

def main():
    """主入口函數（兼容同步調用）"""
    required_vars = ["TG_TOKEN", "TG_CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少環境變數: {', '.join(missing_vars)}")
        sys.exit(1)
    
    success = asyncio.run(main_async())
    
    taiwan_now = get_taiwan_time()
    stop_msg = f"""
🛑 <b>{SYMBOL} 多交易所監控系統停止</b>

✅ 監控任務已完成
📊 總掃描次數: {scan_count}
🚨 總警報次數: {alert_count}
⏰ 運行時間: {timedelta(seconds=scan_count * 15)}

⏰ <b>停止時間:</b> {format_taiwan_time(taiwan_now)} (台灣時間)
"""
    send_telegram(stop_msg)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 監控系統執行完成")
    else:
        print("❌ 監控系統執行失敗")
    print(f"⏰ 結束時間: {format_taiwan_time()}")
    print("=" * 70)

if __name__ == "__main__":
    main()
