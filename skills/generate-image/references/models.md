# OpenRouter image model reference

Snapshot of `GET https://openrouter.ai/api/v1/images/models`, verified 2026-07-31. The catalogue
moves and this table will drift, so treat the live listing as authoritative:

```bash
python scripts/generate_image.py --list-models            # every model, with allowed values
python scripts/generate_image.py --list-models gemini     # filtered by substring
python scripts/generate_image.py --model-info MODEL       # one model, plus pricing
```

No API key is needed for any of those, and nothing is billed. The script validates every request
against this same metadata before spending money, so an unsupported parameter or an out-of-enum
value fails locally rather than as an HTTP 400 — you do not have to memorise the tables below.

## Which parameters each model accepts

`n` is images per request; `refs` is the maximum number of `input_references`. Prices are the
output-image rate the API reports; token-billed models scale with output resolution, so a 4K image
costs roughly sixteen times a 1K one.

| Model | n | refs | stream | Parameters | Output price |
| --- | --- | --- | --- | --- | --- |
| `google/gemini-3.1-flash-image` | 1 | 14 | no | aspect_ratio, input_references, n, resolution | $0.00006/token |
| `google/gemini-3.1-flash-image-preview` | 1 | 14 | no | aspect_ratio, input_references, n, resolution | $0.00006/token |
| `google/gemini-3-pro-image` | 1 | 14 | no | aspect_ratio, input_references, n, resolution | $0.00012/token |
| `google/gemini-3-pro-image-preview` | 1 | 14 | no | aspect_ratio, input_references, n, resolution | $0.00012/token |
| `google/gemini-3.1-flash-lite-image` | 1 | 14 | no | aspect_ratio, input_references, n, resolution | $0.00003/token |
| `google/gemini-2.5-flash-image` | 1 | 3 | no | aspect_ratio, input_references, n | $0.00003/token |
| `bytedance-seed/seedream-4.5` | 10 | 14 | no | aspect_ratio, input_references, n, resolution, seed | $0.04/image |
| `openai/gpt-image-2` | 10 | 16 | yes | aspect_ratio, background, input_references, n, output_compression, quality | $0.00003/token |
| `openai/gpt-image-1` | 10 | 16 | yes | aspect_ratio, background, input_references, n, output_compression, quality | $0.00004/token |
| `openai/gpt-image-1-mini` | 10 | 16 | yes | aspect_ratio, background, input_references, n, output_compression, quality | $0.000008/token |
| `openai/gpt-5.4-image-2` | 10 | 16 | yes | background, input_references, n, output_compression, quality | $0.00003/token |
| `openai/gpt-5-image` | 10 | 16 | yes | background, input_references, n, output_compression, quality | $0.00004/token |
| `openai/gpt-5-image-mini` | 10 | 16 | yes | background, input_references, n, output_compression, quality | $0.000008/token |
| `krea/krea-2-large` | — | 1 | no | aspect_ratio, input_references, resolution, seed | not published |
| `krea/krea-2-medium` | — | 1 | no | aspect_ratio, input_references, resolution, seed | not published |
| `krea/krea-2-medium-turbo` | — | 1 | no | aspect_ratio, input_references, resolution, seed | not published |
| `microsoft/mai-image-2.5` | 1 | 1 | no | aspect_ratio, input_references, n | $0.000047/token |
| `microsoft/mai-image-2.5-pro` | 1 | 1 | no | aspect_ratio, input_references, n | $0.000108/token |
| `recraft/recraft-v4.1` | 6 | 1 | no | aspect_ratio, input_references, n | $0.035/image |
| `recraft/recraft-v4.1-pro` | 6 | 1 | no | aspect_ratio, input_references, n | $0.21/image |
| `recraft/recraft-v4.1-vector` | 6 | 1 | no | aspect_ratio, input_references, n | $0.08/image |
| `recraft/recraft-v4.1-pro-vector` | 6 | 1 | no | aspect_ratio, input_references, n | $0.30/image |
| `recraft/recraft-v4.1-utility` | 6 | 1 | no | aspect_ratio, input_references, n | $0.035/image |
| `recraft/recraft-v4.1-utility-pro` | 6 | 1 | no | aspect_ratio, input_references, n | $0.21/image |
| `recraft/recraft-v4` | 6 | 1 | no | aspect_ratio, input_references, n | $0.04/image |
| `recraft/recraft-v4-pro` | 6 | 1 | no | aspect_ratio, input_references, n | $0.25/image |
| `recraft/recraft-v4-vector` | 6 | 1 | no | aspect_ratio, input_references, n | $0.08/image |
| `recraft/recraft-v4-pro-vector` | 6 | 1 | no | aspect_ratio, input_references, n | $0.30/image |
| `recraft/recraft-v3` | 6 | 1 | no | aspect_ratio, input_references, n | $0.04/image |
| `sourceful/riverflow-v2.5-pro` | 1 | 10 | no | aspect_ratio, background, input_references, n, output_format, resolution | $0.13/image; $0.15 at 2K; $0.17 at 4K |
| `sourceful/riverflow-v2.5-fast` | 1 | 4 | no | aspect_ratio, background, input_references, n, output_format, resolution | $0.019/image; $0.021 at 2K |
| `sourceful/riverflow-v2-pro` | 1 | 10 | no | aspect_ratio, input_references, n, resolution | $0.15/image; $0.33 at 4K |
| `sourceful/riverflow-v2-fast` | 1 | 4 | no | aspect_ratio, input_references, n, resolution | $0.02/image; $0.04 at 2K |
| `x-ai/grok-imagine-image-quality` | 1 | 3 | no | aspect_ratio, input_references, n, resolution | $0.05/image at 1K; $0.07 at 2K |

