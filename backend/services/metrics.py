from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models import DailyEquity, Decision

class MetricsService:
    def __init__(self, db: Session):
        self.db = db

    def record_daily_equity(self, equity: float):
        live_q = self.db.query(DailyEquity).filter(DailyEquity.source == "live")
        high_water_mark = live_q.with_entities(func.max(DailyEquity.equity)).scalar() or equity
        high_water_mark = max(high_water_mark, equity)
        drawdown_pct = 0.0
        if high_water_mark > 0:
            drawdown_pct = (high_water_mark - equity) / high_water_mark * 100

        rec = DailyEquity(
            equity=equity,
            drawdown_pct=drawdown_pct,
            source="live"
        )
        self.db.add(rec)
        self.db.commit()

    def get_metrics(self):
        # 1. Total runs
        total_runs = self.db.query(Decision).count()
        
        # 2. Equity Curve — live Alpaca account data only, never backtest rows
        equity_recs = (
            self.db.query(DailyEquity)
            .filter(DailyEquity.source == "live")
            .order_by(DailyEquity.date.asc())
            .all()
        )
        if not equity_recs:
            return {"total_runs": total_runs, "current_equity": 0, "drawdown": 0}
            
        current_equity = equity_recs[-1].equity
        
        # Simple Drawdown Calculation
        high_water_mark = -1
        max_drawdown = 0
        
        for r in equity_recs:
            if r.equity > high_water_mark:
                high_water_mark = r.equity
            
            if high_water_mark > 0:
                dd = (high_water_mark - r.equity) / high_water_mark
                if dd > max_drawdown:
                    max_drawdown = dd
                    
        return {
            "total_runs": total_runs,
            "current_equity": current_equity,
            "max_drawdown_pct": max_drawdown * 100,
            "history": [
                {"date": r.date.strftime("%Y-%m-%d"), "equity": round(r.equity, 2)}
                for r in equity_recs
            ]
        }
