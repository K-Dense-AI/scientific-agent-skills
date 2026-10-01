# Review evidence and boundaries

Reviewed 2026-10-01. The catalog fetcher is standard-library only. Resource examples
were checked with Python 3.13, Transformers 5.18.0, Torch 2.14.1, Datasets 5.0.1,
Hub 1.33.0 and Gradio Client 2.7.1. Datasets 5.0.1 rejects Hub 2.0 through its
`<2.0` dependency bound; the combined workflow therefore uses Hub 1.33.0.

## Catalog contract

Public unauthenticated GET requests retrieved and parsed
[the index](https://huggingscience.co/llms.txt),
[the full catalog](https://huggingscience.co/llms-full.txt),
all 17 [topic routes](https://huggingscience.co/topics/biology.md), and
[the RSS feed](https://huggingscience.co/feed.xml).
The full document had 1,329 H3 occurrences representing 544 unique section/URL
pairs because topics overlap; the feed contained 50 items. These are snapshots,
not stable counts or evidence of resource quality. The helper has no auth,
request body, server-side search, or pagination; filtering/search are local.

## Hub and dataset contracts

[Hub API](https://huggingface.co/docs/hub/api) and
[HfApi reference](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api)
were checked against actual public responses. Read-only routes used were
`GET /api/models/{repo}`, `/api/datasets/{repo}`, `/api/spaces/{repo}` and
`/api/spaces?author=hugging-science&limit=100` at `huggingface.co`.
Individual metadata returns an object; lists paginate with Link headers, which
the SDK iterator follows. Public tests explicitly suppressed token use. Gated
repositories may expose metadata while returning 401 for card/artifact access;
401 does not establish that a repository was deleted.

The provider check uses `GET /api/models/{repo}?expand=inferenceProviderMapping`.
Its raw JSON object becomes a **list** of `InferenceProviderMapping` records in
the tested SDK. ESM2-650M had a live `hf-inference` mapping for `fill-mask`;
Evo2-40B had no mappings. The fill-mask request/typed-result contract was exercised
with a mocked transport, not an authenticated provider call.

[Datasets loading](https://huggingface.co/docs/datasets/loading),
[streaming](https://huggingface.co/docs/datasets/stream), and
[5.0.1 loader source](https://github.com/huggingface/datasets/blob/5.0.1/src/datasets/load.py)
confirm iterable behavior and removal of dataset-script execution.
The live OAS metadata helpers returned configs `default`, `paired` and paired
split `train`. Synthetic CSV tests ran the documented lazy filter and bounded
materialization, including failure on absent `meta_Species`.

## Model and resource cards

Cards/manifests were inspected for all named flagship repository IDs. Key fixes:

- [Evo2 official runtime](https://github.com/ArcInstitute/evo2): native Evo2/Vortex,
  BF16/FP8 and hardware distinctions; 7B is not an instruction-tuned variant.
  [40B card](https://huggingface.co/arcinstitute/evo2_40b) and
  [7B card](https://huggingface.co/arcinstitute/evo2_7b) point to that runtime.
- [ESM2-650M](https://huggingface.co/facebook/esm2_t33_650M_UR50D),
  [ESM2-35M](https://huggingface.co/facebook/esm2_t12_35M_UR50D), and
  [ESM API](https://huggingface.co/docs/transformers/model_doc/esm): native
  Transformers support; tiny random CPU model tested special/padding exclusion
  and equivalence of a short sequence alone versus in a padded batch.
- [TEDDY](https://huggingface.co/Merck/TEDDY): model/code repository, 116 million
  training cells; [STACK](https://huggingface.co/arcinstitute/Stack-Large): its own
  package/checkpoints, not a generic AutoModel guarantee.
- [OAS](https://huggingface.co/datasets/opig/OAS): `meta_Species` and paired CSVs;
  [OpenGenome2](https://huggingface.co/datasets/arcinstitute/opengenome2): raw
  multipart FASTA plus complete JSONL shards, with pretraining-specific content.
- [NatureLM-audio](https://huggingface.co/EarthSpeciesProject/NatureLM-audio) and
  [AVEX checkpoint](https://huggingface.co/EarthSpeciesProject/esp-aves2-sl-beats-all):
  dedicated loaders/preprocessing, not generic provider availability.
- [AQAffinity](https://huggingface.co/SandboxAQ/AQAffinity) metadata is public and
  gated; its raw card and [SAIR card](https://huggingface.co/datasets/SandboxAQ/SAIR)
  returned 401 anonymously. Access and execution remain unverified.
- [LeMat-Bulk](https://huggingface.co/datasets/LeMaterial/LeMat-Bulk),
  [breast ultrasound checkpoint](https://huggingface.co/hugging-science/breast-cancer-detector-2),
  [Kimina-Prover](https://huggingface.co/AI-MO/Kimina-Prover-72B), and
  [Legacy Survey release](https://huggingface.co/datasets/hugging-science/mmu_legacysurvey_dr10_south_21)
  were checked as discovery pointers; the astronomy release uses HATS/Parquet.
  No claim of clinical, proof, affinity or structural accuracy was tested.

## Spaces and verification limits

[Gradio Client 2.7.1 source](https://github.com/gradio-app/gradio/blob/gradio_client%402.7.1/client/python/gradio_client/client.py)
verifies `token`, separate endpoint-scoped `oauth_token`, `view_api`, prediction,
queue and download behavior. Local `handle_file` tests confirm file marking only.
The current [BoltzGen demo source](https://huggingface.co/spaces/hugging-science/BoltzGen_Demo/blob/main/app.py)
at commit `829bdf3baf7ac85f252fea917028a813f4d0aebd` must be rechecked if the app changes.
Its runtime was `PAUSED`; public `/config` and `/gradio_api/info` returned 503.
The five-input design contract and status-string return are source verified only;
no endpoint name or downloadable artifact has been validated against a live job.
The old lower-case demo ID and old heatmap ID returned 401; live organization
metadata identified `BoltzGen_Demo` and Docker `science-release-map` instead.

No large dataset shard, pretrained model weight, native Evo2/CUDA runtime,
authenticated inference, upload, moderation action or design job was executed.
Use the live application schema before any of those operations.
