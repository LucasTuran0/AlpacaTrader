import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from datetime import datetime, timedelta
from backend.backtest import run_backtest
from backend.db import SessionLocal
from backend.models import BanditState

def run_triple_blind_test():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TripleBlind")

    # PERIODS:
    # 1. Train on 2022 - Sept 2025 (The known past)
    # 2. Blind Test on Oct 2025 - Today (The absolute most recent 'Unknown' regime)
    today = datetime.now()
    ninety_days_ago = today - timedelta(days=90)

    logger.info("🛡️ PHASE 1: Training on the Past (2022 -> 3 months ago)")
    run_backtest(days_to_sim=1000, end_date=ninety_days_ago, reset_bandit=True, is_training=True)

    logger.info("\n🛡️ PHASE 2: TRIPLE-BLIND TEST (The Last 90 Days)")
    logger.info("This data has zero 'Bull Market' bias. It's the most recent, messy reality.")
    
    # reset_bandit=False (Keep the brain)
    # is_training=False (Locked mode)
    run_backtest(days_to_sim=90, end_date=today, reset_bandit=False, is_training=False)

    logger.info("\n✅ Triple-Blind Validation Complete.")
    logger.info("If the last 90 days are profitable, the bot is NOT overfitted to the long-term bull market.")

if __name__ == "__main__":
    run_triple_blind_test()
