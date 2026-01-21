#!/usr/bin/env python3
"""
幣安 DUSKUSDT 智能監控系統 - 防封鎖版
專為長時間運行優化，避免 GitHub 封鎖
"""

import os
import time
import random
import requests
import json
from datetime import datetime, timedelta
from binance.client import Client

# ========== 配置參數 ==========
SYMBOL = "DUSKUSDT"
TIMEFRAME = "1m"
ALERT_VOLUME_RATIO = 3.0  # 成交量異常閾值
CHECK_INTERVAL = random.randint(55, 65)  # 隨機55-65秒間隔

# 全局狀態變量
last_alert_time = {}
alert_cooldown = 300  # 相同警報冷卻時間5分鐘

# ========== Telegram 通知 ==========
def send_telegram_alert(alert_type, data, is_test=False):
    """發送 Telegram 警報（帶冷卻機制）"""
    # 冷卻檢查
    current_time = time.time()
    if alert_type in last_alert_time:
        time_since_last = current_time - last_alert_time[alert_type]
        if time_since_last < alert_cooldown:
            print(f"⏳ {alert_type} 警報冷卻中 ({int(alert_cooldown - time_since_last)}秒)")
            return False
    
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 缺少 Telegram 配置")
        return False
    
    try:
        # 根據警報類型生成訊息
        if alert_type == "BUY_PRESSURE":
            message = f"""🚨 <b>大量買盤偵測 - DUSKUSDT</b>

📉 狀態：陰線下跌中出現大量買單
💰 價格：{data['price']} USDT
📊 成交量：{data['volume']:.0f} DUSK
⚡ 買單比例：{data['buy_ratio']:.1%}
🕒 時間：{data['time']}

🔍 可能為：機構吸籌 / 大戶抄底
⚠️ 注意：可能是底部反轉信號"""
            
        elif alert_type == "SELL_PRESSURE":
            message = f"""🚨 <b>大量賣盤出逃 - DUSKUSDT</b>

📈 狀態：陽線上漲中出現大量賣單
💰 價格：{data['price']} USDT
📊 成交量：{data['volume']:.0f} DUSK
⚡ 賣單比例：{data['sell_ratio']:.1%}
🕒 時間：{data['time']}

🔍 可能為：獲利了結 / 主力出貨
⚠️ 注意：可能是頂部反轉信號"""
        
        elif alert_type == "SYSTEM_START":
            monitor_mode = os.getenv('MONITOR_MODE', 'main')
            message = f"""✅ <b>DUSKUSDT 監控系統啟動</b>

🔄 模式：{monitor_mode}系統
📊 交易對：{SYMBOL}
⏰ 啟動時間：{data['time']}
📡 監控間隔：{CHECK_INTERVAL}秒
🎯 警報條件：成交量>{ALERT_VOLUME_RATIO}倍 + 買賣比例>60%

💡 系統開始24/7監控..."""
        
        else:
            message = f"📊 {data.get('message', '系統更新')}"
        
        # 如果是測試模式，不實際發送
        if is_test:
            print(f"[TEST] Telegram 訊息: {message[:100]}...")
            return True
        
        # 發送通知
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        response = requests.post(url, json=payload, timeout=8)
        
        if response.status_code == 200:
            print(f"✅ {alert_type} 警報發送成功")
            last_alert_time[alert_type] = current_time  # 更新冷卻時間
            return True
        else:
            print(f"❌ 警報發送失敗: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram 錯誤: {str(e)[:100]}")
        return False

# ========== 輕量級數據獲取 ==========
def get_market_data_light():
    """輕量級數據獲取，最小化 API 調用"""
    try:
        client = Client()
        
        # 只獲取必要數據
        # 1. 最新K線（限1條）
        klines = client.get_klines(
            symbol=SYMBOL,
            interval=TIMEFRAME,
            limit=2  # 只取2條
        )
        
        if len(klines) < 2:
            return None
        
        latest = klines[-1]
        previous = klines[-2]
        
        # 2. 當前價格
        ticker = client.get_symbol_ticker(symbol=SYMBOL)
        
        # 3. 訂單簿（限5檔）
        depth = client.get_order_book(symbol=SYMBOL, limit=5)
        
        return {
            'kline': {
                'open': float(latest[1]),
                'high': float(latest[2]),
                'low': float(latest[3]),
                'close': float(latest[4]),
                'volume': float(latest[5]),
                'prev_volume': float(previous[5]),
                'timestamp': latest[0],
                'time': datetime.fromtimestamp(latest[0]/1000).strftime('%H:%M:%S')
            },
            'price': float(ticker['price']),
            'order_book': {
                'bids': depth['bids'][:3],  # 只取前3檔
                'asks': depth['asks'][:3]
            }
        }
        
    except Exception as e:
        print(f"❌ 數據獲取錯誤: {str(e)[:100]}")
        return None

