"""CPU-friendly training with held-out monitoring and matching normalization files.

Run SubprocVecEnv callers from a file under an if __name__ == '__main__' guard.
Evaluation during training selects checkpoints; use new seeds for final testing.
"""

from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, EvalCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


class SaveBestNormalization(BaseCallback):
    """Pair each EvalCallback best model with statistics from that same step."""

    def __init__(self, path):
        super().__init__()
        self.path = Path(path)

    def _on_step(self):
        normalizer = self.model.get_vec_normalize_env()
        if normalizer is not None:
            normalizer.save(str(self.path))
        return True


def train_agent(
    env_id="CartPole-v1", algorithm=PPO, policy="MlpPolicy", n_envs=4,
    total_timesteps=100000, eval_freq=10000, save_freq=10000,
    log_dir="./logs/", save_path="./models/", *, seed=0, eval_seed=10000,
    n_eval_episodes=10, normalize=False, vec_env_cls=DummyVecEnv,
    algorithm_kwargs=None, tensorboard=True, device="cpu",
    save_replay_buffer=False, env_kwargs=None,
):
    """Train and save a core SB3 model; return it with its environments closed.

    Frequencies are requested total transitions (rounded down to a vector step,
    at least one call). total_timesteps is a lower bound due to rollout collection.
    algorithm_kwargs supplies algorithm-specific parameters, e.g. PPO n_steps.
    normalize writes final_model_vecnormalize.pkl and best_model/vecnormalize.pkl,
    and matching statistics for periodic checkpoints. Use a fresh output directory
    per run. For off-policy continuation, opt in to replay-buffer saving.
    """
    for name, value in (("n_envs", n_envs), ("total_timesteps", total_timesteps),
                        ("eval_freq", eval_freq), ("save_freq", save_freq),
                        ("n_eval_episodes", n_eval_episodes)):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    log_dir, save_path = Path(log_dir), Path(save_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    save_path.mkdir(parents=True, exist_ok=True)
    best_path = save_path / "best_model"
    env = eval_env = None
    try:
        env = make_vec_env(env_id, n_envs=n_envs, seed=seed,
                           vec_env_cls=vec_env_cls, env_kwargs=env_kwargs)
        eval_env = make_vec_env(env_id, n_envs=1, seed=eval_seed, env_kwargs=env_kwargs)
        params = dict(verbose=1, tensorboard_log=str(log_dir) if tensorboard else None,
                      seed=seed, device=device)
        params.update(algorithm_kwargs or {})
        if normalize:
            gamma = params.get("gamma", 0.99)
            env = VecNormalize(env, gamma=gamma)
            eval_env = VecNormalize(eval_env, training=False, norm_reward=False, gamma=gamma)
        evaluation = EvalCallback(
            eval_env, best_model_save_path=str(best_path), log_path=str(log_dir / "eval"),
            eval_freq=max(eval_freq // n_envs, 1), n_eval_episodes=n_eval_episodes,
            deterministic=True,
            callback_on_new_best=SaveBestNormalization(best_path / "vecnormalize.pkl"),
        )
        checkpoint = CheckpointCallback(
            save_freq=max(save_freq // n_envs, 1), save_path=str(save_path),
            name_prefix="rl_model", save_replay_buffer=save_replay_buffer,
            save_vecnormalize=normalize,
        )
        model = algorithm(policy, env, **params)
        model.learn(total_timesteps=total_timesteps, callback=[evaluation, checkpoint],
                    tb_log_name=f"{algorithm.__name__}_{env_id}")
        model.save(str(save_path / "final_model"))
        if normalize:
            env.save(str(save_path / "final_model_vecnormalize.pkl"))
        if save_replay_buffer and getattr(model, "replay_buffer", None) is not None:
            model.save_replay_buffer(str(save_path / "final_model_replay_buffer.pkl"))
        print(f"Training complete! Actual transitions: {model.num_timesteps}")
        print(f"Final model: {save_path / 'final_model.zip'}")
        if (best_path / "best_model.zip").exists():
            print(f"Best validation model: {best_path / 'best_model.zip'}")
        return model
    finally:
        if eval_env is not None:
            eval_env.close()
        if env is not None:
            env.close()


if __name__ == "__main__":
    train_agent()
