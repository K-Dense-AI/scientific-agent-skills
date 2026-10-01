"""Small requests client shared by the Open Notebook examples (v1.14.0)."""

import os
from urllib.parse import quote

import requests


def api_url():
    """Accept the backend origin or an origin already ending in /api."""
    base = os.getenv("OPEN_NOTEBOOK_URL", "http://localhost:5055").rstrip("/")
    return base if base.endswith("/api") else base + "/api"


def record_path(record_id):
    """Encode a server-returned record ID as one URL path segment."""
    return quote(str(record_id), safe="")


def request(method, path, **kwargs):
    """Send an authenticated request; fail before decoding a non-success response."""
    headers = dict(kwargs.pop("headers", {}))
    password = os.getenv("OPEN_NOTEBOOK_PASSWORD")
    if password:
        headers["Authorization"] = f"Bearer {password}"
    kwargs.setdefault("timeout", (10, 300))
    # A redirect is not expected for these exact routes. Do not forward a secret
    # or a mutation body to a different path/deployment implicitly.
    response = requests.request(
        method, api_url() + path, headers=headers, allow_redirects=False, **kwargs
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        response.close()
        raise
    if 300 <= response.status_code < 400:
        response.close()
        raise requests.HTTPError("Unexpected Open Notebook redirect", response=response)
    return response


def request_json(method, path, **kwargs):
    with request(method, path, **kwargs) as response:
        return response.json()
