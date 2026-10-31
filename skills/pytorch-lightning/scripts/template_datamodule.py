"""Small, deterministic DataModule example; replace synthetic data with real splits.

The 784-feature samples match TemplateLightningModule. Random labels are only a
loop smoke test, never evidence of scientific accuracy. No files are downloaded.
"""

import lightning as L
import torch
from torch.utils.data import DataLoader, Dataset, Subset


class CustomDataset(Dataset):
    """Synthetic labelled vectors with an explicit seed and optional transform."""

    def __init__(self, data_path, transform=None, *, seed=42, num_samples=1000):
        self.data_path = data_path  # Reserved for a real dataset implementation.
        self.transform = transform
        generator = torch.Generator().manual_seed(seed)
        self.data = torch.randn(num_samples, 784, generator=generator)
        self.labels = torch.randint(0, 10, (num_samples,), generator=generator)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sample = self.data[idx]
        if self.transform is not None:
            sample = self.transform(sample)
        return sample, self.labels[idx]


class TemplateDataModule(L.LightningDataModule):
    """Seeded train/validation split with separate evaluation transforms.

    For real data, preserve sample IDs and preprocessing provenance in the
    checkpoint; use group/time splits where observations are correlated.
    """

    def __init__(
        self,
        data_dir: str = "./data",
        batch_size: int = 32,
        num_workers: int = 0,
        train_val_split: float = 0.8,
        pin_memory: bool = False,
        seed: int = 42,
        num_samples: int = 1000,
    ):
        super().__init__()
        if not 0 < train_val_split < 1:
            raise ValueError("train_val_split must be between 0 and 1")
        if num_samples < 2 or not 0 < int(train_val_split * num_samples) < num_samples:
            raise ValueError("Both train and validation splits must be nonempty")
        if batch_size < 1 or num_workers < 0:
            raise ValueError("batch_size must be positive and num_workers nonnegative")
        self.save_hyperparameters()
        self.train_dataset = self.val_dataset = None
        self.test_dataset = self.predict_dataset = None

    def prepare_data(self):
        """Download/cache here, if needed; do not assign distributed state.

        Lightning calls this on local rank zero on each node by default. Set
        prepare_data_per_node=False for one global writer with shared storage.
        This synthetic example has no preparation or network access.
        """

    def _dataset(self, transform, seed_offset=0):
        return CustomDataset(
            self.hparams.data_dir,
            transform=transform,
            seed=self.hparams.seed + seed_offset,
            num_samples=self.hparams.num_samples,
        )

    def setup(self, stage=None):
        """Build per-process state, including standalone validate()."""
        if stage not in (None, "fit", "validate", "test", "predict"):
            raise ValueError(f"Unsupported stage: {stage}")
        if stage in (None, "fit", "validate"):
            indices = torch.randperm(
                self.hparams.num_samples,
                generator=torch.Generator().manual_seed(self.hparams.seed),
            ).tolist()
            boundary = int(self.hparams.train_val_split * len(indices))
            # Two dataset views have identical underlying samples but different
            # transforms; mutating one Subset's dataset must not augment validation.
            self.train_dataset = Subset(
                self._dataset(self._get_train_transforms()), indices[:boundary]
            )
            self.val_dataset = Subset(
                self._dataset(self._get_test_transforms()), indices[boundary:]
            )
        if stage in (None, "test"):
            self.test_dataset = self._dataset(self._get_test_transforms(), seed_offset=1)
        if stage in (None, "predict"):
            self.predict_dataset = self._dataset(self._get_test_transforms(), seed_offset=2)

    def _get_train_transforms(self):
        """Override with training-only augmentation, fit on training data only."""
        return None

    def _get_test_transforms(self):
        """Override with deterministic transforms using training-fitted parameters."""
        return None

    def _loader(self, dataset, *, training=False):
        if dataset is None:
            raise RuntimeError("Call setup() for this stage before requesting a DataLoader")
        return DataLoader(
            dataset,
            batch_size=self.hparams.batch_size,
            shuffle=training,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            persistent_workers=self.hparams.num_workers > 0,
            drop_last=False,
        )

    def train_dataloader(self):
        return self._loader(self.train_dataset, training=True)

    def val_dataloader(self):
        return self._loader(self.val_dataset)

    def test_dataloader(self):
        return self._loader(self.test_dataset)

    def predict_dataloader(self):
        return self._loader(self.predict_dataset)

    def state_dict(self):
        """Enough provenance to regenerate this synthetic dataset and its split."""
        return {
            key: self.hparams[key]
            for key in ("train_val_split", "seed", "num_samples")
        }

    def load_state_dict(self, state_dict):
        """Lightning restores DataModule state after setup; rebuild existing views."""
        stages = []
        if self.train_dataset is not None or self.val_dataset is not None:
            stages.append("fit")
        if self.test_dataset is not None:
            stages.append("test")
        if self.predict_dataset is not None:
            stages.append("predict")
        for key in ("train_val_split", "seed", "num_samples"):
            if key in state_dict:  # Accept older checkpoints containing just ratio.
                self.hparams[key] = state_dict[key]
        if not 0 < int(self.hparams.train_val_split * self.hparams.num_samples) < self.hparams.num_samples:
            raise ValueError("Restored split must have nonempty train and validation sets")
        for stage in stages:
            self.setup(stage)

    def teardown(self, stage=None):
        if stage in (None, "fit", "validate"):
            self.train_dataset = self.val_dataset = None
        if stage in (None, "test"):
            self.test_dataset = None
        if stage in (None, "predict"):
            self.predict_dataset = None


if __name__ == "__main__":
    dm = TemplateDataModule(batch_size=64)
    dm.prepare_data()
    dm.setup("fit")
    print(f"[OK] Train/validation samples: {len(dm.train_dataset)}/{len(dm.val_dataset)}")
    print(f"[OK] Batch shape: {tuple(next(iter(dm.train_dataloader()))[0].shape)}")
