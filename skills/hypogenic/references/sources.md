# Dated official sources and verification

Review date: **2026-10-01**. The July 2026 review remains historical evidence;
package, source, dataset revisions, provider contracts and the local tools were
rechecked for this refresh. Source inspection and mock transport tests are not
authenticated provider or scientific validation.

## Release and implementation

- [PyPI package](https://pypi.org/project/hypogenic/) and
  [official metadata](https://pypi.org/pypi/hypogenic/json): latest release
  remains 0.3.5, released 2025-07-16, Python >=3.10, beta classifier, MIT,
  dependencies, artifact hashes and trusted-publisher provenance. The 96,169-byte
  wheel was downloaded and its SHA-256 matched the metadata.
- [Official repository](https://github.com/ChicagoHAI/hypothesis-generation),
  [latest release](https://api.github.com/repos/ChicagoHAI/hypothesis-generation/releases/latest),
  and [default branch](https://api.github.com/repos/ChicagoHAI/hypothesis-generation/commits/master):
  v0.3.5 and master `bd37a3129a2f98ee586f545a57b10b59496eedad` remain unchanged.
- [Pinned release source](https://github.com/ChicagoHAI/hypothesis-generation/tree/8c3800ccae155e333fac5b530afa8abdaac38300)
  and [pyproject](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/pyproject.toml):
  source/API review targets this exact version rather than an unpinned branch.
- [Generation CLI](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic_cmd/generation.py),
  [inference CLI](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic_cmd/inference.py),
  and [logger](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic/logger_config.py):
  parser flags and positional arguments, early help exit, swapped logger and
  hosted-wrapper constructor arguments, small-bank assertion and averaging bug.
- [Task loader](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic/tasks.py)
  and [prompt implementation](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic/prompt.py):
  config fields, column JSON, sampling, return order, OOD aliasing, and template
  substitution. The shipped template rendered locally with synthetic examples.
- [Model wrappers](https://github.com/ChicagoHAI/hypothesis-generation/tree/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic/LLM_wrapper):
  SDK calls, cost table, local registration, model loading, retries, message
  mutation, block assumptions and error behavior. Executed hosted paths used
  mock HTTP responses and stubbed heavy import-only dependencies.
- [Output serializer](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic/algorithm/update/base.py)
  and [SummaryInformation](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic/algorithm/summary_information.py):
  JSON hypothesis-bank structure and stored statistics.
- [Redis cache](https://github.com/ChicagoHAI/hypothesis-generation/blob/8c3800ccae155e333fac5b530afa8abdaac38300/hypogenic/LLM_cache.py):
  cache keys, prompt/response storage and pickle serialization. No Redis server
  was started or contacted.
- [PyTorch 2.4.1 release metadata](https://pypi.org/pypi/torch/2.4.1/json):
  no CPython 3.13 wheels; the upstream package's `torch~=2.4.0` range still
  prevents the default repository interpreter from installing its full stack.
- [PyYAML release metadata](https://pypi.org/pypi/PyYAML/json) and
  [parser documentation](https://pyyaml.org/wiki/PyYAMLDocumentation): reviewed
  local parser pin advanced to 6.0.3. Valid YAML and rejection of duplicate keys,
  aliases, anchors, tags, dates and malformed input were exercised locally.

## Datasets

- [HypoBench GitHub repository](https://github.com/ChicagoHAI/HypoBench-datasets)
  and [default commit](https://api.github.com/repos/ChicagoHAI/HypoBench-datasets/commits/main):
  remain at `7e4bbc341ee90b7efaa607f67a81543cd68cdf2e`.
- [Pinned dataset tree](https://github.com/ChicagoHAI/HypoBench-datasets/tree/7e4bbc341ee90b7efaa607f67a81543cd68cdf2e):
  the deceptive-review config and train/validation/test JSON hashes were
  rechecked; 800/300/500 rows and three cross-split duplicate groups reproduced.
  The optional OOD file was acquired only to verify the task's path contract.
- [Official Hugging Face publication](https://huggingface.co/datasets/ChicagoHAI/HypoGeniC-datasets)
  and [Hub metadata](https://huggingface.co/api/datasets/ChicagoHAI/HypoGeniC-datasets):
  revision remains `613860dcbcda9e522a6163ee9edf78c261ebe4bb`.

## Provider contracts and privacy

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create):
  request and response fields, legacy `max_tokens`, choice/usage semantics and
  incompatibility with o-series models. The pinned OpenAI 1.40.3 SDK was exercised
  through HTTPX MockTransport; it sent the documented route and Bearer header.
- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
  and [deprecations](https://developers.openai.com/api/docs/deprecations):
  endpoint/model-specific storage and availability must be checked at execution
  time. This review did not query an authenticated model catalog or account.
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create):
  top-level system field, content-block response, version header, token parameter,
  and current temperature restriction. Anthropic 0.32.0 sent the expected route,
  `x-api-key` and API-version header in mock transport tests.
- [Anthropic model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations):
  retired model IDs and rejection of non-default temperature on newer models.
- [Anthropic API retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)
  and [commercial retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data):
  standard deletion policy, exceptions, ZDR eligibility, and covered-model
  30-day requirements. No account-specific arrangement was verified.
- [OpenAI 1.40.3 client source](https://github.com/openai/openai-python/blob/v1.40.3/src/openai/_client.py)
  and [Anthropic 0.32.0 client source](https://github.com/anthropics/anthropic-sdk-python/blob/v0.32.0/src/anthropic/_client.py):
  automatic credential lookup and base-URL environment overrides. These were
  also inspected in the installed pinned SDKs; no credential values were read.

## Local wrappers and scientific scope

- [Transformers 4.45.2 pipelines](https://huggingface.co/docs/transformers/v4.45.2/en/main_classes/pipelines)
  and [installation/offline mode](https://huggingface.co/docs/transformers/v4.45.2/en/installation):
  model/path loading and offline configuration compatible with the pinned
  4.45.x line. No model weights or local inference were tested.
- [vLLM 0.6.2 LLM API](https://docs.vllm.ai/en/v0.6.2/dev/offline_inference/llm.html):
  offline model, sampling and generation interfaces; reviewed alongside the
  package wrapper, not validated on GPU hardware.
- [Hypothesis Generation with Large Language Models](https://aclanthology.org/2024.nlp4science-1.10/):
  Zhou et al., NLP4Science 2024, DOI `10.18653/v1/2024.nlp4science-1.10`;
  data-driven candidate generation and classification evaluations.
- [Literature Meets Data](https://arxiv.org/abs/2410.17309): Liu et al.,
  version 3 dated 2025-01-08; HypoRefine and literature/data integration.
- [HypoBench](https://arxiv.org/abs/2504.11524): Liu et al., version 2
  dated 2026-02-10; seven real-world tasks, five synthetic families and 194
  datasets. Publication metadata does not establish scientific validity of an
  individual generated hypothesis.
- [HypoBench OpenReview record](https://openreview.net/forum?id=cizEoSePyT):
  current retrieval reached a browser challenge. No current review/acceptance
  status is asserted from that response.
