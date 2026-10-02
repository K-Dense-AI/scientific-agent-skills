"""Offline contracts, real-response parser regressions, and bounded request tests.

Fixtures were captured on 2026-09-23. No test contacts production RMBase.
Task tests deliberately assert the unverified boundary, not an invented lifecycle.
"""

from __future__ import annotations

import hashlib
import io
import json
import socket
import sys
import tarfile
import urllib.error
from pathlib import Path

import pytest
import skill_contract

sys.dont_write_bytecode = True
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "rmbase"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import client
import datasets
import parsers
import rmbase
import transport

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not open network connections")
    monkeypatch.setattr(socket, "create_connection", blocked)


def fixture(name):
    return (FIXTURES / name).read_bytes()


class Response(io.BytesIO):
    def __init__(self, raw, url=transport.BASE + "ajaxFiles/getModGeneRes.php", headers=None):
        super().__init__(raw)
        self.url, self.status = url, 200
        self.headers = headers or {"Content-Length": str(len(raw))}


class Opener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return Response(item, request.full_url)


def make_client(tmp_path, monkeypatch, *responses, **options):
    opener = Opener(*responses)
    http = transport.Transport(tmp_path, retries=0, opener=opener)
    monkeypatch.setattr(http, "_pace", lambda: None)
    return client.Client(http, **options), opener


def archive_bytes(data, name="genes.tsv", kind=tarfile.REGTYPE):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name)
        info.type, info.size = kind, len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_gene_query_parameters_data_and_provenance(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path, monkeypatch, fixture("gene.json"))
    result = c.gene("METTL3")
    assert result["records"][0]["totalNum"] == 61
    assert result["records"][0]["geneID"] == "ENSG00000165819.12"
    assert result["records"][0]["m6aNum"] == 59
    assert opener.requests[0].get_method() == "POST"
    assert opener.requests[0].data == b"assembly=hg38&genename=METTL3&genome=Homo+sapiens&mode=genename"
    assert result["provenance"]["genome_assembly"] == "hg38"
    assert result["provenance"]["sources"][0]["sha256"] == hashlib.sha256(fixture("gene.json")).hexdigest()


def test_gene_absence_has_no_biological_absence_claim(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, fixture("empty.json"))
    result = c.gene("UNKNOWN_GENE")
    assert result["status"] == "no_records"
    assert result["pagination"]["complete"]
    assert any("biological absence" in note for note in result["warnings"])


@pytest.mark.parametrize("assembly,species", [("hg19", None), ("hg38", "Mus musculus"), ("../hg38", None)])
def test_assembly_errors_precede_network(tmp_path, monkeypatch, assembly, species):
    c, opener = make_client(tmp_path, monkeypatch, assembly=assembly, species=species)
    with pytest.raises(transport.RMBaseError):
        c.gene("METTL3")
    assert not opener.requests


@pytest.mark.parametrize("name", ["", "all", "ALL", "METTL3;whoami", "METTL3\nFOO", "../gene"])
def test_unbounded_or_malformed_gene_rejected(tmp_path, monkeypatch, name):
    c, opener = make_client(tmp_path, monkeypatch)
    with pytest.raises(transport.RMBaseError):
        c.gene(name)
    assert not opener.requests


def test_gene_sites_reconcile_59_records(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path, monkeypatch, fixture("gene.json"), fixture("gene-sites.html"), limit=100)
    result = c.gene("METTL3", modification="m6a")
    assert len(result["records"]) == 59
    assert result["provenance"]["access_mode"] == "HTML_ADAPTER"
    assert any(r["Mod ID"] == "m6A_site_239470" for r in result["records"])
    assert "geneid=ENSG00000165819.12" in opener.requests[1].full_url


def test_count_mismatch_fails_visibly(tmp_path, monkeypatch):
    altered = json.loads(fixture("gene.json"))
    altered[0]["m6aNum"] = 60
    c, _ = make_client(tmp_path, monkeypatch, json.dumps(altered).encode(), fixture("gene-sites.html"))
    with pytest.raises(transport.RMBaseError, match="counts disagree"):
        c.gene("METTL3", modification="m6a")


def test_modification_detail_handles_nested_tables_and_publications(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, fixture("modification.html"))
    row = c.modification("m6A_site_239470", "m6a")["records"][0]
    assert row["fields"]["mod Site"] == "chr14:21503347-21503348:-"
    assert row["fields"]["Writer Name List"] == "METTL14,METTL3"
    assert row["pmids"]
    assert len(row["related_tables"][0]["records"]) == 10
    assert row["related_tables"][1]["records"][1]["Writer Name"] == "METTL3"


def test_missing_modification_does_not_accept_echoed_id_or_placeholder_support(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, fixture("modification-missing.html"))
    result = c.modification("m6A_site_0", "m6a")
    assert result["status"] == "no_records"
    assert result["records"] == []


