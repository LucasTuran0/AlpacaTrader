from types import SimpleNamespace

import pandas as pd
import pytest

import backend.app as app_module


class _DummySession:
    def add(self, _obj):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


class _DummyLoggingService:
    def __init__(self, _db):
        pass

    def log_decision(self, *args, **kwargs):
        return None

    def update_order_status(self, *args, **kwargs):
        return None


class _DummyMetricsService:
    def __init__(self, _db):
        pass

    def record_daily_equity(self, _equity):
        return None


class _FakeTradingClient:
    def __init__(self):
        self.submit_called = False

    def get_account(self):
        return SimpleNamespace(cash=100000.0, equity=100000.0, non_marginable_buying_power=100000.0)

    def get_all_positions(self):
        return []

    def get_orders(self, _req):
        return []

    def cancel_order_by_id(self, _order_id):
        return None

    def submit_order(self, _req):
        self.submit_called = True
        return SimpleNamespace(id="fake-order-id")


class _FakeMarketProvider:
    def get_bars(self, symbols, lookback_days=2, timeframe=None):
        _ = (lookback_days, timeframe)
        rows = []
        for idx, symbol in enumerate(symbols[:2]):
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(minutes=idx),
                    "open": 100.0 + idx,
                    "high": 101.0 + idx,
                    "low": 99.0 + idx,
                    "close": 100.0 + idx,
                    "volume": 1000,
                }
            )
        return pd.DataFrame(rows).set_index(["symbol", "timestamp"]).sort_index()

    def get_latest_trades(self, symbols):
        return {s: SimpleNamespace(price=100.0) for s in symbols[:2]}

    def get_vix(self):
        return 17.0


@pytest.fixture
def patched_cycle_deps(monkeypatch):
    captured = {"market_contexts": []}

    monkeypatch.setattr(app_module, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(app_module, "LoggingService", _DummyLoggingService)
    monkeypatch.setattr(app_module, "MetricsService", _DummyMetricsService)

    trading = _FakeTradingClient()
    monkeypatch.setattr(app_module, "trading_client", trading)
    monkeypatch.setattr(app_module, "market_provider", _FakeMarketProvider())

    monkeypatch.setattr(
        app_module,
        "compute_signal",
        lambda *args, **kwargs: pd.DataFrame(
            {"signal": [0.0]},
            index=pd.MultiIndex.from_tuples([("NVDA", pd.Timestamp("2026-01-01"))], names=["symbol", "timestamp"]),
        ),
    )
    monkeypatch.setattr(
        app_module,
        "compute_volatility",
        lambda *args, **kwargs: pd.DataFrame(
            {"volatility": [0.01]},
            index=pd.MultiIndex.from_tuples([("NVDA", pd.Timestamp("2026-01-01"))], names=["symbol", "timestamp"]),
        ),
    )
    monkeypatch.setattr(app_module, "size_position", lambda *args, **kwargs: {})
    monkeypatch.setattr(app_module, "calculate_orders", lambda *args, **kwargs: [])

    class _FakeAgenticExecutor:
        async def run(self, market_context):
            captured["market_contexts"].append(market_context)
            if market_context.get("risk_override") == "CRISIS":
                return {
                    "risk_shield_status": "CRISIS",
                    "trade_proposal": {"action": "HOLD"},
                    "decision_reasoning": "halted by override",
                }
            if market_context.get("dry_run"):
                return {
                    "risk_shield_status": "SAFE",
                    "trade_proposal": {
                        "action": "TRADE",
                        "params": {"fast": 20, "slow": 60, "vol_target": 0.10},
                    },
                    "decision_reasoning": "dry run fixed params",
                }
            return {
                "risk_shield_status": "SAFE",
                "trade_proposal": {"action": "HOLD"},
                "decision_reasoning": "hold",
            }

    monkeypatch.setattr(app_module, "AgenticExecutor", _FakeAgenticExecutor)

    original_override = app_module.risk_override
    original_epsilon = app_module.bandit_epsilon_override
    yield captured, trading
    app_module.risk_override = original_override
    app_module.bandit_epsilon_override = original_epsilon


@pytest.mark.asyncio
async def test_halt_blocks_orders(patched_cycle_deps):
    captured, trading = patched_cycle_deps
    app_module.risk_override = "CRISIS"

    result = await app_module.execute_bot_cycle(dry_run=False)

    assert result["status"] == "halted"
    assert trading.submit_called is False
    assert captured["market_contexts"][-1]["risk_override"] == "CRISIS"


@pytest.mark.asyncio
async def test_dry_run_uses_fixed_params(patched_cycle_deps):
    captured, trading = patched_cycle_deps
    app_module.risk_override = None

    result = await app_module.execute_bot_cycle(dry_run=True)

    assert result["status"] == "success"
    assert result["params"] == {"fast": 20, "slow": 60, "vol_target": 0.10}
    assert captured["market_contexts"][-1]["dry_run"] is True
    assert trading.submit_called is False
