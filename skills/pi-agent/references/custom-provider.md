# Custom Providers

Source: https://pi.dev/docs/latest/custom-provider

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Extensions register providers with `pi.registerProvider()` for proxies, private deployments, OAuth/SSO, and non-standard streaming APIs. Two forms exist: a complete pi-ai `Provider` (preferred when you need custom authentication, filtering, refresh, or streaming) and the legacy provider-config object. `models.json` overrides compose **above** registered native providers.

## Complete Provider Form

```ts
import { createProvider } from "@earendil-works/pi-ai";
import * as openaiCompletionsApi from "@earendil-works/pi-ai/api/openai-completions";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerProvider(createProvider({
    id: "native-local",
    name: "Native Local",
    baseUrl: "http://localhost:8080/v1",
    auth: {
      apiKey: {
        name: "Local server API key",
        async login(interaction) {
          return { type: "api_key", key: await interaction.prompt({ type: "secret", message: "API key" }) };
        },
        async resolve({ credential }) {
          return credential?.key ? { auth: { apiKey: credential.key }, source: "stored API key" } : undefined;
        },
      },
    },
    models: [],
    api: openaiCompletionsApi,
  }));
}
```

The object form accepts a complete `Provider`, including native `auth`, `getModels`, `refreshModels`, `filterModels`, `stream`, and `streamSimple`.

## Legacy Config Form

```ts
// Override baseUrl and/or headers only — existing models are preserved
pi.registerProvider("anthropic", { baseUrl: "https://proxy.example.com" });
pi.registerProvider("openai", { headers: { "X-Custom-Header": "value" } });

// New provider with models — replaces all existing models for that provider
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
    maxTokens: 4096,
  }],
});
```

Use an **async extension factory** for dynamic model discovery so models are registered before startup finishes and are visible to `pi --list-models`. Dynamic providers can also implement `refreshModels(context)`. Complete Providers return nothing and call `context.publish({ update })` to install provider-owned state exposed by `getModels()`. Legacy config callbacks return model definitions. Use the generation-checked publish persistence contract, never the removed `context.store` pattern; pass `context.signal` to I/O.

`pi.unregisterProvider(name)` removes that provider's dynamic models, API key fallback, OAuth registration, and custom stream handlers, restoring overridden built-in behavior. Calls made after the initial load phase take effect immediately — no `/reload`.

## API Types

`anthropic-messages`, `openai-completions`, `openai-responses`, `azure-openai-responses`, `openai-codex-responses`, `mistral-conversations`, `google-generative-ai`, `google-vertex`, `bedrock-converse-stream`.

Most OpenAI-compatible providers work with `openai-completions`; use model-level `thinkingLevelMap` for thinking levels and `compat` for quirks (full flag list in `references/models.md`). `xhigh` and `max` are opt-in and require non-null map entries. Mistral moved from `openai-completions` to `mistral-conversations` (native Mistral Chat Completions streaming) — use the latter for native Mistral models.

## Auth Header and Secrets

`authHeader: true` adds `Authorization: Bearer <apiKey>`; the key is resolved per request and an explicit request `Authorization` header wins. `apiKey` and custom header values use the same syntax as `models.json`: leading `!command` executes for the whole value, `$ENV`/`${ENV}` interpolate, `$$` and `$!` escape literals.

## OAuth

```ts
oauth: {
  name: "Corporate AI (SSO)",
  async login(callbacks: OAuthLoginCallbacks): Promise<OAuthCredentials>,
  async refreshToken(credentials: OAuthCredentials, signal: AbortSignal): Promise<OAuthCredentials>,
  getApiKey(credentials: OAuthCredentials): string,
}
```

`OAuthLoginCallbacks`: `onAuth({ url })` (open in browser), `onDeviceCode({ userCode, verificationUri, intervalSeconds?, expiresInSeconds? })`, `onProgress?(message)`, `onPrompt({ message }): Promise<string>`, `onSelect({ message, options: { id, label }[] }): Promise<string | undefined>`.

`OAuthCredentials` is `{ refresh, access, expires }` (expiry in ms), persisted in `~/.pi/agent/auth.json`. Users authenticate with `/login <provider-name>`. `refreshToken` receives an `AbortSignal` — pass it to blocking I/O and call `signal.throwIfAborted()` early.

## Custom Streaming