@pytest.mark.parametrize("raw", [b"<html>maintenance</html>", b"{}", b"null", b'[1]', b'[{"geneName":"METTL3"}]'])
def test_unexpected_json_is_error_not_empty(tmp_path, monkeypatch, raw):
    c, _ = make_client(tmp_path, monkeypatch, raw)
    with pytest.raises(transport.RMBaseError) as error:
        c.gene("METTL3")
    assert error.value.code == "schema_changed"


def test_html_structure_change_is_not_no_records():
    changed = fixture("gene-sites.html").replace(b'id="resultTable"', b'id="changed"')
    with pytest.raises(transport.RMBaseError, match="missing or changed"):
        parsers.gene_sites(changed)


def test_motif_html_fields_are_data_and_local_pages_are_explicit(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path, monkeypatch, fixture("motif.json"), limit=3)
    result = c.lookup("motif", "m6A")
    assert result["pagination"] == {"kind": "local", "total_records": 8, "returned_records": 3,
                                    "offset": 0, "limit": 3, "complete": False, "next_offset": 3}
    assert result["records"][0]["matrix"]["links"][0].endswith(".motif")
    c.offset = 3
    second = c.lookup("motif", "m6A")
    assert len(opener.requests) == 1  # Next page reuses the full cached array.
    assert second["provenance"]["sources"][-1]["cache_hit"]


def test_enzyme_records_are_not_gene_modification_counts(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, fixture("enzyme.json"))
    result = c.lookup("enzyme", "METTL3")
    assert result["command"] == "enzyme"
    assert all(r["writerName"] == "METTL3" for r in result["records"])
    assert "totalNum" not in result["records"][0]


def test_cancer_nested_json_retains_unspecified_coordinate_assembly(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, fixture("cancer.json"))
    result = c.cancer("METTL3")
    assert result["records"][0]["Tumor"] == "BRCA"
    assert result["provenance"]["genome_assembly"] is None


def test_local_gene_archive_matches_remote_counts(tmp_path, monkeypatch):
    raw = archive_bytes(fixture("genes.tsv"))
    c, opener = make_client(tmp_path, monkeypatch, raw)
    meta = c.datasets.sync("hg38")
    assert meta["rows"] == 2
    result = c.gene("METTL3")
    assert result["records"][0]["totalNum"] == 61
    assert len(result["records"][0]["m6aList"]) == 59
    assert result["provenance"]["access_mode"] == "LOCAL_DATASET"
    assert len(opener.requests) == 1
    assert c.datasets.sync("hg38") == meta
    assert len(opener.requests) == 1


def test_local_only_missing_dataset_never_uses_network(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path, monkeypatch)
    with pytest.raises(transport.RMBaseError) as error:
        c.gene("METTL3", source="local")
    assert error.value.code == "dataset_missing"
    assert not opener.requests


def test_local_gene_ids_can_be_queried_offline(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, archive_bytes(fixture("genes.tsv")), limit=100)
    c.datasets.sync("hg38")
    c.http.offline = True
    result = c.gene("ENSG00000165819.12", mode="geneid", modification="m6a")
    assert len(result["records"]) == 59
    assert all(row["geneName"] == "METTL3" for row in result["records"])


def test_archive_traversal_path_is_never_extracted(tmp_path):
    rows = list(datasets.archive_rows(archive_bytes(fixture("genes.tsv"), "../../escape.txt"), "genes"))
    assert len(rows) == 2
    assert not (tmp_path.parent / "escape.txt").exists()


def test_archive_links_rejected():
    with pytest.raises(transport.RMBaseError):
        list(datasets.archive_rows(archive_bytes(b"", "link.tsv", tarfile.SYMTYPE), "genes"))


def test_bad_dataset_schema_rejected():
    with pytest.raises(transport.RMBaseError, match="22 columns"):
        list(datasets.archive_rows(archive_bytes(b"a\tb\n"), "genes"))


def test_cached_dataset_checksum_mismatch_is_error(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, archive_bytes(fixture("genes.tsv")))
    c.datasets.sync("hg38")
    path, _ = c.datasets.paths("hg38", "genes")
    path.write_bytes(b"corrupted")
    with pytest.raises(transport.RMBaseError, match="checksum"):
        c.gene("METTL3")


def test_timeout_is_structured_and_retry_count_is_bounded(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path, monkeypatch, TimeoutError(), TimeoutError())
    c.http.retries = 1
    monkeypatch.setattr(transport.time, "sleep", lambda _: None)
    with pytest.raises(transport.RMBaseError) as error:
        c.gene("METTL3")
    assert error.value.code == "network_error"
    assert len(opener.requests) == 2


def test_http_429_never_retries(tmp_path, monkeypatch):
    err = urllib.error.HTTPError(transport.BASE, 429, "rate limit", {"Retry-After": "60"}, None)
    c, opener = make_client(tmp_path, monkeypatch, err)
    c.http.retries = 2
    with pytest.raises(transport.RMBaseError) as error:
        c.gene("METTL3")
    assert error.value.code == "rate_limited"
    assert error.value.details["retry_after"] == "60"
    assert len(opener.requests) == 1


