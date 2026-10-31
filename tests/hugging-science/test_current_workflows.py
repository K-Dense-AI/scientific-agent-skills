"""Run documentation operations with tiny local data/models and mocked HTTP only."""
from pathlib import Path
import json
import re
from unittest import mock

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'hugging-science'


def code_block(reference, contains):
    text = (SKILL_ROOT / 'references' / reference).read_text()
    return next(b for b in re.findall(r'```python\n(.*?)\n```', text, re.S) if contains in b)


def test_esm_documented_embedding_excludes_special_and_padding_tokens(tmp_path):
    torch = pytest.importorskip('torch')
    transformers = pytest.importorskip('transformers')
    pytest.importorskip('dotenv')
    vocab = ['<cls>', '<pad>', '<eos>', '<unk>', *'ACDEFGHIKLMNPQRSTVWYBXZUO', '<mask>']
    path = tmp_path / 'vocab.txt'
    path.write_text('\n'.join(vocab) + '\n')
    tokenizer = transformers.EsmTokenizer(vocab_file=str(path))
    config = transformers.EsmConfig(vocab_size=len(vocab), hidden_size=16,
        num_hidden_layers=1, num_attention_heads=2, intermediate_size=32,
        max_position_embeddings=64, pad_token_id=1, mask_token_id=len(vocab)-1,
        token_dropout=False, hidden_dropout_prob=0.0, attention_probs_dropout_prob=0.0)
    model = transformers.EsmModel(config).eval()
    namespace = {}
    with mock.patch.object(transformers.AutoTokenizer, 'from_pretrained', return_value=tokenizer), \
         mock.patch.object(transformers.AutoModel, 'from_pretrained', return_value=model), \
         mock.patch('dotenv.load_dotenv', return_value=False):
        exec(code_block('using-models.md', 'per_residue ='), namespace)
    assert [x.shape for x in namespace['per_residue']] == [torch.Size([10,16]), torch.Size([4,16])]
    assert namespace['mean_embeddings'].shape == (2,16)
    # Masked padding must not change the shorter sequence's residue embeddings.
    inputs = tokenizer('ACDE', return_tensors='pt')
    with torch.inference_mode():
        alone = model(**inputs).last_hidden_state[0, 1:-1]
    torch.testing.assert_close(namespace['per_residue'][1], alone, rtol=1e-4, atol=1e-5)


def test_documented_oas_filter_retains_human_rows(tmp_path):
    datasets = pytest.importorskip('datasets')
    path = tmp_path / 'oas.csv'
    path.write_text('meta_Species,sequence_alignment_aa_heavy\nhuman,ACDE\nmouse,GGG\nhuman,MKTA\n')
    real_load = datasets.load_dataset
    calls = []
    def local_load(*args, **kwargs):
        calls.append((args, kwargs))
        return real_load('csv', data_files=str(path), split=kwargs['split'],
                         streaming=kwargs['streaming'])
    namespace = {'repo':'opig/OAS', 'revision':'synthetic-revision'}
    with mock.patch.object(datasets, 'load_dataset', side_effect=local_load):
        exec(code_block('using-datasets.md', 'human_only ='), namespace)
    assert namespace['subset']['meta_Species'] == ['human','human']
    assert calls[0][1]['name'] == 'paired'
    assert calls[0][1]['revision'] == 'synthetic-revision'


def test_documented_filter_fails_on_wrong_schema(tmp_path):
    datasets = pytest.importorskip('datasets')
    path = tmp_path / 'wrong.csv'
    path.write_text('species,sequence\nhuman,ACDE\n')
    data = datasets.load_dataset('csv', data_files=str(path), split='train', streaming=True)
    with mock.patch.object(datasets, 'load_dataset', return_value=data):
        with pytest.raises(ValueError, match='schema changed'):
            exec(code_block('using-datasets.md', 'human_only ='), {'repo':'opig/OAS', 'revision':'test'})


def test_inference_fill_mask_serialization_and_typed_response():
    hub = pytest.importorskip('huggingface_hub')
    # An explicit dedicated URL avoids any live provider lookup; exercise the
    # same task serializer/parser without credentials or a network request.
    with hub.InferenceClient(model='https://example.invalid/inference', token='synthetic-test-token') as client:
        response = json.dumps([{'score':0.6,'token':5,'token_str':'A','sequence':'MKTAYIAKQR'}]).encode()
        with mock.patch.object(client, '_inner_post', return_value=response) as post:
            candidates = client.fill_mask('MKT<mask>YIAKQR')
    assert candidates[0].token_str == 'A'
    assert candidates[0].score == pytest.approx(0.6)
    assert post.call_args.args[0].json['inputs'] == 'MKT<mask>YIAKQR'


def test_gradio_file_marking_does_not_upload(tmp_path):
    gradio = pytest.importorskip('gradio_client')
    path = tmp_path / 'target.pdb'
    path.write_text('END\n')
    data = gradio.handle_file(str(path))
    assert data['path'] == str(path)
    assert data['meta']['_type'] == 'gradio.FileData'
    assert path.read_text() == 'END\n'


def test_provider_mapping_example_uses_sdk_records_not_raw_json():
    hub = pytest.importorskip('huggingface_hub')
    info = hub.ModelInfo(id='facebook/esm2_t33_650M_UR50D', inferenceProviderMapping={
        'hf-inference': {'status':'live','providerId':'facebook/esm2_t33_650M_UR50D','task':'fill-mask'},
        'other': {'status':'staging','providerId':'other-id','task':'feature-extraction'},
    })
    namespace = {}
    with mock.patch.object(hub.HfApi, 'model_info', return_value=info):
        exec(code_block('using-models.md', 'inference_provider_mapping'), namespace)
    assert list(namespace['live']) == ['hf-inference']
    assert namespace['live']['hf-inference'].task == 'fill-mask'