# ========== 智能分析 ==========
def analyze_market_smart(data):
    """智能市場分析"""
    if not data:
        return None
    
    kline = data['kline']
    
    # 基本分析
    is_bearish = kline['close'] < kline['open']
    is_bullish = kline['close'] > kline['open']
    
    # 成交量分析
    volume_ratio = kline['volume'] / kline['prev_volume'] if kline['prev_volume'] > 0 else 1
    
    # 買賣壓力分析（簡化版）
    buy_pressure = sum(float(bid[1]) for bid in data['order_book']['bids'])
    sell_pressure = sum(float(ask[1]) for ask in data['order_book']['asks'])
    total_pressure = buy_pressure + sell_pressure
    
    buy_ratio = buy_pressure / total_pressure if total_pressure > 0 else 0
    sell_ratio = sell_pressure / total_pressure if total_pressure > 0 else 0
    
    return {
        'price': data['price'],
        'volume': kline['volume'],
        'volume_ratio': volume_ratio,
        'buy_ratio': buy_ratio,
        'sell_ratio': sell_ratio,
        'is_bearish': is_bearish,
        'is_bullish': is_bullish,
        'time': kline['time']
    }

# ========== 主監控循環 ==========
def smart_monitor_loop():
    """智能監控主循環"""
    print("=" * 50)
    print("🚀 DUSKUSDT 智能監控系統啟動")
    print(f"📊 交易對: {SYMBOL}")
    print(f"⏰ 監控間隔: {CHECK_INTERVAL}秒")
    print(f"🎯 警報條件: 成交量>{ALERT_VOLUME_RATIO}倍 + 買賣比例>60%")
    print("=" * 50)
    
    # 發送啟動通知
    send_telegram_alert("SYSTEM_START", {
        'time': datetime.now().strftime('%H:%M:%S')
    })
    
    scan_count = 0
    last_scan_time = time.time()
    
    try:
        while True:
            scan_count += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            
            print(f"\n[{current_time}] 第 {scan_count} 次掃描")
            
            # 1. 獲取數據
            market_data = get_market_data_light()
            
            if not market_data:
                print("⏸️ 數據獲取失敗，等待重試")
                time.sleep(30)
                continue
            
            # 2. 分析數據
            analysis = analyze_market_smart(market_data)
            
            if analysis:
                # 3. 打印狀態
                status_icon = "📉" if analysis['is_bearish'] else "📈" if analysis['is_bullish'] else "➖"
                print(f"{status_icon} 價格: {analysis['price']}")
                print(f"📊 成交量: {analysis['volume_ratio']:.1f}倍")
                print(f"🟢 買單: {analysis['buy_ratio']:.1%}")
                print(f"🔴 賣單: {analysis['sell_ratio']:.1%}")
                
                # 4. 檢查警報條件
                alerts_detected = []
                
                # 條件1: 陰線 + 大量買單
                if (analysis['is_bearish'] and 
                    analysis['volume_ratio'] > ALERT_VOLUME_RATIO and 
                    analysis['buy_ratio'] > 0.6):
                    alerts_detected.append(("BUY_PRESSURE", analysis))
                
                # 條件2: 陽線 + 大量賣單
                if (analysis['is_bullish'] and 
                    analysis['volume_ratio'] > ALERT_VOLUME_RATIO and 
                    analysis['sell_ratio'] > 0.6):
                    alerts_detected.append(("SELL_PRESSURE", analysis))
                
                # 5. 觸發警報
                if alerts_detected:
                    for alert_type, alert_data in alerts_detected:
                        print(f"🚨 觸發警報: {alert_type}")
                        send_telegram_alert(alert_type, alert_data)
                else:
                    print("✅ 無異常信號")
            
            # 6. 智能等待
            elapsed = time.time() - last_scan_time
            wait_time = max(1, CHECK_INTERVAL - elapsed)
            
            print(f"⏳ 下次掃描: {wait_time:.0f}秒後")
            
            # 分批等待，可中斷
            for i in range(int(wait_time)):
                time.sleep(1)
            
            last_scan_time = time.time()
            
            # 每10次掃描隨機休息一次
            if scan_count % 10 == 0:
                extra_wait = random.randint(5, 15)
                print(f"💤 隨機休息 {extra_wait}秒")
                time.sleep(extra_wait)
                
    except KeyboardInterrupt:
        print("\n👋 監控系統停止")
        send_telegram_alert("SYSTEM_STOP", {
            'time': datetime.now().strftime('%H:%M:%S'),
            'message': f'完成 {scan_count} 次掃描'
        })
    except Exception as e:
        print(f"❌ 監控錯誤: {e}")
        # 不發送錯誤通知，避免 spam

# ========== 主程序 ==========
if __name__ == "__main__":
    # 檢查是否為測試模式
    is_test = os.getenv('GITHUB_ACTIONS') is None
    
    if is_test:
        print("🔧 測試模式啟動")
        # 測試 Telegram 功能
        test_result = send_telegram_alert("TEST", {
            'time': datetime.now().strftime('%H:%M:%S'),
            'message': '系統測試中'
        }, is_test=True)
        print(f"測試結果: {'成功' if test_result else '失敗'}")
    else:
        # 生產模式
        smart_monitor_loop()
