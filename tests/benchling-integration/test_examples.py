"""Execute documented Python examples against the real SDK and an offline transport."""
import csv
import json
from pathlib import Path
import re

import pytest

pytest.importorskip("benchling_sdk")
pytest.importorskip("Bio")
import httpx
from benchling_sdk.auth.api_key_auth import ApiKeyAuth
from benchling_sdk.benchling import Benchling

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "benchling-integration"


@pytest.fixture
def offline_sdk(monkeypatch, tmp_path):
    """Only synthetic records and dummy credentials; no network is possible."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sequences.fasta").write_text(">external-001\nATCG\n")
    for key, value in {
        "BENCHLING_TENANT_URL": "https://example.benchling.com",
        "BENCHLING_API_KEY": "dummy-key",
        "BENCHLING_CLIENT_ID": "dummy-client",
        "BENCHLING_CLIENT_SECRET": "dummy-secret",
    }.items():
        monkeypatch.setenv(key, value)
    calls = []
    dna = {"id": "seq_example", "name": "Construct 001", "bases": "ATCG",
           "entityRegistryId": "CONSTRUCT001"}
    keys = {"dna-sequences": "dnaSequences", "containers": "containers",
            "entries": "entries", "workflow-tasks": "workflowTasks",
            "projects": "projects", "events": "events"}

    def respond(request):
        assert request.url.host == "example.benchling.com"
        body = json.loads(request.content) if request.content and request.headers.get(
            "content-type", "").startswith("application/json") else None
        calls.append((request.method, request.url.path, dict(request.url.params), body))
        path = request.url.path.removeprefix("/api/v2/")
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "dummy-token", "expires_in": 900,
                                             "token_type": "Bearer"})
        if path.startswith("tasks/"):
            return httpx.Response(200, json={"status": "SUCCEEDED", "response": {}})
        if path == "transfers":
            return httpx.Response(202, json={"taskId": "task_transfer"})
        if path in {"containers:check-in", "containers:check-out"}:
            return httpx.Response(200, json={})
        if path == "dna-sequences:archive":
            return httpx.Response(200, json={"dnaSequenceIds": body["dnaSequenceIds"]})
        if request.method == "GET" and path in keys:
            if path == "events":
                rows = []
            elif path == "dna-sequences":
                rows = [dict(dna, id="seq_page2" if request.url.params.get("nextToken") else "seq_page1")]
            else:
                rows = [{"id": "example_id", "name": "Example", "barcode": "BARCODE"}]
            token = "second" if path == "dna-sequences" and not request.url.params.get("nextToken") else ""
            return httpx.Response(200, json={keys[path]: rows, "nextToken": token},
                                  headers={"result-count": "2"})
        record = {"id": "example_id", "name": "Example", "barcode": "BARCODE"}
        if path.startswith("dna-sequences"):
            record = dict(dna)
        if body:
            record.update(body)
        if request.method == "GET" and path.startswith("entries/"):
            record = {"entry": record}
        return httpx.Response(201 if request.method == "POST" else 200, json=record)

    original_client = httpx.Client
    clients = []

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(respond)
        client = original_client(*args, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "Client", client_factory)
    client = Benchling(url="https://example.benchling.com", auth_method=ApiKeyAuth("dummy-key"))
    yield {"benchling": client}, calls, tmp_path
    for client in clients:
        client.close()


def execute_examples(path, scope):
    snippets = re.findall(r"```python\n(.*?)```", path.read_text(), flags=re.S)
    for index, snippet in enumerate(snippets):
        exec(compile(snippet, f"{path.name}:example-{index + 1}", "exec"), scope)
    return len(snippets)


@pytest.mark.parametrize("document", [
    "SKILL.md", "references/sdk_reference.md", "references/authentication.md",
    "references/api_endpoints.md", "references/eventbridge.md",
])
def test_python_examples_use_valid_sdk_calls_and_payloads(document, offline_sdk):
    scope, calls, tmp_path = offline_sdk
    assert execute_examples(SKILL_ROOT / document, scope) > 0
    if document == "SKILL.md":
        with (tmp_path / "sequences.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        assert [row["id"] for row in rows] == ["seq_page1", "seq_page2"]
        assert all(row["length"] == "4" for row in rows)
    elif document.endswith("sdk_reference.md"):
        payloads = {(method, path): body for method, path, _, body in calls}
        create = payloads["POST", "/api/v2/dna-sequences"]
        assert create["fields"]["gene_name"] == {"value": "GFP"}
        assert create["registryId"] == "src_example"
        assert create["namingStrategy"] == "NEW_IDS"
        assert "entityRegistryId" not in create
        assert payloads["POST", "/api/v2/workflow-tasks"]["workflowTaskGroupId"] == "wtg_example"
        transfer = payloads["POST", "/api/v2/transfers"]["transfers"][0]
        assert transfer["transferQuantity"] == {"value": 5.0, "units": "uL"}
        assert payloads["POST", "/api/v2/containers:check-out"]["assigneeId"] == "usr_example"
        assert payloads["POST", "/api/v2/containers:check-in"]["comments"] == "Returned"
        assert not any(method != "GET" and "/tasks/" in path for method, path, _, _ in calls)
    elif document.endswith("authentication.md"):
        # Construction is lazy: OAuth is replaced before the first request here.
        assert any(path == "/api/v2/projects" for _, path, _, _ in calls)
    elif document.endswith("api_endpoints.md"):
        assert len(calls) == 2
        assert calls[1][2]["nextToken"] == "second"
        assert calls[1][2]["schemaId"] == calls[0][2]["schemaId"]
    elif document.endswith("eventbridge.md"):
        handler = scope["handler"]
        assert handler({"detail-type": "v2.request.created",
                        "detail": {"request": {"id": "req_test"}}}, None)["request_id"] == "req_test"
        with pytest.raises(ValueError, match="request.id"):
            handler({"detail-type": "v2.request.created", "detail": {}}, None)
        assert handler({"detail-type": "unsupported", "detail": {}}, None)["status"] == "ignored"