Riverflow also bills reference images: v2 charges $0.20 per `input_reference` and $0.03 per input
font. The Krea models publish no price through the API — check the cost the script reports after a
run before using them at volume.

## Which values each parameter accepts

Support is not enough: the allowed **values** differ per model too, and an out-of-enum value is
rejected the same way an unsupported parameter is. A dash means the model does not accept the
parameter at all.

| Model | resolution | output_format | background | quality | seed |
| --- | --- | --- | --- | --- | --- |
| `google/gemini-3.1-flash-image` | 512, 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3.1-flash-image-preview` | 512, 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3-pro-image` | 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3-pro-image-preview` | 1K, 2K, 4K | — | — | — | — |
| `google/gemini-3.1-flash-lite-image` | **1K only** | — | — | — | — |
| `google/gemini-2.5-flash-image` | — | — | — | — | — |
| `bytedance-seed/seedream-4.5` | 1K, 2K, 4K | — | — | — | yes |
| `openai/gpt-image-2` | — | — | **auto, opaque** | auto, low, medium, high | — |
| `openai/gpt-image-1` | — | — | auto, transparent, opaque | auto, low, medium, high | — |
| `openai/gpt-image-1-mini` | — | — | auto, transparent, opaque | auto, low, medium, high | — |
| `openai/gpt-5.4-image-2` | — | — | **auto, opaque** | auto, low, medium, high | — |
| `openai/gpt-5-image` | — | — | auto, transparent, opaque | auto, low, medium, high | — |
| `openai/gpt-5-image-mini` | — | — | auto, transparent, opaque | auto, low, medium, high | — |
| `krea/krea-2-*` | **1K only** | — | — | — | yes |
| `microsoft/mai-image-2.5`, `-pro` | — | — | — | — | — |
| `recraft/*` | — | — | — | — | — |
| `sourceful/riverflow-v2.5-pro` | 1K, 2K, 4K | png, jpeg, webp | auto, transparent, opaque | — | — |
| `sourceful/riverflow-v2.5-fast` | 1K, 2K | **jpeg only** | auto, transparent, opaque | — | — |
| `sourceful/riverflow-v2-pro`, `-fast` | 1K, 2K, 4K | — | — | — | — |
| `x-ai/grok-imagine-image-quality` | 1K, 2K | — | — | — | — |

Traps worth knowing, because each one is a wasted round trip:

- `transparent` is **not** available on `gpt-image-2` or `gpt-5.4-image-2`, the newest OpenAI
  models. Use `gpt-image-1`, `gpt-image-1-mini`, `gpt-5-image`, `gpt-5-image-mini`, or Riverflow 2.5.
- `512` exists only on Gemini 3.1 Flash. `flash-lite` and the Krea models take `1K` and nothing else.
- `output_compression` is offered only by the OpenAI models, and none of them accept
  `output_format` — the container is theirs to choose.
- This table is a dated snapshot. The [current Image API](https://openrouter.ai/docs/guides/overview/multimodal/image-generation)
  documents `size` and `output_format: svg`; availability depends on the live model/endpoint.
  The bundled CLI still has no `--size` flag. For vector output, verify the returned
  `media_type: image/svg+xml` instead of inferring the format from a filename.

### Aspect ratio enums

`aspect_ratio` is the most varied parameter, and three OpenAI models do not accept it at all.

| Models | Allowed |
| --- | --- |
| `gemini-3.1-flash-image`, `-preview`, `flash-lite` | 1:1, 1:4, 1:8, 2:3, 3:2, 3:4, 4:1, 4:3, 4:5, 5:4, 8:1, 9:16, 16:9, 21:9 |
| `gemini-3-pro-image`, `-preview`, `gemini-2.5-flash-image` | 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 |
| `seedream-4.5` | 1:1, 1:2, 2:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 9:19.5, 19.5:9, 9:20, 20:9, 9:21, 21:9, auto |
| `gpt-image-2` | 1:1, 3:2, 2:3, 4:3, 3:4, 16:9, 9:16, 21:9, auto |
| `gpt-image-1`, `gpt-image-1-mini` | **1:1, 3:2, 2:3, auto only — no 16:9** |
| `gpt-5-image`, `gpt-5-image-mini`, `gpt-5.4-image-2` | **not accepted at all** |
| `recraft/*` | 1:1, 4:3, 3:4, 16:9, 9:16, auto |
| `riverflow-*` | 1:1, 4:3, 3:4, 3:2, 2:3, 16:9, 9:16, 21:9, auto |
| `mai-image-2.5`, `-pro` | 1:1, 4:3, 3:4, 16:9, 9:16, 3:2, 2:3, auto |
| `krea/krea-2-*` | 1:1, 4:3, 3:2, 16:9, 4:5, 2:3, 9:16 |
| `grok-imagine-image-quality` | 1:1, 3:4, 4:3, 9:16, 16:9, 2:3, 3:2, 9:19.5, 19.5:9, 9:20, 20:9, 1:2, 2:1, auto |

## Choosing a model

- **General quality and prompt adherence** — `google/gemini-3.1-flash-image` (skill default), or
  `google/gemini-3-pro-image` for the higher tier at double the token rate.
- **Cheap iteration** — `google/gemini-3.1-flash-lite-image` (half the flash rate, but 1K only) or
  `openai/gpt-image-1-mini`. Measured: one 1K `flash-lite` image is 1120 output tokens, $0.034.
- **Photoreal and artistic control** — `bytedance-seed/seedream-4.5` (flat $0.04/image, seeded) or
  `microsoft/mai-image-2.5-pro`.
- **Reproducible output from a seed** — `bytedance-seed/seedream-4.5` and the Krea models. The
  Gemini and OpenAI families do not accept `seed`.
- **Batches** — `bytedance-seed/seedream-4.5` or the OpenAI family, up to 10 per request. Gemini,
  Riverflow, MAI, and Grok cap at 1; Recraft at 6.
- **True vector output (SVG)** — `recraft/recraft-v4.1-vector`, `recraft/recraft-v4-vector`, and the
  `-pro-vector` variants. These return `media_type: image/svg+xml`.
- **Text rendered legibly inside the image** — Recraft (which takes `text_layout` as a passthrough
  parameter) and Riverflow are the strongest, but no model is dependable. Prefer overlaying text in
  LaTeX, PowerPoint, or HTML.
- **Transparent backgrounds** — `gpt-image-1`, `gpt-image-1-mini`, `gpt-5-image`,
  `gpt-5-image-mini`, or `riverflow-v2.5-*`.
- **Heavy multi-reference compositing** — OpenAI (16 references), Gemini and Seedream (14),
  `riverflow-v2*-pro` (10). Recraft, MAI, and Krea accept exactly 1.

## Passthrough parameters

`GET /api/v1/images/models/<model>/endpoints` lists `allowed_passthrough_parameters` — provider
options the Image API forwards but the bundled script does not expose. Notable sets:

- Recraft: `style`, `controls`, `text_layout`
- Krea: `styles`, `moodboards`, `image_style_references`, `creativity`, `intensity`, `complexity`,
  `movement`, `strength`
- OpenAI: `moderation`
- Gemini: `cachedContent`
- Riverflow: `font_inputs`

Send a direct request when you need one of these. `--model-info MODEL` prints the list.

## Provider routing

The Image API accepts the same `provider` block as chat completions — `provider.only`,
`provider.order`, `provider.ignore`, `provider.sort` (`price`, `throughput`, `latency`), and
`provider.allow_fallbacks`. The bundled script does not expose these; send a direct request when
routing control matters.

## Billing

Image billing is all-or-nothing: a generation either completes and is billed in full, or fails and
is not billed. A rejected parameter therefore costs nothing but time. Partial preview frames
delivered during streaming are not charged separately.

Per-request cost comes back in `usage.cost`, which the script prints. On a bring-your-own-key
account `usage.cost` is `0` and the real figure is in `cost_details.upstream_inference_cost`, where
the upstream provider bills you directly — the script reports that instead of claiming the
generation was free.
