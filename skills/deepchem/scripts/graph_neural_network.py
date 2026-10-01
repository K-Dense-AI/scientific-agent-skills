#!/usr/bin/env python3
"""
Graph Neural Network Training Script

This script demonstrates training Graph Convolutional Networks (GCNs) and other
graph-based models for molecular property prediction.

Usage:
    python graph_neural_network.py --dataset tox21 --model gcn
    python graph_neural_network.py --dataset bbbp --model attentivefp
    python graph_neural_network.py --data custom.csv --task-type regression
"""

import argparse
import deepchem as dc
import sys
from _common import load_csv, validate_splits, evaluate_splits


AVAILABLE_MODELS = {
    'gcn': 'Graph Convolutional Network',
    'gat': 'Graph Attention Network',
    'attentivefp': 'Attentive Fingerprint',
    'mpnn': 'Message Passing Neural Network',
    'dmpnn': 'Directed Message Passing Neural Network'
}

MOLNET_DATASETS = {
    'tox21': ('classification', 12),
    'bbbp': ('classification', 1),
    'bace': ('classification', 1),
    'hiv': ('classification', 1),
    'delaney': ('regression', 1),
    'freesolv': ('regression', 1),
    'lipo': ('regression', 1)
}

# MoleculeNet loader names that are not simply load_<dataset>. BACE ships as
# separate classification and regression loaders, so dc.molnet.load_bace does
# not exist; the entry above treats it as a classification benchmark.
MOLNET_LOADERS = {
    'bace': 'load_bace_classification'
}


def molnet_loader(dataset_name):
    """Return the dc.molnet loader function for a MoleculeNet dataset name."""
    return getattr(dc.molnet, MOLNET_LOADERS.get(dataset_name, f'load_{dataset_name}'))


