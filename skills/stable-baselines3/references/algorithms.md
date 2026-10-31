# Stable Baselines3 Algorithm Reference

Targets SB3/SB3-Contrib 2.9.0. Algorithm performance and tuning suggestions below
are task-dependent starting points, not guarantees or benchmark results.
Sources: [action support](https://stable-baselines3.readthedocs.io/en/v2.9.0/guide/algos.html),
[algorithm APIs](https://stable-baselines3.readthedocs.io/en/v2.9.0/modules/ppo.html),
[RL experiment guidance](https://stable-baselines3.readthedocs.io/en/v2.9.0/guide/rl_tips.html).

## Algorithm Comparison Table

| Algorithm | Type | Action Space | Sample Efficiency | Training Speed | Use Case |
|-----------|------|--------------|-------------------|----------------|----------|
| **PPO** | On-Policy | Box/Discrete/MultiDiscrete/MultiBinary | Medium | Fast | General-purpose, stable |
| **A2C** | On-Policy | Box/Discrete/MultiDiscrete/MultiBinary | Low | Very Fast | Quick prototyping, multiprocessing |
| **SAC** | Off-Policy | Continuous | High | Medium | Continuous control, sample-efficient |
| **TD3** | Off-Policy | Continuous | High | Medium | Continuous control, deterministic |
| **DDPG** | Off-Policy | Continuous | High | Medium | Continuous control (use TD3 instead) |
| **DQN** | Off-Policy | Discrete | Medium | Medium | Discrete actions, Atari games |
| **HER** | Replay buffer | Box or Discrete, per underlying algorithm | Task-dependent | Task-dependent | Goal-conditioned tasks |
| **RecurrentPPO** | On-Policy | Box/Discrete/MultiDiscrete/MultiBinary | Medium | Slow | Partial observability (POMDP) |

## Detailed Algorithm Characteristics

### PPO (Proximal Policy Optimization)

**Overview:** General-purpose on-policy algorithm with good performance across many tasks.

**Strengths:**
- Stable and reliable training
- Works with supported action space types (Discrete, Box, MultiDiscrete, MultiBinary)
- Good balance between sample efficiency and training speed
- Excellent for multiprocessing with vectorized environments
- Easy to tune

**Weaknesses:**
- Less sample-efficient than off-policy methods
- Requires many environment interactions

**Best For:**
- General-purpose RL tasks
- When stability is important
- When you have cheap environment simulations
- Tasks with continuous or discrete actions

**Hyperparameter Guidance:**
- `n_steps`: 2048-4096 for continuous, 128-256 for Atari
- `learning_rate`: 3e-4 is a good default
- `n_epochs`: 10 for continuous, 4 for Atari
- `batch_size`: 64
- `gamma`: 0.99 (0.995-0.999 for long episodes)

### A2C (Advantage Actor-Critic)

**Overview:** Synchronous variant of A3C, simpler than PPO but less stable.

**Strengths:**
- Very fast training (simpler than PPO)
- Works with supported action space types
- Good for quick prototyping
- Memory efficient

**Weaknesses:**
- Less stable than PPO
- Requires careful hyperparameter tuning
- Lower sample efficiency

**Best For:**
- Quick experimentation
- When training speed is critical
- Simple environments

**Hyperparameter Guidance:**
- `n_steps`: 5-256 depending on task
- `learning_rate`: 7e-4
- `gamma`: 0.99

### SAC (Soft Actor-Critic)

**Overview:** Off-policy algorithm with entropy regularization, widely used for continuous control.

**Strengths:**
- Excellent sample efficiency
- Very stable training
- Automatic entropy tuning
- Good exploration through stochastic policy
- Suitable baseline for robotics

**Weaknesses:**
- Only supports continuous action spaces (Box)
- Slower wall-clock time than on-policy methods
- More complex hyperparameters

**Best For:**
- Continuous control (robotics, physics simulations)
- When sample efficiency is critical
- Expensive environment simulations
- Tasks requiring good exploration

**Hyperparameter Guidance:**
- `learning_rate`: 3e-4
- `buffer_size`: 1M for most tasks
- `learning_starts`: 10000
- `batch_size`: 256
- `tau`: 0.005 (target network update rate)
- `train_freq`: 1 with `gradient_steps=-1` as one update-to-data ratio to evaluate

### TD3 (Twin Delayed DDPG)

**Overview:** Improved DDPG with double Q-learning and delayed policy updates.

**Strengths:**
- High sample efficiency
- Deterministic policy (good for deployment)
- More stable than DDPG
- Good for continuous control

**Weaknesses:**
- Only supports continuous action spaces (Box)
- Less exploration than SAC
- Requires careful tuning

**Best For:**
- Continuous control tasks
- When deterministic policies are preferred
- Sample-efficient learning

**Hyperparameter Guidance:**
- `learning_rate`: 1e-3
- `buffer_size`: 1M
- `learning_starts`: 10000
- `batch_size`: 256 (current TD3 default)
- `policy_delay`: 2 (update policy every 2 critic updates)

### DDPG (Deep Deterministic Policy Gradient)

**Overview:** Early off-policy continuous control algorithm.

**Strengths:**
- Continuous action space support
- Off-policy learning

**Weaknesses:**
- Less stable than TD3 or SAC
- Sensitive to hyperparameters
- Generally outperformed by TD3

**Best For:**
- Legacy compatibility
- **Recommendation:** Use TD3 instead for new projects

### DQN (Deep Q-Network)

**Overview:** Classic off-policy algorithm for discrete action spaces.

**Strengths:**
- Sample-efficient for discrete actions
- Experience replay enables reuse of past data
- Proven success on Atari games

**Weaknesses:**
- Only supports discrete action spaces
- Can be unstable without proper tuning
- Overestimation bias

**Best For:**
- Discrete action tasks
- Atari games and similar environments
- When sample efficiency matters

**Hyperparameter Guidance:**
- `learning_rate`: 1e-4
- `buffer_size`: 100K-1M depending on task
- `learning_starts`: 50000 for Atari
- `batch_size`: 32
- `exploration_fraction`: 0.1
- `exploration_final_eps`: 0.05

**Variants:**
- **QR-DQN**: Distributional RL version for better value estimates (SB3-Contrib)
- **MaskablePPO**: Contrib supports invalid action masking with PPO; there is no released `MaskableDQN` in contrib 2.9.0.

### HER (Hindsight Experience Replay)

**Overview:** Not a standalone algorithm but a replay buffer strategy for goal-conditioned tasks.

**Strengths:**
- Dramatically improves learning in sparse reward settings
- Learns from failures by relabeling goals
- Supports SB3 off-policy algorithms using compatible Dict replay buffers (SAC, TD3, DDPG, DQN)

**Weaknesses:**
- Only for goal-conditioned environments
- Requires specific observation structure (Dict with "observation", "achieved_goal", "desired_goal")

**Best For:**
- Goal-conditioned tasks (robotics manipulation, navigation)
- Sparse reward environments
- Tasks where goal is clear but reward is binary

**Usage (illustrative, supply the task environment):**

The environment must return Dict observations containing `observation`,
`achieved_goal`, and `desired_goal`, and expose vectorized `compute_reward`.
Set `learning_starts` beyond the first full episode so HER can sample completed
episodes. Pass an environment when loading a HER model, including for inference.

```python
from stable_baselines3 import SAC, HerReplayBuffer

model = SAC(
    "MultiInputPolicy",
    env,
    replay_buffer_class=HerReplayBuffer,
    replay_buffer_kwargs=dict(
        n_sampled_goal=4,
        goal_selection_strategy="future",  # or "episode", "final"
    ),
)
```

### RecurrentPPO

Use `from sb3_contrib import RecurrentPPO` and `"MlpLstmPolicy"`
(or `"CnnLstmPolicy"` / `"MultiInputLstmPolicy"`). During manual prediction
pass and retain `state`, and pass `episode_start=dones` from the preceding
VecEnv step; initialize it to all True after reset. Core `evaluate_policy`
handles those recurrent states. See the [official recurrent example](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_recurrent.html).

**Overview:** PPO with LSTM policy for handling partial observability.

**Strengths:**
- Handles partial observability (POMDP)
- Can learn temporal dependencies
- Good for memory-required tasks

**Weaknesses:**
- Slower training than standard PPO
- More complex to tune
- Requires sequential data

**Best For:**
- Partially observable environments
- Tasks requiring memory (e.g., navigation without full map)
- Time-series problems

## Algorithm Selection Guide

### Decision Tree

1. **What is your action space?**
   - **Continuous (Box)** → Consider PPO, SAC, or TD3
   - **Discrete** → Consider PPO, A2C, or DQN
   - **MultiDiscrete/MultiBinary** → Use PPO or A2C

2. **Is sample efficiency critical?**
   - **Yes (expensive simulations)** → Use off-policy: SAC, TD3, DQN, or HER
   - **No (cheap simulations)** → Use on-policy: PPO, A2C

3. **Do you need fast wall-clock training?**
   - **Yes** → Use PPO or A2C with vectorized environments
   - **No** → Any algorithm works

4. **Is the task goal-conditioned with sparse rewards?**
   - **Yes** → Use HER with SAC or TD3
   - **No** → Continue with standard algorithms

5. **Is the environment partially observable?**
   - **Yes** → Use RecurrentPPO
   - **No** → Use standard algorithms

### Quick Recommendations

- **Starting out / General tasks:** PPO
- **Continuous control / Robotics:** SAC
- **Discrete actions / Atari:** DQN or PPO
- **Goal-conditioned / Sparse rewards:** SAC + HER
- **Fast prototyping:** A2C
- **Sample efficiency critical:** SAC, TD3, or DQN
- **Partial observability:** RecurrentPPO

## Training Configuration Tips

### For On-Policy Algorithms (PPO, A2C)

```python
# Illustrative configuration; env_id and imports are supplied by the caller.
# Use DummyVecEnv first; SubprocVecEnv calls require a guarded Python entry point.
env = make_vec_env(env_id, n_envs=8)

model = PPO(
    "MlpPolicy",
    env,
    n_steps=2048,  # Collect this many steps per environment before update
    batch_size=64,
    n_epochs=10,
    learning_rate=3e-4,
    gamma=0.99,
    device="cpu",  # Often faster than GPU for small MLP tasks
)
```

### For Off-Policy Algorithms (SAC, TD3, DQN)

```python
# Use step-based collection with multiple environments.
env = make_vec_env(env_id, n_envs=4)

model = SAC(
    "MlpPolicy",
    env,
    buffer_size=1_000_000,
    learning_starts=10000,
    batch_size=256,
    train_freq=1,
    gradient_steps=-1,  # Do 1 gradient step per env step (4 with 4 envs)
    learning_rate=3e-4,
)
```

## Common Pitfalls

1. **Using DQN with continuous actions** - DQN only works with discrete actions
2. **Assuming parallelism always helps** - benchmark environment cost against IPC overhead
3. **Changing n_envs without checking rollout size** - PPO uses n_envs * n_steps; choose batch_size dividing that product
4. **Using too large replay buffer** - Can cause memory issues
5. **Not tuning learning rate** - Critical for stable training
6. **Mixing reward units** - if normalizing training rewards, report original rewards during evaluation
7. **Wrong policy type** - Use "CnnPolicy" for images, "MultiInputPolicy" for dict observations

## Reporting benchmark results

Use the exact environment version, wrapper stack, action repeat, reward clipping,
training budget and independent training seeds. Current Gymnasium MuJoCo IDs use
v5 (for example `HalfCheetah-v5`); scores from v4 or different wrappers are not a
reference target. Use the Zoo's versioned configurations and actual evaluation
artifacts instead of unsourced expected reward numbers. The tiny tests for this
skill do not measure comparative algorithm quality.

## SB3-Contrib (Experimental Algorithms)

These algorithms live in the separate **[sb3-contrib](https://github.com/Stable-Baselines-Team/stable-baselines3-contrib)** package, not core SB3:

| Algorithm | Use Case |
|-----------|----------|
| **MaskablePPO** | Discrete actions with action masking (invalid moves masked out) |
| **CrossQ** | Continuous control; sample-efficient off-policy (added SB3-Contrib 2.4+) |
| **QR-DQN** | Distributional DQN for better value estimates |
| **RecurrentPPO** | Partial observability (POMDP) with LSTM policy |
| **TQC** | Continuous control with distributional critics |

Install with `uv pip install "sb3-contrib==2.9.0"`.

## Additional Resources

- **RL Baselines3 Zoo**: Collection of pre-trained agents and hyperparameters: https://github.com/DLR-RM/rl-baselines3-zoo
- **Hyperparameter Tuning**: Use Optuna for systematic tuning
- **Custom Policies**: Extend base policies for custom network architectures
- **PPO + MlpPolicy on CPU**: For small MLP tasks (CartPole, Pendulum), `device="cpu"` often trains faster than GPU

### Masked evaluation

For MaskablePPO, `True` marks a valid action. Use
`sb3_contrib.common.maskable.callbacks.MaskableEvalCallback` and
`sb3_contrib.common.maskable.evaluation.evaluate_policy`; core evaluators do not
supply masks. In SubprocVecEnv, implement `action_masks()` inside the environment;
`ActionMasker` is not the supported multiprocessing route. `check_env` samples
actions without consulting masks, so validation needs a defined response to those
actions. [Official masking contract](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html).
