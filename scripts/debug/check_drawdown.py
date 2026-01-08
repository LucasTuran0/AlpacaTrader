from backend.db import SessionLocal
from backend.models import DailyEquity
import pandas as pd
from datetime import datetime

def check_drawdown():
    db = SessionLocal()
    start_filter = datetime(2025, 12, 20)
    equity_all = db.query(DailyEquity).filter(DailyEquity.date >= start_filter).all()
    
    df = pd.DataFrame([{ "date": e.date, "equity": e.equity } for e in equity_all])
    df = df.sort_values("date")
    
    min_equity = df["equity"].min()
    max_equity = df["equity"].max()
    print(f"Min Equity: ${min_equity:,.2f}")
    print(f"Max Equity: ${max_equity:,.2f}")
    
    # Show the 10 lowest equity points to see if it was a spike
    lowest = df.sort_values("equity").head(10)
    print("\nLowest 10 Points:")
    print(lowest)
    
    db.close()

if __name__ == "__main__":
    check_drawdown()