def test_maximum_response_bytes_prevents_partial_success(tmp_path, monkeypatch):
    c, _ = make_client(tmp_path, monkeypatch, b"x" * 20)
    with pytest.raises(transport.RMBaseError) as error:
        c.http.request("modgene.php", max_bytes=10)
    assert error.value.exit_code == 5


@pytest.mark.parametrize("url", ["https://example.com/rmbase/", "file:///etc/passwd", "http://bioinformaticsscience.cn/rmbase/../admin", "http://bioinformaticsscience.cn/rmbase/%2e%2e/admin", "http://user@bioinformaticsscience.cn/rmbase/"])
def test_url_boundary(url):
    with pytest.raises(transport.RMBaseError):
        transport.public_url(url)


def test_cached_response_can_be_used_offline_with_original_timestamp(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path, monkeypatch, fixture("gene.json"))
    first = c.gene("METTL3")
    c.http.offline = True
    second = c.gene("METTL3")
    assert len(opener.requests) == 1
    assert second["provenance"]["sources"][-1]["retrieved_at"] == first["provenance"]["sources"][0]["retrieved_at"]


def test_shared_rate_limit_applies_across_clients(tmp_path, monkeypatch):
    clock = [100.0]
    sleeps = []
    monkeypatch.setattr(transport.time, "time", lambda: clock[0])
    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(transport.time, "sleep", sleep)
    transport.Transport(tmp_path)._pace()
    transport.Transport(tmp_path)._pace()
    assert sleeps == [2.0]


GOOD_BED = b"chr1\t853842\t853902\tregion_1\t0\t+\n"


@pytest.mark.parametrize("bed", [b"", b"chr1 0 1 region 0 +", b"chr1\t10\t1\tx\t0\t+\n", b"chr1\t-1\t2\tx\t0\t+\n", b"chr1\t0\t2\tx\t1001\t+\n", GOOD_BED + GOOD_BED])
def test_malformed_bed_rejected(bed):
    with pytest.raises(transport.RMBaseError) as error:
        parsers.validate_bed(bed)
    assert error.value.code == "invalid_bed"


def test_annotation_upload_uses_observed_fields_once_and_reports_503(tmp_path, monkeypatch):
    err = urllib.error.HTTPError(transport.BASE, 503, "Service Unavailable", {}, None)
    c, opener = make_client(tmp_path / "cache", monkeypatch, err)
    c.http.retries = 2
    path = tmp_path / "public.bed"
    path.write_bytes(GOOD_BED)
    with pytest.raises(transport.RMBaseError) as error:
        c.submit("annotation", path, public_data=True)
    assert error.value.details["http_status"] == 503
    assert len(opener.requests) == 1
    req = opener.requests[0]
    assert req.full_url.endswith("/cgi-bin/runModAnno.pl")
    assert b'name="Species"\r\n\r\nhg38' in req.data
    assert b'name="bedInputFile"' in req.data
    assert GOOD_BED in req.data


def test_invalid_bed_is_rejected_before_upload(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path / "cache", monkeypatch)
    path = tmp_path / "bad.bed"
    path.write_bytes(b"bad\n")
    with pytest.raises(transport.RMBaseError, match="Invalid BED6"):
        c.submit("annotation", path, public_data=True)
    assert not opener.requests


def test_unknown_successful_task_response_is_not_fabricated(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path / "cache", monkeypatch, b"<html>Queued</html>")
    path = tmp_path / "public.bed"
    path.write_bytes(GOOD_BED)
    with pytest.raises(transport.RMBaseError) as error:
        c.submit("annotation", path, public_data=True)
    assert error.value.code == "unverified_task_response"
    assert len(opener.requests) == 1


def test_task_id_contract_is_explicitly_unverified(tmp_path, monkeypatch):
    c, opener = make_client(tmp_path, monkeypatch)
    with pytest.raises(transport.RMBaseError) as error:
        c.task("example-task-id")
    assert error.value.exit_code == 7
    assert not opener.requests


def test_cli_argument_errors_are_json(capsys):
    assert rmbase.main(["gene", "METTL3", "--limit", "bad"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["code"] == "invalid_arguments"


def test_cli_offline_miss_and_exit_code(tmp_path, capsys):
    code = rmbase.main(["gene", "METTL3", "--offline", "--cache-dir", str(tmp_path)])
    assert code == 6
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "offline_cache_miss"


def test_tsv_requires_a_provenance_sidecar(capsys):
    assert rmbase.main(["catalog", "--tsv"]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "provenance_required"


def test_tsv_quoting_preserves_embedded_tabs():
    output = rmbase.tsv_text([{"a": "x\ty", "b": ["z"]}])
    assert '"x\ty"' in output


def test_catalog_has_distinct_species_and_no_hg19():
    assert len(client.CATALOG["modules"]["gene"]["assemblies"]) == 62
    assert client.context("gene", "mm10")["species"] == "Mus musculus"
    with pytest.raises(transport.RMBaseError):
        client.context("gene", "hg19")
