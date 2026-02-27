import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "backend", "alpaca_trader_v3.db")
print(f"Connecting to database at {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE orders ADD COLUMN parent_order_id VARCHAR")
    print("Added parent_order_id column")
except Exception as e:
    print(f"parent_order_id error (maybe exists): {e}")

try:
    cursor.execute("ALTER TABLE orders ADD COLUMN entry_price FLOAT")
    print("Added entry_price column")
except Exception as e:
    print(f"entry_price error (maybe exists): {e}")

conn.commit()
conn.close()
