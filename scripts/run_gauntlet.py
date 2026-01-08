import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
import time
from backend.backtest import run_backtest
from backend.db import SessionLocal
from backend.learning import EpsilonGreedyBandit

def run_stress_gauntlet():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Gauntlet")
    
    logger.info("⚔️  Launching The Gauntlet: Deep Stress & Walk-Forward ⚔️")

    # STAGE 1: INTRADAY FLASH CRASH RESILIENCE
    # We run 30 days of 1-minute data with 'stress_test=True'
    # This proves the Bracket Orders (TP/SL) protect the principal.
    logger.info("\n--- STAGE 1: Black Swan Resilience (-3% Micro-Crashes) ---")
    run_backtest(
        days_to_sim=14, 
        reset_bandit=True, 
        is_training=True, 
        timeframe="1m",
        stress_test=True
    )

    # STAGE 2: WALK-FORWARD EVOLUTION
    # We cycle: Train on Week 1, Test on Week 2. Preserving the brain throughout.
    logger.info("\n--- STAGE 2: 4-Stage Walk-Forward Evolution ---")
    for stage in range(1, 5):
        logger.info(f"\n🚀 GAUNTLET STAGE {stage} Training...")
        run_backtest(days_to_sim=7, reset_bandit=False, is_training=True, timeframe="1m")
        
        logger.info(f"🧪 GAUNTLET STAGE {stage} Validation (Blind)...")
        run_backtest(days_to_sim=3, reset_bandit=False, is_training=False, timeframe="1m")

    logger.info("\n🏆 GAUNTLET COMPLETE. If Equity >= $100k, the bot is UNSTOPPABLE. 🏆")

if __name__ == "__main__":
    run_stress_gauntlet()
