from sqlalchemy.orm import Session
from backend.models import Decision, Order
import json
from datetime import datetime

class LoggingService:
    def __init__(self, db: Session):
        self.db = db

    def log_decision(
        self,
        run_id: str,
        params_used: dict,
        signals: dict,
        targets: dict,
        orders: list,
        reasoning: str = ""
    ):
        # Create Decision Record
        decision = Decision(
            run_id=run_id,
            params_used=params_used,
            signals=signals,
            targets=targets,
            reasoning=reasoning
        )
        self.db.add(decision)

        # Create Order Records
        for o in orders:
            order_rec = Order(
                run_id=run_id,
                symbol=o['symbol'],
                qty=float(o['qty']),
                side=o['side'],
                status="planned", # Initial status
                timestamp=datetime.utcnow()
            )
            self.db.add(order_rec)
            
        self.db.commit()
        return decision.id

    def update_order_status(self, run_id: str, symbol: str, status: str, alpaca_id: str = None):
        # Simple lookup - in real app might use ID directly
        order = self.db.query(Order).filter(
            Order.run_id == run_id, 
            Order.symbol == symbol
        ).first()
        
        if order:
            order.status = status
            if alpaca_id:
                order.alpaca_id = alpaca_id
            self.db.commit()

    def get_recent_runs(self, limit: int = 10):
        return self.db.query(Decision).order_by(Decision.timestamp.desc()).limit(limit).all()
