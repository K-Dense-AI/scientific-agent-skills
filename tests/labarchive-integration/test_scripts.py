"""Tests for the LabArchives integration helpers.

Three security boundaries live in these scripts, and all three are testable
without touching LabArchives:

* the HMAC-SHA-512 request signature, which the vendor documents with a public
  test vector -- so the suite is a known-answer test, not a self-consistency
  check;
* the path validators in front of that signature, which refuse anything that
  would sign a different route than the one actually requested;
* the LA container inspector, which inspects untrusted ZIP archives without extraction;
  they must reject traversal, absolute paths, and symlink members.

Nothing here uses a real credential; key material consists of dummy strings and the vendor's
published test vector.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import stat
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "labarchive-integration"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import entry_operations  # noqa: E402
import notebook_operations  # noqa: E402
import setup_config  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class SignatureTests(unittest.TestCase):
    def test_the_official_vendor_vector_reproduces_exactly(self) -> None:
        vector = entry_operations._OFFICIAL_VECTOR
        signature = entry_operations.create_signature(
            vector["access_key_id"],
            vector["api_method_input"],
            int(vector["expires_ms"]),
            vector["access_password"],
        )
        self.assertEqual(signature, vector["signature"])

    def test_the_signature_is_base64_hmac_sha512_over_the_concatenation(self) -> None:
        # Recomputed independently: any change to the message layout shows up
        # here rather than as a 401 from the API.
        expected = base64.b64encode(
            hmac.new(
                b"secret", b"keyidmethod12345", hashlib.sha512
            ).digest()
        ).decode("ascii")
        self.assertEqual(
            entry_operations.create_signature("keyid", "method", 12345, "secret"),
            expected,
        )

    def test_every_input_changes_the_signature(self) -> None:
        base = entry_operations.create_signature("k", "m", 1, "s")
        variants = {
            "key": entry_operations.create_signature("K", "m", 1, "s"),
            "method": entry_operations.create_signature("k", "M", 1, "s"),
            "expires": entry_operations.create_signature("k", "m", 2, "s"),
            "secret": entry_operations.create_signature("k", "m", 1, "S"),
        }
        for name, signature in variants.items():
            with self.subTest(changed=name):
                self.assertNotEqual(signature, base)

    def test_empty_inputs_are_refused_before_signing(self) -> None:
        cases = [
            (("", "m", 1, "s"), "Access Key ID"),
            (("k", "", 1, "s"), "API method input"),
            (("k", "m", 1, ""), "Access Password"),
        ]
        for arguments, label in cases:
            with self.subTest(label=label):
                with self.assertRaises(setup_config.ConfigError) as raised:
                    entry_operations.create_signature(*arguments)
                self.assertIn(label, str(raised.exception))

    def test_a_negative_expiry_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            entry_operations.create_signature("k", "m", -1, "s")

    def test_the_signature_is_uri_encoded_for_a_query_parameter(self) -> None:
        # Base64 contains '+' and '/', which are meaningful in a query string.
        encoded = entry_operations.encode_eln_signature("a+b/c==")
        self.assertEqual(encoded, "a%2Bb%2Fc%3D%3D")

    def test_the_self_test_command_reports_a_pass_without_a_network_call(self) -> None:
        class Args:
            compact = True

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = entry_operations.command_self_test(Args())

        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["passed"])
        self.assertFalse(payload["remote_request_performed"])
        # The signature itself must never be printed, only a fingerprint.
        self.assertNotIn(
            entry_operations._OFFICIAL_VECTOR["signature"], buffer.getvalue()
        )


class AuthParameterTests(unittest.TestCase):
    def test_eln_parameters_carry_the_key_expiry_and_signature(self) -> None:
        params = entry_operations.build_eln_auth_params(
            "keyid", "secret", "entry_attachment", expires_ms=1000
        )
        self.assertEqual(set(params), {"akid", "expires", "sig"})
        self.assertEqual(params["akid"], "keyid")
        self.assertEqual(params["expires"], "1000")
        self.assertEqual(
            params["sig"],
            entry_operations.create_signature("keyid", "entry_attachment", 1000, "secret"),
        )

    def test_the_password_never_appears_in_the_parameters(self) -> None:
        params = entry_operations.build_eln_auth_params(
            "keyid", "hunter2", "entry_attachment", expires_ms=1000
        )
        self.assertNotIn("hunter2", json.dumps(params))

    def test_inventory_headers_sign_the_resolved_path(self) -> None:
        headers = entry_operations.build_inventory_headers(
            "keyid", "secret", "user", "lab", "/public/v1/inventory/42", expires_ms=1000
        )
        self.assertEqual(
            headers["X-LabArchives-Signature"],
            entry_operations.create_signature(
                "keyid", "/public/v1/inventory/42", 1000, "secret"
            ),
        )
        self.assertEqual(headers["X-LabArchives-UId"], "user")
        self.assertEqual(headers["X-LabArchives-LabId"], "lab")

    def test_inventory_bootstrap_omits_lab_header_when_not_known(self) -> None:
        for lab_id in (None, "", "  "):
            with self.subTest(lab_id=lab_id):
                headers = entry_operations.build_inventory_headers(
                    "keyid", "secret", "user", lab_id, "/public/v1/users/me", expires_ms=1000
                )
                self.assertNotIn("X-LabArchives-LabId", headers)
                self.assertEqual(len(headers), 4)
                self.assertEqual(
                    headers["X-LabArchives-Signature"],
                    entry_operations.create_signature("keyid", "/public/v1/users/me", 1000, "secret"),
                )

    def test_inventory_lab_scoped_calls_still_require_lab_header(self) -> None:
        for path in ("/public/v1/inventory", "/public/v1/inventory/ITEM-42", "/public/v1/users/me/"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(setup_config.ConfigError, "Inventory Lab ID"):
                    entry_operations.build_inventory_headers("k", "s", "u", None, path)

    def test_inventory_bootstrap_plan_works_before_lab_selection(self) -> None:
        args = entry_operations.build_parser().parse_args([
            "inventory-plan", "--path", "/public/v1/users/me", "--expires-ms", "1000"
        ])
        env = {
            setup_config.ENV_ACCESS_KEY_ID: "fake-key",
            setup_config.ENV_ACCESS_PASSWORD: "fake-secret",
            setup_config.ENV_USER_ID: "fake-user",
        }
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(entry_operations.command_inventory_plan(args, env), 0)
        payload = json.loads(buffer.getvalue())
        self.assertNotIn("X-LabArchives-LabId", payload["authentication_header_names"])
        self.assertFalse(payload["remote_request_performed"])
        for value in env.values():
            self.assertNotIn(value, buffer.getvalue())

    def test_an_omitted_expiry_defaults_to_now(self) -> None:
        params = entry_operations.build_eln_auth_params("k", "s", "entry_attachment")
        self.assertTrue(params["expires"].isdigit())
        self.assertGreater(int(params["expires"]), 1_700_000_000_000)


class ComponentValidationTests(unittest.TestCase):
    def test_valid_method_names_are_accepted(self) -> None:
        for value in ("entry_attachment", "users", "tree_tools", "a1_b2"):
            with self.subTest(value=value):
                self.assertEqual(
                    entry_operations.validate_eln_component(value, "method"), value
                )

    def test_anything_outside_the_documented_shape_is_refused(self) -> None:
        for value in ("Entry", "1entry", "entry-attachment", "entry attachment", "", "entry/x"):
            with self.subTest(value=value):
                with self.assertRaises(setup_config.ConfigError):
                    entry_operations.validate_eln_component(value, "method")


class InventoryPathTests(unittest.TestCase):
    def test_a_resolved_route_is_accepted(self) -> None:
        for path in ("/public/v1/inventory", "/public/v1/inventory/42", "/public/v1/a.b~c"):
            with self.subTest(path=path):
                self.assertEqual(entry_operations.validate_inventory_path(path), path)

    def test_a_query_or_fragment_is_refused(self) -> None:
        # The signature excludes the query; callers pass query parameters separately.
        for path in ("/public/v1/inventory?page=2", "/public/v1/inventory#top"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "query strings and fragments"):
                    entry_operations.validate_inventory_path(path)

    def test_a_percent_encoded_path_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "unencoded relative route"):
            entry_operations.validate_inventory_path("/public/v1/it%20ems")

    def test_unresolved_placeholders_are_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "resolve all Inventory route placeholders"):
            entry_operations.validate_inventory_path("/public/v1/inventory/{id}")

    def test_a_path_outside_the_public_v1_prefix_is_refused(self) -> None:
        for path in ("/private/v1/items", "public/v1/items", "/public/v2/items"):
            with self.subTest(path=path):
                with self.assertRaises(setup_config.ConfigError):
                    entry_operations.validate_inventory_path(path)

    def test_traversal_and_ambiguous_segments_are_refused(self) -> None:
        for path in ("/public/v1/../secret", "/public/v1/./items", "/public/v1//items"):
            with self.subTest(path=path):
                with self.assertRaises(setup_config.ConfigError):
                    entry_operations.validate_inventory_path(path)

    def test_whitespace_and_backslashes_are_refused(self) -> None:
        for path in ("/public/v1/it ems", "/public/v1/it\tems", "/public/v1\\items"):
            with self.subTest(path=repr(path)):
                with self.assertRaises(setup_config.ConfigError):
                    entry_operations.validate_inventory_path(path)


class ApiUrlTests(unittest.TestCase):
    def test_every_documented_region_url_normalises_to_itself(self) -> None:
        self.assertTrue(setup_config.REGIONS)
        for region, values in setup_config.REGIONS.items():
            with self.subTest(region=region):
                url = values["eln_api_url"]
                self.assertEqual(setup_config.normalize_eln_api_url(url), url)

    def test_a_trailing_slash_and_mixed_case_host_are_normalised(self) -> None:
        url = next(iter(setup_config.REGIONS.values()))["eln_api_url"]
        host = url.removeprefix("https://").removesuffix("/api")
        self.assertEqual(
            setup_config.normalize_eln_api_url(f"https://{host.upper()}/api/"), url
        )

    def test_plain_http_is_refused(self) -> None:
        url = next(iter(setup_config.REGIONS.values()))["eln_api_url"]
        with self.assertRaisesRegex(ValueError, "must use https"):
            setup_config.normalize_eln_api_url(url.replace("https://", "http://"))

    def test_embedded_credentials_are_refused(self) -> None:
        url = next(iter(setup_config.REGIONS.values()))["eln_api_url"]
        host = url.removeprefix("https://").removesuffix("/api")
        with self.assertRaisesRegex(ValueError, "credentials must not be embedded"):
            setup_config.normalize_eln_api_url(f"https://user:pass@{host}/api")

    def test_a_custom_port_query_or_fragment_is_refused(self) -> None:
        url = next(iter(setup_config.REGIONS.values()))["eln_api_url"]
        host = url.removeprefix("https://").removesuffix("/api")
        cases = {
            f"https://{host}:8443/api": "custom port",
            f"https://{host}/api?x=1": "query or fragment",
            f"https://{host}/api#y": "query or fragment",
        }
        for candidate, expected in cases.items():
            with self.subTest(url=candidate):
                with self.assertRaisesRegex(ValueError, expected):
                    setup_config.normalize_eln_api_url(candidate)

    def test_a_non_allowlisted_host_is_refused_and_lists_the_alternatives(self) -> None:
        with self.assertRaises(setup_config.ConfigError) as raised:
            setup_config.normalize_eln_api_url("https://evil.example.invalid/api")
        self.assertIn("not allowlisted", str(raised.exception))

    def test_the_path_must_be_exactly_api(self) -> None:
        url = next(iter(setup_config.REGIONS.values()))["eln_api_url"]
        host = url.removeprefix("https://").removesuffix("/api")
        with self.assertRaisesRegex(ValueError, "path must be exactly /api"):
            setup_config.normalize_eln_api_url(f"https://{host}/api/v2")

    def test_an_empty_url_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "is empty"):
            setup_config.normalize_eln_api_url("   ")


class ContainerMemberTests(unittest.TestCase):
    """LA container ZIP archives come from outside; member names are untrusted."""

    def test_ordinary_member_paths_are_accepted(self) -> None:
        for name in ("lamanifest.xml", "data/entry.json", "a/b/c.txt"):
            with self.subTest(name=name):
                self.assertIsNone(notebook_operations._member_path_error(name))

    def test_traversal_and_absolute_paths_are_rejected(self) -> None:
        for name in ("../escape.xml", "a/../../b", "/etc/passwd", "C:\\win\\x"):
            with self.subTest(name=name):
                self.assertIsNotNone(notebook_operations._member_path_error(name))

    def test_backslashes_nulls_and_empty_names_are_rejected(self) -> None:
        for name in ("a\\b", "a\x00b", ""):
            with self.subTest(name=repr(name)):
                self.assertIsNotNone(notebook_operations._member_path_error(name))

    def test_redundant_but_harmless_segments_are_allowed(self) -> None:
        # PurePosixPath collapses `.` and doubled separators, so these resolve
        # inside the extraction root and are not treated as ambiguous. Only
        # `..` actually escapes.
        for name in ("./a.txt", "a/./b", "a//b"):
            with self.subTest(name=name):
                self.assertIsNone(notebook_operations._member_path_error(name))

    def test_symlink_members_are_detected_from_the_mode_bits(self) -> None:
        link = zipfile.ZipInfo("link")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assertTrue(notebook_operations._is_symlink(link))

        regular = zipfile.ZipInfo("file")
        regular.external_attr = (stat.S_IFREG | 0o644) << 16
        self.assertFalse(notebook_operations._is_symlink(regular))


class ContainerLimitTests(unittest.TestCase):
    def test_the_documented_limits_are_positive_and_ordered(self) -> None:
        # Every limit exists to stop a zip bomb; a zero or negative one would
        # disable the guard silently.
        for name in (
            "DEFAULT_MAX_MEMBERS",
            "DEFAULT_MAX_TOTAL_BYTES",
            "DEFAULT_MAX_MANIFEST_BYTES",
            "DEFAULT_MAX_INDEX_BYTES",
            "DEFAULT_MAX_COMPRESSION_RATIO",
        ):
            with self.subTest(limit=name):
                self.assertGreater(getattr(notebook_operations, name), 0)
        self.assertLess(
            notebook_operations.DEFAULT_MAX_MANIFEST_BYTES,
            notebook_operations.DEFAULT_MAX_TOTAL_BYTES,
        )

    def _inspect(self, build) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "notebook.eln"
            with zipfile.ZipFile(archive, "w") as handle:
                build(handle)
            return notebook_operations.inspect_container(archive)

    def test_a_traversing_member_is_reported_as_an_error(self) -> None:
        # The inspector reports rather than raises: the point is to hand back a
        # full account of what is wrong with an archive, not to stop at the
        # first problem.
        report = self._inspect(lambda z: z.writestr("../escaped.xml", "<x/>"))
        self.assertTrue(report["errors"])
        self.assertTrue(
            any("unsafe member paths" in error for error in report["errors"]),
            report["errors"],
        )

    def test_a_symlink_member_is_reported_as_an_error(self) -> None:
        def build(handle: zipfile.ZipFile) -> None:
            info = zipfile.ZipInfo("link")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            handle.writestr(info, "/etc/passwd")

        report = self._inspect(build)
        self.assertTrue(report["errors"])

    def test_a_missing_manifest_is_reported(self) -> None:
        report = self._inspect(lambda z: z.writestr("data/entry.json", "{}"))
        self.assertTrue(report["errors"] or report["warnings"])
        combined = " ".join(report["errors"] + report["warnings"])
        self.assertIn(notebook_operations.MANIFEST_NAME, combined)

    def test_non_positive_limits_are_refused_outright(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "notebook.eln"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("a.txt", "x")
            for override in ("max_members", "max_total_bytes", "max_manifest_bytes"):
                with self.subTest(limit=override):
                    with self.assertRaisesRegex(
                        notebook_operations.InspectionError, "must be positive"
                    ):
                        notebook_operations.inspect_container(archive, **{override: 0})

    def test_a_member_count_over_the_limit_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "notebook.eln"
            with zipfile.ZipFile(archive, "w") as handle:
                for index in range(5):
                    handle.writestr(f"file{index}.txt", "x")
            report = notebook_operations.inspect_container(archive, max_members=2)
        self.assertTrue(report["errors"])

    def test_a_missing_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((notebook_operations.InspectionError, OSError)):
                notebook_operations.inspect_container(Path(directory) / "absent.eln")

    def test_a_non_zip_file_is_refused_rather_than_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "notebook.eln"
            archive.write_bytes(b"not a zip at all")
            with self.assertRaises((notebook_operations.InspectionError, zipfile.BadZipFile)):
                notebook_operations.inspect_container(archive)

    def test_the_manifest_name_is_the_documented_one(self) -> None:
        self.assertEqual(notebook_operations.MANIFEST_NAME, "lamanifest.xml")


class XmlHelperTests(unittest.TestCase):
    def test_namespaced_tags_are_reduced_to_their_local_name(self) -> None:
        self.assertEqual(notebook_operations._local_name("{urn:x}entry"), "entry")
        self.assertEqual(notebook_operations._local_name("entry"), "entry")


if __name__ == "__main__":
    unittest.main()
