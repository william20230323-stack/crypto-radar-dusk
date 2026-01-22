#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime, timedelta
import random
import traceback
import math

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
CHECK_INTERVAL = 60  # 檢查間隔（秒）- 改為60秒，對齊每分鐘
ALERT_COOLDOWN = 60  # 警報冷卻時間（秒）
REQUEST_DELAY = 2.0  # API請求間隔（秒）
MAX_RETRIES = 3
API_TIMEOUT = 10

# 警報條件閾值
VOLUME_THRESHOLD = 1.8  # 成交量閾值
BUY_SELL_THRESHOLD = 1.8  # 買賣比率閾值
PRICE_CHANGE_THRESHOLD = 1.0  # 價格變化閾值（%）

# 狀態追蹤
last_alert_time = {"BUY_IN_RED": 0, "SELL_IN_GREEN": 0, "VOLUME_SPIKE": 0}
last_processed_kline_time = 0

class BinanceAPI:
    """幣安API客戶端（支援國際版和美國版）"""
    def __init__(self):
        # 多個API端點，優先嘗試美國版，再嘗試國際版
        self.base_urls = [
            "https://api.binance.us/api/v3",  # 美國版
            "https://api1.binance.us/api/v3",
            "https://api2.binance.us/api/v3",
            "https://api.binance.com/api/v3",  # 國際版（備用）
            "https://api1.binance.com/api/v3",
            "https://api2.binance.com/api/v3",
            "https://api3.binance.com/api/v3",
        ]
        self.current_base = 0
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-MBX-APIKEY": ""
        })
        self.last_request_time = 0
        self.request_count = 0
        self.reset_time = time.time()
        self.api_type = "未知"  # 用於標記當前使用的API類型
    
    def rotate_base_url(self):
        """輪換API端點"""
        self.current_base = (self.current_base + 1) % len(self.base_urls)
        url = self.base_urls[self.current_base]
        if "binance.us" in url:
            self.api_type = "美國版"
        else:
            self.api_type = "國際版"
        print(f"🔄 輪換到 {self.api_type} API端點 ({self.current_base + 1}/{len(self.base_urls)})")
    
    def check_rate_limit(self):
        """檢查並實施速率限制"""
        current_time = time.time()
        
        # 每分鐘重置計數器
        if current_time - self.reset_time > 60:
            self.request_count = 0
            self.reset_time = current_time
        
        # 速率限制：每分鐘1200次請求
        if self.request_count >= 1000:
            wait_time = 60 - (current_time - self.reset_time)
            if wait_time > 0:
                print(f"⏳ 接近速率限制，等待 {wait_time:.1f}秒...")
                time.sleep(wait_time)
                self.reset_time = time.time()
                self.request_count = 0
    
    def make_request(self, endpoint: str, params: dict = None, retry: int = 0):
        """發送API請求"""
        # 速率控制和延遲
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        
        # 檢查速率限制
        self.check_rate_limit()
        
        url = f"{self.base_urls[self.current_base]}/{endpoint}"
        
        try:
            print(f"📡 請求 {endpoint} (API: {self.api_type})...")
            
            # 根據API類型調整參數
            request_params = params.copy() if params else {}
            
            response = self.session.get(
                url, 
                params=request_params, 
                timeout=API_TIMEOUT,
                verify=True
            )
            
            self.request_count += 1
            self.last_request_time = current_time
            
            # 處理429錯誤（請求過多）
            if response.status_code == 429:
                print(f"⚠️ 請求限制 (429)，輪換API端點...")
                self.rotate_base_url()
                wait_time = 60 + random.uniform(1, 5)
                print(f"⏳ 等待 {wait_time:.1f}秒後重試...")
                time.sleep(wait_time)
                
                if retry < MAX_RETRIES:
                    return self.make_request(endpoint, params, retry + 1)
                return None
            
            # 處理403/451錯誤（地理限制）
            if response.status_code in [403, 451]:
                print(f"❌ 地理限制 ({response.status_code})，嘗試其他端點...")
                self.rotate_base_url()
                
                if retry < MAX_RETRIES:
                    wait_time = 5 + random.uniform(1, 3)
                    print(f"⏳ 等待 {wait_time:.1f}秒後重試...")
                    time.sleep(wait_time)
                    return self.make_request(endpoint, params, retry + 1)
                return None
            
            # 處理其他錯誤狀態碼
            if response.status_code != 200:
                print(f"⚠️ API返回狀態碼 {response.status_code}: {response.text[:200]}")
                
                if retry < MAX_RETRIES:
                    wait_time = 2 ** retry + random.uniform(0.5, 1.5)
                    print(f"⏳ 等待 {wait_time:.1f}秒後重試...")
                    time.sleep(wait_time)
                    self.rotate_base_url()
                    return self.make_request(endpoint, params, retry + 1)
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API請求失敗: {type(e).__name__}: {e}")
            
            if retry < MAX_RETRIES:
                wait_time = 2 ** retry + random.uniform(1, 3)
                print(f"⏳ 等待 {wait_time:.1f}秒後重試...")
                time.sleep(wait_time)
                self.rotate_base_url()
                return self.make_request(endpoint, params, retry + 1)
            
            return None
    
    def get_latest_kline(self, symbol: str, interval: str = "1m"):
        """獲取最新一根完整K線數據"""
        print(f"🔍 獲取 {symbol} 最新K線數據...")
        
        try:
            # 獲取最近2根K線（用於比較）
            data = self.make_request("klines", {
                "symbol": symbol,
                "interval": interval,
                "limit": 2
            })
            
            if data and isinstance(data, list) and len(data) >= 1:
                # 使用最新一根完整K線
                k = data[-1]
                kline_time = k[0]
                
                # 獲取前一根K線用於比較
                prev_k = data[-2] if len(data) >= 2 else k
                
                kline_data = {
                    "time": kline_time,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "quote_volume": float(k[7]),
                    "taker_buy_volume": float(k[9]),
                    "taker_buy_quote_volume": float(k[10])
                }
                
                prev_kline_data = {
                    "time": prev_k[0],
                    "close": float(prev_k[4]),
                    "volume": float(prev_k[5])
                }
                
                kline_time_str = datetime.fromtimestamp(kline_time/1000).strftime('%H:%M:%S')
                print(f"✅ 成功獲取K線數據 (時間: {kline_time_str}, API: {self.api_type})")
                return {
                    "current": kline_data,
                    "previous": prev_kline_data
                }
            
            print("❌ 獲取的K線數據格式不正確")
            return None
            
        except Exception as e:
            print(f"❌ 獲取K線數據時發生錯誤: {type(e).__name__}: {e}")
            return None
    
    def check_symbol_availability(self, symbol: str) -> bool:
        """檢查交易對是否可用"""
        try:
            print(f"🔍 檢查交易對 {symbol} 可用性...")
            
            # 嘗試獲取價格信息
            ticker = self.make_request("ticker/price", {"symbol": symbol})
            
            if ticker and "price" in ticker:
                print(f"✅ 交易對 {symbol} 在 {self.api_type} 可用")
                return True
            
            print(f"❌ 交易對 {symbol} 在 {self.api_type} 不可用")
            return False
            
        except Exception as e:
            print(f"❌ 檢查交易對可用性時發生錯誤: {e}")
            return False

