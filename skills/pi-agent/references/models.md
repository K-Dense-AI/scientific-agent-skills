# Custom Models

Source: https://pi.dev/docs/latest/models

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

The `apiKey` is required even when the server ignores it. Edit during a session; `/model` reloads the file.

## Supported APIs

- `openai-completions`: OpenAI Chat Completions and compatibles.
- `openai-responses`: OpenAI Responses API.
- `anthropic-messages`: Anthropic Messages API.
- `google-generative-ai`: Google Generative AI.

## Provider Fields

`baseUrl`, `api`, `apiKey`, `headers`, `authHeader`, `models`, `modelOverrides`.

`apiKey` and `headers` support command execution (`!command`), env interpolation (`$ENV`/`${ENV}`), escapes (`$$`, `$!`), and literals. Shell commands in `models.json` resolve at request time and do not get built-in TTL/recovery; wrap slow or flaky secret commands yourself.

## Model Fields

Required: `id`.

Optional: `name`, `api`, `reasoning`, `thinkingLevelMap`, `input`, `contextWindow`, `maxTokens`, `cost`, `compat`.

`thinkingLevelMap` maps Pi levels (`off`, `minimal`, `low`, `medium`, `high`, `xhigh`) to provider values; `null` hides unsupported levels.

## Built-in Overrides

Override a provider base URL without redefining models:

```json
{ "providers": { "anthropic": { "baseUrl": "https://my-proxy.example.com/v1" } } }
```

If `models` is included, custom models merge into built-ins by `id`; matching IDs replace built-ins. Use `modelOverrides` to modify specific built-in models without replacing the provider list.

## Compatibility Flags

Anthropic flags include `supportsEagerToolInputStreaming`, `supportsLongCacheRetention`, `sendSessionAffinityHeaders`, `supportsCacheControlOnTools`, `forceAdaptiveThinking`, and `allowEmptySignature`.

OpenAI compatibility flags include `supportsStore`, `supportsDeveloperRole`, `supportsReasoningEffort`, `supportsUsageInStreaming`, `maxTokensField`, `requiresToolResultName`, `requiresAssistantAfterToolResult`, `requiresThinkingAsText`, `requiresReasoningContentOnAssistantMessages`, `thinkingFormat`, `cacheControlFormat`, `supportsStrictMode`, `supportsLongCacheRetention`, `openRouterRouting`, and `vercelGatewayRouting`.
