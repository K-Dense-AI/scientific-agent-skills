from __future__ import annotations

import argparse
import copy
import importlib.util
import io
import json
import os
import re
import stat
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path
from unittest import mock

import skill_contract


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "ncats-arax"
SCRIPT = SKILL_ROOT / "scripts" / "arax_client.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_client():
    spec = importlib.util.spec_from_file_location("ncats_arax_client", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


client = _load_client()
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_json(name: str):
    return json.loads(fixture_bytes(name).decode("utf-8"))


def one_hop_body(**overrides):
    values = {
        "subject_id": "CHEBI:31690",
        "subject_category": "biolink:SmallMolecule",
        "predicates": ["biolink:affects"],
        "object_id": "NCBIGene:25",
        "object_category": "biolink:Gene",
        "qualifiers": [
            ("biolink:object_aspect_qualifier", "activity_or_abundance"),
            ("biolink:object_direction_qualifier", "decreased"),
        ],
        "mode": "lookup",
        "provider_ids": ["infores:rtx-kg2"],
        "result_limit": 20,
    }
    values.update(overrides)
    return client.build_one_hop_query(**values)


def two_hop_body(**overrides):
    values = {
        "subject_id": "CHEBI:66901",
        "subject_category": "biolink:SmallMolecule",
        "predicates_1": ["biolink:affects"],
        "intermediate_category": "biolink:Gene",
        "predicates_2": ["biolink:associated_with"],
        "object_id": "MONDO:0009061",
        "object_category": "biolink:Disease",
        "qualifiers_1": [
            ("biolink:object_aspect_qualifier", "activity_or_abundance"),
            ("biolink:object_direction_qualifier", "increased"),
        ],
        "qualifiers_2": [],
        "mode": "lookup",
        "provider_ids": ["infores:rtx-kg2"],
        "expand_order": "right-first",
        "result_limit": 20,
    }
    values.update(overrides)
    return client.build_two_hop_query(**values)


def service_info(warnings=()):
    return client.ServiceInfo(
        base_url=client.PRODUCTION_BASE_URL,
        openapi_url=client.PRODUCTION_BASE_URL + "/openapi.json",
        arax_version="1.5.4",
        trapi_version="1.5.0",
        warnings=tuple(warnings),
    )


def one_hop_args(output_dir: Path, **overrides):
    values = {
        "command": "one-hop",
        "subject_id": "CHEBI:31690",
        "subject_category": "biolink:SmallMolecule",
        "predicate": ["biolink:affects"],
        "object_id": "NCBIGene:25",
        "object_category": "biolink:Gene",
        "qualifier": [],
        "mode": "lookup",
        "kp": [],
        "result_limit": 20,
        "acknowledge_public_query": True,
        "output_dir": str(output_dir),
        "base_url": client.PRODUCTION_BASE_URL,
        "allow_nonproduction_endpoint": False,
        "allow_untested_version": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def normalize_args(output_dir: Path, **overrides):
    values = {
        "term": "ivacaftor",
        "expected_category": "biolink:SmallMolecule",
        "max_synonyms": 10,
        "acknowledge_public_query": True,
        "output_dir": str(output_dir),
        "base_url": client.PRODUCTION_BASE_URL,
        "allow_nonproduction_endpoint": False,
        "allow_untested_version": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class FakeResponse:
    def __init__(self, body: bytes, *, status: int = 200, headers=None):
        self.body = io.BytesIO(body)
        self.status = status
        self.headers = headers or {}

    def read(self, amount=-1):
        return self.body.read(amount)

    def getcode(self):
        return self.status

    def close(self):
        self.body.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class ValidationTests(unittest.TestCase):
    def test_curie_validation(self):
        self.assertEqual(client.validate_curie("CHEBI:31690"), "CHEBI:31690")
        for invalid in ("CHEBI", "9CHEBI:1", "CHEBI:one two", "CHEBI:one\ntwo", "CHEBI:\x00one", "X:" + "a" * 201):
            with self.subTest(invalid=repr(invalid)), self.assertRaises(client.UsageError):
                client.validate_curie(invalid)

    def test_biolink_and_provider_validation(self):
        self.assertEqual(client.validate_biolink_term("biolink:Gene"), "biolink:Gene")
        self.assertEqual(client.validate_provider_id("infores:rtx-kg2"), "infores:rtx-kg2")
        for invalid in ("Gene", "biolink:", "biolink:Gene name"):
            with self.subTest(invalid=invalid), self.assertRaises(client.UsageError):
                client.validate_biolink_term(invalid)
        for invalid in ("rtx-kg2", "infores:all", "infores:a,b", "infores:a]", "infores:a=b"):
            with self.subTest(invalid=invalid), self.assertRaises(client.UsageError):
                client.validate_provider_id(invalid)

    def test_qualifier_limits_and_duplicate_types(self):
        parsed = client.parse_qualifiers(
            [
                "biolink:object_aspect_qualifier=activity_or_abundance",
                "biolink:object_direction_qualifier=decreased",
            ]
        )
        self.assertEqual(len(parsed), 2)
        with self.assertRaises(client.UsageError):
            client.parse_qualifiers(["missing-equals"])
        with self.assertRaises(client.UsageError):
            client.parse_qualifiers(
                [
                    "biolink:object_direction_qualifier=decreased",
                    "biolink:object_direction_qualifier=increased",
                ]
            )
        with self.assertRaises(client.UsageError):
            client.parse_qualifiers([f"biolink:q{i}=v" for i in range(7)])

    def test_mode_provider_and_result_caps(self):
        self.assertEqual(client.resolve_mode("lookup", [], None), (["infores:rtx-kg2"], 20))
        self.assertEqual(
            client.resolve_mode("federated", ["infores:rtx-kg2", "infores:molepro"], None),
            (["infores:rtx-kg2", "infores:molepro"], 50),
        )
        invalid = [
            ("lookup", ["infores:rtx-kg2"], None),
            ("federated", [], None),
            ("federated", ["infores:rtx-kg2"], None),
            ("federated", ["infores:a", "infores:a"], None),
            ("federated", [f"infores:k{i}" for i in range(6)], None),
            ("lookup", [], 51),
            ("lookup", [], 0),
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(client.UsageError):
                client.resolve_mode(*values)

    def test_one_hop_requires_a_pinned_endpoint(self):
        with self.assertRaises(client.UsageError):
            one_hop_body(subject_id=None, object_id=None)

    def test_base_url_policy(self):
        url, warnings = client.validate_base_url(client.PRODUCTION_BASE_URL, False)
        self.assertEqual(url, client.PRODUCTION_BASE_URL)
        self.assertEqual(warnings, [])
        with self.assertRaises(client.PreflightError):
            client.validate_base_url("https://arax.ncats.io/api/arax/v1.4", False)
        url, warnings = client.validate_base_url("https://arax.ncats.io/api/arax/v1.4/", True)
        self.assertEqual(url, "https://arax.ncats.io/api/arax/v1.4")
        self.assertEqual(warnings[0]["code"], "NONPRODUCTION_ENDPOINT")
        for invalid in (
            "http://arax.transltr.io/api/arax/v1.4",
            "https://user:pass@example.org/arax",
            "https://localhost/arax",
            "https://127.0.0.1/arax",
            "https://example.org:abc/arax",
            "https://example.org/arax?q=one",
            "https://example.org/arax#fragment",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(client.UsageError):
                client.validate_base_url(invalid, True)

    def test_repeated_endpoint_flag_is_rejected(self):
        parser = client.build_parser()
        with self.assertRaises(SystemExit) as raised, mock.patch("sys.stderr", new=io.StringIO()):
            parser.parse_args(
                [
                    "one-hop",
                    "--subject-id",
                    "CHEBI:1",
                    "--subject-id",
                    "CHEBI:2",
                    "--subject-category",
                    "biolink:SmallMolecule",
                    "--predicate",
                    "biolink:related_to",
                    "--object-category",
                    "biolink:Gene",
                    "--acknowledge-public-query",
                    "--output-dir",
                    "out",
                ]
            )
        self.assertEqual(raised.exception.code, 2)

    def test_parser_exposes_no_arbitrary_or_batch_query_surface(self):
        parser = client.build_parser()
        option_strings = {
            option
            for action in parser._actions
            for option in action.option_strings
        }
        subparsers = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        for subparser in subparsers.choices.values():
            option_strings.update(
                option for action in subparser._actions for option in action.option_strings
            )
        for excluded in (
            "--raw-query",
            "--query-file",
            "--workflow",
            "--action",
            "--overlay",
            "--rank",
            "--inference",
            "--ars",
            "--batch",
            "--all-kps",
        ):
            self.assertNotIn(excluded, option_strings)


class RequestBuilderTests(unittest.TestCase):
    def test_one_hop_exact_shape_and_and_qualifiers(self):
        body = one_hop_body(object_id=None)
        graph = body["message"]["query_graph"]
        self.assertEqual(set(graph["nodes"]), {"n0", "n1"})
        self.assertNotIn("ids", graph["nodes"]["n1"])
        self.assertEqual(graph["edges"]["e0"]["subject"], "n0")
        self.assertEqual(graph["edges"]["e0"]["object"], "n1")
        constraints = graph["edges"]["e0"]["qualifier_constraints"]
        self.assertEqual(len(constraints), 1)
        self.assertEqual(len(constraints[0]["qualifier_set"]), 2)
        self.assertEqual(body["submitter"], client.SUBMITTER)
        self.assertNotIn("workflow", body)

    def test_empty_qualifiers_are_omitted(self):
        edge = one_hop_body(qualifiers=[])["message"]["query_graph"]["edges"]["e0"]
        self.assertNotIn("qualifier_constraints", edge)

    def test_two_hop_right_and_left_first(self):
        right = two_hop_body()
        left = two_hop_body(expand_order="left-first")
        graph = right["message"]["query_graph"]
        self.assertEqual(set(graph["nodes"]), {"n0", "n1", "n2"})
        self.assertNotIn("ids", graph["nodes"]["n1"])
        fixed_tail = [
            "scoreless_resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results,max_results=20,prune_kg=true)",
            "return(response=true,store=false)",
        ]
        self.assertEqual(
            right["operations"]["actions"],
            [
                "expand(edge_key=e1,kp=infores:rtx-kg2,kp_timeout=30,return_minimal_metadata=false)",
                "expand(edge_key=e0,kp=infores:rtx-kg2,kp_timeout=30,return_minimal_metadata=false)",
                *fixed_tail,
            ],
        )
        self.assertEqual(
            left["operations"]["actions"],
            [
                "expand(edge_key=e0,kp=infores:rtx-kg2,kp_timeout=30,return_minimal_metadata=false)",
                "expand(edge_key=e1,kp=infores:rtx-kg2,kp_timeout=30,return_minimal_metadata=false)",
                *fixed_tail,
            ],
        )
        self.assertIs(right["stream_progress"], False)

    def test_federation_uses_one_list_valued_kp(self):
        body = two_hop_body(
            mode="federated",
            provider_ids=["infores:rtx-kg2", "infores:molepro"],
            result_limit=50,
        )
        for action in body["operations"]["actions"][:2]:
            self.assertIn("kp=[infores:rtx-kg2,infores:molepro]", action)
            self.assertEqual(action.count("kp="), 1)

    def test_fixed_actions_exclude_banned_workflows(self):
        serialized = client.serialize_request(two_hop_body()).decode("utf-8")
        self.assertIn("scoreless_resultify(ignore_edge_direction=true)", serialized)
        self.assertIn("return(response=true,store=false)", serialized)
        for banned in ("overlay", "rank_results", "infer", "pathfinder", "workflow"):
            self.assertNotIn(banned, serialized.lower())

    def test_deterministic_non_ascii_serialization(self):
        body = one_hop_body()
        body["message"]["note"] = "β"
        encoded = client.serialize_request(body)
        self.assertIn("β".encode("utf-8"), encoded)
        self.assertNotIn(b" ", encoded)
        self.assertEqual(encoded, client.serialize_request(body))

    def test_strict_json_rejects_nonfinite_numbers(self):
        with self.assertRaises(client.UsageError):
            client.serialize_request({"score": float("nan")})
        for constant in (b'{"score":NaN}', b'{"score":Infinity}', b'{"score":-Infinity}'):
            with self.subTest(constant=constant), self.assertRaises(client.ResponseError):
                client._decode_json(constant, "fixture")

    def test_saved_request_validator_rejects_escape_hatches(self):
        body = two_hop_body()
        contract = client.validate_saved_request_contract(body)
        self.assertEqual(contract.kind, "two-hop")
        self.assertEqual(contract.expand_order, "right-first")
        mutations = []
        workflow = copy.deepcopy(body)
        workflow["workflow"] = []
        mutations.append(workflow)
        overlay = copy.deepcopy(body)
        overlay["operations"]["actions"][0] = "overlay(action=compute_ngd)"
        mutations.append(overlay)
        ranked = copy.deepcopy(body)
        ranked["operations"]["actions"][-3] = "rank_results()"
        mutations.append(ranked)
        third_hop = copy.deepcopy(body)
        third_hop["message"]["query_graph"]["nodes"]["n3"] = {"categories": ["biolink:Gene"]}
        mutations.append(third_hop)
        all_kp = copy.deepcopy(body)
        all_kp["operations"]["actions"][0] = all_kp["operations"]["actions"][0].replace(
            "kp=infores:rtx-kg2", "kp=[]"
        )
        mutations.append(all_kp)
        extra_cases = [
            ("inferred", ("message", "query_graph", "edges", "e0"), "knowledge_type", "inferred"),
            ("creative", (), "workflow", [{"id": "lookup_and_score"}]),
            ("pathfinder", (), "pathfinder", True),
            ("batch_ids", ("message", "query_graph", "nodes", "n0"), "ids", ["CHEBI:1", "CHEBI:2"]),
            ("qnode_escape", ("message", "query_graph", "nodes", "n1"), "is_set", True),
            ("result_limit", (), None, None),
            ("streaming", (), "stream_progress", True),
            ("altered_return", (), None, None),
            ("duplicate_expand", (), None, None),
            ("missing_action", (), None, None),
            ("wildcard_provider", (), None, None),
            ("mixed_providers", (), None, None),
        ]
        for name, path, key, value in extra_cases:
            mutation = copy.deepcopy(body)
            target = mutation
            for item in path:
                target = target[item]
            if key is not None:
                target[key] = value
            elif name == "result_limit":
                mutation["operations"]["actions"][-2] = mutation["operations"]["actions"][-2].replace(
                    "max_results=20", "max_results=51"
                )
            elif name == "altered_return":
                mutation["operations"]["actions"][-1] = "return(response=true,store=true)"
            elif name == "duplicate_expand":
                mutation["operations"]["actions"][1] = mutation["operations"]["actions"][0]
            elif name == "missing_action":
                mutation["operations"]["actions"].pop()
            elif name == "wildcard_provider":
                mutation["operations"]["actions"][0] = mutation["operations"]["actions"][0].replace(
                    "kp=infores:rtx-kg2", "kp=*"
                )
            elif name == "mixed_providers":
                mutation["operations"]["actions"][1] = mutation["operations"]["actions"][1].replace(
                    "kp=infores:rtx-kg2", "kp=[infores:rtx-kg2,infores:molepro]"
                )
            mutations.append(mutation)
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(client.UsageError):
                client.validate_saved_request_contract(mutation)


class OpenApiAndTransportTests(unittest.TestCase):
    def test_minimal_openapi_parses(self):
        service = client.parse_openapi_service_info(
            fixture_json("openapi_1_5_minimal.json"),
            base_url=client.PRODUCTION_BASE_URL,
            openapi_url=client.PRODUCTION_BASE_URL + "/openapi.json",
            allow_untested_version=False,
        )
        self.assertEqual(service.arax_version, "1.5.4")
        self.assertEqual(service.trapi_version, "1.5.0")
        self.assertEqual(service.warnings, ())

    def test_openapi_title_path_and_version_failures(self):
        base = fixture_json("openapi_1_5_minimal.json")
        cases = []
        wrong_title = copy.deepcopy(base)
        wrong_title["info"]["title"] = "Other ARA - TRAPI 1.5.0"
        cases.append(wrong_title)
        no_query = copy.deepcopy(base)
        del no_query["paths"]["/query"]
        cases.append(no_query)
        unknown = copy.deepcopy(base)
        unknown["info"]["title"] = "ARAX Translator Reasoner - TRAPI 2.0.0"
        cases.append(unknown)
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(client.PreflightError):
                client.parse_openapi_service_info(
                    payload,
                    base_url=client.PRODUCTION_BASE_URL,
                    openapi_url=client.PRODUCTION_BASE_URL + "/openapi.json",
                    allow_untested_version=False,
                )

    def test_known_version_skew_warns_and_unknown_override_warns(self):
        payload = fixture_json("openapi_1_5_minimal.json")
        payload["info"]["title"] = "ARAX Translator Reasoner - TRAPI 1.6.0"
        payload["info"]["version"] = "1.6.2"
        service = client.parse_openapi_service_info(
            payload,
            base_url=client.PRODUCTION_BASE_URL,
            openapi_url=client.PRODUCTION_BASE_URL + "/openapi.json",
            allow_untested_version=False,
        )
        self.assertTrue(all(item["code"] == "UNTESTED_SERVICE_VERSION" for item in service.warnings))
        payload["info"]["title"] = "ARAX Translator Reasoner - TRAPI 2.0.0"
        service = client.parse_openapi_service_info(
            payload,
            base_url=client.PRODUCTION_BASE_URL,
            openapi_url=client.PRODUCTION_BASE_URL + "/openapi.json",
            allow_untested_version=True,
        )
        self.assertIn("UNTESTED_SERVICE_VERSION", {item["code"] for item in service.warnings})

    def test_get_retries_one_retryable_status(self):
        headers = Message()
        headers["Retry-After"] = "0"
        failure = urllib.error.HTTPError("https://example.org", 503, "busy", headers, io.BytesIO(b"busy"))
        sleeps = []
        with mock.patch.object(
            client,
            "_open_url",
            side_effect=[failure, FakeResponse(b"{}")],
        ) as opener:
            result = client.request_get_with_retry("https://example.org", sleep=sleeps.append)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(sleeps, [0.0])
        self.assertEqual(opener.call_count, 2)

    def test_get_headers_timeout_and_http_date_retry_after(self):
        captured = {}

        def opened(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(b"{}")

        with mock.patch.object(client, "_open_url", side_effect=opened):
            client.request_get_with_retry("https://example.org/data", timeout=17)
        headers = {key.lower(): value for key, value in captured["request"].header_items()}
        self.assertEqual(captured["request"].method, "GET")
        self.assertEqual(captured["timeout"], 17)
        self.assertEqual(headers["accept"], "application/json")
        self.assertEqual(headers["accept-encoding"], "identity")
        self.assertEqual(headers["user-agent"], client.USER_AGENT)

        now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
        retry_at = now + timedelta(seconds=7)
        self.assertEqual(
            client._retry_delay(
                {"Retry-After": retry_at.strftime("%a, %d %b %Y %H:%M:%S GMT")},
                now=lambda: now,
            ),
            7.0,
        )

    def test_redirects_are_https_and_same_origin_only(self):
        handler = client.SameOriginHttpsRedirectHandler()
        request = urllib.request.Request("https://example.org/start")
        headers = Message()
        redirected = handler.redirect_request(
            request,
            FakeResponse(b""),
            302,
            "found",
            headers,
            "https://example.org/next",
        )
        self.assertEqual(redirected.full_url, "https://example.org/next")
        for destination in (
            "https://other.example/next",
            "http://example.org/next",
            "https://example.org:abc/next",
        ):
            with self.subTest(destination=destination), self.assertRaises(urllib.error.HTTPError):
                handler.redirect_request(
                    request,
                    FakeResponse(b""),
                    302,
                    "found",
                    headers,
                    destination,
                )

    def test_get_retries_timeout_but_not_other_transport(self):
        with mock.patch.object(
            client,
            "_open_url",
            side_effect=[TimeoutError("slow"), FakeResponse(b"{}")],
        ) as opener:
            result = client.request_get_with_retry("https://example.org", sleep=lambda _: None)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(opener.call_count, 2)
        with mock.patch.object(
            client, "_open_url", side_effect=urllib.error.URLError("dns")
        ) as opener:
            with self.assertRaises(client.TransportError):
                client.request_get_with_retry("https://example.org", sleep=lambda _: None)
        self.assertEqual(opener.call_count, 1)

    def test_post_never_retries_and_uses_identity_encoding(self):
        captured = []

        def fail(request, timeout):
            captured.append((request, timeout))
            raise urllib.error.URLError("offline")

        with mock.patch.object(client, "_open_url", side_effect=fail):
            with self.assertRaises(client.TransportError):
                client.post_query("https://example.org/query", b"{}", timeout=120)
        self.assertEqual(len(captured), 1)
        headers = {key.lower(): value for key, value in captured[0][0].header_items()}
        self.assertEqual(headers["accept-encoding"], "identity")
        self.assertEqual(headers["user-agent"], client.USER_AGENT)

    def test_response_byte_limit(self):
        self.assertEqual(client.read_bounded_response(FakeResponse(b"12345"), 5), b"12345")
        with self.assertRaises(client.ResponseError):
            client.read_bounded_response(FakeResponse(b"123456"), 5)

    def test_oversized_success_and_http_error_preserve_exit_and_attempts(self):
        oversized = client.ResponseError("too large")
        with mock.patch.object(client, "_open_url", return_value=FakeResponse(b"{}")), mock.patch.object(
            client, "read_bounded_response", side_effect=oversized
        ):
            with self.assertRaises(client.ResponseError) as raised:
                client.request_get_with_retry("https://example.org")
        self.assertEqual(raised.exception.exit_code, 6)
        self.assertEqual(raised.exception.attempts, 1)
        self.assertEqual(raised.exception.http_status, 200)

        error = urllib.error.HTTPError(
            "https://example.org", 500, "failure", Message(), io.BytesIO(b"large")
        )
        with mock.patch.object(client, "_open_url", side_effect=error), mock.patch.object(
            client, "read_bounded_response", side_effect=client.ResponseError("too large")
        ):
            with self.assertRaises(client.ResponseError) as raised:
                client.post_query("https://example.org/query", b"{}", timeout=120)
        self.assertEqual(raised.exception.exit_code, 6)
        self.assertEqual(raised.exception.attempts, 1)
        self.assertEqual(raised.exception.http_status, 500)

    def test_retry_after_is_capped_and_invalid_defaults(self):
        self.assertEqual(client._retry_delay({"Retry-After": "99"}), 10.0)
        self.assertEqual(client._retry_delay({"Retry-After": "invalid"}), 1.0)

    def test_query_response_version_policy(self):
        for version, allowed, warning in (
            ("1.5.0", False, False),
            ("1.6.0", False, True),
            ("2.0.0", True, True),
        ):
            warnings = []
            client._validate_query_response_version(
                {"schema_version": version}, allowed, warnings
            )
            self.assertEqual(bool(warnings), warning)
        with self.assertRaises(client.PreflightError):
            client._validate_query_response_version(
                {"schema_version": "2.0.0"}, False, []
            )


class NormalizationTests(unittest.TestCase):
    def test_nested_normalization_match_and_mismatch(self):
        payload = fixture_json("normalization_response.json")
        summary, usable = client.parse_normalization_response(
            payload,
            term="ivacaftor",
            expected_category="biolink:SmallMolecule",
            max_synonyms=1,
            service=service_info(),
        )
        self.assertTrue(usable)
        self.assertEqual(
            summary["canonical"],
            {
                "identifier": "CHEBI:66901",
                "name": "ivacaftor",
                "category": "biolink:SmallMolecule",
            },
        )
        self.assertEqual(
            summary["category_counts"],
            {"biolink:Drug": 3, "biolink:SmallMolecule": 2},
        )
        self.assertEqual(summary["total_synonyms"], 2)
        self.assertEqual(len(summary["synonym_preview"]), 1)
        self.assertTrue(summary["query"]["requires_user_confirmation"])
        codes = {item["code"] for item in summary["warnings"]}
        self.assertTrue({"PUBLIC_QUERY", "NORMALIZATION_REQUIRES_CONFIRMATION"}.issubset(codes))
        summary, usable = client.parse_normalization_response(
            payload,
            term="ivacaftor",
            expected_category="biolink:Disease",
            max_synonyms=10,
            service=service_info(),
        )
        self.assertTrue(usable)
        self.assertIn("NORMALIZATION_CATEGORY_MISMATCH", {item["code"] for item in summary["warnings"]})

    def test_curie_input_does_not_require_normalization_confirmation(self):
        payload = {"CHEBI:66901": fixture_json("normalization_response.json")["ivacaftor"]}
        summary, usable = client.parse_normalization_response(
            payload,
            term="CHEBI:66901",
            expected_category=None,
            max_synonyms=0,
            service=service_info(),
        )
        self.assertTrue(usable)
        self.assertFalse(summary["query"]["requires_user_confirmation"])
        self.assertEqual(summary["synonym_preview"], [])

    def test_no_usable_normalization(self):
        summary, usable = client.parse_normalization_response(
            {"unknown": {}},
            term="unknown",
            expected_category=None,
            max_synonyms=10,
            service=service_info(),
        )
        self.assertFalse(usable)
        self.assertIsNone(summary["canonical"]["identifier"])
        self.assertIn("NO_RESULTS", {item["code"] for item in summary["warnings"]})


class ResponseParserTests(unittest.TestCase):
    def parse_fixture(self, name, *, contract=None):
        return client.parse_trapi_response(
            fixture_json(name),
            contract or client.validate_saved_request_contract(one_hop_body()),
            service=service_info(),
        )

    def test_one_hop_bindings_multiple_analyses_and_provenance(self):
        payload = fixture_json("one_hop_provenance.json")
        summary = client.parse_trapi_response(
            payload,
            client.validate_saved_request_contract(one_hop_body()),
            service=service_info(),
        )
        self.assertEqual(summary["counts"]["results_returned"], 1)
        self.assertEqual(summary["counts"]["analyses_summarized"], 2)
        self.assertEqual(summary["counts"]["bound_edges_summarized"], 3)
        analyses = summary["results"][0]["analyses"]
        edge_ids = [
            edge["edge_id"]
            for analysis in analyses
            for edge in analysis["edge_bindings"]["e0"]
        ]
        self.assertNotIn("kg-unbound", edge_ids)
        first = analyses[0]["edge_bindings"]["e0"][0]
        self.assertEqual(first["qualifiers"][0]["qualifier_value"], "activity")
        self.assertEqual(first["primary_knowledge_sources"], ["infores:drugbank"])
        self.assertEqual(first["aggregator_knowledge_sources"], ["infores:rtx-kg2", "infores:arax"])
        self.assertEqual(first["supporting_data_sources"], [])
        self.assertEqual(
            first["sources"],
            payload["message"]["knowledge_graph"]["edges"]["kg-e0-primary"]["sources"],
        )
        self.assertEqual(first["sources"][1]["upstream_resource_ids"], ["infores:drugbank"])
        self.assertEqual(first["sources"][0]["source_record_urls"], ["https://example.org/drugbank/one"])
        secondary = analyses[0]["edge_bindings"]["e0"][1]
        self.assertEqual(secondary["supporting_data_sources"], ["infores:ctd"])
        self.assertIsNone(analyses[0]["score"])
        self.assertEqual(analyses[0]["support_graphs"], ["sg-one"])
        self.assertEqual(first["support_graph_ids"], ["sg-one"])
        self.assertEqual(first["support_graph_status"], "available")
        self.assertEqual(
            analyses[1]["edge_bindings"]["e0"][0]["support_graph_status"],
            "not_returned",
        )
        self.assertEqual(
            summary["results"][0]["node_bindings"]["n0"][0],
            {"id": "CHEBI:31690", "query_id": "CHEBI:31690", "attributes": []},
        )
        publications = [
            publication
            for edge in analyses[0]["edge_bindings"]["e0"]
            for publication in edge["publication_ids"]
        ]
        self.assertEqual(publications, ["PMID:100", "PMID:101", "PMID:100"])
        self.assertIn("UNSCORED_RESPONSE_ORDER", {item["code"] for item in summary["warnings"]})

    def test_publications_are_deduplicated_within_each_edge(self):
        payload = fixture_json("one_hop_provenance.json")
        payload["message"]["knowledge_graph"]["edges"]["kg-e0-primary"]["attributes"][0][
            "value"
        ] = ["PMID:100", "PMID:100", "PMID:101"]
        summary = client.parse_trapi_response(
            payload,
            client.validate_saved_request_contract(one_hop_body()),
            service=service_info(),
        )
        publications = summary["results"][0]["analyses"][0]["edge_bindings"]["e0"][0][
            "publication_ids"
        ]
        self.assertEqual(publications, ["PMID:100", "PMID:101"])

    def test_two_hop_preserves_refined_predicate_and_support_graph(self):
        contract = client.validate_saved_request_contract(two_hop_body())
        summary = self.parse_fixture("two_hop_provenance.json", contract=contract)
        analysis = summary["results"][0]["analyses"][0]
        first = analysis["edge_bindings"]["e0"][0]
        second = analysis["edge_bindings"]["e1"][0]
        self.assertEqual(first["qualifiers"][0]["qualifier_value"], "activity")
        self.assertEqual(second["predicate"], "biolink:gene_associated_with_condition")
        self.assertEqual(first["support_graph_status"], "available")

    def test_reversed_edge_is_flagged_and_not_rewritten(self):
        summary = self.parse_fixture("reversed_edge.json")
        edge = summary["results"][0]["analyses"][0]["edge_bindings"]["e0"][0]
        self.assertFalse(edge["matches_query_direction"])
        self.assertEqual(edge["subject"], "NCBIGene:25")
        self.assertIn("REVERSED_EDGE_BINDING", {item["code"] for item in summary["warnings"]})

    def test_missing_publications_and_auxiliary_graph(self):
        publications = self.parse_fixture("missing_publications.json")
        edge = publications["results"][0]["analyses"][0]["edge_bindings"]["e0"][0]
        self.assertEqual(edge["publication_ids"], [])
        self.assertEqual(edge["publication_availability"], "not_returned")
        self.assertIn(
            "NO_PUBLICATIONS_RETURNED",
            {item["code"] for item in publications["warnings"]},
        )
        auxiliary = self.parse_fixture("missing_auxiliary_graph.json")
        edge = auxiliary["results"][0]["analyses"][0]["edge_bindings"]["e0"][0]
        self.assertEqual(edge["support_graph_status"], "missing")
        self.assertIn("MISSING_AUXILIARY_GRAPH", {item["code"] for item in auxiliary["warnings"]})

        no_primary = fixture_json("missing_publications.json")
        no_primary["message"]["knowledge_graph"]["edges"]["kg-no-pubs"]["sources"] = []
        summary = client.parse_trapi_response(
            no_primary,
            client.validate_saved_request_contract(one_hop_body()),
            service=service_info(),
        )
        codes = {item["code"] for item in summary["warnings"]}
        self.assertTrue({"NO_PRIMARY_SOURCE_RETURNED", "NO_PUBLICATIONS_RETURNED"}.issubset(codes))

    def test_zero_results_are_valid(self):
        summary = self.parse_fixture("no_results.json")
        self.assertEqual(summary["counts"]["results_returned"], 0)
        self.assertEqual(summary["results"], [])
        self.assertEqual(summary["truncation_status"], "no")
        self.assertIn("NO_RESULTS", {item["code"] for item in summary["warnings"]})

    def test_partial_federation_is_retained(self):
        body = one_hop_body(
            mode="federated",
            provider_ids=["infores:rtx-kg2", "infores:molepro"],
            result_limit=50,
        )
        summary = self.parse_fixture(
            "federated_partial_response.json",
            contract=client.validate_saved_request_contract(body),
        )
        self.assertEqual(summary["completeness"], "partial")
        codes = {item["code"] for item in summary["warnings"]}
        self.assertTrue({"KP_TIMEOUT", "KP_ERROR", "MALFORMED_KP_RESPONSE"}.issubset(codes))

    def test_truncation_states(self):
        payload = fixture_json("one_hop_provenance.json")
        contract = client.validate_saved_request_contract(one_hop_body(result_limit=1))
        summary = client.parse_trapi_response(payload, contract, service=service_info())
        self.assertEqual(summary["truncation_status"], "possible")
        payload["total_results_count"] = 2
        summary = client.parse_trapi_response(payload, contract, service=service_info())
        self.assertEqual(summary["truncation_status"], "confirmed")
        payload["total_results_count"] = 1
        payload["message"]["results"].append(copy.deepcopy(payload["message"]["results"][0]))
        summary = client.parse_trapi_response(payload, contract, service=service_info())
        self.assertEqual(summary["truncation_status"], "confirmed")
        self.assertEqual(len(summary["results"]), 1)

    def test_explicit_pruning_confirms_truncation(self):
        payload = fixture_json("one_hop_provenance.json")
        payload["logs"] = [{"level": "WARNING", "code": "PRUNED", "message": "Removed results during pruning"}]
        summary = client.parse_trapi_response(
            payload,
            client.validate_saved_request_contract(one_hop_body()),
            service=service_info(),
        )
        self.assertEqual(summary["truncation_status"], "confirmed")
        self.assertIn("INTERNAL_PRUNING_DETECTED", {item["code"] for item in summary["warnings"]})

    def test_informational_timeout_and_prune_configuration_do_not_mark_partial(self):
        payload = fixture_json("one_hop_provenance.json")
        payload["logs"] = [
            {"level": "INFO", "code": "CONFIG", "message": "kp_timeout=30"},
            {"level": "INFO", "code": "CONFIG", "message": "prune_kg=true"},
        ]
        contract = client.validate_saved_request_contract(
            one_hop_body(
                mode="federated",
                provider_ids=["infores:rtx-kg2", "infores:molepro"],
                result_limit=50,
            )
        )
        summary = client.parse_trapi_response(payload, contract, service=service_info())
        self.assertEqual(summary["completeness"], "complete")
        self.assertEqual(summary["truncation_status"], "no")
        codes = {item["code"] for item in summary["warnings"]}
        self.assertNotIn("KP_TIMEOUT", codes)
        self.assertNotIn("INTERNAL_PRUNING_DETECTED", codes)

    def test_malformed_message_graph_and_binding_fail(self):
        payload = fixture_json("one_hop_provenance.json")
        mutations = []
        no_message = copy.deepcopy(payload)
        del no_message["message"]
        mutations.append(no_message)
        no_graph = copy.deepcopy(payload)
        del no_graph["message"]["knowledge_graph"]
        mutations.append(no_graph)
        missing_edge = copy.deepcopy(payload)
        del missing_edge["message"]["knowledge_graph"]["edges"]["kg-e0-primary"]
        mutations.append(missing_edge)
        missing_qnode = copy.deepcopy(payload)
        del missing_qnode["message"]["results"][0]["node_bindings"]["n1"]
        mutations.append(missing_qnode)
        unrelated = copy.deepcopy(payload)
        unrelated["message"]["knowledge_graph"]["edges"]["kg-e0-primary"]["object"] = "NCBIGene:999"
        mutations.append(unrelated)
        extra_qedge = copy.deepcopy(payload)
        extra_qedge["message"]["results"][0]["analyses"][0]["edge_bindings"]["extra"] = []
        mutations.append(extra_qedge)
        contract = client.validate_saved_request_contract(one_hop_body())
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(client.ResponseError):
                client.parse_trapi_response(mutation, contract, service=service_info())


class RenderingTests(unittest.TestCase):
    def test_text_is_cautious_bounded_and_points_to_raw_artifacts(self):
        payload = fixture_json("one_hop_provenance.json")
        edge = payload["message"]["knowledge_graph"]["edges"]["kg-e0-primary"]
        edge["attributes"][0]["value"] = [f"PMID:{index}" for index in range(20)]
        summary = client.parse_trapi_response(
            payload,
            client.validate_saved_request_contract(one_hop_body()),
            service=service_info(),
        )
        rendered = client.render_text_summary(summary)
        self.assertIn("Unscored position 1", rendered)
        self.assertIn("Complete bounded publication and source lists: summary.json", rendered)
        self.assertIn("Exact TRAPI payload: response.json", rendered)
        self.assertIn("Candidate paths require subsequent scientific verification", rendered)
        self.assertIn("CHEBI:31690", rendered)
        self.assertIn("NCBIGene:25", rendered)
        self.assertIn("biolink:affects", rendered)
        self.assertIn("biolink:object_aspect_qualifier=activity", rendered)
        self.assertIn("infores:drugbank", rendered)
        self.assertIn("Publications: 20", rendered)
        self.assertNotIn("PMID:19", rendered)
        for prohibited in ("proved", "No relationship exists", "top-ranked"):
            self.assertNotIn(prohibited, rendered)

    def test_display_text_removes_controls_and_caps_length(self):
        value = client._sanitize_text("line\n" + "x" * 600)
        self.assertNotIn("\n", value)
        self.assertLessEqual(len(value), client.MAX_DISPLAY_TEXT)

    def test_all_remote_scalar_fields_are_terminal_safe(self):
        summary = client.parse_trapi_response(
            fixture_json("one_hop_provenance.json"),
            client.validate_saved_request_contract(one_hop_body()),
            service=service_info(),
        )
        result = summary["results"][0]
        result["node_bindings"]["n0\nINJECT"] = [{"id": "CURIE:1\nINJECT"}]
        analysis = result["analyses"][0]
        analysis["resource_id"] = "infores:arax\nINJECT"
        edge = analysis["edge_bindings"]["e0"][0]
        for field in ("edge_id", "subject", "subject_name", "predicate", "object", "object_name"):
            edge[field] = f"{field}\nINJECT"
        edge["qualifiers"] = [
            {"qualifier_type_id": "type\nINJECT", "qualifier_value": "value\nINJECT"}
        ]
        edge["primary_knowledge_sources"] = ["source\nINJECT"]
        edge["publication_ids"] = ["PMID:1\nINJECT"]
        rendered = client.render_text_summary(
            summary,
            summary_path="summary\nINJECT.json",
            response_path="response\nINJECT.json",
        )
        self.assertNotIn("\nINJECT", rendered)


class ArtifactAndCommandTests(unittest.TestCase):
    def test_output_directory_policy_and_atomic_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing_empty = root / "empty"
            existing_empty.mkdir()
            self.assertEqual(client.prepare_output_directory(existing_empty), existing_empty)
            new_dir = client.prepare_output_directory(root / "new")
            self.assertTrue(new_dir.is_dir())
            client.atomic_write_bytes(new_dir / "value.json", b"one")
            with self.assertRaises(client.ResponseError):
                client.atomic_write_bytes(new_dir / "value.json", b"two")
            with self.assertRaises(client.UsageError):
                client.prepare_output_directory(new_dir)
            self.assertEqual((new_dir / "value.json").read_bytes(), b"one")
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE((new_dir / "value.json").stat().st_mode), 0o600)

            failed_dir = root / "failed"
            failed_dir.mkdir()
            with mock.patch.object(client.os, "replace", side_effect=OSError("disk full")):
                with self.assertRaises(client.ResponseError):
                    client.atomic_write_bytes(failed_dir / "value.json", b"two")
            self.assertEqual(list(failed_dir.iterdir()), [])
            with mock.patch.object(client.tempfile, "mkstemp", side_effect=OSError("denied")):
                with self.assertRaises(client.ResponseError) as raised:
                    client.atomic_write_bytes(failed_dir / "other.json", b"three")
            self.assertEqual(raised.exception.exit_code, 6)
            with mock.patch.object(client.Path, "mkdir", side_effect=OSError("denied")):
                with self.assertRaises(client.ResponseError) as raised:
                    client.prepare_output_directory(root / "cannot-create")
            self.assertEqual(raised.exception.exit_code, 6)

    def test_failure_retention_is_best_effort_and_does_not_mask_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            manifest = client.new_manifest(
                "one-hop",
                base_url=client.PRODUCTION_BASE_URL,
                privacy_acknowledged=True,
                http_timeout=120,
                result_limit=20,
            )
            original = client.ResponseError("original artifact failure")
            with mock.patch.object(client, "_write_manifest", side_effect=OSError("disk full")), mock.patch(
                "sys.stderr", new=io.StringIO()
            ) as stderr:
                client._retain_failure(output, manifest, original, "query")
            self.assertIn("could not retain failure artifacts", stderr.getvalue())
            self.assertEqual(str(original), "original artifact failure")

    def test_graph_command_posts_saved_bytes_and_hashes_exact_response(self):
        captured = {}
        response_body = fixture_bytes("one_hop_provenance.json")
        preflight = client.HttpResult(200, fixture_bytes("openapi_1_5_minimal.json"), {}, 2, 1)

        def fake_post(url, request_bytes, *, timeout):
            captured["url"] = url
            captured["bytes"] = request_bytes
            captured["timeout"] = timeout
            return client.HttpResult(200, response_body, {}, 3, 1)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), preflight)
        ), mock.patch.object(client, "post_query", side_effect=fake_post):
            output = Path(temporary) / "run"
            args = argparse.Namespace(
                command="one-hop",
                subject_id="CHEBI:31690",
                subject_category="biolink:SmallMolecule",
                predicate=["biolink:affects"],
                object_id="NCBIGene:25",
                object_category="biolink:Gene",
                qualifier=[],
                mode="lookup",
                kp=[],
                result_limit=20,
                acknowledge_public_query=True,
                output_dir=str(output),
                base_url=client.PRODUCTION_BASE_URL,
                allow_nonproduction_endpoint=False,
                allow_untested_version=False,
            )
            with mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(client.handle_graph_query(args), 0)
            self.assertEqual((output / "request.json").read_bytes(), captured["bytes"])
            self.assertEqual((output / "response.json").read_bytes(), response_body)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["manifest_version"], "1.0")
            self.assertEqual(manifest["execution_status"], "success")
            self.assertEqual(manifest["result_status"], "results")
            self.assertTrue(manifest["privacy_acknowledged"])
            self.assertEqual(manifest["request"]["method"], "POST")
            self.assertEqual(manifest["request"]["url"], client.PRODUCTION_BASE_URL + "/query")
            self.assertEqual(manifest["request"]["file"], "request.json")
            self.assertEqual(manifest["request"]["bytes"], len(captured["bytes"]))
            self.assertEqual(manifest["request"]["sha256"], client.sha256_bytes(captured["bytes"]))
            self.assertEqual(manifest["response"]["http_status"], 200)
            self.assertEqual(manifest["response"]["file"], "response.json")
            self.assertEqual(manifest["response"]["bytes"], len(response_body))
            self.assertEqual(manifest["response"]["elapsed_ms"], 3)
            self.assertEqual(manifest["response"]["sha256"], client.sha256_bytes(response_body))
            self.assertEqual(
                manifest["limits"],
                {
                    "http_timeout_seconds": 120,
                    "kp_timeout_seconds": 30,
                    "response_byte_limit": 25 * 1024 * 1024,
                    "result_limit": 20,
                },
            )
            self.assertEqual(
                manifest["attempts"],
                {"openapi_get": 1, "entity_get": 0, "query_post": 1},
            )
            self.assertEqual(
                manifest["artifacts"],
                {"request": "request.json", "response": "response.json", "summary": "summary.json"},
            )
            self.assertIn("PUBLIC_QUERY", {item["code"] for item in manifest["warnings"]})
            self.assertRegex(manifest["run_id"], r"^[0-9a-f-]{36}$")
            self.assertTrue(manifest["started_at"].endswith("Z"))
            self.assertTrue(manifest["finished_at"].endswith("Z"))
            self.assertNotIn("CHEBI:31690", client.USER_AGENT)
            self.assertNotIn("CHEBI:31690", client.SUBMITTER)

    def test_preflight_with_output_has_get_manifest_and_no_request_artifact(self):
        response_body = fixture_bytes("openapi_1_5_minimal.json")
        result = client.HttpResult(200, response_body, {}, 4, 1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), result)
        ):
            output = Path(temporary) / "preflight"
            args = argparse.Namespace(
                output_dir=str(output),
                base_url=client.PRODUCTION_BASE_URL,
                allow_nonproduction_endpoint=False,
                allow_untested_version=False,
            )
            with mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(client.handle_preflight(args), 0)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"response.json", "summary.json", "manifest.json"},
            )
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["privacy_acknowledged"])
            self.assertEqual(
                manifest["request"],
                {
                    "method": "GET",
                    "url": client.PRODUCTION_BASE_URL + "/openapi.json",
                    "file": None,
                    "bytes": None,
                    "sha256": None,
                },
            )
            self.assertEqual(manifest["artifacts"]["request"], None)
            self.assertEqual(manifest["attempts"]["openapi_get"], 1)

    def test_failure_manifests_record_the_actual_network_stage(self):
        preflight = client.HttpResult(200, fixture_bytes("openapi_1_5_minimal.json"), {}, 2, 1)
        cases = [
            (
                "openapi",
                client.PreflightError(
                    "preflight failed", http_status=503, response_body=b"openapi-error", attempts=2
                ),
            ),
            (
                "entity",
                client.TransportError(
                    "entity failed", http_status=502, response_body=b"entity-error", attempts=1
                ),
            ),
            (
                "query",
                client.TransportError(
                    "query failed", http_status=500, response_body=b"query-error", attempts=1
                ),
            ),
        ]
        for stage, failure in cases:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / stage
                if stage == "openapi":
                    with mock.patch.object(client, "fetch_openapi", side_effect=failure):
                        with self.assertRaises(client.PreflightError):
                            client.handle_graph_query(one_hop_args(output))
                    expected_url = client.PRODUCTION_BASE_URL + "/openapi.json"
                    expected_method = "GET"
                    expected_attempts = {"openapi_get": 2, "entity_get": 0, "query_post": 0}
                    self.assertFalse((output / "request.json").exists())
                elif stage == "entity":
                    with mock.patch.object(
                        client, "fetch_openapi", return_value=(service_info(), preflight)
                    ), mock.patch.object(client, "normalize_entity_request", side_effect=failure):
                        with self.assertRaises(client.TransportError):
                            client.handle_normalize(normalize_args(output))
                    expected_url = client.PRODUCTION_BASE_URL + "/entity?q=ivacaftor"
                    expected_method = "GET"
                    expected_attempts = {"openapi_get": 1, "entity_get": 1, "query_post": 0}
                else:
                    with mock.patch.object(
                        client, "fetch_openapi", return_value=(service_info(), preflight)
                    ), mock.patch.object(client, "post_query", side_effect=failure):
                        with self.assertRaises(client.TransportError):
                            client.handle_graph_query(one_hop_args(output))
                    expected_url = client.PRODUCTION_BASE_URL + "/query"
                    expected_method = "POST"
                    expected_attempts = {"openapi_get": 1, "entity_get": 0, "query_post": 1}
                    self.assertTrue((output / "request.json").exists())
                self.assertEqual((output / "response.json").read_bytes(), failure.response_body)
                manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["request"]["method"], expected_method)
                self.assertEqual(manifest["request"]["url"], expected_url)
                self.assertEqual(manifest["attempts"], expected_attempts)
                self.assertEqual(manifest["response"]["http_status"], failure.http_status)
                self.assertEqual(manifest["execution_status"], "http_error" if failure.exit_code == 5 else "client_error")

    def test_oversized_query_retains_request_and_manifest_but_no_partial_response(self):
        preflight = client.HttpResult(200, fixture_bytes("openapi_1_5_minimal.json"), {}, 2, 1)
        failure = client.ResponseError("response exceeded limit", http_status=200, attempts=1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), preflight)
        ), mock.patch.object(client, "post_query", side_effect=failure):
            output = Path(temporary) / "oversized"
            with self.assertRaises(client.ResponseError):
                client.handle_graph_query(one_hop_args(output))
            self.assertTrue((output / "request.json").exists())
            self.assertFalse((output / "response.json").exists())
            self.assertFalse((output / "summary.json").exists())
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["attempts"]["query_post"], 1)
            self.assertEqual(manifest["response"]["http_status"], 200)
            self.assertIsNone(manifest["response"]["file"])
            self.assertEqual(manifest["error"]["kind"], "invalid_response")

    def test_zero_result_and_normalization_no_result_statuses(self):
        preflight = client.HttpResult(200, fixture_bytes("openapi_1_5_minimal.json"), {}, 2, 1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), preflight)
        ), mock.patch.object(
            client,
            "post_query",
            return_value=client.HttpResult(200, fixture_bytes("no_results.json"), {}, 3, 1),
        ):
            output = Path(temporary) / "zero"
            with mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(client.handle_graph_query(one_hop_args(output)), 0)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["execution_status"], "success")
            self.assertEqual(manifest["result_status"], "no_results")

        entity = client.HttpResult(200, b'{"ivacaftor":{}}', {}, 3, 1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), preflight)
        ), mock.patch.object(client, "normalize_entity_request", return_value=entity):
            output = Path(temporary) / "normalize-none"
            with self.assertRaises(client.NormalizationError) as raised:
                client.handle_normalize(normalize_args(output))
            self.assertEqual(raised.exception.exit_code, 4)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["execution_status"], "success")
            self.assertEqual(manifest["result_status"], "no_results")

    def test_partial_graph_command_retains_all_artifacts_and_exits_seven(self):
        response_body = fixture_bytes("federated_partial_response.json")
        preflight = client.HttpResult(200, fixture_bytes("openapi_1_5_minimal.json"), {}, 2, 1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), preflight)
        ), mock.patch.object(
            client,
            "post_query",
            return_value=client.HttpResult(200, response_body, {}, 3, 1),
        ):
            output = Path(temporary) / "run"
            args = argparse.Namespace(
                command="one-hop",
                subject_id="CHEBI:31690",
                subject_category="biolink:SmallMolecule",
                predicate=["biolink:affects"],
                object_id="NCBIGene:25",
                object_category="biolink:Gene",
                qualifier=[],
                mode="federated",
                kp=["infores:rtx-kg2", "infores:molepro"],
                result_limit=50,
                acknowledge_public_query=True,
                output_dir=str(output),
                base_url=client.PRODUCTION_BASE_URL,
                allow_nonproduction_endpoint=False,
                allow_untested_version=False,
            )
            with mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(client.handle_graph_query(args), 7)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"request.json", "response.json", "summary.json", "manifest.json"},
            )
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["result_status"], "partial")

    def test_malformed_response_is_retained_without_summary(self):
        preflight = client.HttpResult(200, fixture_bytes("openapi_1_5_minimal.json"), {}, 2, 1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), preflight)
        ), mock.patch.object(
            client,
            "post_query",
            return_value=client.HttpResult(200, b"{not-json", {}, 3, 1),
        ):
            output = Path(temporary) / "run"
            args = argparse.Namespace(
                command="one-hop",
                subject_id="CHEBI:31690",
                subject_category="biolink:SmallMolecule",
                predicate=["biolink:affects"],
                object_id="NCBIGene:25",
                object_category="biolink:Gene",
                qualifier=[],
                mode="lookup",
                kp=[],
                result_limit=20,
                acknowledge_public_query=True,
                output_dir=str(output),
                base_url=client.PRODUCTION_BASE_URL,
                allow_nonproduction_endpoint=False,
                allow_untested_version=False,
            )
            with self.assertRaises(client.ResponseError):
                client.handle_graph_query(args)
            self.assertTrue((output / "request.json").exists())
            self.assertEqual((output / "response.json").read_bytes(), b"{not-json")
            self.assertFalse((output / "summary.json").exists())
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["execution_status"], "client_error")

    def test_normalize_command_never_posts(self):
        preflight = client.HttpResult(200, fixture_bytes("openapi_1_5_minimal.json"), {}, 2, 1)
        entity = client.HttpResult(200, fixture_bytes("normalization_response.json"), {}, 3, 1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            client, "fetch_openapi", return_value=(service_info(), preflight)
        ), mock.patch.object(client, "normalize_entity_request", return_value=entity), mock.patch.object(
            client, "post_query", side_effect=AssertionError("normalization must not POST")
        ):
            output = Path(temporary) / "normalize"
            args = argparse.Namespace(
                term="ivacaftor",
                expected_category="biolink:SmallMolecule",
                max_synonyms=10,
                acknowledge_public_query=True,
                output_dir=str(output),
                base_url=client.PRODUCTION_BASE_URL,
                allow_nonproduction_endpoint=False,
                allow_untested_version=False,
            )
            with mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(client.handle_normalize(args), 0)
            self.assertFalse((output / "request.json").exists())
            self.assertTrue((output / "response.json").exists())
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["request"],
                {
                    "method": "GET",
                    "url": client.PRODUCTION_BASE_URL + "/entity?q=ivacaftor",
                    "file": None,
                    "bytes": None,
                    "sha256": None,
                },
            )
            self.assertEqual(
                manifest["attempts"],
                {"openapi_get": 1, "entity_get": 1, "query_post": 0},
            )
            self.assertEqual(manifest["artifacts"]["request"], None)

    def test_summarize_is_offline_and_preserves_inputs(self):
        request_bytes = client.serialize_request(one_hop_body())
        response_bytes = fixture_bytes("one_hop_provenance.json")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = root / "request.json"
            response_path = root / "response.json"
            request_path.write_bytes(request_bytes)
            response_path.write_bytes(response_bytes)
            args = argparse.Namespace(
                request=str(request_path), response=str(response_path), format="json"
            )
            with mock.patch.object(
                client, "_open_url", side_effect=AssertionError("offline summarize used network")
            ), mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                self.assertEqual(client.handle_summarize(args), 0)
            parsed = json.loads(stdout.getvalue())
            self.assertEqual(parsed["results"][0]["position"], 1)
            self.assertEqual(request_path.read_bytes(), request_bytes)
            self.assertEqual(response_path.read_bytes(), response_bytes)

    def test_main_exit_code_mapping_for_local_and_response_errors(self):
        normalize_cli = [
            "normalize",
            "term",
            "--acknowledge-public-query",
            "--output-dir",
            "unused",
        ]
        graph_cli = [
            "one-hop",
            "--subject-id",
            "CHEBI:1",
            "--subject-category",
            "biolink:SmallMolecule",
            "--predicate",
            "biolink:related_to",
            "--object-category",
            "biolink:Gene",
            "--acknowledge-public-query",
            "--output-dir",
            "unused",
        ]
        cases = [
            ("handle_preflight", ["preflight"], client.PreflightError("bad service"), 3),
            ("handle_normalize", normalize_cli, client.NormalizationError("not found"), 4),
            ("handle_graph_query", graph_cli, client.TransportError("offline"), 5),
            ("handle_graph_query", graph_cli, client.ResponseError("bad response"), 6),
        ]
        for handler, argv, failure, expected in cases:
            with self.subTest(expected=expected), mock.patch.object(
                client, handler, side_effect=failure
            ), mock.patch("sys.stderr", new=io.StringIO()):
                self.assertEqual(client.main(argv), expected)
        with mock.patch.object(client, "handle_graph_query", return_value=0):
            self.assertEqual(client.main(graph_cli), 0)
        with mock.patch.object(client, "handle_graph_query", return_value=7):
            self.assertEqual(client.main(graph_cli), 7)

        with tempfile.TemporaryDirectory() as temporary:
            request = Path(temporary) / "request.json"
            response = Path(temporary) / "response.json"
            request.write_text("{}", encoding="utf-8")
            response.write_text("{}", encoding="utf-8")
            with mock.patch("sys.stderr", new=io.StringIO()):
                code = client.main(
                    ["summarize", "--request", str(request), "--response", str(response)]
                )
            self.assertEqual(code, 2)
            request.write_bytes(client.serialize_request(one_hop_body()))
            response.write_bytes(b"not-json")
            with mock.patch("sys.stderr", new=io.StringIO()):
                code = client.main(
                    ["summarize", "--request", str(request), "--response", str(response)]
                )
            self.assertEqual(code, 6)


