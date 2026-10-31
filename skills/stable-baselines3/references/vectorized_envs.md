# Vectorized Environments in Stable Baselines3

Targets SB3 2.9.0 / Gymnasium 1.3.0. Code snippets are illustrative fragments
sharing imports and environment/model variables; run process-based examples in
a Python file under a main guard. The bundled training script and repository
tests exercise DummyVecEnv and SubprocVecEnv with small CPU environments.

## Overview

Vectorized environments stack multiple independent environment instances into a single environment that processes actions and observations in batches. Instead of interacting with one environment at a time, you interact with `n` environments simultaneously.

**Benefits:**
- **Speed:** Process parallelism can help expensive environments; measure IPC overhead
- **Batching:** Collect transitions from independent environments; this does not guarantee better sample efficiency
- **Required for:** Frame stacking and normalization wrappers
- **Better for:** On-policy algorithms (PPO, A2C)

## VecEnv Types

### DummyVecEnv

Executes environments sequentially on the current Python process.

```python
import gymnasium as gym
from stable_baselines3.common.vec_env import DummyVecEnv

# Method 1: Using make_vec_env
from stable_baselines3.common.env_util import make_vec_env

env = make_vec_env("CartPole-v1", n_envs=4, vec_env_cls=DummyVecEnv)

# Method 2: Manual creation
def make_env():
    def _init():
        return gym.make("CartPole-v1")
    return _init

env = DummyVecEnv([make_env() for _ in range(4)])
```

**When to use:**
- Lightweight environments (CartPole, simple grids)
- When multiprocessing overhead > computation time
- Debugging (easier to trace errors)
- Single-threaded environments

**Performance:** No actual parallelism (sequential execution).

### SubprocVecEnv

Executes each environment in a separate process, enabling true parallelism.

```python
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.env_util import make_vec_env

env = make_vec_env("CartPole-v1", n_envs=8, vec_env_cls=SubprocVecEnv)
```

**When to use:**
- Computationally expensive environments (physics simulations, 3D games)
- When environment computation time justifies multiprocessing overhead
- When you need true parallel execution

**Important:** Requires wrapping code in `if __name__ == "__main__":` when using forkserver or spawn:

```python
if __name__ == "__main__":
    env = make_vec_env("CartPole-v1", n_envs=8, vec_env_cls=SubprocVecEnv)
    model = PPO("MlpPolicy", env)
    model.learn(total_timesteps=100000)
```

**Performance:** True parallelism across CPU cores.

## Quick Setup with make_vec_env

The easiest way to create vectorized environments:

```python
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv

# Basic usage
env = make_vec_env("CartPole-v1", n_envs=4)

# With SubprocVecEnv
env = make_vec_env("CartPole-v1", n_envs=8, vec_env_cls=SubprocVecEnv)

# With custom environment kwargs
env = make_vec_env(
    "MyEnv-v0",
    n_envs=4,
    env_kwargs={"difficulty": "hard", "max_steps": 500}
)

# With custom seed
env = make_vec_env("CartPole-v1", n_envs=4, seed=42)
```

## API Differences from Gymnasium

SB3 VecEnv is not Gymnasium VectorEnv. Do not pass a Gymnasium vector environment
directly to an SB3 algorithm or reuse its autoreset/info conventions:

### reset()

**Gymnasium Env:**
```python
obs, info = env.reset()
```

**VecEnv:**
```python
obs = env.reset()  # Returns only observations (numpy array)
# Access info via env.reset_infos (list of dicts)
infos = env.reset_infos
```

**Seeding and options:** Call `vec_env.seed(seed=seed)` and/or `vec_env.set_options(options)` before the initial `reset()`. Seed and options are discarded after each `reset()` call.

**Truncation vs termination:** When an episode ends, check `infos[env_idx]["TimeLimit.truncated"]` to distinguish timeout/truncation from natural termination. It is computed as `truncated and not terminated`, so simultaneous flags count as
termination for bootstrapping. Bootstrap through pure truncation using the
`terminal_observation`, not the auto-reset observation; do not bootstrap through
termination. SB3 algorithms implement this handling internally.

### step()

**Gymnasium Env:**
```python
obs, reward, terminated, truncated, info = env.step(action)
```

**VecEnv:**
```python
obs, rewards, dones, infos = env.step(actions)
# Returns 4-tuple instead of 5-tuple
# dones = terminated | truncated
# actions is an array of shape (n_envs,) or (n_envs, action_dim)
```

### Auto-reset

