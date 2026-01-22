#!/usr/bin/env python3
"""
Binance API 快速诊断工具
用于检测哪个API端点能返回有效的K线数据
"""

import requests
import time
from datetime import datetime

def test_binance_api():
    """快速诊断 Binance API 连接和数据有效性"""
    symbol = "DUSKUSDT"
    
    # 需要测试的 API 端点（优先国际版）
    endpoints = [
        {"name": "国际版-主站", "url": "https://api.binance.com/api/v3"},
        {"name": "国际版-节点1", "url": "https://api1.binance.com/api/v3"},
        {"name": "国际版-节点2", "url": "https://api2.binance.com/api/v3"},
        {"name": "国际版-节点3", "url": "https://api3.binance.com/api/v3"},
        {"name": "美国版-主站", "url": "https://api.binance.us/api/v3"},
    ]
    
    print("🔍 开始 Binance API 连接诊断...")
    print(f"📊 交易对: {symbol}")
    print(f"🕐 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    working_endpoint = None
    
    for ep in endpoints:
        api_name = ep["name"]
        base_url = ep["url"]
        
        # 测试 1: 检查交易对价格（基础可用性）
        price_url = f"{base_url}/ticker/price?symbol={symbol}"
        # 测试 2: 检查 K 线数据（数据有效性）
        kline_url = f"{base_url}/klines?symbol={symbol}&interval=1m&limit=2"
        
        print(f"\n🔄 测试端点: {api_name} ({base_url})")
        
        try:
            # 测试价格请求
            print(f"  1. 检查交易对价格...", end="")
            price_resp = requests.get(price_url, timeout=10)
            
            if price_resp.status_code != 200:
                print(f" ❌ 失败 (状态码: {price_resp.status_code})")
                if price_resp.status_code == 400:
                    print(f"     错误信息: {price_resp.text[:200]}")
                continue
                
            price_data = price_resp.json()
            if "price" not in price_data:
                print(" ❌ 返回数据异常 (无'price'字段)")
                continue
                
            current_price = price_data["price"]
            print(f" ✅ 成功 - 当前价格: ${current_price}")
            
            # 测试 K 线请求
            print(f"  2. 获取K线数据...", end="")
            kline_resp = requests.get(kline_url, timeout=10)
            
            if kline_resp.status_code != 200:
                print(f" ❌ 失败 (状态码: {kline_resp.status_code})")
                continue
                
            kline_data = kline_resp.json()
            if not isinstance(kline_data, list) or len(kline_data) < 1:
                print(" ❌ 返回数据格式不正确")
                continue
            
            # 分析最新一根K线
            latest_kline = kline_data[-1]
            if len(latest_kline) < 7:
                print(" ❌ K线数据字段不完整")
                continue
                
            kline_time = latest_kline[0]
            close_price = float(latest_kline[4])
            volume = float(latest_kline[5])
            quote_volume = float(latest_kline[7])
            
            time_str = datetime.fromtimestamp(kline_time/1000).strftime("%H:%M:%S")
            
            print(f" ✅ 成功")
            print(f"     最新K线时间: {time_str}")
            print(f"     收盘价: ${close_price}")
            print(f"     成交量: {volume:,.0f}")
            print(f"     成交额: ${quote_volume:,.2f}")
            
            if volume > 0:
                print(f"  🎯 **成交量有效 (>0)，此端点可用！**")
                working_endpoint = {"name": api_name, "url": base_url, "volume": volume}
                break
            else:
                print(f"  ⚠️  警告: 成交量为 0，数据可能无效")
                
        except requests.exceptions.ConnectionError:
            print(f" ❌ 网络连接失败")
        except requests.exceptions.Timeout:
            print(f" ❌ 请求超时")
        except Exception as e:
            print(f" ❌ 未知错误: {type(e).__name__}: {str(e)[:100]}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    if working_endpoint:
        print(f"✅ 诊断完成！找到可用端点:")
        print(f"   名称: {working_endpoint['name']}")
        print(f"   URL: {working_endpoint['url']}")
        print(f"   测试成交量: {working_endpoint['volume']:,.0f}")
        print("\n💡 请将此 URL 设置为你的监控代码中的 `base_urls` 的第一项。")
    else:
        print("❌ 诊断完成！未找到任何返回有效成交量数据的端点。")
        print("可能原因:")
        print(f"  1. 交易对 {symbol} 在测试的所有站点均不可用")
        print("  2. 网络问题导致无法连接 Binance API")
        print("  3. 当前时间为非交易时间（但加密货币市场应24/7交易）")
        print(f"\n⚠️  请手动访问以下链接验证:")
        print(f"   https://www.binance.com/zh-TC/trade/{symbol}?type=spot")

if __name__ == "__main__":
    test_binance_api()
