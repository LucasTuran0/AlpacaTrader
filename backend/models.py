from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from datetime import datetime
from backend.db import Base

class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    run_id = Column(String, index=True)
    
    # Store key inputs/outputs as JSON for flexibility
    params_used = Column(JSON)      # e.g., {"fast": 20, "slow": 60}
    signals = Column(JSON)          # e.g., {"SPY": 1, "QQQ": 0}
    targets = Column(JSON)          # e.g., {"SPY": 5000.0}
    reasoning = Column(String)      # Detailed analysis of why this trade happened
    reward = Column(Float, nullable=True) # PnL associated with this decision

class BanditState(Base):
    __tablename__ = "bandit_state"
    
    # Key representing the parameter set, e.g. "20_60_0.1"
    param_key = Column(String, primary_key=True, index=True)
    trials = Column(Integer, default=0)
    total_reward = Column(Float, default=0.0)
    avg_reward = Column(Float, default=0.0)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    symbol = Column(String)
    qty = Column(Float)
    side = Column(String)
    status = Column(String) # "planned", "submitted", "filled", "canceled"
    alpaca_id = Column(String, nullable=True, index=True)
    parent_order_id = Column(String, nullable=True, index=True) # To link bracket children to parent
    entry_price = Column(Float, nullable=True) # To calculate PnL on exit

class DailyEquity(Base):
    __tablename__ = "daily_equity"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    equity = Column(Float)
    drawdown_pct = Column(Float)
