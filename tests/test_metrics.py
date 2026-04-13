from backend.services.metrics import MetricsService
from backend.models import DailyEquity


class TestDrawdownCalculation:
    def test_drawdown_persisted_on_record(self, db_session):
        svc = MetricsService(db_session)
        svc.record_daily_equity(100_000)
        svc.record_daily_equity(95_000)

        records = db_session.query(DailyEquity).order_by(DailyEquity.id.asc()).all()
        assert records[0].drawdown_pct == 0.0  # At peak, no drawdown
        assert round(records[1].drawdown_pct, 2) == 5.0  # 5% drawdown

    def test_drawdown_zero_at_new_high(self, db_session):
        svc = MetricsService(db_session)
        svc.record_daily_equity(100_000)
        svc.record_daily_equity(110_000)

        records = db_session.query(DailyEquity).order_by(DailyEquity.id.asc()).all()
        assert records[1].drawdown_pct == 0.0

    def test_get_metrics_returns_history(self, db_session):
        svc = MetricsService(db_session)
        svc.record_daily_equity(100_000)
        svc.record_daily_equity(105_000)
        metrics = svc.get_metrics()
        assert metrics["current_equity"] == 105_000
        assert len(metrics["history"]) == 2
        assert metrics["max_drawdown_pct"] == 0.0  # Never dropped

    def test_get_metrics_computes_max_drawdown(self, db_session):
        svc = MetricsService(db_session)
        svc.record_daily_equity(100_000)
        svc.record_daily_equity(90_000)
        svc.record_daily_equity(95_000)
        metrics = svc.get_metrics()
        assert metrics["max_drawdown_pct"] == 10.0  # Peak 100k -> trough 90k

    def test_get_metrics_empty_db(self, db_session):
        svc = MetricsService(db_session)
        metrics = svc.get_metrics()
        assert metrics["total_runs"] == 0
        assert metrics["current_equity"] == 0
