import pandas as pd
import numpy as np

def compute_volatility(bars: pd.DataFrame, window: int = 20, timeframe: str = "1d") -> pd.DataFrame:
    """
    Computes annualized realized volatility.
    """
    closes = bars['close'].unstack(level=0)
    log_returns = np.log(closes / closes.shift(1))
    
    # Scale based on frequency
    # Daily: sqrt(252)
    # Minute: sqrt(252 * 6.5 * 60) assuming 6.5 hour trading day
    if timeframe == "1m":
        multiplier = np.sqrt(252 * 390) # 390 minutes per day
    else:
        multiplier = np.sqrt(252)
        
    vol = log_returns.rolling(window=window).std() * multiplier
    
    return vol.stack().to_frame('volatility').swaplevel(0, 1).sort_index()

def size_position(
    signals: pd.DataFrame, 
    volatility: pd.DataFrame, 
    account_value: float,
    vol_target: float = 0.10,
    max_position_weight: float = 0.50,
    vix_value: float = 20.0 # Default to neutral
) -> dict[str, float]:
    """
    Calculates target weights, downshifting risk if VIX is high.
    """
    # Join signal and vol
    df = signals.join(volatility, how='inner')
    latest = df.groupby(level=0).last()
    
    # Regime Shield: If VIX > 25, we are in a high-fear regime. Cut aggression.
    risk_multiplier = 1.0
    if vix_value > 25:
        risk_multiplier = 0.5 # Defensive shift
    elif vix_value > 35:
        risk_multiplier = 0.1 # Panic shift (move almost everything to cash)

    targets = {}
    for symbol, row in latest.iterrows():
        sig = row['signal']
        vol = row['volatility']
        
        if pd.isna(sig) or pd.isna(vol) or vol == 0:
            targets[symbol] = 0.0
            continue
            
        # Apply regime-adjusted target
        adjusted_vol_target = vol_target * risk_multiplier
        raw_weight = (adjusted_vol_target / vol) * sig
        
        capped_weight = min(raw_weight, max_position_weight)
        targets[symbol] = account_value * capped_weight
        
    return targets
