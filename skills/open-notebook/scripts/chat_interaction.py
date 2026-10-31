"""Context-aware chat and search helpers for Open Notebook v1.14.0.

Requires requests. CLI lists a notebook's chat sessions; AI calls are explicit
Python function calls. Set OPEN_NOTEBOOK_URL and optional OPEN_NOTEBOOK_PASSWORD.
"""

import argparse
import json

from _common import record_path, request_json


def create_chat_session(notebook_id, title, model_override=None):
    payload = {"notebook_id": notebook_id, "title": title}
    if model_override:
        payload["model_override"] = model_override
    return request_json("POST", "/chat/sessions", json=payload)


def list_chat_sessions(notebook_id):
    return request_json("GET", "/chat/sessions", params={"notebook_id": notebook_id})


def build_context(notebook_id, source_ids=None, note_ids=None):
    """Build explicit full-text context from selected IDs.

    None/None requests upstream's default short context for all notebook items.
    Empty lists select no items. Check returned IDs/content: upstream can skip
    unavailable records without failing the whole request.
    """
    config = {}
    if source_ids is not None or note_ids is not None:
        config = {
            "sources": {sid: "full content" for sid in source_ids or []},
            "notes": {nid: "full content" for nid in note_ids or []},
        }
    return request_json("POST", "/chat/context", json={
        "notebook_id": notebook_id, "context_config": config,
    })


def send_chat_message(session_id, message, context, model_override=None):
    """Send the built context dict (not the wrapper and not include_* flags)."""
    if not isinstance(context, dict) or not {"sources", "notes"}.issubset(context):
        raise ValueError("Pass build_context(...)[\"context\"] with sources and notes")
    payload = {"session_id": session_id, "message": message, "context": context}
    if model_override:
        payload["model_override"] = model_override
    result = request_json("POST", "/chat/execute", json=payload)
    for msg in reversed(result["messages"]):
        if msg["type"] == "ai":
            print(msg["content"])
            break
    return result


def get_session_history(session_id):
    return request_json("GET", f"/chat/sessions/{record_path(session_id)}")


def search_knowledge_base(query, search_type="vector", limit=5, minimum_score=0.2):
    """Search globally on v1.14.0; unknown scope fields would be ignored there."""
    if search_type not in {"text", "vector"}:
        raise ValueError("search_type must be text or vector")
    if not 1 <= limit <= 1000 or not 0 <= minimum_score <= 1:
        raise ValueError("limit must be 1..1000 and minimum_score must be 0..1")
    return request_json("POST", "/search", json={
        "query": query, "type": search_type, "limit": limit,
        "search_sources": True, "search_notes": True, "minimum_score": minimum_score,
    })


def ask_question(question, strategy_model, answer_model, final_answer_model):
    """Use registered model record IDs for all three required Ask stages."""
    return request_json("POST", "/search/ask/simple", json={
        "question": question, "strategy_model": strategy_model,
        "answer_model": answer_model, "final_answer_model": final_answer_model,
    })


def delete_chat_session(session_id):
    return request_json("DELETE", f"/chat/sessions/{record_path(session_id)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook_id")
    args = parser.parse_args()
    print(json.dumps(list_chat_sessions(args.notebook_id), indent=2))


if __name__ == "__main__":
    main()
