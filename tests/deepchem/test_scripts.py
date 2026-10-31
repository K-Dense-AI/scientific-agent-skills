"""Offline synthetic API/data/fit contracts; no public datasets or model downloads."""
from pathlib import Path
import sys
import numpy as np
import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'deepchem'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
dc = pytest.importorskip('deepchem')
import _common
import graph_neural_network as graph
import predict_solubility as solubility
import transfer_learning as transfer

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

SMILES = ['CCO', 'CCC', 'CCCC', 'c1ccccc1', 'CC(=O)O',
          'CN1C=NC2=C1C(=O)N(C(=O)N2C)C', 'CCN', 'CCCN', 'c1ccncc1', 'CC(C)O',
          'CCOC', 'CCCl', 'CCBr', 'c1ccc(O)cc1', 'CC(N)=O',
          'CCS', 'CC#N', 'CCC=O', 'c1ccc2ccccc2c1', 'CC(C)(C)O']


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / 'molecules.csv'
    path.write_text('smiles,target\n' + ''.join(f'{s},{i / 10}\n' for i, s in enumerate(SMILES)))
    return path


def test_molnet_catalogue_and_alias_contracts():
    assert graph.molnet_loader('bace') is dc.molnet.load_bace_classification
    for name in graph.MOLNET_DATASETS:
        assert callable(graph.molnet_loader(name))
    from deepchem.molnet.load_function.molnet_loader import featurizers
    assert featurizers['ecfp'].featurize(['CCO']).shape == (1, 1024)
    assert not isinstance(featurizers['raw'].featurize(['CCO'])[0], str)
    assert transfer.transfer_featurizer('chemberta').featurize(['CCO'])[0] == 'CCO'


@pytest.mark.parametrize('name,width,bonds', [('gcn',30,None),('gat',30,None),
    ('attentivefp',30,11),('mpnn',30,11),('dmpnn',133,14)])
def test_graph_model_feature_contract(name, width, bonds):
    feature = graph.create_featurizer(name).featurize(['CCO'])[0]
    assert feature.node_features.shape == (3, width)
    if bonds is None:
        assert feature.edge_features is None
    else:
        assert feature.edge_features.shape == (4, bonds)


def test_grover_featurization():
    feature = transfer.transfer_featurizer('grover').featurize(['CCO'])[0]
    assert feature.node_features.shape == (3,151)
    assert feature.edge_features.shape == (4,165)
    assert len(feature.additional_features) == 2048


def test_csv_loading_and_split_conserve_rows(csv_path):
    train, valid, test = transfer.load_custom_dataset(csv_path, ['target'], 'smiles', 'chemberta')
    assert (len(train), len(valid), len(test)) == (16, 2, 2)
    assert set(np.concatenate([train.ids, valid.ids, test.ids])) == set(SMILES)
    assert all(isinstance(s, str) for s in train.X)


@pytest.mark.parametrize('text,match', [
    ('smiles,target,target\nCCO,1,2\n','duplicate'),
    ('smiles,target\nnot-a-molecule,1\n','Invalid SMILES'),
    ('smiles,target\nCCO,nan\n','Non-finite'),
    ('smiles,target\nCCO,inf\n','Non-finite'),
    ('smiles,target\nCCO,1,2\n','number of fields'),
])
def test_csv_rejects_ambiguous_or_invalid_data(tmp_path, text, match):
    path = tmp_path / 'bad.csv'
    path.write_text(text)
    with pytest.raises(ValueError, match=match):
        _common.load_csv(path, ['target'], 'smiles', dc.feat.CircularFingerprint())


def test_missing_labels_remain_masked(tmp_path):
    path = tmp_path / 'missing.csv'
    path.write_text('smiles,target\nCCO,\nCCC,1\n')
    data = _common.load_csv(path, ['target'], 'smiles', dc.feat.DummyFeaturizer())
    assert data.w[:,0].tolist() == [0,1]
    with pytest.raises(ValueError, match='ignores weights'):
        transfer.validate_hf_data((data,data,data), 'classification', 1)


def test_hf_rejects_sparse_multitask_and_nonbinary_labels():
    data = dc.data.NumpyDataset(np.array(['CCO','CCC']), np.ones((2,2)))
    with pytest.raises(ValueError, match='one task'):
        transfer.validate_hf_data((data,data,data), 'classification', 2)
    data = dc.data.NumpyDataset(np.array(['CCO','CCC']), np.array([[0],[2]]))
    with pytest.raises(ValueError, match='binary'):
        transfer.validate_hf_data((data,data,data), 'classification', 1)


