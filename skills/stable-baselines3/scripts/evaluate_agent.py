"""Evaluate trusted SB3 checkpoints with reproducible seeds and original rewards.

Recreate the training environment and observation wrappers exactly. The helper
supports core algorithms and RecurrentPPO; MaskablePPO needs contrib's specialized
evaluation helper and is deliberately rejected here.
"""

from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import VecNormalize, VecVideoRecorder


def evaluate_agent(
    model_path, env_id="CartPole-v1", n_eval_episodes=10, deterministic=True,
    render=False, record_video=False, video_folder="./videos/", vec_normalize_path=None,
    *, algorithm=PPO, seed=20000, device="cpu", video_length=1000, env_kwargs=None,
):
    """Return mean and population SD of whole-episode undiscounted returns.

    Pass the class used for training via algorithm, and the normalization file
    from that exact checkpoint. Missing requested statistics fail immediately.
    Video records one bounded clip starting at reset, not every evaluation episode.
    Rendering and recording are separate modes. Files must come from a trusted
    source because SB3/VecNormalize persistence includes serialized Python objects.
    """
    if not isinstance(n_eval_episodes, int) or n_eval_episodes <= 0:
        raise ValueError("n_eval_episodes must be a positive integer")
    if render and record_video:
        raise ValueError("choose render or record_video for one environment")
    if record_video and (not isinstance(video_length, int) or video_length < 1):
        raise ValueError("video_length must be a positive integer")
    if algorithm.__name__ == "MaskablePPO":
        raise ValueError("MaskablePPO requires sb3_contrib.common.maskable.evaluation.evaluate_policy")
    if vec_normalize_path is not None and not Path(vec_normalize_path).is_file():
        raise FileNotFoundError(vec_normalize_path)
    kwargs = dict(env_kwargs or {})
    kwargs["render_mode"] = "rgb_array" if record_video else "human" if render else None
    env = make_vec_env(env_id, n_envs=1, seed=seed, env_kwargs=kwargs)
    try:
        if vec_normalize_path is not None:
            env = VecNormalize.load(str(vec_normalize_path), env)
            env.training = False
            env.norm_reward = False
        model = algorithm.load(model_path, env=env, device=device)
        if record_video:
            env = VecVideoRecorder(
                env, video_folder, record_video_trigger=lambda step: step == 0,
                video_length=video_length, name_prefix="evaluation",
            )
        mean, std = evaluate_policy(
            model, env, n_eval_episodes=n_eval_episodes,
            deterministic=deterministic, render=render,
        )
        print(f"Mean reward: {mean:.2f} +/- {std:.2f} (episode SD)")
        return float(mean), float(std)
    finally:
        env.close()


def watch_agent(model_path, env_id="CartPole-v1", n_episodes=5,
                deterministic=True, vec_normalize_path=None, **kwargs):
    """Human rendering through the same normalization and recurrent-state path."""
    return evaluate_agent(
        model_path, env_id, n_episodes, deterministic, render=True,
        vec_normalize_path=vec_normalize_path, **kwargs,
    )


def compare_models(model_paths, env_id="CartPole-v1", n_eval_episodes=10,
                   deterministic=True, *, normalization_paths=None, **kwargs):
    """Compare checkpoints using the same reset seed; SD is not a confidence interval.

    normalization_paths optionally maps each checkpoint path to its matching stats.
    Reusing evaluation seeds aids comparison; use independent training runs to
    estimate training variability and new held-out seeds after model selection.
    """
    results = {}
    for path in model_paths:
        stats_path = None if normalization_paths is None else normalization_paths[path]
        mean, std = evaluate_agent(
            path, env_id, n_eval_episodes, deterministic,
            vec_normalize_path=stats_path, **kwargs,
        )
        results[path] = {"mean": mean, "std": std}
    return results


if __name__ == "__main__":
    evaluate_agent("./models/best_model/best_model.zip")
