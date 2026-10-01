# OpenRouter image model reference

Reviewed 2026-09-30 using the public [image catalogue](https://openrouter.ai/api/v1/images/models)
and all 55 corresponding `/api/v1/images/models/{model_id}/endpoints` responses. These are
read-only metadata checks, not generation benchmarks or evidence that a paid request will succeed.

```bash
python scripts/generate_image.py --list-models
python scripts/generate_image.py --list-models gemini
python scripts/generate_image.py --model-info openai/gpt-image-2.5-sunburst
```

The first endpoint returns a `data` array and each model's capability **union**. Endpoint discovery
returns an object with `id` and `endpoints`; there is no documented pagination for either list.
The CLI additionally checks that at least one endpoint accepts the whole parameter combination.
Account access, provider availability, moderation and undeclared cross-parameter constraints still
require a real request. `--model-info` prints each provider's definitive capabilities and prices.

## Catalogue snapshot

`n` and `refs` are inclusive ranges. A dash is unsupported, not unlimited; omitting `n` uses the
provider default. `n` is an upper bound and can produce fewer images. A positive `refs` minimum
means text-only generation is not supported. Prices below are **output only**, not total cost.

| Model | n | refs | stream | Output rates |
| --- | --- | --- | --- | --- |
| `black-forest-labs/flux.2-flex` | 1–1 | 0–8 | no | $0.06/megapixel |
| `black-forest-labs/flux.2-klein-4b` | 1–1 | 0–4 | no | $0.014/megapixel |
| `black-forest-labs/flux.2-max` | 1–1 | 0–8 | no | $0.07/megapixel |
| `black-forest-labs/flux.2-pro` | 1–1 | 0–8 | no | $0.03/megapixel |
| `bytedance-seed/seedream-4.5` | 1–10 | 0–14 | no | $0.04/image |
| `bytedance-seed/seedream-5-0-lite` | 1–4 | 0–14 | no | $0.035/image |
| `bytedance-seed/seedream-5-0-pro` | 1–1 | 0–14 | no | $0.045/image; $0.09/image (high_resolution) |
| `google/gemini-2.5-flash-image` | 1–1 | 0–3 | no | $0.000054/token; $0.000015/token; $0.00003/token |
| `google/gemini-3-pro-image` | 1–1 | 0–14 | no | $0.00012/token |
| `google/gemini-3-pro-image-preview` | 1–1 | 0–14 | no | $0.00006/token; $0.00012/token |
| `google/gemini-3.1-flash-image` | 1–1 | 0–14 | no | $0.00006/token |
| `google/gemini-3.1-flash-image-preview` | 1–1 | 0–14 | no | $0.00006/token |
| `google/gemini-3.1-flash-lite-image` | 1–1 | 0–14 | no | $0.00003/token |
| `inclusionai/ming-image-0.1-design` | 1–1 | 0–0 | no | $0/token |
| `inclusionai/ming-image-0.1-design-layer` | 1–1 | 1–1 | no | $0/token |
| `krea/krea-2-large` | — | 0–1 | no | not published |
| `krea/krea-2-medium` | — | 0–1 | no | not published |
| `krea/krea-2-medium-turbo` | — | 0–1 | no | not published |
| `meta/muse-image` | — | — | no | not published |
| `microsoft/mai-image-2.5` | 1–1 | 0–1 | no | $0.000047/token |
| `microsoft/mai-image-2.5-pro` | 1–1 | 0–1 | no | $0.000108/token |
| `microsoft/mai-image-2.6` | 1–1 | 0–5 | no | $0.000038/token |
| `microsoft/mai-image-2.6-flash` | 1–1 | 0–5 | no | $0.000019/token |
| `openai/gpt-5-image` | 1–10 | 0–16 | yes | $0.00004/token |
| `openai/gpt-5-image-mini` | 1–10 | 0–16 | yes | $0.000008/token |
| `openai/gpt-5.4-image-2` | 1–10 | 0–16 | yes | $0.00003/token |
| `openai/gpt-image-1` | 1–10 | 0–16 | yes | $0.00004/token |
| `openai/gpt-image-1-mini` | 1–10 | 0–16 | yes | $0.000008/token |
| `openai/gpt-image-2` | 1–10 | 0–16 | yes | $0.00003/token |
| `openai/gpt-image-2.5-flare` | 1–10 | 0–16 | yes | $0.00003/token |
| `openai/gpt-image-2.5-sunburst` | 1–10 | 0–16 | yes | $0.00003/token |
| `qwen/qwen-image-3` | 1–6 | 0–4 | no | $0.03/image (1k); $0.03/image (2k) |
| `qwen/qwen-image-3-pro` | 1–6 | 0–4 | no | $0.04/image (1k); $0.075/image (2k) |
| `recraft/recraft-v3` | 1–6 | 0–1 | no | $0.04/image |
| `recraft/recraft-v4` | 1–6 | 0–1 | no | $0.04/image |
| `recraft/recraft-v4-pro` | 1–6 | 0–1 | no | $0.25/image |
| `recraft/recraft-v4-pro-vector` | 1–6 | 0–1 | no | $0.3/image |
| `recraft/recraft-v4-styles` | 1–6 | 1–10 | no | $0.035/image |
| `recraft/recraft-v4-styles-pro` | 1–6 | 1–10 | no | $0.1/image |
| `recraft/recraft-v4-styles-pro-vector` | 1–6 | 1–10 | no | $0.12/image |
| `recraft/recraft-v4-styles-vector` | 1–6 | 1–10 | no | $0.05/image |
| `recraft/recraft-v4-vector` | 1–6 | 0–1 | no | $0.08/image |
| `recraft/recraft-v4.1` | 1–6 | 0–1 | no | $0.035/image |
| `recraft/recraft-v4.1-flash` | 1–6 | — | no | $0.007/image |
| `recraft/recraft-v4.1-pro` | 1–6 | 0–1 | no | $0.21/image |
| `recraft/recraft-v4.1-pro-vector` | 1–6 | 0–1 | no | $0.3/image |
| `recraft/recraft-v4.1-utility` | 1–6 | 0–1 | no | $0.035/image |
| `recraft/recraft-v4.1-utility-pro` | 1–6 | 0–1 | no | $0.21/image |
| `recraft/recraft-v4.1-vector` | 1–6 | 0–1 | no | $0.08/image |
| `sourceful/riverflow-v2-fast` | 1–1 | 0–4 | no | $0.02/image; $0.04/image (2k) |
| `sourceful/riverflow-v2-pro` | 1–1 | 0–10 | no | $0.15/image; $0.15/image (2k); $0.33/image (4k) |
| `sourceful/riverflow-v2.5-fast` | 1–1 | 0–4 | no | $0.019/image; $0.021/image (2k) |
| `sourceful/riverflow-v2.5-pro` | 1–1 | 0–10 | no | $0.13/image; $0.15/image (2k); $0.17/image (4k) |
| `x-ai/grok-imagine-image-2.0` | 1–1 | 0–3 | no | $0.04/image (low_1k); $0.06/image (low_2k); $0.06/image (medium_1k); $0.08/image (medium_2k) |
| `x-ai/grok-imagine-image-quality` | 1–1 | 0–3 | no | $0.05/image (1k); $0.07/image (2k) |

`meta/muse-image` was listed but returned no provider endpoints: catalogue membership does not
establish availability. Krea returned empty pricing arrays. Ming's zero published rates are not a
promise of permanently free generation. Gemini 2.5 and Gemini 3 Pro Preview offer multiple
endpoints/tiers with different prices; inspect the endpoint and routing tag instead of assuming
the lowest rate. Gemini 3 Pro's Vertex endpoint advertises only 1K/2K although its model union
includes 4K through AI Studio.

Input charges matter: Riverflow v2 reports $0.20/reference and $0.03/font; Seedream 5.0 Pro
reports $0.003/input image; Grok reports $0.01/input image. OpenAI and MAI advertise input token
rates. Recraft Styles charges $0.005/request for the input-reference line. Inspect every pricing
line and its `billable`, `unit`, and optional `variant`; do not multiply a token or megapixel rate
as if it were per image. The discovery schema supplies variant labels but does not always explain
how they map to a particular request (for example Seedream Pro's `high_resolution`).

## Allowed values

This table records the full advertised value sets for the CLI's format, size-tier, quality and
background knobs. `seed` is supported when present in discovery; a boolean capability descriptor
means support, **not** that the seed request value should be boolean. Send an integer seed.

| Model | resolution | output_format | quality | background | seed |
| --- | --- | --- | --- | --- | --- |
| `black-forest-labs/flux.2-flex` | — | png, jpeg | — | — | yes |
| `black-forest-labs/flux.2-klein-4b` | — | png, jpeg | — | — | yes |
| `black-forest-labs/flux.2-max` | — | png, jpeg | — | — | yes |
| `black-forest-labs/flux.2-pro` | — | png, jpeg | — | — | yes |
| `bytedance-seed/seedream-4.5` | 1K, 2K, 4K | — | — | — | yes |
| `bytedance-seed/seedream-5-0-lite` | 2K, 4K | — | — | — | yes |
| `bytedance-seed/seedream-5-0-pro` | 1K, 2K | — | — | — | yes |
| `google/gemini-2.5-flash-image` | — | — | — | — | — |
| `google/gemini-3-pro-image` | 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3-pro-image-preview` | 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3.1-flash-image` | 512, 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3.1-flash-image-preview` | 512, 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3.1-flash-lite-image` | 1K | — | — | — | — |
| `inclusionai/ming-image-0.1-design` | — | png, jpeg, webp | — | — | — |
| `inclusionai/ming-image-0.1-design-layer` | — | png, webp | — | — | — |
| `krea/krea-2-large` | 1K | — | — | — | yes |
| `krea/krea-2-medium` | 1K | — | — | — | yes |
| `krea/krea-2-medium-turbo` | 1K | — | — | — | yes |
| `meta/muse-image` | — | — | — | — | — |
| `microsoft/mai-image-2.5` | — | — | — | — | — |
| `microsoft/mai-image-2.5-pro` | — | — | — | — | — |
| `microsoft/mai-image-2.6` | — | — | — | — | — |
| `microsoft/mai-image-2.6-flash` | — | — | — | — | — |
| `openai/gpt-5-image` | — | — | auto, low, medium, high | auto, transparent, opaque | — |
| `openai/gpt-5-image-mini` | — | — | auto, low, medium, high | auto, transparent, opaque | — |
| `openai/gpt-5.4-image-2` | — | — | auto, low, medium, high | auto, opaque | — |
| `openai/gpt-image-1` | — | — | auto, low, medium, high | auto, transparent, opaque | — |
| `openai/gpt-image-1-mini` | — | — | auto, low, medium, high | auto, transparent, opaque | — |
| `openai/gpt-image-2` | — | — | auto, low, medium, high | auto, opaque | — |
| `openai/gpt-image-2.5-flare` | — | — | auto, low, medium, high, xhigh, max | auto, transparent, opaque | — |
| `openai/gpt-image-2.5-sunburst` | — | — | auto, low, medium, high, xhigh, max | auto, transparent, opaque | — |
| `qwen/qwen-image-3` | 1K, 2K | — | — | — | yes |
| `qwen/qwen-image-3-pro` | 1K, 2K | — | — | — | yes |
| `recraft/recraft-v3` | — | — | — | — | — |
| `recraft/recraft-v4` | — | — | — | — | — |
| `recraft/recraft-v4-pro` | — | — | — | — | — |
| `recraft/recraft-v4-pro-vector` | — | svg | — | — | — |
| `recraft/recraft-v4-styles` | — | — | — | — | — |
| `recraft/recraft-v4-styles-pro` | — | — | — | — | — |
| `recraft/recraft-v4-styles-pro-vector` | — | svg | — | — | — |
| `recraft/recraft-v4-styles-vector` | — | svg | — | — | — |
| `recraft/recraft-v4-vector` | — | svg | — | — | — |
| `recraft/recraft-v4.1` | — | — | — | — | — |
| `recraft/recraft-v4.1-flash` | — | — | — | — | — |
| `recraft/recraft-v4.1-pro` | — | — | — | — | — |
| `recraft/recraft-v4.1-pro-vector` | — | svg | — | — | — |
| `recraft/recraft-v4.1-utility` | — | — | — | — | — |
| `recraft/recraft-v4.1-utility-pro` | — | — | — | — | — |
| `recraft/recraft-v4.1-vector` | — | svg | — | — | — |
| `sourceful/riverflow-v2-fast` | 1K, 2K, 4K | — | — | — | — |
| `sourceful/riverflow-v2-pro` | 1K, 2K, 4K | — | — | — | — |
| `sourceful/riverflow-v2.5-fast` | 1K, 2K | jpeg | — | auto, transparent, opaque | — |
| `sourceful/riverflow-v2.5-pro` | 1K, 2K, 4K | png, jpeg, webp | — | auto, transparent, opaque | — |
| `x-ai/grok-imagine-image-2.0` | 1K, 2K | — | low, medium | — | — |
| `x-ai/grok-imagine-image-quality` | 1K, 2K | — | — | — | — |

The generic guide's OpenAI example includes `output_format`, but current OpenAI endpoint discovery
does not advertise it. The helper follows discovery and rejects it unless preflight is explicitly
bypassed. Recraft vector models now advertise `output_format: svg`; use that value only where
listed. Riverflow Fast advertises both JPEG-only output and transparent backgrounds: the helper
rejects their explicit combination, because JPEG has no alpha channel. Validate actual output
when requesting transparency with an omitted format too.

### Aspect ratios

Read `--model-info` for the complete enum. Several important boundaries:

- GPT Image 1, 1 Mini, GPT-5 Image and Mini: `1:1`, `3:2`, `2:3`, `auto`.
- GPT Image 2, 2.5 Flare/Sunburst and GPT-5.4 Image 2 additionally accept `4:3`, `3:4`,
  `16:9`, `9:16`, `21:9`.
- Regular Recraft v3/v4/v4.1: `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `auto`.
  Recraft Styles also accepts `2:1`, `1:2`, `3:2`, `2:3`, `5:4`, `4:5`.
- Gemini 3.1 Flash/Flash Lite include extreme ratios `1:4`, `1:8`, `4:1`, `8:1`;
  Gemini 3 Pro and 2.5 Flash do not.
- Krea accepts `1:1`, `4:3`, `3:2`, `16:9`, `4:5`, `2:3`, `9:16` and no `auto`.

The CLI has no `--size` flag. Direct Image API requests can use `size` as a tier (`2K`) or explicit
pixels (`2048x2048`); explicit pixels override normalization, and contradictory resolution/aspect
settings cause 400 errors. A `resolution` tier is not a promise of exact pixel dimensions.

## Provider options and routing

[The Image API guide](https://openrouter.ai/docs/guides/overview/multimodal/image-generation)
documents `provider.only`, `order`, `ignore`, `sort` and `allow_fallbacks`. Use an endpoint's
`provider_tag` for routing; a null tag means provider-level routing is unavailable. Options use the
separate `provider_slug` key under `provider.options`. The helper prints both but does not expose
routing/options flags. Do not put passthrough options at the request top level.

Current passthrough sets differ even within a family:

- Regular Recraft: `style`, `controls`, `text_layout`; Flash: `controls` only;
  Styles: `style_id`, `style_match`, `controls`, `random_seed`.
- Krea: `styles`, `moodboards`, `image_style_references`, `creativity`, `intensity`, `complexity`,
  `movement`, `strength`.
- OpenAI: `moderation`; Gemini: `cachedContent`; Riverflow: `font_inputs`.
- MAI 2.6: `web_grounding`; FLUX: `steps`, `guidance`, `safety_tolerance`.

An allowed key does not validate nested types, option values, or model/provider restrictions.

## Response, streaming and billing

Generation uses authenticated `POST https://openrouter.ai/api/v1/images` with a Bearer API key and
JSON `model`/`prompt`. References use `input_references[].image_url.url` plus `type: image_url`,
with HTTP(S) or base64 data URLs. Buffered output is `data[].b64_json` (raw base64) with optional
`media_type` and `usage`. There is no task polling/pagination in this synchronous workflow.

Only use SSE when the endpoint advertises streaming. Its `data:` JSON has `type` equal to
`image_generation.partial_image`, `image_generation.completed`, or `error`; final `[DONE]` is not
itself an image or proof of success. Completed events carry `b64_json`, optional `media_type`,
`created` and `usage`. The CLI does not stream.

The Image API documents full billing for completed generations and none for failed/cancelled
ones. Preview frames are not separate billable images. A local timeout or malformed response does
not by itself establish server-side billing status; inspect activity before replaying a request.

[Usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting) defines
`usage.cost` as the OpenRouter charge and `usage.cost_details.upstream_inference_cost` as upstream
inference cost. [BYOK](https://openrouter.ai/docs/guides/overview/auth/byok) may incur an OpenRouter
fee after its plan allowance. Display both fields without blindly adding them, and do not assume
`cost: 0` means an upstream provider did no billable work. Pixel area alone does not determine
output token count; old claims that 4K always costs sixteen times 1K were unsupported.
