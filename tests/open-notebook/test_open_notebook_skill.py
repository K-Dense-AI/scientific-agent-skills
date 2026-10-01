"""Behavioral regressions for the Open Notebook v1.14.0 REST helpers."""

import importlib
import json
from pathlib import Path
import re
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "open-notebook"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
common = importlib.import_module("_common")
notebooks = importlib.import_module("notebook_management")
sources = importlib.import_module("source_ingestion")
chat = importlib.import_module("chat_interaction")
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


@pytest.mark.parametrize("base", ["https://notebook.example", "https://notebook.example/",
                                  "https://notebook.example/api", "https://notebook.example/api/"])
def test_base_url_avoids_duplicate_api(monkeypatch, base):
    monkeypatch.setenv("OPEN_NOTEBOOK_URL", base)
    assert common.api_url() == "https://notebook.example/api"


def test_auth_timeout_and_http_check(monkeypatch):
    monkeypatch.setenv("OPEN_NOTEBOOK_URL", "https://notebook.example")
    monkeypatch.setenv("OPEN_NOTEBOOK_PASSWORD", "test-password")
    response = MagicMock(status_code=200)
    response.__enter__.return_value = response
    response.json.return_value = {"id": "notebook:a"}
    with patch.object(common.requests, "request", return_value=response) as send:
        assert notebooks.create_notebook("Study")["id"] == "notebook:a"
    args, kwargs = send.call_args
    assert args == ("POST", "https://notebook.example/api/notebooks")
    assert kwargs["headers"] == {"Authorization": "Bearer test-password"}
    assert kwargs["timeout"] == (10, 300)
    assert kwargs["allow_redirects"] is False
    response.raise_for_status.assert_called_once()
    response.close.assert_not_called()  # context manager owns success cleanup


def test_unconfigured_password_sends_no_auth(monkeypatch):
    monkeypatch.delenv("OPEN_NOTEBOOK_PASSWORD", raising=False)
    with patch.object(common.requests, "request", return_value=MagicMock(status_code=200)) as send:
        common.request("GET", "/notebooks")
    assert "Authorization" not in send.call_args.kwargs["headers"]


def test_http_failure_is_not_decoded():
    response = MagicMock(status_code=401)
    response.raise_for_status.side_effect = requests.HTTPError("unauthorized")
    with patch.object(common.requests, "request", return_value=response):
        with pytest.raises(requests.HTTPError):
            common.request_json("GET", "/notebooks")
    response.json.assert_not_called()
    response.close.assert_called_once()


def test_redirect_is_not_treated_as_success():
    response = MagicMock(status_code=307)
    with patch.object(common.requests, "request", return_value=response):
        with pytest.raises(requests.HTTPError, match="redirect"):
            common.request_json("POST", "/sources", data={})
    response.json.assert_not_called()
    response.close.assert_called_once()


def test_ids_are_one_path_segment():
    assert common.record_path("source:a/b?#") == "source%3Aa%2Fb%3F%23"


def test_delete_uses_exclusive_flag_and_preview():
    preview = {"note_count": 2, "exclusive_source_count": 1, "shared_source_count": 3}
    result = {"deleted_notes": 2, "deleted_sources": 1}
    with patch.object(notebooks, "request_json", side_effect=[preview, result]) as send:
        assert notebooks.delete_notebook("notebook:a", True) == result
    assert send.call_args_list[0].args == ("GET", "/notebooks/notebook%3Aa/delete-preview")
    assert send.call_args_list[1].kwargs["params"] == {"delete_exclusive_sources": "true"}


def test_failed_preview_does_not_delete():
    with patch.object(notebooks, "request_json", side_effect=requests.HTTPError()) as send:
        with pytest.raises(requests.HTTPError):
            notebooks.delete_notebook("notebook:a")
    assert send.call_count == 1


def test_notebook_false_values_survive_partial_update():
    with patch.object(notebooks, "request_json") as send:
        notebooks.update_notebook("notebook:a", description="", archived=False)
    assert send.call_args.kwargs["json"] == {"description": "", "archived": False}


def test_notebook_listing_can_include_archived():
    with patch.object(notebooks, "request_json") as send:
        notebooks.list_notebooks()
        assert send.call_args.kwargs["params"] == {}
        notebooks.list_notebooks(False)
        assert send.call_args.kwargs["params"] == {"archived": "false"}


def test_link_source_request():
    with patch.object(notebooks, "request_json") as send:
        notebooks.link_source_to_notebook("notebook:a", "source:b")
        assert send.call_args.args == ("POST", "/notebooks/notebook%3Aa/sources/source%3Ab")
        notebooks.unlink_source_from_notebook("notebook:a", "source:b")
        assert send.call_args.args[0] == "DELETE"


