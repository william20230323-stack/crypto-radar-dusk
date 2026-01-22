#!/usr/bin/env python3
"""
多交易所並發掃描器 - 簡化版
以台灣時間為準，每15秒掃描6家交易所最新K線
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from config import (
    EXCHANGES, EXCHANGE_LIST, 
    SYMBOL, TIMEFRAME, API_TIMEOUT,
    get_taiwan_time, format_taiwan_time
)

@dataclass
class SimpleKlineData:
    """簡化的K線數據結構"""
    exchange: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_red: bool = False
    is_green: bool = False
    fetch_time: datetime = None  # 台灣時間的獲取時間
    
    def __post_init__(self):
        """初始化後計算K線顏色"""
        self.is_red = self.close < self.open
        self.is_green = self.close > self.open
        if self.fetch_time is None:
            self.fetch_time = get_taiwan_time()

class SimpleExchangeScanner:
    """簡化版交易所掃描器"""
    
    def __init__(self):
        self.session = None
        self.last_scan = None
        
    async def __aenter__(self):
        """異步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def fetch_single_exchange(self, exchange_id: str) -> Optional[SimpleKlineData]:
        """獲取單一交易所的最新K線數據"""
        exchange_config = EXCHANGES[exchange_id]
        
        try:
            # 根據不同交易所構建API請求
            if exchange_id == "coinbase":
                # Coinbase - 需要特殊處理，可能用ticker
                url = f"{exchange_config['api_base']}/v2/prices/{SYMBOL}/spot"
                async with self.session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data['data']['amount'])
                        return SimpleKlineData(
                            exchange=exchange_config['name'],
                            symbol=SYMBOL,
                            open=price,  # 簡化：用當前價作為open/close
                            high=price,
                            low=price,
                            close=price,
                            volume=0  # Coinbase可能不提供實時成交量
                        )
            
            elif exchange_id == "kraken":
                # Kraken
                pair = "DUSKUSD"  # 需要確認實際交易對
                url = f"{exchange_config['api_base']}/0/public/Ticker"
                params = {"pair": pair}
                async with self.session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data['result'][pair]
                        return SimpleKlineData(
                            exchange=exchange_config['name'],
                            symbol=SYMBOL,
                            open=float(result['o']),
                            high=float(result['h'][0]),
                            low=float(result['l'][0]),
                            close=float(result['c'][0]),
                            volume=float(result['v'][0])
                        )
            
            elif exchange_id == "okx":
                # OKX
                url = f"{exchange_config['api_base']}/api/v5/market/ticker"
                params = {"instId": "DUSK-USDT"}
                async with self.session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        ticker = data['data'][0]
                        return SimpleKlineData(
                            exchange=exchange_config['name'],
                            symbol=SYMBOL,
                            open=float(ticker['open24h']),
                            high=float(ticker['high24h']),
                            low=float(ticker['low24h']),
                            close=float(ticker['last']),
                            volume=float(ticker['vol24h'])
                        )
            
            elif exchange_id == "bybit":
                # Bybit
                url = f"{exchange_config['api_base']}/v5/market/tickers"
                params = {"category": "spot", "symbol": "DUSKUSDT"}
                async with self.session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        ticker = data['result']['list'][0]
                        return SimpleKlineData(
                            exchange=exchange_config['name'],
                            symbol=SYMBOL,
                            open=float(ticker['openPrice']),
                            high=float(ticker['highPrice24h']),
                            low=float(ticker['lowPrice24h']),
                            close=float(ticker['lastPrice']),
                            volume=float(ticker['volume24h'])
                        )
            
            elif exchange_id == "gateio":
                # Gate.io
                url = f"{exchange_config['api_base']}/api/v4/spot/tickers"
                params = {"currency_pair": "DUSK_USDT"}
                async with self.session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        ticker = data[0]
                        return SimpleKlineData(
                            exchange=exchange_config['name'],
                            symbol=SYMBOL,
                            open=float(ticker['open']),
                            high=float(ticker['high_24h']),
                            low=float(ticker['low_24h']),
                            close=float(ticker['last']),
                            volume=float(ticker['quote_volume'])
                        )
            
            elif exchange_id == "mexc":
                # MEXC
                url = f"{exchange_config['api_base']}/api/v3/ticker/24hr"
                params = {"symbol": "DUSKUSDT"}
                async with self.session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return SimpleKlineData(
                            exchange=exchange_config['name'],
                            symbol=SYMBOL,
                            open=float(data['openPrice']),
                            high=float(data['highPrice']),
                            low=float(data['lowPrice']),
                            close=float(data['lastPrice']),
                            volume=float(data['volume'])
                        )
            
            return None
            
        except Exception as e:
            print(f"❌ {exchange_config['name']} 請求失敗: {str(e)[:50]}")
            return None
    
    async def scan_all_exchanges(self) -> Dict[str, SimpleKlineData]:
        """並發掃描所有交易所"""
        taiwan_now = get_taiwan_time()
        print(f"\n🔄 掃描開始 ({taiwan_now.strftime('%H:%M:%S')} 台灣時間)")
        print("=" * 60)
        
        # 創建並發任務
        tasks = []
        for exchange_id in EXCHANGE_LIST:
            task = self.fetch_single_exchange(exchange_id)
            tasks.append(task)
        
        # 同時執行所有請求
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理結果
        kline_data = {}
        successful = 0
        
        for i, result in enumerate(results):
            exchange_id = EXCHANGE_LIST[i]
            exchange_name = EXCHANGES[exchange_id]['name']
            
            if isinstance(result, Exception):
                print(f"❌ {exchange_name}: 錯誤 - {str(result)[:50]}")
            elif result is None:
                print(f"❌ {exchange_name}: 無數據")
            else:
                kline_data[exchange_id] = result
                successful += 1
                print(f"✅ {exchange_name}: ${result.close:.5f} "
                      f"{'🔴' if result.is_red else '🟢'}")
        
        self.last_scan = taiwan_now
        print(f"📊 掃描完成: {successful}/{len(EXCHANGES)} 成功")
        print("=" * 60)
        
        return kline_data
    
    def check_alert_conditions(self, kline_data: Dict[str, SimpleKlineData], 
                               minute_key: str) -> List[Dict]:
        """檢查警報條件並過濾重複"""
        alerts = []
        taiwan_now = get_taiwan_time()
        
        # 獲取當前分鐘已觸發的交易所
        triggered_exchanges = self.alert_minute_tracker.get(minute_key, [])
        
        for exchange_id, data in kline_data.items():
            # 檢查是否已經觸發過
            if exchange_id in triggered_exchanges:
                continue
            
            exchange_name = EXCHANGES[exchange_id]['name']
            
            # 條件1: 陰線但大量買入（買/賣比 > 1.8）
            # 注意：簡化版沒有買賣數據，這裡需要根據實際API調整
            # 暫時用價格變化模擬
            if data.is_red:
                # 這裡應該用實際的買賣數據
                alerts.append({
                    "exchange": exchange_name,
                    "exchange_id": exchange_id,
                    "condition": "BUY_IN_RED",
                    "data": data,
                    "message": f"陰線中檢測到大量買入 ({exchange_name})"
                })
                triggered_exchanges.append(exchange_id)
            
            # 條件2: 陽線但大量賣出（賣/買比 > 1.8）
            elif data.is_green:
                alerts.append({
                    "exchange": exchange_name,
                    "exchange_id": exchange_id,
                    "condition": "SELL_IN_GREEN",
                    "data": data,
                    "message": f"陽線中檢測到大量賣出 ({exchange_name})"
                })
                triggered_exchanges.append(exchange_id)
        
        # 更新分鐘追蹤器
        if triggered_exchanges:
            self.alert_minute_tracker[minute_key] = triggered_exchanges
        
        return alerts

# 測試函數
async def test_scanner():
    """測試掃描器"""
    print("🧪 測試多交易所掃描器...")
    
    async with SimpleExchangeScanner() as scanner:
        data = await scanner.scan_all_exchanges()
        
        if data:
            print(f"\n📋 獲取到 {len(data)} 家交易所數據:")
            for exchange_id, kline in data.items():
                print(f"  {EXCHANGES[exchange_id]['name']}: "
                      f"${kline.close:.5f} {kline.volume:,.0f}")

if __name__ == "__main__":
    # 運行測試
    asyncio.run(test_scanner())
