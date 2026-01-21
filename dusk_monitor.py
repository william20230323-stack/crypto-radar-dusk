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

def get_alternative_price():
    """從多個來源獲取價格，優先使用美國可訪問的API"""
    price_sources = [
        # 來源1: CoinGecko API (美國可訪問)
        {
            "name": "CoinGecko",
            "url": "https://api.coingecko.com/api/v3/simple/price",
            "params": {"ids": "dusk-network", "vs_currencies": "usd"},
            "parser": lambda data: data["dusk-network"]["usd"]
        },
        # 來源2: CoinMarketCap API (需要註冊，但我們使用公開數據)
        {
            "name": "CoinMarketCap",
            "url": "https://api.coincap.io/v2/assets/dusk-network",
            "parser": lambda data: float(data["data"]["priceUsd"])
        },
        # 來源3: Kraken API (美國交易所)
        {
            "name": "Kraken",
            "url": "https://api.kraken.com/0/public/Ticker",
            "params": {"pair": "DUSKUSD"},
            "parser": lambda data: float(data["result"]["DUSKUSD"]["c"][0])
        },
        # 來源4: CryptoCompare API
        {
            "name": "CryptoCompare",
            "url": "https://min-api.cryptocompare.com/data/price",
            "params": {"fsym": "DUSK", "tsyms": "USD"},
            "parser": lambda data: data["USD"]
        }
    ]
    
    for source in price_sources:
        try:
            print(f"🔄 嘗試從 {source['name']} 獲取價格...")
            response = requests.get(source['url'], 
                                  params=source.get('params', {}), 
                                  timeout=10)
            data = response.json()
            price = source['parser'](data)
            print(f"✅ 從 {source['name']} 獲取價格成功: ${price:.5f}")
            return price, source['name']
        except Exception as e:
            print(f"❌ {source['name']} 失敗: {e}")
            continue
    
    return None, None

