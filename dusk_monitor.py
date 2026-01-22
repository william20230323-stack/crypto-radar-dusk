# 在 dusk_monitor.py 中修改這個函數：

def check_single_kline_alert(kline: EnhancedKlineData, exchange_id: str, 
                            minute_key: str) -> tuple:
    """
    檢查單一K線的警報條件（使用真實買賣數據）
    返回: (should_alert, alert_type, alert_data, message)
    """
    exchange_name = EXCHANGES[exchange_id]['name']
    
    # 檢查是否已經在這分鐘內觸發過
    triggered = alert_minute_tracker.get(minute_key, [])
    if exchange_id in triggered:
        return False, None, None, f"{exchange_name} 本分鐘已觸發過警報"
    
    # 使用真實的買賣數據
    buy_sell_ratio = kline.buy_sell_ratio
    sell_buy_ratio = kline.sell_buy_ratio
    
    # 條件1: 陰線但大量買入（買/賣比 > 1.8）
    if kline.is_red and buy_sell_ratio > BUY_SELL_THRESHOLD:
        # 記錄這分鐘已觸發
        if minute_key not in alert_minute_tracker:
            alert_minute_tracker[minute_key] = []
        alert_minute_tracker[minute_key].append(exchange_id)
        
        alert_data = {
            "exchange": exchange_name,
            "symbol": SYMBOL,
            "price": kline.close,
            "buy_volume": kline.buy_volume,
            "sell_volume": kline.sell_volume,
            "buy_ratio": buy_sell_ratio,
            "kline_time": format_taiwan_time(kline.fetch_time, "%H:%M:%S"),
            "volume": kline.volume
        }
        
        return True, "BUY_IN_RED", alert_data, f"{exchange_name} 陰線大量買入 (比率: {buy_sell_ratio:.2f})"
    
    # 條件2: 陽線但大量賣出（賣/買比 > 1.8）
    elif kline.is_green and sell_buy_ratio > BUY_SELL_THRESHOLD:
        # 記錄這分鐘已觸發
        if minute_key not in alert_minute_tracker:
            alert_minute_tracker[minute_key] = []
        alert_minute_tracker[minute_key].append(exchange_id)
        
        alert_data = {
            "exchange": exchange_name,
            "symbol": SYMBOL,
            "price": kline.close,
            "buy_volume": kline.buy_volume,
            "sell_volume": kline.sell_volume,
            "sell_ratio": sell_buy_ratio,
            "kline_time": format_taiwan_time(kline.fetch_time, "%H:%M:%S"),
            "volume": kline.volume
        }
        
        return True, "SELL_IN_GREEN", alert_data, f"{exchange_name} 陽線大量賣出 (比率: {sell_buy_ratio:.2f})"
    
    return False, None, None, f"{exchange_name} 正常 (買/賣: {buy_sell_ratio:.2f})"
