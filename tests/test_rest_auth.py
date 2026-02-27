import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

def test_rest_auth():
    load_dotenv("backend/.env")
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_API_SECRET")
    paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    
    print(f"Testing REST Auth for Key: {api_key[:4]}...")
    
    try:
        client = TradingClient(api_key, secret_key, paper=paper)
        acct = client.get_account()
        print(f" REST Auth SUCCESS! Account Status: {acct.status}")
    except Exception as e:
        print(f" REST Auth FAILED: {e}")

if __name__ == "__main__":
    test_rest_auth()
