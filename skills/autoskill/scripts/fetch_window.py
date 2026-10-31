import warnings

_MAX_PAGES = 10_000  # bounded exit: hard ceiling so the loop cannot spin forever


def fetch_window(client, start_time, end_time, page_size=50, token=None):
    """Fetch local timeline rows; memories/parsed records are not activity events."""
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
        raise ValueError("page_size must be a positive integer")
    events = []
    skipped_types = set()
    offset = 0
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for _page in range(_MAX_PAGES):
        response = client.get("/search", params={
            "start_time": start_time,
            "end_time": end_time,
            "limit": page_size,
            "offset": offset,
            "content_type": "all",
            "include_frames": "false",
            "include_cloud": "false",
            # Upstream filter_pii can use a remote enclave. Redact locally instead.
            "filter_pii": "false",
        }, headers=headers)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        pagination = payload.get("pagination", {})
        total = pagination.get("total")
        if (not isinstance(data, list) or isinstance(total, bool)
                or not isinstance(total, int) or total < 0):
            raise ValueError("Screenpipe /search must return data[] and pagination.total")
        if pagination.get("offset", offset) != offset:
            raise ValueError("Screenpipe /search returned an unexpected pagination offset")

        for item in data:
            content = item.get("content", {})
            kind = item.get("type", "").lower()
            if kind not in {"ocr", "ui", "accessibility", "input", "audio"}:
                skipped_types.add(kind or "unknown")
                continue
            if not content.get("timestamp"):
                raise ValueError(f"Screenpipe {kind} row has no timestamp")
            events.append({
                "ts": content.get("timestamp"),
                "app": content.get("app_name") or "",
                "window_title": content.get("window_name") or content.get("window_title") or "",
                "text": content.get("text") or content.get("transcription") or content.get("text_content") or "",
                "content_type": kind,
            })

        offset += len(data)
        if offset >= total:
            break
        if not data:
            raise RuntimeError("Screenpipe search ended before pagination.total; rerun a fixed time window")
    else:
        raise RuntimeError("Screenpipe search exceeded the page limit; request a smaller time window")
    if skipped_types:
        warnings.warn("Skipped non-timeline Screenpipe types: " + ", ".join(sorted(skipped_types)),
                      stacklevel=2)
    return events