**VecEnv automatically resets environments when episodes end:**

```python
import numpy as np

obs = env.reset()  # Shape: (n_envs, obs_dim)
for _ in range(1000):
    actions = np.array([env.action_space.sample() for _ in range(env.num_envs)])
    obs, rewards, dones, infos = env.step(actions)
    # If dones[i] is True, env i was automatically reset
    # Final observation before reset available in infos[i]["terminal_observation"]
```

### Terminal Observations

When an episode ends, access the true final observation:

```python
obs, rewards, dones, infos = env.step(actions)

for i, done in enumerate(dones):
    if done:
        # The obs[i] is already the reset observation
        # True terminal observation is in info
        terminal_obs = infos[i]["terminal_observation"]
        print(f"Episode ended with terminal observation: {terminal_obs}")
```

## Training with Vectorized Environments

### On-Policy Algorithms (PPO, A2C)

On-policy algorithms benefit greatly from vectorization:

```python
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv

# Create vectorized environment
env = make_vec_env("CartPole-v1", n_envs=8, vec_env_cls=SubprocVecEnv)

# Train
model = PPO("MlpPolicy", env, verbose=1, n_steps=128)
model.learn(total_timesteps=100000)

# With n_envs=8 and n_steps=128:
# - Collects 8*128=1024 steps per rollout
# - Updates after every 1024 steps
```

Benchmark environment count and keep `n_steps * n_envs` and PPO minibatch
divisibility explicit; changing rollout size also changes optimization.

### Off-Policy Algorithms (SAC, TD3, DQN)

Off-policy algorithms can use vectorization but benefit less:

```python
from stable_baselines3 import SAC
from stable_baselines3.common.env_util import make_vec_env

# Use fewer environments (1-4)
env = make_vec_env("Pendulum-v1", n_envs=4)

# Set gradient_steps=-1 for efficiency
model = SAC(
    "MlpPolicy",
    env,
    verbose=1,
    train_freq=1,
    gradient_steps=-1,  # Do 1 gradient step per env step (4 total with 4 envs)
)
model.learn(total_timesteps=50000)
```

Use step-based `train_freq` with multiple environments; episode-based collection
is restricted to a single environment. `gradient_steps=-1` matches updates to
collected transitions after warmup; it is a compute/learning tradeoff.

## Wrappers for Vectorized Environments

### VecNormalize

Normalizes observations and rewards using running statistics.

```python
from stable_baselines3.common.vec_env import VecNormalize

env = make_vec_env("Pendulum-v1", n_envs=4)

# Wrap with normalization
env = VecNormalize(
    env,
    norm_obs=True,        # Normalize observations
    norm_reward=True,     # Normalize rewards
    clip_obs=10.0,        # Clip normalized observations
    clip_reward=10.0,     # Clip normalized rewards
    gamma=0.99,           # Discount factor for reward normalization
)

# Train
model = PPO("MlpPolicy", env)
model.learn(total_timesteps=50000)

# Save model AND normalization statistics
model.save("ppo_pendulum")
env.save("vec_normalize.pkl")

# Load for evaluation
env = make_vec_env("Pendulum-v1", n_envs=1)
env = VecNormalize.load("vec_normalize.pkl", env)
env.training = False  # Don't update stats during evaluation
env.norm_reward = False  # Don't normalize rewards during evaluation

model = PPO.load("ppo_pendulum", env=env)
```

**When to use:**
- Continuous control tasks (especially MuJoCo)
- When observation scales vary widely
- When rewards have high variance

**Important:**
- Statistics are NOT saved with model - save separately
- Disable training and reward normalization during evaluation

### VecFrameStack

Stacks observations from multiple consecutive frames.

```python
from stable_baselines3.common.vec_env import VecFrameStack

import ale_py
import gymnasium as gym
from stable_baselines3.common.env_util import make_atari_env
gym.register_envs(ale_py)

# ALE repeats once; SB3 AtariWrapper performs the four-frame skip.
env = make_atari_env("ALE/Pong-v5", n_envs=8,
                     env_kwargs={"frameskip": 1},
                     wrapper_kwargs={"frame_skip": 4})

# Stack 4 frames
env = VecFrameStack(env, n_stack=4)

# AtariWrapper produces HWC grayscale; stacking here gives (n_envs, 84, 84, 4).
# SB3 wraps HWC for its CNN; VecFrameStack concatenates along the channel axis.
model = PPO("CnnPolicy", env)
model.learn(total_timesteps=1000000)
```

