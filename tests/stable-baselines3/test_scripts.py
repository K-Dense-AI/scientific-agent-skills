"""Tests for the Stable-Baselines3 environment, training, and evaluation templates.

`custom_env_template` is the piece with real logic, and all of it is checkable
against values fixed by the template's own docstring: action 0 moves up, the
reward is 1.0 on reaching the goal and -0.1 times the Euclidean distance
otherwise, positions clip at the grid edge, and the registered environment
truncates at 100 steps. Those are the numbers a user copies and then relies on,
so a transposed direction table or a sign flip in the reward must fail here.

The environment also has to satisfy SB3's `check_env`, and that is asserted in
both directions: the template passes with no warnings, while a subclass that
returns float64 observations against a float32 `Box` is rejected -- otherwise
"check_env passed" would prove only that the checker was called.

The training and evaluation templates are thin wrappers over SB3, so they are
covered by one small end-to-end run each: a real (tiny) PPO fit through
`train_agent`, driven in a subprocess to explicitly exercise `SubprocVecEnv`, and
`evaluate_agent` loading the saved model back.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import textwrap
import unittest
import warnings
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "stable-baselines3"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="the templates need numpy")
gym = pytest.importorskip("gymnasium", reason="the templates need gymnasium")
pytest.importorskip("torch", reason="stable-baselines3 needs torch")
pytest.importorskip("stable_baselines3", reason="the templates need stable-baselines3")

from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.env_checker import check_env  # noqa: E402

import custom_env_template  # noqa: E402
import evaluate_agent  # noqa: E402
import train_rl_agent  # noqa: E402

# Only `custom_env_template` has a runnable demo: its `__main__` block validates
# the environment and returns. `train_rl_agent`'s trains for 100k timesteps and
# `evaluate_agent`'s loads a checkpoint that does not exist in a clean checkout,
# so neither can be run as documentation; both are covered by the tests below.
DemoBlockTests = skill_contract.cli.demo_test_case(
    SKILL_ROOT, ("custom_env_template.py",)
)

#: Direction table from the template's own step() docstring.
MOVES = {0: (-1, 0), 1: (1, 0), 2: (0, -1), 3: (0, 1)}


def placed_env(agent, goal, grid_size=5, render_mode=None):
    """A reset environment with the agent and goal pinned where we want them."""
    env = custom_env_template.CustomEnv(grid_size=grid_size, render_mode=render_mode)
    env.reset(seed=0)
    env._agent_position = np.array(agent)
    env._goal_position = np.array(goal)
    return env


class SpaceDefinitionTests(unittest.TestCase):
    def test_the_action_space_is_the_four_documented_moves(self) -> None:
        self.assertEqual(custom_env_template.CustomEnv().action_space.n, 4)

    def test_the_observation_box_spans_the_grid_and_is_float32(self) -> None:
        # SB3 expects float32 observations; float64 silently costs a conversion
        # warning at best and a space mismatch at worst.
        for grid_size in (3, 5, 8):
            with self.subTest(grid_size=grid_size):
                space = custom_env_template.CustomEnv(grid_size=grid_size).observation_space
                self.assertEqual(space.shape, (4,))
                self.assertEqual(space.dtype, np.float32)
                np.testing.assert_allclose(space.low, [0.0] * 4)
                np.testing.assert_allclose(space.high, [grid_size - 1] * 4)

    def test_the_metadata_declares_the_render_modes_it_implements(self) -> None:
        self.assertEqual(
            custom_env_template.CustomEnv.metadata["render_modes"],
            ["human", "rgb_array"],
        )


class ResetTests(unittest.TestCase):
    def test_the_same_seed_gives_the_same_starting_layout(self) -> None:
        first, first_info = custom_env_template.CustomEnv().reset(seed=17)
        second, second_info = custom_env_template.CustomEnv().reset(seed=17)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(
            first_info["goal_position"], second_info["goal_position"]
        )

    def test_different_seeds_give_different_layouts(self) -> None:
        layouts = {
            tuple(custom_env_template.CustomEnv().reset(seed=seed)[0])
            for seed in range(30)
        }
        self.assertGreater(len(layouts), 1)

    def test_the_goal_never_starts_on_the_agent(self) -> None:
        # reset() loops until they differ; otherwise the episode would be over
        # before it began.
        for seed in range(50):
            with self.subTest(seed=seed):
                _, info = custom_env_template.CustomEnv(grid_size=2).reset(seed=seed)
                self.assertFalse(
                    np.array_equal(info["agent_position"], info["goal_position"])
                )

    def test_the_observation_contains_agent_and_goal_and_lies_in_the_space(self) -> None:
        env = custom_env_template.CustomEnv()
        observation, info = env.reset(seed=3)
        self.assertTrue(env.observation_space.contains(observation))
        np.testing.assert_allclose(observation[:2], info["agent_position"])
        np.testing.assert_allclose(observation[2:], info["goal_position"])

    def test_the_info_distance_is_the_euclidean_distance_to_the_goal(self) -> None:
        env = placed_env(agent=(0, 0), goal=(3, 4))
        info = env._get_info()
        # 3-4-5 triangle.
        self.assertAlmostEqual(info["distance_to_goal"], 5.0)


class StepTests(unittest.TestCase):
    def test_each_action_moves_one_cell_in_its_documented_direction(self) -> None:
        for action, (row_delta, column_delta) in MOVES.items():
            with self.subTest(action=action):
                env = placed_env(agent=(2, 2), goal=(4, 4))
                observation, _, terminated, truncated, _ = env.step(action)
                np.testing.assert_allclose(
                    observation[:2], [2 + row_delta, 2 + column_delta]
                )
                self.assertFalse(terminated)
                self.assertFalse(truncated)

    def test_moves_are_clipped_at_every_edge(self) -> None:
        # Walking into a wall must be a no-op, not an out-of-space observation.
        cases = [((0, 0), 0, (0, 0)), ((0, 0), 2, (0, 0)), ((4, 4), 1, (4, 4)), ((4, 4), 3, (4, 4))]
        for start, action, expected in cases:
            with self.subTest(start=start, action=action):
                env = placed_env(agent=start, goal=(2, 2))
                observation, _, _, _, _ = env.step(action)
                np.testing.assert_allclose(observation[:2], expected)
                self.assertTrue(env.observation_space.contains(observation))

    def test_reaching_the_goal_pays_one_and_terminates(self) -> None:
        env = placed_env(agent=(4, 3), goal=(4, 4))
        _, reward, terminated, truncated, _ = env.step(3)
        self.assertEqual(reward, 1.0)
        self.assertTrue(terminated)
        self.assertFalse(truncated)

    def test_not_reaching_the_goal_costs_a_tenth_of_the_distance(self) -> None:
        # From (2, 2) moving up lands on (1, 2); the goal at (4, 4) is then
        # sqrt(9 + 4) = 3.6055... away, so the reward is -0.36055...
        env = placed_env(agent=(2, 2), goal=(4, 4))
        _, reward, _, _, info = env.step(0)
        self.assertAlmostEqual(reward, -0.1 * np.sqrt(13.0))
        self.assertAlmostEqual(reward, -0.1 * info["distance_to_goal"])

    def test_the_step_penalty_shrinks_as_the_agent_closes_in(self) -> None:
        far = placed_env(agent=(0, 0), goal=(4, 4)).step(1)[1]
        near = placed_env(agent=(3, 4), goal=(4, 4)).step(2)[1]
        self.assertLess(far, near)

    def test_the_raw_environment_never_truncates_on_its_own(self) -> None:
        # The template says the time limit comes from registration, not step().
        env = placed_env(agent=(0, 0), goal=(4, 4))
        for _ in range(50):
            _, _, terminated, truncated, _ = env.step(1)
            self.assertFalse(truncated)
            if terminated:
                break


class RegistrationTests(unittest.TestCase):
    def test_the_environment_is_registered_under_its_documented_id(self) -> None:
        self.assertIn("CustomEnv-v0", gym.registry)

    def test_gym_make_applies_the_hundred_step_time_limit(self) -> None:
        made = gym.make("CustomEnv-v0")
        self.assertEqual(made.spec.max_episode_steps, 100)

    def test_an_episode_that_never_reaches_the_goal_truncates_at_one_hundred(self) -> None:
        # Park the agent in the top row and keep pressing up: it can never reach
        # a goal in the bottom-right corner, so only the time limit ends this.
        made = gym.make("CustomEnv-v0")
        made.reset(seed=0)
        made.unwrapped._agent_position = np.array([0, 0])
        made.unwrapped._goal_position = np.array([4, 4])
        steps = 0
        while True:
            _, _, terminated, truncated, _ = made.step(0)
            steps += 1
            self.assertFalse(terminated)
            if truncated:
                break
            self.assertLess(steps, 100)
        self.assertEqual(steps, 100)


class EnvCheckerTests(unittest.TestCase):
    def test_the_template_passes_sb3s_checker_without_warnings(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            check_env(custom_env_template.CustomEnv(), warn=True)
        self.assertEqual([str(warning.message) for warning in caught], [])

    def test_the_checker_rejects_an_observation_outside_the_declared_space(self) -> None:
        # The other direction: without this, "check_env passed" would only prove
        # the checker ran.
        class WrongDtypeEnv(custom_env_template.CustomEnv):
            def _get_obs(self):
                return super()._get_obs().astype(np.float64)

        with self.assertRaises(AssertionError):
            check_env(WrongDtypeEnv(), warn=True)

    def test_the_validate_helper_runs_the_checker_on_the_template(self) -> None:
        # The helper is what the demo block calls; it must not print a failure.
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            custom_env_template.validate_environment()
        self.assertIn("validation passed", stream.getvalue())


class RenderTests(unittest.TestCase):
    def test_human_rendering_draws_the_agent_and_the_goal(self) -> None:
        env = placed_env(agent=(0, 0), goal=(2, 2), grid_size=3, render_mode="human")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            env.render()
        drawn = stream.getvalue()
        self.assertIn("A", drawn)
        self.assertIn("G", drawn)
        self.assertEqual(drawn.count("A"), 1)

    def test_rgb_rendering_returns_a_fifty_pixel_cell_canvas(self) -> None:
        env = placed_env(agent=(0, 0), goal=(2, 2), grid_size=3, render_mode="rgb_array")
        frame = env.render()
        self.assertEqual(frame.shape, (150, 150, 3))
        self.assertEqual(frame.dtype, np.uint8)

    def test_rendering_is_a_no_op_when_no_mode_was_requested(self) -> None:
        env = placed_env(agent=(0, 0), goal=(2, 2), render_mode=None)
        self.assertIsNone(env.render())


def train_tiny_agent(directory: Path) -> Path:
    """A two-rollout PPO on CartPole, saved to disk. Not a competent policy."""
    model = PPO(
        "MlpPolicy",
        "CartPole-v1",
        n_steps=64,
        batch_size=32,
        n_epochs=1,
        seed=0,
        verbose=0,
    )
    model.learn(total_timesteps=128)
    path = directory / "tiny_model"
    model.save(str(path))
    return path


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        cls.model_path = train_tiny_agent(Path(cls._directory.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_evaluation_returns_a_mean_and_a_non_negative_spread(self) -> None:
        mean, deviation = evaluate_agent.evaluate_agent(
            str(self.model_path), env_id="CartPole-v1", n_eval_episodes=3
        )
        self.assertIsInstance(float(mean), float)
        self.assertGreaterEqual(deviation, 0.0)
        # CartPole-v1 pays 1 per surviving step and caps at 500.
        self.assertGreater(mean, 0.0)
        self.assertLessEqual(mean, 500.0)

    def test_the_score_is_an_average_of_whole_cartpole_episodes(self) -> None:
        # CartPole pays exactly 1 per surviving step, so the mean of n episodes
        # is a multiple of 1/n. The helper takes no seed, so the value itself
        # varies between calls -- its arithmetic must not.
        mean, _ = evaluate_agent.evaluate_agent(
            str(self.model_path), env_id="CartPole-v1", n_eval_episodes=4
        )
        self.assertAlmostEqual((mean * 4) % 1.0, 0.0, places=9)
        self.assertGreaterEqual(mean, 1.0)

    def test_a_single_episode_has_no_spread(self) -> None:
        _, deviation = evaluate_agent.evaluate_agent(
            str(self.model_path), env_id="CartPole-v1", n_eval_episodes=1
        )
        self.assertEqual(deviation, 0.0)

    def test_a_missing_requested_normalisation_file_fails_loudly(self) -> None:
        with self.assertRaises(FileNotFoundError):
            evaluate_agent.evaluate_agent(
                str(self.model_path), n_eval_episodes=1,
                vec_normalize_path=str(Path(self._directory.name) / "absent.pkl"),
            )

    def test_seeded_evaluation_repeats_the_same_episode_returns(self) -> None:
        first = evaluate_agent.evaluate_agent(str(self.model_path), n_eval_episodes=4, seed=91)
        second = evaluate_agent.evaluate_agent(str(self.model_path), n_eval_episodes=4, seed=91)
        self.assertEqual(first, second)

    def test_video_is_encoded_from_rgb_frames(self) -> None:
        pytest.importorskip("moviepy")
        pytest.importorskip("pygame")
        import imageio.v2 as imageio
        with tempfile.TemporaryDirectory() as directory:
            evaluate_agent.evaluate_agent(
                str(self.model_path), n_eval_episodes=1, record_video=True,
                video_folder=directory, video_length=4,
            )
            videos = list(Path(directory).glob("*.mp4"))
            self.assertEqual(len(videos), 1)
            with imageio.get_reader(videos[0]) as reader:
                frame = reader.get_data(0)
                self.assertEqual(frame.ndim, 3)
                self.assertGreater(frame.std(), 0)
                self.assertGreaterEqual(reader.count_frames(), 2)

    def test_comparing_models_reports_one_row_per_path(self) -> None:
        # The results are keyed by path, so the same checkpoint twice collapses
        # to one entry rather than silently overwriting a different model's row.
        results = evaluate_agent.compare_models(
            [str(self.model_path), str(self.model_path)],
            env_id="CartPole-v1",
            n_eval_episodes=2,
        )
        self.assertEqual(set(results), {str(self.model_path)})
        entry = results[str(self.model_path)]
        self.assertEqual(set(entry), {"mean", "std"})
        self.assertGreater(entry["mean"], 0.0)
        self.assertLessEqual(entry["mean"], 500.0)
        self.assertGreaterEqual(entry["std"], 0.0)

    def test_loading_a_model_that_does_not_exist_fails_loudly(self) -> None:
        with self.assertRaises((FileNotFoundError, ValueError)):
            evaluate_agent.evaluate_agent(
                str(Path(self._directory.name) / "nothing"), env_id="CartPole-v1"
            )


DRIVER = """
import json, sys
sys.path.insert(0, {scripts!r})
import train_rl_agent
from stable_baselines3.common.vec_env import SubprocVecEnv

