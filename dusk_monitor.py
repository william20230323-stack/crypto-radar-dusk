#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime
import random
from typing import Dict, Optional, Tuple

# 從環境變數讀取設定
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
SYMBOL = "DUSKUSDT"

# 檢查設定
if not TG_TOKEN or not TG_CHAT_ID:
    print("❌ 錯誤: TG_TOKEN 或 TG_CHAT_ID 未設定")
    sys.exit(1)

print(f"✅ 開始監控 {SYMBOL} 1分鐘K線...")

# 速率限制設定
REQUEST_DELAY = 1.5  # 每次請求間隔1.5秒
MAX_RETRIES = 3
API_TIMEOUT = 10

# 用戶代理輪換列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/537.36",
    "Mozilla/5.0 (Android 10; Mobile) AppleWebKit/537.36"
]

class RateLimiter:
    """速率限制器"""
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.last_request = 0
    
    def wait_if_needed(self):
        """如果需要則等待"""
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request = time.time()

class BinanceUSAPI:
    """美國合規 Binance API 客戶端"""
    def __init__(self):
        self.base_url = "https://api.binance.us/api/v3"
        self.rate_limiter = RateLimiter(REQUEST_DELAY)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": random.choice(USER_AGENTS)
        })
    
    def make_request(self, endpoint: str, params: Dict = None, retry: int = 0) -> Optional[Dict]:
        """發送API請求"""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            print(f"📡 請求 {endpoint}...")
            response = self.session.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            # 隨機切換User-Agent
            if random.random() > 0.7:
                self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API請求失敗: {e}")
            
            if retry < MAX_RETRIES:
                wait_time = 2 ** retry + random.uniform(0.1, 0.5)
                print(f"⏳ 等待 {wait_time:.1f}秒後重試...")
                time.sleep(wait_time)
                return self.make_request(endpoint, params, retry + 1)
            
            return None
    
    def get_price(self, symbol: str) -> Optional[float]:
        """獲取當前價格"""
        data = self.make_request("ticker/price", {"symbol": symbol})
        
        if data and "price" in data:
            price = float(data["price"])
            print(f"✅ 獲取價格成功: ${price:.5f}")
            return price
        
        return None
    
    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 20) -> Optional[list]:
        """獲取K線數據"""
        data = self.make_request("klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        
        if data and isinstance(data, list):
            klines = []
            for k in data:
                try:
                    klines.append({
                        "time": k[0],
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "quote_volume": float(k[7]),
                        "trades": k[8],
                        "taker_buy_volume": float(k[9]),
                        "taker_buy_quote_volume": float(k[10])
                    })
                except (IndexError, ValueError) as e:
                    print(f"⚠️ 解析K線數據錯誤: {e}")
                    continue
            
            if klines:
                print(f"✅ 獲取 {len(klines)} 根K線數據成功")
                return klines
        
        return None
    
    def get_ticker_24h(self, symbol: str) -> Optional[Dict]:
        """獲取24小時統計數據"""
        data = self.make_request("ticker/24hr", {"symbol": symbol})
        return data

def send_telegram(message: str) -> bool:
    """發送 Telegram 訊息"""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        # 為Telegram請求也添加延遲
        time.sleep(0.5)
        response = requests.post(url, json=payload, timeout=API_TIMEOUT)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Telegram 錯誤: {e}")
        return False

def analyze_market_data(api: BinanceUSAPI) -> Optional[Dict]:
    """分析市場數據"""
    print("📊 獲取市場數據...")
    
    # 獲取當前價格
    current_price = api.get_price(SYMBOL)
    if current_price is None:
        print("❌ 無法獲取當前價格")
        return None
    
    # 獲取K線數據
    klines = api.get_klines(SYMBOL, "1m", 15)
    if not klines or len(klines) < 5:
        print("❌ 無法獲取足夠的K線數據")
        return None
    
    # 確保使用完整的K線（避免使用當前正在形成的K線）
    # 取倒數第二根K線作為最新完整K線
    if len(klines) >= 2:
        latest = klines[-2]  # 前一根完整的K線
    else:
        latest = klines[-1]
    
    if len(klines) >= 3:
        previous = klines[-3]  # 前兩根的K線
    else:
        previous = klines[-2] if len(klines) >= 2 else latest
    
    # 判斷K線顏色
    is_red = latest["close"] < latest["open"]
    is_green = latest["close"] > latest["open"]
    
    # 計算價格變化
    price_change = ((latest["close"] - previous["close"]) / previous["close"]) * 100
    
    # 計算平均成交量（使用最近5根完整K線）
    recent_klines = klines[-7:-2] if len(klines) >= 7 else klines[:-1]
    volumes = [k["volume"] for k in recent_klines[-5:]]
    avg_volume = sum(volumes) / len(volumes) if volumes else latest["volume"]
    
    # 計算成交量比率
    volume_ratio = latest["volume"] / avg_volume if avg_volume > 0 else 1
    
    # 計算買入/賣出數據
    buy_volume = latest["taker_buy_volume"]
    sell_volume = latest["volume"] - buy_volume
    
    buy_value = latest["taker_buy_quote_volume"]
    sell_value = latest["quote_volume"] - buy_value
    
    # 計算買賣比率
    buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else 999
    
    print(f"📊 數據分析完成:")
    print(f"   當前價格: ${current_price:.5f}")
    print(f"   K線收盤價: ${latest['close']:.5f}")
    print(f"   價格變化: {price_change:.2f}%")
    print(f"   成交量比率: {volume_ratio:.2f}x")
    print(f"   買賣比率: {buy_sell_ratio:.2f}")
    
    return {
        "symbol": SYMBOL,
        "current_price": current_price,
        "kline_data": latest,
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
        "avg_volume": avg_volume,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

def send_alert(market_data: Dict) -> Tuple[bool, str]:
    """發送警報"""
    alert_sent = False
    alert_type = "NORMAL"
    
    # 警報條件
    volume_threshold = 2.0
    buy_sell_threshold = 2.0
    
    current_time = market_data["timestamp"]
    
    # 情況1: 陰線但大量買入
    if market_data["is_red"] and market_data["buy_sell_ratio"] > buy_sell_threshold:
        message = f"""
🚨 <b>異常買入警報 - {SYMBOL}</b>

📉 <b>K線類型:</b> 陰線下跌
💰 <b>當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
💵 <b>買入金額:</b> ${market_data['buy_value']:,.2f}
🔄 <b>買/賣比率:</b> {market_data['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陰線中出現大量買單！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance.US API
"""
        if send_telegram(message):
            alert_sent = True
            alert_type = "BUY_IN_RED"
            print("✅ 發送異常買入警報")
    
    # 情況2: 陽線但大量賣出
    elif market_data["is_green"] and market_data["buy_sell_ratio"] < (1/buy_sell_threshold):
        message = f"""
🚨 <b>異常賣出警報 - {SYMBOL}</b>

📈 <b>K線類型:</b> 陽線上漲
💰 <b>當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
💸 <b>賣出金額:</b> ${market_data['sell_value']:,.2f}
🔄 <b>賣/買比率:</b> {1/market_data['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陽線中出現大量賣單！</b>

⏰ <b>時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance.US API
"""
        if send_telegram(message):
            alert_sent = True
            alert_type = "SELL_IN_GREEN"
            print("✅ 發送異常賣出警報")
    
    # 發送狀態報告
    status_msg = f"""
📊 <b>{SYMBOL} 實時監控報告</b>

💰 <b>當前價格:</b> ${market_data['current_price']:.5f}
📊 <b>K線收盤價:</b> ${market_data['close']:.5f}
📈 <b>價格變化:</b> {market_data['price_change']:.2f}%
📦 <b>成交量:</b> {market_data['volume']:,.0f}
💵 <b>成交額:</b> ${market_data['quote_volume']:,.2f}
📊 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
🎨 <b>K線狀態:</b> {'🔴 陰線' if market_data['is_red'] else '🟢 陽線'}

⏰ <b>監控時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance.US API
"""
    send_telegram(status_msg)
    
    return alert_sent, alert_type

def run_monitoring_cycle(api: BinanceUSAPI, duration_minutes: int = 5) -> bool:
    """運行監控循環"""
    print(f"🔄 開始監控循環，持續 {duration_minutes} 分鐘...")
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    cycle_count = 0
    
    try:
        while time.time() < end_time:
            cycle_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n🔄 循環 #{cycle_count} - {current_time}")
            
            # 獲取並分析市場數據
            market_data = analyze_market_data(api)
            
            if market_data:
                # 發送警報
                alert_sent, alert_type = send_alert(market_data)
                
                if alert_sent:
                    print(f"⚠️ 檢測到 {alert_type} 警報")
                else:
                    print(f"📊 市場狀態正常")
            else:
                print("❌ 數據獲取失敗")
            
            # 計算下一次檢查的時間
            elapsed = time.time() - start_time
            remaining = end_time - time.time()
            
            if remaining > 30:
                # 等待30秒後進行下一次檢查
                wait_time = 30 + random.uniform(-2, 2)  # 添加隨機性
                print(f"⏳ 等待 {wait_time:.1f}秒後繼續...")
                time.sleep(wait_time)
            else:
                break
        
        print(f"✅ 監控循環完成，共執行 {cycle_count} 次檢查")
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️ 監控手動停止")
        return True
    except Exception as e:
        print(f"❌ 監控循環錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函數"""
    print("=" * 70)
    print("🚀 DUSK/USDT 實時監控系統 (Binance.US 數據源)")
    print("=" * 70)
    print(f"📊 交易對: {SYMBOL}")
    print(f"⏰ 時間框架: 1分鐘K線")
    print(f"🔔 Telegram 通知: 已啟用")
    print(f"🔗 數據來源: Binance.US API")
    print(f"⏱️  請求間隔: {REQUEST_DELAY}秒")
    print(f"🔄 最大重試次數: {MAX_RETRIES}")
    print("=" * 70)
    
    # 測試 Telegram 連線
    print("📡 測試 Telegram 連線...")
    test_msg = f"""
🤖 <b>{SYMBOL} 監控系統啟動</b>

✅ 系統使用 Binance.US API
💰 美國合規數據源
📊 交易對: {SYMBOL}
⏰ 時間框架: 1分鐘K線
🔄 監控間隔: 30秒
⏱️  請求延遲: {REQUEST_DELAY}秒

🕐 啟動時間: {datetime.now().strftime('%H:%M:%S')}
"""
    
    if not send_telegram(test_msg):
        print("❌ Telegram 連線失敗")
        return False
    
    print("✅ Telegram 連線成功")
    
    # 初始化 API 客戶端
    api = BinanceUSAPI()
    
    # 運行監控循環
    success = run_monitoring_cycle(api, duration_minutes=5)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 監控任務執行完成")
        print(f"⏰ 完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("❌ 監控任務執行失敗")
    print("=" * 70)
    
    return success

if __name__ == "__main__":
    main()
