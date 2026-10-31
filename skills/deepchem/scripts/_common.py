"""Small data and evaluation guards shared by the bundled training examples."""
import csv
import numpy as np
import deepchem as dc
from rdkit import Chem
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error,
                             mean_squared_error, r2_score, roc_auc_score,
                             average_precision_score)


def load_csv(path, tasks, smiles_col, featurizer):
    """Reject ambiguous headers, invalid SMILES/labels and silent row loss."""
    if not tasks or len(set(tasks)) != len(tasks) or smiles_col in tasks:
        raise ValueError('Choose distinct target columns separate from SMILES')
    with open(path, newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError('CSV has duplicate column headers')
        if not set([smiles_col, *tasks]).issubset(fields):
            raise ValueError('CSV is missing requested SMILES/target columns')
        count = 0
        for line, row in enumerate(reader, 2):
            count += 1
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'CSV row {line} has the wrong number of fields')
            smiles = row[smiles_col].strip()
            molecule = Chem.MolFromSmiles(smiles)
            if not smiles or molecule is None or molecule.GetNumAtoms() == 0:
                raise ValueError(f'Invalid SMILES at row {line}')
            for task in tasks:
                value = row[task].strip()
                if value and not np.isfinite(float(value)):
                    raise ValueError(f'Non-finite label at row {line}, task {task}')
    if not count:
        raise ValueError('CSV has no data rows')
    loader = dc.data.CSVLoader(tasks=tasks, feature_field=smiles_col,
                               featurizer=featurizer)
    dataset = loader.create_dataset(str(path))
    if len(dataset) != count:
        raise ValueError('Featurization dropped rows; inspect unsupported molecules')
    return dataset


def validate_splits(datasets, task_type, n_tasks):
    """Check the assumptions needed for fitting and meaningful evaluation."""
    for name, dataset in zip(('Train', 'Valid', 'Test'), datasets):
        if not len(dataset):
            raise ValueError(f'{name} split is empty; choose a suitable split')
        y, w = np.asarray(dataset.y), np.asarray(dataset.w)
        if y.shape != w.shape or y.ndim != 2 or y.shape[1] != n_tasks:
            raise ValueError(f'{name} labels/weights have incompatible shapes')
        if not np.isfinite(w).all() or (w < 0).any():
            raise ValueError(f'{name} weights must be finite and nonnegative')
        if not np.isfinite(y[w > 0]).all():
            raise ValueError(f'{name} observed labels must be finite')
        if name == 'Train' and (np.sum(w > 0, axis=0) == 0).any():
            raise ValueError('Every task needs an observed training label')
        if task_type == 'classification' and not np.isin(y[w > 0], [0, 1]).all():
            raise ValueError('These classification examples require binary 0/1 labels')


def evaluate_model(model, dataset, task_type, transformers=(), logits=False):
    """Per-task metrics in original units, excluding unobserved labels.

    HF 2.8.0 returns logits; graph classifiers return probabilities. Macro means
    omit undefined tasks and report the actual number of contributing tasks.
    Nonzero sample weights designate observed labels; this is unweighted scoring.
    """
    prediction = np.asarray(model.predict(dataset, transformers=list(transformers)))
    y = dc.trans.undo_transforms(dataset.y, list(transformers))
    if task_type == 'classification':
        if logits:
            shifted = prediction - prediction.max(axis=-1, keepdims=True)
            probability = np.exp(shifted)
            prediction = probability / probability.sum(axis=-1, keepdims=True)
        if prediction.ndim == 2 and y.shape[1] == 1 and prediction.shape[1] == 2:
            prediction = prediction[:, None, :]
        if prediction.shape != (*y.shape, 2):
            raise ValueError(f'Expected (samples, tasks, 2) class scores, got {prediction.shape}')
        if not np.isfinite(prediction).all() or (prediction < 0).any() or (prediction > 1).any():
            raise ValueError('Class scores must be finite probabilities')
        prediction = prediction[..., 1]
    else:
        prediction = prediction.reshape(y.shape)
    if not np.isfinite(prediction).all():
        raise ValueError('Model returned non-finite predictions')
    rows = []
    for task in range(y.shape[1]):
        observed = dataset.w[:, task] > 0
        actual, pred = y[observed, task], prediction[observed, task]
        scores = {'observed': int(observed.sum())}
        if task_type == 'classification':
            scores.update(accuracy=float(accuracy_score(actual, pred >= .5)) if len(actual) else float('nan'),
                          f1=float(f1_score(actual, pred >= .5, zero_division=0)) if len(actual) else float('nan'),
                          roc_auc=float(roc_auc_score(actual, pred)) if len(np.unique(actual)) == 2 else float('nan'),
                          average_precision=float(average_precision_score(actual, pred)) if len(np.unique(actual)) == 2 else float('nan'))
        else:
            scores.update(mae=float(mean_absolute_error(actual, pred)) if len(actual) else float('nan'),
                          rmse=float(np.sqrt(mean_squared_error(actual, pred))) if len(actual) else float('nan'),
                          r2=float(r2_score(actual, pred)) if len(actual) > 1 and np.ptp(actual) > 0 else float('nan'))
        rows.append(scores)
    result = {'per_task': rows, 'macro': {}, 'contributing_tasks': {}}
    for key in rows[0]:
        if key == 'observed':
            continue
        values = [row[key] for row in rows if np.isfinite(row[key])]
        result['macro'][key] = float(np.mean(values)) if values else float('nan')
        result['contributing_tasks'][key] = len(values)
    return result


def evaluate_splits(model, datasets, task_type, transformers=(), logits=False):
    results = {}
    for name, dataset in zip(('Train', 'Valid', 'Test'), datasets):
        result = evaluate_model(model, dataset, task_type, transformers, logits)
        results[name] = result
        print(f'{name}: {result}')
    return results
