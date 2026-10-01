"""Native, offline checks for the skill's v5 recipes, using random tiny models."""
from pathlib import Path
import math
import re

import pytest

torch = pytest.importorskip("torch")
t = pytest.importorskip("transformers")
np = pytest.importorskip("numpy")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "transformers"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("HF_DATASETS_OFFLINE", "1")
    torch.manual_seed(7)
    torch.set_num_threads(1)


@pytest.fixture
def tokenizer():
    words = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "hello", "world", "good", "bad", "text", "paris", "is", "capital", "france", "what", "?", ".", "user", "assistant", ":", "[EOS]"]
    tok = t.BertTokenizer(vocab={word: i for i, word in enumerate(words)}, eos_token="[EOS]")
    tok.chat_template = "{% for message in messages %}{{ message['role'] + ': ' + message['content'] + ' ' + eos_token + ' ' }}{% endfor %}{% if add_generation_prompt %}{{ 'assistant: ' }}{% endif %}"
    return tok


def bert_config(tokenizer, **kwargs):
    return t.BertConfig(vocab_size=len(tokenizer), hidden_size=16, num_hidden_layers=1,
                        num_attention_heads=2, intermediate_size=32, max_position_embeddings=64,
                        pad_token_id=tokenizer.pad_token_id, **kwargs)


def causal_model(tokenizer):
    return t.GPT2LMHeadModel(t.GPT2Config(vocab_size=len(tokenizer), n_embd=16, n_layer=1,
                                        n_head=2, n_positions=64, bos_token_id=tokenizer.cls_token_id,
                                        eos_token_id=tokenizer.eos_token_id,
                                        pad_token_id=tokenizer.pad_token_id)).eval()


def test_tokenizer_offsets_chat_and_roundtrip(tokenizer, tmp_path):
    enc = tokenizer("hello world", return_offsets_mapping=True)
    assert enc.word_ids() == [None, 0, 1, None]
    assert enc["offset_mapping"][1:3] == [(0, 5), (6, 11)]
    chat = [{"role": "user", "content": "hello"}]
    batch = tokenizer.apply_chat_template(chat, tokenize=True, add_generation_prompt=True, return_tensors="pt")
    assert set(batch) >= {"input_ids", "attention_mask"}
    formatted = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    assert batch["input_ids"][0].tolist() == tokenizer(formatted, add_special_tokens=False)["input_ids"]
    tokenizer.add_special_tokens({"extra_special_tokens": ["<CUSTOM>"]})
    tokenizer.save_pretrained(tmp_path)
    restored = t.AutoTokenizer.from_pretrained(tmp_path, local_files_only=True, use_fast=False)
    assert restored.is_fast  # v5 ignores this legacy selector.
    assert restored.get_vocab() == tokenizer.get_vocab()
    assert restored.chat_template == tokenizer.chat_template


def test_model_local_save_reload_and_resize(tokenizer, tmp_path):
    model = t.AutoModelForSequenceClassification.from_config(bert_config(tokenizer, num_labels=3)).eval()
    inputs = tokenizer(["hello", "hello world"], padding=True, return_tensors="pt")
    with torch.inference_mode():
        before = model(**inputs).logits
    model.save_pretrained(tmp_path)
    assert (tmp_path / "model.safetensors").is_file()
    restored = t.AutoModelForSequenceClassification.from_pretrained(tmp_path, local_files_only=True, device_map={"": "cpu"}, dtype=torch.float32)
    with torch.inference_mode():
        torch.testing.assert_close(before, restored(**inputs).logits)
    assert not restored.training
    assert restored.num_parameters() > 0 and restored.get_memory_footprint() > 0
    tokenizer.add_special_tokens({"extra_special_tokens": ["<CUSTOM>"]})
    restored.resize_token_embeddings(len(tokenizer))
    assert restored.get_input_embeddings().weight.shape[0] == len(tokenizer)


@pytest.mark.parametrize("task,head", [("text-classification", t.AutoModelForSequenceClassification),
                                       ("token-classification", t.AutoModelForTokenClassification),
                                       ("fill-mask", t.AutoModelForMaskedLM)])
def test_text_pipelines(tokenizer, task, head):
    model = head.from_config(bert_config(tokenizer)).eval()
    pipe = t.pipeline(task, model=model, tokenizer=tokenizer, device="cpu")
    texts = ["hello [MASK]", "good [MASK]"] if task == "fill-mask" else ["hello world", "good text"]
    result = pipe(texts, batch_size=2)
    assert len(result) == 2
    values = result if isinstance(result[0], dict) else [v for row in result for v in row]
    assert values and all(math.isfinite(float(v["score"])) for v in values)