Implement `streamSimple(model, context, options?)` with a normalized `TranscriptContext`: read prompt/tools with `getCurrentSystemPrompt(context.messages)` and `getCurrentTools(context.messages)`, or use `collapseSystemMessages(context)` for transports that cannot represent mid-conversation updates. Do not read removed `context.systemPrompt`/`context.tools`. Return an `AssistantMessageEventStream` from `createAssistantMessageEventStream()`. Initialize an `AssistantMessage` (`role`, `content: []`, `api`, `provider`, `model`, zeroed `usage`, `stopReason: "pending"`, `timestamp`), then:

1. `stream.push({ type: "start", partial: output })`
2. Content events, tracking `contentIndex` per block: `text_start`, `text_delta`, `text_end`, `thinking_start`, `thinking_delta`, `thinking_end`, `toolcall_start`, `toolcall_delta`, `toolcall_end`
3. `stream.push({ type: "done", reason, message })` or `{ type: "error", reason, error }`, then `stream.end()`

`stopReason: "pending"` marks the partial message; set a terminal reason before pushing `done` (throw for `"error"`/`"aborted"`). Content/start events carry `partial` with the current `AssistantMessage` state; terminal events instead carry `message` or `error` — mutate `output.content` as data arrives and pass `output`. Tool calls accumulate JSON deltas, parse into `{ id, name, arguments }`, and finish with `toolcall_end` carrying the full `toolCall`. Update usage from the API response and call `calculateCost(model, output.usage)`. Register with `streamSimple` on the provider config.

Reference implementations live in `packages/ai/src/api/`, including `anthropic-messages.ts`, `mistral-conversations.ts`, `openai-completions.ts`, `openai-responses.ts`, `google-generative-ai.ts`, and `bedrock-converse-stream.ts`. Honor `options.onPayload`, `options.onResponse`, and awaited `options.onProviderStreamEvent` plus cancellation and provider-scoped environment.

## Context Overflow Errors

Pi auto-recovers from context overflow by compacting and retrying once, but only when it recognizes the failure: `stopReason === "error"` and `errorMessage` matching a known pattern (see `packages/ai/src/utils/overflow.ts`). If your provider's message is unrecognized, normalize it from the same extension with a `message_end` handler so `errorMessage` starts with a recognized phrase — `context_length_exceeded` is the safest:

```ts
pi.on("message_end", (event, ctx) => {
  const message = event.message;
  if (message.role !== "assistant" || message.stopReason !== "error") return;
  if (message.provider !== "my-provider" && ctx.model?.provider !== "my-provider") return;
  const errorMessage = message.errorMessage ?? "";
  if (errorMessage.includes("context_length_exceeded")) return;
  if (!MY_PROVIDER_OVERFLOW_PATTERN.test(errorMessage)) return;
  return { message: { ...message, errorMessage: `context_length_exceeded: ${errorMessage}` } };
});
```

`message_end` runs before Pi tracks the message for auto-compaction, so the rewrite is what Pi checks. Scope it to your provider, match a provider-specific pattern (never Pi's generic ones — rewriting rate-limit errors would trigger compaction instead of retry-with-backoff), and skip when the phrase is already present so the handler is idempotent.

## Testing

Adapt the suites in `packages/ai/test/` for your provider/model pairs: `stream.test.ts`, `tokens.test.ts`, `abort.test.ts`, `empty.test.ts`, `context-overflow.test.ts`, `image-limits.test.ts`, `unicode-surrogate.test.ts`, `tool-call-without-result.test.ts`, `image-tool-result.test.ts`, `total-tokens.test.ts`, `cross-provider-handoff.test.ts`. Verify registration with `pi --list-models`, then exercise auth, tools, thinking levels, image input, cache behavior, retries, and context overflow.

## Config Reference

`ProviderConfig`: `name?`, `baseUrl?`, `apiKey?`, `api?`, `streamSimple?`, `headers?`, `authHeader?`, `models?`, `refreshModels?`, `oauth?`.

`ProviderModelConfig`: `id`, `name`, `api?`, `baseUrl?` (per-model endpoint override), `reasoning`, `thinkingLevelMap?`, `input`, `cost` (`input`, `output`, `cacheRead`, `cacheWrite` per million tokens), `contextWindow`, `maxTokens`, `headers?`, `compat?`.

Example extensions: `examples/extensions/custom-provider-anthropic/` and `examples/extensions/custom-provider-gitlab-duo/`.
