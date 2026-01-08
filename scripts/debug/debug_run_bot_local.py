import os
import uuid
from dotenv import load_dotenv

# Mock FastAPI models
class RunBotIn:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run

def debug_run():
    print("--- Debugging Run Bot Logic ---")
    load_dotenv("backend/.env")
    
    # Imports mirroring app.py
    from backend.market_data import MarketDataProvider
    from backend.strategy.ts_mom import compute_signal
    from backend.strategy.risk import compute_volatility, size_position
    from backend.services.execution import calculate_orders
    from backend.services.logging import LoggingService
    from backend.services.metrics import MetricsService
    from backend.db import SessionLocal, Base, engine
    from backend.learning import EpsilonGreedyBandit
    from alpaca.trading.client import TradingClient
    
    try:
        # 1. Config
        API_KEY = os.getenv("ALPACA_API_KEY")
        API_SECRET = os.getenv("ALPACA_API_SECRET")
        PAPER = True
        trading_client = TradingClient(API_KEY, API_SECRET, paper=PAPER)
        market_provider = MarketDataProvider()
        
        params = RunBotIn(dry_run=False)
        run_id = str(uuid.uuid4())
        symbols = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
        
        print("1. Market Data...")
        bars = market_provider.get_bars(symbols, lookback_days=365)
        print("   - Got bars.")
        
        print("2. Account...")
        acct = trading_client.get_account()
        equity = float(acct.equity)
        print(f"   - Equity: {equity}")
        
        print("3. Init Services...")
        db = SessionLocal()
        logger = LoggingService(db)
        metrics = MetricsService(db)
        bandit = EpsilonGreedyBandit(db)
        
        print("4. Bandit Choose...")
        params_used = bandit.choose_arm()
        print(f"   - Params: {params_used}")
        
        print("5. Compute Signal...")
        signals = compute_signal(bars, fast_window=params_used['fast'], slow_window=params_used['slow'])
        print("   - Signals computed.")
        
        print("6. Risk...")
        current_vol = compute_volatility(bars)
        targets = size_position(
            signals, 
            current_vol, 
            account_value=equity, 
            vol_target=params_used['vol_target']
        )
        print("   - Targets size computed.")
        
        print("7. Calculate Orders...")
        alpaca_positions = trading_client.get_all_positions()
        current_positions = [{"symbol": p.symbol, "qty": float(p.qty)} for p in alpaca_positions]
        latest_prices = bars['close'].groupby(level=0).last().to_dict()
        orders_to_place = calculate_orders(current_positions, targets, latest_prices)
        print(f"   - Orders: {len(orders_to_place)}")
        
        print("8. Log Decision...")
        signals_dict = signals.groupby(level=0).last()['signal'].to_dict()
        logger.log_decision(
            run_id=run_id,
            params=params_used,
            signals=signals_dict,
            targets=targets,
            orders=orders_to_place
        )
        print("   - Logged.")
        
        print("9. Record Metrics...")
        metrics.record_daily_equity(equity)
        print("   - Metrics recorded.")
        
        print("SUCCESS! Logic is sound.")
        
    except Exception as e:
        print("\n!!! EXCEPTION CAUGHT !!!")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    debug_run()
