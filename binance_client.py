from binance.client import Client
from config import SYMBOL, TIMEFRAME

class BinanceClient:
    def __init__(self):
        self.symbol = SYMBOL
        self.timeframe = TIMEFRAME
        self.client = Client()
    
    def get_kline_data(self, limit=100):
        try:
            klines = self.client.get_klines(
                symbol=self.symbol,
                interval=self.timeframe,
                limit=limit
            )
            data = []
            for k in klines:
                data.append({
                    'time': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': k[6],
                    'quote_volume': float(k[7]),
                    'trades': k[8],
                    'buy_volume': float(k[9]) if len(k) > 9 else 0,
                    'quote_buy_volume': float(k[10]) if len(k) > 10 else 0
                })
            return data
        except Exception as e:
            print(f"❌ Binance API 錯誤: {e}")
            return None
    
    def get_current_price(self):
        try:
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"❌ 取得價格失敗: {e}")
            return 0
