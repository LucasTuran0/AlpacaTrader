# AlpacaTrader

## Overview
AlpacaTrader is an automated trading bot integrating the Alpaca Trading API, an Epsilon-Greedy Multi-Armed Bandit machine learning module, and an AI agent executor powered by LangGraph. It is designed to trade high-momentum equities (such as the 'Mag-7' and leveraged ETFs like TQQQ) based on dynamically updating moving averages and volatility targeting. The system reacts to 1-minute streaming market data to evaluate and execute trades.

## System Architecture
- **Backend API**: A FastAPI application handles REST endpoints, background task scheduling, and WebSocket-based telemetry broadcasting.
- **Trading Engine**: Execution logic relies on the `alpaca-py` library to stream real-time price data and route market orders.
- **Machine Learning**: Located in `backend/learning.py`, the system implements an Epsilon-Greedy Bandit model. It continuously evaluates historical trade outcomes to dynamically select the most profitable fast/slow moving average periods and volatility constraints.
- **Agentic Intelligence**: A LangGraph state machine (`backend/agency/`) and an integrated Model Context Protocol (MCP) client (`agent/mcp_client.py`) evaluate positions, act on discretionary overrides, and monitor portfolio health using large language models.
- **Database**: A local SQLite database (`alpaca_trader_v3.db`) stores performance metrics, explicit PnL records, and the internal state parameters of the Multi-Armed Bandit model using SQLAlchemy.

## Key Features
- **Live WebSocket Integration**: Maintains a persistent connection to Alpaca's data streams (`backend/services/streaming.py`) for instantaneous reaction to bar closes.
- **Dynamic Parameter Optimization**: The Epsilon-Greedy Bandit algorithm actively records the profit/loss of trades tied to specific parameter sets ("arms"). It heavily favors the most profitable historical strategy while sustaining an epsilon exploration rate to adapt to changing market conditions.
- **Automated Risk Management**: A persistent background scheduler systematically liquidates all open positions at 3:53 PM ET daily, preventing overnight exposure risk.
- **Systematic Backtesting Suite**: The project includes extensive logic for backtesting, walk-forward analysis, blind tests, and broad stress testing (`scripts/`).

## Setup and Installation

1. **Environment Variables**: Create a `.env` file in the root directory and configure the minimum required keys:
   ```env
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_API_SECRET=your_alpaca_secret
   PAPER=True
   GOOGLE_API_KEY=your_gemini_api_key
   ```

2. **Python Environment setup**:
   It is recommended to use a virtual environment. Install all required dependencies from the backend constraints list:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\Activate.ps1 on Windows
   pip install -r backend/requirements.txt
   ```

3. **Database Initialization**:
   The backend initializes the core SQLite database tables automatically upon the first startup via the `backend/db.py` declarative base.

## Usage

### Running the API Server
Start the background daemon and FastAPI server:
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Upon startup, the server boots the Alpaca streaming components, attaches the SQLite data sessions, scopes the agent execution graph, and schedules end-of-day liquidation routines.

### Strategy Operations and Analysis
The `scripts/` directory houses dedicated CLI execution paths to evaluate, tune, and test the trading logic without activating the main API daemon:
- `run_deep_training.py`: Executes batched evaluation of complex parameter constraints using large historical context windows.
- `run_blind_test.py`: Conducts out-of-sample testing to validate the strategy against overfitting.
- `run_walk_forward.py`: Re-evaluates baseline parameter validity by sweeping sequentially across historical blocks of data.
- `analyze_blind_results.py`: Computes base statistical significance (including standard metrics like Sharpe ratio, max drawdown, and overall win rate) relative to the backtest logs.

## Core Trading Logic
By default, the strategy analyzes standard asset constraints based on:
- Fast Moving Average (e.g., 10 periods)
- Slow Moving Average (e.g., 30 periods)
- Volatility Target (e.g., 0.25)

These periods are not static. The `EpsilonGreedyBandit` stores each chosen parameter pair and its subsequent real-world execution state. The overall success rate and average monetary return per parameter sequence adjust the statistical density for future decisions, shifting the active periods automatically throughout standard operation.
