import os
import pytz
from datetime import datetime

# ======================
# 時區設定
# ======================
TAIWAN_TZ = pytz.timezone('Asia/Taipei')

def get_taiwan_time():
    """獲取台灣時間 (UTC+8)"""
    return datetime.now(TAIWAN_TZ)

def format_taiwan_time(dt=None, format_str="%Y-%m-%d %H:%M:%S"):
    """格式化台灣時間"""
    if dt is None:
        dt = get_taiwan_time()
    return dt.strftime(format_str)

# ======================
# Telegram 設定
# ======================
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# ======================
# 交易對設定
# ======================
SYMBOL = "DUSKUSDT"
TIMEFRAME = "1m"
CHECK_INTERVAL = 15  # 每15秒掃描一次（00、15、30、45秒）

# ======================
# 警報條件（只保留前兩種）
# ======================
BUY_SELL_THRESHOLD = 1.8  # 買賣比率閾值
# 注意：已移除 VOLUME_THRESHOLD 和 PRICE_CHANGE_THRESHOLD

# ======================
# 監控設定
# ======================
ALERT_COOLDOWN = 60  # 警報冷卻時間（秒）
MAX_RETRIES = 3
API_TIMEOUT = 10
REQUEST_DELAY = 1.0  # API請求間隔（秒）

# ======================
# 6家交易所配置（完全不用幣安）
# ======================
EXCHANGES = {
    "coinbase": {
        "name": "Coinbase",
        "api_base": "https://api.coinbase.com",
        "endpoint": "/v2/exchange-rates",  # 需要確認實際DUSKUSDT端點
        "symbol_param": "currency",
        "symbol_mapping": {"DUSKUSDT": "DUSK-USD"},  # 需要確認
        "timeframe": "1m"
    },
    "kraken": {
        "name": "Kraken",
        "api_base": "https://api.kraken.com",
        "endpoint": "/0/public/OHLC",
        "symbol_param": "pair",
        "symbol_mapping": {"DUSKUSDT": "DUSKUSD"},  # 需要確認
        "interval_param": "interval",
        "interval_mapping": {"1m": 1}
    },
    "okx": {
        "name": "OKX",
        "api_base": "https://www.okx.com",
        "endpoint": "/api/v5/market/candles",
        "symbol_param": "instId",
        "symbol_mapping": {"DUSKUSDT": "DUSK-USDT"},
        "interval_param": "bar",
        "interval_mapping": {"1m": "1m"}
    },
    "bybit": {
        "name": "Bybit",
        "api_base": "https://api.bybit.com",
        "endpoint": "/v5/market/kline",
        "symbol_param": "symbol",
        "symbol_mapping": {"DUSKUSDT": "DUSKUSDT"},
        "interval_param": "interval",
        "interval_mapping": {"1m": 1}
    },
    "gateio": {
        "name": "Gate.io",
        "api_base": "https://api.gate.io",
        "endpoint": "/api/v4/spot/candlesticks",
        "symbol_param": "currency_pair",
        "symbol_mapping": {"DUSKUSDT": "DUSK_USDT"},
        "interval_param": "interval",
        "interval_mapping": {"1m": "1m"}
    },
    "mexc": {
        "name": "MEXC",
        "api_base": "https://api.mexc.com",
        "endpoint": "/api/v3/klines",
        "symbol_param": "symbol",
        "symbol_mapping": {"DUSKUSDT": "DUSKUSDT"},
        "interval_param": "interval",
        "interval_mapping": {"1m": "1m"}
    }
}

# 交易所列表（方便迭代）
EXCHANGE_LIST = list(EXCHANGES.keys())

# ======================
# 數據解析配置
# ======================
# 不同交易所的K線數據字段映射
KLINE_FIELD_MAPPING = {
    "coinbase": {"time": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5},
    "kraken": {"time": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 6},
    "okx": {"time": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5},
    "bybit": {"time": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5},
    "gateio": {"time": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5},
    "mexc": {"time": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5}
}

# ======================
# 掃描時間點配置
# ======================
SCAN_SECONDS = [0, 15, 30, 45]  # 台灣時間的秒數

def check_config():
    """檢查配置是否完整"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TG_TOKEN 未設定")
    if not TELEGRAM_CHAT_ID:
        errors.append("TG_CHAT_ID 未設定")
    
    # 檢查交易所配置
    required_exchanges = ["coinbase", "kraken", "okx", "bybit", "gateio", "mexc"]
    for exchange in required_exchanges:
        if exchange not in EXCHANGES:
            errors.append(f"交易所 {exchange} 未配置")
    
    if errors:
        print("❌ 配置錯誤:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print(f"✅ 配置檢查完成")
    print(f"   監控交易對: {SYMBOL}")
    print(f"   時間框架: {TIMEFRAME}")
    print(f"   掃描間隔: 每15秒（台灣時間 {SCAN_SECONDS} 秒）")
    print(f"   交易所數量: {len(EXCHANGES)} 家")
    print(f"   時區: 台灣時間 (UTC+8)")
    print(f"   當前台灣時間: {format_taiwan_time()}")
    
    return True

if __name__ == "__main__":
    check_config()
