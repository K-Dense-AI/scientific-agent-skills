import ipaddress
import os
import sys
from urllib.parse import urlparse

import httpx


def _is_loopback(host):
    if host == "localhost":
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

    if (parsed.scheme not in ("http", "https") or not host
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment):
        raise ValueError(
            f"{label} endpoint must be an http:// or https:// base URL with a host, "
            "without credentials, query, or fragment"
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
        reason = payload.get("stop_reason")
        if reason not in ("end_turn", "stop_sequence"):
            raise RuntimeError(f"Claude synthesis did not finish normally: {reason}")
        text = "".join(block["text"] for block in payload.get("content", [])
                       if block.get("type") == "text" and isinstance(block.get("text"), str))
        if not text.strip():
            raise RuntimeError("Claude synthesis returned no text content")
        return text


class LocalBackend:
    def __init__(self, endpoint, model, client=None, api_key=None):
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.client = client or httpx.Client(base_url=endpoint, timeout=120.0)

    def __call__(self, prompt):
        response = self.client.post(
            "/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices", [])
        if not choices:
            raise RuntimeError("Local synthesis returned no choices")
        choice = choices[0]
        reason = choice.get("finish_reason")
        if reason != "stop":
            raise RuntimeError(f"Local synthesis did not finish normally: {reason}")
        text = choice.get("message", {}).get("content")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Local synthesis returned no text content")
        return text


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
        return LocalBackend(endpoint=check_remote_endpoint(l["endpoint"], "local"), model=l["model"],
                            api_key=os.environ.get("LM_API_TOKEN"))

    raise ValueError(f"unknown backend: {kind!r}")
