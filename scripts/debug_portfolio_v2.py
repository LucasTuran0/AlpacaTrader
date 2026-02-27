import sqlite3
import os
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

db_path = os.path.join(os.path.dirname(__file__), "..", "backend", "alpaca_trader_v3.db")
conn = sqlite3.connect(db_path)

print("\n--- Last 10 Orders ---")
try:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, symbol, side, qty, status, entry_price 
        FROM orders 
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print(e)

print("\n--- Last 5 Equity Records ---")
try:
    cursor.execute("SELECT date, equity FROM daily_equity ORDER BY date DESC LIMIT 5")
    for r in cursor.fetchall():
        print(r)
except Exception as e:
    print(e)

conn.close()
