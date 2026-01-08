import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.services.monte_carlo import run_monte_carlo

if __name__ == "__main__":
    print("🕵️ Starting Monte Carlo Robustness Verification...")
    run_monte_carlo(iterations=1000)
