#!/usr/bin/env python3
"""
Molecular Solubility Prediction Script

This script trains a model to predict aqueous solubility from SMILES strings
using the Delaney (ESOL) dataset as an example. Can be adapted for custom datasets.

Usage:
    python predict_solubility.py --data custom_data.csv --smiles-col smiles --target-col solubility
    python predict_solubility.py  # Uses Delaney dataset by default
"""

import argparse
import deepchem as dc
import numpy as np
import sys
from _common import load_csv, validate_splits, evaluate_splits


def train_solubility_model(data_path=None, smiles_col='smiles', target_col='measured log solubility in mols per litre', n_epochs=50):
    """
    Train a solubility prediction model.

    Args:
        data_path: Path to CSV file with SMILES and solubility data. If None, uses Delaney dataset.
        smiles_col: Name of column containing SMILES strings
        target_col: Name of column containing solubility values

    Returns:
        Trained model, test dataset, and transformers
    """
    print("=" * 60)
    print("DeepChem Solubility Prediction")
    print("=" * 60)

    # Load data
    if data_path is None:
        print("\nUsing Delaney (ESOL) benchmark dataset...")
        tasks, datasets, transformers = dc.molnet.load_delaney(
            featurizer=dc.feat.CircularFingerprint(radius=2, size=2048),
            splitter='scaffold'
        )
        train, valid, test = datasets
    else:
        print(f"\nLoading custom data from {data_path}...")
        featurizer = dc.feat.CircularFingerprint(radius=2, size=2048)
        dataset = load_csv(data_path, [target_col], smiles_col, featurizer)
        if not np.all(dataset.w > 0):
            raise ValueError('Solubility training requires a measured target for every row')

        # Split data
        print("Splitting data with scaffold splitter...")
        splitter = dc.splits.ScaffoldSplitter()
        train, valid, test = splitter.train_valid_test_split(
            dataset,
            frac_train=0.8,
            frac_valid=0.1,
            frac_test=0.1
        )

        # Normalize data
        print("Normalizing targets using training statistics...")
        transformers = [
            dc.trans.NormalizationTransformer(
                transform_y=True,
                dataset=train
            )
        ]
        for transformer in transformers:
            train = transformer.transform(train)
            valid = transformer.transform(valid)
            test = transformer.transform(test)

        tasks = [target_col]

    print(f"\nDataset sizes:")
    print(f"  Training:   {len(train)} molecules")
    print(f"  Validation: {len(valid)} molecules")
    print(f"  Test:       {len(test)} molecules")

    validate_splits((train, valid, test), "regression", len(tasks))

    # Create model
    print("\nCreating multitask regressor...")
    model = dc.models.MultitaskRegressor(
        n_tasks=len(tasks),
        n_features=2048,  # ECFP fingerprint size
        layer_sizes=[128, 64],
        dropouts=0.25,
        learning_rate=0.001,
        device="cpu",
        batch_size=50
    )

    # Train model
    print("\nTraining model...")
    model.fit(train, nb_epoch=n_epochs)
    print("Training complete!")

    # Evaluate model
    print("\n" + "=" * 60)
    print("Model Evaluation")
    print("=" * 60)

    evaluate_splits(model, (train, valid, test), "regression", transformers)

    return model, test, transformers


def predict_new_molecules(model, smiles_list, transformers=None):
    """
    Predict solubility for new molecules.

    Args:
        model: Trained DeepChem model
        smiles_list: List of SMILES strings
        transformers: List of data transformers to apply

    Returns:
        Array of predictions
    """
    print("\n" + "=" * 60)
    print("Predicting New Molecules")
    print("=" * 60)

    # Featurize new molecules
    featurizer = dc.feat.CircularFingerprint(radius=2, size=2048)
    features = featurizer.featurize(smiles_list)

    if any(np.asarray(feature).shape != (2048,) for feature in features):
        raise ValueError('Cannot predict invalid or unsupported SMILES')

    # Create dataset
    new_dataset = dc.data.NumpyDataset(X=features)

    # Both training paths normalize with transform_y=True, so the model learned
    # in z-scored target space. Hand the transformers to predict() so it
    # untransforms the output back to target units -- transforming the dataset
    # instead would do nothing (these transformers touch y, not X, and a
    # prediction dataset has no y) and leave the printed numbers z-scored.
    predictions = np.asarray(model.predict(new_dataset, transformers=transformers or [])).reshape(len(smiles_list), 1)

    # Display results
    print("\nPredictions:")
    for smiles, pred in zip(smiles_list, predictions):
        print(f"  {smiles:30s} -> {pred[0]:.3f} target units")

    return predictions


def main():
    parser = argparse.ArgumentParser(
        description='Train a molecular solubility prediction model'
    )
    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='Path to CSV file with molecular data'
    )
    parser.add_argument(
        '--smiles-col',
        type=str,
        default='smiles',
        help='Name of column containing SMILES strings'
    )
    parser.add_argument(
        '--target-col',
        type=str,
        default='solubility',
        help='Name of column containing target values'
    )
    parser.add_argument(
        '--predict',
        nargs='+',
        default=None,
        help='SMILES strings to predict after training'
    )

    parser.add_argument('--epochs', type=int, default=50)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('--epochs must be positive')

    # Train model
    try:
        model, test_set, transformers = train_solubility_model(
            data_path=args.data,
            smiles_col=args.smiles_col,
            target_col=args.target_col,
            n_epochs=args.epochs
        )
    except Exception as e:
        print(f"\nError during training: {e}", file=sys.stderr)
        return 1

    # Make predictions on new molecules if provided
    if args.predict:
        try:
            predict_new_molecules(model, args.predict, transformers)
        except Exception as e:
            print(f"\nError during prediction: {e}", file=sys.stderr)
            return 1
    else:
        # Example predictions
        example_smiles = [
            'CCO',                    # Ethanol
            'CC(=O)O',                # Acetic acid
            'c1ccccc1',               # Benzene
            'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',  # Caffeine
        ]
        predict_new_molecules(model, example_smiles, transformers)

    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
