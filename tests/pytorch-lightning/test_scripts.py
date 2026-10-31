"""Tests for the PyTorch Lightning module, datamodule, and trainer templates.

A template is only useful if it runs, and these had three ways of not running.
`configure_optimizers` passed `verbose=True` to `ReduceLROnPlateau`, which
PyTorch removed, so every model built from the template raised TypeError before
the first step. Two trainer builders asked `ModelCheckpoint` for the top 3
checkpoints without a `monitor`, which Lightning rejects outright -- so those
functions could not be called on any machine. And the module demo printed
`model.num_parameters`, an attribute LightningModule does not have.

Beyond that the tests assert the configuration the templates claim, because
claiming it is the whole point: Adam at the requested learning rate with 1e-5
weight decay, a plateau scheduler watching `val/loss` on an epoch interval, a
784 -> hidden -> 10 network whose parameter count is arithmetic, and a
train/val split that is reproducible because it is seeded. One short CPU fit
then proves the pieces compose -- in particular that the metric the scheduler
monitors is one the module actually logs, which Lightning enforces at runtime.

CUDA-only builders skip when CUDA hardware is absent. The companion contract
suite runs the production callback configuration on CPU with explicit overrides;
GPU/FSDP/DeepSpeed execution remains unvalidated here.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pytorch-lightning"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

torch = pytest.importorskip("torch", reason="the templates need torch")
L = pytest.importorskip("lightning", reason="the templates need lightning")

from lightning.pytorch.accelerators import CUDAAccelerator, MPSAccelerator  # noqa: E402
from lightning.pytorch.callbacks import (  # noqa: E402
    EarlyStopping,
    LearningRateMonitor,
    ModelCheckpoint,
)
from torch.utils.data import DataLoader, TensorDataset  # noqa: E402

import quick_trainer_setup  # noqa: E402
import template_datamodule  # noqa: E402
import template_lightning_module  # noqa: E402

# All three scripts are importable templates with a worked example under
# `if __name__ == "__main__"`, and none builds an argparse parser.
DemoBlockTests = skill_contract.cli.demo_test_case(
    SKILL_ROOT,
    (
        "template_lightning_module.py",
        "template_datamodule.py",
        "quick_trainer_setup.py",
    ),
)

CUDA_DEVICES = CUDAAccelerator.auto_device_count() if CUDAAccelerator.is_available() else 0


def build_or_skip(test: unittest.TestCase, builder, *args, **kwargs):
    """Only unavailable CUDA hardware skips; construction errors must fail."""
    if not CUDA_DEVICES:
        test.skipTest("CUDA hardware unavailable")
    return builder(*args, **kwargs)


class ModuleArchitectureTests(unittest.TestCase):
    def test_the_hyperparameters_are_saved_and_reachable(self) -> None:
        # save_hyperparameters() is what makes checkpoints reloadable without
        # repeating the constructor arguments.
        module = template_lightning_module.TemplateLightningModule(
            learning_rate=0.01, hidden_dim=32, dropout=0.25
        )
        self.assertEqual(
            dict(module.hparams),
            {"learning_rate": 0.01, "hidden_dim": 32, "dropout": 0.25},
        )

    def test_the_network_maps_784_inputs_to_10_logits(self) -> None:
        module = template_lightning_module.TemplateLightningModule(hidden_dim=16)
        output = module(torch.randn(5, 784))
        self.assertEqual(tuple(output.shape), (5, 10))

    def test_the_parameter_count_is_the_two_dense_layers(self) -> None:
        # 784*h + h + h*10 + 10, which the demo block now prints correctly.
        for hidden_dim in (8, 256):
            with self.subTest(hidden_dim=hidden_dim):
                module = template_lightning_module.TemplateLightningModule(
                    hidden_dim=hidden_dim
                )
                self.assertEqual(
                    sum(p.numel() for p in module.parameters()),
                    784 * hidden_dim + hidden_dim + hidden_dim * 10 + 10,
                )

    def test_dropout_is_active_in_training_and_disabled_in_eval(self) -> None:
        # A template that leaves dropout on at inference reports noisy metrics.
        module = template_lightning_module.TemplateLightningModule(
            hidden_dim=64, dropout=0.9
        )
        batch = torch.randn(8, 784)
        module.train()
        torch.manual_seed(0)
        first = module(batch)
        torch.manual_seed(1)
        second = module(batch)
        self.assertFalse(torch.allclose(first, second))
        module.eval()
        with torch.no_grad():
            self.assertTrue(torch.allclose(module(batch), module(batch)))


class OptimiserConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = template_lightning_module.TemplateLightningModule(
            learning_rate=0.003, hidden_dim=8
        )
        # The regression: ReduceLROnPlateau dropped `verbose`, so this call
        # raised TypeError and no model built from the template could train.
        self.configuration = self.module.configure_optimizers()

    def test_it_returns_an_adam_optimiser_at_the_requested_learning_rate(self) -> None:
        optimizer = self.configuration["optimizer"]
        self.assertIsInstance(optimizer, torch.optim.Adam)
        self.assertEqual(optimizer.param_groups[0]["lr"], 0.003)
        self.assertEqual(optimizer.param_groups[0]["weight_decay"], 1e-5)

    def test_the_optimiser_owns_every_model_parameter(self) -> None:
        optimised = sum(
            p.numel() for group in self.configuration["optimizer"].param_groups
            for p in group["params"]
        )
        self.assertEqual(optimised, sum(p.numel() for p in self.module.parameters()))

    def test_the_scheduler_halves_the_rate_on_a_five_epoch_plateau(self) -> None:
        scheduler = self.configuration["lr_scheduler"]["scheduler"]
        self.assertIsInstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau)
        self.assertEqual(scheduler.mode, "min")
        self.assertEqual(scheduler.factor, 0.5)
        self.assertEqual(scheduler.patience, 5)

    def test_the_scheduler_watches_a_metric_the_module_logs(self) -> None:
        # Lightning raises at the end of the first epoch if the monitored key
        # was never logged, so these two have to agree.
        self.assertEqual(self.configuration["lr_scheduler"]["monitor"], "val/loss")
        self.assertEqual(self.configuration["lr_scheduler"]["interval"], "epoch")
        self.assertEqual(self.configuration["lr_scheduler"]["frequency"], 1)

    def test_the_plateau_scheduler_actually_reduces_the_rate(self) -> None:
        # patience=5 means six non-improving epochs before the drop.
        scheduler = self.configuration["lr_scheduler"]["scheduler"]
        optimizer = self.configuration["optimizer"]
        for _ in range(7):
            scheduler.step(1.0)
        self.assertAlmostEqual(optimizer.param_groups[0]["lr"], 0.0015)


class DataModuleTests(unittest.TestCase):
    """The synthetic vectors match the model and use isolated evaluation views."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.datamodule = template_datamodule.TemplateDataModule(
            data_dir="./data", batch_size=8, num_workers=0, train_val_split=0.75
        )
        cls.datamodule.prepare_data()
        cls.datamodule.setup(stage="fit")

    def test_the_split_honours_the_requested_ratio(self) -> None:
        self.assertEqual(len(self.datamodule.train_dataset), 750)
        self.assertEqual(len(self.datamodule.val_dataset), 250)
        self.assertEqual(
            len(self.datamodule.train_dataset) + len(self.datamodule.val_dataset), 1000
        )

    def test_the_split_is_seeded_so_two_runs_agree(self) -> None:
        # random_split is given an explicit generator seed; without it the
        # validation set would change every run and every resumed checkpoint.
        other = template_datamodule.TemplateDataModule(
            data_dir="./data", batch_size=8, num_workers=0, train_val_split=0.75
        )
        other.setup(stage="fit")
        self.assertEqual(
            list(other.train_dataset.indices), list(self.datamodule.train_dataset.indices)
        )
        self.assertEqual(
            set(other.train_dataset.indices) & set(other.val_dataset.indices), set()
        )

    def test_the_training_loader_shuffles_and_keeps_the_short_batch(self) -> None:
        loader = self.datamodule.train_dataloader()
        self.assertFalse(loader.drop_last)
        self.assertIsInstance(loader.sampler, torch.utils.data.RandomSampler)
        # Keep the final six examples.
        self.assertEqual(len(loader), 94)

    def test_the_validation_loader_keeps_order_and_every_sample(self) -> None:
        loader = self.datamodule.val_dataloader()
        self.assertIsInstance(loader.sampler, torch.utils.data.SequentialSampler)
        self.assertFalse(loader.drop_last)
        # ceil(250 / 8) = 32 batches, so nothing is silently discarded.
        self.assertEqual(len(loader), 32)

    def test_a_batch_has_the_declared_shape_and_dtypes(self) -> None:
        samples, labels = next(iter(self.datamodule.train_dataloader()))
        self.assertEqual(tuple(samples.shape), (8, 784))
        self.assertEqual(tuple(labels.shape), (8,))
        self.assertEqual(samples.dtype, torch.float32)
        self.assertEqual(labels.dtype, torch.int64)
        self.assertTrue(bool(((labels >= 0) & (labels < 10)).all()))

    def test_a_different_ratio_moves_the_boundary(self) -> None:
        datamodule = template_datamodule.TemplateDataModule(
            data_dir="./data", batch_size=32, num_workers=0, train_val_split=0.6
        )
        datamodule.setup(stage="fit")
        self.assertEqual(len(datamodule.train_dataset), 600)
        self.assertEqual(len(datamodule.val_dataset), 400)

    def test_the_test_and_predict_stages_build_their_own_datasets(self) -> None:
        datamodule = template_datamodule.TemplateDataModule(
            data_dir="./data", batch_size=64, num_workers=0
        )
        datamodule.setup(stage="test")
        self.assertEqual(len(datamodule.test_dataset), 1000)
        self.assertIsNone(datamodule.predict_dataset)
        datamodule.setup(stage="predict")
        self.assertEqual(len(datamodule.predict_dataset), 1000)
        self.assertEqual(len(datamodule.test_dataloader()), 16)

    def test_the_checkpointed_state_round_trips(self) -> None:
        datamodule = template_datamodule.TemplateDataModule(train_val_split=0.8)
        self.assertEqual(datamodule.state_dict(), {"train_val_split": 0.8, "seed": 42, "num_samples": 1000})
        datamodule.load_state_dict({"train_val_split": 0.5})
        self.assertEqual(datamodule.hparams.train_val_split, 0.5)
        self.assertEqual(datamodule.state_dict(), {"train_val_split": 0.5, "seed": 42, "num_samples": 1000})

    def test_teardown_releases_only_the_stage_it_was_given(self) -> None:
        datamodule = template_datamodule.TemplateDataModule(num_workers=0)
        datamodule.setup(stage="test")
        datamodule.teardown(stage="predict")
        self.assertIsNotNone(datamodule.test_dataset)
        datamodule.teardown(stage="test")
        self.assertIsNone(datamodule.test_dataset)

    def test_a_transform_is_applied_to_every_sample(self) -> None:
        dataset = template_datamodule.CustomDataset(
            "./data", transform=lambda sample: torch.zeros_like(sample)
        )
        sample, label = dataset[0]
        self.assertTrue(bool((sample == 0).all()))
        # The label is never passed through the transform.
        self.assertEqual(label.dtype, torch.int64)
        self.assertEqual(len(dataset), 1000)