def test_original_unit_regression_and_class_support():
    data = dc.data.NumpyDataset(np.zeros((3,2)), np.array([[10.],[12.],[14.]]))
    transformer = dc.trans.NormalizationTransformer(transform_y=True, dataset=data)
    normalized = transformer.transform(data)
    class Predictor:
        def predict(self, dataset, transformers=()):
            return dc.trans.undo_transforms(np.zeros_like(dataset.y), transformers)
    scores = _common.evaluate_model(Predictor(), normalized, 'regression', [transformer])
    assert scores['macro']['mae'] == pytest.approx(4/3)
    class Logits:
        def predict(self, dataset, transformers=()):
            return np.array([[2.,1.],[2.,1.],[1.,2.]])
    data = dc.data.NumpyDataset(np.zeros((3,2)), np.array([[0.],[0.],[0.]]))
    scores = _common.evaluate_model(Logits(), data, 'classification', logits=True)
    assert scores['macro']['accuracy'] == pytest.approx(2/3)
    assert np.isnan(scores['macro']['roc_auc'])
    assert scores['contributing_tasks']['roc_auc'] == 0


def test_solubility_small_cpu_training_and_prediction(csv_path, tmp_path, monkeypatch):
    pytest.importorskip('torch')
    monkeypatch.chdir(tmp_path)
    model, _, transforms = solubility.train_solubility_model(csv_path, target_col='target', n_epochs=1)
    prediction = solubility.predict_new_molecules(model, ['CCO','c1ccccc1'], transforms)
    assert prediction.shape == (2,1)
    assert np.isfinite(prediction).all()
    with pytest.raises(ValueError, match='invalid or unsupported'):
        solubility.predict_new_molecules(model, ['not-a-molecule'], transforms)


def test_dmpnn_binary_forward_and_training(tmp_path):
    pytest.importorskip('torch_geometric')
    import torch
    torch.set_num_threads(1)
    model = graph.create_model('dmpnn', 1, 'classification')
    features = graph.create_featurizer('dmpnn').featurize(['CCO','CCC','CCN','CCCl'])
    data = dc.data.NumpyDataset(features, np.array([[0.],[1.],[0.],[1.]]))
    loss = model.fit(data, nb_epoch=1, checkpoint_interval=0)
    assert np.isfinite(loss)
    assert model.predict(data).shape == (4,2)
    assert _common.evaluate_model(model, data, 'classification')['per_task'][0]['observed'] == 4


@pytest.mark.parametrize('task', ['classification','regression'])
def test_local_hf_model_object_tokenizer_fit_and_score(tmp_path, task):
    transformers = pytest.importorskip('transformers')
    pytest.importorskip('torch')
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    tokenizer = Tokenizer(WordLevel({'[UNK]':0,'[PAD]':1,'CCO':2,'CCC':3,'CCN':4,'CCCl':5}, unk_token='[UNK]'))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer = transformers.PreTrainedTokenizerFast(tokenizer_object=tokenizer, unk_token='[UNK]', pad_token='[PAD]', model_max_length=32)
    directory = tmp_path / task
    tokenizer.save_pretrained(directory)
    config = transformers.RobertaConfig(vocab_size=6, hidden_size=16, num_hidden_layers=1,
        num_attention_heads=2, intermediate_size=24, max_position_embeddings=64,
        pad_token_id=1, num_labels=2 if task == 'classification' else 1,
        problem_type='single_label_classification' if task == 'classification' else 'regression')
    network = transformers.RobertaForSequenceClassification(config)
    network.save_pretrained(directory)
    data = dc.data.NumpyDataset(np.array(['CCO','CCC','CCN','CCCl']), np.array([[0.],[1.],[0.],[1.]]))
    model, scores = transfer.train_chemberta(data,data,data,task_type=task,n_epochs=1,
                                            model_id=str(directory),local_files_only=True)
    assert np.isfinite(model.predict(data)).all()
    assert scores['Test']['per_task'][0]['observed'] == 4


