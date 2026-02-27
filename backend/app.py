import os
import uuid
import logging
import asyncio
from typing import List
from datetime import datetime
import pytz
from contextlib import asynccontextmanager
import pandas as pd

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, QueryOrderStatus
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from backend.market_data import MarketDataProvider
from backend.strategy.ts_mom import compute_signal
from backend.strategy.risk import compute_volatility, size_position
from backend.config import TRADED_SYMBOLS
from backend.services.execution import calculate_orders
from backend.services.logging import LoggingService
from backend.services.metrics import MetricsService
from backend.db import Base, engine, SessionLocal
from backend.models import Decision, Order, DailyEquity, BanditState
from backend.learning import EpsilonGreedyBandit
from backend.backtest import run_backtest
from backend.services.streaming import AlpacaStreamingService
from backend.agency.executor import AgenticExecutor

load_dotenv()

# --- Logging & WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

class WebSocketHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(manager.broadcast(log_entry))
        except:
             pass

logging.basicConfig(level=logging.INFO)
ws_handler = WebSocketHandler()
ws_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(ws_handler)
logger = logging.getLogger("PaperPilot")

# --- Globals ---
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_API_SECRET")
PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"

if not API_KEY or not API_SECRET:
    raise RuntimeError("Missing ALPACA_API_KEY / ALPACA_API_SECRET in .env")

trading_client = TradingClient(API_KEY, API_SECRET, paper=PAPER)
market_provider = MarketDataProvider()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(" Starting PaperPilot Backend...")
    Base.metadata.create_all(bind=engine)
    
    # Initialize Streaming Service
    # We pass BOTH price trigger and trade update handlers
    stream_svc = AlpacaStreamingService(execute_bot_cycle, handle_trade_update)
    
    # Start stream in the background
    asyncio.create_task(stream_svc.start())
    logger.info(" Real-Time 'Alpha-Stream' + 'Learning-Loop' Connected.")

    # Start Scheduler for EOD Liquidation
    scheduler.add_job(liquidate_all_positions, 'cron', day_of_week='mon-fri', hour=15, minute=53)
    scheduler.start()
    logger.info(" EOD Liquidation Scheduler Armed (15:53 ET)")
    
    yield
    
    scheduler.shutdown()
    await stream_svc.stop()
    logger.info(" Shutting down...")

async def handle_trade_update(data):
    """
    Called by AlpacaStreamingService when an order event occurs.
    Updates the bandit based on PnL of closed trades.
    """
    db = SessionLocal()
    try:
        event = data.event
        order = data.order
        symbol = order.symbol
        alpaca_id = str(order.id)
        
        # 1. Update order status in DB
        db_order = db.query(Order).filter(Order.alpaca_id == alpaca_id).first()
        if not db_order:
            # Might be a child order we haven't seen yet, or from a previous run
            # Try to find by parent_id if it's a child
            parent_id = getattr(order, 'parent_id', None)
            if parent_id:
                db_order = db.query(Order).filter(Order.alpaca_id == str(parent_id)).first()
        
        if db_order:
            db_order.status = event
            if event == "fill":
                fill_price = float(order.filled_avg_price)
                
                # Check if it's an EXIT order (child of a bracket)
                is_exit = hasattr(order, 'parent_id') and order.parent_id is not None
                
                if not is_exit:
                    # ENTRY Filled: Record entry price for later PnL
                    db_order.entry_price = fill_price
                    logger.info(f" ENTRY Filled: {symbol} at {fill_price}")
                else:
                    # EXIT Filled: Calculate PnL and UPDATE BANDIT
                    entry_price = db_order.entry_price
                    if entry_price:
                        side_mult = 1 if db_order.side == "buy" else -1
                        pnl_pct = (fill_price - entry_price) / entry_price * side_mult
                        
                        # Find the Decision that triggered this
                        decision = db.query(Decision).filter(Decision.run_id == db_order.run_id).first()
                        if decision:
                            bandit = EpsilonGreedyBandit(db)
                            bandit.update_arm(decision.params_used, pnl_pct)
                            decision.reward = (decision.reward or 0) + pnl_pct
                            logger.info(f" PROFIT TAKEN: {symbol} PnL: {pnl_pct:.2%}. Bandit Optimized.")
            
            db.commit()
    except Exception as e:
        logger.error(f"Error in handle_trade_update: {e}")
    finally:
        db.close()

