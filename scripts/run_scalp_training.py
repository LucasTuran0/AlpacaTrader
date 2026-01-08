import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
import time
from datetime import datetime, timedelta
from backend.backtest import run_backtest
from backend.services.optimizer import generate_parameter_grid, mutate_parameters
from backend.db import SessionLocal
from backend.learning import EpsilonGreedyBandit
from backend.services.advisor import StrategyAdvisor
import subprocess
import yfinance as yf
import pandas as pd

def run_scalp_training():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ScalpTraining")
    
    logger.info("⚡ Starting High-Velocity Scalp Calibration ⚡")
    logger.info("Objective: Optimize for 0.1% Threshold triggers using 1-hour bar granularity.")

    # 1. FETCH 1-HOUR DATA (Last 2 years)
    # Note: We do this manually here to override the default 1d behavior in backtest.py if needed,
    # but for simplicity, we'll just tell run_backtest to use a shorter window if it supports it.
    # Actually, let's just use the existing run_backtest but with specialized Epochs.

    # EPCOH 1: Scalp Grid Discovery
    logger.info("\n--- EPOCH 1: Scalp Grid Discovery ---")
    grid = generate_parameter_grid()
    
    db = SessionLocal()
    bandit = EpsilonGreedyBandit(db, epsilon=0.4)
    bandit.set_arms(grid)
    db.close()

    # We simulate 30 days of high-fidelity 1-minute 'Scalp' behavior
    run_backtest(days_to_sim=30, reset_bandit=True, is_training=True, inject_arms=grid, timeframe="1m")

    logger.info("Waiting for AI Advisor to refine Scalp parameters...")
    subprocess.run(["python", "run_advisor.py"])

    # EPOCH 2: High-Density Refinement
    logger.info("\n--- EPOCH 2: High-Density Refinement ---")
    db = SessionLocal()
    bandit = EpsilonGreedyBandit(db, epsilon=0.1)
    best_arm = bandit.get_best_arm()
    logger.info(f"Top Performer: {best_arm}")
    
    mutations = mutate_parameters(best_arm)
    bandit.set_arms(mutations)
    db.close()

    run_backtest(days_to_sim=30, reset_bandit=False, is_training=True, inject_arms=mutations, timeframe="1m")
    
    logger.info("Waiting for AI Advisor for Final Calibration...")
    subprocess.run(["python", "run_advisor.py"])

    logger.info("\n🏆 Scalp Calibration Complete! High-Velocity parameters are now live.")

if __name__ == "__main__":
    run_scalp_training()