def test_zero_shot_and_task_registry(tokenizer):
    model = t.AutoModelForSequenceClassification.from_config(bert_config(tokenizer, num_labels=3, id2label={0: "contradiction", 1: "neutral", 2: "entailment"}, label2id={"contradiction": 0, "neutral": 1, "entailment": 2})).eval()
    pipe = t.pipeline("zero-shot-classification", model=model, tokenizer=tokenizer, device="cpu")
    result = pipe("hello world", candidate_labels=["good", "bad"])
    assert set(result["labels"]) == {"good", "bad"}
    assert sum(result["scores"]) == pytest.approx(1.0)
    from transformers.pipelines import get_supported_tasks
    current = set(get_supported_tasks())
    assert "image-text-to-text" in current and "document-question-answering" in current
    assert not ({"question-answering", "summarization", "translation", "image-to-text", "visual-question-answering"} & current)


@pytest.mark.parametrize("kwargs", [{"do_sample": False, "num_beams": 1},
                                     {"do_sample": True, "temperature": .8, "top_k": 5, "top_p": .95, "num_return_sequences": 2},
                                     {"do_sample": False, "num_beams": 3, "num_return_sequences": 2},
                                     {"do_sample": True, "num_beams": 3, "num_return_sequences": 2}])
def test_generation_modes(tokenizer, kwargs):
    model = causal_model(tokenizer)
    tokenizer.padding_side = "left"
    inputs = tokenizer(["hello", "hello world"], padding=True, return_tensors="pt")
    generated = model.generate(**inputs, max_new_tokens=3, **kwargs)
    assert generated.shape[0] == 2 * kwargs.get("num_return_sequences", 1)
    assert inputs["input_ids"].shape[1] < generated.shape[1] <= inputs["input_ids"].shape[1] + 3


