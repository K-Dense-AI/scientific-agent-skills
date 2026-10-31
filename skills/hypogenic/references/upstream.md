# Upstream package, source, CLI, and workflows

Review date: 2026-10-01. Package/source assertions were rechecked against the
verified release wheel, current official metadata, and provider documentation.

## Release and integrity status

The latest stable PyPI artifact is `hypogenic==0.3.5`, uploaded
2025-07-16. PyPI metadata declares Python `>=3.10`, MIT, and Development Status
4 (Beta). Both files are non-yanked:

- wheel: `hypogenic-0.3.5-py3-none-any.whl`, 96,169 bytes,
  SHA-256
  `f4ee8d7fa433cd59c58e0a8fe7df2f481ae29e7465a1b30ccbdac2c216a1b755`;
- sdist: `hypogenic-0.3.5.tar.gz`, 65,423 bytes, SHA-256
  `5e1e5590f3612cb606a669909aab117d66577cf078dd56cae0f4123c5e8c44ae`.

PyPI trusted-publisher attestations identify repository
`ChicagoHAI/hypothesis-generation`, tag `v0.3.5`, commit
`8c3800ccae155e333fac5b530afa8abdaac38300`, and the repository's
`publish-to-pypi.yml` workflow. This is sufficient to recommend a pinned PyPI
install, while still requiring ordinary lockfile/hash controls.

The default `master` commit observed was
`bd37a3129a2f98ee586f545a57b10b59496eedad` (2025-07-17). It is four commits
ahead of the release tag; the changed files add logging/visualization support
and a debug option. The `README.md` and `pyproject.toml` blobs are identical
between `v0.3.5` and that master revision, and the source version remains
`0.3.5`. No newer GitHub release or PyPI version was found on 2026-10-01.

Interpretation: artifact, source tag, metadata, and README provenance align.
The branch has small unreleased logging changes, so do not substitute branch
tip for the release.

## Declared dependency surface

The default artifact declares broad compatible-release ranges around:

- NumPy 1.26.3, pandas 2.1.4, datasets 2.16.1;
- Transformers 4.45.1, PyTorch 2.4.0, Accelerate 0.33.0;
- OpenAI 1.40.3, Anthropic 0.32.0, Redis 5.0.1;
- scikit-learn 1.3.0, matplotlib 3.8.0, PuLP 2.9.0;
- PyYAML 6.0.1 and several document/web packages.

The `dev` extra adds vLLM 0.6.2 and `vllm-flash-attn` 2.6.2. Resolve this in an
isolated environment. The package declaration says Python `>=3.10` but does not
state an upper bound; actual resolver/platform support is constrained by those
older compiled dependencies. PyTorch 2.4.1 still has no CPython 3.13 wheels;
use Python 3.12 for a separately resolved upstream environment. This review
executed the small local tools, task/prompt code, and mocked hosted wrappers;
it did not install the full PyTorch/Transformers/vLLM dependency set.

## Verified import and registry surface

The package root does not export `BaseTask`. The source imports used by its own
examples include:

```python
from hypogenic.tasks import BaseTask
from hypogenic.prompt import BasePrompt
from hypogenic.extract_label import extract_label_register
from hypogenic.LLM_wrapper import llm_wrapper_register
```

These are source-level interfaces in 0.3.5, not a separately versioned public
API contract. Prefer the pinned examples when writing custom code.

Registered model wrapper types:

- `gpt`: OpenAI Python client and chat-completions calls;
- `claude`: Anthropic Python client and Messages calls;
- `huggingface`: local Transformers text-generation pipeline;
- `vllm`: local vLLM generation.

Important local-provider limitation: `hypogenic.LLM_wrapper.__init__` imports
both local wrappers from one module, and that module raises when `vllm` is
absent. The exception is caught, leaving both `huggingface` and `vllm`
unregistered. Thus the base install's CLI advertises both choices, but local
wrapper registration depends on the `dev` path in this release.

The hosted wrappers instantiate `OpenAI()` and `Anthropic()` without an
explicit key, so their API-key environment names are `OPENAI_API_KEY` and
`ANTHROPIC_API_KEY`. The pinned SDKs also honor `OPENAI_BASE_URL` and
`ANTHROPIC_BASE_URL`. Consequently the local policy records an intended
destination; it does not enforce the network endpoint or SDK account settings.

