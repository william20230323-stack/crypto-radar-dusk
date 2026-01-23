# 修正 dusk_monitor.py 第3-4行的錯誤
sed -i '3s/def check_single_kline_alert(kline: EnhancedKLineData, exchange_id: str, name: str) -> None:/def check_single_kline_alert(kline, exchange_id, name):/' dusk_monitor.py
sed -i '4s/def check_kline_volume_alert(kline: EnhancedKLineData, exchange_id: str, name: str, minute_key: str) -> tuple:/def check_kline_volume_alert(kline, exchange_id, name, minute_key):/' dusk_monitor.py

# 移除所有類型註解
sed -i 's/: EnhancedKLineData//g' dusk_monitor.py
sed -i 's/: str//g' dusk_monitor.py
sed -i 's/: int//g' dusk_monitor.py
sed -i 's/: float//g' dusk_monitor.py
sed -i 's/: bool//g' dusk_monitor.py
sed -i 's/: tuple//g' dusk_monitor.py
sed -i 's/-> None://g' dusk_monitor.py
sed -i 's/-> tuple://g' dusk_monitor.py
sed -i 's/):/:/g' dusk_monitor.py
