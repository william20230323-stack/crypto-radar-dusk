#!/usr/bin/env python3
import os
import sys
import time
import requests
import json
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

def get_binance_kline_data(symbol="DUSKUSDT", interval="1m", limit=100):
    """從 Binance 獲取 K 線數據"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        klines = []
        for k in data:
            klines.append({
                "time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": k[6],
                "quote_volume": float(k[7]),
                "trades": k[8],
                "taker_buy_volume": float(k[9]),
                "taker_buy_quote_volume": float(k[10])
            })
        
        return klines
    except Exception as e:
        print(f"❌ 獲取 Binance 數據失敗: {e}")
        return None

def analyze_kline(kline_data):
    """分析 K 線數據"""
    if not kline_data or len(kline_data) < 10:
        return None
    
    # 獲取最新一根 K 線
    latest = kline_data[-1]
    
    # 計算平均成交量（使用最近10根K線）
    recent_volumes = [k["volume"] for k in kline_data[-10:]]
    avg_volume = sum(recent_volumes) / len(recent_volumes)
    
    # 判斷 K 線顏色
    is_red = latest["close"] < latest["open"]  # 陰線
    is_green = latest["close"] > latest["open"]  # 陽線
    
    # 計算價格變化百分比
    price_change = ((latest["close"] - latest["open"]) / latest["open"]) * 100
    
    # 計算成交量比率
    volume_ratio = latest["volume"] / avg_volume if avg_volume > 0 else 1
    
    # 計算買入/賣出金額
    buy_volume = latest["taker_buy_volume"]
    sell_volume = latest["volume"] - buy_volume
    
    buy_value = latest["taker_buy_quote_volume"]
    sell_value = latest["quote_volume"] - buy_value
    
    # 計算買賣比率
    buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else 999
    
    return {
        "symbol": SYMBOL,
        "time": datetime.fromtimestamp(latest["time"]/1000).strftime("%H:%M:%S"),
        "open": latest["open"],
        "high": latest["high"],
        "low": latest["low"],
        "close": latest["close"],
        "price": latest["close"],
        "volume": latest["volume"],
        "quote_volume": latest["quote_volume"],
        "price_change": price_change,
        "is_red": is_red,
        "is_green": is_green,
        "volume_ratio": volume_ratio,
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "buy_value": buy_value,
        "sell_value": sell_value,
        "buy_sell_ratio": buy_sell_ratio,
        "avg_volume": avg_volume
    }

def send_alert(analysis):
    """根據分析結果發送警報"""
    
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # 警報條件
    volume_threshold = 2.0  # 成交量超過平均2倍
    buy_sell_threshold = 2.0  # 買賣比率閾值
    
    # 情況1: 陰線但大量買入（買單是賣單的2倍以上）
    if analysis["is_red"] and analysis["buy_sell_ratio"] > buy_sell_threshold:
        message = f"""
🚨 <b>異常買入警報 - {SYMBOL}</b>

📉 <b>K線類型:</b> 陰線下跌
💰 <b>當前價格:</b> ${analysis['price']:.6f}
📊 <b>價格變化:</b> {analysis['price_change']:.2f}%
📈 <b>成交量比率:</b> {analysis['volume_ratio']:.2f}x
💵 <b>買入金額:</b> ${analysis['buy_value']:,.2f}
🔄 <b>買/賣比率:</b> {analysis['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陰線中出現大量買單！</b>

⏰ <b>時間:</b> {current_time}
"""
        return send_telegram(message), "BUY_IN_RED"
    
    # 情況2: 陽線但大量賣出（賣單是買單的2倍以上）
    elif analysis["is_green"] and analysis["buy_sell_ratio"] < (1/buy_sell_threshold):
        message = f"""
🚨 <b>異常賣出警報 - {SYMBOL}</b>

📈 <b>K線類型:</b> 陽線上漲
💰 <b>當前價格:</b> ${analysis['price']:.6f}
📊 <b>價格變化:</b> {analysis['price_change']:.2f}%
📈 <b>成交量比率:</b> {analysis['volume_ratio']:.2f}x
💸 <b>賣出金額:</b> ${analysis['sell_value']:,.2f}
🔄 <b>賣/買比率:</b> {1/analysis['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陽線中出現大量賣單！</b>

⏰ <b>時間:</b> {current_time}
"""
        return send_telegram(message), "SELL_IN_GREEN"
    
    # 情況3: 成交量異常但不符合上述條件
    elif analysis["volume_ratio"] > volume_threshold:
        message = f"""
⚠️ <b>成交量異常 - {SYMBOL}</b>

💰 <b>當前價格:</b> ${analysis['price']:.6f}
📊 <b>價格變化:</b> {analysis['price_change']:.2f}%
📈 <b>成交量比率:</b> {analysis['volume_ratio']:.2f}x
📦 <b>成交量:</b> {analysis['volume']:,.0f}

⏰ <b>時間:</b> {current_time}
"""
        return send_telegram(message), "VOLUME_SPIKE"
    
    return False, "NORMAL"

def main_monitor():
    """主監控函數"""
    print("=" * 50)
    print("🚀 DUSKUSDT 1分鐘監控系統")
    print("=" * 50)
    
    # 測試 Telegram 連線
    print("📡 測試 Telegram 連線...")
    test_msg = "🤖 DUSKUSDT 監控系統啟動成功！\n系統已開始監控 1分鐘K線。"
    if not send_telegram(test_msg):
        print("❌ Telegram 連線失敗")
        return False
    
    print("✅ Telegram 連線成功")
    
    # 開始監控循環
    print("\n📊 開始監控 Binance 數據...")
    
    try:
        # 在 GitHub Actions 中，我們只執行一次完整的檢查
        # 因為 Actions 會每2分鐘觸發一次
        kline_data = get_binance_kline_data(SYMBOL, "1m", 100)
        
        if not kline_data:
            print("❌ 無法獲取 Binance 數據")
            return False
        
        # 分析數據
        analysis = analyze_kline(kline_data)
        
        if not analysis:
            print("❌ 數據分析失敗")
            return False
        
        # 顯示當前狀態
        print(f"📊 當前價格: ${analysis['price']:.6f}")
        print(f"📈 價格變化: {analysis['price_change']:.2f}%")
        print(f"📦 成交量: {analysis['volume']:,.0f}")
        print(f"📊 成交量比率: {analysis['volume_ratio']:.2f}x")
        print(f"🔄 買/賣比率: {analysis['buy_sell_ratio']:.2f}")
        print(f"🎨 K線顏色: {'🔴 陰線' if analysis['is_red'] else '🟢 陽線'}")
        
        # 檢查並發送警報
        alert_sent, alert_type = send_alert(analysis)
        
        if alert_sent:
            print(f"✅ 已發送 {alert_type} 警報")
        else:
            print("📊 市場狀態正常，無異常訊號")
            
            # 每10次正常狀態發送一次狀態報告
            status_msg = f"""
📊 <b>{SYMBOL} 市場狀態報告</b>

💰 <b>當前價格:</b> ${analysis['price']:.6f}
📊 <b>價格變化:</b> {analysis['price_change']:.2f}%
📦 <b>成交量:</b> {analysis['volume']:,.0f}
📈 <b>成交量比率:</b> {analysis['volume_ratio']:.2f}x

⏰ <b>時間:</b> {datetime.now().strftime('%H:%M:%S')}
"""
            send_telegram(status_msg)
        
        return True
        
    except Exception as e:
        print(f"❌ 監控過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main_monitor()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 監控任務執行完成")
        print(f"⏰ 完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("❌ 監控任務執行失敗")
    print("=" * 50)
