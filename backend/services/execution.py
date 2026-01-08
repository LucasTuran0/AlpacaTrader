from typing import List, Dict, Any
from math import floor

def calculate_orders(
    current_positions: List[Dict[str, Any]], 
    target_values: Dict[str, float], 
    current_prices: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Generates orders to move from current positions to target values.
    
    Args:
        current_positions: List of dicts (alpaca position objects or dicts).
        target_values: Dict {symbol: target_market_value_usd}.
        current_prices: Dict {symbol: current_price_usd}.
        
    Returns:
        List of order dicts.
    """
    orders = []
    
    # Map current qty per symbol
    current_qtys = {p['symbol']: float(p['qty']) for p in current_positions}
    
    # Union of all symbols
    all_symbols = set(current_qtys.keys()) | set(target_values.keys())
    
    for symbol in all_symbols:
        target_val = target_values.get(symbol, 0.0)
        curr_qty = current_qtys.get(symbol, 0.0)
        price = current_prices.get(symbol)
        
        if not price:
            # Cannot trade without price
            continue
            
        # Calculate target qty
        # Floor to integer for MVP simplicity (though fractional is supported by Alpaca)
        target_qty = floor(target_val / price)
        
        diff_qty = target_qty - curr_qty
        
        if diff_qty == 0:
            continue
            
        side = "buy" if diff_qty > 0 else "sell"
        abs_qty = int(abs(diff_qty))
        
        if abs_qty > 0:
            orders.append({
                "symbol": symbol,
                "qty": abs_qty,
                "side": side,
                "type": "market",
                "time_in_force": "day"
            })
            
    return orders
