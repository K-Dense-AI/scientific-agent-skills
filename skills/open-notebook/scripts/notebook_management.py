"""Notebook helpers using requests; running this file lists notebooks only.

Usage: uv run --isolated --with requests python notebook_management.py --help
Set OPEN_NOTEBOOK_URL to the backend origin and OPEN_NOTEBOOK_PASSWORD if enabled.
"""

import argparse
import json

from _common import record_path, request_json


def create_notebook(name, description=""):
    return request_json("POST", "/notebooks", json={
        "name": name, "description": description,
    })


def list_notebooks(archived=None):
    """Return all notebooks; a supplied bool filters active/archived notebooks."""
    params = {} if archived is None else {"archived": str(archived).lower()}
    return request_json("GET", "/notebooks", params=params)


def get_notebook(notebook_id):
    return request_json("GET", f"/notebooks/{record_path(notebook_id)}")


def update_notebook(notebook_id, name=None, description=None, archived=None):
    payload = {key: value for key, value in {
        "name": name, "description": description, "archived": archived,
    }.items() if value is not None}
    return request_json("PUT", f"/notebooks/{record_path(notebook_id)}", json=payload)


def delete_notebook(notebook_id, delete_sources=False):
    """Delete notebook, its notes/chats, and optionally its exclusive sources.

    The Python argument is retained for compatibility; the API query parameter is
    delete_exclusive_sources. Inspect the returned counts, not a guessed count.
    """
    path = f"/notebooks/{record_path(notebook_id)}"
    preview = request_json("GET", path + "/delete-preview")
    print(f"Deleting {preview['note_count']} notes; "
          f"{preview['exclusive_source_count']} exclusive and "
          f"{preview['shared_source_count']} shared sources affected")
    return request_json("DELETE", path, params={
        "delete_exclusive_sources": str(delete_sources).lower(),
    })


def link_source_to_notebook(notebook_id, source_id):
    """Associate a source; verify membership before repeatedly linking it."""
    return request_json("POST", f"/notebooks/{record_path(notebook_id)}"
                        f"/sources/{record_path(source_id)}")


def unlink_source_from_notebook(notebook_id, source_id):
    return request_json("DELETE", f"/notebooks/{record_path(notebook_id)}"
                        f"/sources/{record_path(source_id)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archived", choices=["true", "false"])
    args = parser.parse_args()
    archived = None if args.archived is None else args.archived == "true"
    print(json.dumps(list_notebooks(archived), indent=2))


if __name__ == "__main__":
    main()
