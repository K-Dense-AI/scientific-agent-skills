# `waypoint` CLI reference

Reviewed 2026-10-01 against `waypoint-bio` 1.0.2 (PyPI wheel) and GitHub main
1.0.4 (`f45eee6d07a480bfc90f84ab8082bbc969dec15d`). Flags below are shared;
export/logging differences and known failures are recorded in `upstream-review.md`.
Hub-backed training examples are illustrative, without authenticated scientific execution.

```
waypoint {pretrain,benchmark,finetune,embed,prepare-dataset} ...
```

Config paths are resolved first against the working directory, then against the bundled
`waypoint_bio/configs/` tree inside the installed wheel. So `--config configs/benchmark.yaml`
works from anywhere without cloning the repo. The same fallback applies to the bundled example
data (`examples/abundance_matrix.tsv`, `examples/finetune_classification.parquet`, …).

---

## `waypoint prepare-dataset`

Converts a sample × taxa abundance matrix into waypoint format.

| Flag | Default | Notes |
| --- | --- | --- |
| `--input` | *required* | `.csv` / `.tsv` abundance matrix. |
| `--output` | *required* | `.parquet` recommended; `.csv` supported. |
| `--orientation` | `auto` | `auto`, `samples_as_rows`, `taxa_as_rows`. |
| `--taxonomy_format` | `full` | `full` for lineage strings; a rank name (`genus`, `species`, …) to prefix bare names. |
| `--no_normalize` | off | Skip row-normalisation to relative abundances. |
| `--keep_zeros` | off | Keep zero-abundance entries in each sample's lists. |
| `--metadata` | none | CSV/TSV/parquet of per-sample metadata, indexed by sample ID, merged in as extra columns. |

`auto` treats the file as taxa-as-rows when the first column header is `taxonomy`, `lineage`,
`taxon`, `otu`, or `#otu id` (case-insensitive); otherwise samples-as-rows with the first column
as the sample ID.

`--taxonomy_format genus` prefixes bare column names with `g__`. It disables higher-rank fallback,
because a bare name carries no lineage to fall back to — prefer real lineage strings.

---

## `waypoint embed`

One fixed-size vector per sample from a pretrained checkpoint. No fine-tuning, no labels needed.

| Flag | Default | Notes |
| --- | --- | --- |
| `--model` | `outpost-bio/Waypoint-6m` | Hub id or local checkpoint directory. |
| `--data` | *required* | Waypoint-format `.parquet` / `.csv` / `.tsv`. |
| `--output` | *required* | `.parquet`, or `.csv` if the path ends in `.csv`. |
| `--pooling` | `last_token` | `last_token`, `mean`, `first_token`, `cls_token`. |
| `--batch_size` | `32` | |
| `--max_length` | `512` | Keeps at most max_length - 2 ordered entries; no guarantee discarded taxa are uninformative. |
| `--device` | auto | `cuda`, `mps`, or `cpu`; auto-detects in that order. |

Output columns are `dim_0 … dim_{H-1}`, indexed by sample ID. Hidden size `H` is 256 (6m),
512 (45m), 768 (170m).

**Behaviour worth knowing:** tokens that map to `<unk>` are *dropped* before ordering, not encoded.
A row with no in-vocabulary taxa still produces an output row, but its sequence is `[BOS][EOS]` and
the embedding is meaningless. Run `scripts/vocab_coverage.py` first.

Ordering: by descending abundance z-score when `token_std_means.parquet` is present (it ships with
every published checkpoint and with `waypoint pretrain` output), otherwise by descending raw
relative abundance.

---

## `waypoint finetune`

Fine-tunes a checkpoint on your own labelled waypoint-format data.

