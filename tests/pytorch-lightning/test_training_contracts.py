"""Real tiny CPU runs for composition, metric weighting, hooks and resume."""
from pathlib import Path
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pytorch-lightning"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
torch = pytest.importorskip("torch")
L = pytest.importorskip("lightning")
from lightning.pytorch.callbacks import Callback, EarlyStopping, ModelCheckpoint, Timer
from lightning.pytorch.loggers import CSVLogger
from torch.utils.data import DataLoader, DistributedSampler, TensorDataset
from template_datamodule import TemplateDataModule, CustomDataset
from template_lightning_module import TemplateLightningModule
from quick_trainer_setup import production_single_gpu_trainer, deepspeed_trainer


def cpu_trainer(tmp_path, **kwargs):
    defaults = dict(accelerator="cpu", devices=1, max_epochs=1, logger=False,
                    enable_checkpointing=False, enable_progress_bar=False,
                    enable_model_summary=False, default_root_dir=tmp_path)
    return L.Trainer(**(defaults | kwargs))


def test_data_are_repeatable_and_transform_views_do_not_leak():
    class Augmented(TemplateDataModule):
        def _get_train_transforms(self):
            return torch.zeros_like

    dm = Augmented(num_samples=23, batch_size=8)
    dm.setup("validate")
    assert len(dm.val_dataset) == 5
    assert dm.train_dataset.dataset is not dm.val_dataset.dataset
    assert torch.equal(dm.train_dataset.dataset.data, dm.val_dataset.dataset.data)
    assert not dm.train_dataset[0][0].any()
    assert dm.val_dataset[0][0].any()
    reference = CustomDataset("unused", num_samples=23)
    idx = dm.val_dataset.indices[0]
    assert torch.equal(dm.val_dataset[0][0], reference[idx][0])
    dm.setup("test")
    assert not torch.equal(reference.data, dm.test_dataset.data)


def test_state_restoration_after_setup_rebuilds_splits_and_samples():
    original = TemplateDataModule(seed=7, num_samples=31, train_val_split=0.7)
    original.setup("fit")
    restored = TemplateDataModule(seed=99, num_samples=20, train_val_split=0.5)
    restored.setup("fit")
    restored.load_state_dict(original.state_dict())
    assert restored.val_dataset.indices == original.val_dataset.indices
    assert torch.equal(restored.val_dataset.dataset.data, original.val_dataset.dataset.data)


@pytest.mark.parametrize("kwargs", [{"train_val_split": 0}, {"train_val_split": 1},
                                     {"num_samples": 1}, {"batch_size": 0},
                                     {"num_workers": -1}])
def test_invalid_data_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        TemplateDataModule(**kwargs)


def test_standalone_validate_then_predict_uses_matching_template(tmp_path):
    model = TemplateLightningModule(hidden_dim=4)
    dm = TemplateDataModule(num_samples=23, batch_size=7)
    trainer = cpu_trainer(tmp_path)
    values = trainer.validate(model, datamodule=dm, verbose=False)
    assert set(values[0]) == {"val/loss", "val/acc"}
    predictions = trainer.predict(model, datamodule=dm)
    assert sum(len(x) for x in predictions) == 23
    assert dm.val_dataset is None and dm.predict_dataset is None


def test_scalar_metrics_weight_uneven_batches_and_disable_dropout(tmp_path):
    model = TemplateLightningModule(hidden_dim=4, dropout=0.9)
    model.model = torch.nn.Identity()
    logits = torch.zeros(11, 10)
    logits[:8, 0] = 10
    logits[8:, 1] = 10
    labels = torch.zeros(11, dtype=torch.long)
    loader = DataLoader(TensorDataset(logits, labels), batch_size=8)
    trainer = cpu_trainer(tmp_path)
    val = trainer.validate(model, loader, verbose=False)[0]
    test = trainer.test(model, loader, verbose=False)[0]
    assert val["val/acc"] == pytest.approx(8 / 11)
    assert test["test/acc"] == pytest.approx(8 / 11)
    expected_loss = torch.nn.functional.cross_entropy(logits, labels).item()
    assert val["val/loss"] == pytest.approx(expected_loss, rel=1e-6)
    assert test["test/loss"] == pytest.approx(expected_loss, rel=1e-6)


