# Custom Providers

Source: https://pi.dev/docs/latest/custom-provider

Extensions can register providers with `pi.registerProvider()` for proxies, private deployments, OAuth/SSO, and non-standard streaming APIs.

## Quick Reference

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerProvider("anthropic", { baseUrl: "https://proxy.example.com" });

  pi.registerProvider("my-provider", {
    name: "My Provider",
    baseUrl: "https://api.example.com",
    apiKey: "$MY_API_KEY",
    api: "openai-completions",
    models: [{
      id: "my-model",
      name: "My Model",
      reasoning: false,
      input: ["text", "image"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      contextWindow: 128000,
      maxTokens: 4096
    }]
  });
}
```

Use an async extension factory for dynamic model discovery so models are available during startup and `pi --list-models`.

## Overrides and New Providers

When only `baseUrl` and/or `headers` are provided, existing models for a built-in provider are preserved. When `models` is provided, it replaces dynamic models for that provider.

`pi.unregisterProvider(name)` removes dynamic models, API key fallback, OAuth registration, and custom stream handlers, restoring built-in behavior where relevant.

## API Types

Common values: `anthropic-messages`, `openai-completions`, `openai-responses`, `azure-openai-responses`, `openai-codex-responses`, `mistral-conversations`, `google-generative-ai`, `google-vertex`, `bedrock-converse-stream`.

Most OpenAI-compatible providers work with `openai-completions`; use `compat` for quirks and `thinkingLevelMap` for model-specific thinking levels.

## Auth Header and Secrets

Set `authHeader: true` to add `Authorization: Bearer <apiKey>`. `apiKey` and custom header values use `!command`, `$ENV`, `${ENV}`, `$$`, and `$!` resolution like `models.json`.

## OAuth

Register `oauth` with `login(callbacks)`, `refreshToken(credentials)`, `getApiKey(credentials)`, and optional `modifyModels(models, credentials)`. Credentials persist in `~/.pi/agent/auth.json` with `refresh`, `access`, and `expires` fields. Users authenticate with `/login provider-name`.

Callbacks include `onAuth`, `onDeviceCode`, `onPrompt`, and `onSelect`.

## Custom Streaming

For non-standard APIs, implement `streamSimple(model, context, options)`. Create an `AssistantMessage`, push `{ type: "start", partial }`, push content events as data arrives, then push `{ type: "done", reason, message }` or `{ type: "error", reason, error }`, and end the stream.

Content events include `text_start`, `text_delta`, `text_end`, `thinking_start`, `thinking_delta`, `thinking_end`, `toolcall_start`, `toolcall_delta`, and `toolcall_end`. Keep `partial` updated with the current assistant message state.

For tool calls, accumulate JSON deltas, parse into `{ id, name, arguments }`, and end with `toolcall_end`.

## Testing

Test provider registration with `pi --list-models`, authenticate through `/login` or env vars, run a simple prompt, then exercise tools, thinking levels, image input, cache behavior, retry behavior, and context overflow errors.
