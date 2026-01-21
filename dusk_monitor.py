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

def get_binance_real_price(symbol="DUSKUSDT"):
    """從 Binance 獲取真實價格 - 使用正確的API"""
    try:
        # 方法1: 使用 ticker/price API
        url = f"https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": symbol}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'price' in data:
            price = float(data['price'])
            print(f"✅ 從 ticker/price 獲取價格: ${price}")
            return price
        else:
            print(f"⚠️ ticker/price API 返回異常: {data}")
            
    except Exception as e:
        print(f"❌ 方法1失敗: {e}")
    
    try:
        # 方法2: 使用 ticker/24hr API 作為備用
        url = f"https://api.binance.com/api/v3/ticker/24hr"
        params = {"symbol": symbol}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'lastPrice' in data:
            price = float(data['lastPrice'])
            print(f"✅ 從 ticker/24hr 獲取價格: ${price}")
            return price
        else:
            print(f"⚠️ ticker/24hr API 返回異常: {data}")
            
    except Exception as e:
        print(f"❌ 方法2失敗: {e}")
    
    return None

def get_binance_klines(symbol="DUSKUSDT", interval="1m", limit=10):
    """從 Binance 獲取真實 K 線數據"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if not isinstance(data, list):
            print(f"⚠️ K線API返回非列表數據: {data}")
            return None
        
        klines = []
        for k in data:
            klines.append({
                "time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "quote_volume": float(k[7]),  # 成交額
                "taker_buy_volume": float(k[9])  # 主動買入成交量
            })
        
        print(f"✅ 成功獲取 {len(klines)} 根K線數據")
        return klines
    except Exception as e:
        print(f"❌ 獲取K線數據失敗: {e}")
        return None

def analyze_market_data():
    """分析真實市場數據"""
    # 獲取當前真實價格
    current_price = get_binance_real_price(SYMBOL)
    if current_price is None:
        print("❌ 無法獲取當前價格")
        return None
    
    # 獲取K線數據
    klines = get_binance_klines(SYMBOL, "1m", 20)
    if not klines or len(klines) < 5:
        print("❌ 無法獲取足夠的K線數據")
        return None
    
    latest = klines[-1]
    previous = klines[-2] if len(klines) > 1 else latest
    
    # 判斷K線顏色（真實數據）
    is_red = latest["close"] < latest["open"]
    is_green = latest["close"] > latest["open"]
    
    # 計算價格變化
    price_change = ((latest["close"] - previous["close"]) / previous["close"]) * 100
    
    # 計算平均成交量
    volumes = [k["volume"] for k in klines[-5:]]
    avg_volume = sum(volumes) / len(volumes)
    
    # 計算成交量比率
    volume_ratio = latest["volume"] / avg_volume if avg_volume > 0 else 1
    
    # 計算買入金額（使用taker buy volume）
    buy_volume = latest["taker_buy_volume"]
    buy_value = buy_volume * latest["close"]
    
    # 計算賣出金額
    sell_volume = latest["volume"] - buy_volume
    sell_value = sell_volume * latest["close"]
    
    # 買賣比率
    buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else 999
    
    print(f"📊 數據分析完成:")
    print(f"   當前價格: ${current_price:.5f}")
    print(f"   K線收盤價: ${latest['close']:.5f}")
    print(f"   價格變化: {price_change:.2f}%")
    print(f"   成交量: {latest['volume']:,.0f}")
    print(f"   買入金額: ${buy_value:,.2f}")
    
    return {
        "symbol": SYMBOL,
        "current_price": current_price,
        "kline_price": latest["close"],
        "open": latest["open"],
        "high": latest["high"],
        "low": latest["low"],
        "close": latest["close"],
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
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

def check_and_alert():
    """檢查市場狀況並發送警報"""
    print("📊 獲取真實市場數據...")
    
    # 獲取真實數據
    market_data = analyze_market_data()
    if not market_data:
        print("❌ 無法獲取市場數據")
        return False
    
    # 顯示真實數據
    print(f"✅ 真實價格獲取成功")
    print(f"💰 當前價格: ${market_data['current_price']:.5f}")
    print(f"📈 K線收盤價: ${market_data['close']:.5f}")
    print(f"📊 價格變化: {market_data['price_change']:.2f}%")
    print(f"📦 成交量: {market_data['volume']:,.0f}")
    print(f"🎨 K線顏色: {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}")
    
    # 警報條件
    volume_threshold = 2.0
    buy_sell_threshold = 2.0
    
    current_time = datetime.now().strftime("%H:%M:%S")
    alert_sent = False
    
    # 情況1: 陰線但大量買入
    if market_data["is_red"] and market_data["buy_sell_ratio"] > buy_sell_threshold:
        message = f"""
🚨 <b>異常買入警報 - {SYMBOL}</b>

📉 <b>K線類型:</b> 陰線下跌
💰 <b>Binance價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
💵 <b>買入金額:</b> ${market_data['buy_value']:,.2f}
🔄 <b>買/賣比率:</b> {market_data['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陰線中出現大量買單！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance API 實時數據
"""
        send_telegram(message)
        alert_sent = True
        print("✅ 發送異常買入警報")
    
    # 情況2: 陽線但大量賣出
    elif market_data["is_green"] and market_data["buy_sell_ratio"] < (1/buy_sell_threshold):
        message = f"""
🚨 <b>異常賣出警報 - {SYMBOL}</b>

📈 <b>K線類型:</b> 陽線上漲
💰 <b>Binance價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
💸 <b>賣出金額:</b> ${market_data['sell_value']:,.2f}
🔄 <b>賣/買比率:</b> {1/market_data['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陽線中出現大量賣單！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance API 實時數據
"""
        send_telegram(message)
        alert_sent = True
        print("✅ 發送異常賣出警報")
    
    # 發送狀態報告（無論是否有警報）
    status_msg = f"""
📊 <b>{SYMBOL} 實時監控報告</b>

💰 <b>Binance當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📦 <b>成交量:</b> {market_data['volume']:,.0f}
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
🎨 <b>K線狀態:</b> {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}

⏰ <b>監控時間:</b> {current_time}
🔗 <b>數據驗證:</b> Binance API 實時
"""
    send_telegram(status_msg)
    
    return True

def main():
    """主函數"""
    print("=" * 60)
    print("🚀 DUSKUSDT 實時監控系統 (真實數據版)")
    print("=" * 60)
    print(f"📊 交易對: {SYMBOL}")
    print(f"⏰ 時間框架: 1分鐘K線")
    print(f"🔔 Telegram 通知: 已啟用")
    print(f"🔗 數據來源: Binance API 實時")
    print("=" * 60)
    
    # 測試 Telegram 連線
    print("📡 測試 Telegram 連線...")
    test_msg = f"""
🤖 <b>DUSKUSDT 監控系統啟動</b>

✅ 系統已使用真實數據模式
💰 使用 Binance 實時價格API
📊 交易對: {SYMBOL}
⏰ 時間框架: 1分鐘K線

🕐 啟動時間: {datetime.now().strftime('%H:%M:%S')}
"""
    
    if not send_telegram(test_msg):
        print("❌ Telegram 連線失敗")
        return False
    
    print("✅ Telegram 連線成功")
    
    # 執行一次完整監控
    success = check_and_alert()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 監控任務執行完成")
        print(f"⏰ 完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("❌ 監控任務執行失敗")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    main()
