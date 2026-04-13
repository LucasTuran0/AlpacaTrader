# backend/config.py
import os

# Diversified momentum universe: core tech + sectors + hedges + high-vol
TRADED_SYMBOLS = [
    # High-momentum tech
    "NVDA", "TSLA", "META", "AAPL", "MSFT", "AMZN",
    # Leveraged tech / broad indices
    "TQQQ", "SPY", "IWM",
    # Uncorrelated sectors
    "XLE", "XLF",
    # Risk-off hedges (trend up when tech trends down)
    "GLD", "TLT",
    # High-volatility momentum
    "AMD", "COIN",
]

# Strategy default parameters (Pivoting to Aggressive)
DEFAULT_PARAMS = {
    "fast": 10,
    "slow": 30,
    "vol_target": 0.25  # Increased from 0.10 for higher daily range
}

# When True, the LangGraph agent gets access to MCP Brain tools
# (portfolio snapshot, risk status, bandit analysis, etc.) during its
# decision loop, enabling deeper introspection before trading.
AGENTIC_MODE = os.getenv("AGENTIC_MODE", "false").lower() == "true"
