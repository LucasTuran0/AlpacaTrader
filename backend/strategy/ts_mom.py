import pandas as pd
import numpy as np

def compute_signal(bars: pd.DataFrame, fast_window: int = 20, slow_window: int = 60, threshold: float = 0.0005) -> pd.DataFrame:
    """
    Computes time-series momentum signals based on MA crossover with a confidence threshold.
    
    Args:
        bars: DataFrame with MultiIndex (symbol, timestamp) and 'close' column.
        fast_window: Lookback for fast moving average.
        slow_window: Lookback for slow moving average.
        threshold: Minimum percentage distance between fast and slow to trigger a signal.
    """
    # Ensure sorted
    bars = bars.sort_index()
    
    # Calculate MAs per symbol
    closes = bars['close'].unstack(level=0)
    
    fast_ma = closes.rolling(window=fast_window).mean()
    slow_ma = closes.rolling(window=slow_window).mean()
    
    # Signal: 1 if fast_ma > slow_ma * (1 + threshold)
    # This prevents 'micro-flips' where MAs touch but don't trend.
    diff_pct = (fast_ma - slow_ma) / slow_ma
    
    raw_signal = np.where(diff_pct > threshold, 1.0, 
                          np.where(diff_pct < -threshold, -1.0, 0.0))
    
    # Convert back to DataFrame
    signals = pd.DataFrame(raw_signal, index=closes.index, columns=closes.columns)
    
    # Restack to match input structure (symbol, timestamp)
    signals = signals.stack().to_frame('signal')
    signals = signals.swaplevel(0, 1).sort_index()
    
    # For MVP: Long only if positive, else flat.
    signals['signal'] = signals['signal'].apply(lambda x: 1.0 if x > 0 else 0.0)
    
    return signals
