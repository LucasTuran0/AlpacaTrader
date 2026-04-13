import pandas as pd
import numpy as np
from backend.strategy.risk import size_position


def _make_signal_vol(symbols, signal_vals, vol_vals):
    """Helper: builds signal and volatility DataFrames for size_position."""
    rows_sig = []
    rows_vol = []
    ts = pd.Timestamp("2025-01-01")
    for sym, sig, vol in zip(symbols, signal_vals, vol_vals):
        rows_sig.append({"symbol": sym, "timestamp": ts, "signal": sig})
        rows_vol.append({"symbol": sym, "timestamp": ts, "volatility": vol})
    sig_df = pd.DataFrame(rows_sig).set_index(["symbol", "timestamp"])
    vol_df = pd.DataFrame(rows_vol).set_index(["symbol", "timestamp"])
    return sig_df, vol_df


class TestVIXRegime:
    def test_low_vix_full_risk(self):
        sig, vol = _make_signal_vol(["AAPL"], [1.0], [0.20])
        targets = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=15.0)
        assert targets["AAPL"] > 0

    def test_medium_vix_defensive(self):
        sig, vol = _make_signal_vol(["AAPL"], [1.0], [0.20])
        low_vix = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=15.0)
        med_vix = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=28.0)
        assert med_vix["AAPL"] < low_vix["AAPL"]

    def test_high_vix_panic(self):
        sig, vol = _make_signal_vol(["AAPL"], [1.0], [0.20])
        med_vix = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=28.0)
        high_vix = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=40.0)
        # Panic (>35) should be much smaller than defensive (>25)
        assert high_vix["AAPL"] < med_vix["AAPL"]

    def test_panic_ordering_fixed(self):
        """Regression: VIX=40 must trigger 0.1x panic, not 0.5x defensive."""
        sig, vol = _make_signal_vol(["AAPL"], [1.0], [0.20])
        panic = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=40.0)
        defensive = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=28.0)
        ratio = panic["AAPL"] / defensive["AAPL"] if defensive["AAPL"] != 0 else 0
        assert ratio < 0.3  # 0.1/0.5 = 0.2, allow some float tolerance


class TestNormalization:
    def test_leverage_cap(self):
        """Many strong signals should be normalized so total exposure <= 95%."""
        symbols = [f"SYM{i}" for i in range(10)]
        sig, vol = _make_signal_vol(symbols, [1.0] * 10, [0.05] * 10)
        targets = size_position(sig, vol, account_value=100_000, vol_target=0.20, vix_value=15.0)
        total_weight = sum(abs(v) for v in targets.values()) / 100_000
        assert total_weight <= 0.96  # 95% cap + float tolerance

    def test_zero_signal_no_position(self):
        sig, vol = _make_signal_vol(["AAPL"], [0.0], [0.20])
        targets = size_position(sig, vol, account_value=100_000, vol_target=0.10, vix_value=15.0)
        assert targets["AAPL"] == 0.0
