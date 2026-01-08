import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from backend.db import SessionLocal
from backend.services.advisor import StrategyAdvisor

# Init Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Advisor")

def main():
    logger.info("🕵️ Starting AI Strategy Retrospective...")
    db = SessionLocal()
    try:
        advisor = StrategyAdvisor(db)
        result = advisor.perform_retrospective()
        logger.info("--- Retrospective Results ---")
        print(result)
        logger.info("✅ Optimization complete. Bandit weights updated via AI Feedback.")
    except Exception as e:
        logger.error(f"Advisor Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
