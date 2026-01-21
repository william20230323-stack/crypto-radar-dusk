#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime, timedelta
import random
import json
from typing import Dict, Optional, Tuple, List

# 從環境變數讀取設定
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
SYMBOL = "DUSKUSDT"

# 檢查設定
if not TG_TOKEN or not TG_CHAT_ID:
    print("❌ 錯誤: TG_TOKEN 或 TG_CHAT_ID 未設定")
    sys.exit(1)

print(f"✅ 開始實時監控 {SYMBOL} 1分鐘K線...")

# 監控設定
CHECK_INTERVAL = 12  # 檢查間隔（秒） - 每12秒檢查一次
ALERT_COOLDOWN = 60  # 警報冷卻時間（秒） - 同一種警報1分鐘內不重複發送
REQUEST_DELAY = 1.0  # API請求間隔（秒）
MAX_RETRIES = 3
API_TIMEOUT = 8

# 狀態追蹤
last_alert_time = {"BUY_IN_RED": 0, "SELL_IN_GREEN": 0}
processed_kline_times = set()  # 已處理的K線時間戳

class BinanceAPI:
    """幣安API客戶端 - 優化版本"""
    def __init__(self):
        self.base_urls = [
            "https://api.binance.com/api/v3",
            "https://api1.binance.com/api/v3",
            "https://api2.binance.com/api/v3",
            "https://api3.binance.com/api/v3"
        ]
        self.current_base = 0
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.last_request_time = 0
    
    def rotate_base_url(self):
        """輪換API端點"""
        self.current_base = (self.current_base + 1) % len(self.base_urls)
    
    def make_request(self, endpoint: str, params: Dict = None, retry: int = 0) -> Optional[Dict]:
        """發送API請求"""
        # 速率控制
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        
        url = f"{self.base_urls[self.current_base]}/{endpoint}"
        
        try:
            print(f"📡 請求 {endpoint}...")
            response = self.session.get(url, params=params, timeout=API_TIMEOUT)
            
            if response.status_code == 429:  # 請求過於頻繁
                print(f"⚠️ 請求限制，輪換API端點...")
                self.rotate_base_url()
                time.sleep(2)
                if retry < MAX_RETRIES:
                    return self.make_request(endpoint, params, retry + 1)
                return None
            
            response.raise_for_status()
            self.last_request_time = time.time()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API請求失敗: {e}")
            
            if retry < MAX_RETRIES:
                wait_time = 2 ** retry + random.uniform(0.1, 0.3)
                print(f"⏳ 等待 {wait_time:.1f}秒後重試...")
                time.sleep(wait_time)
                self.rotate_base_url()
                return self.make_request(endpoint, params, retry + 1)
            
            return None
    
    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 5) -> Optional[List[Dict]]:
        """獲取K線數據 - 只獲取最近幾根"""
        data = self.make_request("klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        
        if data and isinstance(data, list):
            klines = []
            for k in data:
                try:
                    kline_time = k[0]
                    klines.append({
                        "time": kline_time,
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "quote_volume": float(k[7]),
                        "taker_buy_volume": float(k[9]),  # 主動買入成交量
                        "taker_buy_quote_volume": float(k[10])  # 主動買入成交額
                    })
                except (IndexError, ValueError) as e:
                    print(f"⚠️ 解析K線數據錯誤: {e}")
                    continue
            
            if klines:
                # 按時間排序（最新的在最後）
                klines.sort(key=lambda x: x["time"])
                return klines
        
        return None

def send_telegram(message: str) -> bool:
    """發送 Telegram 訊息"""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=API_TIMEOUT)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Telegram 錯誤: {e}")
        return False

