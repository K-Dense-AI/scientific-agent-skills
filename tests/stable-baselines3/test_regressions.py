"""Bounded CPU behavior checks for RL semantics; no policy-quality claims."""
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

np = pytest.importorskip("numpy")
gym = pytest.importorskip("gymnasium")
sb3 = pytest.importorskip("stable_baselines3")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "stable-baselines3"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import custom_env_template
import train_rl_agent
import evaluate_agent
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.env_util import make_vec_env


def test_random_goal_is_part_of_the_observation_and_info_is_not_mutable_state():
    env = custom_env_template.CustomEnv()
    before, info = env.reset(seed=4)
    env._goal_position = (env._goal_position + 1) % env.grid_size
    after = env._get_obs()
    np.testing.assert_array_equal(before[:2], after[:2])
    assert not np.array_equal(before[2:], after[2:])
    info["agent_position"][:] = 123
    assert env.observation_space.contains(env._get_obs())


@pytest.mark.parametrize("grid_size", [0, 1, -1, 2.5, True])
def test_invalid_grid_does_not_loop_forever(grid_size):
    with pytest.raises(ValueError):
        custom_env_template.CustomEnv(grid_size=grid_size)


def test_invalid_action_is_rejected():
    env = custom_env_template.CustomEnv()
    env.reset(seed=1)
    for action in [-1, 4, 0.5, np.array([1])]:
        with pytest.raises(ValueError):
            env.step(action)


def test_vecenv_timeout_retains_terminal_observation():
    env = DummyVecEnv([lambda: gym.make("CustomEnv-v0", max_episode_steps=1)])
    try:
        env.seed(0)
        env.reset()
        raw = env.envs[0].unwrapped
        raw._agent_position = np.array([0, 0])
        raw._goal_position = np.array([4, 4])
        obs, _, done, infos = env.step(np.array([0]))
        assert done[0] and infos[0]["TimeLimit.truncated"]
        np.testing.assert_array_equal(infos[0]["terminal_observation"], [0, 0, 4, 4])
        assert not np.array_equal(obs[0], infos[0]["terminal_observation"])
    finally:
        env.close()


def test_normalized_training_pairs_best_and_final_and_eval_freezes_stats(tmp_path):
    model = train_rl_agent.train_agent(
        n_envs=2, total_timesteps=16, eval_freq=1, save_freq=1, normalize=True,
        n_eval_episodes=1, tensorboard=False, save_path=tmp_path / "models",
        log_dir=tmp_path / "logs", algorithm_kwargs=dict(n_steps=8, batch_size=8, n_epochs=1),
    )
    assert model.num_timesteps == 16
    root = tmp_path / "models"
    for checkpoint, stats in [("final_model.zip", "final_model_vecnormalize.pkl"),
                              ("best_model/best_model.zip", "best_model/vecnormalize.pkl"),
                              ("rl_model_2_steps.zip", "rl_model_vecnormalize_2_steps.pkl")]:
        assert (root / checkpoint).is_file() and (root / stats).is_file()
        saved_model = sb3.PPO.load(root / checkpoint)
        normalizer = VecNormalize.load(root / stats, make_vec_env("CartPole-v1", n_envs=1))
        try:
            # Initial train reset observes two states, then one per transition.
            assert normalizer.obs_rms.count == pytest.approx(saved_model.num_timesteps + 2.0001)
        finally:
            normalizer.close()
        captured = {}
        original = evaluate_agent.evaluate_policy
        def checked(policy, env, **kwargs):
            assert isinstance(env, VecNormalize)
            assert env.training is False and env.norm_reward is False
            before = env.obs_rms.mean.copy()
            result = original(policy, env, **kwargs)
            np.testing.assert_array_equal(env.obs_rms.mean, before)
            captured["result"] = result
            return result
        with patch.object(evaluate_agent, "evaluate_policy", checked):
            mean, _ = evaluate_agent.evaluate_agent(root / checkpoint,
                vec_normalize_path=root / stats, n_eval_episodes=2)
        assert 1 <= mean <= 500
        assert (mean * 2) % 1 == 0  # Raw CartPole rewards, despite normalized training.
        assert "result" in captured