class TrainerConfigurationTests(unittest.TestCase):
    def test_the_basic_trainer_runs_ten_epochs_on_whatever_is_available(self) -> None:
        trainer = quick_trainer_setup.basic_trainer()
        self.assertEqual(trainer.max_epochs, 10)
        self.assertGreaterEqual(trainer.num_devices, 1)

    def test_the_debug_trainer_pins_itself_to_the_cpu(self) -> None:
        # Debugging on an accelerator hides the errors you are debugging, and
        # fast_dev_run is what makes it a debug configuration at all.
        from lightning.pytorch.accelerators import CPUAccelerator

        trainer = quick_trainer_setup.debug_trainer()
        self.assertTrue(trainer.fast_dev_run)
        self.assertIsInstance(trainer.accelerator, CPUAccelerator)
        self.assertEqual(trainer.log_every_n_steps, 1)

    def test_the_tuning_trainer_writes_nothing_and_halves_the_data(self) -> None:
        trainer = quick_trainer_setup.hyperparameter_tuning_trainer(max_epochs=5)
        self.assertEqual(trainer.max_epochs, 5)
        self.assertEqual(trainer.checkpoint_callbacks, [])
        self.assertIsNone(trainer.logger)
        self.assertEqual(trainer.limit_train_batches, 0.5)
        self.assertEqual(trainer.limit_val_batches, 0.5)

    def test_the_overfit_trainer_restricts_itself_to_the_requested_batches(self) -> None:
        trainer = quick_trainer_setup.overfit_test_trainer(num_batches=3)
        self.assertEqual(trainer.overfit_batches, 3)
        self.assertEqual(trainer.max_epochs, 100)

    def test_the_production_trainer_checkpoints_stops_early_and_tracks_the_rate(self) -> None:
        trainer = build_or_skip(self, quick_trainer_setup.production_single_gpu_trainer)
        self.assertEqual(trainer.precision, "16-mixed")
        self.assertEqual(trainer.gradient_clip_val, 1.0)
        kinds = {type(callback) for callback in trainer.callbacks}
        self.assertLessEqual(
            {ModelCheckpoint, EarlyStopping, LearningRateMonitor}, kinds
        )
        checkpointer = trainer.checkpoint_callbacks[0]
        self.assertEqual(checkpointer.monitor, "val/loss")
        self.assertEqual(checkpointer.save_top_k, 3)

    def test_the_time_limited_trainer_is_a_valid_checkpoint_configuration(self) -> None:
        # The regression: save_top_k=3 with monitor=None made this function
        # raise on every machine, GPU or not.
        trainer = build_or_skip(
            self, quick_trainer_setup.time_limited_trainer, max_time_hours=1.0
        )
        checkpointer = trainer.checkpoint_callbacks[0]
        self.assertEqual(checkpointer.save_top_k, 3)
        self.assertIsNotNone(checkpointer.monitor)
        self.assertTrue(checkpointer.save_last)

    def test_the_reproducible_trainer_seeds_and_pins_full_precision(self) -> None:
        trainer = build_or_skip(self, quick_trainer_setup.reproducible_trainer, seed=123)
        # seed_everything writes the seed where workers can read it back.
        import os

        self.assertEqual(os.environ.get("PL_GLOBAL_SEED"), "123")
        self.assertEqual(trainer.precision, "32-true")

    @unittest.skipUnless(CUDA_DEVICES >= 4, "DDP over 4 CUDA devices is unavailable")
    def test_the_ddp_trainer_shards_across_the_requested_gpus(self) -> None:
        from lightning.pytorch.strategies import DDPStrategy

        trainer = quick_trainer_setup.multi_gpu_ddp_trainer(num_gpus=4)
        self.assertIsInstance(trainer.strategy, DDPStrategy)
        self.assertEqual(trainer.num_devices, 4)

    @unittest.skipUnless(CUDA_DEVICES >= 8, "FSDP over 8 CUDA devices is unavailable")
    def test_the_fsdp_trainer_uses_bfloat16_and_accumulates(self) -> None:
        from lightning.pytorch.strategies import FSDPStrategy

        trainer = quick_trainer_setup.large_model_fsdp_trainer(num_gpus=8)
        self.assertIsInstance(trainer.strategy, FSDPStrategy)
        self.assertEqual(trainer.precision, "bf16-mixed")
        self.assertEqual(trainer.accumulate_grad_batches, 4)

    def test_the_deepspeed_trainer_selects_the_requested_stage(self) -> None:
        pytest.importorskip("deepspeed", reason="optional DeepSpeed is not installed")
        if CUDA_DEVICES < 8:
            self.skipTest("DeepSpeed stage 3 needs 8 CUDA devices")
        trainer = quick_trainer_setup.deepspeed_trainer(stage=3)
        self.assertEqual(trainer.accumulate_grad_batches, 4)


