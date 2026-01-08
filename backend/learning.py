import random
from sqlalchemy.orm import Session
from .models import BanditState, Decision

class EpsilonGreedyBandit:
    def __init__(self, db: Session, epsilon: float = 0.2):
        self.db = db
        self.epsilon = epsilon
        # Default arms as a fallback
        self.arms = [
            {"fast": 5, "slow": 15, "vol_target": 0.4},
            {"fast": 10, "slow": 30, "vol_target": 0.3},
            {"fast": 20, "slow": 60, "vol_target": 0.15},
            {"fast": 50, "slow": 100, "vol_target": 0.1},
        ]
        self._load_arms_from_db()

    def _load_arms_from_db(self):
        """Loads all parameter keys from BanditState and adds them to possible arms."""
        states = self.db.query(BanditState).all()
        for s in states:
            try:
                # Key format: "fast_slow_vol"
                parts = s.param_key.split("_")
                arm = {"fast": int(parts[0]), "slow": int(parts[1]), "vol_target": float(parts[2])}
                if arm not in self.arms:
                    self.arms.append(arm)
            except:
                continue

    def set_arms(self, arms_list: list[dict]):
        """Injects a massive set of arms for deep optimization."""
        self.arms = arms_list

    def _get_arm_key(self, params: dict) -> str:
        return f"{params['fast']}_{params['slow']}_{params['vol_target']}"

    def get_best_arm(self) -> dict:
        # 1. Query DB for all arm stats
        states = self.db.query(BanditState).all()
        state_map = {s.param_key: s for s in states}
        
        best_arm = self.arms[1] # Default to standard
        best_reward = -float('inf')
        
        for arm in self.arms:
            key = self._get_arm_key(arm)
            if key in state_map:
                avg = state_map[key].avg_reward
                if avg > best_reward:
                    best_reward = avg
                    best_arm = arm
            else:
                # If arm never tried, treat as neutral (0.0) or optimistic
                if 0.0 > best_reward:
                    best_reward = 0.0
                    best_arm = arm
                    
        return best_arm

    def choose_arm(self) -> dict:
        """Selects parameters using Epsilon-Greedy strategy."""
        if random.random() < self.epsilon:
            # Explore: Random arm
            return random.choice(self.arms)
        else:
            # Exploit: Best historical arm
            return self.get_best_arm()

    def update_arm(self, params: dict, reward: float):
        """Updates the running stats for the chosen arm."""
        key = self._get_arm_key(params)
        
        state = self.db.query(BanditState).filter(BanditState.param_key == key).first()
        if not state:
            state = BanditState(param_key=key, trials=0, total_reward=0.0, avg_reward=0.0)
            self.db.add(state)
        
        state.trials += 1
        state.total_reward += reward
        state.avg_reward = state.total_reward / state.trials
        
        self.db.commit()
