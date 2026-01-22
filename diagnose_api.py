# diagnose_api.py
import requests
import time
from datetime import datetime

def test_binance_api():
    """快速診斷 Binance API 連接和數據有效性"""
    symbol = \"DUSKUSDT\"
    
    # 需要測試的 API 端點（優先國際版）
    endpoints = [
        {\"name\": \"國際版-主站\", \"url\": \"https://api.binance.com/api/v3\"},
        {\"name\": \"國際版-節點1\", \"url\": \"https://api1.binance.com/api/v3\"},
        {\"name\": \"國際版-節點2\", \"url\": \"https://api2.binance.com/api/v3\"},
        {\"name\": \"國際版-節點3\", \"url\": \"https://api3.binance.com/api/v3\"},
        {\"name\": \"美國版-主站\", \"url\": \"https://api.binance.us/api/v3\"},
    ]
    
    print(\"🔍 開始 Binance API 連接診斷...\")
    print(f\"📊 交易對: {symbol}\")
    print(f\"🕐 診斷時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\")
    print(\"=\" * 60)
    
    working_endpoint = None
    
    for ep in endpoints:
        api_name = ep[\"name\"]
        base_url = ep[\"url\"]
        
        # 測試 1: 檢查交易對價格（基礎可用性）
        price_url = f\"{base_url}/ticker/price?symbol={symbol}\"
        # 測試 2: 檢查 K 線數據（數據有效性）
        kline_url = f\"{base_url}/klines?symbol={symbol}&interval=1m&limit=2\"
        
        print(f\"\\n🔄 測試端點: {api_name} ({base_url})\")
        
        try:
            # 測試價格請求
            print(f\"  1. 檢查交易對價格...\", end=\"\")
            price_resp = requests.get(price_url, timeout=10)
            
            if price_resp.status_code != 200:
                print(f\" ❌ 失敗 (狀態碼: {price_resp.status_code})\")
                if price_resp.status_code == 400:
                    print(f\"     錯誤信息: {price_resp.text[:200]}\")
                continue
                
            price_data = price_resp.json()
            if \"price\" not in price_data:
                print(\" ❌ 返回數據異常 (無'price'字段)\")
                continue
                
            current_price = price_data[\"price\"]
            print(f\" ✅ 成功 - 當前價格: ${current_price}\")
            
            # 測試 K 線請求
            print(f\"  2. 獲取K線數據...\", end=\"\")
            kline_resp = requests.get(kline_url, timeout=10)
            
            if kline_resp.status_code != 200:
                print(f\" ❌ 失敗 (狀態碼: {kline_resp.status_code})\")
                continue
                
            kline_data = kline_resp.json()
            if not isinstance(kline_data, list) or len(kline_data) < 1:
                print(\" ❌ 返回數據格式不正確\")
                continue
            
            # 分析最新一根K線
            latest_kline = kline_data[-1]
            if len(latest_kline) < 7:  # 確保有成交量字段
                print(\" ❌ K線數據字段不完整\")
                continue
                
            kline_time = latest_kline[0]  # 開盤時間戳
            close_price = float(latest_kline[4])  # 收盤價
            volume = float(latest_kline[5])  # 成交量
            quote_volume = float(latest_kline[7])  # 成交額
            
            # 格式化時間
            time_str = datetime.fromtimestamp(kline_time/1000).strftime(\"%H:%M:%S\")
            
            print(f\" ✅ 成功\")
            print(f\"     最新K線時間: {time_str}\")
            print(f\"     收盤價: ${close_price}\")
            print(f\"     成交量: {volume:,.0f}\")
            print(f\"     成交額: ${quote_volume:,.2f}\")
            
            # 關鍵檢查：成交量是否有效
            if volume > 0:
                print(f\"  🎯 **成交量有效 (>0)，此端點可用！**\")
                working_endpoint = {\"name\": api_name, \"url\": base_url, \"volume\": volume}
                # 找到一個有效的就停止測試
                break
            else:
                print(f\"  ⚠️  警告: 成交量為 0，數據可能無效\")
                
        except requests.exceptions.ConnectionError:
            print(f\" ❌ 網絡連接失敗\")
        except requests.exceptions.Timeout:
            print(f\" ❌ 請求超時\")
        except Exception as e:
            print(f\" ❌ 未知錯誤: {type(e).__name__}: {str(e)[:100]}\")
        
        # 避免請求過快，稍作停頓
        time.sleep(0.5)
    
    print(\"\\n\" + \"=\" * 60)
    if working_endpoint:
        print(f\"✅ 診斷完成！找到可用端點:\")
        print(f\"   名稱: {working_endpoint['name']}\")
        print(f\"   URL: {working_endpoint['url']}\")
        print(f\"   測試成交量: {working_endpoint['volume']:,.0f}\")
        print(\"\\n💡 請將此 URL 設置為你的監控代碼中的 `base_urls` 的第一項。\")
    else:
        print(\"❌ 診斷完成！未找到任何返回有效成交量數據的端點。\")
        print(\"可能原因:\")
        print(\"  1. 交易對 {symbol} 在測試的所有站點均不可用\")
        print(\"  2. 網絡問題導致無法連接 Binance API\")
        print(\"  3. 當前時間為非交易時間（但加密貨幣市場應24/7交易）\")
        print(\"\\n⚠️  請手動訪問以下鏈接驗證:\")
        print(f\"   https://www.binance.com/zh-TC/trade/{symbol}?type=spot\")

if __name__ == \"__main__\":
    test_binance_api()