**When to use:**
- Atari games (stack 4 frames)
- Environments where velocity information is needed
- Partial observability problems

### VecVideoRecorder

Records videos of agent behavior.

```python
from stable_baselines3.common.vec_env import VecVideoRecorder

env = make_vec_env("CartPole-v1", n_envs=1,
                   env_kwargs={"render_mode": "rgb_array"})

# Requires moviepy, FFmpeg, and pygame-ce for CartPole.
# Record videos
env = VecVideoRecorder(
    env,
    video_folder="./videos/",
    record_video_trigger=lambda x: x % 2000 == 0,  # Record every 2000 steps
    video_length=200,  # Max video length
    name_prefix="training"
)

model = PPO("MlpPolicy", env)
model.learn(total_timesteps=10000)
```

**Output:** MP4 clips in `./videos/`; close the outer wrapper to flush the last
clip. Frames accumulate in memory, so keep `video_length` bounded. A periodic
trigger records clips at vector-step intervals, not one video per episode.

### VecCheckNan

Checks for NaN or infinite values in observations and rewards.

```python
from stable_baselines3.common.vec_env import VecCheckNan

env = make_vec_env("CustomEnv-v0", n_envs=4)

# Add NaN checking (useful for debugging)
env = VecCheckNan(env, raise_exception=True, warn_once=True)

model = PPO("MlpPolicy", env)
model.learn(total_timesteps=10000)
```

**When to use:**
- Debugging custom environments
- Catching numerical instabilities
- Validating environment implementation

### VecTransposeImage

Transposes image observations from (height, width, channels) to (channels, height, width).

```python
from stable_baselines3.common.vec_env import VecTransposeImage

import ale_py
import gymnasium as gym
gym.register_envs(ale_py)
env = make_vec_env("ALE/Pong-v5", n_envs=4)

# Convert HWC to CHW format
env = VecTransposeImage(env)

model = PPO("CnnPolicy", env)
```

**When to use:**
- When environment returns images in HWC format
- SB3 expects CHW format for CNN policies

## Advanced Usage

### Custom VecEnv

Create custom vectorized environment:

```python
from stable_baselines3.common.vec_env import DummyVecEnv
import gymnasium as gym

class CustomVecEnv(DummyVecEnv):
    def step_wait(self):
        # Custom logic before/after stepping
        obs, rewards, dones, infos = super().step_wait()
        # Modify observations/rewards/etc
        return obs, rewards, dones, infos
```

### Environment Method Calls

Call methods on wrapped environments:

```python
env = make_vec_env("MyEnv-v0", n_envs=4)

# Call method on all environments
env.env_method("set_difficulty", "hard")

# Call method on specific environment
env.env_method("reset_level", indices=[0, 2])

# Get attribute from all environments
levels = env.get_attr("current_level")
```

### Setting Attributes

```python
# Prefer an explicit underlying-env setter, applying changes at reset.
env.env_method("set_difficulty", "hard")

# For existing wrapped attributes, Gymnasium searches the wrapper chain:
env.env_method("set_wrapper_attr", "max_steps", 1000, indices=[1, 3])
```

### Checking Attributes

```python
# Check if attribute exists on all sub-environments (added SB3 2.6.0)
if env.has_attr("current_level"):
    levels = env.get_attr("current_level")
```

## Performance Optimization

### Choosing Number of Environments

**On-Policy (PPO, A2C):**
```python
# General rule: 4-16 environments
# More environments = faster data collection
n_envs = 8
env = make_vec_env("CartPole-v1", n_envs=n_envs)

# Adjust n_steps to maintain same rollout length
# Total steps per rollout = n_envs * n_steps
model = PPO("MlpPolicy", env, n_steps=128)  # 8*128 = 1024 steps/rollout
```

**Off-Policy (SAC, TD3, DQN):**
```python
# General rule: 1-4 environments
# More doesn't help as much (replay buffer provides diversity)
n_envs = 4
env = make_vec_env("Pendulum-v1", n_envs=n_envs)

model = SAC("MlpPolicy", env, gradient_steps=-1)  # 1 grad step per env step
```

### CPU Core Utilization

```python
import multiprocessing

# Use one less than total cores (leave one for Python main process)
n_cpus = max(multiprocessing.cpu_count() - 1, 1)
env = make_vec_env("MyEnv-v0", n_envs=n_cpus, vec_env_cls=SubprocVecEnv)
```

### Memory Considerations

