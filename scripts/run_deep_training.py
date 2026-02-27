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

def run_deep_training_session():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DeepTraining")
    
    logger.info(" Starting 1-Hour Genetic Intelligence Sweep ")
    
    # 1. GENERATION 1: WIDE GRID DISCOVERY
    logger.info("\n--- EPOCH 1: Wide Grid Discovery ---")
    grid = generate_parameter_grid()
    logger.info(f"Injecting {len(grid)} parameter sets into the Bandit...")
    
    db = SessionLocal()
    bandit = EpsilonGreedyBandit(db, epsilon=0.5) # High exploration
    bandit.set_arms(grid)
    db.close()
    
    # Run 5-year backtest (Train on wide grid)
    run_backtest(days_to_sim=1260, reset_bandit=True, is_training=True, inject_arms=grid)
    
    logger.info("Waiting for AI Advisor to analyze Epoch 1...")
    subprocess.run(["python", "run_advisor.py"])
    
    # 2. GENERATION 2: CONVERSION & MUTATION
    logger.info("\n--- EPOCH 2: Genetic Mutation & Neighborhood Search ---")
    db = SessionLocal()
    bandit = EpsilonGreedyBandit(db, epsilon=0.2)
    best_arm = bandit.get_best_arm()
    logger.info(f"Best arm from Epoch 1: {best_arm}")
    
    mutations = mutate_parameters(best_arm)
    logger.info(f"Generated {len(mutations)} genetic mutations from the winner.")
    bandit.set_arms(mutations)
    db.close()
    
    # Run 5-year backtest again (Refine on mutations)
    run_backtest(days_to_sim=1260, reset_bandit=False, is_training=True, inject_arms=mutations)
    
    logger.info("Waiting for AI Advisor to analyze Epoch 2...")
    subprocess.run(["python", "run_advisor.py"])
    
    # 3. GENERATION 3: FINAL LOCKING
    logger.info("\n--- EPOCH 3: Final Convergence & AI Retrospective ---")
    # Low epsilon for exploitation
    run_backtest(days_to_sim=1260, reset_bandit=False, is_training=True)
    
    logger.info("\n Deep Training Complete! The Master Model is now locked.")
    logger.info("Run 'python run_stress_test.py' to see the final robustness score.")

if __name__ == "__main__":
    run_deep_training_session()