def send_telegram(message: str) -> bool:
    """發送 Telegram 訊息"""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        time.sleep(0.3)  # 避免Telegram API限制
        response = requests.post(url, json=payload, timeout=API_TIMEOUT)
        
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Telegram 返回狀態碼 {response.status_code}: {response.text[:200]}")
            return False
        
    except Exception as e:
        print(f"❌ Telegram 錯誤: {type(e).__name__}: {e}")
        return False

def analyze_single_kline(api: BinanceAPI):
    """分析單根K線"""
    global last_processed_kline_time
    
    # 獲取最新K線數據
    kline_data = api.get_latest_kline(SYMBOL, "1m")
    if not kline_data:
        print("❌ 無法獲取K線數據")
        return None
    
    current_kline = kline_data["current"]
    previous_kline = kline_data["previous"]
    
    kline_time = current_kline["time"]
    kline_time_str = datetime.fromtimestamp(kline_time/1000).strftime("%H:%M:%S")
    
    # 調試信息
    current_timestamp = int(time.time() * 1000)
    print(f"[DEBUG] 當前時間戳: {current_timestamp}")
    print(f"[DEBUG] K線時間戳: {kline_time}")
    print(f"[DEBUG] 最後處理時間: {last_processed_kline_time}")
    print(f"[DEBUG] 時間差: {current_timestamp - kline_time}ms")
    
    # 檢查是否已經處理過這根K線
    # 只跳過完全相同的K線時間，但允許處理新的K線
    if kline_time <= last_processed_kline_time:
        print(f"⏭️  K線 {kline_time_str} 已處理或過時，跳過")
        return None
    
    # 更新最後處理的K線時間
    last_processed_kline_time = kline_time
    
    # 判斷K線顏色
    is_red = current_kline["close"] < current_kline["open"]  # 陰線
    is_green = current_kline["close"] > current_kline["open"]  # 陽線
    
    # 計算價格變化
    price_change = ((current_kline["close"] - previous_kline["close"]) / previous_kline["close"]) * 100
    
    # 計算成交量數據
    buy_volume = current_kline.get("taker_buy_volume", 0)
    sell_volume = current_kline["volume"] - buy_volume
    
    buy_value = current_kline.get("taker_buy_quote_volume", 0)
    sell_value = current_kline["quote_volume"] - buy_value
    
    # 計算買賣比率
    if sell_volume > 0:
        buy_sell_ratio = buy_volume / sell_volume
    else:
        buy_sell_ratio = 999 if buy_volume > 0 else 1
    
    # 計算成交量比率（與前一根K線比較）
    if previous_kline["volume"] > 0:
        volume_ratio = current_kline["volume"] / previous_kline["volume"]
    else:
        volume_ratio = 1
    
    print(f"📊 分析K線 {kline_time_str}:")
    print(f"   收盤價: ${current_kline['close']:.5f}")
    print(f"   價格變化: {price_change:.2f}%")
    print(f"   K線顏色: {'🔴 陰線' if is_red else '🟢 陽線'}")
    print(f"   成交量: {current_kline['volume']:,.0f}")
    print(f"   成交量比率: {volume_ratio:.2f}x")
    print(f"   買入金額: ${buy_value:,.2f}")
    print(f"   賣出金額: ${sell_value:,.2f}")
    print(f"   買/賣比: {buy_sell_ratio:.2f}")
    
    return {
        "symbol": SYMBOL,
        "kline_time": kline_time,
        "kline_time_str": kline_time_str,
        "open": current_kline["open"],
        "high": current_kline["high"],
        "low": current_kline["low"],
        "close": current_kline["close"],
        "volume": current_kline["volume"],
        "quote_volume": current_kline["quote_volume"],
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

def check_alert_conditions(market_data: dict):
    """檢查警報條件"""
    
    current_time = market_data["timestamp"]
    kline_time_str = market_data["kline_time_str"]
    
    # 情況1: 陰線但大量買入
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

⏰ <b>K線時間:</b> {kline_time_str}
📡 <b>警報時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance API
"""
        return True, "BUY_IN_RED", message
    
    # 情況2: 陽線但大量賣出
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

⏰ <b>K線時間:</b> {kline_time_str}
📡 <b>警報時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance API
"""
        return True, "SELL_IN_GREEN", message
    
    # 情況3: 成交量異常放大
    elif market_data["volume_ratio"] > VOLUME_THRESHOLD and abs(market_data["price_change"]) > PRICE_CHANGE_THRESHOLD:
        kline_type = "陰線" if market_data["is_red"] else "陽線"
        change_direction = "下跌" if market_data["price_change"] < 0 else "上漲"
        
        message = f"""
⚠️ <b>成交量異常警報 - {SYMBOL}</b>

🎨 <b>K線類型:</b> {kline_type}
💰 <b>K線收盤價:</b> ${market_data['close']:.5f}
📊 <b>價格變化:</b> {market_data['price_change']:.2f}% ({change_direction})
📈 <b>成交量比率:</b> {market_data['volume_ratio']:.2f}x
📦 <b>成交量:</b> {market_data['volume']:,.0f}

⏰ <b>K線時間:</b> {kline_time_str}
📡 <b>警報時間:</b> {current_time}
🔗 <b>數據來源:</b> Binance API
"""
        return True, "VOLUME_SPIKE", message
    
    return False, "NORMAL", ""

def can_send_alert(alert_type: str) -> bool:
    """檢查是否可以發送警報（冷卻時間）"""
    current_time = time.time()
    last_time = last_alert_time.get(alert_type, 0)
    
    if current_time - last_time < ALERT_COOLDOWN:
        remaining = ALERT_COOLDOWN - (current_time - last_time)
        print(f"⏳ {alert_type} 警報在冷卻中，還需 {remaining:.0f}秒，跳過...")
        return False
    
    last_alert_time[alert_type] = current_time
    return True

def print_banner():
    """顯示啟動橫幅"""
    print("=" * 70)
    print("🚀 DUSK/USDT 單K線實時監控系統")
    print("=" * 70)
    print(f"📊 交易對: {SYMBOL}")
    print(f"⏰ 時間框架: 1分鐘K線")
    print(f"🔄 檢查間隔: 每分鐘00秒整點執行")
    print(f"🔔 通知模式: 僅異常時發送")
    print(f"⏱️  警報冷卻: {ALERT_COOLDOWN}秒")
    print(f"🌐 API類型: 自動選擇（美國版/國際版）")
    print("=" * 70)
    print(f"📈 警報閾值設定:")
    print(f"   買賣比率: >{BUY_SELL_THRESHOLD:.1f}")
    print(f"   成交量比率: >{VOLUME_THRESHOLD:.1f}")
    print(f"   價格變化: >{PRICE_CHANGE_THRESHOLD:.1f}%")
    print("=" * 70)

def wait_until_next_minute():
    """等待到下一個分鐘的00秒"""
    now = datetime.now()
    current_second = now.second
    current_microsecond = now.microsecond
    
    # 計算到下一分鐘00秒需要等待的時間
    seconds_to_wait = 60 - current_second
    
    # 如果現在就是00秒（或非常接近），則直接返回
    if seconds_to_wait <= 1:
        if seconds_to_wait > 0:
            # 微調，確保在00秒時執行
            time.sleep(seconds_to_wait)
        return
    
    # 顯示等待信息
    next_minute_time = (now + timedelta(seconds=seconds_to_wait)).strftime("%H:%M:%S")
    print(f"⏳ 等待 {seconds_to_wait} 秒直到下一分鐘整點 ({next_minute_time})...")
    
    # 等待到下一個分鐘的00秒
    time.sleep(seconds_to_wait)
    
    # 微調，確保精確對齊
    time.sleep(0.01)  # 10毫秒微調

def real_time_monitor():
    """實時監控主函數"""
    print_banner()
    
    # 初始化API
    api = BinanceAPI()
    
    # 檢查交易對可用性
    print("🔍 檢查交易對可用性...")
    if not api.check_symbol_availability(SYMBOL):
        error_msg = f"""
❌ <b>{SYMBOL} 監控系統啟動失敗</b>

交易對 {SYMBOL} 在當前可用的 API 端點不可用。
請確認該交易對在幣安是否存在。

🕐 時間: {datetime.now().strftime('%H:%M:%S')}
"""
        send_telegram(error_msg)
        print("❌ 交易對不可用，停止監控")
        return False
    
    # 發送啟動通知
    start_msg = f"""
🤖 <b>{SYMBOL} 單K線監控系統啟動</b>

✅ 系統已啟動並開始實時監控
📊 交易對: {SYMBOL}
⏰ 時間框架: 1分鐘K線
🔄 檢查間隔: 每分鐘00秒整點執行
🔔 通知模式: 僅異常時發送
⏱️  警報冷卻: {ALERT_COOLDOWN}秒
🌐 API類型: {api.api_type}

📈 <b>警報條件:</b>
1. 陰線但大量買入（買/賣比 > {BUY_SELL_THRESHOLD}）
2. 陽線但大量賣出（賣/買比 > {BUY_SELL_THRESHOLD}）
3. 成交量異常放大（成交量比率 > {VOLUME_THRESHOLD}）

🕐 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    send_telegram(start_msg)
    print("✅ 啟動通知已發送")
    
    # 監控循環計數器
    check_count = 0
    alert_count = 0
    error_count = 0
    
    # 第一次執行前等待到下一分鐘整點
    print("\n⏳ 首次執行，等待到下一個分鐘的00秒...")
    wait_until_next_minute()
    
    # 主監控循環
    try:
        while True:
            check_count += 1
            current_time_str = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n🔄 檢查 #{check_count} - {current_time_str} (整點執行)")
            
            # 分析單根K線
            market_data = analyze_single_kline(api)
            
            if market_data:
                # 重置錯誤計數器
                error_count = 0
                
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
            else:
                error_count += 1
                print(f"⚠️ 數據獲取失敗 (連續錯誤: {error_count})")
                
                # 如果連續錯誤太多，等待更長時間
                if error_count >= 3:
                    wait_time = 60 + random.uniform(10, 30)
                    print(f"⏳ 連續錯誤過多，等待 {wait_time:.1f}秒...")
                    time.sleep(wait_time)
                    error_count = 0
            
            # 顯示統計資訊
            if check_count % 10 == 0:
                print(f"\n📈 統計資訊:")
                print(f"   檢查次數: {check_count}")
                print(f"   警報次數: {alert_count}")
                print(f"   錯誤次數: {error_count}")
                success_rate = ((check_count - error_count) / check_count * 100) if check_count > 0 else 0
                print(f"   成功率: {success_rate:.1f}%")
                print(f"   運行時間: {timedelta(seconds=check_count * 60)}")
                print(f"   API類型: {api.api_type}")
            
            # 等待到下一個分鐘的00秒
            print(f"⏳ 等待到下一個分鐘的00秒...")
            wait_until_next_minute()
            
    except KeyboardInterrupt:
        print("\n\n⏹️  監控手動停止")
    except Exception as e:
        print(f"\n❌ 監控錯誤: {type(e).__name__}: {e}")
        traceback.print_exc()
        
        # 發送錯誤通知
        error_msg = f"""
⚠️ <b>{SYMBOL} 監控系統錯誤</b>

❌ 系統發生錯誤: {str(e)}
🕐 錯誤時間: {datetime.now().strftime('%H:%M:%S')}

系統將嘗試重新啟動...
"""
        send_telegram(error_msg)
        
        # 等待後重新啟動
        print("⏳ 等待30秒後嘗試重新啟動...")
        time.sleep(30)
        return False
    
    finally:
        # 發送停止通知
        stop_msg = f"""
🛑 <b>{SYMBOL} 實時監控系統停止</b>

✅ 監控任務已完成
📊 總檢查次數: {check_count}
🚨 總警報次數: {alert_count}
⏰ 運行時間: {timedelta(seconds=check_count * 60)}

🕐 停止時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        send_telegram(stop_msg)
        print("✅ 停止通知已發送")
    
    return True

def main():
    """主入口函數"""
    print("🚀 啟動單K線實時監控系統...")
    print(f"📅 當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 最大重啟次數
    max_restarts = 3
    restarts = 0
    
    while restarts < max_restarts:
        try:
            success = real_time_monitor()
            if success:
                return True
            else:
                restarts += 1
                print(f"🔄 嘗試重啟 ({restarts}/{max_restarts})...")
                # 重啟時也等待到整點
                wait_until_next_minute()
        except Exception as e:
            print(f"❌ 系統嚴重錯誤: {type(e).__name__}: {e}")
            restarts += 1
            if restarts < max_restarts:
                print(f"🔄 等待後重啟 ({restarts}/{max_restarts})...")
                time.sleep(30)
    
    print("❌ 達到最大重啟次數，停止系統")
    return False

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
