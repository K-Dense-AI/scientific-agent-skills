# Providers

Source: https://pi.dev/docs/latest/providers

Pi supports subscription providers via OAuth and API-key providers via env vars or `~/.pi/agent/auth.json`. Built-in model lists are updated with each Pi release.

## Subscription Providers

Use `/login` and choose Claude Pro/Max, ChatGPT Plus/Pro (Codex), or GitHub Copilot. Use `/logout` to clear credentials. Tokens live in `~/.pi/agent/auth.json` and refresh automatically.

## API Key Providers

Set env vars before startup or use `/login` to store keys. Common mappings:

- `ANTHROPIC_API_KEY` -> `anthropic`
- `OPENAI_API_KEY` -> `openai`
- `GEMINI_API_KEY` -> `google`
- `MISTRAL_API_KEY` -> `mistral`
- `GROQ_API_KEY` -> `groq`
- `OPENROUTER_API_KEY` -> `openrouter`
- `AI_GATEWAY_API_KEY` -> `vercel-ai-gateway`
- `CLOUDFLARE_API_KEY` plus account/gateway vars -> Cloudflare providers
- `AWS_*` credentials -> Amazon Bedrock

`auth.json` entries use `{ "type": "api_key", "key": "..." }` and are created with `0600` permissions.

## Key Resolution Syntax

The `key` field supports:

```json
{ "type": "api_key", "key": "!op read 'op://vault/item/credential'" }
{ "type": "api_key", "key": "$MY_API_KEY" }
{ "type": "api_key", "key": "${KEY_PREFIX}_${KEY_SUFFIX}" }
{ "type": "api_key", "key": "$$literal-dollar" }
{ "type": "api_key", "key": "$!literal-bang" }
```

Auth file credentials take priority over environment variables.

## Cloud Providers

Azure OpenAI needs `AZURE_OPENAI_API_KEY` plus `AZURE_OPENAI_BASE_URL` or `AZURE_OPENAI_RESOURCE_NAME`; optional `AZURE_OPENAI_API_VERSION` and deployment mapping.

Amazon Bedrock uses AWS profile, IAM keys, bearer token, ECS task roles, or IRSA. Set region through `AWS_REGION`. For application inference profiles that do not include recognizable model names, set `AWS_BEDROCK_FORCE_CACHE=1` to force cache points.

Cloudflare AI Gateway requires `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, and `CLOUDFLARE_GATEWAY_ID`. Prefer unified billing or stored BYOK.

Google Vertex AI uses Application Default Credentials plus `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`.

## Resolution Order

1. CLI `--api-key`
2. `auth.json` entry
3. Environment variable
4. Custom provider keys from `models.json`
