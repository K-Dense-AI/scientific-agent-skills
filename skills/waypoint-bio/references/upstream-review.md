# Upstream verification and compatibility

Reviewed 2026-10-01. This skill targets the published `waypoint-bio==1.0.2` wheel;
GitHub main still identifies itself as 1.0.4 at
`f45eee6d07a480bfc90f84ab8082bbc969dec15d`. These are different distributions.

## Verified local behavior

Small native checks used Python 3.12, Torch 2.14.1, Transformers 4.57.6, PEFT 0.18.1,
Datasets 5.0.1, huggingface-hub 0.36.2, pandas 3.0.6 and PyArrow 25.0.1. They exercise
synthetic taxa, a randomly initialized 16-dimensional GPT-2, pooling/heads, the language-model
collator, scoring, CLI parsing, and local matrix preparation/embedding. The Compass download
interface was checked with synthetic Dataset-shaped mocks for all eight task definitions.
These checks do not establish pretrained prediction quality or reproduce Compass results.

| Interface | Finding and consequence |
| --- | --- |
| `TaxonomicTokenizer.save_pretrained` | The package class lacks `save_vocabulary`; native saving raises `NotImplementedError`. Both reviewed versions have identical tokenizer source. `pretrain` hits this before training; local-tokenizer `finetune` export also needs this resolved. Test vocabulary save/reload before any expensive run. The gated Hub tokenizer implementation was not downloaded, so this finding is scoped to the package class. |
| `load_waypoint_dataframe` | The CSV/TSV parser only parses object-dtype columns. With pandas 3 the list cells stay strings; the reader also does not restore the sample-ID index. Use parquet. |
| `TrainingArguments` | Pretraining passes `logging_dir`, removed in Transformers 5. The package has no upper dependency bound; the documented compatible stack therefore retains Transformers 4.57.6. |
| `finetune` exports | PyPI 1.0.2 does not merge PEFT adapters or write training logs/prediction CSVs. GitHub 1.0.4 adds those. An adapter-only export requires PEFT and its original base model, not plain `AutoModel`. |
| Benchmark training budget | The shipped YAML says one epoch; the paper describes up to 300 with early stopping. Those are different protocols. |
| Benchmark seeding | `--seed` initializes Torch/NumPy once, but `TrainingArguments` receives no seed and uses its own default 42. The YAML seed is unused. For independent runs, explicitly wire the seed into the trainer in a reviewed local change. |
| Token ordering | Unknown entries are removed, but entries mapping to the same genus are not aggregated. Statistics use observed entries without absent-sample zeros. Preserve and report the profiler/aggregation convention. |
| Statistics loading | `try_load_token_std_means` catches all Hub errors and silently returns `None`, changing ordering to raw abundance. Require the expected statistics file when comparing runs. |
| `--max_samples` | Applied after dataset loading; does not cap bytes downloaded. Use a tiny local corpus for a bounded check. |

## Hub interfaces

The three checkpoints and two datasets currently have auto-approved access gates. Public model
and dataset cards/metadata were read without authentication; file access requires accepting the
individual repository conditions and a read token. No gated artifacts, pretrained weights,
scientific inference, uploads, or access requests were performed for this review.

| Repository | Hub revision checked |
| --- | --- |
| `outpost-bio/Waypoint-6m` | `2f14877d9ed09b7354dbd205bd426d94da3d616c` |
| `outpost-bio/Waypoint-45m` | `1664ab5ec88b4bdf571f2512968f99dc222ce0ac` |
| `outpost-bio/Waypoint-170m` | `eb7d87184a73d5c0475379c408c7412cd0514678` |
| `outpost-bio/Atlas` | `9dad400edb9e4f1e483a2f9021208c16f694aec2` |
| `outpost-bio/Compass` | `370f857265cab6756bb06c72451c083b13e2418f` |

Model loading uses `AutoModel.from_pretrained`; taxonomic tokenizers need reviewed custom code
or the installed package class. Dataset loading uses `load_dataset(repo_id, config, split=...,
revision=...)`. Atlas has `pretrain`/`benchmark`; Compass configurations are `mgnify-biomes`,
`handuo`, `mastrorilli`, and `roswall`, each with `train`/`validation`/`test`. Public card schemas
confirm the columns and row counts in this skill; no row-content validation was performed.
The upstream CLI has no revision arguments and hardcodes dataset repository IDs internally.
Use explicit pinned Python loaders or a reviewed local change when dataset reproducibility is
required. Do not infer a hosted inference API from a Hub model identifier.

## Primary sources

- [Published PyPI release and dependency metadata](https://pypi.org/project/waypoint-bio/1.0.2/).
- [Reviewed GitHub source](https://github.com/Outpost-Bio/waypoint/tree/f45eee6d07a480bfc90f84ab8082bbc969dec15d).
- [Waypoint 6M model card](https://huggingface.co/outpost-bio/Waypoint-6m),
  [45M model card](https://huggingface.co/outpost-bio/Waypoint-45m),
  [170M model card](https://huggingface.co/outpost-bio/Waypoint-170m).
- [Atlas card and schema](https://huggingface.co/datasets/outpost-bio/Atlas),
  [Compass card and schema](https://huggingface.co/datasets/outpost-bio/Compass).
- [Hub downloads and revision pinning](https://huggingface.co/docs/huggingface_hub/guides/download).
- [Transformers Trainer](https://huggingface.co/docs/transformers/main_classes/trainer).
- [Treloar, Ur-Rehman and Yang, paper v2](https://www.biorxiv.org/content/10.64898/2026.05.02.722381v2.full).
  Full text was retrieved through the extraction tool after direct browsing returned HTTP 403.
