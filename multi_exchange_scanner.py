#!/usr/bin/env python3
"""
多交易所並發掃描器 - 增強版
以台灣時間為準，每15秒掃描6家交易所最新K線
包含真實的買賣數據
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
class EnhancedKlineData:
    """增強版K線數據結構（包含買賣數據）"""
    exchange: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_volume: float = 0.0  # 主動買入量
    sell_volume: float = 0.0  # 主動賣出量
    is_red: bool = False
    is_green: bool = False
    fetch_time: datetime = None
    
    @property
    def buy_sell_ratio(self) -> float:
        """計算買賣比率"""
        if self.sell_volume > 0:
            return self.buy_volume / self.sell_volume
        elif self.buy_volume > 0:
            return 99.0  # 只有買入
        return 1.0
    
    @property
    def sell_buy_ratio(self) -> float:
        """計算賣買比率"""
        if self.buy_volume > 0:
            return self.sell_volume / self.buy_volume
        elif self.sell_volume > 0:
            return 99.0  # 只有賣出
        return 1.0
    
    def __post_init__(self):
        """初始化後計算K線顏色"""
        self.is_red = self.close < self.open
        self.is_green = self.close > self.open
        if self.fetch_time is None:
            self.fetch_time = get_taiwan_time()

class EnhancedExchangeScanner:
    """增強版交易所掃描器（包含買賣數據）"""
    
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_single_exchange(self, exchange_id: str) -> Optional[EnhancedKlineData]:
        """獲取單一交易所的最新K線數據（包含買賣數據）"""
        exchange_config = EXCHANGES[exchange_id]
        exchange_name = exchange_config['name']
        
        try:
            # 根據不同交易所使用不同的API
            if exchange_id == "coinbase":
                # Coinbase - 使用Ticker和交易紀錄
                # 先獲取價格
                ticker_url = f"{exchange_config['api_base']}/v2/prices/DUSK-USD/spot"
                async with self.session.get(ticker_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data['data']['amount'])
                        
                        # Coinbase可能不提供實時買賣數據
                        return EnhancedKlineData(
                            exchange=exchange_name,
                            symbol=SYMBOL,
                            open=price,
                            high=price,
                            low=price,
                            close=price,
                            volume=0,
                            buy_volume=0,
                            sell_volume=0
                        )
            
            elif exchange_id == "kraken":
                # Kraken - 使用Trades API獲取買賣數據
                pair = "DUSKUSD"
                url = f"{exchange_config['api_base']}/0/public/Trades"
                params = {"pair": pair, "count": 100}  # 獲取最近100筆交易
                
                async with self.session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        trades = data['result'][pair]
                        
                        # 分析最近交易
                        buy_volume = 0.0
                        sell_volume = 0.0
                        total_volume = 0.0
                        prices = []
                        
                        for trade in trades[-50:]:  # 分析最近50筆
                            price = float(trade[0])
                            volume = float(trade[1])
                            side = trade[3]  # 'b' = buy, 's' = sell
                            
                            prices.append(price)
                            total_volume += volume
                            
                            if side == 'b':
                                buy_volume += volume
                            elif side == 's':
                                sell_volume += volume
                        
                        if prices:
                            current_price = prices[-1]
                            min_price = min(prices)
                            max_price = max(prices)
                            
                            return EnhancedKlineData(
                                exchange=exchange_name,
                                symbol=SYMBOL,
                                open=prices[0],
                                high=max_price,
                                low=min_price,
                                close=current_price,
                                volume=total_volume,
                                buy_volume=buy_volume,
                                sell_volume=sell_volume
                            )
            
            elif exchange_id == "okx":
                # OKX - 使用Tickers和Trades
                # 獲取Ticker
                ticker_url = f"{exchange_config['api_base']}/api/v5/market/ticker"
                params = {"instId": "DUSK-USDT"}
                
                async with self.session.get(ticker_url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        ticker = data['data'][0]
                        
                        # 獲取最近交易
                        trades_url = f"{exchange_config['api_base']}/api/v5/market/trades"
                        async with self.session.get(trades_url, params=params, timeout=10) as resp2:
                            trades_data = await resp2.json()
                            
                            # 分析交易方向
                            buy_vol = 0.0
                            sell_vol = 0.0
                            
                            if trades_data and 'data' in trades_data:
                                for trade in trades_data['data'][-20:]:  # 最近20筆
                                    side = trade['side']  # 'buy' or 'sell'
                                    vol = float(trade['sz'])
                                    
                                    if side == 'buy':
                                        buy_vol += vol
                                    elif side == 'sell':
                                        sell_vol += vol
                            
                            return EnhancedKlineData(
                                exchange=exchange_name,
                                symbol=SYMBOL,
                                open=float(ticker['open24h']),
                                high=float(ticker['high24h']),
                                low=float(ticker['low24h']),
                                close=float(ticker['last']),
                                volume=float(ticker['vol24h']),
                                buy_volume=buy_vol,
                                sell_volume=sell_vol
                            )
            
            elif exchange_id == "bybit":
                # Bybit - 使用Ticker和Recent Trades
                ticker_url = f"{exchange_config['api_base']}/v5/market/tickers"
                params = {"category": "spot", "symbol": "DUSKUSDT"}
                
                async with self.session.get(ticker_url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['retCode'] == 0 and data['result']['list']:
                            ticker = data['result']['list'][0]
                            
                            # 獲取最近交易
                            trades_url = f"{exchange_config['api_base']}/v5/market/recent-trade"
                            async with self.session.get(trades_url, params=params, timeout=10) as resp2:
                                trades_data = await resp2.json()
                                
                                buy_vol = 0.0
                                sell_vol = 0.0
                                
                                if trades_data['retCode'] == 0:
                                    for trade in trades_data['result']['list'][-20:]:
                                        side = trade['side']
                                        vol = float(trade['size'])
                                        
                                        if side == 'Buy':
                                            buy_vol += vol
                                        elif side == 'Sell':
                                            sell_vol += vol
                                
                                return EnhancedKlineData(
                                    exchange=exchange_name,
                                    symbol=SYMBOL,
                                    open=float(ticker['openPrice']),
                                    high=float(ticker['highPrice24h']),
                                    low=float(ticker['lowPrice24h']),
                                    close=float(ticker['lastPrice']),
                                    volume=float(ticker['volume24h']),
                                    buy_volume=buy_vol,
                                    sell_volume=sell_vol
                                )
            
            elif exchange_id == "gateio":
                # Gate.io - 使用Ticker和Trades
                ticker_url = f"{exchange_config['api_base']}/api/v4/spot/tickers"
                params = {"currency_pair": "DUSK_USDT"}
                
                async with self.session.get(ticker_url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        ticker = data[0]
                        
                        # 獲取最近交易
                        trades_url = f"{exchange_config['api_base']}/api/v4/spot/trades"
                        async with self.session.get(trades_url, params=params, timeout=10) as resp2:
                            trades_data = await resp2.json()
                            
                            buy_vol = 0.0
                            sell_vol = 0.0
                            
                            for trade in trades_data[-20:]:
                                side = trade['side']  # 'buy' or 'sell'
                                vol = float(trade['amount'])
                                
                                if side == 'buy':
                                    buy_vol += vol
                                elif side == 'sell':
                                    sell_vol += vol
                            
                            return EnhancedKlineData(
                                exchange=exchange_name,
                                symbol=SYMBOL,
                                open=float(ticker['open']),
                                high=float(ticker['high_24h']),
                                low=float(ticker['low_24h']),
                                close=float(ticker['last']),
                                volume=float(ticker['quote_volume']),
                                buy_volume=buy_vol,
                                sell_volume=sell_vol
                            )
            
            elif exchange_id == "mexc":
                # MEXC - 使用Ticker和Recent Trades
                ticker_url = f"{exchange_config['api_base']}/api/v3/ticker/24hr"
                params = {"symbol": "DUSKUSDT"}
                
                async with self.session.get(ticker_url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 獲取最近交易
                        trades_url = f"{exchange_config['api_base']}/api/v3/trades"
                        async with self.session.get(trades_url, params=params, timeout=10) as resp2:
                            trades_data = await resp2.json()
                            
                            buy_vol = 0.0
                            sell_vol = 0.0
                            
                            for trade in trades_data[-20:]:
                                is_buyer_maker = trade['isBuyerMaker']
                                vol = float(trade['qty'])
                                
                                if not is_buyer_maker:  # 買方主動
                                    buy_vol += vol
                                else:  # 賣方主動
                                    sell_vol += vol
                            
                            return EnhancedKlineData(
                                exchange=exchange_name,
                                symbol=SYMBOL,
                                open=float(data['openPrice']),
                                high=float(data['highPrice']),
                                low=float(data['lowPrice']),
                                close=float(data['lastPrice']),
                                volume=float(data['volume']),
                                buy_volume=buy_vol,
                                sell_volume=sell_vol
                            )
            
            return None
            
        except Exception as e:
            print(f"❌ {exchange_name} 請求失敗: {str(e)[:80]}")
            return None
    
    async def scan_all_exchanges(self) -> Dict[str, EnhancedKlineData]:
        """並發掃描所有交易所"""
        taiwan_now = get_taiwan_time()
        print(f"\n🔄 掃描開始 ({taiwan_now.strftime('%H:%M:%S')} 台灣時間)")
        print("=" * 60)
        
        tasks = [self.fetch_single_exchange(ex_id) for ex_id in EXCHANGE_LIST]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
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
                
                # 顯示買賣比率
                ratio_info = ""
                if result.buy_volume > 0 or result.sell_volume > 0:
                    ratio_info = f" 買/賣: {result.buy_sell_ratio:.2f}"
                
                print(f"✅ {exchange_name}: ${result.close:.5f} "
                      f"{'🔴' if result.is_red else '🟢'}{ratio_info}")
        
        print(f"📊 掃描完成: {successful}/{len(EXCHANGES)} 成功")
        print("=" * 60)
        
        return kline_data

async def test_enhanced_scanner():
    """測試增強版掃描器"""
    print("🧪 測試增強版多交易所掃描器...")
    
    async with EnhancedExchangeScanner() as scanner:
        data = await scanner.scan_all_exchanges()
        
        if data:
            print(f"\n📋 詳細數據:")
            for exchange_id, kline in data.items():
                ex_name = EXCHANGES[exchange_id]['name']
                print(f"\n  {ex_name}:")
                print(f"    價格: ${kline.close:.5f}")
                print(f"    買入量: {kline.buy_volume:.2f}")
                print(f"    賣出量: {kline.sell_volume:.2f}")
                print(f"    買賣比: {kline.buy_sell_ratio:.2f}")
                print(f"    顏色: {'🔴陰線' if kline.is_red else '🟢陽線'}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_scanner())
