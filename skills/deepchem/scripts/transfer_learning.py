#!/usr/bin/env python3
"""Fine-tune explicit Hugging Face or compatible DeepChem GROVER checkpoints.

HF examples support one fully observed, unweighted binary or regression task.
GROVER requires a local DeepChem component checkpoint and matching architecture.
No pretrained weights are implied by a model output directory.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import deepchem as dc
import numpy as np
from _common import load_csv, validate_splits, evaluate_splits
from graph_neural_network import MOLNET_DATASETS, molnet_loader

PRETRAINED_MODELS = {
    'chemberta': {
        'name': 'ChemBERTa',
        'description': 'RoBERTa pretrained on 100k ZINC SMILES (model card)',
        'model_id': 'seyonec/ChemBERTa-zinc-base-v1',
    },
    'grover': {
        'name': 'GROVER',
        'description': 'Transfer a matching DeepChem GROVER embedding checkpoint',
        'model_id': None,
    },
    'molformer': {
        'name': 'MoLFormer',
        'description': 'MoLFormer-XL pretrained on 10% ZINC plus 10% PubChem',
        'model_id': 'ibm-research/MoLFormer-XL-both-10pct',
    },
}


def transfer_featurizer(model_type):
    if model_type in ('chemberta', 'molformer'):
        return dc.feat.DummyFeaturizer()
    if model_type == 'grover':
        return dc.feat.GroverFeaturizer(features_generator=dc.feat.CircularFingerprint(size=2048))
    raise ValueError(f'Unknown model type: {model_type}')


def load_molnet_dataset(dataset_name, model_type):
    if dataset_name not in MOLNET_DATASETS:
        raise ValueError(f'Unknown dataset: {dataset_name}')
    # Raw alias produces RDKit Mol objects in stable 2.8.0, not tokenizer strings.
    # Disable balancing/normalization here: the HF loss ignores dataset.w.
    return molnet_loader(dataset_name)(featurizer=transfer_featurizer(model_type),
                                      splitter='scaffold', transformers=[])


def load_custom_dataset(data_path, target_cols, smiles_col, model_type):
    dataset = load_csv(data_path, target_cols, smiles_col, transfer_featurizer(model_type))
    return dc.splits.ScaffoldSplitter().train_valid_test_split(
        dataset, frac_train=.8, frac_valid=.1, frac_test=.1)


def validate_hf_data(datasets, task_type, n_tasks):
    if n_tasks != 1:
        raise ValueError('HF example supports one task; sparse multitask loss needs a custom adapter')
    validate_splits(datasets, task_type, n_tasks)
    for dataset in datasets:
        if not np.all(dataset.w == 1):
            raise ValueError('HF 2.8.0 loss ignores weights: labels must be complete and weights equal 1')
        if not all(isinstance(value, str) for value in dataset.X):
            raise ValueError('HF tokenizer requires SMILES strings')


def validate_remote_revision(trust_remote_code, revision):
    if trust_remote_code and (not isinstance(revision, str) or
                             re.fullmatch(r'[0-9a-fA-F]{40}', revision) is None):
        raise ValueError('Remote code requires a reviewed immutable 40-character commit SHA in --revision')


def build_hf_model(model_type, task_type, model_id=None, revision=None,
                   trust_remote_code=False, local_files_only=False):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from deepchem.models.torch_models import HuggingFaceModel
    if model_type == 'molformer' and not trust_remote_code:
        raise ValueError('MoLFormer needs reviewed remote code; supply --trust-remote-code and a pinned --revision')
    validate_remote_revision(trust_remote_code, revision)
    model_id = model_id or PRETRAINED_MODELS[model_type]['model_id']
    options = dict(trust_remote_code=trust_remote_code, local_files_only=local_files_only)
    if revision:
        options['revision'] = revision
    tokenizer = AutoTokenizer.from_pretrained(model_id, **options)
    model_options = dict(options)
    if model_type == 'molformer':
        # Its forward accepts no token_type_ids; generic fast tokenizers add them.
        tokenizer.model_input_names = ['input_ids', 'attention_mask']
        model_options['deterministic_eval'] = True
    network = AutoModelForSequenceClassification.from_pretrained(
        model_id, num_labels=2 if task_type == 'classification' else 1,
        problem_type='single_label_classification' if task_type == 'classification' else 'regression',
        **model_options)
    # The base checkpoint supplies the encoder; the prediction head may be new.
    return HuggingFaceModel(model=network, tokenizer=tokenizer, task=task_type,
                            batch_size=16, learning_rate=2e-5, device='cpu')


def train_hf(model_type, train, valid, test, task_type='classification',
             n_tasks=1, n_epochs=10, **options):
    validate_hf_data((train, valid, test), task_type, n_tasks)
    model = build_hf_model(model_type, task_type, **options)
    model.fit(train, nb_epoch=n_epochs)
    # The stable HuggingFaceModel prediction contract is raw logits.
    results = evaluate_splits(model, (train, valid, test), task_type,
                              logits=task_type == 'classification')
    return model, results


def train_chemberta(train_dataset, valid_dataset, test_dataset,
                    task_type='classification', n_tasks=1, n_epochs=10, **options):
    return train_hf('chemberta', train_dataset, valid_dataset, test_dataset,
                    task_type, n_tasks, n_epochs, **options)


def train_molformer(train_dataset, valid_dataset, test_dataset,
                    task_type='classification', n_tasks=1, n_epochs=10, **options):
    return train_hf('molformer', train_dataset, valid_dataset, test_dataset,
                    task_type, n_tasks, n_epochs, **options)


def build_grover(task_type, n_tasks, config, checkpoint):
    """Strictly restore only the encoder, leaving a new supervised head."""
    import torch
    from deepchem.models.torch_models import GroverModel
    if not checkpoint or not Path(checkpoint).is_file():
        raise ValueError('GROVER requires an existing --checkpoint (DeepChem component format)')
    if not isinstance(config, dict) or 'hidden_size' not in config:
        raise ValueError('GROVER config must declare the checkpoint hidden_size')
    allowed = {'hidden_size', 'num_attn_heads', 'depth', 'dropout', 'activation',
               'self_attention', 'attn_out_size', 'ffn_num_layers', 'ffn_hidden_size'}
    if set(config) - allowed:
        raise ValueError(f'Unsupported GROVER config keys: {sorted(set(config) - allowed)}')
    model = GroverModel(node_fdim=151, edge_fdim=165, features_dim=2048,
                        task='finetuning', mode=task_type, n_tasks=n_tasks,
                        n_classes=2 if task_type == 'classification' else None,
                        batch_size=16, learning_rate=1e-4, device='cpu', **config)
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    if not isinstance(state, dict) or 'embedding' not in state:
        raise ValueError('Checkpoint has no DeepChem embedding component')
    model.components['embedding'].load_state_dict(state['embedding'], strict=True)
    return model


def train_grover(train_dataset, test_dataset, task_type='classification',
                 n_tasks=1, n_epochs=20, checkpoint=None, config=None,
                 valid_dataset=None):
    valid_dataset = valid_dataset if valid_dataset is not None else test_dataset
    validate_splits((train_dataset, valid_dataset, test_dataset), task_type, n_tasks)
    model = build_grover(task_type, n_tasks, config, checkpoint)
    model.fit(train_dataset, nb_epoch=n_epochs)
    return model, evaluate_splits(model, (train_dataset, valid_dataset, test_dataset), task_type)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=list(PRETRAINED_MODELS), required=True)
    parser.add_argument('--dataset', choices=list(MOLNET_DATASETS))
    parser.add_argument('--data')
    parser.add_argument('--target', nargs='+', default=['target'])
    parser.add_argument('--smiles-col', default='smiles')
    parser.add_argument('--task-type', choices=['classification', 'regression'], default='classification')
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--model-id', help='HF repository or local save_pretrained directory')
    parser.add_argument('--revision', help='HF revision; remote code requires a reviewed immutable commit SHA')
    parser.add_argument('--trust-remote-code', action='store_true', help='Enable model repository code after review')
    parser.add_argument('--local-files-only', action='store_true')
    parser.add_argument('--checkpoint', help='Local DeepChem GROVER component checkpoint')
    parser.add_argument('--grover-config', help='JSON architecture matching the checkpoint')
    args = parser.parse_args()
    if not args.dataset and not args.data:
        print('Error: Must specify either --dataset or --data', file=sys.stderr)
        return 1
    if args.dataset and args.data:
        print('Error: Cannot specify both --dataset and --data', file=sys.stderr)
        return 1
    if args.epochs < 1:
        parser.error('--epochs must be positive')
    try:
        # Fail before benchmark/weight downloads if required inputs are absent.
        if args.model == 'grover' and (not args.checkpoint or not args.grover_config):
            raise ValueError('GROVER requires --checkpoint and --grover-config')
        if args.model == 'molformer' and (not args.trust_remote_code or not args.revision):
            raise ValueError('MoLFormer requires reviewed --trust-remote-code and --revision')
        if args.model != 'grover':
            validate_remote_revision(args.trust_remote_code, args.revision)
        if args.dataset:
            task_type, n_tasks = MOLNET_DATASETS[args.dataset]
            if args.model != 'grover' and n_tasks != 1:
                raise ValueError('HF example supports one task; choose a single-task dataset')
            tasks, datasets, _ = load_molnet_dataset(args.dataset, args.model)
            train, valid, test = datasets
            n_tasks = len(tasks)
        else:
            train, valid, test = load_custom_dataset(args.data, args.target, args.smiles_col, args.model)
            task_type, n_tasks = args.task_type, len(args.target)
        if args.model == 'grover':
            config = json.loads(Path(args.grover_config).read_text())
            train_grover(train, test, task_type, n_tasks, args.epochs,
                          args.checkpoint, config, valid)
        else:
            train_hf(args.model, train, valid, test, task_type, n_tasks, args.epochs,
                     model_id=args.model_id, revision=args.revision,
                     trust_remote_code=args.trust_remote_code,
                     local_files_only=args.local_files_only)
        print('[OK] Fine-tuning finished; evaluate applicability before using predictions')
        return 0
    except Exception as error:
        print(f'[FAIL] {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
