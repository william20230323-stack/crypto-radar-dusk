#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime

# 從環境變數讀取設定
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
SYMBOL = "DUSK-USDT"  # OKX 使用短橫線格式

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

def get_okx_real_price(symbol="DUSK-USDT"):
    """從 OKX 獲取真實價格"""
    try:
        url = "https://www.okx.com/api/v5/market/ticker"
        params = {"instId": symbol}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("code") == "0" and len(data.get("data", [])) > 0:
            ticker = data["data"][0]
            price = float(ticker["last"])
            print(f"✅ 從 OKX 獲取價格: ${price}")
            return price
        else:
            print(f"⚠️ OKX API 返回異常: {data}")
            return None
            
    except Exception as e:
        print(f"❌ 獲取OKX價格失敗: {e}")
        return None

def get_okx_klines(symbol="DUSK-USDT", interval="1m", limit=20):
    """從 OKX 獲取真實 K 線數據"""
    try:
        url = "https://www.okx.com/api/v5/market/candles"
        params = {
            "instId": symbol,
            "bar": interval,
            "limit": str(limit)
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("code") == "0" and len(data.get("data", [])) > 0:
            klines = []
            for k in data["data"]:
                # OKX 返回格式: [時間戳, 開盤價, 最高價, 最低價, 收盤價, 成交量, 成交額, 成交量幣種]
                klines.append({
                    "time": int(k[0]),  # 時間戳 (毫秒)
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),  # 成交量
                    "quote_volume": float(k[6]),  # 成交額 (USDT)
                })
            
            print(f"✅ 成功獲取 {len(klines)} 根K線數據")
            return klines
        else:
            print(f"⚠️ OKX K線API返回異常: {data}")
            return None
            
    except Exception as e:
        print(f"❌ 獲取OKX K線數據失敗: {e}")
        return None

def analyze_market_data():
    """分析真實市場數據"""
    # 獲取當前真實價格
    current_price = get_okx_real_price(SYMBOL)
    if current_price is None:
        print("❌ 無法獲取當前價格")
        return None
    
    # 獲取K線數據
    klines = get_okx_klines(SYMBOL, "1m", 20)
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
    
    # 由於OKX API不提供買賣量明細，我們使用成交額作為參考
    # 在真實交易中，可以通過其他方式獲取深度數據
    buy_volume = latest["volume"] * 0.5  # 模擬買入量
    buy_value = buy_volume * latest["close"]
    sell_volume = latest["volume"] * 0.5  # 模擬賣出量
    sell_value = sell_volume * latest["close"]
    
    # 買賣比率（使用成交量比率模擬）
    buy_sell_ratio = volume_ratio  # 使用成交量比率作為參考
    
    print(f"📊 數據分析完成:")
    print(f"   當前價格: ${current_price:.5f}")
    print(f"   K線收盤價: ${latest['close']:.5f}")
    print(f"   價格變化: {price_change:.2f}%")
    print(f"   成交量: {latest['volume']:,.0f} DUSK")
    print(f"   成交額: ${latest['quote_volume']:,.2f}")
    
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
    print(f"📦 成交量: {market_data['volume']:,.0f} DUSK")
    print(f"💵 成交額: ${market_data['quote_volume']:,.2f}")
    print(f"🎨 K線顏色: {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}")
    
    # 警報條件
    volume_threshold = 2.0
    buy_sell_threshold = 2.0
    
    current_time = datetime.now().strftime("%H:%M:%S")
    alert_sent = False
    
    # 情況1: 陰線但成交量異常（模擬大量買入）
    if market_data["is_red"] and market_data["volume_ratio"] > volume_threshold:
        message = f"""
🚨 <b>異常成交量警報 - DUSK/USDT</b>

📉 <b>K線類型:</b> 陰線下跌
💰 <b>OKX當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
📦 <b>成交量:</b> {market_data['volume']:,.0f} DUSK
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}

⚠️ <b>檢測到陰線中出現異常成交量！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> OKX API 實時數據
"""
        send_telegram(message)
        alert_sent = True
        print("✅ 發送異常成交量警報")
    
    # 情況2: 陽線但成交量異常（模擬大量賣出）
    elif market_data["is_green"] and market_data["volume_ratio"] > volume_threshold:
        message = f"""
🚨 <b>異常成交量警報 - DUSK/USDT</b>

📈 <b>K線類型:</b> 陽線上漲
💰 <b>OKX當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
📦 <b>成交量:</b> {market_data['volume']:,.0f} DUSK
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}

⚠️ <b>檢測到陽線中出現異常成交量！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> OKX API 實時數據
"""
        send_telegram(message)
        alert_sent = True
        print("✅ 發送異常成交量警報")
    
    # 發送狀態報告（無論是否有警報）
    status_msg = f"""
📊 <b>DUSK/USDT 實時監控報告</b>

💰 <b>OKX當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📦 <b>成交量:</b> {market_data['volume']:,.0f} DUSK
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
🎨 <b>K線狀態:</b> {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}

⏰ <b>監控時間:</b> {current_time}
🔗 <b>數據驗證:</b> OKX API 實時數據
"""
    send_telegram(status_msg)
    
    return True

def main():
    """主函數"""
    print("=" * 60)
    print("🚀 DUSK/USDT 實時監控系統 (OKX 數據源)")
    print("=" * 60)
    print(f"📊 交易對: DUSK-USDT")
    print(f"⏰ 時間框架: 1分鐘K線")
    print(f"🔔 Telegram 通知: 已啟用")
    print(f"🔗 數據來源: OKX API 實時")
    print("=" * 60)
    
    # 測試 Telegram 連線
    print("📡 測試 Telegram 連線...")
    test_msg = f"""
🤖 <b>DUSK/USDT 監控系統啟動</b>

✅ 系統已切換至 OKX 數據源
💰 使用 OKX 實時價格API
📊 交易對: DUSK-USDT
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