if __name__ == "__main__":
    model = train_rl_agent.train_agent(
        env_id="CartPole-v1",
        n_envs=2,
        total_timesteps=16,
        vec_env_cls=SubprocVecEnv,
        algorithm_kwargs=dict(n_steps=8, batch_size=8, n_epochs=1),
        eval_freq=10 ** 9,
        save_freq=10 ** 9,
        log_dir={logs!r},
        save_path={models!r},
    )
    print("TIMESTEPS", model.num_timesteps)
"""


class TrainingPipelineTests(unittest.TestCase):
    """One real (tiny) run of the training template, end to end."""

    def test_the_template_trains_and_saves_a_loadable_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver = root / "driver.py"
            # This run requests SubprocVecEnv, and spawn/forkserver
            # re-imports the entry module, so it can only be launched from a
            # script guarded by `if __name__ == "__main__"`.
            driver.write_text(
                textwrap.dedent(DRIVER).format(
                    scripts=str(SCRIPTS),
                    logs=str(root / "logs"),
                    models=str(root / "models"),
                )
            )
            completed = subprocess.run(
                [sys.executable, str(driver)],
                capture_output=True,
                text=True,
                timeout=900,
            )
            self.assertEqual(
                completed.returncode, 0, f"driver failed:\n{completed.stderr[-3000:]}"
            )
            self.assertIn("Training complete!", completed.stdout)

            # PPO collects n_steps per environment before it can update, so the
            # 16 requested timesteps become one full rollout.
            reported = int(completed.stdout.split("TIMESTEPS")[1].split()[0])
            self.assertGreaterEqual(reported, 16)

            saved = root / "models" / "final_model.zip"
            self.assertTrue(saved.is_file())
            self.assertTrue((root / "logs" / "eval").is_dir())
            self.assertTrue((root / "models" / "best_model").is_dir())

            # The point of saving is being able to load it again.
            mean, _ = evaluate_agent.evaluate_agent(
                str(root / "models" / "final_model"),
                env_id="CartPole-v1",
                n_eval_episodes=2,
            )
            self.assertGreater(mean, 0.0)


# `watch_agent` is deliberately untested: it exists to open a
# render_mode="human" window, which needs a display this suite does not have.


if __name__ == "__main__":
    unittest.main()
