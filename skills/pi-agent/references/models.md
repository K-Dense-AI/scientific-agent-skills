# Custom Models

Source: https://pi.dev/docs/latest/models

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Add custom providers and models through `~/.pi/agent/models.json` for Ollama, LM Studio, vLLM, SGLang, proxies, and custom endpoints.

## Minimal Local Example

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        { "id": "llama3.1:8b" },
        { "id": "qwen2.5-coder:7b" }
      ]
    }
  }
}
```

Only `id` is required per model. The `apiKey` placeholder matters because Pi treats models as requiring auth before they appear in `/model`; keyless local servers should keep a dummy value, store a key via `/login`, or pass `--api-key`. Set `compat.supportsDeveloperRole: false` for OpenAI-compatible servers that reject the `developer` role, and `compat.supportsReasoningEffort: false` when `reasoning_effort` is unsupported. `compat` can be set at provider level (all models) or model level (override). The file reloads each time `/model` opens — no restart needed.

For `google-generative-ai` custom models, `baseUrl` is required (for example `https://generativelanguage.googleapis.com/v1beta`).

## Supported APIs

`openai-completions` (most compatible), `openai-responses`, `anthropic-messages`, `google-generative-ai`. Set `api` at provider level as the default, or per model to override.

## Provider Fields

`baseUrl`, `api`, `apiKey`, `oauth`, `headers`, `authHeader`, `models`, `modelOverrides`.

- `oauth`: dynamic OAuth provider type; currently `"radius"`, which requires the gateway `baseUrl`.
- `authHeader: true` adds `Authorization: Bearer <apiKey>`.
- `apiKey` is optional — omit it when auth comes from `/login`/`auth.json`/`--api-key`. Non-built-in providers with `models` need `baseUrl` and an `api` value at provider or model level. Without any auth, models load but stay unavailable in `/model` and `--list-models`.

`apiKey` and `headers` support command execution (`!command`, whole value), env interpolation (`$ENV` / `${ENV}`, works inside larger literals), escapes (`$$`, `$!`), and literals (plain uppercase strings are literals). Shell commands in `models.json` resolve at request time with no built-in TTL, stale reuse, or recovery — wrap slow or flaky secret commands yourself. `/model` availability checks use configured auth presence and do not execute shell commands.

## Model Fields

Required: `id`. Optional: `name` (defaults to `id`), `api`, `reasoning` (`false`), `thinkingLevelMap`, `input` (`["text"]` or `["text","image"]`), `contextWindow` (`128000`), `maxTokens` (`16384`), `samplingParams`, `cost` (zeros), `compat` (merged with provider `compat`).

`/model`, `--list-models`, and the footer display entries by model `id`; `name` is used for `--model` pattern matching and secondary detail text.

`cost` is per million tokens and supports request-wide input pricing tiers. A tier supplies a complete alternate rate set and applies to the whole request when `input + cacheRead + cacheWrite` exceeds `inputTokensAbove`; the highest matching threshold wins.

```json
{
  "cost": {
    "input": 5, "output": 30, "cacheRead": 0.5, "cacheWrite": 6.25,
    "tiers": [{ "inputTokensAbove": 272000, "input": 10, "output": 45, "cacheRead": 1, "cacheWrite": 12.5 }]
  }
}
```

## Sampling Parameters

`samplingParams` is a free-form object merged verbatim into every request body for that model, after the fields Pi sets itself — so its keys win, including over Pi's own `temperature`. Use it for sampling controls Pi does not model, such as llama.cpp `min_p` or vLLM `top_k`:

```json
{ "id": "deepseek-v4-flash",
  "samplingParams": { "temperature": 1.0, "top_p": 0.95, "top_k": 0, "min_p": 0.0 } }
```

Only OpenAI-compatible APIs apply it (`openai-completions`, `openai-responses`, `azure-openai-responses`); other APIs ignore it. Treat it as the single source of sampling truth for a model. In `modelOverrides`, `samplingParams` merges per key with the base model's value.

## Thinking Level Map

Keys are Pi levels: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Maps may have holes. Values are tristate: omitted means standard levels through `high` use the provider default mapping while `xhigh`/`max` are unsupported; a string is sent to the provider; `null` marks the level unsupported so it is hidden/skipped/clamped away.

```json
{ "id": "deepseek-v4-pro", "reasoning": true,
  "thinkingLevelMap": { "minimal": null, "low": null, "medium": null, "high": "high", "xhigh": null, "max": "max" } }
```

Use `{ "off": null }` for models where thinking cannot be disabled. Older `compat.reasoningEffortMap` configs should move to model-level `thinkingLevelMap`.

## Overriding Built-in Providers

Base-URL-only overrides keep all built-in models and existing auth:

```json
{ "providers": { "anthropic": { "baseUrl": "https://my-proxy.example.com/v1" } } }
```

