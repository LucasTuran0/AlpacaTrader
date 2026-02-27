import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from datetime import datetime, timedelta
from backend.backtest import run_backtest

def run_walk_forward():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("WalkForward")

    # 1. Period Setup
    # Train: 2022 -> end of 2024
    # Test: 2025 -> Today
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)
    three_years_ago = today - timedelta(days=365 * 3)

    logger.info(" Step 1: Training Phase (Lookback Period)")
    logger.info("Processing 2 years of history to train the Bandit...")
    # Train on everything up to 1 year ago.
    # days_to_sim = 730 (~2 years of simulation)
    # The backtester adds its own 365-day buffer.
    run_backtest(days_to_sim=730, end_date=one_year_ago, reset_bandit=True, is_training=True)

    logger.info("\n Step 2: Blind Validation Phase (Out-of-Sample)")
    logger.info("Testing the 'Locked' strategy on the most recent 12 months of 'unseen' data...")
    # Test on the last 1 year.
    # reset_bandit=False (keep the weights we just learned)
    # is_training=False (don't learn from this data, just exploit)
    run_backtest(days_to_sim=365, end_date=today, reset_bandit=False, is_training=False)

    logger.info("\n Walk-Forward Validation Complete.")
    logger.info("Check the Equity Chart on the Dashboard to compare the 'Training' vs 'Validation' slopes.")

if __name__ == "__main__":
    run_walk_forward()
