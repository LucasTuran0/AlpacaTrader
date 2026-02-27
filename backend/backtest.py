import logging
import uuid
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from backend.db import SessionLocal, engine, Base
from backend.models import Decision, DailyEquity, BanditState
from backend.market_data import MarketDataProvider
from backend.learning import EpsilonGreedyBandit
from backend.strategy.ts_mom import compute_signal
from backend.strategy.risk import compute_volatility, size_position
from backend.config import TRADED_SYMBOLS
import yfinance as yf

# Load env from backend folder (still needed for DB/keys if used elsewhere)
load_dotenv("backend/.env")

logger = logging.getLogger("PaperPilot")

def run_backtest(days_to_sim=200, start_date=None, end_date=None, reset_bandit=True, is_training=True, inject_arms=None, timeframe="1d", **kwargs):
    logger.info(f"--- Starting Backtest Session ({timeframe}) ---")
    
    db = SessionLocal()
    provider = MarketDataProvider()
    try:
        # Clear old training state for a clean run if requested
        if reset_bandit:
            db.query(BanditState).delete()
            db.commit()

        bandit = EpsilonGreedyBandit(db)
        if inject_arms:
            bandit.set_arms(inject_arms)
        
        # 1. Setup Virtual Account
        equity = 100000.0
        symbols = TRADED_SYMBOLS
        
        # 2. Get Data
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=days_to_sim + 365)
        
        if timeframe == "1m":
            from alpaca.data.timeframe import TimeFrame
            logger.info(f"Fetching 1-Minute data from Alpaca for {symbols}...")
            # For 1m, Alpaca is better. We'll use provider.
            # Limit days_to_sim for 1m to avoid timeouts/overload
            if days_to_sim > 30:
                logger.warning("1m backtest limited to 30 days for stability.")
                days_to_sim = 30
            
            bars = provider.get_bars(symbols, lookback_days=days_to_sim, timeframe=TimeFrame.Minute)
            
            # For VIX (Regime), we still need yfinance (Daily)
            vix_raw = yf.download("^VIX", start=start_date, end=end_date, interval="1d", progress=False)
            vix_bars = vix_raw.rename(columns={'Close': 'close'})
        else:
            logger.info(f"Fetching Daily data from Yahoo Finance...")
            download_list = list(set(symbols + ["^VIX"]))
            raw_bars = yf.download(download_list, start=start_date, end=end_date, interval="1d", progress=False)
            
            if len(download_list) > 1:
                bars = raw_bars.stack(level=1).rename_axis(['timestamp', 'symbol']).swaplevel(0, 1).sort_index()
            else:
                bars = raw_bars.copy()
                bars['symbol'] = download_list[0]
                bars = bars.set_index('symbol', append=True).swaplevel(0, 1).sort_index()
                bars.index.names = ['symbol', 'timestamp']

            bars = bars.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            })
            vix_bars = bars.xs("^VIX", level="symbol") if "^VIX" in bars.index.get_level_values("symbol").unique() else None
            bars = bars[bars.index.get_level_values("symbol") != "^VIX"]

        time_level = 'timestamp'
        # Crucial: Determine the tradable timeline AFTER removing VIX
        dates = bars.index.get_level_values(time_level).unique().sort_values()
        
        if timeframe == "1m":
            # For intraday, the provider already fetched Exactly the days_to_sim.
            # So we start from the beginning of the fetched data.
            sim_start_index = 0
        else:
            # For Daily, we might have fetched extra for vol lookbacks.
            sim_start_index = len(dates) - days_to_sim
        
        if sim_start_index < 0:
            logger.warning("Not enough data. Starting from earliest possible point.")
            sim_start_index = 0
            
        logger.info(f"Simulating from {dates[sim_start_index]} to {dates[-1]}")
        
        # 3. Simulation Loop
        for i in range(sim_start_index, len(dates) - 1):
            current_date = dates[i]
            next_date = dates[i+1]
            
            # Use data up to current_date
            current_data = bars.loc[bars.index.get_level_values(time_level) <= current_date]
            
            # STRESS TEST: Inject a 'Flash Crash' on a random bar (e.g. periodically)
            # This forces the bot to handle a sudden -3% drop.
            is_crash = False
            if kwargs.get('stress_test') and (i - sim_start_index) > 10 and (i % 200 == 0):
                is_crash = True
                logger.warning(f" FLASH CRASH SIMULATED at {current_date} ")
            
            # A. Bandit Choose
            if is_training:
                params_used = bandit.choose_arm()
            else:
                # Validation mode: Always exploit the best arm found during training
                params_used = bandit.get_best_arm()
            
            # B. Strategy & Signals
            signals = compute_signal(
                current_data, 
                fast_window=params_used['fast'], 
                slow_window=params_used['slow'],
                threshold=params_used.get('threshold', 0.0005)
            )
            
            # C. Risk Scaling
            current_vol = compute_volatility(current_data, timeframe=timeframe)
            
            # Extract VIX for regime detection. 
            # If intraday, we match the current_date's calendar date to the VIX daily close.
            vix_today = 20.0
            if vix_bars is not None:
                v_lookup = current_date.normalize() if hasattr(current_date, 'normalize') else current_date
                if v_lookup in vix_bars.index:
                    vix_today = vix_bars.loc[v_lookup]['close']

            targets = size_position(
                signals, 
                current_vol, 
                account_value=equity, 
                vol_target=params_used['vol_target'],
                vix_value=vix_today
            )
            
            # D. Simulated PnL (T to T+1)
            daily_pnl = 0.0
            
            # Extract SL/TP from params or use defaults
            sl_pct = params_used.get('sl_pct', 0.02)
            tp_pct = params_used.get('tp_pct', 0.05)
            stop_triggered = False
            tp_triggered = False
            
            prices_t = bars.xs(current_date, level=time_level)
            prices_t1 = bars.xs(next_date, level=time_level)
            
            for symbol, target_usd in targets.items():
                if symbol in prices_t.index and symbol in prices_t1.index:
                    s_t = prices_t.loc[symbol]
                    s_t1 = prices_t1.loc[symbol]
                    
                    price_initial = s_t['close']
                    price_final = s_t1['close']
                    price_high = s_t1['high']
                    price_low = s_t1['low']
                    
                    if is_crash:
                        # Force a deep wick down to trigger SL
                        price_low = price_initial * 0.97
                        price_final = price_initial * 0.975 # Partial recovery
                    
                    change_pct = (price_final - price_initial) / price_initial
                    
                    # Size weighted impact
                    # We check if Low hit SL or High hit TP during the next bar
                    # (Note: This is a daily approximation. For 1-min bars, it's very accurate)
                    
                    # 1. Check Stop Loss
                    if (price_low - price_initial) / price_initial < -sl_pct:
                        daily_pnl += (target_usd / price_initial) * (price_initial * (1 - sl_pct) - price_initial)
                        stop_triggered = True
                    # 2. Check Take Profit
                    elif (price_high - price_initial) / price_initial > tp_pct:
                        daily_pnl += (target_usd / price_initial) * (price_initial * (1 + tp_pct) - price_initial)
                        tp_triggered = True
                    else:
                        daily_pnl += (target_usd / price_initial) * (price_final - price_initial)
            
            # E. Update Training State
            equity += daily_pnl
            if is_training:
                bandit.update_arm(params_used, daily_pnl)
            
            # F. Persist to DB
            run_id = f"sim_{current_date.strftime('%Y%m%d')}"
            sig_dict = signals.groupby(level=0).last()['signal'].to_dict()
            
            # Generate Analysis Text
            reasons = []
            for symbol, target in targets.items():
                sig = sig_dict.get(symbol, 0)
                if sig > 0:
                    reasons.append(f"LONG {symbol} (Momentum Positive)")
                elif sig < 0:
                    reasons.append(f"SHORT {symbol} (Momentum Negative)")
                else:
                    reasons.append(f"FLAT {symbol} (No Trend)")
            
            analysis_text = f"Strategy: TS_MOM | Params: {params_used['fast']}/{params_used['slow']} | VolTarget: {params_used['vol_target']} | Rational: " + "; ".join(reasons)
            if stop_triggered:
                analysis_text += " |  STOP LOSS TRIGGERED"
            if tp_triggered:
                analysis_text += " |  TAKE PROFIT TRIGGERED"

            decision = Decision(
                run_id=run_id,
                timestamp=pd.to_datetime(current_date).to_pydatetime(),
                params_used=params_used,
                signals=sig_dict,
                targets=targets,
                reasoning=analysis_text,
                reward=daily_pnl
            )
            db.merge(decision)
            
            eq_record = DailyEquity(
                date=pd.to_datetime(current_date).to_pydatetime(),
                equity=equity,
                drawdown_pct=0.0
            )
            db.merge(eq_record)
            
            if (i - sim_start_index) % 10 == 0:
                year_indicator = current_date.year
                logger.info(f" [{year_indicator}] Progress: {current_date.date()} | Equity: ${equity:,.0f} | Last PnL: ${daily_pnl:,.2f}")
                # Commit every 10 steps so the Dashboard shows live progress!
                db.commit()
                
        db.commit()
        logger.info(" Deep Training Complete. 5 years of history processed.")
        
    except Exception as e:
        logger.error(f" Backtest Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    # Setup console logging for standalone run
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # 5 years = ~1260 trading days
    run_backtest(days_to_sim=1260)