@pytest.mark.parametrize('task', ['classification', 'regression'])
def test_grover_embedding_restore_and_fit(tmp_path, task):
    torch = pytest.importorskip('torch')
    from deepchem.models.torch_models import GroverModel
    config = dict(hidden_size=16, num_attn_heads=2, depth=1, ffn_hidden_size=16)
    source = GroverModel(node_fdim=151, edge_fdim=165, features_dim=2048,
                         task='finetuning', mode=task, n_tasks=1, n_classes=2 if task == 'classification' else None, device='cpu', **config)
    path = tmp_path / 'embedding.pt'
    torch.save({'embedding':source.components['embedding'].state_dict()}, path)
    target = transfer.build_grover(task, 1, config, path)
    for name, value in source.components['embedding'].state_dict().items():
        assert torch.equal(value, target.components['embedding'].state_dict()[name])
    data = dc.data.NumpyDataset(transfer.transfer_featurizer('grover').featurize(['CCO','CCC']), np.array([[0.],[1.]]))
    loss = target.fit(data, nb_epoch=1, checkpoint_interval=0)
    assert np.isfinite(loss)
    assert np.isfinite(target.predict(data)).all()
    assert _common.evaluate_model(target, data, task)['per_task'][0]['observed'] == 2


def test_transfer_refuses_missing_checkpoint_and_unreviewed_code():
    with pytest.raises(ValueError, match='existing --checkpoint'):
        transfer.build_grover('regression', 1, {'hidden_size':16}, None)
    with pytest.raises(ValueError, match='reviewed remote code'):
        transfer.build_hf_model('molformer', 'classification')


def test_numeric_baseline_and_custom_torch_loss():
    from sklearn.ensemble import RandomForestRegressor
    data = dc.data.NumpyDataset(dc.feat.CircularFingerprint(size=2048).featurize(SMILES[:6]),
                               np.arange(6,dtype=float)[:,None],ids=SMILES[:6])
    model = dc.models.SklearnModel(RandomForestRegressor(n_estimators=8,random_state=7))
    model.fit(data.select([0,1,2,3]))
    assert model.predict(data.select([4,5])).shape == (2,)
    torch = pytest.importorskip('torch')
    wrapped = dc.models.TorchModel(torch.nn.Linear(2048,1), loss=dc.models.losses.L2Loss(),
                                   output_types=['prediction'], device='cpu')
    assert np.isfinite(wrapped.fit(data,nb_epoch=1,checkpoint_interval=0))


@pytest.mark.parametrize('revision', [None, '', 'main', 'compat-v4', 'a' * 39, 'g' * 40])
def test_remote_code_rejects_moving_or_invalid_revisions(revision):
    with pytest.raises(ValueError, match='40-character commit SHA'):
        transfer.build_hf_model('molformer', 'classification',
                                trust_remote_code=True, revision=revision)


def test_remote_code_accepts_full_commit_and_builtin_models_allow_branches():
    transfer.validate_remote_revision(True, '361063d0ad524ef77cf39b08469f6be770dc550f')
    transfer.validate_remote_revision(False, 'main')


def test_grid_search_keyword_builder_and_result_contract(tmp_path):
    from sklearn.ensemble import RandomForestRegressor
    data = dc.data.NumpyDataset(np.arange(16).reshape(8,2), np.arange(8)[:,None])
    def builder(n_estimators, max_depth, model_dir=None):
        return dc.models.SklearnModel(RandomForestRegressor(n_estimators=n_estimators,
            max_depth=max_depth,random_state=7),model_dir=model_dir)
    best, params, scores = dc.hyper.GridHyperparamOpt(builder).hyperparam_search(
        {'n_estimators':[4,8],'max_depth':[2]},data.select([0,1,2,3,4,5]),
        data.select([6,7]),dc.metrics.Metric(dc.metrics.mean_absolute_error),
        output_transformers=[],use_max=False,logdir=str(tmp_path))
    assert params['n_estimators'] in [4,8]
    assert len(scores) == 2
    assert np.isfinite(best.predict(data)).all()


def test_cli_conflicting_sources_fail_before_loading(monkeypatch):
    for module, args in [(graph, ['script','--dataset','bbbp','--data','missing.csv']),
                         (transfer, ['script','--model','chemberta','--dataset','bbbp','--data','missing.csv'])]:
        monkeypatch.setattr(sys, 'argv', args)
        assert module.main() == 1
