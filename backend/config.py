# backend/config.py

# List of assets to trade (The 'Mag-7' Momentum Leaders + TQQQ)
TRADED_SYMBOLS = ["TQQQ", "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "SPY"]

# Strategy default parameters (Pivoting to Aggressive)
DEFAULT_PARAMS = {
    "fast": 10,
    "slow": 30,
    "vol_target": 0.25 # Increased from 0.10 for higher daily range
}

# Predator Mode: The bot is always watching via WebSockets.
# It reacts instantly to every 1-minute bar close from Alpaca.
# BOT_INTERVAL_MINS = 15 (DEFUNCT: Now listening to live streams)
