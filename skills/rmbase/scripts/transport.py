"""Bounded, anonymous HTTP access to the existing RMBase public website."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://bioinformaticsscience.cn/rmbase/"
HOST = "bioinformaticsscience.cn"
UPLOAD_PATHS = {
    "/cgi-bin/runModAnno.pl", "/cgi-bin/runModMeta.pl", "/cgi-bin/runModgenetool.pl"
}


class RMBaseError(Exception):
    def __init__(self, code, message, exit_code=2, **details):
        super().__init__(message)
        self.code, self.exit_code, self.details = code, exit_code, details

    def as_dict(self):
        return {"code": self.code, "message": str(self), **self.details}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public_url(url):
    """Allow only the public site and the three observed upload form actions."""
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(p.path)
    if (p.scheme not in {"http", "https"} or p.hostname != HOST
            or p.username or p.password or p.port is not None
            or "\\" in path or any(x in {".", ".."} for x in path.split("/"))
            or not (path.startswith("/rmbase/") or path in UPLOAD_PATHS)):
        raise RMBaseError("unsafe_url", "URL is outside the observed RMBase public surface.")
    return url


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        if req.get_method() == "POST" and urllib.parse.urlsplit(req.full_url).path in UPLOAD_PATHS:
            raise RMBaseError("upload_redirect", "Upload redirected; it was not resubmitted.", 3)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def atomic_write(path, data):
    """Write only our specific cache file, never unpack remote paths."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temp.write_bytes(data)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


class Transport:
    def __init__(self, cache_dir=None, timeout=30, retries=1, offline=False,
                 refresh=False, interval=2, opener=None):
        if not math.isfinite(timeout) or not 1 <= timeout <= 120:
            raise RMBaseError("invalid_timeout", "Timeout must be between 1 and 120 seconds.")
        if retries not in (0, 1, 2):
            raise RMBaseError("invalid_retries", "At most two read retries are permitted.")
        if not math.isfinite(interval) or interval < 2:
            raise RMBaseError("invalid_interval", "Request spacing must be at least two seconds.")
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "rmbase"
        self.timeout, self.retries = timeout, retries
        self.offline, self.refresh, self.interval = offline, refresh, interval
        self.opener = opener or urllib.request.build_opener(PublicRedirect())
        self.sources = []

    def _pace(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        lock = self.cache_dir / ".request.lock"
        deadline = time.monotonic() + 15
        while True:
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                break
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise RMBaseError("client_busy", "Another RMBase client holds the rate lock.", 3)
                time.sleep(0.1)
        stamp = self.cache_dir / "next-request.txt"
        try:
            os.close(fd)
            try:
                next_time = float(stamp.read_text(encoding="ascii"))
            except (FileNotFoundError, ValueError):
                next_time = 0
            delay = next_time - time.time()
            if not math.isfinite(next_time) or delay > 30:
                raise RMBaseError("cache_corrupt", "Rate-limit timestamp is invalid; inspect the cache before retrying.", 6)
            if delay > 0:
                time.sleep(delay)
            atomic_write(stamp, str(time.time() + self.interval).encode("ascii"))
        finally:
            lock.unlink(missing_ok=True)

    def request(self, route, params=None, method="GET", *, body=None,
                content_type=None, cache=True, retry=True, max_bytes=8_000_000):
        url = public_url(urllib.parse.urljoin(BASE, route))
        params = dict(params or {})
        if method == "GET" and params:
            url += "?" + urllib.parse.urlencode(sorted(params.items()))
        elif body is None and method == "POST":
            body = urllib.parse.urlencode(sorted(params.items())).encode("utf-8")
            content_type = "application/x-www-form-urlencoded"
        key = hashlib.sha256(method.encode() + url.encode() + (body or b"")).hexdigest()
        cache_file = self.cache_dir / "responses" / (key + ".json")
        data_file = cache_file.with_suffix(".body")
        if cache and not self.refresh and cache_file.exists() and data_file.exists():
            try:
                meta = json.loads(cache_file.read_text(encoding="utf-8"))
                age = time.time() - meta["cached_epoch"]
                if self.offline or 0 <= age < 86400:
                    if data_file.stat().st_size > max_bytes:
                        raise RMBaseError("response_too_large", "Cached response exceeds the byte limit.", 5)
                    raw = data_file.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                        raise RMBaseError("cache_corrupt", "Cached response checksum mismatch.", 6)
                    self.sources.append({**meta, "cache_hit": True})
                    return raw
            except (ValueError, KeyError, TypeError) as exc:
                raise RMBaseError("cache_corrupt", "Invalid response cache metadata.", 6) from exc
        if self.offline:
            raise RMBaseError("offline_cache_miss", "No saved response for this exact query.", 6)
        headers = {"User-Agent": "RMBase-Agent-Skill/1.0 (bounded scientific client)",
                   "Accept-Encoding": "identity"}
        if content_type:
            headers["Content-Type"] = content_type
        for attempt in range((self.retries if retry else 0) + 1):
            self._pace()
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with self.opener.open(req, timeout=self.timeout) as response:
                    public_url(response.url)
                    if int(response.headers.get("Content-Length", "0")) > max_bytes:
                        raise RMBaseError("response_too_large", "Use a narrower query or an official dataset.", 5)
                    raw = response.read(max_bytes + 1)
                    if len(raw) > max_bytes:
                        raise RMBaseError("response_too_large", "Response exceeded the byte limit; no partial data returned.", 5)
                    meta = {"url": response.url, "method": method, "parameters": params,
                            "status": response.status, "retrieved_at": utc_now(),
                            "cached_epoch": time.time(), "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytes": len(raw), "cache_hit": False,
                            "last_modified": response.headers.get("Last-Modified"),
                            "etag": response.headers.get("ETag"),
                            "transport": urllib.parse.urlsplit(response.url).scheme}
                    self.sources.append(meta)
                    if cache:
                        atomic_write(data_file, raw)
                        atomic_write(cache_file, json.dumps(meta, sort_keys=True).encode())
                    return raw
            except urllib.error.HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After")
                exc.close()
                # A server rate limit is a stopping signal, not a retry opportunity.
                if status == 429 or retry_after:
                    raise RMBaseError("rate_limited", "RMBase asked the client to stop; retry later.", 3,
                                      http_status=status, retry_after=retry_after, endpoint=url) from exc
                if retry and status in (502, 503, 504) and attempt < self.retries:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise RMBaseError("http_error", f"RMBase returned HTTP {status}.", 3,
                                  http_status=status, endpoint=url, submission_may_have_reached_server=not retry) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if retry and attempt < self.retries:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise RMBaseError("network_error", "RMBase request failed or timed out.", 3,
                                  endpoint=url, submission_may_have_reached_server=not retry) from exc
        raise RMBaseError("network_error", "Read retries exhausted.", 3)
