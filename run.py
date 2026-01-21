#!/usr/bin/env python3
import os
import sys

# 將當前目錄加入 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# 檢查必要環境變數
required_vars = ['TG_TOKEN', 'TG_CHAT_ID']
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"❌ 缺少環境變數: {', '.join(missing)}")
    sys.exit(1)

try:
    # 直接匯入類別
    from monitor import DUSKMonitor
    
    print("=" * 40)
    print("🚀 DUSKUSDT 1分鐘監控系統")
    print("=" * 40)
    print(f"📊 交易對: DUSKUSDT")
    print(f"⏰ 時間框架: 1分鐘")
    print(f"🔔 Telegram 通知: 已啟用")
    print("=" * 40)
    
    # 啟動監控
    monitor = DUSKMonitor()
    monitor.run()
    
except KeyboardInterrupt:
    print("\n👋 監控系統已停止")
except Exception as e:
    print(f"❌ 啟動失敗: {e}")
    import traceback
    traceback.print_exc()
