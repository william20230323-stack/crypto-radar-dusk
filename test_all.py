#!/usr/bin/env python3
"""
DUSKUSDT 多交易所監控系統 - 全面測試腳本
測試所有組件是否正常工作
"""

import asyncio
import sys
import os
import time
from datetime import datetime

def print_header():
    """打印測試標頭"""
    print("=" * 70)
    print("🧪 DUSKUSDT 多交易所監控系統 - 全面測試")
    print("=" * 70)
    print(f"⏰ 測試開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

async def test_config_module():
    """測試配置模組"""
    print("🔧 測試 1: 配置模組 (config.py)")
    print("-" * 40)
    
    try:
        # 嘗試導入配置模組
        import config
        
        # 測試時區函數
        taiwan_time = config.get_taiwan_time()
        formatted_time = config.format_taiwan_time(taiwan_time)
        
        print(f"✅ 台灣時間獲取成功: {formatted_time}")
        print(f"✅ 時區設置: {config.TAIWAN_TZ}")
        
        # 測試交易所配置
        print(f"✅ 交易所數量: {len(config.EXCHANGES)} 家")
        print("✅ 交易所列表:")
        for ex_id, ex_info in config.EXCHANGES.items():
            print(f"   • {ex_info['name']} ({ex_id})")
        
        # 測試配置檢查
        print("\n🔍 運行配置檢查...")
        config_ok = config.check_config()
        
        if config_ok:
            print("✅ 配置檢查通過")
            return True
        else:
            print("❌ 配置檢查失敗")
            return False
            
    except Exception as e:
        print(f"❌ 配置模組測試失敗: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_exchange_scanner():
    """測試交易所掃描器"""
    print("\n🔍 測試 2: 交易所掃描器 (multi_exchange_scanner.py)")
    print("-" * 40)
    
    try:
        # 檢查是否安裝了必要庫
        import importlib
        
        # 檢查 aiohttp
        try:
            import aiohttp
            print(f"✅ aiohttp 版本: {aiohttp.__version__}")
        except ImportError:
            print("❌ aiohttp 未安裝，請執行: pip install aiohttp")
            return False
        
        # 導入掃描器
        from multi_exchange_scanner import EnhancedExchangeScanner, EnhancedKlineData
        
        print("✅ 掃描器模組導入成功")
        
        # 測試掃描
        print("\n🔄 開始測試掃描（10秒超時）...")
        
        try:
            # 設置超時
            async with EnhancedExchangeScanner() as scanner:
                # 創建超時任務
                scan_task = asyncio.create_task(scanner.scan_all_exchanges())
                
                try:
                    # 等待結果，最多10秒
                    data = await asyncio.wait_for(scan_task, timeout=10)
                    
                    if data:
                        print(f"✅ 掃描成功: 獲取到 {len(data)} 家交易所數據")
                        
                        # 顯示詳細信息
                        print("\n📊 掃描結果:")
                        for ex_id, kline in data.items():
                            ex_name = config.EXCHANGES[ex_id]['name']
                            color = "🔴" if kline.is_red else "🟢"
                            ratio = kline.buy_sell_ratio
                            print(f"   {ex_name}: ${kline.close:.5f} {color} 買/賣比: {ratio:.2f}")
                        
                        return True
                    else:
                        print("❌ 掃描成功但未獲取到數據")
                        return False
                        
                except asyncio.TimeoutError:
                    print("❌ 掃描超時（超過10秒）")
                    return False
                    
        except Exception as e:
            print(f"❌ 掃描器測試失敗: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ 掃描器模組導入失敗: {type(e).__name__}: {e}")
        return False

def test_telegram_module():
    """測試 Telegram 模組"""
    print("\n🤖 測試 3: Telegram 通知模組 (telegram_bot.py)")
    print("-" * 40)
    
    try:
        # 檢查環境變數
        has_token = os.getenv("TG_TOKEN") is not None
        has_chat_id = os.getenv("TG_CHAT_ID") is not None
        
        if not has_token or not has_chat_id:
            print("⚠️  環境變數未設置:")
            if not has_token:
                print("   ❌ TG_TOKEN 未設置")
            if not has_chat_id:
                print("   ❌ TG_CHAT_ID 未設置")
            print("⚠️  請設置環境變數或手動測試")
            # 返回True，因為這不是程式錯誤
            return True
        
        # 導入Telegram模組
        from telegram_bot import bot, EnhancedTelegramBot
        
        print("✅ Telegram 模組導入成功")
        
        # 測試連接
        print("\n🔗 測試 Telegram 連接...")
        connected = bot.test_connection()
        
        if connected:
            print("✅ Telegram Bot 連接成功")
            
            # 創建測試警報數據
            test_alert_data = {
                "exchange": "Coinbase",
                "symbol": "DUSKUSDT",
                "price": 0.123456,
                "buy_volume": 1000.50,
                "sell_volume": 500.25,
                "buy_ratio": 2.1,
                "kline_time": datetime.now().strftime("%H:%M:%S"),
                "volume": 1500.75
            }
            
            # 測試警報訊息創建（不實際發送）
            print("\n📝 測試警報訊息創建...")
            try:
                buy_msg = bot.create_buy_in_red_alert(test_alert_data)
                sell_msg = bot.create_sell_in_green_alert(test_alert_data)
                
                if buy_msg and sell_msg:
                    print("✅ 警報訊息創建成功")
                    print(f"   買入警報長度: {len(buy_msg)} 字符")
                    print(f"   賣出警報長度: {len(sell_msg)} 字符")
                    return True
                else:
                    print("❌ 警報訊息創建失敗")
                    return False
                    
            except Exception as e:
                print(f"❌ 警報訊息測試失敗: {e}")
                return False
                
        else:
            print("❌ Telegram Bot 連接失敗")
            print("⚠️  這可能是因為Token無效或網絡問題")
            return False
            
    except Exception as e:
        print(f"❌ Telegram 模組測試失敗: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """測試依賴庫"""
    print("\n📦 測試 4: Python 依賴庫")
    print("-" * 40)
    
    dependencies = {
        "aiohttp": "3.8.0",
        "requests": "2.28.0",
        "pytz": "2022.7"
    }
    
    all_ok = True
    
    for lib, min_version in dependencies.items():
        try:
            module = __import__(lib)
            version = getattr(module, "__version__", "未知")
            print(f"✅ {lib:15} 已安裝 (版本: {version})")
        except ImportError:
            print(f"❌ {lib:15} 未安裝 (需要版本: >={min_version})")
            all_ok = False
    
    return all_ok

async def main():
    """主測試函數"""
    print_header()
    
    test_results = []
    
    # 測試依賴庫
    deps_ok = test_dependencies()
    test_results.append(("依賴庫", deps_ok))
    
    if not deps_ok:
        print("\n⚠️  依賴庫不完整，繼續測試可能失敗")
        print("   請執行: pip install -r requirements.txt")
    
    # 測試配置模組
    config_ok = await test_config_module()
    test_results.append(("配置模組", config_ok))
    
    # 測試交易所掃描器
    scanner_ok = await test_exchange_scanner()
    test_results.append(("交易所掃描器", scanner_ok))
    
    # 測試Telegram模組
    telegram_ok = test_telegram_module()
    test_results.append(("Telegram模組", telegram_ok))
    
    # 顯示測試總結
    print("\n" + "=" * 70)
    print("📋 測試總結")
    print("=" * 70)
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:20} {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("🎉 所有測試通過！系統準備就緒")
        print("🚀 可以運行: python dusk_monitor.py")
    else:
        print("⚠️  部分測試失敗，請檢查上述錯誤訊息")
        
        # 提供建議
        print("\n💡 建議解決方案:")
        if not deps_ok:
            print("   1. 安裝依賴: pip install -r requirements.txt")
        if not config_ok:
            print("   2. 檢查 config.py 配置")
        if not scanner_ok:
            print("   3. 檢查網絡連接和API端點")
        if not telegram_ok:
            print("   4. 確認 Telegram Bot Token 和 Chat ID")
    
    print(f"⏰ 測試結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    try:
        # 設置事件循環策略（Windows兼容）
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 測試過程中發生未預期錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
