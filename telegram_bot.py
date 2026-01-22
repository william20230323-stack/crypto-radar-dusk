import time
import pytz
from datetime import datetime
from typing import Dict, Any
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TAIWAN_TZ, format_taiwan_time

class EnhancedTelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
    def create_buy_in_red_alert(self, alert_data: Dict[str, Any]) -> str:
        """創建陰線大量買入警報訊息"""
        taiwan_now = datetime.now(TAIWAN_TZ)
        
        # 格式化買賣數據
        buy_volume = alert_data.get('buy_volume', 0)
        sell_volume = alert_data.get('sell_volume', 0)
        total_volume = buy_volume + sell_volume
        
        if total_volume > 0:
            buy_percentage = (buy_volume / total_volume) * 100
        else:
            buy_percentage = 0
        
        message = f"""
🚨 <b>異常買入警報 - {alert_data['symbol']}</b>

🏦 <b>交易所:</b> {alert_data['exchange']}
📉 <b>K線類型:</b> 陰線下跌
💰 <b>當前價格:</b> ${alert_data.get('price', 0):.6f}

📊 <b>買賣分析:</b>
  買入量: {buy_volume:,.2f}
  賣出量: {sell_volume:,.2f}
  買入比率: {buy_percentage:.1f}%
  買/賣比: {alert_data.get('buy_ratio', 0):.2f}

📈 <b>成交量:</b> {alert_data.get('volume', 0):,.0f}
🎯 <b>觸發條件:</b> 買/賣比 > 1.8

⚠️ <b>警報說明:</b>
陰線下跌中檢測到異常大量買單！
這可能表示有大戶在低價吸籌。

⏰ <b>數據時間:</b> {alert_data.get('kline_time', 'N/A')}
📡 <b>警報時間:</b> {format_taiwan_time(taiwan_now, '%H:%M:%S')} (台灣時間)
🌍 <b>多交易所監控系統</b>
📅 <b>日期:</b> {taiwan_now.strftime('%Y-%m-%d')}

#DUSK #買入警報 #{alert_data['exchange'].replace('.', '').replace(' ', '')}
"""
        return message
    
    def create_sell_in_green_alert(self, alert_data: Dict[str, Any]) -> str:
        """創建陽線大量賣出警報訊息"""
        taiwan_now = datetime.now(TAIWAN_TZ)
        
        # 格式化買賣數據
        buy_volume = alert_data.get('buy_volume', 0)
        sell_volume = alert_data.get('sell_volume', 0)
        total_volume = buy_volume + sell_volume
        
        if total_volume > 0:
            sell_percentage = (sell_volume / total_volume) * 100
        else:
            sell_percentage = 0
        
        message = f"""
🚨 <b>異常賣出警報 - {alert_data['symbol']}</b>

🏦 <b>交易所:</b> {alert_data['exchange']}
📈 <b>K線類型:</b> 陽線上漲
💰 <b>當前價格:</b> ${alert_data.get('price', 0):.6f}

📊 <b>買賣分析:</b>
  買入量: {buy_volume:,.2f}
  賣出量: {sell_volume:,.2f}
  賣出比率: {sell_percentage:.1f}%
  賣/買比: {alert_data.get('sell_ratio', 0):.2f}

📈 <b>成交量:</b> {alert_data.get('volume', 0):,.0f}
🎯 <b>觸發條件:</b> 賣/買比 > 1.8

⚠️ <b>警報說明:</b>
陽線上漲中檢測到異常大量賣單！
這可能表示有大戶在高價出貨。

⏰ <b>數據時間:</b> {alert_data.get('kline_time', 'N/A')}
📡 <b>警報時間:</b> {format_taiwan_time(taiwan_now, '%H:%M:%S')} (台灣時間)
🌍 <b>多交易所監控系統</b>
📅 <b>日期:</b> {taiwan_now.strftime('%Y-%m-%d')}

#DUSK #賣出警報 #{alert_data['exchange'].replace('.', '').replace(' ', '')}
"""
        return message
    
    def create_system_message(self, message_type: str, data: Dict[str, Any] = None) -> str:
        """創建系統訊息"""
        taiwan_now = datetime.now(TAIWAN_TZ)
        
        if message_type == "START":
            message = f"""
🤖 <b>DUSK/USDT 多交易所監控系統啟動</b>

✅ <b>系統狀態:</b> 已啟動並開始實時監控
🏦 <b>監控交易所:</b> {data.get('exchange_count', 6)} 家
📊 <b>交易對:</b> {data.get('symbol', 'DUSKUSDT')}
⏰ <b>時間框架:</b> {data.get('timeframe', '1分鐘')} K線
🔄 <b>掃描頻率:</b> 每15秒（台灣時間 00、15、30、45秒）
🔔 <b>通知模式:</b> 僅異常時發送
⏱️  <b>警報冷卻:</b> {data.get('cooldown', 60)}秒

🎯 <b>警報條件:</b>
1. 陰線但大量買入（買/賣比 > {data.get('threshold', 1.8)}）
2. 陽線但大量賣出（賣/買比 > {data.get('threshold', 1.8)}）

⏰ <b>啟動時間:</b> {format_taiwan_time(taiwan_now)} (台灣時間)
🌍 <b>多交易所監控系統</b>
📅 <b>系統版本:</b> 增強版 v2.0

#DUSK #系統啟動 #監控開始
"""
        
        elif message_type == "STOP":
            message = f"""
🛑 <b>DUSK/USDT 多交易所監控系統停止</b>

✅ <b>監控任務已完成</b>
📊 <b>總掃描次數:</b> {data.get('scan_count', 0)}
🚨 <b>總警報次數:</b> {data.get('alert_count', 0)}
⏰ <b>運行時間:</b> {data.get('runtime', 'N/A')}
🏦 <b>交易所成功率:</b> {data.get('success_rate', 'N/A')}%

📈 <b>最後統計:</b>
  平均掃描時間: {data.get('avg_scan_time', 'N/A')}秒
  數據成功率: {data.get('data_success_rate', 'N/A')}%
  最後掃描時間: {data.get('last_scan', 'N/A')}

⏰ <b>停止時間:</b> {format_taiwan_time(taiwan_now)} (台灣時間)
🌍 <b>多交易所監控系統</b>

#DUSK #系統停止 #監控結束
"""
        
        elif message_type == "ERROR":
            message = f"""
⚠️ <b>DUSK/USDT 監控系統錯誤</b>

❌ <b>錯誤類型:</b> {data.get('error_type', '未知錯誤')}
📝 <b>錯誤訊息:</b> {data.get('error_message', '無詳細訊息')[:200]}

🔄 <b>系統狀態:</b> 嘗試自動恢復
🏦 <b>受影響交易所:</b> {data.get('affected_exchanges', '未知')}
📊 <b>當前掃描次數:</b> {data.get('scan_count', 0)}

⏰ <b>錯誤時間:</b> {format_taiwan_time(taiwan_now)} (台灣時間)
🌍 <b>多交易所監控系統</b>

#DUSK #系統錯誤 #自動恢復
"""
        
        elif message_type == "STATUS":
            message = f"""
📊 <b>DUSK/USDT 監控系統狀態報告</b>

⏰ <b>報告時間:</b> {format_taiwan_time(taiwan_now)} (台灣時間)
🏦 <b>監控中交易所:</b> {data.get('exchange_count', 6)} 家
📈 <b>當前狀態:</b> {data.get('status', '運行中')}

📊 <b>統計數據:</b>
  總掃描次數: {data.get('total_scans', 0)}
  總警報次數: {data.get('total_alerts', 0)}
  數據成功率: {data.get('success_rate', 0):.1f}%
  運行時間: {data.get('runtime', 'N/A')}

🎯 <b>警報分佈:</b>
  買入警報: {data.get('buy_alerts', 0)} 次
  賣出警報: {data.get('sell_alerts', 0)} 次

🏦 <b>交易所狀態:</b>
{self._format_exchange_status(data.get('exchange_stats', {}))}

🌍 <b>多交易所監控系統</b>

#DUSK #狀態報告 #系統監控
"""
        else:
            message = ""
        
        return message
    
    def _format_exchange_status(self, exchange_stats: Dict) -> str:
        """格式化交易所狀態"""
        lines = []
        for exchange_id, stats in exchange_stats.items():
            success_rate = (stats['success'] / max(stats['total'], 1)) * 100
            line = f"  • {exchange_id}: {success_rate:.1f}% ({stats['success']}/{stats['total']})"
            lines.append(line)
        return "\n".join(lines) if lines else "  無數據"
    
    def send_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> bool:
        """發送警報訊息"""
        try:
            import requests
            
            # 根據警報類型創建訊息
            if alert_type == "BUY_IN_RED":
                message = self.create_buy_in_red_alert(alert_data)
            elif alert_type == "SELL_IN_GREEN":
                message = self.create_sell_in_green_alert(alert_data)
            else:
                print(f"❌ 未知的警報類型: {alert_type}")
                return False
            
            # 發送訊息
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "disable_notification": False  # 警報應該有通知
            }
            
            # 避免Telegram API限制
            time.sleep(0.5)
            
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                print(f"✅ Telegram 警報發送成功: {alert_type}")
                return True
            else:
                print(f"❌ Telegram 返回狀態碼 {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram 發送失敗: {e}")
            return False
    
    def send_system_message(self, message_type: str, data: Dict[str, Any] = None) -> bool:
        """發送系統訊息"""
        try:
            import requests
            
            if data is None:
                data = {}
            
            message = self.create_system_message(message_type, data)
            
            if not message:
                print(f"❌ 無法創建 {message_type} 訊息")
                return False
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "disable_notification": message_type != "ERROR"  # 錯誤訊息有通知
            }
            
            # 系統訊息不需要延遲
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                print(f"✅ Telegram 系統訊息發送成功: {message_type}")
                return True
            else:
                print(f"❌ Telegram 系統訊息失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram 系統訊息發送失敗: {e}")
            return False
    
    def test_connection(self) -> bool:
        """測試 Telegram 連接"""
        try:
            import requests
            
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print("✅ Telegram Bot 連接成功")
                return True
            else:
                print(f"❌ Telegram Bot 連接失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram 連接測試失敗: {e}")
            return False

# 全局實例
bot = EnhancedTelegramBot()

if __name__ == "__main__":
    # 測試連接
    if bot.test_connection():
        print("✅ Telegram Bot 初始化成功")
        
        # 測試啟動訊息
        test_data = {
            "exchange_count": 6,
            "symbol": "DUSKUSDT",
            "timeframe": "1分鐘",
            "cooldown": 60,
            "threshold": 1.8
        }
        
        success = bot.send_system_message("START", test_data)
        if success:
            print("✅ 測試訊息發送成功")
        else:
            print("❌ 測試訊息發送失敗")
    else:
        print("❌ Telegram Bot 初始化失敗")