app = FastAPI(title="Alpaca Paper Trader API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Scheduler & Liquidation ---
scheduler = BackgroundScheduler(timezone="America/New_York")

import time

def liquidate_all_positions():
    """
    Called at 3:53 PM ET to exit all positions before market close.
    """
    logger.info(" END OF DAY PROTOCOL INITIATED: LIQUIDATING ALL POSITIONS")
    try:
        # 1. Cancel all open orders for ALL managed symbols (Free up "held" shares)
        # Using the robust method (Get Open -> Cancel ID)
        for symbol in TRADED_SYMBOLS:
            try:
                open_orders = trading_client.get_orders(GetOrdersRequest(
                    status=QueryOrderStatus.OPEN, 
                    symbols=[symbol]
                ))
                for o in open_orders:
                    trading_client.cancel_order_by_id(o.id)
                
                # Wait for Alpaca to process cancellations
                if open_orders:
                    time.sleep(1.0) 
            except Exception as e:
                logger.error(f"Failed to cancel open orders for {symbol}: {e}")
        
        # 2. Close all positions
        positions = trading_client.get_all_positions()
        for p in positions:
            if p.symbol in TRADED_SYMBOLS:
                logger.info(f"Selling {p.qty} of {p.symbol} for EOD...")
                try:
                    trading_client.submit_order(MarketOrderRequest(
                        symbol=p.symbol,
                        qty=p.qty,
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY
                    ))
                except Exception as e:
                    logger.error(f"Failed to liquidate {p.symbol}: {e}")
                    
        logger.info(" EOD Liquidation Complete. Sleep well.")
    except Exception as e:
        logger.error(f"EOD Liquidation Error: {e}")

# --- Logic Core ---
async def execute_bot_cycle(dry_run: bool = False):
    run_id = str(uuid.uuid4())
    logger.info(f"--- Starting Cycle {run_id} (Dry Run: {dry_run}) ---")
    db = SessionLocal()
    try:
        # Time Check: Stop entries after 3:40 PM ET
        tz_ny = pytz.timezone("America/New_York")
        now_ny = datetime.now(tz_ny)
        if now_ny.hour == 15 and now_ny.minute >= 40:
             logger.info(f" Market Closing Soon ({now_ny.strftime('%H:%M')}). Skipping new entries.")
             return

        symbols = TRADED_SYMBOLS
        # Switch to 1-Minute bars + Live Injection for "Sliding Window" logic
        tf = TimeFrame(1, TimeFrameUnit.Minute)
        bars = market_provider.get_bars(symbols, lookback_days=2, timeframe=tf)
        
        # --- LIVE DATA INJECTION ---
        # Get the absolute latest trades to append as the "current partial bar"
        latest_trades = market_provider.get_latest_trades(symbols)
        
        new_rows = []
        now_ts = pd.Timestamp.now(tz='UTC')
        
        for symbol, trade in latest_trades.items():
            # Append a row with current price as close/high/low/open to influence MA instantly
            new_rows.append({
                "symbol": symbol,
                "timestamp": now_ts,
                "open": trade.price,
                "high": trade.price,
                "low": trade.price, 
                "close": trade.price, 
                "volume": 0
            })
        
        if new_rows:
            live_df = pd.DataFrame(new_rows).set_index(["symbol", "timestamp"])
            # Concatenate and resort
            bars = pd.concat([bars, live_df])
            bars = bars.sort_index()
            
        acct = trading_client.get_account()
        
        # --- BUDGETING & PORTFOLIO CONTROL ---
        # Calculate 'Strategy Budget' = Cash + Value of Holdings in Strategy
        # This prevents the bot from seeing the whole account equity (which includes manual positions)
        alpaca_positions = trading_client.get_all_positions()
        
        # 1. Calculate value of current managed positions
        managed_equity = 0.0
        current_positions = []
        for p in alpaca_positions:
            if p.symbol in symbols:
                managed_equity += float(p.market_value)
            
            # Save for execution step later (keep all for now, we filter in calculate_orders)
            current_positions.append({"symbol": p.symbol, "qty": float(p.qty)})
            
        # 2. Get available cash (use non_marginable_buying_power for 1x leverage safety, or strictly cash)
        # Note: 'buying_power' can be 4x equity. We prefer using real cash + managed equity.
        # Fallback to equity if cash is weird, but try cash.
        try:
            available_cash = float(acct.cash) 
        except:
             # Fallback for accounts where cash isn't direct (though it usually is)
            available_cash = float(acct.non_marginable_buying_power)

        strategy_budget = available_cash + managed_equity
        logger.info(f" Budgeting: Cash=${available_cash:,.2f} + Managed=${managed_equity:,.2f} = Budget=${strategy_budget:,.2f}")
        
        if strategy_budget < 1000:
             logger.warning(" Budget very low. Using full equity as fallback to prevent stall.")
             strategy_budget = float(acct.equity)

        # Still track total equity for metrics/agent context
        equity = float(acct.equity)

        bandit = EpsilonGreedyBandit(db)
        params_used = {"fast": 20, "slow": 60, "vol_target": 0.10} if dry_run else bandit.choose_arm()
        logger.info(f"Selected Params: {params_used}")

        signals = compute_signal(
            bars, 
            fast_window=params_used['fast'], 
            slow_window=params_used['slow'],
            threshold=params_used.get('threshold', 0.0005)
        )
        current_vol = compute_volatility(bars, timeframe="1m")
        # Use strategy_budget instead of total equity
        targets = size_position(signals, current_vol, account_value=strategy_budget, vol_target=params_used['vol_target'])
        
        alpaca_positions = trading_client.get_all_positions()
        current_positions = [{"symbol": p.symbol, "qty": float(p.qty)} for p in alpaca_positions]
        latest_prices = bars['close'].groupby(level=0).last().to_dict()
        # Pass whitelist to ONLY trade our symbols
        orders_to_place = calculate_orders(current_positions, targets, latest_prices, only_allow_symbols=symbols)

        logging_svc = LoggingService(db)
        metrics_svc = MetricsService(db)
        
        # --- AGENTIC FLOW ---
        agent = AgenticExecutor()
        
        # Try to get a real VIX proxy (SPY is usually in symbols)
        vix_val = 20.0
        try:
             if 'SPY' in bars.index.get_level_values(0):
                 # This is a very rough proxy if we don't have actual VIX data
                 # Better: fetch VIX from yfinance or just use 20 as default
                 vix_val = 20.0 # Placeholder
        except:
             pass

        market_context = {
            "equity": equity,
            "vix_close": vix_val,
            "latest_prices": latest_prices
        }
        
        agent_result = await agent.run(market_context)
        params_used = agent_result["trade_proposal"].get("params", params_used)
        analysis_text = agent_result["decision_reasoning"]
        
        if agent_result["trade_proposal"]["action"] == "HOLD":
             logging_svc.log_decision(run_id, params_used, {}, {}, [], reasoning=analysis_text)
             return {"run_id": run_id, "status": "shield_active", "reason": analysis_text}

        signals = compute_signal(
            bars, 
            fast_window=params_used['fast'], 
            slow_window=params_used['slow'],
            threshold=params_used.get('threshold', 0.0005)
        )
        current_vol = compute_volatility(bars, timeframe="5m")
        current_vol = compute_volatility(bars, timeframe="5m")
        targets = size_position(signals, current_vol, account_value=strategy_budget, vol_target=params_used['vol_target'])
        
        alpaca_positions = trading_client.get_all_positions()
        current_positions = [{"symbol": p.symbol, "qty": float(p.qty)} for p in alpaca_positions]
        current_positions = [{"symbol": p.symbol, "qty": float(p.qty)} for p in alpaca_positions]
        orders_to_place = calculate_orders(current_positions, targets, latest_prices, only_allow_symbols=symbols)

        signals_dict = signals.groupby(level=0).last()['signal'].to_dict()
        
        logging_svc.log_decision(run_id, params_used, signals_dict, targets, orders_to_place, reasoning=analysis_text)
        metrics_svc.record_daily_equity(equity)
        
        executed_ids = []
        if not dry_run:
            sl_pct = params_used.get('sl_pct', 0.02)
            tp_pct = params_used.get('tp_pct', 0.05)
            
            for order in orders_to_place:
                symbol = order["symbol"]
                curr_price = latest_prices.get(symbol, 0.0)
                
                # Calculate Bracket Prices
                if order["side"] == "buy":
                    # ENTRY: Use Bracket Order
                    stop_price = round(curr_price * (1 - sl_pct), 2)
                    limit_price = round(curr_price * (1 + tp_pct), 2)

                    req = MarketOrderRequest(
                        symbol=symbol,
                        qty=order["qty"],
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.BRACKET,
                        take_profit=TakeProfitRequest(limit_price=limit_price),
                        stop_loss=StopLossRequest(stop_price=stop_price)
                    )
                else:
                    # EXIT: Use Simple Market Order (No Brackets allowed on close)
                    req = MarketOrderRequest(
                        symbol=symbol,
                        qty=order["qty"],
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY
                    )
                # CANCEL PENDING ORDERS FIRST
                # This fixes 'insufficient qty available' caused by old brackets holding shares
                try:
                    # Robust way: Fetch & Cancel specific symbol's open orders
                    open_orders = trading_client.get_orders(GetOrdersRequest(
                        status=QueryOrderStatus.OPEN, 
                        symbols=[symbol]
                    ))
                    for o in open_orders:
                        trading_client.cancel_order_by_id(o.id)
                        # Minimal pause to ensure propagation (sync client blocks anyway but good to be safe)
                        await asyncio.sleep(0.1) 
                except Exception as e:
                    logger.warning(f"Failed to cancel open orders for {symbol}: {e}")

                try:
                    tx = trading_client.submit_order(req)
                    executed_ids.append(str(tx.id))
                    
                    # Create precise Order record with parent ID for tracking
                    new_order = Order(
                        run_id=run_id,
                        symbol=symbol,
                        qty=order["qty"],
                        side=order["side"],
                        status="submitted",
                        alpaca_id=str(tx.id)
                    )
                    db.add(new_order)
                    db.commit()
                except Exception as e:
                    logger.error(f"Order Failed {symbol}: {e}")
                    logging_svc.update_order_status(run_id, symbol, "failed")
        
        return {"run_id": run_id, "status": "success", "params": params_used, "orders_count": len(orders_to_place), "executed_ids": executed_ids}
    finally:
        db.close()

# --- API Endpoints ---
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await websocket.send_text(">>> WebSocket Stream Established. Listening for system events...")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class RunBotIn(BaseModel):
    dry_run: bool = True

@app.post("/bot/run_once")
async def run_bot(params: RunBotIn):
    return await execute_bot_cycle(params.dry_run)

@app.post("/bot/backtest")
def trigger_backtest(background_tasks: BackgroundTasks):
    logger.info("Triggering Backtest Training Session...")
    background_tasks.add_task(run_backtest, days_to_sim=1260)
    return {"status": "started"}

@app.get("/bot/metrics")
def get_bot_metrics():
    db = SessionLocal()
    try:
        return MetricsService(db).get_metrics()
    finally:
        db.close()

@app.get("/bot/bandit_stats")
def get_bandit_stats():
    db = SessionLocal()
    try:
        bandit = EpsilonGreedyBandit(db)
        state = bandit.get_state()
        # Sort by avg_reward descending to show best strategies first
        # state is a list of BanditState objects
        return sorted([
            {
                "param_key": s.param_key,
                "trials": s.trials,
                "total_reward": round(s.total_reward, 2),
                "avg_reward": round(s.avg_reward, 2)
            } for s in state
        ], key=lambda x: x['avg_reward'], reverse=True)
    finally:
        db.close()

@app.get("/bot/logs")
def get_logs(limit: int = 10):
    db = SessionLocal()
    try:
        return LoggingService(db).get_recent_runs(limit)
    finally:
        db.close()

class FeedbackIn(BaseModel):
    decision_id: int
    profit: float

@app.post("/bot/feedback")
def record_feedback(feedback: FeedbackIn):
    db = SessionLocal()
    try:
        decision = db.query(Decision).filter(Decision.id == feedback.decision_id).first()
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        bandit = EpsilonGreedyBandit(db)
        bandit.update_arm(decision.params_used, feedback.profit)
        decision.reward = feedback.profit
        db.commit()
        return {"status": "learned"}
    finally:
        db.close()

@app.get("/health")
def health(): return {"ok": True}

@app.get("/account")
def account():
    acct = trading_client.get_account()
    return {"equity": float(acct.equity), "buying_power": float(acct.buying_power)}

class MarketOrderIn(BaseModel):
    symbol: str
    qty: int
    side: str

@app.post("/orders/market")
def place_market_order(order_in: MarketOrderIn):
    req = MarketOrderRequest(
        symbol=order_in.symbol,
        qty=order_in.qty,
        side=OrderSide.BUY if order_in.side.lower() == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    tx = trading_client.submit_order(req)
    return {"id": str(tx.id), "status": "submitted"}
