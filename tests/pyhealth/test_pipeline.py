"""Behavior checks against PyHealth 2.0.2; no clinical datasets or network calls."""
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("pyhealth")
pytest.importorskip("torch")

import numpy as np
import polars as pl
import torch
from pyhealth.data import Patient
from pyhealth.datasets import create_sample_dataset, get_dataloader, split_by_patient
from pyhealth.models import RETAIN, RNN, Transformer
from pyhealth.tasks import MortalityPredictionMIMIC3
from pyhealth.tokenizer import Tokenizer

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pyhealth"
spec = importlib.util.spec_from_file_location("pyhealth_starter", SKILL_ROOT / "assets" / "starter_pipeline.py")
starter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(starter)


def make_patient():
    """A 2.x event registry with two admissions and codes in the first."""
    start = datetime(2020, 1, 1)
    rows = [
        {"event_type": "admissions", "timestamp": start,
         "admissions/hadm_id": "a", "admissions/hospital_expire_flag": "0"},
        {"event_type": "admissions", "timestamp": start + timedelta(days=30),
         "admissions/hadm_id": "b", "admissions/hospital_expire_flag": "1"},
        {"event_type": "diagnoses_icd", "timestamp": start + timedelta(days=1),
         "diagnoses_icd/hadm_id": "a", "diagnoses_icd/icd9_code": "4280"},
        {"event_type": "procedures_icd", "timestamp": start + timedelta(days=1),
         "procedures_icd/hadm_id": "a", "procedures_icd/icd9_code": "9904"},
        {"event_type": "prescriptions", "timestamp": start + timedelta(days=1),
         "prescriptions/hadm_id": "a", "prescriptions/ndc": "00527051210"},
    ]
    return Patient("person-1", pl.DataFrame(rows))


def test_current_task_uses_future_admission_label_and_event_filter():
    patient = make_patient()
    samples = MortalityPredictionMIMIC3()(patient)
    assert len(samples) == 1
    assert samples[0]["hadm_id"] == "a"
    assert samples[0]["mortality"] == 1
    assert samples[0]["conditions"] == ["4280"]
    assert not patient.get_events(event_type="diagnoses_icd", filters=[("hadm_id", "==", "b")])


def test_train_only_processors_keep_validation_codes_out_of_vocabulary():
    task = MortalityPredictionMIMIC3()
    raw = MortalityPredictionMIMIC3()(make_patient())
    raw.append({**raw[0], "patient_id": "person-2", "mortality": 0})
    train = create_sample_dataset(raw, task.input_schema, task.output_schema)
    held_out = [{**raw[0], "patient_id": "person-3", "conditions": ["unseen-held-out-code"]}]
    val = create_sample_dataset(
        held_out, task.input_schema, task.output_schema,
        input_processors=train.input_processors, output_processors=train.output_processors,
    )
    assert val.input_processors["conditions"] is train.input_processors["conditions"]
    assert set(train.patient_to_index).isdisjoint(val.patient_to_index)
    assert not torch.equal(train[0]["conditions"], val[0]["conditions"])
    assert val[0]["conditions"].numel() == 1


def test_demo_patient_split_has_no_overlap():
    samples = starter.build_samples()
    parts = split_by_patient(samples, [0.6, 0.2, 0.2], seed=42)
    assert [len(part) for part in parts] == [72, 24, 24]
    for i, part in enumerate(parts):
        assert {int(part[j]["mortality"].item()) for j in range(len(part))} == {0, 1}
        for other in parts[:i]:
            assert set(part.patient_to_index).isdisjoint(other.patient_to_index)


def test_cpu_training_and_checkpoint_round_trip(tmp_path):
    samples = starter.build_samples()
    trainer, scores = starter.train_and_evaluate(samples, tmp_path)
    assert all(np.isfinite(value) for value in scores.values())
    assert {"pr_auc", "roc_auc", "f1", "loss"} == set(scores)
    checkpoint = tmp_path / "starter" / "best.ckpt"
    assert checkpoint.is_file()
    loader = get_dataloader(samples, batch_size=16, shuffle=False)
    before = trainer.inference(loader)[1]
    with torch.no_grad():
        for parameter in trainer.model.parameters():
            parameter.add_(1)
    trainer.load_ckpt(str(checkpoint))
    after = trainer.inference(loader)[1]
    np.testing.assert_allclose(before, after)


def test_auc_rejects_single_class_partition(tmp_path):
    task = MortalityPredictionMIMIC3()
    raw = [{"patient_id": str(i), "conditions": ["c"], "procedures": ["p"],
            "drugs": ["d"], "mortality": 0} for i in range(20)]
    fitted = starter.build_samples()
    samples = create_sample_dataset(
        raw, task.input_schema, task.output_schema,
        input_processors=fitted.input_processors, output_processors=fitted.output_processors,
    )
    with pytest.raises(ValueError, match="both binary classes"):
        starter.train_and_evaluate(samples, tmp_path)


@pytest.mark.parametrize("model_class,kwargs", [
    (Transformer, {"embedding_dim": 32, "heads": 2, "num_layers": 1, "dropout": 0.1}),
    (RNN, {"embedding_dim": 32, "hidden_dim": 64, "rnn_type": "GRU"}),
    (RETAIN, {"embedding_dim": 32, "dropout": 0.1}),
])
def test_documented_model_variants_forward(model_class, kwargs):
    samples = starter.build_samples()
    model = model_class(dataset=samples, **kwargs)
    output = model(**next(iter(get_dataloader(samples, batch_size=8))))
    assert torch.isfinite(output["loss"]).all()
    assert output["y_prob"].shape == output["y_true"].shape == (8, 1)


def test_tokenizer_round_trips_corresponding_dimensions():
    tok = Tokenizer(tokens=["A01A", "A02A", "A02B", "A03C", "A03D", "A04A"],
                    special_tokens=["<pad>", "<unk>"])
    encoded = tok.batch_encode_2d([["A03C", "A03D"], ["A04A", "B035"]])
    assert encoded == [[5, 6], [7, 1]]
    assert tok.batch_decode_2d(encoded) == [["A03C", "A03D"], ["A04A", "<unk>"]]
    encoded_3d = tok.batch_encode_3d([[["A03C", "A03D"], ["A04A"]], [["B035"]]])
    assert tok.batch_decode_3d(encoded_3d) == [[["A03C", "A03D"], ["A04A"]], [["<unk>"]]]