| Flag | Default | Notes |
| --- | --- | --- |
| `--model` | *required* | Hub id or local checkpoint. |
| `--data` | *required* | Waypoint-format file containing `--target`. |
| `--output_dir` | *required* | |
| `--task_type` | *required* | `classification` or `regression`. |
| `--target` | *required* | Target column name. |
| `--covariate_column` | none | Categorical column, one-hot encoded and concatenated to the pooled embedding before the head. |
| `--config` | task default | Flat YAML; defaults to the bundled classification/regression config. |

### Fine-tuning config keys

```yaml
split_column: null        # column holding train/validation/test; null = random split
val_fraction: 0.1
test_fraction: 0.1

max_length: 512           # 2 <= max_length <= checkpoint n_positions
pooling_strategy: last_token
filter_unk_taxa: true     # drop out-of-vocabulary taxa rather than feed <unk>

seed: 42
learning_rate: 0.00003
num_epochs: 1             # raise this; early stopping is what should terminate training
batch_size: 64
warmup_steps: 1000        # lower to ~50 for small datasets
weight_decay: 0.001
eval_strategy: steps
eval_steps: 400
logging_steps: 5
patience: 5               # eval steps without improvement before early stopping
save_total_limit: 1

use_lora: false
lora_r: 8
lora_alpha: 16            # convention: 2 * r
lora_dropout: 0.05
lora_target_modules: [c_attn, c_proj]   # GPT-2 fused QKV and output projection
lora_bias: none
lora_fan_in_fan_out: true               # required for GPT-2 Conv1D layouts
```

The shipped configs use `num_epochs: 1`, whereas the paper describes up to 300 fine-tuning
epochs with early stopping. The default CLI config does not reproduce that training budget.
On small datasets, choose enough epochs and a suitable evaluation interval for validation
and early stopping to occur. Likewise `eval_steps: 400` may never fire; lower it so early stopping
and best-checkpoint selection can actually work.

GitHub 1.0.4 merges LoRA adapters before export. PyPI 1.0.2 saves an adapter-only model when
`use_lora: true`; plain `AutoModel.from_pretrained` cannot load that export. Keep LoRA disabled
for the released-package workflow, or explicitly load/merge via PEFT with the original base model.
Both versions also require a tokenizer that actually implements vocabulary serialization.

The fine-tuning config `seed` affects initial RNG setup and random splits, but its value is
not passed to `TrainingArguments` either. Explicitly wire trainer seeds for controlled repeats.

### Outputs

These describe successful exports; see the tokenizer/LoRA limitations above.

| Path | Contents |
| --- | --- |
| `best_model/` | Fine-tuned base transformer in standard HF format, plus tokenizer and `token_std_means.parquet`. |
| `best_model/finetuned_model_state.pt` | Full torch state dict: transformer + head + covariate embedding. |
| `validation_metrics.json`, `test_metrics.json` | Per-split scores, benchmark-equivalent. |
| `training_log.csv`, `training_log.html` | GitHub 1.0.4 only, when log rows exist; HTML uses Plotly from a CDN. |
| `validation_predictions.csv`, `test_predictions.csv` | GitHub 1.0.4 only; prediction order, without original sample IDs. |
| `finetune_results.json` | Run config, label maps, covariate map, val/test scores. |

---

## `waypoint benchmark`

| Flag | Default | Notes |
| --- | --- | --- |
| `--model` | `outpost-bio/Waypoint-6m` | Hub id or local checkpoint. |
| `--config` | bundled `configs/benchmark.yaml` | Shared by all eight tasks. |
| `--output_dir` | `outputs/benchmark` | |
| `--tasks` | all 8 | Space-separated task numbers, e.g. `--tasks 1 6`. |
| `--seed` | `42` | |
| `--max_samples` | none | Caps each split; use for smoke tests only, never for a reported score. |

`configs/benchmark.yaml` is the fine-tuning config applied identically to every task:
`learning_rate: 3e-5`, `num_epochs: 1`, `batch_size: 64`, `warmup_steps: 1000`,
`weight_decay: 0.001`, `patience: 5`, `pooling_strategy: last_token`, `eval_steps: 400`,
`filter_unk_taxa: true`, `seed: 42`. The paper describes up to 300 fine-tuning epochs with early
stopping, so the shipped one-epoch config already differs from the paper. Record the actual
training budget and completed evaluation steps instead of claiming automatic comparability.