def test_url_source_required_type_and_async_fields():
    with patch.object(sources, "request_json", return_value={"id": "source:a"}) as send:
        sources.add_url_source("notebook:a", "https://example.org/paper", embed=True)
    assert send.call_args.args == ("POST", "/sources")
    assert send.call_args.kwargs["data"] == {
        "type": "link", "notebooks": '["notebook:a"]', "async_processing": "true",
        "embed": "true", "url": "https://example.org/paper",
    }


def test_text_source_preserves_title_and_content():
    with patch.object(sources, "request_json") as send:
        sources.add_text_source("notebook:a", "Methods", "24 samples")
    data = send.call_args.kwargs["data"]
    assert data["type"] == "text"
    assert data["title"] == "Methods"
    assert data["content"] == "24 samples"
    assert data["async_processing"] == "false" and data["embed"] == "false"


def test_upload_bytes_and_close(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF fixture")
    seen = []
    def receive(*args, **kwargs):
        name, handle = kwargs["files"]["file"]
        assert name == "paper.pdf" and handle.read() == b"%PDF fixture"
        assert kwargs["data"]["type"] == "upload"
        seen.append(handle)
        return {"id": "source:a"}
    with patch.object(sources, "request_json", side_effect=receive):
        assert sources.upload_file_source("notebook:a", pdf)["id"] == "source:a"
    assert seen[0].closed


def test_source_pagination_does_not_stop_at_default_limit():
    with patch.object(sources, "request_json", side_effect=[[{"id": "a"}, {"id": "b"}],
                                                           [{"id": "c"}]]) as send:
        assert [s["id"] for s in sources.iter_sources("notebook:a", 2)] == ["a", "b", "c"]
    assert [call.kwargs["params"]["offset"] for call in send.call_args_list] == [0, 2]
    assert all(call.kwargs["params"]["sort_by"] == "created" for call in send.call_args_list)


def test_source_pagination_rejects_repeated_ids_before_yielding_duplicate():
    with patch.object(sources, "request_json", return_value=[{"id": "a"}]) as send:
        records = sources.iter_sources(page_size=1)
        assert next(records) == {"id": "a"}
        with pytest.raises(RuntimeError, match="Repeated source IDs"):
            next(records)
    assert send.call_count == 2


def test_source_pagination_cap_does_not_claim_completion():
    with patch.object(sources, "request_json", side_effect=[[{"id": "a"}], [{"id": "b"}]]) as send:
        with pytest.raises(RuntimeError, match="completeness is unknown"):
            list(sources.iter_sources(page_size=1, max_pages=2))
    assert send.call_count == 2


@pytest.mark.parametrize("page", [{"data": []}, [None], [{}], [{"id": ""}],
                                  [{"id": "a"}, {"id": "a"}], [{"id": 123}],
                                  [{"id": "a"}, {"id": "b"}, {"id": "c"}]])
def test_source_pagination_rejects_malformed_page(page):
    with patch.object(sources, "request_json", return_value=page):
        with pytest.raises(RuntimeError):
            list(sources.iter_sources(page_size=2))


@pytest.mark.parametrize("max_pages", [0, -1, True, 1.5])
def test_source_pagination_rejects_invalid_cap(max_pages):
    with patch.object(sources, "request_json") as send:
        with pytest.raises(ValueError):
            list(sources.iter_sources(max_pages=max_pages))
    send.assert_not_called()


@pytest.mark.parametrize("limit,offset", [(0, 0), (101, 0), (20, -1)])
def test_invalid_page_rejected(limit, offset):
    with pytest.raises(ValueError):
        sources.list_sources(limit=limit, offset=offset)


def test_poll_queued_then_completed():
    with patch.object(sources, "request_json", side_effect=[{"status": "queued"},
                                                           {"status": "completed"}]), \
         patch.object(sources.time, "sleep"):
        assert sources.wait_for_processing("source:a")["status"] == "completed"


def test_poll_failure_is_not_returned_as_success():
    with patch.object(sources, "request_json", return_value={"status": "failed", "message": "Extraction failed"}):
        with pytest.raises(RuntimeError, match="failed"):
            sources.wait_for_processing("source:a")


def test_legacy_null_status_requires_extracted_text():
    with patch.object(sources, "request_json", side_effect=[{"status": None, "command_id": None},
                                                           {"full_text": "Evidence"}]):
        assert sources.wait_for_processing("source:a")["status"] is None
    with patch.object(sources, "request_json", side_effect=[{"status": None}, {"full_text": None}]):
        with pytest.raises(RuntimeError, match="no extracted text"):
            sources.wait_for_processing("source:a")


def test_poll_timeout_uses_elapsed_clock():
    with patch.object(sources.time, "monotonic", side_effect=[0, 0, 10]), \
         patch.object(sources, "request_json", return_value={"status": "unknown", "command_id": "command:a"}):
        with pytest.raises(TimeoutError):
            sources.wait_for_processing("source:a", timeout=5)


@pytest.mark.parametrize("option", ["timeout", "poll_interval"])
@pytest.mark.parametrize("value", [float("inf"), float("nan"), 0])
def test_poll_rejects_unbounded_timing(option, value):
    with patch.object(sources, "request_json") as send:
        with pytest.raises(ValueError, match="finite and positive"):
            sources.wait_for_processing("source:a", **{option: value})
    send.assert_not_called()


@pytest.mark.parametrize("state", ["running", "queued", "unknown", None, "completed"])
def test_retry_does_not_duplicate_active_or_unknown_job(state):
    with patch.object(sources, "request_json", return_value={"status": state}) as send:
        with pytest.raises(ValueError):
            sources.retry_failed_source("source:a")
    assert send.call_count == 1


def test_failed_job_can_be_explicitly_retried():
    with patch.object(sources, "request_json", side_effect=[{"status": "failed"}, {"status": "queued"}]) as send:
        assert sources.retry_failed_source("source:a")["status"] == "queued"
    assert send.call_args.args == ("POST", "/sources/source%3Aa/retry")


def test_context_selection_is_built_before_chat():
    with patch.object(chat, "request_json") as send:
        chat.build_context("notebook:a", ["source:a"], [])
    assert send.call_args.kwargs["json"] == {
        "notebook_id": "notebook:a",
        "context_config": {"sources": {"source:a": "full content"}, "notes": {}},
    }


def test_empty_selection_differs_from_default_context():
    with patch.object(chat, "request_json") as send:
        chat.build_context("notebook:a")
        assert send.call_args.kwargs["json"]["context_config"] == {}
        chat.build_context("notebook:a", [], [])
        assert send.call_args.kwargs["json"]["context_config"] == {"sources": {}, "notes": {}}


def test_chat_reads_ai_message_content(capsys):
    result = {"session_id": "chat_session:a", "messages": [
        {"type": "human", "content": "Question"}, {"type": "ai", "content": "Answer"}]}
    context = {"sources": [{"id": "source:a", "full_text": "Evidence"}], "notes": []}
    with patch.object(chat, "request_json", return_value=result) as send:
        assert chat.send_chat_message("chat_session:a", "Question", context) == result
    assert send.call_args.kwargs["json"]["context"] == context
    assert capsys.readouterr().out.strip() == "Answer"


def test_fake_context_flags_rejected():
    with pytest.raises(ValueError):
        chat.send_chat_message("chat_session:a", "Question", {"include_sources": True})


def test_search_uses_current_names_and_response():
    result = {"results": [{"id": "source:a"}], "total_count": 1, "search_type": "vector"}
    with patch.object(chat, "request_json", return_value=result) as send:
        assert chat.search_knowledge_base("design", minimum_score=0.7) == result
    assert send.call_args.kwargs["json"] == {
        "query": "design", "type": "vector", "limit": 5,
        "search_sources": True, "search_notes": True, "minimum_score": 0.7,
    }


def test_ask_requires_explicit_models_and_question():
    with patch.object(chat, "request_json", return_value={"answer": "Evidence", "question": "Design?"}) as send:
        assert chat.ask_question("Design?", "model:a", "model:b", "model:c")["answer"] == "Evidence"
    assert send.call_args.kwargs["json"] == {
        "question": "Design?", "strategy_model": "model:a", "answer_model": "model:b",
        "final_answer_model": "model:c",
    }


def _example_functions(filename):
    """Load illustrative function definitions only; no API operation runs at import."""
    text = (SKILL_ROOT / "references" / filename).read_text()
    blocks = re.findall(r"```python\n(.*?)```", text, flags=re.S)
    namespace = {}
    for block in blocks:
        exec(compile(block, filename, "exec"), namespace)
    return namespace


def test_credential_discovery_and_registration_shape(monkeypatch):
    examples = _example_functions("configuration.md")
    monkeypatch.setenv("OPENAI_API_KEY", "provider-test-key")
    responses = [{"id": "credential:a"}, {"success": True},
                 {"discovered": [{"name": "chosen", "provider": "openai", "model_type": None}]},
                 {"created": 1, "existing": 0}]
    send = MagicMock(side_effect=responses)
    examples["request_json"] = send
    assert examples["register_openai_language_model"]("chosen")[0] == "credential:a"
    assert send.call_args.kwargs["json"] == {
        "models": [{"name": "chosen", "provider": "openai", "model_type": "language"}]}


def test_podcast_example_nested_result_and_binary_download(tmp_path):
    examples = _example_functions("examples.md")
    send = MagicMock(side_effect=[{"job_id": "command:a"},
                                 {"status": "completed", "result": {"episode_id": "episode:a"}}])
    response = MagicMock()
    response.__enter__.return_value = response
    response.headers = {"Content-Type": "audio/mpeg"}
    response.iter_content.return_value = [b"audio", b" bytes"]
    examples["request_json"] = send
    examples["request"] = MagicMock(return_value=response)
    target = tmp_path / "podcast.mp3"
    assert examples["generate_podcast"]("Evidence", "Episode profile", "Cast", target) == "episode:a"
    assert target.read_bytes() == b"audio bytes"
    assert send.call_args_list[0].kwargs["json"]["speaker_profile"] == "Cast"
    assert examples["request"].call_args.args == ("GET", "/podcasts/episodes/episode%3Aa/audio")


def test_podcast_failure_does_not_download(tmp_path):
    examples = _example_functions("examples.md")
    examples["request_json"] = MagicMock(side_effect=[{"job_id": "command:a"},
                                                     {"status": "failed", "error_message": "TTS failed"}])
    examples["request"] = MagicMock()
    with pytest.raises(RuntimeError, match="TTS failed"):
        examples["generate_podcast"]("Evidence", "Episode", "Cast", tmp_path / "bad.mp3")
    examples["request"].assert_not_called()


def test_research_workflow_stops_when_extraction_is_empty():
    examples = _example_functions("examples.md")
    examples["create_notebook"] = MagicMock(return_value={"id": "notebook:a"})
    examples["add_url_source"] = MagicMock(return_value={"id": "source:a"})
    examples["wait_for_processing"] = MagicMock()
    examples["request_json"] = MagicMock(return_value={"full_text": None})
    examples["build_context"] = MagicMock()
    with pytest.raises(RuntimeError, match="no research text"):
        examples["research_workflow"]("https://example.org/paper")
    examples["build_context"].assert_not_called()


def test_research_workflow_saves_ai_message_with_provenance_title():
    examples = _example_functions("examples.md")
    examples["create_notebook"] = MagicMock(return_value={"id": "notebook:a"})
    examples["add_url_source"] = MagicMock(return_value={"id": "source:a"})
    examples["wait_for_processing"] = MagicMock()
    examples["request_json"] = MagicMock(side_effect=[{"full_text": "Evidence"}, {"id": "note:a"}])
    context = {"sources": [{"id": "source:a", "full_text": "Evidence"}], "notes": []}
    examples["build_context"] = MagicMock(return_value={"context": context, "token_count": 5})
    examples["create_chat_session"] = MagicMock(return_value={"id": "chat_session:a"})
    examples["send_chat_message"] = MagicMock(return_value={"messages": [{"type": "ai", "content": "Draft"}]})
    assert examples["research_workflow"]("https://example.org/paper")["note"]["id"] == "note:a"
    assert examples["request_json"].call_args.kwargs["json"]["content"] == "Draft"
    assert examples["send_chat_message"].call_args.args[2] == context


def test_transformation_example_reads_output_and_registered_model():
    examples = _example_functions("examples.md")
    examples["request_json"] = MagicMock(side_effect=[{"id": "transformation:a"}, {"output": "Draft"}])
    assert examples["extract_methods"]("Evidence", "model:a") == "Draft"
    assert examples["request_json"].call_args.kwargs["json"] == {
        "transformation_id": "transformation:a", "input_text": "Evidence", "model_id": "model:a"}


def test_search_example_uses_global_ask_response():
    examples = _example_functions("examples.md")
    examples["search_knowledge_base"] = MagicMock(return_value={"total_count": 1, "results": [{"id": "source:a"}]})
    examples["request_json"] = MagicMock(return_value={"default_chat_model": "model:a", "default_embedding_model": "model:e"})
    examples["ask_question"] = MagicMock(return_value={"answer": "Draft"})
    assert examples["search_and_answer"]("Design?") == (1, [{"id": "source:a"}], "Draft")
    examples["ask_question"].assert_called_once_with("Design?", "model:a", "model:a", "model:a")
