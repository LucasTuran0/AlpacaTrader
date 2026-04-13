import pandas as pd
import numpy as np
from backend.strategy.ts_mom import compute_signal
from backend.strategy.risk import compute_volatility


def _make_bars(prices_by_symbol: dict, freq="1min") -> pd.DataFrame:
    """Helper: builds a MultiIndex (symbol, timestamp) DataFrame from a dict of price lists."""
    rows = []
    for symbol, prices in prices_by_symbol.items():
        for i, p in enumerate(prices):
            rows.append({
                "symbol": symbol,
                "timestamp": pd.Timestamp("2025-01-01") + pd.Timedelta(minutes=i),
                "open": p, "high": p * 1.001, "low": p * 0.999, "close": p, "volume": 100,
            })
    df = pd.DataFrame(rows).set_index(["symbol", "timestamp"]).sort_index()
    return df


class TestComputeSignal:
    def test_strong_uptrend_produces_long_signal(self):
        prices = list(range(100, 200))
        bars = _make_bars({"AAPL": prices})
        signals = compute_signal(bars, fast_window=5, slow_window=20, threshold=0.0)
        last_sig = signals.xs("AAPL", level=0)["signal"].iloc[-1]
        assert last_sig == 1.0

    def test_flat_market_produces_zero_signal(self):
        prices = [100.0] * 100
        bars = _make_bars({"AAPL": prices})
        signals = compute_signal(bars, fast_window=5, slow_window=20, threshold=0.001)
        last_sig = signals.xs("AAPL", level=0)["signal"].iloc[-1]
        assert last_sig == 0.0

    def test_multiple_symbols_independent(self):
        bars = _make_bars({
            "AAPL": list(range(100, 200)),
            "TSLA": [100.0] * 100,
        })
        signals = compute_signal(bars, fast_window=5, slow_window=20, threshold=0.0)
        assert signals.xs("AAPL", level=0)["signal"].iloc[-1] == 1.0
        assert signals.xs("TSLA", level=0)["signal"].iloc[-1] == 0.0


class TestComputeVolatility:
    def test_constant_prices_zero_vol(self):
        prices = [100.0] * 50
        bars = _make_bars({"SPY": prices})
        vol = compute_volatility(bars, window=10, timeframe="1d")
        last_vol = vol.xs("SPY", level=0)["volatility"].iloc[-1]
        assert last_vol == 0.0 or np.isnan(last_vol)

    def test_volatile_prices_nonzero(self):
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        bars = _make_bars({"SPY": prices.tolist()})
        vol = compute_volatility(bars, window=10, timeframe="1d")
        last_vol = vol.xs("SPY", level=0)["volatility"].dropna().iloc[-1]
        assert last_vol > 0