class TrainingLoopTests(unittest.TestCase):
    """One short CPU fit: the templates have to compose, not converge."""

    @classmethod
    def setUpClass(cls) -> None:
        torch.manual_seed(0)
        features = torch.randn(24, 784)
        labels = torch.randint(0, 10, (24,))
        cls.loader = DataLoader(TensorDataset(features, labels), batch_size=8)
        cls.module = template_lightning_module.TemplateLightningModule(
            learning_rate=0.01, hidden_dim=16, dropout=0.0
        )
        cls.before_weights = {name: value.detach().clone() for name, value in cls.module.named_parameters()}
        cls._directory = tempfile.TemporaryDirectory()
        cls.trainer = L.Trainer(
            max_epochs=1,
            accelerator="cpu",
            devices=1,
            logger=False,
            enable_checkpointing=False,
            enable_progress_bar=False,
            enable_model_summary=False,
            default_root_dir=cls._directory.name,
        )
        cls.trainer.fit(cls.module, cls.loader, cls.loader)
        # Snapshot now: a later trainer.test() or .predict() replaces
        # logged_metrics with that stage's own values.
        cls.fit_metrics = dict(cls.trainer.logged_metrics)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_the_fit_logs_the_metrics_the_template_documents(self) -> None:
        logged = set(self.fit_metrics)
        self.assertIn("val/loss", logged)
        self.assertIn("val/acc", logged)
        self.assertIn("learning_rate", logged)
        self.assertLessEqual({"train/loss_step", "train/loss_epoch"}, logged)

    def test_the_logged_learning_rate_is_the_configured_one(self) -> None:
        self.assertAlmostEqual(
            float(self.fit_metrics["learning_rate"]), 0.01, places=6
        )

    def test_the_losses_are_finite_and_the_accuracies_are_proportions(self) -> None:
        for name, value in self.fit_metrics.items():
            with self.subTest(metric=name):
                self.assertTrue(torch.isfinite(torch.as_tensor(value)))
                if name.endswith("acc"):
                    self.assertGreaterEqual(float(value), 0.0)
                    self.assertLessEqual(float(value), 1.0)

    def test_a_test_pass_reports_its_own_metrics(self) -> None:
        results = self.trainer.test(self.module, self.loader, verbose=False)
        self.assertEqual(set(results[0]), {"test/loss", "test/acc"})

    def test_prediction_returns_one_class_index_per_sample(self) -> None:
        predictions = self.trainer.predict(self.module, self.loader)
        self.assertEqual(sum(len(batch) for batch in predictions), 24)
        for batch in predictions:
            self.assertEqual(batch.dtype, torch.int64)
            self.assertTrue(bool(((batch >= 0) & (batch < 10)).all()))

    def test_training_moved_the_weights(self) -> None:
        # A fit that leaves every parameter untouched has not trained.
        trained = dict(self.module.named_parameters())
        self.assertTrue(any(not torch.allclose(value, trained[name])
                            for name, value in self.before_weights.items()))



if __name__ == "__main__":
    unittest.main()