If `models` is included, built-in models are kept and custom models are upserted by `id` — a matching `id` replaces the built-in, a new `id` is added.

`modelOverrides` customizes built-in and matching extension-registered models without replacing the provider list. Supported per-model fields: `name`, `reasoning`, `thinkingLevelMap`, `input`, `cost` (partial), `contextWindow`, `maxTokens`, `samplingParams` (merged per key), `headers`, `compat`. Unknown model IDs are ignored; provider-level `baseUrl`/`headers` can be combined with it. If `models` is also defined, custom models merge after built-in overrides.

Example — opt a direct OpenAI GPT-5.6 model into the 1.05M context window (they default to `272000` to stay in the short-context pricing tier):

```json
{ "providers": { "openai": { "modelOverrides": { "gpt-5.6-sol": { "contextWindow": 1050000 } } } } }
```

## Anthropic Messages Compatibility Flags

`supportsEagerToolInputStreaming` (default `true`; `false` omits `tools[].eager_input_streaming` and sends the legacy fine-grained-tool-streaming beta header), `supportsLongCacheRetention` (default `true`, `cache_control.ttl: "1h"`), `sendSessionAffinityHeaders` (auto-detected), `supportsCacheControlOnTools` (default `true`), `forceAdaptiveThinking` (`thinking.type: "adaptive"` plus `output_config.effort`; built-in adaptive models set it automatically), `allowEmptySignature` (replay empty thinking signatures as `signature: ""`), `supportsStrictTools` (default `false`; built-in Anthropic models enable it).

## OpenAI Compatibility Flags

`supportsStore`, `supportsDeveloperRole`, `supportsReasoningEffort`, `supportsUsageInStreaming` (default `true`), `supportsFinishReason` (default `true`; `false` makes Pi infer `stop`/`toolUse` when the stream ends without one), `maxTokensField` (`max_completion_tokens` | `max_tokens`), `requiresToolResultName`, `requiresAssistantAfterToolResult`, `requiresThinkingAsText`, `requiresReasoningContentOnAssistantMessages`, `thinkingFormat` (`openai`, `openrouter`, `deepseek`, `together`, `baseten`, `zai`, `qwen`, `chat-template`, `qwen-chat-template`, `string-thinking`, `ant-ling`), `chatTemplateKwargs`, `chatTemplateArgs` (`chat_template_args` values for `thinkingFormat: "baseten"`), `cacheControlFormat` (`anthropic`), `sendSessionAffinityHeaders` (default `false`), `sessionAffinityFormat` (`openai`, `openai-nosession`, `openrouter`), `supportsStrictMode`, `supportsOpenAIGrammarTools` (default `false`; the built-in catalog enables it for GPT-5+ on OpenAI, OpenAI Codex, Azure OpenAI, GitHub Copilot, opencode, Cloudflare AI Gateway), `vllmPriority`, `supportsMaxOutputTokens` (Responses), `supportsToolSearch` (Responses), `supportsLongCacheRetention` (default `true`; Responses uses `prompt_cache_options.ttl: "30m"` on GPT-5.6+ and `prompt_cache_retention: "24h"` on earlier models), `openRouterRouting`, `vercelGatewayRouting`.

Thinking-format notes: `openrouter` uses `reasoning: { effort }`; `together` uses `reasoning: { enabled }` plus `reasoning_effort` when `supportsReasoningEffort`; `qwen` uses top-level `enable_thinking`; `qwen-chat-template` targets local Qwen servers needing `chat_template_kwargs.enable_thinking` and `preserve_thinking`; `chat-template` plus `chatTemplateKwargs` targets vLLM/Hugging Face templates, e.g. `chatTemplateKwargs: { "thinking": { "$var": "thinking.enabled" } }` for DeepSeek V3.x. `baseten` plus `chatTemplateArgs` targets providers exposing toggle controls through `chat_template_args`, optionally with top-level `reasoning_effort`. `$var` accepts `thinking.enabled`, `thinking.effort`, or `thinking.budget`.

`openRouterRouting` is sent as-is in the OpenRouter `provider` field (`only`, `order`, `ignore`, `sort`, `max_price`, `quantizations`, `zdr`, …). `vercelGatewayRouting` takes `only`/`order`.


`inputLimits.images.resize` controls new image encoding (`maxWidth`, `maxHeight`, `maxBytes` for base64 payload, `jpegQuality`); historical images are not rewritten on model changes. `promptCache: { short, long }` declares best-effort lifetimes in seconds for cache warming. Both can be overridden through `modelOverrides`. Classifier models are separate from `/model`; use `ModelRuntime.getAvailableOfType("classifier")` and `classify()` or codemode's `models` API. Virtual model routing is experimental; use the current [virtual-model guide](https://pi.dev/docs/latest/virtual-models) and checked `jev-router.ts` example rather than changing persisted physical model identities yourself.
