from sqlalchemy.orm import Session
from backend.models import DailyEquity, Decision
from datetime import datetime
import pandas as pd

class MetricsService:
    def __init__(self, db: Session):
        self.db = db

    def record_daily_equity(self, equity: float):
        # In a real app we'd fetch historical or ensure only 1 per day
        # MVP: just insert a record
        rec = DailyEquity(
            equity=equity,
            # Drawdown calc requires history, MVP placeholder
            drawdown_pct=0.0
        )
        self.db.add(rec)
        self.db.commit()

    def get_metrics(self):
        # 1. Total runs
        total_runs = self.db.query(Decision).count()
        
        # 2. Equity Curve
        equity_recs = self.db.query(DailyEquity).order_by(DailyEquity.date.asc()).all()
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