def test_chat_generation_streamer_and_config(tokenizer, tmp_path, capsys):
    model = causal_model(tokenizer)
    inputs = tokenizer.apply_chat_template([{"role": "user", "content": "hello"}], tokenize=True, add_generation_prompt=True, return_tensors="pt")
    config = t.GenerationConfig(max_new_tokens=3, do_sample=False, pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
    config.save_pretrained(tmp_path)
    config = t.GenerationConfig.from_pretrained(tmp_path, local_files_only=True)
    stream = t.TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    out = model.generate(**inputs, generation_config=config, streamer=stream)
    response = tokenizer.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    assert isinstance(response, str) and capsys.readouterr().out.endswith("\n")
    pipe = t.pipeline("text-generation", model=model, tokenizer=tokenizer, device="cpu")
    result = pipe([{"role": "user", "content": "hello"}], max_new_tokens=2, do_sample=False)
    assert result[0]["generated_text"][-1]["role"] == "assistant"


def test_static_cache_matches_dynamic(tokenizer):
    config = t.LlamaConfig(vocab_size=len(tokenizer), hidden_size=16, intermediate_size=32,
                           num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=2,
                           max_position_embeddings=64, pad_token_id=0, bos_token_id=2, eos_token_id=20)
    model = t.AutoModelForCausalLM.from_config(config).eval()
    inputs = tokenizer("hello world", return_tensors="pt", return_token_type_ids=False)
    baseline = model.generate(**inputs, max_new_tokens=3, do_sample=False)
    cache = t.StaticCache(config=model.config, max_cache_len=inputs["input_ids"].shape[1] + 3)
    static = model.generate(**inputs, max_new_tokens=3, do_sample=False, past_key_values=cache)
    assert torch.equal(baseline, static)


def test_seq2seq_and_collators(tokenizer):
    model = t.AutoModelForSeq2SeqLM.from_config(t.T5Config(vocab_size=len(tokenizer), d_model=16, d_ff=32, num_layers=1, num_decoder_layers=1, num_heads=2, decoder_start_token_id=0, pad_token_id=0, eos_token_id=20)).eval()
    inputs = tokenizer("hello world", return_tensors="pt", return_token_type_ids=False)
    output = model.generate(**inputs, max_new_tokens=3)
    assert 1 < output.shape[1] <= 4
    collator = t.DataCollatorForSeq2Seq(tokenizer, model=model)
    batch = collator([{"input_ids": [5, 6], "labels": [7, 20]}, {"input_ids": [5], "labels": [8]}])
    assert batch["labels"][1, -1] == -100
    assert "decoder_input_ids" in batch
    mlm = t.DataCollatorForLanguageModeling(tokenizer, mlm=True, mlm_probability=1.0)
    masked = mlm([tokenizer("hello world"), tokenizer("hello")])
    assert (masked["labels"][:, 0] == -100).all()
    # A genuine EOS survives when PAD is distinct, but is masked when PAD=EOS.
    features = [{"input_ids": [5, 20]}, {"input_ids": [5]}]
    assert t.DataCollatorForLanguageModeling(tokenizer, mlm=False)(features)["labels"][0, 1] == 20
    tokenizer.pad_token = tokenizer.eos_token
    assert t.DataCollatorForLanguageModeling(tokenizer, mlm=False)(features)["labels"][0, 1] == -100


def training_data(tokenizer):
    datasets = pytest.importorskip("datasets")
    data = datasets.Dataset.from_dict({"text": ["good text", "bad", "hello world", "good", "bad text", "hello", "good world", "bad world"], "label": [1, 0, 1, 1, 0, 0, 1, 0]})
    return data.map(lambda batch: tokenizer(batch["text"], truncation=True, max_length=32), batched=True)


def args(tmp_path, **kwargs):
    return t.TrainingArguments(output_dir=str(tmp_path), use_cpu=True, report_to="none", disable_tqdm=True,
                               optim="adamw_torch", dataloader_pin_memory=False,
                               per_device_train_batch_size=2, per_device_eval_batch_size=2, **kwargs)


def test_trainer_train_evaluate_save_resume(tokenizer, tmp_path):
    pytest.importorskip("accelerate")
    model = t.AutoModelForSequenceClassification.from_config(bert_config(tokenizer, num_labels=2))
    data = training_data(tokenizer)
    trainer = t.Trainer(model=model, args=args(tmp_path, max_steps=2, eval_strategy="steps", eval_steps=1, save_strategy="steps", save_steps=1, load_best_model_at_end=True, metric_for_best_model="accuracy", warmup_steps=.1), train_dataset=data, eval_dataset=data, processing_class=tokenizer, data_collator=t.DataCollatorWithPadding(tokenizer), compute_metrics=lambda pred: {"accuracy": float(np.mean(pred.predictions.argmax(-1) == pred.label_ids))})
    original = model.classifier.weight.detach().clone()
    result = trainer.train()
    assert result.global_step == 2 and math.isfinite(result.training_loss)
    trained = t.AutoModelForSequenceClassification.from_pretrained(tmp_path / "checkpoint-2", local_files_only=True)
    assert not torch.equal(original, trained.classifier.weight)
    assert 0 <= trainer.evaluate()["eval_accuracy"] <= 1
    assert (tmp_path / "checkpoint-2" / "optimizer.pt").exists()
    trainer.save_model(tmp_path / "export")
    assert (tmp_path / "export" / "tokenizer.json").exists()
    resume = t.Trainer(model=t.AutoModelForSequenceClassification.from_config(bert_config(tokenizer, num_labels=2)), args=args(tmp_path, max_steps=3, save_strategy="no"), train_dataset=data, processing_class=tokenizer, data_collator=t.DataCollatorWithPadding(tokenizer))
    assert resume.train(resume_from_checkpoint=str(tmp_path / "checkpoint-2")).global_step == 3


def test_documented_weighted_trainer(tokenizer, tmp_path):
    text = (SKILL_ROOT / "references" / "training.md").read_text()
    section = text.split("### Custom Trainer", 1)[1].split("### Custom Callbacks", 1)[0]
    code = re.search(r"```python\n(.*?)```", section, re.S).group(1)
    namespace = {}
    exec(compile(code, "training.md:WeightedTrainer", "exec"), namespace)
    model = t.AutoModelForSequenceClassification.from_config(bert_config(tokenizer, num_labels=2))
    data = training_data(tokenizer)
    trainer = namespace["WeightedTrainer"](model=model, args=args(tmp_path, max_steps=1, save_strategy="no"), train_dataset=data, class_weights=[1., 2.], processing_class=tokenizer, data_collator=t.DataCollatorWithPadding(tokenizer))
    assert not trainer.model_accepts_loss_kwargs
    assert math.isfinite(trainer.train().training_loss)
    batch = t.DataCollatorWithPadding(tokenizer)([{**tokenizer("hello"), "labels": 0}, {**tokenizer("bad"), "labels": 1}])
    model.eval()
    loss, output = trainer.compute_loss(model, batch, return_outputs=True, num_items_in_batch=2)
    expected = torch.nn.functional.cross_entropy(output.logits, batch["labels"], weight=torch.tensor([1., 2.]))
    torch.testing.assert_close(loss, expected)
    assert "labels" in batch


def test_peft_lora_updates_only_trainable_parameters(tokenizer, tmp_path):
    peft = pytest.importorskip("peft")
    model = t.AutoModelForSequenceClassification.from_config(bert_config(tokenizer, num_labels=2))
    model = peft.get_peft_model(model, peft.LoraConfig(r=2, lora_alpha=4, target_modules=["query", "value"], lora_dropout=0.0, bias="none", task_type="SEQ_CLS"))
    frozen = next(p for p in model.parameters() if not p.requires_grad)
    before = frozen.detach().clone()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=.01)
    batch = tokenizer(["hello", "bad world"], padding=True, return_tensors="pt")
    loss = model(**batch, labels=torch.tensor([1, 0])).loss
    loss.backward()
    assert any(p.grad is not None and torch.count_nonzero(p.grad) > 0 for n, p in model.named_parameters() if "lora_B" in n)
    opt.step()
    torch.testing.assert_close(frozen, before)
    model.save_pretrained(tmp_path)
    assert (tmp_path / "adapter_model.safetensors").exists()


