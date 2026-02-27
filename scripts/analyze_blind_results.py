import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.db import SessionLocal
from backend.models import DailyEquity, Decision
import pandas as pd
from datetime import datetime

def analyze_results():
    db = SessionLocal()
    
    #  FETCH ALL DATA
    # Since we purge before running, we can take everything or just the latest window.
    equity_all = db.query(DailyEquity).order_by(DailyEquity.date.asc()).all()
    
    if not equity_all:
        print("No equity data found! Run run_blind_test.py first.")
        db.close()
        return

    df = pd.DataFrame([{ "date": e.date, "equity": e.equity } for e in equity_all])
    
    # Ensure we are analyzing from the moment it starts at $100k (or the first record)
    start_equity = df.iloc[0]["equity"]
    end_equity = df.iloc[-1]["equity"]
    total_pnl = end_equity - start_equity
    pnl_pct = (total_pnl / start_equity) * 100
    
    # Calculate Drawdown relative to the HIGH of the curve
    df["cummax"] = df["equity"].cummax()
    df["drawdown"] = (df["equity"] - df["cummax"]) / df["cummax"]
    max_drawdown = df["drawdown"].min() * 100
    
    # Get win rate from Decisions
    decisions = db.query(Decision).filter(Decision.reward != 0).all()
    wins = [d for d in decisions if d.reward > 0]
    win_rate = (len(wins) / len(decisions)) * 100 if decisions else 0

    print(f"\n---  Final Blind Out-of-Sample Analysis  ---")
    print(f"Window: {df.iloc[0]['date']} to {df.iloc[-1]['date']}")
    print(f"Initial Equity: ${start_equity:,.2f}")
    print(f"Final Equity:   ${end_equity:,.2f}")
    print(f"Total PnL:      ${total_pnl:,.2f} ({pnl_pct:.2f}%)")
    print(f"Max Drawdown:   {max_drawdown:.2f}%")
    print(f"Win Rate:       {win_rate:.2f}% ({len(wins)}/{len(decisions)} trades)")
    print(f"Total Trades:   {len(decisions)}")
    
    # Performance summary
    daily_days = (df.iloc[-1]["date"] - df.iloc[0]["date"]).days
    if daily_days > 0:
        avg_daily_return = (pnl_pct / daily_days)
        print(f"Avg Daily Return: {avg_daily_return:.2f}%")

    if max_drawdown < -10:
        print("\n WARNING: Significant Drawdown detected.")
    elif max_drawdown < -5:
        print("\n NOTE: Moderate Drawdown, typical for scalping.")
    else:
        print("\n EXCELLENT: Low drawdown profile.")

    db.close()

if __name__ == "__main__":
    analyze_results()
