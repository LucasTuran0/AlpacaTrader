from backend.db import Base, engine, SessionLocal
from backend.models import BanditState, Decision
from backend.learning import EpsilonGreedyBandit
import sys

def test_bandit():
    print("1. Creating Tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   Tables created.")
    except Exception as e:
        print(f"FAILED to create tables: {e}")
        return

    db = SessionLocal()
    try:
        print("2. Initializing Bandit...")
        bandit = EpsilonGreedyBandit(db)
        
        print("3. Choosing Arm...")
        arm = bandit.choose_arm()
        print(f"   Chosen Arm: {arm}")
        
        print("4. Updating Arm (Fake Feedback)...")
        bandit.update_arm(arm, 10.0)
        print("   Update success.")
        
        print("5. Verifying State...")
        states = db.query(BanditState).all()
        for s in states:
            print(f"   State: {s.param_key} | Avg: {s.avg_reward} | Trials: {s.trials}")
            
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_bandit()