class EventCounter(Callback):
    def __init__(self):
        self.count = 0
        self.loaded_count = None
        self.events = []
        self.restored_step = None
        self.restored_moments = False
        self.restored_scheduler = None
        self.prediction_batches = 0

    def state_dict(self):
        return {"count": self.count}

    def load_state_dict(self, state_dict):
        self.loaded_count = self.count = state_dict["count"]

    def on_fit_start(self, trainer, pl_module):
        self.events.append("fit")

    def on_train_start(self, trainer, pl_module):
        self.restored_step = trainer.global_step
        self.restored_moments = bool(trainer.optimizers[0].state)
        self.restored_scheduler = trainer.lr_scheduler_configs[0].scheduler.state_dict()

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        self.count += 1

    def on_validation_batch_end(self, trainer, pl_module, outputs, batch, batch_idx, dataloader_idx=0):
        assert not pl_module.training
        assert not torch.is_grad_enabled()
        self.events.append("sanity" if trainer.sanity_checking else "validation")

    def on_predict_batch_end(self, trainer, pl_module, outputs, batch, batch_idx, dataloader_idx=0):
        self.prediction_batches += 1


def test_full_cpu_checkpoint_resume_restores_state_and_fresh_split(tmp_path):
    L.seed_everything(19, workers=True)
    dm = TemplateDataModule(seed=17, num_samples=23, train_val_split=0.7, batch_size=8)
    model = TemplateLightningModule(hidden_dim=4, dropout=0.0)
    callback = EventCounter()
    checkpoint = ModelCheckpoint(dirpath=tmp_path / "ckpts", monitor="val/loss", save_last=True)
    trainer = cpu_trainer(tmp_path, callbacks=[callback, checkpoint], enable_checkpointing=True)
    trainer.fit(model, datamodule=dm)
    assert callback.events[0] == "fit"
    assert "sanity" in callback.events and "validation" in callback.events
    path = checkpoint.last_model_path
    saved = torch.load(path, map_location="cpu", weights_only=True)
    assert saved["global_step"] == 2
    assert saved["optimizer_states"][0]["state"]
    assert saved["lr_schedulers"]
    loaded = TemplateLightningModule.load_from_checkpoint(path, weights_only=True)
    assert loaded.hparams.hidden_dim == 4
    for name, value in model.state_dict().items():
        torch.testing.assert_close(value, loaded.state_dict()[name])

    dm2 = TemplateDataModule(seed=999, num_samples=40, train_val_split=0.5, batch_size=8)
    callback2 = EventCounter()
    model2 = TemplateLightningModule(hidden_dim=4, dropout=0.0)
    checkpoint2 = ModelCheckpoint(dirpath=tmp_path / "ckpts", monitor="val/loss", save_last=True)
    trainer2 = cpu_trainer(tmp_path, max_epochs=2, callbacks=[callback2, checkpoint2], enable_checkpointing=True)
    trainer2.fit(model2, datamodule=dm2, ckpt_path=path, weights_only=True)
    assert callback2.loaded_count == 2
    assert callback2.count == 4
    assert callback2.restored_step == 2
    assert callback2.restored_scheduler == saved["lr_schedulers"][0]
    assert callback2.restored_moments
    assert trainer2.global_step == 4
    assert dm2.state_dict() == dm.state_dict()
    trainer2.predict(model2, datamodule=dm2)
    assert callback2.prediction_batches == 3


