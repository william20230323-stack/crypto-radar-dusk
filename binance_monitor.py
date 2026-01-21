#!/usr/bin/env python3
"""
幣安 DUSKUSDT 智能監控系統
監控規則：
1. 1分鐘陰線 + 大量買單 → 買入警報
2. 1分鐘陽線 + 大量賣單 → 出逃警報
"""

import os
import time
import requests
from datetime import datetime
from binance.client import Client
from binance.enums import *

# ========== 配置參數 ==========
SYMBOL = "DUSKUSDT"
TIMEFRAME = Client.KLINE_INTERVAL_1MINUTE
ALERT_VOLUME_RATIO = 3.0  # 成交量異常閾值（3倍平均）

# ========== Telegram 通知 ==========
def send_telegram_alert(alert_type, data):
    """發送 Telegram 警報"""
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 缺少 Telegram 配置")
        return False
    
    try:
        # 根據警報類型生成不同訊息
        if alert_type == "BUY_PRESSURE":
            message = f"""🚨 <b>大量買盤偵測 - DUSKUSDT</b>

📉 K線狀態：陰線下跌
💰 當前價格：{data['price']} USDT
📊 成交量：{data['volume']:.2f} DUSK
⚡ 買入壓力：{data['buy_pressure']:.1%}
🕒 時間：{data['time']}

🔍 特徵：
• 價格下跌但買單持續流入
• 成交量異常放大 {data['volume_ratio']:.1f} 倍
• 可能為機構吸籌或抄底資金進入

⚠️ 注意：可能是反轉信號"""
            
        elif alert_type == "SELL_PRESSURE":
            message = f"""🚨 <b>大量賣盤出逃 - DUSKUSDT</b>

📈 K線狀態：陽線上漲
💰 當前價格：{data['price']} USDT
📊 成交量：{data['volume']:.2f} DUSK
⚡ 賣出壓力：{data['sell_pressure']:.1%}
🕒 時間：{data['time']}

🔍 特徵：
• 價格上漲但賣單持續流出
• 成交量異常放大 {data['volume_ratio']:.1f} 倍
• 可能為獲利了結或主力出貨

⚠️ 注意：可能是頂部信號"""
        
        else:
            message = f"📊 DUSKUSDT 監控更新\n價格: {data['price']} USDT\n時間: {data['time']}"
        
        # 發送通知
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ {alert_type} 警報發送成功")
            return True
        else:
            print(f"❌ 警報發送失敗: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram 發送錯誤: {e}")
        return False

# ========== 幣安數據獲取 ==========
def get_binance_data():
    """獲取幣安市場數據"""
    try:
        # 初始化幣安客戶端（無需API密鑰，僅讀取公開數據）
        client = Client()
        
        # 獲取最新K線數據
        klines = client.get_klines(
            symbol=SYMBOL,
            interval=TIMEFRAME,
            limit=20  # 獲取最近20根K線
        )
        
        if not klines:
            print("❌ 無法獲取K線數據")
            return None
        
        # 解析最新K線
        latest = klines[-1]
        prev = klines[-2] if len(klines) > 1 else latest
        
        # K線數據結構：[時間戳, 開盤, 最高, 最低, 收盤, 成交量, ...]
        current_kline = {
            'timestamp': latest[0],
            'open': float(latest[1]),
            'high': float(latest[2]),
            'low': float(latest[3]),
            'close': float(latest[4]),
            'volume': float(latest[5]),
            'time': datetime.fromtimestamp(latest[0]/1000).strftime('%H:%M:%S')
        }
        
        previous_kline = {
            'volume': float(prev[5])
        }
        
        # 獲取當前訂單簿（買賣掛單）
        depth = client.get_order_book(symbol=SYMBOL, limit=10)
        
        # 獲取當前價格
        ticker = client.get_symbol_ticker(symbol=SYMBOL)
        current_price = float(ticker['price'])
        
        # 計算買賣壓力
        buy_pressure = sum(float(order[1]) for order in depth['bids'][:5])  # 前5檔買單
        sell_pressure = sum(float(order[1]) for order in depth['asks'][:5])  # 前5檔賣單
        
        return {
            'current_kline': current_kline,
            'previous_kline': previous_kline,
            'current_price': current_price,
            'buy_pressure': buy_pressure,
            'sell_pressure': sell_pressure,
            'order_book': depth
        }
        
    except Exception as e:
        print(f"❌ 獲取幣安數據錯誤: {e}")
        return None