def test_image_pipeline_with_pil_processor():
    Image = pytest.importorskip("PIL.Image")
    model = t.AutoModelForImageClassification.from_config(t.ViTConfig(image_size=16, patch_size=8, hidden_size=16, num_hidden_layers=1, num_attention_heads=2, intermediate_size=32, num_labels=2)).eval()
    processor = t.ViTImageProcessorPil(size={"height": 16, "width": 16})
    pipe = t.pipeline("image-classification", model=model, image_processor=processor, device="cpu")
    result = pipe(Image.new("RGB", (24, 20), (30, 60, 90)))
    assert len(result) == 2 and sum(item["score"] for item in result) == pytest.approx(1.0)


def test_audio_pipeline_waveform_sampling_rate():
    model = t.AutoModelForAudioClassification.from_config(t.Wav2Vec2Config(hidden_size=16, num_hidden_layers=1, num_attention_heads=2, intermediate_size=32, conv_dim=(8, 8, 8), conv_stride=(5, 2, 2), conv_kernel=(10, 3, 3), num_conv_pos_embedding_groups=2, num_conv_pos_embeddings=8, classifier_proj_size=8, num_labels=2)).eval()
    extractor = t.Wav2Vec2FeatureExtractor(sampling_rate=16000, return_attention_mask=True)
    pipe = t.pipeline("audio-classification", model=model, feature_extractor=extractor, device="cpu")
    result = pipe({"array": np.sin(np.arange(800, dtype=np.float32) * .1), "sampling_rate": 16000})
    assert len(result) == 2 and sum(item["score"] for item in result) == pytest.approx(1.0)
    waveform = np.sin(np.arange(800, dtype=np.float32) * .1)
    independent = pipe({"array": waveform, "sampling_rate": 16000}, function_to_apply="sigmoid")
    with torch.inference_mode():
        logits = model(**extractor(waveform, sampling_rate=16000, return_tensors="pt")).logits[0]
    scores = {row["label"]: row["score"] for row in independent}
    for index, value in enumerate(logits.sigmoid()):
        assert scores[model.config.id2label[index]] == pytest.approx(float(value), abs=1e-6)


def test_bitsandbytes_cpu_quantization():
    bnb = pytest.importorskip("bitsandbytes")
    values = torch.linspace(-1, 1, 256).reshape(16, 16)
    quantized, state = bnb.functional.quantize_4bit(values, blocksize=64, quant_type="nf4")
    restored = bnb.functional.dequantize_4bit(quantized, state)
    assert restored.shape == values.shape and torch.isfinite(restored).all()
    assert torch.mean((restored - values) ** 2) < .01


def test_direct_qa_context_spans(tokenizer):
    model = t.AutoModelForQuestionAnswering.from_config(bert_config(tokenizer)).eval()
    batch = tokenizer("what capital ?", "paris is capital france", return_offsets_mapping=True,
                      truncation="only_second", max_length=32, return_tensors="pt")
    offsets = batch.pop("offset_mapping")[0].tolist()
    context_tokens = [i for i, sequence in enumerate(batch.sequence_ids()) if sequence == 1]
    with torch.inference_mode():
        output = model(**batch)
    spans = [(float(output.start_logits[0, start] + output.end_logits[0, end]), start, end)
             for start in context_tokens for end in context_tokens if start <= end < start + 4]
    _, start, end = max(spans)
    answer = "paris is capital france"[offsets[start][0]:offsets[end][1]]
    assert answer and start <= end


def test_attention_modes_and_checkpointed_backward(tokenizer, tmp_path):
    model = t.AutoModel.from_config(bert_config(tokenizer)).eval()
    model.save_pretrained(tmp_path)
    inputs = tokenizer("hello world", return_tensors="pt")
    outputs = []
    for implementation in ["eager", "sdpa"]:
        restored = t.AutoModel.from_pretrained(tmp_path, local_files_only=True, attn_implementation=implementation)
        with torch.inference_mode():
            outputs.append(restored(**inputs).last_hidden_state)
    torch.testing.assert_close(*outputs, atol=1e-5, rtol=1e-5)
    classifier = t.AutoModelForSequenceClassification.from_config(bert_config(tokenizer, num_labels=2))
    classifier.gradient_checkpointing_enable()
    classifier.train()
    loss = classifier(**inputs, labels=torch.tensor([1])).loss
    loss.backward()
    assert math.isfinite(float(loss.detach())) and classifier.classifier.weight.grad is not None
