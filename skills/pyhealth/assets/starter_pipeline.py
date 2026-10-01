"""PyHealth 2.0.2 CPU starter: --demo or --root <MIMIC-III directory/URL>.

The demo has invented codes and labels: it checks plumbing, not clinical validity.
Real-data mode uses the upstream next-visit mortality task, not early warning.
"""

import argparse
from pathlib import Path


def build_samples(root=None, cache_dir=None, dev=False):
    from pyhealth.datasets import MIMIC3Dataset, create_sample_dataset
    from pyhealth.tasks import MortalityPredictionMIMIC3

    task = MortalityPredictionMIMIC3()
    if root is not None:
        base = MIMIC3Dataset(
            root=root,
            tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
            cache_dir=cache_dir,
            dev=dev,
            num_workers=1,
        )
        return base.set_task(task)
    records = [
        {
            "patient_id": f"demo-{i}",
            "visit_id": f"demo-{i}-{j}",
            "conditions": ["invented-condition", f"group-{i % 3}"],
            "procedures": ["invented-procedure"],
            "drugs": ["invented-drug"],
            "mortality": (i + j) % 2,
        }
        for i in range(60)
        for j in range(2)
    ]
    return create_sample_dataset(
        records, input_schema=task.input_schema, output_schema=task.output_schema
    )


def train_and_evaluate(samples, output_path, epochs=1, seed=42):
    import random
    import numpy as np
    import torch
    from pyhealth.datasets import get_dataloader, split_by_patient
    from pyhealth.models import Transformer
    from pyhealth.trainer import Trainer

    if epochs < 1:
        raise ValueError("epochs must be positive")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    parts = split_by_patient(samples, [0.6, 0.2, 0.2], seed=seed)
    patient_sets = [set(part.patient_to_index) for part in parts]
    for i in range(3):
        for j in range(i):
            if patient_sets[i] & patient_sets[j]:
                raise ValueError("Patient overlap between partitions")
    for name, part in zip(("train", "validation", "test"), parts):
        if len(part) == 0:
            raise ValueError(f"Empty {name} partition")
        labels = {int(part[i]["mortality"].item()) for i in range(len(part))}
        if labels != {0, 1}:
            raise ValueError(f"{name} needs both binary classes for ROC AUC")
    loaders = [
        get_dataloader(part, batch_size=16, shuffle=(i == 0))
        for i, part in enumerate(parts)
    ]
    model = Transformer(dataset=parts[0], embedding_dim=16, dropout=0.0)
    trainer = Trainer(
        model=model,
        metrics=["pr_auc", "roc_auc", "f1"],
        device="cpu",
        output_path=str(output_path),
        exp_name="starter",
    )
    trainer.train(
        train_dataloader=loaders[0],
        val_dataloader=loaders[1],
        epochs=epochs,
        monitor="pr_auc",
        monitor_criterion="max",
        patience=5,
    )
    scores = trainer.evaluate(loaders[2])
    return trainer, scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="Use invented in-memory data")
    source.add_argument("--root", help="Local or public MIMIC-III root")
    parser.add_argument("--cache-dir", type=Path, default=Path("cache/mimic3"))
    parser.add_argument("--output", type=Path, default=Path("output/pyhealth"))
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--dev", action="store_true", help="Limit raw data to 1000 patients")
    args = parser.parse_args()
    samples = build_samples(args.root, args.cache_dir, args.dev)
    _, scores = train_and_evaluate(samples, args.output, epochs=args.epochs)
    print("[OK]", scores)


if __name__ == "__main__":
    main()
