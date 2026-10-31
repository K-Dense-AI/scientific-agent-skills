"""Dependency-free, mocked-network tests for protocols.io helper scripts."""

from __future__ import annotations

import io
import json
import os
import stat
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills" / "protocolsio-integration"
TESTS_DIR = Path(__file__).resolve().parent
FIXTURES = TESTS_DIR / "fixtures"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import (  # noqa: E402
    pagination_helper,
    plan_write_request,
    protocols_read,
    validate_auth_config,
    validate_protocol_json,
)
from scripts._common import (  # noqa: E402
    ACCESS_TOKEN_ENV,
    MAX_JSON_RESPONSE_BYTES,
    NoRedirectHandler,
    SafetyError,
    load_local_json,
    request_bytes,
    sanitize_untrusted,
    validate_origin,
)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        url: str,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.url = url
        self.headers = headers or {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        }
        self._stream = io.BytesIO(body)

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def getcode(self) -> int:
        return self.status


class SequenceOpener:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.requests: list[object] = []

    def open(self, request: object, timeout: float) -> object:
        del timeout
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class ScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_cwd = Path.cwd()
        os.chdir(REPO_ROOT)

    def tearDown(self) -> None:
        os.chdir(self.previous_cwd)

    def test_all_help_paths_are_dependency_free(self) -> None:
        modules = (
            validate_auth_config,
            pagination_helper,
            validate_protocol_json,
            plan_write_request,
            protocols_read,
        )
        for module in modules:
            output = io.StringIO()
            with self.subTest(module=module.__name__), redirect_stdout(output):
                with self.assertRaises(SystemExit) as raised:
                    module.main(["--help"])
                self.assertEqual(raised.exception.code, 0)
                self.assertIn("usage:", output.getvalue())

    def test_auth_validator_reports_presence_without_values(self) -> None:
        environment = {
            "PROTOCOLS_IO_ACCESS_TOKEN": "value-access",
            "UNRELATED_SETTING": "value-unrelated",
        }
        code, report = validate_auth_config.validate_config(
            origin="https://www.protocols.io",
            tenant_origin="https://tenant.protocols.io",
            requirement="read",
            environ=environment,
        )
        serialized = json.dumps(report)
        self.assertEqual(code, 0)
        self.assertNotIn("value-", serialized)
        self.assertFalse(report["network_accessed"])
        self.assertFalse(report["dotenv_loaded"])

    def test_origin_allowlist_is_https_only(self) -> None:
        self.assertEqual(
            validate_origin("https://www.protocols.io"),
            "https://www.protocols.io",
        )
        self.assertEqual(
            validate_origin(
                "https://tenant.protocols.io",
                allow_tenant=True,
            ),
            "https://tenant.protocols.io",
        )
        for origin in (
            "http://www.protocols.io",
            "https://example.org",
            "https://www.protocols.io.evil.example",
            "https://user@www.protocols.io",
        ):
            with self.subTest(origin=origin), self.assertRaises(SafetyError):
                validate_origin(origin, allow_tenant=True)

    def test_pagination_rejects_untrusted_next_host_and_path(self) -> None:
        base = {
            "pagination": {
                "current_page": 1,
                "total_pages": 2,
                "total_results": 2,
                "page_size": 1,
            }
        }
        valid = {
            **base,
            "pagination": {
                **base["pagination"],
                "next_page": (
                    "https://protocols.io/api/v3/protocols?filter=public&page_id=2"
                ),
            },
        }
        report = pagination_helper.inspect_pagination(
            valid,
            current_url=(
                "https://www.protocols.io/api/v3/protocols?filter=public&page_id=1"
            ),
            pages_seen=1,
            items_seen=1,
            max_pages=3,
            max_items=10,
        )
        self.assertTrue(report["can_continue"])

        for next_page in (
            "https://evil.example/api/v3/protocols?page_id=2",
            "https://www.protocols.io/api/v3/oauth/clients/x",
            "http://www.protocols.io/api/v3/protocols?page_id=2",
            ("https://www.protocols.io/api/v3/protocols?filter=user_private&page_id=2"),
        ):
            payload = {
                "pagination": {
                    **base["pagination"],
                    "next_page": next_page,
                }
            }
            with self.subTest(next_page=next_page), self.assertRaises(SafetyError):
                pagination_helper.inspect_pagination(
                    payload,
                    current_url=("https://www.protocols.io/api/v3/protocols?page_id=1"),
                    pages_seen=1,
                    items_seen=1,
                    max_pages=3,
                    max_items=10,
                )

    def test_offline_protocol_summary_preserves_version_and_attribution(self) -> None:
        payload = load_local_json(
            "tests/protocolsio-integration/fixtures/protocol_response.json"
        )
        schema = load_local_json(
            "skills/protocolsio-integration/assets/protocol-snapshot.schema.json"
        )
        report = validate_protocol_json.validate_and_summarize(
            payload,
            require_version=True,
            max_steps=100,
        )
        self.assertEqual(
            schema["$id"],
            "https://scientific-agent-skills.local/protocolsio/"
            "protocol-snapshot.schema.json",
        )
        self.assertEqual(
            report["schema_asset"],
            "assets/protocol-snapshot.schema.json",
        )
        protocol = report["protocol"]
        self.assertTrue(protocol["version_specific"])
        self.assertEqual(
            protocol["attribution"]["version_uri"],
            "example-protocol-abcd1234/v2",
        )
        self.assertEqual(protocol["attribution"]["authors"], ["Example Author"])
        self.assertFalse(report["embedded_instructions_followed"])
        self.assertFalse(report["network_accessed"])

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"protocol": {}, "protocol": {}}', encoding="utf-8")
            relative = path.relative_to(REPO_ROOT)
            with self.assertRaises(SafetyError):
                load_local_json(str(relative))

    def test_write_planner_redacts_and_never_executes(self) -> None:
        sensitive_value = "value-" + "redacted"
        payload = {
            "title": "Updated title",
            "client_secret": sensitive_value,
        }
        report = plan_write_request.build_plan(
            operation="update-protocol",
            target="example-protocol",
            payload=payload,
            origin="https://www.protocols.io",
            tenant_origin=None,
            upload_file=None,
            local_max_upload_bytes=1_000_000,
            confirmation=None,
        )
        serialized = json.dumps(report)
        self.assertNotIn(sensitive_value, serialized)
        self.assertIn("$.client_secret", report["redacted_sensitive_paths"])
        self.assertFalse(report["network_accessed"])
        self.assertFalse(report["request_executed"])
        self.assertFalse(report["execution_supported"])

    def test_write_planner_requires_exact_confirmation(self) -> None:
        kwargs = {
            "operation": "delete-steps",
            "target": "example-protocol",
            "payload": {
                "steps": ["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"],
            },
            "origin": "https://www.protocols.io",
            "tenant_origin": None,
            "upload_file": None,
            "local_max_upload_bytes": 1_000_000,
        }
        first = plan_write_request.build_plan(**kwargs, confirmation=None)
        phrase = first["confirmation"]["phrase"]
        second = plan_write_request.build_plan(
            **kwargs,
            confirmation=phrase,
        )
        self.assertFalse(first["ready_for_separate_execution_review"])
        self.assertTrue(second["confirmation"]["confirmed"])
        self.assertTrue(second["ready_for_separate_execution_review"])
        self.assertFalse(second["execution_supported"])

    def test_publish_plan_requires_protocol_uri_not_doi(self) -> None:
        with self.assertRaises(SafetyError):
            plan_write_request.build_plan(
                operation="publish-protocol",
                target="protocols.io.example/v1",
                payload={},
                origin="https://www.protocols.io",
                tenant_origin=None,
                upload_file=None,
                local_max_upload_bytes=1_000_000,
                confirmation=None,
            )

    def test_upload_plan_hashes_bounded_local_file_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as directory:
            path = Path(directory) / "sample.bin"
            path.write_bytes(b"sample")
            report = plan_write_request.build_plan(
                operation="upload-file",
                target=None,
                payload={},
                origin="https://www.protocols.io",
                tenant_origin=None,
                upload_file=str(path.relative_to(REPO_ROOT)),
                local_max_upload_bytes=100,
                confirmation=None,
            )
        self.assertEqual(report["upload"]["size_bytes"], 6)
        self.assertFalse(report["upload"]["service_limit_asserted"])
        self.assertIn("REDACTED", json.dumps(report["phases"]))
        self.assertFalse(report["request_executed"])

    def test_read_plan_does_not_touch_network_or_credentials(self) -> None:
        args = protocols_read.build_parser().parse_args(
            ["get", "--id", "example-protocol/v2"]
        )
        plan = protocols_read._plan(args)
        self.assertFalse(plan["network_accessed"])
        self.assertIn("/api/v4/protocols/example-protocol/v2", plan["url"])
        self.assertNotIn("Authorization", json.dumps(plan))

    def test_documented_full_doi_reads_preserve_version_path(self) -> None:
        for command in ("get", "steps"):
            args = protocols_read.build_parser().parse_args(
                [command, "--id", "10.17504/protocols.io.example/v2"]
            )
            plan = protocols_read._plan(args)
            suffix = "/steps" if command == "steps" else ""
            self.assertEqual(
                plan["url"],
                "https://www.protocols.io/api/v4/protocols/"
                f"10.17504/protocols.io.example/v2{suffix}?content_format=json",
            )
        for identifier in (
            "10.99999/protocols.io.example/v1",
            "example/../../oauth/token",
        ):
            args = protocols_read.build_parser().parse_args(["get", "--id", identifier])
            with self.subTest(identifier=identifier), self.assertRaises(SafetyError):
                protocols_read._plan(args)

    def test_offline_validator_accepts_current_v4_and_legacy_envelopes(self) -> None:
        protocol = json.loads((FIXTURES / "protocol_response.json").read_text())[
            "protocol"
        ]
        for payload in (
            protocol,
            {"payload": protocol, "status_code": 0},
            {"payload": {"protocol": protocol}, "status_code": 0},
            {"protocol": protocol, "status_code": 0},
        ):
            report = validate_protocol_json.validate_and_summarize(
                payload,
                require_version=True,
                max_steps=100,
            )
            self.assertEqual(report["protocol"]["counts"]["steps"]["count"], 2)
            self.assertEqual(report["protocol"]["identifiers"]["id"], 12345)
        protocol["doi"] = ""
        report = validate_protocol_json.validate_and_summarize(
            {"payload": protocol},
            require_version=True,
            max_steps=100,
        )
        self.assertIsNone(report["protocol"]["identifiers"]["doi"])
        for bad_doi in (0, False, []):
            with self.subTest(doi=bad_doi), self.assertRaises(SafetyError):
                validate_protocol_json.validate_and_summarize(
                    {"payload": {**protocol, "doi": bad_doi}},
                    require_version=True,
                    max_steps=100,
                )

    def test_mutation_plans_use_endpoint_specific_identifiers_and_encoding(
        self,
    ) -> None:
        common = {
            "origin": "https://www.protocols.io",
            "tenant_origin": None,
            "upload_file": None,
            "local_max_upload_bytes": 1_000_000,
            "confirmation": None,
        }
        for operation, target, payload, encoding in (
            ("create-protocol", "A" * 32, {}, "application/x-www-form-urlencoded"),
            (
                "add-comment",
                "example",
                {"body": "Reviewed comment"},
                "application/x-www-form-urlencoded",
            ),
            ("trash-files", None, {"ids": [123]}, "application/x-www-form-urlencoded"),
            (
                "update-protocol",
                "example",
                {"title": "Reviewed title"},
                "application/json",
            ),
            ("delete-comment", "123", {}, None),
        ):
            plan = plan_write_request.build_plan(
                operation=operation,
                target=target,
                payload=payload,
                **common,
            )
            self.assertEqual(plan["headers"].get("Content-Type"), encoding)
            self.assertFalse(plan["execution_supported"])
        for target in (
            "10.17504/protocols.io.example/v2",
            "protocols.io.example",
            "example/v2",
            "example/latest",
        ):
            with self.subTest(target=target), self.assertRaises(SafetyError):
                plan_write_request.build_plan(
                    operation="update-protocol",
                    target=target,
                    payload={"title": "Reviewed title"},
                    **common,
                )
        common["confirmation"] = "CONFIRM publish-protocol example"
        plan = plan_write_request.build_plan(
            operation="publish-protocol",
            target="example",
            payload={"prepublish": 1},
            **common,
        )
        self.assertTrue(plan["confirmation"]["confirmed"])
        self.assertFalse(plan["ready_for_separate_execution_review"])
        self.assertNotIn("Content-Type", plan["headers"])

    def test_step_plan_supports_current_optional_fields(self) -> None:
        step = {
            "guid": "A" * 32,
            "previous_guid": None,
            "step": "Reviewed step",
            "section_color": "#A1B2C3",
            "is_substep": True,
        }
        plan_write_request._validate_steps({"steps": [step]}, deleting=False)
        for field, bad in (("section_color", "not a color"), ("is_substep", "true")):
            with self.subTest(field=field), self.assertRaises(SafetyError):
                plan_write_request._validate_steps(
                    {"steps": [{**step, field: bad}]}, deleting=False
                )

    def test_pdf_rejects_doi_and_marks_filtered_export_partial(self) -> None:
        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as directory:
            output = str((Path(directory) / "subset.pdf").relative_to(REPO_ROOT))
            args = protocols_read.build_parser().parse_args(
                [
                    "export-pdf",
                    "--id",
                    "10.17504/protocols.io.example/v2",
                    "--output",
                    output,
                ]
            )
            with self.assertRaises(SafetyError):
                protocols_read._plan(args)
            args = protocols_read.build_parser().parse_args(
                [
                    "--execute",
                    "export-pdf",
                    "--id",
                    "example",
                    "--only",
                    "steps",
                    "--anonymous",
                    "--output",
                    output,
                ]
            )
            plan = protocols_read._plan(args)
            self.assertTrue(plan["url"].endswith(".pdf?only_steps=1"))
            opener = SequenceOpener(
                [
                    FakeResponse(
                        b"%PDF-1.7\nmock",
                        url=plan["url"],
                        headers={"Content-Type": "application/pdf"},
                    )
                ]
            )
            report = protocols_read.execute(
                args, plan, environ={}, opener=opener, sleep=lambda _: None
            )
            self.assertTrue(report["partial_export"])
            self.assertEqual(report["pdf_filter"], "steps")
            self.assertEqual(report["source_url"], plan["url"])
            self.assertIsNone(opener.requests[0].get_header("Authorization"))

    def test_mocked_get_uses_named_token_without_emitting_it(self) -> None:
        credential = "-".join(("unit", "test", "bearer"))
        body = (FIXTURES / "protocol_response.json").read_bytes()
        url = (
            "https://www.protocols.io/api/v4/protocols/"
            "example-protocol/v2?content_format=json"
        )
        opener = SequenceOpener([FakeResponse(body, url=url)])
        args = protocols_read.build_parser().parse_args(
            ["--execute", "get", "--id", "example-protocol/v2"]
        )
        plan = protocols_read._plan(args)
        report = protocols_read.execute(
            args,
            plan,
            environ={ACCESS_TOKEN_ENV: credential},
            opener=opener,
            sleep=lambda _: None,
        )
        self.assertTrue(report["network_accessed"])
        self.assertEqual(len(opener.requests), 1)
        request = opener.requests[0]
        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer " + credential,
        )
        self.assertNotIn(credential, json.dumps(report))

    def test_mocked_list_follows_only_validated_bounded_page(self) -> None:
        first_url = (
            "https://www.protocols.io/api/v3/protocols?"
            "filter=public&key=test&page_size=1&page_id=1"
        )
        second_url = (
            "https://www.protocols.io/api/v3/protocols?"
            "filter=public&key=test&page_size=1&page_id=2"
        )
        first = json.dumps(
            {
                "status_code": 0,
                "items": [{"id": 1, "title": "untrusted one"}],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 2,
                    "total_results": 2,
                    "next_page": second_url,
                    "prev_page": None,
                    "page_size": 1,
                },
            }
        ).encode()
        second = json.dumps(
            {
                "status_code": 0,
                "items": [{"id": 2, "title": "untrusted two"}],
                "pagination": {
                    "current_page": 2,
                    "total_pages": 2,
                    "total_results": 2,
                    "next_page": None,
                    "prev_page": first_url,
                    "page_size": 1,
                },
            }
        ).encode()
        opener = SequenceOpener(
            [
                FakeResponse(first, url=first_url),
                FakeResponse(second, url=second_url),
            ]
        )
        args = protocols_read.build_parser().parse_args(
            [
                "--execute",
                "list",
                "--query",
                "test",
                "--page-size",
                "1",
                "--max-pages",
                "2",
                "--max-items",
                "2",
            ]
        )
        plan = protocols_read._plan(args)
        report = protocols_read.execute(
            args,
            plan,
            environ={ACCESS_TOKEN_ENV: "unit-test"},
            opener=opener,
            sleep=lambda _: None,
        )
        self.assertEqual(report["request_count"], 2)
        self.assertEqual(report["returned_items"], 2)
        self.assertEqual(len(opener.requests), 2)
        self.assertFalse(report["embedded_instructions_followed"])

    def test_retry_after_is_capped_and_attempts_are_bounded(self) -> None:
        url = "https://www.protocols.io/api/v4/protocols/example"
        error = urllib.error.HTTPError(
            url,
            429,
            "Too Many Requests",
            {"Retry-After": "9999", "Content-Type": "application/json"},
            io.BytesIO(b'{"status_code": 1, "error_message": "slow down"}'),
        )
        opener = SequenceOpener(
            [
                error,
                FakeResponse(b'{"status_code": 0}', url=url),
            ]
        )
        delays: list[float] = []
        result = request_bytes(
            url,
            token="unit-test",
            accept="application/json",
            retries=1,
            opener=opener,
            sleep=delays.append,
        )
        self.assertEqual(result.attempts, 2)
        self.assertEqual(delays, [30.0])

    def test_response_size_cap_is_enforced(self) -> None:
        url = "https://www.protocols.io/api/v4/protocols/example"
        opener = SequenceOpener(
            [
                FakeResponse(
                    b"{}",
                    url=url,
                    headers={
                        "Content-Type": "application/json",
                        "Content-Length": str(MAX_JSON_RESPONSE_BYTES + 1),
                    },
                )
            ]
        )
        with self.assertRaises(SafetyError):
            request_bytes(
                url,
                token="unit-test",
                accept="application/json",
                max_bytes=MAX_JSON_RESPONSE_BYTES,
                retries=0,
                opener=opener,
            )

    def test_mocked_pdf_export_writes_private_file(self) -> None:
        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as directory:
            output = Path(directory) / "protocol.pdf"
            relative = output.relative_to(REPO_ROOT)
            args = protocols_read.build_parser().parse_args(
                [
                    "--execute",
                    "export-pdf",
                    "--id",
                    "example-protocol",
                    "--output",
                    str(relative),
                ]
            )
            plan = protocols_read._plan(args)
            opener = SequenceOpener(
                [
                    FakeResponse(
                        b"%PDF-1.7\nmock",
                        url=plan["url"],
                        headers={
                            "Content-Type": "application/pdf",
                            "Content-Length": "13",
                        },
                    )
                ]
            )
            report = protocols_read.execute(
                args,
                plan,
                environ={ACCESS_TOKEN_ENV: "unit-test"},
                opener=opener,
                sleep=lambda _: None,
            )
            mode = stat.S_IMODE(output.stat().st_mode)
            self.assertEqual(mode, 0o600)
            self.assertEqual(report["bytes_written"], 13)

    def test_sanitizer_redacts_remote_credential_fields(self) -> None:
        sensitive_value = "value-" + "redacted"
        result = sanitize_untrusted(
            {
                "title": "safe",
                "access_token": sensitive_value,
                "nested": {"Signature": sensitive_value + "-either"},
            }
        )
        serialized = json.dumps(result)
        self.assertNotIn(sensitive_value, serialized)
        self.assertEqual(result["access_token"], "[REDACTED]")

    def test_redirect_handler_refuses_redirects(self) -> None:
        handler = NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(
                object(),
                object(),
                302,
                "Found",
                {},
                "https://example.org/",
            )
        )


if __name__ == "__main__":
    unittest.main()
