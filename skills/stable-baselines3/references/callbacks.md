# Stable Baselines3 callbacks

Targets SB3 2.9.0. Sources: [callback guide and API](https://stable-baselines3.readthedocs.io/en/v2.9.0/guide/callbacks.html)
and [released implementation](https://github.com/DLR-RM/stable-baselines3/blob/v2.9.0/stable_baselines3/common/callbacks.py).
Examples are fragments requiring the model and environments named below; the
complete tested pipeline is [train_rl_agent.py](../scripts/train_rl_agent.py).

## Timing and callback state

`BaseCallback._on_step()` runs once per vector step. `n_calls` counts calls;
`num_timesteps` counts transitions across all environments. `eval_freq` and
`CheckpointCallback.save_freq` use calls. For a requested transition interval use
`max(interval // n_envs, 1)`; the actual interval is a multiple of `n_envs`.
`EveryNTimesteps(n_steps, callback)` and `LogEveryNTimesteps(n_steps)` instead
compare total transitions, with the same vector-step granularity.

`_init_callback` runs when initialized for a learn call. `_on_training_start`,
`_on_rollout_start`, `_on_rollout_end`, and `_on_training_end` delimit collection
and training. Off-policy algorithms also invoke rollout hooks. `_on_step`
returning False stops learning; return True otherwise. Rollout-end occurs before
the subsequent gradient update, so it does not expose that update's losses.

Available attributes: `model`, `training_env`, `logger`, `n_calls`,
`num_timesteps`, `locals`, `globals`, and `parent`. The `locals` dictionary is
specific to the algorithm and collection phase. An event callback attaches itself
as its child's `parent`; `CallbackList` propagates its own parent, rather than
becoming the child's parent. Do not assume `locals['total_timesteps']` or
`locals['entropy_losses']` exists at every step.

## Evaluation and checkpointing

Use a separate environment with the same observation transforms. `make_vec_env`
adds Monitor. When using VecNormalize, wrap both train and evaluation environments
in matching order and set evaluation `training=False`, `norm_reward=False`.
EvalCallback synchronizes training statistics before each evaluation. Evaluation
during training is validation for model selection; reserve fresh final test seeds.

```python
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback

# env and eval_env already constructed; n_envs is the training count.
evaluation = EvalCallback(
    eval_env,
    eval_freq=max(10000 // n_envs, 1),
    n_eval_episodes=5,
    deterministic=True,
    best_model_save_path="logs/best/",
    log_path="logs/eval/",
)
checkpoint = CheckpointCallback(
    save_freq=max(10000 // n_envs, 1),
    save_path="logs/checkpoints/",
    name_prefix="rl_model",
    save_replay_buffer=True,   # Applies only when a replay buffer exists.
    save_vecnormalize=True,
)
model.learn(100000, callback=[evaluation, checkpoint])
```

`EvalCallback` saves `best_model.zip` and `evaluations.npz`; it does not save
VecNormalize state with that best model. Attach a `callback_on_new_best` that saves
`model.get_vec_normalize_env()` at the same step, as the bundled training script
does. Loading final-run statistics alongside an earlier best checkpoint changes
the policy input transform. Periodic CheckpointCallback files include the actual
transition count, e.g. `rl_model_10000_steps.zip`,
`rl_model_vecnormalize_10000_steps.pkl`, and optionally
`rl_model_replay_buffer_10000_steps.pkl`.

## Stopping and logging

```python
from stable_baselines3.common.callbacks import (
    EvalCallback, StopTrainingOnRewardThreshold,
    StopTrainingOnNoModelImprovement, StopTrainingOnMaxEpisodes,
    LogEveryNTimesteps, ProgressBarCallback, CallbackList,
)

stop_reward = StopTrainingOnRewardThreshold(reward_threshold=200)
stop_plateau = StopTrainingOnNoModelImprovement(
    max_no_improvement_evals=10, min_evals=20,
)
evaluation = EvalCallback(
    eval_env, eval_freq=max(10000 // n_envs, 1),
    callback_on_new_best=stop_reward,
    callback_after_eval=stop_plateau,
)
callbacks = CallbackList([evaluation, LogEveryNTimesteps(n_steps=1000)])
# log_interval belongs to learn(), not the algorithm constructor.
model.learn(100000, callback=callbacks, log_interval=None)
```

The reward callback continues while best reward is below the threshold. Plateau
stopping attaches after every evaluation, not just new best events.
`StopTrainingOnMaxEpisodes(max_episodes=1000)` uses a total target of
`1000 * n_envs`, not exactly 1000 episodes globally (and counts can overshoot at a
vector step). `ProgressBarCallback()` or `learn(progress_bar=True)` requires both
`tqdm` and `rich`, included in SB3 extras.

## Custom metrics across all environments

Collect actual Monitor summaries, avoiding fabricated zero rewards or only
looking at environment zero. A bounded deque avoids growth over long runs.

```python
from collections import deque
import numpy as np
from stable_baselines3.common.callbacks import BaseCallback

class EpisodeMetrics(BaseCallback):
    def __init__(self):
        super().__init__()
        self.returns = deque(maxlen=100)

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done and 'episode' in info:
                self.returns.append(info['episode']['r'])
                if 'is_success' in info:
                    self.logger.record_mean('custom/success', float(info['is_success']))
        if self.returns:
            self.logger.record('custom/mean_return_100', float(np.mean(self.returns)))
        return True
```

`logger.record` stores the latest value; `record_mean` aggregates values until
logger dump. Output routes depend on logger configuration (for TensorBoard set
`tensorboard_log=...` when constructing the model). `info['is_success']` is the
standard success key used by EvalCallback; define success and its denominator
explicitly for the task. Do not equate entropy to task success.

## Schedules and curricula

Pass learning-rate schedules through the algorithm API so training updates do
not overwrite callback changes. The same principle applies to off-policy models
with separate actor and critic optimizers.

```python
from stable_baselines3.common.utils import LinearSchedule
from stable_baselines3 import PPO

model = PPO('MlpPolicy', env, learning_rate=LinearSchedule(3e-4, 3e-5, 1.0))
```

For curriculum changes expose a setter on the underlying Gymnasium environment,
then call `training_env.env_method('set_difficulty', new_difficulty)` at a chosen
event. Have the environment apply the pending difficulty at its next reset, not
mid-episode. A custom callback should keep an explicit schedule index; do not loop
through every prior threshold and reapply all stages every step. Keep evaluation
difficulty fixed and separately described.

Debug a callback by inspecting types/keys in `self.locals` on its first call;
avoid printing large observations or saving on every step. If a custom metric or
population-training method is not implemented, treat that fragment as a design
sketch, not executable training logic.