# ========== 分析邏輯 ==========
def analyze_market(data):
    """分析市場異常"""
    if not data:
        return None
    
    kline = data['current_kline']
    prev_kline = data['previous_kline']
    
    # 判斷陰線陽線
    is_bearish = kline['close'] < kline['open']  # 陰線：收盤低於開盤
    is_bullish = kline['close'] > kline['open']  # 陽線：收盤高於開盤
    
    # 計算成交量異常
    avg_volume = prev_kline['volume']
    volume_ratio = kline['volume'] / avg_volume if avg_volume > 0 else 1
    
    # 計算買賣壓力比例
    total_pressure = data['buy_pressure'] + data['sell_pressure']
    buy_ratio = data['buy_pressure'] / total_pressure if total_pressure > 0 else 0
    sell_ratio = data['sell_pressure'] / total_pressure if total_pressure > 0 else 0
    
    analysis = {
        'is_bearish': is_bearish,
        'is_bullish': is_bullish,
        'volume_ratio': volume_ratio,
        'buy_ratio': buy_ratio,
        'sell_ratio': sell_ratio,
        'price': data['current_price'],
        'volume': kline['volume'],
        'time': kline['time']
    }
    
    # 檢查觸發條件
    alerts = []
    
    # 條件1：陰線 + 大量買單
    if is_bearish and volume_ratio > ALERT_VOLUME_RATIO and buy_ratio > 0.6:
        alerts.append({
            'type': 'BUY_PRESSURE',
            'data': {
                'price': data['current_price'],
                'volume': kline['volume'],
                'volume_ratio': volume_ratio,
                'buy_pressure': buy_ratio,
                'time': kline['time']
            }
        })
    
    # 條件2：陽線 + 大量賣單
    if is_bullish and volume_ratio > ALERT_VOLUME_RATIO and sell_ratio > 0.6:
        alerts.append({
            'type': 'SELL_PRESSURE',
            'data': {
                'price': data['current_price'],
                'volume': kline['volume'],
                'volume_ratio': volume_ratio,
                'sell_pressure': sell_ratio,
                'time': kline['time']
            }
        })
    
    return {
        'analysis': analysis,
        'alerts': alerts
    }

# ========== 主程序 ==========
def main():
    """主監控程序"""
    print("=" * 50)
    print("🚀 幣安 DUSKUSDT 智能監控系統啟動")
    print(f"📊 監控交易對: {SYMBOL}")
    print(f"⏰ 時間框架: 1分鐘K線")
    print(f"📈 成交量警報閾值: {ALERT_VOLUME_RATIO}倍")
    print("=" * 50)
    
    # 發送啟動通知
    send_telegram_alert("START", {
        'price': 0,
        'time': datetime.now().strftime('%H:%M:%S'),
        'message': 'DUSKUSDT 智能監控系統已啟動'
    })
    
    monitor_count = 0
    
    while True:
        try:
            monitor_count += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            
            print(f"\n[{current_time}] 第 {monitor_count} 次監控掃描...")
            
            # 1. 獲取市場數據
            print("📡 獲取幣安市場數據...")
            market_data = get_binance_data()
            
            if not market_data:
                print("⏸️ 數據獲取失敗，等待重試...")
                time.sleep(30)
                continue
            
            # 2. 分析市場
            print("🔍 分析市場異常...")
            result = analyze_market(market_data)
            
            if not result:
                time.sleep(30)
                continue
            
            analysis = result['analysis']
            alerts = result['alerts']
            
            # 3. 打印分析結果
            print(f"📊 當前價格: {analysis['price']} USDT")
            print(f"📈 成交量比率: {analysis['volume_ratio']:.1f}倍")
            print(f"🟢 買單比例: {analysis['buy_ratio']:.1%}")
            print(f"🔴 賣單比例: {analysis['sell_ratio']:.1%}")
            print(f"🎯 K線狀態: {'陰線' if analysis['is_bearish'] else '陽線' if analysis['is_bullish'] else '十字線'}")
            
            # 4. 觸發警報
            if alerts:
                print(f"🚨 檢測到 {len(alerts)} 個警報")
                for alert in alerts:
                    print(f"  觸發: {alert['type']}")
                    send_telegram_alert(alert['type'], alert['data'])
            else:
                print("✅ 無異常信號")
            
            # 5. 等待下一分鐘
            print(f"⏳ 等待下一次掃描...")
            
            # 計算等待時間（確保每分鐘執行一次）
            now = datetime.now()
            seconds_past = now.second
            wait_time = 60 - seconds_past
            
            if wait_time > 0:
                for i in range(wait_time):
                    if i % 10 == 0 and i > 0:
                        print(f"  倒數 {wait_time - i} 秒...")
                    time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n👋 手動停止監控系統")
            send_telegram_alert("STOP", {
                'price': 0,
                'time': datetime.now().strftime('%H:%M:%S'),
                'message': '監控系統已停止'
            })
            break
            
        except Exception as e:
            print(f"❌ 監控循環錯誤: {e}")
            time.sleep(30)  # 錯誤後等待30秒

if __name__ == "__main__":
    main()