def analyze_latest_kline(api: BinanceAPI) -> Optional[Dict]:
    """分析最新的完整K線"""
    # 獲取最近5根K線
    klines = api.get_klines(SYMBOL, "1m", 5)
    if not klines:
        print("❌ 無法獲取K線數據")
        return None
    
    # 獲取最新完整的K線（倒數第二根）
    if len(klines) >= 2:
        latest_complete = klines[-2]
    else:
        latest_complete = klines[-1]
    
    kline_time = latest_complete["time"]
    
    # 檢查是否已經處理過這根K線
    if kline_time in processed_kline_times:
        # print(f"⏭️  K線 {kline_time} 已處理，跳過")
        return None
    
    # 獲取前一K線進行比較
    if len(klines) >= 3:
        previous = klines[-3]
    elif len(klines) >= 2:
        previous = klines[-2]
    else:
        previous = latest_complete
    
    # 標記為已處理
    processed_kline_times.add(kline_time)
    
    # 如果集合太大，清理舊的時間戳（保留最近100個）
    if len(processed_kline_times) > 100:
        # 只保留最近5分鐘的時間戳
        five_min_ago = time.time() * 1000 - 300000
        processed_kline_times = {t for t in processed_kline_times if t > five_min_ago}
    
    # 判斷K線顏色
    is_red = latest_complete["close"] < latest_complete["open"]  # 陰線
    is_green = latest_complete["close"] > latest_complete["open"]  # 陽線
    
    # 計算價格變化
    price_change = ((latest_complete["close"] - previous["close"]) / previous["close"]) * 100
    
    # 計算成交量數據
    buy_volume = latest_complete["taker_buy_volume"]
    sell_volume = latest_complete["volume"] - buy_volume
    
    buy_value = latest_complete["taker_buy_quote_volume"]
    sell_value = latest_complete["quote_volume"] - buy_value
    
    # 計算買賣比率
    buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else 999
    
    # 計算成交量比率（與前一根K線比較）
    volume_ratio = latest_complete["volume"] / previous["volume"] if previous["volume"] > 0 else 1
    
    print(f"📊 分析K線 {datetime.fromtimestamp(kline_time/1000).strftime('%H:%M:%S')}:")
    print(f"   收盤價: ${latest_complete['close']:.5f}")
    print(f"   價格變化: {price_change:.2f}%")
    print(f"   K線顏色: {'🔴 陰線' if is_red else '🟢 陽線'}")
    print(f"   成交量: {latest_complete['volume']:,.0f}")
    print(f"   買入金額: ${buy_value:,.2f}")
    print(f"   賣出金額: ${sell_value:,.2f}")
    print(f"   買/賣比: {buy_sell_ratio:.2f}")
    
    return {
        "symbol": SYMBOL,
        "kline_time": kline_time,
        "open": latest_complete["open"],
        "high": latest_complete["high"],
        "low": latest_complete["low"],
        "close": latest_complete["close"],
        "volume": latest_complete["volume"],
        "quote_volume": latest_complete["quote_volume"],
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

def check_alert_conditions(market_data: Dict) -> Tuple[bool, str, str]:
    """檢查警報條件"""
    
    # 警報條件 - 可調整參數
    VOLUME_THRESHOLD = 1.5  # 成交量閾值（相對於前一根）
    BUY_SELL_THRESHOLD = 2.0  # 買賣比率閾值
    
    current_time = market_data["timestamp"]
    kline_time = market_data["kline_time"]
    
    # 情況1: 陰線但大量買入（買單是賣單的2倍以上）
    if market_data["is_red"] and market_data["buy_sell_ratio"] > BUY_SELL_THRESHOLD:
        message = f"""
🚨 <b>異常買入警報 - {SYMBOL}</b>

📉 <b>K線類型:</b> 陰線下跌
💰 <b>K線收盤價:</b> ${market_data['close']:.5f}
📊 <b>價格變化:</b> {market_data['price_change']:.2f}%
📈 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
💵 <b>買入金額:</b> ${market_data['buy_value']:,.2f}
🔄 <b>買/賣比率:</b> {market_data['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陰線中出現大量買單！</b>

⏰ <b>K線時間:</b> {datetime.fromtimestamp(kline_time/1000).strftime('%H:%M:%S')}
📡 <b>警報時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance API
"""
        return True, "BUY_IN_RED", message
    
    # 情況2: 陽線但大量賣出（賣單是買單的2倍以上）
    elif market_data["is_green"] and market_data["buy_sell_ratio"] < (1/BUY_SELL_THRESHOLD):
        message = f"""
🚨 <b>異常賣出警報 - {SYMBOL}</b>

📈 <b>K線類型:</b> 陽線上漲
💰 <b>K線收盤價:</b> ${market_data['close']:.5f}
📊 <b>價格變化:</b> {market_data['price_change']:.2f}%
📈 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
💸 <b>賣出金額:</b> ${market_data['sell_value']:,.2f}
🔄 <b>賣/買比率:</b> {1/market_data['buy_sell_ratio']:.2f}

⚠️ <b>檢測到陽線中出現大量賣單！</b>

⏰ <b>K線時間:</b> {datetime.fromtimestamp(kline_time/1000).strftime('%H:%M:%S')}
📡 <b>警報時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance API
"""
        return True, "SELL_IN_GREEN", message
    
    return False, "NORMAL", ""

def can_send_alert(alert_type: str) -> bool:
    """檢查是否可以發送警報（冷卻時間）"""
    current_time = time.time()
    last_time = last_alert_time.get(alert_type, 0)
    
    if current_time - last_time < ALERT_COOLDOWN:
        print(f"⏳ {alert_type} 警報在冷卻中，跳過...")
        return False
    
    last_alert_time[alert_type] = current_time
    return True

def real_time_monitor():
    """實時監控主函數"""
    print("=" * 70)
    print("🚀 DUSK/USDT 實時監控系統啟動")
    print("=" * 70)
    print(f"📊 交易對: {SYMBOL}")
    print(f"⏰ 時間框架: 1分鐘K線")
    print(f"🔄 檢查間隔: {CHECK_INTERVAL}秒")
    print(f"🔔 通知模式: 僅異常時發送")
    print(f"⏱️  警報冷卻: {ALERT_COOLDOWN}秒")
    print("=" * 70)
    
    # 發送啟動通知
    start_msg = f"""
🤖 <b>{SYMBOL} 實時監控系統啟動</b>

✅ 系統已啟動並開始實時監控
📊 交易對: {SYMBOL}
⏰ 時間框架: 1分鐘K線
🔄 檢查間隔: {CHECK_INTERVAL}秒
🔔 通知模式: 僅異常時發送
⏱️  警報冷卻: {ALERT_COOLDOWN}秒

⚠️ <b>監控條件:</b>
1. 陰線但大量買入（買/賣比 > 2.0）
2. 陽線但大量賣出（賣/買比 > 2.0）

🕐 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    send_telegram(start_msg)
    print("✅ 啟動通知已發送")
    
    # 初始化API
    api = BinanceAPI()
    
    # 監控循環計數器
    check_count = 0
    alert_count = 0
    
    # 主監控循環
    try:
        while True:
            check_count += 1
            current_time_str = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n🔄 檢查 #{check_count} - {current_time_str}")
            
            # 獲取並分析最新K線
            market_data = analyze_latest_kline(api)
            
            if market_data:
                # 檢查警報條件
                should_alert, alert_type, alert_message = check_alert_conditions(market_data)
                
                if should_alert and can_send_alert(alert_type):
                    print(f"⚠️  檢測到 {alert_type} 警報條件，發送通知...")
                    
                    if send_telegram(alert_message):
                        alert_count += 1
                        print(f"✅ 警報通知發送成功 (總計: {alert_count})")
                    else:
                        print("❌ 警報通知發送失敗")
                elif not should_alert:
                    print(f"📊 市場狀態正常，未觸發警報條件")
            
            # 顯示統計資訊
            if check_count % 10 == 0:  # 每10次檢查顯示一次統計
                print(f"\n📈 統計資訊:")
                print(f"   檢查次數: {check_count}")
                print(f"   警報次數: {alert_count}")
                print(f"   正常率: {((check_count - alert_count) / check_count * 100):.1f}%")
                print(f"   運行時間: {timedelta(seconds=check_count * CHECK_INTERVAL)}")
            
            # 等待下一次檢查
            print(f"⏳ 等待 {CHECK_INTERVAL} 秒後繼續...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  監控手動停止")
    except Exception as e:
        print(f"\n❌ 監控錯誤: {e}")
        import traceback
        traceback.print_exc()
        
        # 發送錯誤通知
        error_msg = f"""
⚠️ <b>{SYMBOL} 監控系統錯誤</b>

❌ 系統發生錯誤: {str(e)}
🕐 錯誤時間: {datetime.now().strftime('%H:%M:%S')}

系統將嘗試重新啟動...
"""
        send_telegram(error_msg)
        
        # 等待一段時間後重新啟動
        print("⏳ 等待30秒後嘗試重新啟動...")
        time.sleep(30)
        real_time_monitor()
    
    finally:
        # 發送停止通知
        stop_msg = f"""
🛑 <b>{SYMBOL} 實時監控系統停止</b>

✅ 監控任務已完成
📊 總檢查次數: {check_count}
🚨 總警報次數: {alert_count}
⏰ 運行時間: {timedelta(seconds=check_count * CHECK_INTERVAL)}

🕐 停止時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        send_telegram(stop_msg)
        print("✅ 停止通知已發送")

def main():
    """主入口函數"""
    print("🚀 啟動實時監控系統...")
    print(f"📅 當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        real_time_monitor()
    except Exception as e:
        print(f"❌ 系統嚴重錯誤: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # 檢查必要環境變數
    required_vars = ["TG_TOKEN", "TG_CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少環境變數: {', '.join(missing_vars)}")
        sys.exit(1)
    
    success = main()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 監控系統執行完成")
    else:
        print("❌ 監控系統執行失敗")
    print(f"⏰ 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