def test_off_policy_class_and_replay_buffer_roundtrip(tmp_path):
    model = train_rl_agent.train_agent(
        algorithm=sb3.DQN, n_envs=1, total_timesteps=12, eval_freq=100, save_freq=100,
        n_eval_episodes=1, tensorboard=False, save_path=tmp_path / "models",
        log_dir=tmp_path / "logs", save_replay_buffer=True,
        algorithm_kwargs=dict(buffer_size=100, learning_starts=2, train_freq=1,
                              gradient_steps=1, batch_size=4, policy_kwargs=dict(net_arch=[16])),
    )
    assert model.replay_buffer.size() == 12
    loaded = sb3.DQN.load(tmp_path / "models/final_model.zip")
    loaded.load_replay_buffer(tmp_path / "models/final_model_replay_buffer.pkl")
    assert loaded.replay_buffer.size() == 12
    mean, _ = evaluate_agent.evaluate_agent(tmp_path / "models/final_model.zip",
                                          algorithm=sb3.DQN, n_eval_episodes=1)
    assert 1 <= mean <= 500


def test_evaluation_closes_environment_when_loading_fails():
    env = make_vec_env("CartPole-v1", n_envs=1)
    with patch.object(evaluate_agent, "make_vec_env", return_value=env), \
         patch.object(env, "close", wraps=env.close) as close:
        with pytest.raises(FileNotFoundError):
            evaluate_agent.evaluate_agent("missing-model.zip")
        close.assert_called_once()


def test_recurrent_evaluation_and_masking_guard(tmp_path):
    contrib = pytest.importorskip("sb3_contrib")
    model = contrib.RecurrentPPO("MlpLstmPolicy", "CartPole-v1", n_steps=8,
        batch_size=8, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[8]))
    try:
        model.learn(8)
        model.save(tmp_path / "recurrent")
    finally:
        model.get_env().close()
    mean, _ = evaluate_agent.evaluate_agent(tmp_path / "recurrent",
        algorithm=contrib.RecurrentPPO, n_eval_episodes=1)
    assert 1 <= mean <= 500
    with pytest.raises(ValueError, match="maskable"):
        evaluate_agent.evaluate_agent("unused", algorithm=contrib.MaskablePPO)


@pytest.mark.parametrize("algorithm", [sb3.SAC, sb3.TD3, sb3.DDPG])
def test_continuous_algorithms_collect_and_update(algorithm):
    env = make_vec_env("Pendulum-v1", n_envs=2, seed=7)
    try:
        model = algorithm("MlpPolicy", env, seed=7, device="cpu", buffer_size=32,
            learning_starts=2, batch_size=4, train_freq=1, gradient_steps=-1,
            policy_kwargs=dict(net_arch=[8]))
        model.learn(8)
        assert model.num_timesteps == 8 and model._n_updates > 0
        actions, _ = model.predict(env.reset(), deterministic=True)
        assert actions.shape == (2, 1) and np.isfinite(actions).all()
    finally:
        env.close()


def test_a2c_training_and_parameter_roundtrip():
    model = sb3.A2C("MlpPolicy", "CartPole-v1", n_steps=4, seed=0, device="cpu")
    try:
        model.learn(8)
        params = model.get_parameters()
        model.set_parameters(params)
        assert model.num_timesteps == 8 and model.policy.state_dict()
    finally:
        model.get_env().close()


def test_simultaneous_goal_and_timeout_are_not_bootstrapped_as_pure_timeout():
    env = DummyVecEnv([lambda: gym.make("CustomEnv-v0", max_episode_steps=1)])
    try:
        env.reset()
        raw = env.envs[0].unwrapped
        raw._agent_position = np.array([0, 0])
        raw._goal_position = np.array([0, 1])
        _, reward, done, infos = env.step(np.array([3]))
        assert done[0] and reward[0] == 1
        assert infos[0]["TimeLimit.truncated"] is False
    finally:
        env.close()
