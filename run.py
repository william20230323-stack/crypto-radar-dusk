#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

load_dotenv()

required_vars = ['TG_TOKEN', 'TG_CHAT_ID']
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"❌ 缺少: {', '.join(missing)}")
    sys.exit(1)

try:
    from monitor import DUSKMonitor
    
    print("=" * 40)
    print("🚀 DUSKUSDT 1分鐘監控系統")
    print("=" * 40)
    
    monitor = DUSKMonitor()
    monitor.run()
    
except KeyboardInterrupt:
    print("\n👋 已停止")
except Exception as e:
    print(f"❌ 錯誤: {e}")
