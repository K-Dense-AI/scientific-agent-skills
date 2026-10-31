"""Source ingestion helpers; CLI lists sources without creating demo records.

Requires requests and a running Open Notebook backend with a processing worker.
Set OPEN_NOTEBOOK_URL and, when enabled, OPEN_NOTEBOOK_PASSWORD.
"""

import argparse
import json
import math
from pathlib import Path
import time

from _common import record_path, request_json


def _source_fields(notebook_id, source_type, process_async, embed):
    return {
        "type": source_type,
        "notebooks": json.dumps([notebook_id]),
        "async_processing": str(process_async).lower(),
        "embed": str(embed).lower(),
    }


def add_url_source(notebook_id, url, process_async=True, embed=False):
    data = _source_fields(notebook_id, "link", process_async, embed)
    data["url"] = url
    return request_json("POST", "/sources", data=data)


def add_text_source(notebook_id, title, text, process_async=False, embed=False):
    data = _source_fields(notebook_id, "text", process_async, embed)
    data.update(title=title, content=text)
    return request_json("POST", "/sources", data=data)


def upload_file_source(notebook_id, file_path, process_async=True, embed=False):
    path = Path(file_path)
    with path.open("rb") as handle:
        return request_json("POST", "/sources",
                            data=_source_fields(notebook_id, "upload", process_async, embed),
                            files={"file": (path.name, handle)})


def wait_for_processing(source_id, poll_interval=5, timeout=300):
    """Return completed status; raise on failure, unknown legacy state or timeout.

    Status=None with no command can describe synchronous/legacy sources. Confirm
    full_text exists before treating those as complete. Embeddings need a separate
    embedded_chunks check if vector retrieval is required.
    """
    if not all(math.isfinite(value) and value > 0 for value in (timeout, poll_interval)):
        raise ValueError("timeout and poll_interval must be finite and positive")
    deadline = time.monotonic() + timeout
    path = f"/sources/{record_path(source_id)}"
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Source {source_id} processing timed out")
        status = request_json("GET", path + "/status", timeout=min(30, remaining))
        state = status.get("status")
        if state == "completed":
            return status
        if state in {"failed", "error", "canceled", "cancelled"}:
            raise RuntimeError(f"Source {source_id} processing {state}: {status.get('message', '')}")
        if state is None and not status.get("command_id"):
            source = request_json("GET", path, timeout=max(0.001, min(30, deadline - time.monotonic())))
            if source.get("full_text"):
                return status
            raise RuntimeError(f"Source {source_id} has no command and no extracted text")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Source {source_id} processing timed out")
        time.sleep(min(poll_interval, remaining))


def list_sources(notebook_id=None, limit=20, offset=0):
    """Return one page. /sources supports 1..100 rows and zero-based offsets."""
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError("limit must be 1..100 and offset must be nonnegative")
    params = {"limit": limit, "offset": offset, "sort_by": "created", "sort_order": "asc"}
    if notebook_id:
        params["notebook_id"] = notebook_id
    return request_json("GET", "/sources", params=params)


def iter_sources(notebook_id=None, page_size=100, max_pages=1000):
    """Paginate a stable collection, raising on malformed/repeated pages or the cap.

    Writes during iteration may shift pages. Discard partial results after an error;
    an empty or short page is required to establish completion within max_pages.
    """
    if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages < 1:
        raise ValueError("max_pages must be a positive integer")
    offset = 0
    seen_ids = set()
    for _ in range(max_pages):
        page = list_sources(notebook_id, page_size, offset)
        if not isinstance(page, list) or len(page) > page_size:
            raise RuntimeError("Invalid source page: expected a list within the requested limit")
        page_ids = []
        for source in page:
            source_id = source.get("id") if isinstance(source, dict) else None
            if not isinstance(source_id, str) or not source_id:
                raise RuntimeError("Invalid source page: each record must have a nonempty string id")
            page_ids.append(source_id)
        if len(set(page_ids)) != len(page_ids) or seen_ids.intersection(page_ids):
            raise RuntimeError("Repeated source IDs: collection changed or pagination did not advance")
        seen_ids.update(page_ids)
        yield from page
        if len(page) < page_size:
            return
        offset += len(page)
    raise RuntimeError("Source pagination reached max_pages; completeness is unknown")


def get_source_insights(source_id):
    return request_json("GET", f"/sources/{record_path(source_id)}/insights")


def retry_failed_source(source_id):
    """Retry once after inspecting failure; upstream retry always requests embedding."""
    path = f"/sources/{record_path(source_id)}"
    status = request_json("GET", path + "/status")
    if status.get("status") not in {"failed", "error"}:
        raise ValueError("Retry only a confirmed failed source; inspect active/unknown jobs first")
    return request_json("POST", path + "/retry")


def delete_source(source_id):
    return request_json("DELETE", f"/sources/{record_path(source_id)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook-id")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(list_sources(args.notebook_id, args.limit, args.offset), indent=2))


if __name__ == "__main__":
    main()
