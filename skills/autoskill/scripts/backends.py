import os

import httpx


class ClaudeBackend:
    def __init__(self, api_key, model, client=None):
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(base_url="https://api.anthropic.com", timeout=60.0)

    def __call__(self, prompt):
        response = self.client.post(
            "/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload["content"][0]["text"]


class LocalBackend:
    def __init__(self, endpoint, model, client=None):
        self.endpoint = endpoint
        self.model = model
        self.client = client or httpx.Client(base_url=endpoint, timeout=120.0)

    def __call__(self, prompt):
        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]


def make_backend(config):
    kind = config.get("backend")
    if kind == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        model = config.get("claude", {}).get("model", "claude-opus-4-7")
        return ClaudeBackend(api_key=api_key, model=model)

    if kind == "foundry":
        api_key = os.environ.get("FOUNDRY_API_KEY")
        if not api_key:
            raise RuntimeError("FOUNDRY_API_KEY environment variable not set")
        f = config.get("foundry", {})
        client = httpx.Client(base_url=f["endpoint"], timeout=60.0)
        return ClaudeBackend(api_key=api_key, model=f.get("model", "claude-opus-4-7"), client=client)

    if kind == "local":
        l = config.get("local", {})
        return LocalBackend(endpoint=l["endpoint"], model=l["model"])

    raise ValueError(f"unknown backend: {kind!r}")
