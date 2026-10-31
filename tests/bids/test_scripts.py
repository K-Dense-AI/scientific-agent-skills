"""Tests for the BIDS schema updater.

`update_schema.py` is a maintenance script that overwrites files in the skill's
own `references/` directory from the network. Neither of those is acceptable in
a test, so every test here redirects `REFERENCES_DIR` at a temporary directory
and replaces `fetch` with a stub. Nothing reaches the network and nothing
touches the shipped references.

The other half of the suite checks the artefacts that *are* shipped: a schema
the script wrote once must still be parseable and carry its version fields,
because the skill's documentation quotes them.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "bids"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"
sys.path.insert(0, str(SCRIPTS))

import update_schema  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class TemporaryReferencesTestCase(unittest.TestCase):
    """Point the script's output directory at a scratch dir for the test."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.references = Path(self._temporary.name)
        patcher = mock.patch.object(update_schema, "REFERENCES_DIR", self.references)
        patcher.start()
        self.addCleanup(patcher.stop)


class SchemaWriteTests(TemporaryReferencesTestCase):
    SCHEMA = {
        "schema_version": "1.2.1",
        "bids_version": "1.11.1",
        "objects": {"entities": {"subject": {"name": "sub"}}},
        "rules": {"entities": ["subject"]},
    }

    def test_downloaded_schema_is_reserialised_with_stable_formatting(self) -> None:
        # Upstream ships minified JSON; the script re-indents so the checked-in
        # copy diffs sanely on the next update.
        minified = json.dumps(self.SCHEMA, separators=(",", ":")).encode("utf-8")
        with mock.patch.object(update_schema, "fetch", return_value=minified):
            update_schema.update_schema("https://example.invalid/schema.json")

        written = self.references / "bids_schema.json"
        text = written.read_text(encoding="utf-8")
        self.assertEqual(json.loads(text), self.SCHEMA)
        self.assertIn("\n  ", text, "output should be indented")
        self.assertTrue(text.endswith("\n"), "output should end with a newline")

    def test_the_reported_versions_come_from_the_payload(self) -> None:
        payload = json.dumps(self.SCHEMA).encode("utf-8")
        with mock.patch.object(update_schema, "fetch", return_value=payload):
            with mock.patch("builtins.print") as printed:
                update_schema.update_schema("https://example.invalid/schema.json")
        output = " ".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("schema 1.2.1", output)
        self.assertIn("BIDS 1.11.1", output)

    def test_incomplete_schema_does_not_replace_existing_snapshot(self) -> None:
        target = self.references / "bids_schema.json"
        target.write_bytes(b"previous snapshot")
        for payload in (b"{}", b"[]", b'{"bids_version":"1.11.2"}'):
            with self.subTest(payload=payload):
                with mock.patch.object(update_schema, "fetch", return_value=payload):
                    with self.assertRaises(ValueError):
                        update_schema.update_schema("https://example.invalid/schema.json")
                self.assertEqual(target.read_bytes(), b"previous snapshot")

    def test_a_non_json_response_fails_before_anything_is_written(self) -> None:
        with mock.patch.object(update_schema, "fetch", return_value=b"<html>404</html>"):
            with self.assertRaises(json.JSONDecodeError):
                update_schema.update_schema("https://example.invalid/schema.json")
        self.assertFalse((self.references / "bids_schema.json").exists())


class BepsWriteTests(TemporaryReferencesTestCase):
    def test_beps_are_written_verbatim_and_counted(self) -> None:
        payload = (
            b"# template\n"
            b"-   number: '004'\n    title: Diffusion\n"
            b"-   number: '011'\n    title: Structural\n"
        )
        with mock.patch.object(update_schema, "fetch", return_value=payload):
            with mock.patch("builtins.print") as printed:
                update_schema.update_beps()

        written = self.references / "beps.yml"
        self.assertEqual(written.read_bytes(), payload)
        output = " ".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("2 BEPs", output)

    def test_count_accepts_yaml_spacing_and_first_line(self) -> None:
        self.assertEqual(update_schema.bep_numbers(b"- number: '001'\n-   number: 002\n"), ["001", "002"])

    def test_rejects_error_payload_and_duplicate_ids_without_overwriting(self) -> None:
        target = self.references / "beps.yml"
        target.write_bytes(b"previous catalogue")
        for payload in (b"<html>Denied</html>", b"- number: 001\n- number: 001\n"):
            with self.subTest(payload=payload):
                with mock.patch.object(update_schema, "fetch", return_value=payload):
                    with self.assertRaises(ValueError):
                        update_schema.update_beps()
                self.assertEqual(target.read_bytes(), b"previous catalogue")



class FetchTests(unittest.TestCase):
    def test_requests_carry_an_identifying_user_agent(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"{}"
        with mock.patch("urllib.request.urlopen", return_value=response) as opened:
            update_schema.fetch("https://example.invalid/x.json")

        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.invalid/x.json")
        self.assertIn("bids-skill-updater", request.get_header("User-agent"))
        self.assertEqual(opened.call_args.kwargs["timeout"], 30)
        response.__enter__.return_value.read.assert_called_once_with(update_schema.MAX_BYTES + 1)

    def test_oversized_response_and_non_https_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            update_schema.fetch("file:///etc/passwd")
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"12345"
        with mock.patch.object(update_schema, "MAX_BYTES", 4):
            with mock.patch("urllib.request.urlopen", return_value=response):
                with self.assertRaises(ValueError):
                    update_schema.fetch("https://example.invalid/schema.json")

    def test_the_default_sources_are_https_and_upstream(self) -> None:
        self.assertTrue(update_schema.SCHEMA_URL.startswith("https://"))
        self.assertTrue(update_schema.BEPS_URL.startswith("https://"))
        self.assertIn("bids-specification", update_schema.SCHEMA_URL)
        self.assertIn("bids-standard", update_schema.BEPS_URL)


class ShippedReferenceTests(unittest.TestCase):
    """The artefacts the script produced last time it ran must still be usable."""

    def test_the_shipped_schema_parses_and_is_versioned(self) -> None:
        schema = json.loads((REFERENCES / "bids_schema.json").read_text(encoding="utf-8"))
        self.assertRegex(schema["schema_version"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(schema["bids_version"], r"^\d+\.\d+\.\d+$")
        self.assertIn("objects", schema)

    def test_the_references_directory_is_where_the_script_writes(self) -> None:
        self.assertEqual(update_schema.REFERENCES_DIR, REFERENCES)
        self.assertTrue((REFERENCES / "beps.yml").is_file())
        self.assertTrue((REFERENCES / "bids_schema.json").is_file())


if __name__ == "__main__":
    unittest.main()
