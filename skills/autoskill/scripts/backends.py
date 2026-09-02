import ipaddress
import os
import sys
from urllib.parse import urlparse

import httpx


MINIMAX_REGIONS = {
    "global_en": {
        "openai_base_url": "https://api.minimax.io/v1",
        "anthropic_base_url": "https://api.minimax.io/anthropic",
    },
    "cn_zh": {
        "openai_base_url": "https://api.minimaxi.com/v1",
        "anthropic_base_url": "https://api.minimaxi.com/anthropic",
    },
}

MINIMAX_MODELS = {
    "MiniMax-M3": {
        "context_window": 1_000_000,
        "pricing_usd_per_million_tokens": {
            "input": 0.6,
            "output": 2.4,
            "cache_read": 0.12,
            "cache_write": None,
        },
        "input_modalities": ("text", "image", "video"),
        "thinking": ("adaptive", "disabled"),
        "default_thinking": "adaptive",
    },
    "MiniMax-M2.7": {
        "context_window": 204_800,
        "pricing_usd_per_million_tokens": {
            "input": 0.3,
            "output": 1.2,
            "cache_read": 0.06,
            "cache_write": 0.375,
        },
        "input_modalities": ("text",),
        "thinking": ("always_on",),
        "default_thinking": "always_on",
    },
}


def _is_loopback(host):
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_remote_endpoint(endpoint, label):
    """Reject cleartext transport to a remote host, and name the destination.

    This backend sends summaries derived from the user's screen-capture history.
    The endpoint is read from config.yaml, so it is worth being explicit about
    where that data is about to go, and refusing to send it -- along with an API
    key header -- over plaintext HTTP to anything but the local machine.
    """
    parsed = urlparse(endpoint)
    host = parsed.hostname or ""

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"{label} endpoint must be an http:// or https:// URL, got {endpoint!r}"
        )

    if parsed.scheme == "http" and not _is_loopback(host):
        raise ValueError(
            f"{label} endpoint {endpoint!r} uses plaintext HTTP to a remote host. "
            "Screen-derived content and your API key would cross the network "
            "unencrypted. Use https://, or point the endpoint at localhost."
        )

    if not _is_loopback(host):
        print(
            f"[autoskill] sending screen-derived summaries to {parsed.scheme}://{host}",
            file=sys.stderr,
        )

    return endpoint


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


class MiniMaxBackend:
    def __init__(self, api_key, model, endpoint, protocol="openai", thinking=None, client=None):
        if model not in MINIMAX_MODELS:
            supported = ", ".join(sorted(MINIMAX_MODELS))
            raise ValueError(f"unsupported MiniMax model: {model!r}; supported: {supported}")

        model_config = MINIMAX_MODELS[model]
        thinking = thinking or model_config["default_thinking"]
        if thinking not in model_config["thinking"]:
            supported = ", ".join(model_config["thinking"])
            raise ValueError(
                f"unsupported MiniMax thinking mode for {model}: {thinking!r}; "
                f"supported: {supported}"
            )

        if protocol not in ("openai", "anthropic"):
            raise ValueError(f"unsupported MiniMax protocol: {protocol!r}")

        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.protocol = protocol
        self.thinking = thinking
        self.metadata = model_config
        self.client = client or httpx.Client(base_url=endpoint, timeout=60.0)

    def __call__(self, prompt):
        if self.protocol == "anthropic":
            return self._call_anthropic(prompt)
        return self._call_openai(prompt)

    def _thinking_payload(self):
        if self.thinking == "disabled":
            return {"thinking": {"type": "disabled"}}
        if self.thinking == "adaptive":
            return {"thinking": {"type": "enabled", "mode": "adaptive"}}
        return {"thinking": {"type": "enabled"}}

    def _call_openai(self, prompt):
        response = self.client.post(
            "/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                **self._thinking_payload(),
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

    def _call_anthropic(self, prompt):
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
                **self._thinking_payload(),
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload["content"][0]["text"]


def _minimax_endpoint(config):
    region = config.get("region", "global_en")
    protocol = config.get("protocol", "openai")
    if region not in MINIMAX_REGIONS:
        supported = ", ".join(sorted(MINIMAX_REGIONS))
        raise ValueError(f"unsupported MiniMax region: {region!r}; supported: {supported}")
    if protocol == "openai":
        return MINIMAX_REGIONS[region]["openai_base_url"]
    if protocol == "anthropic":
        return MINIMAX_REGIONS[region]["anthropic_base_url"]
    raise ValueError(f"unsupported MiniMax protocol: {protocol!r}")


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
        endpoint = check_remote_endpoint(f["endpoint"], "foundry")
        client = httpx.Client(base_url=endpoint, timeout=60.0)
        return ClaudeBackend(api_key=api_key, model=f.get("model", "claude-opus-4-7"), client=client)

    if kind == "local":
        l = config.get("local", {})
        return LocalBackend(endpoint=check_remote_endpoint(l["endpoint"], "local"), model=l["model"])

    if kind == "minimax":
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            raise RuntimeError("MINIMAX_API_KEY environment variable not set")
        m = config.get("minimax", {})
        endpoint = check_remote_endpoint(m.get("endpoint") or _minimax_endpoint(m), "minimax")
        return MiniMaxBackend(
            api_key=api_key,
            model=m.get("model", "MiniMax-M3"),
            endpoint=endpoint,
            protocol=m.get("protocol", "openai"),
            thinking=m.get("thinking"),
        )

    raise ValueError(f"unknown backend: {kind!r}")
