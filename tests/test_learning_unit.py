from backend.learning import EpsilonGreedyBandit
from backend.models import BanditState


class TestBanditKeyGeneration:
    def test_basic_key(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        key = bandit._get_arm_key({"fast": 10, "slow": 30, "vol_target": 0.25})
        assert key == "10_30_0.25"

    def test_extended_key_with_extra_params(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        params = {"fast": 10, "slow": 30, "vol_target": 0.25, "sl_pct": 0.01, "tp_pct": 0.03, "threshold": 0.001}
        key = bandit._get_arm_key(params)
        assert "0.01" in key
        assert "0.03" in key
        assert "0.001" in key

    def test_different_sl_tp_different_keys(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        p1 = {"fast": 10, "slow": 30, "vol_target": 0.25, "sl_pct": 0.01, "tp_pct": 0.03, "threshold": 0.001}
        p2 = {"fast": 10, "slow": 30, "vol_target": 0.25, "sl_pct": 0.02, "tp_pct": 0.05, "threshold": 0.001}
        assert bandit._get_arm_key(p1) != bandit._get_arm_key(p2)


class TestBanditUpdateAndChoose:
    def test_update_creates_state(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        params = {"fast": 10, "slow": 30, "vol_target": 0.25}
        bandit.update_arm(params, 50.0)
        state = db_session.query(BanditState).first()
        assert state is not None
        assert state.trials == 1
        assert state.total_reward == 50.0

    def test_multiple_updates_average(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        params = {"fast": 10, "slow": 30, "vol_target": 0.25}
        bandit.update_arm(params, 100.0)
        bandit.update_arm(params, 0.0)
        state = db_session.query(BanditState).first()
        assert state.trials == 2
        assert state.avg_reward == 50.0

    def test_choose_arm_returns_dict(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        arm = bandit.choose_arm()
        assert isinstance(arm, dict)
        assert "fast" in arm
        assert "slow" in arm
        assert "vol_target" in arm

    def test_get_best_arm_favors_highest_reward(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        bandit.update_arm({"fast": 15, "slow": 40, "vol_target": 0.5}, -10.0)
        bandit.update_arm({"fast": 30, "slow": 70, "vol_target": 0.4}, 100.0)
        best = bandit.get_best_arm()
        assert best["fast"] == 30
        assert best["slow"] == 70

    def test_get_state_returns_list(self, db_session):
        bandit = EpsilonGreedyBandit(db_session)
        bandit.update_arm({"fast": 10, "slow": 30, "vol_target": 0.25}, 50.0)
        state = bandit.get_state()
        assert isinstance(state, list)
        assert len(state) == 1
