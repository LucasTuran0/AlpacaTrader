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
    elif timeframe == "5m":
        multiplier = np.sqrt(252 * 78) # 78 5-min bars per day
    elif timeframe == "15m":
        multiplier = np.sqrt(252 * 26) # 26 15-min bars per day
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

    # First pass: Calculate raw unconstrained weights
    raw_weights = {}
    total_gross_exposure = 0.0
    
    for symbol, row in latest.iterrows():
        sig = row['signal']
        vol = row['volatility']
        
        if pd.isna(sig) or pd.isna(vol) or vol == 0:
            raw_weights[symbol] = 0.0
            continue
            
        # Apply regime-adjusted target
        adjusted_vol_target = vol_target * risk_multiplier
        
        # Volatility Scalar: target_vol / realized_vol
        # e.g. 0.10 / 0.20 = 0.5 (allocate 50% of equity)
        w = (adjusted_vol_target / vol) * sig
        
        # Clip individual position max
        if w > 0:
            w = min(w, max_position_weight)
        elif w < 0:
            w = max(w, -max_position_weight)
            
        raw_weights[symbol] = w
        total_gross_exposure += abs(w)

    # Second pass: Normalize if total exposure > 1.0 (or provided max_leverage)
    # This ensures we don't try to buy 200% of account if we have many signals
    leverage_cap = 0.95 # Leave 5% cash buffer
    
    normalization_factor = 1.0
    if total_gross_exposure > leverage_cap:
        normalization_factor = leverage_cap / total_gross_exposure
    
    targets = {}
    for symbol, w in raw_weights.items():
        final_weight = w * normalization_factor
        targets[symbol] = account_value * final_weight
        
    return targets
