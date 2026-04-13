from typing import List, Dict, Any
from math import floor

def calculate_orders(
    current_positions: List[Dict[str, Any]], 
    target_values: Dict[str, float], 
    current_prices: Dict[str, float],
    only_allow_symbols: list[str] = None,
    max_positions: int = 6
) -> List[Dict[str, Any]]:
    """
    Generates orders to move from current positions to target values.
    Enforces a maximum number of concurrent positions.
    """
    buy_orders = []
    sell_orders = []
    
    current_qtys = {p['symbol']: float(p['qty']) for p in current_positions}
    
    all_symbols = set(current_qtys.keys()) | set(target_values.keys())
    
    if only_allow_symbols is not None:
        allowed_set = set(only_allow_symbols)
        all_symbols = [s for s in all_symbols if s in allowed_set]
    
    for symbol in all_symbols:
        target_val = target_values.get(symbol, 0.0)
        curr_qty = current_qtys.get(symbol, 0.0)
        price = current_prices.get(symbol)
        
        if not price:
            continue
            
        target_qty = floor(target_val / price)
        diff_qty = target_qty - curr_qty
        
        if diff_qty == 0:
            continue
            
        side = "buy" if diff_qty > 0 else "sell"
        abs_qty = int(abs(diff_qty))
        
        if abs_qty > 0:
            order = {
                "symbol": symbol,
                "qty": abs_qty,
                "side": side,
                "type": "market",
                "time_in_force": "day",
                "_target_val": abs(target_val),
            }
            if side == "buy":
                buy_orders.append(order)
            else:
                sell_orders.append(order)

    # Enforce position limit: count current held + new buys
    current_held = sum(1 for q in current_qtys.values() if q > 0)
    available_slots = max(0, max_positions - current_held)

    if len(buy_orders) > available_slots:
        buy_orders.sort(key=lambda o: o["_target_val"], reverse=True)
        buy_orders = buy_orders[:available_slots]

    # Strip internal sort key before returning
    for o in buy_orders:
        o.pop("_target_val", None)
    for o in sell_orders:
        o.pop("_target_val", None)

    return sell_orders + buy_orders
