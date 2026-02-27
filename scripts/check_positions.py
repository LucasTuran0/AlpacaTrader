import os
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
load_dotenv(env_path)

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_API_SECRET")
paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"

client = TradingClient(api_key, secret_key, paper=paper)

print("\n--- Current Account Positions ---")
try:
    positions = client.get_all_positions()
    for p in positions:
        print(f"{p.symbol}: {p.qty} @ {p.current_price} (MktVal: {p.market_value}, PnL: {p.unrealized_pl})")
except Exception as e:
    print(f"Error fetching positions: {e}")
