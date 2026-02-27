import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

db_path = os.path.join(os.path.dirname(__file__), "..", "backend", "alpaca_trader_v3.db")
print(f"Connecting to database at {db_path}")

conn = sqlite3.connect(db_path)

print("\n--- Recent Orders (Last 24h) ---")
try:
    query = """
    SELECT id, run_id, timestamp, symbol, side, qty, status, entry_price 
    FROM orders 
    ORDER BY timestamp DESC 
    LIMIT 20
    """
    df_orders = pd.read_sql_query(query, conn)
    print(df_orders)
except Exception as e:
    print(f"Error reading orders: {e}")

print("\n--- Recent Equity History ---")
try:
    query = "SELECT * FROM daily_equity ORDER BY date DESC LIMIT 10"
    df_equity = pd.read_sql_query(query, conn)
    print(df_equity)
except Exception as e:
    print(f"Error reading equity: {e}")

conn.close()