## Hosted request and response contracts

Both wrappers use non-streaming requests; there is no pagination or provider
Batch API here. `batched_generate` means local concurrent individual requests.
The following paths/authentication were checked with the pinned SDKs and an
HTTP mock transport; no authenticated service calls were performed.

| Wrapper | Default request | Authentication | Request / returned value |
| --- | --- | --- | --- |
| `gpt` | `POST https://api.openai.com/v1/chat/completions` | SDK Bearer API key | `model`, chat `messages`, `max_tokens`, `temperature`, `n`; reads `usage.prompt_tokens`, `usage.completion_tokens`, then `choices[0].message.content` |
| `claude` | `POST https://api.anthropic.com/v1/messages` | SDK `x-api-key` and `anthropic-version: 2023-06-01` | Extracts one system message into top-level `system`; sends remaining `messages`, `model`, `max_tokens`, `temperature`; reads only `content[0].text` |

Current [OpenAI Chat Completions documentation](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
marks `max_tokens` deprecated and incompatible with o-series models. HypoGeniC
0.3.5 always supplies it; the presence of `o1` and `o3-mini` in its historical
cost table does not make those models compatible. Newer model IDs and dated
snapshots missing from `MODEL_COSTS` raise `KeyError` **after a successful
request**, so they may incur charges without returning a usable result. The
wrapper discards choices after the first even if `n > 1`; keep `n=1`. Its
current code also assumes usage and a text completion exist, and does not check
truncation, refusal, or tool-only responses.

Current [Anthropic Messages documentation](https://platform.claude.com/docs/en/api/messages/create)
rejects non-default temperature for models released after Opus 4.6. The wrapper
always sends `temperature=1e-5` unless overridden. The documented compatibility
value is `1.0`; omission requires a wrapper change. Verify the exact model and
[deprecation table](https://platform.claude.com/docs/en/about-claude/model-deprecations)
before choosing it. Upgrading a model name alone is not an integration test.

The Claude wrapper removes the system entry from the caller's list with
`pop`, requires a system entry although the API itself does not, and assumes
the first returned block is text. Use fresh/deep-copied messages for every call.
It cannot safely handle thinking/tool/mixed-content responses without an
adapter. Any `BadRequestError`, including a parameter error, returns `None`
instead of its actual cause; the multi-request path then dereferences
`None.content` and crashes. Treat these as failed/abstained predictions, not
negative evidence about a hypothesis; preserve redacted status/error details.

These are limits of the released package. A custom driver must fix and test
the parameter mapping, block parsing, missing/failed responses, endpoint
selection, current pricing, and retry accounting before a paid run. The local
audit/planning tools do not implement such a driver.

## CLI entry points and limitations

`pyproject.toml` declares:

```text
hypogenic_generation = hypogenic_cmd.generation:main
hypogenic_inference  = hypogenic_cmd.inference:main
```

Use their pinned `--help` output as the command contract. Do not copy the old
skill's `--config`, `--method`, `--num_hypotheses`, `--hypotheses`,
`--test_data`, or `--papers` examples; those flags are not present in the
0.3.5 entry-point parsers.

Verified generation options include:

- `--task_config_path`, `--model_name`, `--model_path`, `--model_type`;
- train/validation/test counts and seed;
- bank size, initialization, update, replacement, concurrency, Redis/cache,
  output, restart, and logging options;
- `max_tokens` and `temperature` are accidentally declared as positional
  arguments despite having defaults. Treat them as required by this parser and
  confirm with `--help`.

Verified inference options include:

- `--task_config_path`, `--hypothesis_file`, provider/model options;
- seeds, split counts, validation switch, inference style, adaptive settings,
  cache/Redis, concurrency, logging, token cap, and temperature.

Known source quirks relevant to reproducibility:

- both CLIs call `LoggerConfig.setup_logger(args.log_file, args.log_level)`,
  but its signature is `(level, log_file_path)`: defaults create a file named
  `INFO` and then fail on the `None` logging level. A reviewed driver should
  use the keyword form `setup_logger(level=args.log_level,
  log_file_path=args.log_file)`;
- both CLIs pass `(args.model_name, args.model_path)` to every wrapper. For
  `GPTWrapper` and `ClaudeWrapper`, the second argument is `max_retry`, not a
  model path. Default `None` fails at `range(self.max_retry)`. A reviewed driver
  must pass only the model to hosted constructors and use `path_name=` only
  for local constructors;
- inference asserts `adaptive_num_hypotheses <= bank size` even for default
  inference. Its default of five rejects smaller banks; configure a value no
  larger than the inspected bank;
- generation defaults combine `model_type=gpt` with a Meta-Llama model name;
  defaults are not a safe executable plan;
- importing the generation entry-point module on Python 3.13 emits a
  `SyntaxWarning` for an invalid `\{` escape in one help string;
- the GPT wrapper's embedded cost table has only `gpt-4o-mini`, `gpt-4o`,
  `o1`, and `o3-mini`, and uses direct lookup. It is not current pricing or
  general model support;
- generation has a TODO instead of reporting session cost;
- the inference entry point computes per-seed accuracy/F1 but does not append
  them to its averaging lists, so its final averaged log values are not
  reliable;
- the README says new-task command-line support is planned for a later release;
- the README's generic task snippet swaps validation/test filenames, while
  pinned dataset configs use distinct, correctly named split files.

These mismatches are why this skill provides planning/auditing tools but does
not auto-run the upstream CLI.

## Task and dataset support

The label-extractor registry contains handlers for:

- default, AI-generated-content detection, headline comparison, deceptive
  reviews, retweets, shoe color, Yelp rating, persuasive pairs, Dreaddit stress,
  election, preference, and admission tasks.

A registered label parser is not proof of complete end-to-end task support.
The current HypoBench dataset repository covers seven real-world task families
(deception, AI-content detection, persuasive arguments, mental stress,
headline engagement, retweets, and paper citations) plus synthetic task
families and variants. Use the config included with the exact pinned dataset
revision.

Dataset JSON is column-oriented: every field maps to a list and all lists must
have equal length. `BaseTask` joins each configured path to the task config's
directory, samples rows, and returns pandas data frames. Train, validation,
test files remain distinct only if the config preserves them. `get_data` returns
`(train, test, validation)`, not train/validation/test order. Its `seed` argument
seeds the held-out sampling; seed Python randomness before calling it when
reproducing training samples. With `use_ood=True`, `BaseTask` replaces **both**
validation and test paths with the same OOD path. Do not use that mode for
validation selection followed by an independent OOD test claim.

## Generation, outputs, and evaluation

Default HypoGeniC:

1. creates candidate hypotheses from batches of labeled training examples;
2. evaluates hypotheses through LLM-based label inference;
3. updates accuracy/reward/visit statistics;
4. generates replacements after accumulated difficult examples;
5. writes intermediate/final banks.

The saved bank is a JSON object keyed by hypothesis text. Each value serializes
`SummaryInformation`:

```json
{
  "hypothesis": "candidate text",
  "acc": 0.0,
  "reward": 0.0,
  "num_visits": 0,
  "correct_examples": []
}
```

Literature/HypoRefine examples additionally preprocess supplied PDFs, summarize
papers, refine data/literature hypotheses, and create HypoRefine,
literature-only, and union banks. This is an example-script workflow rather
than a `--method hyporefine` flag on the packaged generation entry point.

Default inference sorts the bank by stored accuracy, applies the best entry to
the selected split, and returns prediction/label lists internally. The CLI
logs per-seed accuracy, F1, and wrong indices; it does not define the strict
result artifact used by this skill. `assets/result.example.json` is a
skill-local, model-free interchange schema.

The upstream papers evaluate classification utility, human decision support,
generalization, and hypothesis-discovery behavior. Those evaluations do not
turn generated text into causal or experimentally confirmed scientific
evidence.

## Verification boundary for this review

The unchanged release wheel was downloaded and SHA-256 checked. Both CLI
`--help` paths executed with no site packages. The bundled task template rendered
through the real release `BaseTask`/`BasePrompt` using synthetic data, pandas
2.1.4 and PyYAML 6.0.3. Hosted wrapper paths used OpenAI 1.40.3, Anthropic
0.32.0, HTTPX 0.27.2 and mock HTTP responses; import-only PyTorch, Transformers
and scikit-learn surfaces were stubbed. These checks reproduced the failures
above but do not demonstrate live model availability, account permissions,
scientific accuracy, GPU/local generation, Redis service behavior or a complete
upstream environment installation.