def test_cpu_production_helper_logs_locally_and_monitors_real_metric(tmp_path):
    trainer = production_single_gpu_trainer(
        max_epochs=1, accelerator="cpu", precision="32-true",
        log_dir=str(tmp_path / "logs"), checkpoint_dir=str(tmp_path / "checkpoints"),
    )
    assert isinstance(trainer.logger, CSVLogger)
    model = TemplateLightningModule(hidden_dim=4)
    trainer.fit(model, datamodule=TemplateDataModule(num_samples=19, batch_size=8))
    checkpoint = trainer.checkpoint_callback
    assert Path(checkpoint.best_model_path).exists()
    assert checkpoint.monitor == "val/loss"
    assert list((tmp_path / "logs").rglob("metrics.csv"))
    assert Path(checkpoint.best_model_path).parent == tmp_path / "checkpoints"


def test_early_stopping_counts_validation_checks(tmp_path):
    class ConstantValidation(TemplateLightningModule):
        def validation_step(self, batch, batch_idx):
            self.log("val/loss", 1.0, batch_size=len(batch[1]))
    early = EarlyStopping(monitor="val/loss", patience=1)
    trainer = cpu_trainer(tmp_path, max_epochs=5, val_check_interval=0.5,
                          num_sanity_val_steps=0, callbacks=[early])
    trainer.fit(ConstantValidation(hidden_dim=4), datamodule=TemplateDataModule(num_samples=40, batch_size=8))
    assert trainer.global_step == 4  # Two checks within the first training epoch.
    assert early.wait_count == 1


def test_distributed_sampler_padding_duplicates_real_indices():
    dataset = list(range(5))
    shards = [list(DistributedSampler(dataset, num_replicas=2, rank=rank,
                                     shuffle=False)) for rank in range(2)]
    assert len(shards[0]) == len(shards[1]) == 3
    combined = shards[0] + shards[1]
    assert len(combined) == 6 and len(set(combined)) == 5


def test_timer_rejects_batch_interval_and_deepspeed_rejects_unknown_stage():
    with pytest.raises(Exception, match="interval"):
        Timer(duration={"seconds": 1}, interval="batch")
    with pytest.raises(ValueError, match="stage"):
        deepspeed_trainer(stage=4)


def test_logged_metric_object_resets_between_validation_calls(tmp_path):
    from torchmetrics.classification import MulticlassAccuracy

    class MetricModel(L.LightningModule):
        def __init__(self):
            super().__init__()
            self.accuracy = MulticlassAccuracy(num_classes=2, average="micro")

        def validation_step(self, batch, batch_idx):
            self.accuracy.update(batch[0], batch[1])
            self.log("accuracy", self.accuracy, on_step=False, on_epoch=True)

    model = MetricModel()
    trainer = cpu_trainer(tmp_path)
    labels = torch.zeros(5, dtype=torch.long)
    correct = DataLoader(TensorDataset(torch.zeros_like(labels), labels), batch_size=3)
    wrong = DataLoader(TensorDataset(torch.ones_like(labels), labels), batch_size=3)
    assert trainer.validate(model, correct, verbose=False)[0]["accuracy"] == 1.0
    assert trainer.validate(model, wrong, verbose=False)[0]["accuracy"] == 0.0


def test_derivative_evaluation_needs_inference_mode_disabled(tmp_path):
    class DerivativeModel(L.LightningModule):
        def validation_step(self, batch, batch_idx):
            with torch.enable_grad():
                x = batch[0].clone().requires_grad_(True)
                derivative = torch.autograd.grad(x.square().sum(), x)[0]
                torch.testing.assert_close(derivative, 2 * x)
                self.log("derivative_mean", derivative.mean(), batch_size=len(x))

    trainer = cpu_trainer(tmp_path, inference_mode=False)
    data = DataLoader(TensorDataset(torch.arange(5.)), batch_size=3)
    assert trainer.validate(DerivativeModel(), data, verbose=False)[0]["derivative_mean"] == 4.0