@unittest.skipUnless(os.environ.get("ARAX_LIVE_TESTS") == "1", "set ARAX_LIVE_TESTS=1")
class LiveSmokeTests(unittest.TestCase):
    def live_service(self):
        service, _ = client.fetch_openapi(
            client.PRODUCTION_BASE_URL,
            allow_untested_version=False,
        )
        return service

    def live_query(self, body):
        service = self.live_service()
        contract = client.validate_saved_request_contract(body)
        timeout = (
            client.FEDERATED_TIMEOUT_SECONDS
            if contract.mode == "federated"
            else client.LOOKUP_TIMEOUT_SECONDS
        )
        result = client.post_query(
            client.PRODUCTION_BASE_URL + "/query",
            client.serialize_request(body),
            timeout=timeout,
        )
        payload = client._decode_json(result.body, "live TRAPI response")
        return client.parse_trapi_response(payload, contract, service=service)

    def bound_node_ids(self, summary):
        return {
            binding["id"]
            for result in summary["results"]
            for bindings in result["node_bindings"].values()
            for binding in bindings
        }

    def test_01_production_openapi(self):
        service = self.live_service()
        self.assertIn(service.trapi_version.split(".")[0:2], (["1", "5"], ["1", "6"]))

    def test_02_production_accepts_rtx_kg2_lookup(self):
        summary = self.live_query(one_hop_body(qualifiers=[], result_limit=5))
        self.assertLessEqual(summary["counts"]["results_summarized"], 5)

    def test_03_normalize_ivacaftor(self):
        service = self.live_service()
        result = client.normalize_entity_request(client.PRODUCTION_BASE_URL, "ivacaftor")
        summary, usable = client.parse_normalization_response(
            client._decode_json(result.body, "live entity response"),
            term="ivacaftor",
            expected_category="biolink:SmallMolecule",
            max_synonyms=10,
            service=service,
        )
        self.assertTrue(usable)
        self.assertRegex(summary["canonical"]["identifier"], r"^[^:]+:.+$")
        self.assertTrue(summary["canonical"]["category"])

    def test_04_pinned_imatinib_abl1_one_hop(self):
        summary = self.live_query(one_hop_body(result_limit=20))
        self.assertGreater(summary["counts"]["bound_edges_summarized"], 0)

    def test_05_ivacaftor_gene_cystic_fibrosis_contains_cftr(self):
        summary = self.live_query(two_hop_body(result_limit=20))
        self.assertIn("NCBIGene:1080", self.bound_node_ids(summary))

    def test_06_imatinib_gene_cml_contains_abl1(self):
        body = two_hop_body(
            subject_id="CHEBI:31690",
            object_id="MONDO:0011996",
            qualifiers_1=[
                ("biolink:object_aspect_qualifier", "activity_or_abundance"),
                ("biolink:object_direction_qualifier", "decreased"),
            ],
            result_limit=20,
        )
        summary = self.live_query(body)
        self.assertIn("NCBIGene:25", self.bound_node_ids(summary))

    def test_07_wrong_direction_does_not_return_abl1_path(self):
        body = one_hop_body(
            qualifiers=[
                ("biolink:object_aspect_qualifier", "activity_or_abundance"),
                ("biolink:object_direction_qualifier", "increased"),
            ],
            result_limit=20,
        )
        summary = self.live_query(body)
        self.assertEqual(summary["counts"]["results_returned"], 0)

    def test_08_selected_provider_federation_is_bounded_and_provenanced(self):
        body = one_hop_body(
            qualifiers=[],
            mode="federated",
            provider_ids=["infores:rtx-kg2", "infores:molepro"],
            result_limit=50,
        )
        summary = self.live_query(body)
        self.assertLessEqual(summary["counts"]["results_summarized"], 50)
        for result in summary["results"]:
            for analysis in result["analyses"]:
                for edges in analysis["edge_bindings"].values():
                    for edge in edges:
                        self.assertTrue(edge["sources"])


if __name__ == "__main__":
    unittest.main()