def get_kline_data_from_alternative():
    """從替代來源獲取K線數據"""
    try:
        # 使用 CryptoCompare 的歷史分鐘數據
        url = "https://min-api.cryptocompare.com/data/v2/histominute"
        params = {
            "fsym": "DUSK",
            "tsym": "USD",
            "limit": 20,
            "aggregate": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("Response") == "Success":
            klines = []
            for candle in data["Data"]["Data"]:
                klines.append({
                    "time": candle["time"] * 1000,  # 轉為毫秒
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volumefrom"],  # DUSK 成交量
                    "quote_volume": candle["volumeto"]  # USD 成交額
                })
            
            print(f"✅ 成功獲取 {len(klines)} 根K線數據")
            return klines
        else:
            print(f"⚠️ CryptoCompare 返回異常: {data.get('Message')}")
            return None
            
    except Exception as e:
        print(f"❌ 獲取K線數據失敗: {e}")
        return None

def analyze_market_data():
    """分析市場數據"""
    # 獲取當前價格
    current_price, source_name = get_alternative_price()
    if current_price is None:
        print("❌ 無法從任何來源獲取價格")
        return None
    
    # 獲取K線數據
    klines = get_kline_data_from_alternative()
    if not klines or len(klines) < 5:
        print("❌ 無法獲取足夠的K線數據")
        return None
    
    latest = klines[-1]
    previous = klines[-2] if len(klines) > 1 else latest
    
    # 判斷K線顏色
    is_red = latest["close"] < latest["open"]
    is_green = latest["close"] > latest["open"]
    
    # 計算價格變化
    price_change = ((latest["close"] - previous["close"]) / previous["close"]) * 100
    
    # 計算平均成交量
    volumes = [k["volume"] for k in klines[-5:]]
    avg_volume = sum(volumes) / len(volumes)
    
    # 計算成交量比率
    volume_ratio = latest["volume"] / avg_volume if avg_volume > 0 else 1
    
    # 計算成交額
    total_value = latest["quote_volume"]
    buy_volume = latest["volume"] * 0.5  # 模擬買入量
    buy_value = buy_volume * latest["close"]
    sell_volume = latest["volume"] * 0.5  # 模擬賣出量
    sell_value = sell_volume * latest["close"]
    
    print(f"📊 數據分析完成:")
    print(f"   數據來源: {source_name}")
    print(f"   當前價格: ${current_price:.5f}")
    print(f"   K線收盤價: ${latest['close']:.5f}")
    print(f"   價格變化: {price_change:.2f}%")
    print(f"   成交量: {latest['volume']:,.0f} DUSK")
    print(f"   成交額: ${latest['quote_volume']:,.2f}")
    
    return {
        "symbol": "DUSK/USDT",
        "source": source_name,
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
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

def check_and_alert():
    """檢查市場狀況並發送警報"""
    print("📊 獲取市場數據...")
    
    # 獲取數據
    market_data = analyze_market_data()
    if not market_data:
        print("❌ 無法獲取市場數據")
        return False
    
    # 顯示數據
    print(f"✅ 價格獲取成功")
    print(f"💰 當前價格: ${market_data['current_price']:.5f}")
    print(f"📈 K線收盤價: ${market_data['close']:.5f}")
    print(f"📊 價格變化: {market_data['price_change']:.2f}%")
    print(f"📦 成交量: {market_data['volume']:,.0f} DUSK")
    print(f"🎨 K線顏色: {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}")
    
    # 警報條件
    volume_threshold = 2.0
    price_change_threshold = 2.0
    
    current_time = datetime.now().strftime("%H:%M:%S")
    alert_sent = False
    
    # 情況1: 陰線但成交量異常
    if market_data["is_red"] and market_data["volume_ratio"] > volume_threshold:
        message = f"""
🚨 <b>異常成交量警報 - DUSK/USDT</b>

📉 <b>K線類型:</b> 陰線下跌
💰 <b>當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
📦 <b>成交量:</b> {market_data['volume']:,.0f} DUSK
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}

⚠️ <b>檢測到陰線中出現異常成交量！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> {market_data['source']}
"""
        send_telegram(message)
        alert_sent = True
        print("✅ 發送異常成交量警報")
    
    # 情況2: 陽線但成交量異常
    elif market_data["is_green"] and market_data["volume_ratio"] > volume_threshold:
        message = f"""
🚨 <b>異常成交量警報 - DUSK/USDT</b>

📈 <b>K線類型:</b> 陽線上漲
💰 <b>當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
📦 <b>成交量:</b> {market_data['volume']:,.0f} DUSK
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}

⚠️ <b>檢測到陽線中出現異常成交量！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> {market_data['source']}
"""
        send_telegram(message)
        alert_sent = True
        print("✅ 發送異常成交量警報")
    
    # 情況3: 價格大幅波動
    elif abs(market_data["price_change"]) > price_change_threshold:
        direction = "上漲" if market_data["price_change"] > 0 else "下跌"
        message = f"""
⚠️ <b>價格大幅波動 - DUSK/USDT</b>

💰 <b>當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}% ({direction})
📦 <b>成交量:</b> {market_data['volume']:,.0f} DUSK
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}
🎨 <b>K線狀態:</b> {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> {market_data['source']}
"""
        send_telegram(message)
        alert_sent = True
        print("✅ 發送價格波動警報")
    
    # 發送狀態報告
    status_msg = f"""
📊 <b>DUSK/USDT 監控報告</b>

💰 <b>當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📦 <b>成交量:</b> {market_data['volume']:,.0f} DUSK
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
🎨 <b>K線狀態:</b> {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}

⏰ <b>監控時間:</b> {current_time}
🔗 <b>數據來源:</b> {market_data['source']}
"""
    send_telegram(status_msg)
    
    return True

def main():
    """主函數"""
    print("=" * 60)
    print("🚀 DUSK/USDT 實時監控系統 (多數據源版)")
    print("=" * 60)
    print(f"📊 交易對: DUSK/USDT")
    print(f"⏰ 時間框架: 1分鐘K線")
    print(f"🔔 Telegram 通知: 已啟用")
    print(f"🔗 數據來源: 多來源備援系統")
    print("=" * 60)
    
    # 測試 Telegram 連線
    print("📡 測試 Telegram 連線...")
    test_msg = f"""
🤖 <b>DUSK/USDT 監控系統啟動</b>

✅ 系統已使用多數據源模式
💰 使用美國可訪問的API來源
📊 交易對: DUSK/USDT
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
