import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from datetime import datetime, timedelta
from backend.backtest import run_backtest
from backend.db import SessionLocal
from backend.models import DailyEquity, Decision
from backend.learning import EpsilonGreedyBandit

def run_blind_test():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("BlindTest")
    
    logger.info("🕵️ Starting Blind Out-of-Sample Validation 🕵️")
    logger.info("Objective: Verify 'Turbo-Scalp' performance on recent data WITHOUT learning.")

    # 1. PURGE PREVIOUS RESULTS FOR CLEAN ANALYSIS
    db = SessionLocal()
    logger.info("Cleaning up old simulation data...")
    db.query(DailyEquity).delete()
    db.query(Decision).delete()
    db.commit()

    # 2. LOCK THE BEST ARM
    bandit = EpsilonGreedyBandit(db)
    best_arm = bandit.get_best_arm()
    db.close()
    
    logger.info(f"Using Locked Winner Params: {best_arm}")

    # 2. RUN EVALUATION BACKTEST (is_training=False)
    # Testing the last 14 days of 1-minute data
    # We use reset_bandit=False to preserve the weights, but is_training=False means we don't update them.
    run_backtest(
        days_to_sim=14, 
        reset_bandit=False, 
        is_training=False, 
        timeframe="1m"
    )

    logger.info("\n🏆 Blind Test Complete!")
    logger.info("Check the Frontend Dashboard or 'Daily Equity' history for the OOS performance curve.")

if __name__ == "__main__":
    run_blind_test()