def create_model(model_type, n_tasks, mode='classification'):
    """
    Create a graph neural network model.

    Args:
        model_type: Type of model ('gcn', 'gat', 'attentivefp', etc.)
        n_tasks: Number of prediction tasks
        mode: 'classification' or 'regression'

    Returns:
        DeepChem model
    """
    if model_type == 'gcn':
        return dc.models.GCNModel(
            n_tasks=n_tasks,
            mode=mode,
            device="cpu",
            batch_size=128,
            learning_rate=0.001,
            dropout=0.0
        )
    elif model_type == 'gat':
        return dc.models.GATModel(
            n_tasks=n_tasks,
            mode=mode,
            device="cpu",
            batch_size=128,
            learning_rate=0.001
        )
    elif model_type == 'attentivefp':
        return dc.models.AttentiveFPModel(
            n_tasks=n_tasks,
            mode=mode,
            device="cpu",
            batch_size=128,
            learning_rate=0.001
        )
    elif model_type == 'mpnn':
        from deepchem.models.torch_models import MPNNModel
        return MPNNModel(
            n_tasks=n_tasks,
            mode=mode,
            device="cpu",
            batch_size=128,
            learning_rate=0.001
        )
    elif model_type == 'dmpnn':
        return dc.models.DMPNNModel(
            n_classes=2,
            n_tasks=n_tasks,
            mode=mode,
            device="cpu",
            batch_size=128,
            learning_rate=0.001
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def create_featurizer(model_type):
    """Match the released model's representation, including required bonds."""
    if model_type == 'dmpnn':
        return dc.feat.DMPNNFeaturizer()
    if model_type in AVAILABLE_MODELS:
        return dc.feat.MolGraphConvFeaturizer(
            use_edges=model_type in ('attentivefp', 'mpnn'))
    raise ValueError(f"Unknown model type: {model_type}")


def train_on_molnet(dataset_name, model_type, n_epochs=50):
    """
    Train a graph neural network on a MoleculeNet benchmark dataset.

    Args:
        dataset_name: Name of MoleculeNet dataset
        model_type: Type of model to train
        n_epochs: Number of training epochs

    Returns:
        Trained model and test scores
    """
    print("=" * 70)
    print(f"Training {AVAILABLE_MODELS[model_type]} on {dataset_name.upper()}")
    print("=" * 70)

    # Get dataset info
    task_type, n_tasks_default = MOLNET_DATASETS[dataset_name]

    # Load dataset with graph featurization
    print(f"\nLoading {dataset_name} dataset with {model_type} features...")
    load_func = molnet_loader(dataset_name)
    tasks, datasets, transformers = load_func(
        featurizer=create_featurizer(model_type),
        splitter='scaffold'
    )
    train, valid, test = datasets

    n_tasks = len(tasks)
    print(f"\nDataset Information:")
    print(f"  Task type: {task_type}")
    print(f"  Number of tasks: {n_tasks}")
    print(f"  Training samples: {len(train)}")
    print(f"  Validation samples: {len(valid)}")
    print(f"  Test samples: {len(test)}")

    validate_splits((train, valid, test), task_type, len(tasks))

    # Create model
    print(f"\nCreating {AVAILABLE_MODELS[model_type]} model...")
    model = create_model(model_type, n_tasks, mode=task_type)

    # Train
    print(f"\nTraining for {n_epochs} epochs...")
    model.fit(train, nb_epoch=n_epochs)
    print("Training complete!")

    # Evaluate
    print("\n" + "=" * 70)
    print("Model Evaluation")
    print("=" * 70)

    results = evaluate_splits(model, (train, valid, test), task_type, transformers)

    return model, results


def train_on_custom_data(data_path, model_type, task_type, target_cols, smiles_col='smiles', n_epochs=50):
    """
    Train a graph neural network on custom CSV data.

    Args:
        data_path: Path to CSV file
        model_type: Type of model to train
        task_type: 'classification' or 'regression'
        target_cols: List of target column names
        smiles_col: Name of SMILES column
        n_epochs: Number of training epochs

    Returns:
        Trained model and test dataset
    """
    print("=" * 70)
    print(f"Training {AVAILABLE_MODELS[model_type]} on Custom Data")
    print("=" * 70)

    # Load and featurize data
    print(f"\nLoading data from {data_path}...")
    featurizer = create_featurizer(model_type)
    dataset = load_csv(data_path, target_cols, smiles_col, featurizer)

    print(f"Loaded {len(dataset)} molecules")

    # Split data
    print("\nSplitting data with scaffold splitter...")
    splitter = dc.splits.ScaffoldSplitter()
    train, valid, test = splitter.train_valid_test_split(
        dataset,
        frac_train=0.8,
        frac_valid=0.1,
        frac_test=0.1
    )

    print(f"  Training: {len(train)}")
    print(f"  Validation: {len(valid)}")
    print(f"  Test: {len(test)}")

    # Create model
    print(f"\nCreating {AVAILABLE_MODELS[model_type]} model...")
    n_tasks = len(target_cols)
    validate_splits((train, valid, test), task_type, n_tasks)
    model = create_model(model_type, n_tasks, mode=task_type)

    # Train
    print(f"\nTraining for {n_epochs} epochs...")
    model.fit(train, nb_epoch=n_epochs)
    print("Training complete!")

    # Evaluate
    print("\n" + "=" * 70)
    print("Model Evaluation")
    print("=" * 70)

    evaluate_splits(model, (train, valid, test), task_type)

    return model, test


def main():
    parser = argparse.ArgumentParser(
        description='Train graph neural networks for molecular property prediction'
    )
    parser.add_argument(
        '--model',
        type=str,
        choices=list(AVAILABLE_MODELS.keys()),
        default='gcn',
        help='Type of graph neural network model'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        choices=list(MOLNET_DATASETS.keys()),
        default=None,
        help='MoleculeNet dataset to use'
    )
    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='Path to custom CSV file'
    )
    parser.add_argument(
        '--task-type',
        type=str,
        choices=['classification', 'regression'],
        default='classification',
        help='Type of prediction task (for custom data)'
    )
    parser.add_argument(
        '--targets',
        nargs='+',
        default=['target'],
        help='Names of target columns (for custom data)'
    )
    parser.add_argument(
        '--smiles-col',
        type=str,
        default='smiles',
        help='Name of SMILES column'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=50,
        help='Number of training epochs'
    )

    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('--epochs must be positive')

    # Validate arguments
    if args.dataset is None and args.data is None:
        print("Error: Must specify either --dataset (MoleculeNet) or --data (custom CSV)",
              file=sys.stderr)
        return 1

    if args.dataset and args.data:
        print("Error: Cannot specify both --dataset and --data",
              file=sys.stderr)
        return 1

    # Train model
    try:
        if args.dataset:
            model, results = train_on_molnet(
                args.dataset,
                args.model,
                n_epochs=args.epochs
            )
        else:
            model, test_set = train_on_custom_data(
                args.data,
                args.model,
                args.task_type,
                args.targets,
                smiles_col=args.smiles_col,
                n_epochs=args.epochs
            )

        print("\n" + "=" * 70)
        print("Training Complete!")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
