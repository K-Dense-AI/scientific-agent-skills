"""Released client behavior with network dispatch mocked; no hosted jobs are submitted."""
from unittest.mock import MagicMock

import pytest

cloud = pytest.importorskip("tiledb.cloud")
pa = pytest.importorskip("pyarrow")


def test_distributed_read_returns_arrow_after_wait(monkeypatch):
    from tiledb.cloud.vcf import query

    expected = pa.table({"sample_name": ["S1"], "pos_start": [1]})
    graph, result = MagicMock(), MagicMock()
    result.result.return_value = expected
    build = MagicMock(return_value=(graph, result))
    run = MagicMock()
    monkeypatch.setattr(query, "build_read_dag", build)
    monkeypatch.setattr(query, "run_dag", run)
    actual = query.read("tiledb://example/cohort", attrs=["sample_name", "pos_start"],
                        regions=["chr1:1-100"], samples=["S1"],
                        num_region_partitions=2, namespace="example")
    assert actual is expected
    assert build.call_args.kwargs["num_region_partitions"] == 2
    assert build.call_args.kwargs["namespace"] == "example"
    run.assert_called_once_with(graph, debug=False)


def test_ingest_submission_is_asynchronous(monkeypatch):
    from tiledb.cloud import dag
    from tiledb.cloud.vcf import ingestion

    graph = MagicMock(namespace="example", server_graph_uuid="synthetic-graph")
    factory = MagicMock(return_value=graph)
    monkeypatch.setattr(dag, "DAG", factory)
    result = ingestion.ingest("s3://example/cohort", sample_list_uri="s3://example/list.txt",
                              namespace="example", acn="example-role")
    assert result == {"status": "started", "graph_id": "synthetic-graph"}
    assert graph.submit.call_args.args[0] is ingestion.ingest_vcf
    assert graph.submit.call_args.kwargs["sample_list_uri"] == "s3://example/list.txt"
    graph.compute.assert_called_once_with()
    graph.wait.assert_not_called()


def test_ingest_requires_one_source_before_network():
    from tiledb.cloud.vcf.ingestion import ingest_vcf

    with pytest.raises(ValueError, match="Exactly one"):
        ingest_vcf("s3://example/cohort", search_uri="s3://example/source",
                   sample_list_uri="s3://example/list.txt")


def test_auth_config_converts_token_for_native_client(monkeypatch):
    from tiledb.cloud import client, config

    fake = MagicMock(host="https://api.tiledb.com", username="", password="",
                     api_key={"X-TILEDB-REST-API-KEY": "synthetic-test-token"})
    monkeypatch.setattr(config, "config", fake)
    native = client.Config()
    assert native["rest.server_address"] == "https://api.tiledb.com"
    assert native["rest.token"] == "synthetic-test-token"


@pytest.mark.parametrize("api_name,method,args,path,response_type", [
    ("UdfApi", "submit_generic_udf", ("example", {"language": "python"}),
     "/v1/udfs/generic/{namespace}", "file"),
    ("TaskGraphsApi", "create_task_graph", ("example", {"name": "synthetic"}),
     "/v1/taskgraphs/{namespace}/graphs", "TaskGraph"),
    ("TaskGraphsApi", "submit_task_graph", ("example", "synthetic-graph"),
     "/v1/taskgraphs/{namespace}/graphs/{id}/submit", "TaskGraphLog"),
])
def test_sdk_http_dispatch_contract(api_name, method, args, path, response_type):
    from tiledb.cloud import rest_api

    transport = MagicMock()
    api = getattr(rest_api, api_name)(transport)
    getattr(api, method)(*args)
    call = transport.call_api.call_args
    assert call.args[:2] == (path, "POST")
    assert call.args[2]["namespace"] == "example"
    assert call.args[3] == []  # Job submission has no pagination query.
    assert call.kwargs["response_type"] == response_type
    assert "ApiKeyAuth" in call.kwargs["auth_settings"]
    assert call.kwargs["body"] == (None if method == "submit_task_graph" else args[1])
