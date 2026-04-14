# AlpacaTrader

An automated equities trading system built on the Alpaca API. Combines time-series momentum signals, volatility-aware position sizing, an epsilon-greedy multi-armed bandit for parameter optimization, and an AI agent layer powered by LangGraph and Google Gemini.

## Architecture

```
Frontend (React + Vite)         Backend (FastAPI)              External
┌──────────────────────┐   ┌────────────────────────────┐   ┌──────────────┐
│ Dashboard            │   │ REST API + WebSocket Logs   │   │ Alpaca API   │
│ Equity Chart         │──>│ Bot Cycle Engine            │──>│ (Trading +   │
│ Bandit Stats Table   │   │ Sentinel Shield (VIX+News)  │   │  Streaming)  │
│ Live Log Stream      │   │ Bandit Learning Module      │   ├──────────────┤
│ Bot Controls         │   │ APScheduler (EOD Liquidate) │   │ Yahoo Finance│
└──────────────────────┘   │ Alembic (DB Migrations)     │   │ (VIX data)   │
                           └─────────┬──────────────────┘   ├──────────────┤
                                     │                       │ Google Gemini│
                                     v                       │ (Sentiment)  │
                           ┌─────────────────┐               └──────────────┘
                           │ SQLite (WAL mode)│
                           └─────────────────┘
```

## Key Features

- **Live Streaming**: The backend uses Alpaca’s streaming APIs (`StockDataStream` for live trades, `TradingStream` for order lifecycle events) with exponential backoff reconnect. Material price moves can trigger another bot cycle. The dashboard uses a separate **FastAPI** WebSocket at `/ws/logs` to tail logs—it does not open a browser WebSocket directly to Alpaca.
- **Adaptive Parameters**: A multi-armed bandit stores per-arm stats and updates them from **realized** trade PnL when exits fill. **Backtests** use epsilon-greedy exploration (`choose_arm`). In **live** trading, after LangGraph allows a trade, the strategy step picks the **best historical arm** (`get_best_arm`) for that cycle; the bandit still learns from outcomes so rankings improve over time.
- **VIX regimes (Sentinel)**: Live VIX is fetched via Yahoo Finance (cached briefly). `SentinelShield` maps VIX to **SAFE** (VIX < 20), **SHIELD_ACTIVE** (20 ≤ VIX < 30), or **CRISIS** (VIX ≥ 30). **CRISIS** blocks new entries in the LangGraph strategy node. The `/bot/risk_status` endpoint reports trading blocked only for **CRISIS** (or manual override to that mode) and for the **15:40 ET** no-new-entries cutoff—not for SHIELD_ACTIVE by itself.
- **VIX-aware position sizing**: Independently of the named regime, `size_position` scales the vol target down when **VIX > 25** (defensive) or **> 35** (much smaller targets). Regime labels and these sizing cutoffs are related but use **different thresholds**; see `backend/agency/sentinel.py` and `backend/strategy/risk.py`.
- **AI Sentiment Analysis**: LLM-powered news headline analysis to detect extreme bearish sentiment and block entries.
- **Bracket Orders**: Every entry uses bracket orders with take-profit and stop-loss legs for automated risk management.
- **EOD Liquidation**: Background scheduler closes all positions at 3:53 PM ET to avoid overnight exposure.
- **Position Limits**: Configurable maximum concurrent positions (default 6) to prevent overexposure.
- **Backtesting Suite**: Walk-forward validation, blind out-of-sample testing, Monte Carlo robustness analysis, and flash crash stress testing.

## Setup

### Prerequisites

- Python 3.10+
- Node.js 20+
- Alpaca account (paper or live)
- Google API key (for Gemini AI features)

### 1. Environment Variables

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

Required variables:
- `ALPACA_API_KEY` - Your Alpaca API key
- `ALPACA_API_SECRET` - Your Alpaca secret key
- `ALPACA_PAPER` - `true` for paper trading, `false` for live
- `GOOGLE_API_KEY` - Google Gemini API key

### 2. Backend Setup

```bash
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\Activate.ps1

pip install -r backend/requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Database Migrations

Tables are auto-created on first startup. For subsequent schema changes:

```bash
cd backend
python -m alembic upgrade head
```

## Running

### Development (two terminals)

**Terminal 1 -- Backend:**
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

**Terminal 2 -- Frontend:**
```bash
cd frontend
npm run dev
```

Then open http://localhost:3000.

### Docker

```bash
docker compose up --build
```

This starts both the backend (port 8000) and frontend (port 3000).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/account` | Account equity and buying power |
| POST | `/bot/run_once` | Trigger a single bot cycle (`{"dry_run": true/false}`) |
| POST | `/bot/backtest` | Start a background backtest |
| GET | `/bot/metrics` | Equity history, drawdown, run count |
| GET | `/bot/risk_status` | VIX, regime (SAFE / SHIELD_ACTIVE / CRISIS), override, trading blocked |
| GET | `/bot/bandit_stats` | All bandit arms sorted by avg reward |
| GET | `/bot/logs` | Recent decision logs |
| POST | `/bot/feedback` | Manual reward feedback for a decision |
| WS | `/ws/logs` | Live log stream via WebSocket |
| POST | `/orders/market` | Place a manual market order |

## Scripts

All scripts are in `scripts/` and should be run from the repo root:

| Script | Purpose |
|--------|---------|
| `run_deep_training.py` | Multi-epoch parameter grid search with AI advisor refinement |
| `run_scalp_training.py` | Intraday 1-minute bar optimization |
| `run_walk_forward.py` | Train/test split validation (2 years train, 1 year test) |
| `run_blind_test.py` | Out-of-sample validation with locked parameters |
| `run_triple_blind.py` | 1000-day train + 90-day blind test |
| `run_stress_test.py` | Monte Carlo robustness analysis (1000 shuffled timelines) |
| `run_gauntlet.py` | Flash crash resilience + 4-stage walk-forward evolution |
| `run_agent.py` | Interactive AI agent with MCP tools |
| `run_advisor.py` | AI retrospective analysis of recent trades |
| `analyze_blind_results.py` | Statistical summary of blind test results |
| `check_positions.py` | Print current Alpaca positions |

## Testing

Run unit tests:

```bash
pytest tests/ -m "not integration" -v
```

Run integration tests (requires running server):

```bash
pytest tests/ -m integration -v
```

## Project Structure

```
AlpacaTrader/
├── backend/
│   ├── app.py              # FastAPI server, bot cycle, EOD scheduler
│   ├── config.py           # Traded symbols and default params
│   ├── db.py               # SQLAlchemy engine (SQLite WAL mode)
│   ├── models.py           # Decision, Order, DailyEquity, BanditState
│   ├── learning.py         # Epsilon-greedy multi-armed bandit
│   ├── market_data.py      # Alpaca bars, news, VIX, latest trades
│   ├── backtest.py         # Backtesting engine
│   ├── agency/             # LangGraph agent (sentinel, strategy, executor)
│   ├── services/           # Execution, streaming, metrics, logging, etc.
│   ├── strategy/           # Signal computation and risk/sizing
│   └── alembic/            # Database migrations
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Dashboard layout
│   │   ├── components/     # Header, EquityChart, BanditStats, LogStream, Controls
│   │   ├── hooks/          # useWebSocket
│   │   └── lib/            # API client
│   └── vite.config.ts      # Vite + Tailwind + proxy config
├── agent/                  # MCP client and LangGraph agent
├── mcp_server/             # FastMCP brain server + vendored Alpaca MCP
├── scripts/                # Training, testing, and debug scripts
├── tests/                  # Unit and integration tests
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```