```python
# Large replay buffer + many environments = high memory usage
# Reduce buffer size if memory constrained
model = SAC(
    "MlpPolicy",
    env,
    buffer_size=100_000,  # Reduced from 1M
)
```

## Common Issues

### Issue: "Can't pickle local object"

**Cause:** A captured environment resource may not serialize, or spawned workers
cannot safely import the entry module. SubprocVecEnv uses cloudpickle for factories,
so nested factories and lambdas are supported; they are not inherently the error.
Create native handles inside each worker rather than capturing an already-open
simulator. Each factory must return a distinct environment. Use a main guard.
The released source selects forkserver when available, otherwise spawn.

```python
import gymnasium as gym
from stable_baselines3.common.vec_env import SubprocVecEnv

def make_env():
    return gym.make("CartPole-v1")

if __name__ == "__main__":
    env = SubprocVecEnv([make_env for _ in range(4)])
    try:
        obs = env.reset()
    finally:
        env.close()
```

### Issue: Different behavior between single and vectorized env

**Cause:** Auto-reset in vectorized environments.

**Solution:** Handle terminal observations correctly:

```python
obs, rewards, dones, infos = env.step(actions)
for i, done in enumerate(dones):
    if done:
        terminal_obs = infos[i]["terminal_observation"]
        # Process terminal_obs if needed
```

### Issue: Slower with SubprocVecEnv than DummyVecEnv

**Cause:** Environment too lightweight (multiprocessing overhead > computation).

**Solution:** Use DummyVecEnv for simple environments:

```python
# For CartPole, use DummyVecEnv
env = make_vec_env("CartPole-v1", n_envs=8, vec_env_cls=DummyVecEnv)
```

### Issue: Training crashes with SubprocVecEnv

**Cause:** Environment not properly isolated or has shared state.

**Solution:**
- Ensure environment has no shared global state
- Wrap code in `if __name__ == "__main__":`
- Use DummyVecEnv for debugging

## Best Practices

1. **Use appropriate VecEnv type:**
   - DummyVecEnv: Simple environments (CartPole, basic grids)
   - SubprocVecEnv: Complex environments (MuJoCo, Unity, 3D games)

2. **Adjust hyperparameters for vectorization:**
   - Use `max(freq // n_envs, 1)` for EvalCallback/CheckpointCallback call frequencies
   - Maintain same `n_steps * n_envs` for on-policy algorithms

3. **Save normalization statistics:**
   - Always save VecNormalize stats with model
   - Disable training during evaluation

4. **Monitor memory usage:**
   - More environments = more memory
   - Reduce buffer size if needed

5. **Test with DummyVecEnv first:**
   - Easier debugging
   - Ensure environment works before parallelizing

## Examples

### Basic Training Loop

```python
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv

# Create vectorized environment
env = make_vec_env("CartPole-v1", n_envs=8, vec_env_cls=SubprocVecEnv)

# Train
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=100000)

# Evaluate
obs = env.reset()
for _ in range(1000):
    action, _states = model.predict(obs, deterministic=True)
    obs, rewards, dones, infos = env.step(action)
```

### With Normalization

```python
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize

# Create and normalize
env = make_vec_env("Pendulum-v1", n_envs=4)
env = VecNormalize(env, norm_obs=True, norm_reward=True)

# Train
model = PPO("MlpPolicy", env)
model.learn(total_timesteps=50000)

# Save both
model.save("model")
env.save("vec_normalize.pkl")

# Load for evaluation
eval_env = make_vec_env("Pendulum-v1", n_envs=1)
eval_env = VecNormalize.load("vec_normalize.pkl", eval_env)
eval_env.training = False
eval_env.norm_reward = False

model = PPO.load("model", env=eval_env)
```

## Additional Resources

- Official SB3 VecEnv Guide: https://stable-baselines3.readthedocs.io/en/v2.9.0/guide/vec_envs.html
- VecEnv API Reference: https://stable-baselines3.readthedocs.io/en/v2.9.0/guide/vec_envs.html#module-stable_baselines3.common.vec_env
- Multiprocessing Best Practices: https://docs.python.org/3/library/multiprocessing.html

Atari fragments are source-verified, not executed in this refresh. Install ALE
and its supported ROM setup; keep action repeat, sticky actions, life-loss
termination and reward clipping explicit. Use a separate evaluation environment
with raw reward reporting and full-game episode semantics when comparing scores.
[SB3 AtariWrapper source](https://github.com/DLR-RM/stable-baselines3/blob/v2.9.0/stable_baselines3/common/atari_wrappers.py).