The paper reports repeated runs. The CLI `--seed` seeds Torch/NumPy before tasks, but
`TrainingArguments` does not receive that value and resets training randomness to its default
42; YAML `seed` is unused here. Changing `--seed` alone does not establish independent training
seeds. Use an explicitly reviewed local change passing the seed to the trainer for a seed study.
Record the dataset/model revisions, package/dependency versions and hardware;
unchanged YAML alone is not a claim to reproduce the paper.

---

## `waypoint pretrain`

| Flag | Default | Notes |
| --- | --- | --- |
| `--model_config` | `configs/models/gpt2-6m.yaml` | Architecture YAML. |
| `--pretrain_config` | `configs/pretraining.yaml` | Hyperparameter YAML. |
| `--output_dir` | `outputs/pretrain` | Best checkpoint written to `<output_dir>/best_model/`. |
| `--max_samples` | none | Limit training samples for a quick test. |
| `--data` | none | Local waypoint-format corpus instead of downloading Atlas. |

**Known blocker:** both reviewed upstream versions call the local tokenizer
`save_pretrained()` before training; it raises `NotImplementedError` because `save_vocabulary`
is missing. A repaired tokenizer and save/reload test are prerequisites.

Intended steps: download the Atlas `pretrain` split → build a taxonomic tokenizer from the corpus →
compute per-token abundance mean/std for z-score ordering → train GPT-2 with next-token prediction
and early stopping → save `best_model/`.

### `configs/pretraining.yaml`

```yaml
training_type: next_token_prediction
taxon_rank: genus              # tokenization rank; changing it means re-pretraining
fallback_to_higher_rank: true  # use the most specific higher rank when genus is absent
max_length: 512
learning_rate: 0.001
warmup_steps: 1000
weight_decay: 0.001
batch_size: 32
num_epochs: 100
patience: 10
eval_steps: 3261
save_steps: 3261
logging_steps: 100
val_split: 0.1
seed: 42
```

### Architectures

All share `model_type: gpt2` and `n_positions: 512`. Per-head dimension is 64 except
`gpt2-6m-mgm.yaml`, where 256 / 8 = 32.

| Config | Layers | Hidden | Heads | ~Params |
| --- | --- | --- | --- | --- |
| `gpt2-6m.yaml` | 8 | 256 | 4 | 6M |
| `gpt2-6m-mgm.yaml` | 8 | 256 | 8 | 6M — matches the MGM baseline architecture |
| `gpt2-10m.yaml` | 8 | 320 | 5 | 10M |
| `gpt2-18m.yaml` | 10 | 384 | 6 | 18M |
| `gpt2-29m.yaml` | 12 | 448 | 7 | 29M |
| `gpt2-45m.yaml` | 14 | 512 | 8 | 45M |
| `gpt2-79m.yaml` | 16 | 640 | 10 | 79M |
| `gpt2-85m-gpt-small.yaml` | 12 | 768 | 12 | 85M — GPT-2 small geometry |
| `gpt2-170m.yaml` | 24 | 768 | 12 | 170M |

Only 6m, 45m, and 170m are published as checkpoints. The rest exist so the paper's scaling study is
reproducible; `gpt2-6m-mgm` isolates the effect of head count against the MGM baseline.

Parameter counts exclude token and positional embeddings, so the Hub's reported sizes are larger
(the 6m checkpoint reports ~10.1M, the 45m ~51.8M).

Pretraining Atlas end to end is a multi-GPU-day job. After resolving serialization, validate the pipeline with a tiny local corpus and architecture
before a full run. `--max_samples` caps rows after `load_dataset`, so it does not bound the Atlas
download size.
