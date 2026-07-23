"""Synthetic tests for the OMERO helper scripts; no server is contacted."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import export_image_metadata  # noqa: E402
import inventory  # noqa: E402
import plan_transfer  # noqa: E402
from omero_common import (  # noqa: E402
    ConfigError,
    atomic_write_json,
    config_summary,
    json_safe,
    load_connection_config,
    take_bounded,
)


class FakeParty:
    def __init__(self, identifier: int, username: str = "private-user"):
        self.identifier = identifier
        self.username = username

    def getId(self) -> int:
        return self.identifier

    def getOmeName(self) -> str:
        return self.username


class FakeDetails:
    def __init__(self):
        self.owner = FakeParty(7)
        self.group = FakeParty(8)

    def getOwner(self) -> FakeParty:
        return self.owner

    def getGroup(self) -> FakeParty:
        return self.group


class FakeImage:
    OMERO_CLASS = "Image"

    def __init__(self, identifier: int):
        self.identifier = identifier

    def getId(self) -> int:
        return self.identifier

    def getName(self) -> str:
        return f"sensitive-{self.identifier}"

    def getDetails(self) -> FakeDetails:
        return FakeDetails()

    def getSizeX(self) -> int:
        return 10

    def getSizeY(self) -> int:
        return 20

    def getSizeZ(self) -> int:
        return 2

    def getSizeC(self) -> int:
        return 3

    def getSizeT(self) -> int:
        return 4

    def getPixelsType(self) -> str:
        return "uint16"


class FakeConnection:
    def __init__(self, count: int):
        self.objects = [FakeImage(index + 1) for index in range(count)]
        self.requests: list[dict[str, int | str]] = []

    def getObjects(self, object_type: str, opts: dict):
        self.requests.append(dict(opts))
        start = int(opts["offset"])
        stop = start + int(opts["limit"])
        return iter(self.objects[start:stop])


class FakeFile:
    def getId(self) -> int:
        return 77

    def getSize(self) -> int:
        return 1234

    def getMimetype(self) -> str:
        return "text/plain"

    def getName(self) -> str:
        return "sensitive-name.txt"


class FakeAnnotation:
    OMERO_CLASS = "FileAnnotation"

    def __init__(self):
        self.value_read = False

    def getId(self) -> int:
        return 11

    def getNs(self) -> str:
        return "org.example"

    def getDetails(self) -> FakeDetails:
        return FakeDetails()

    def getValue(self) -> str:
        self.value_read = True
        return "sensitive-value"

    def getFile(self) -> FakeFile:
        return FakeFile()


class ConfigTests(unittest.TestCase):
    def test_defaults_and_no_auth(self):
        config = load_connection_config(
            require_auth=False,
            environ={"OMERO_HOST": "omero.example.org"},
        )
        self.assertEqual(config.port, 4064)
        self.assertTrue(config.secure)
        self.assertEqual(config.authentication_mode, "missing")

    def test_session_key_takes_precedence_without_leaking(self):
        environment = {
            "OMERO_HOST": "omero.example.org",
            "OMERO_USER": "secret-user",
            "OMERO_PASSWORD": "secret-password",
            "OMERO_SESSION_KEY": "secret-session",
        }
        config = load_connection_config(
            require_auth=True,
            environ=environment,
        )
        self.assertEqual(config.authentication_mode, "session_key")
        serialized = json.dumps(
            config_summary(config, environ=environment)
        )
        self.assertNotIn("secret-user", serialized)
        self.assertNotIn("secret-password", serialized)
        self.assertNotIn("secret-session", serialized)

    def test_partial_password_auth_is_rejected(self):
        with self.assertRaises(ConfigError):
            load_connection_config(
                require_auth=False,
                environ={
                    "OMERO_HOST": "omero.example.org",
                    "OMERO_USER": "user-only",
                },
            )

    def test_url_is_not_a_host(self):
        with self.assertRaises(ConfigError):
            load_connection_config(
                require_auth=False,
                environ={"OMERO_HOST": "https://omero.example.org"},
            )


class OutputTests(unittest.TestCase):
    def test_atomic_json_refuses_overwrite_and_uses_private_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            written = atomic_write_json(
                output,
                {"ok": True},
                overwrite=False,
            )
            self.assertEqual(json.loads(written.read_text()), {"ok": True})
            mode = stat.S_IMODE(written.stat().st_mode)
            self.assertEqual(mode, 0o600)
            with self.assertRaises(FileExistsError):
                atomic_write_json(
                    output,
                    {"ok": False},
                    overwrite=False,
                )

    def test_atomic_json_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.json"
            real.write_text("{}")
            link = root / "link.json"
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ValueError):
                atomic_write_json(link, {"ok": True}, overwrite=True)


class BoundTests(unittest.TestCase):
    def test_take_bounded_detects_extra_item(self):
        result = take_bounded(range(5), 3)
        self.assertEqual(result.items, [0, 1, 2])
        self.assertTrue(result.truncated)

    def test_json_safe_bounds_nested_values(self):
        result = json_safe(
            ["abcdef", "ghijkl", "mnopqr"],
            max_string_length=3,
            max_collection_length=2,
        )
        self.assertEqual(len(result), 3)
        self.assertIn("truncated", result[0])
        self.assertEqual(result[-1], {"truncated_items": 1})


class InventoryTests(unittest.TestCase):
    def test_inventory_pages_and_redacts_names(self):
        connection = FakeConnection(7)
        result = inventory.collect_inventory(
            connection,
            object_type="Image",
            limit=5,
            page_size=2,
            include_names=False,
        )
        self.assertEqual(result["returned"], 5)
        self.assertTrue(result["limit_reached"])
        self.assertEqual(
            [request["offset"] for request in connection.requests],
            [0, 2, 4],
        )
        self.assertTrue(
            all(record["name_redacted"] for record in result["records"])
        )
        self.assertNotIn(
            "sensitive",
            json.dumps(result),
        )


class RedactionTests(unittest.TestCase):
    def test_annotation_value_and_filename_not_read_when_redacted(self):
        annotation = FakeAnnotation()
        record = export_image_metadata.annotation_record(
            annotation,
            include_values=False,
            include_owner_names=False,
            include_file_names=False,
            max_string_length=128,
            max_value_items=10,
        )
        self.assertFalse(annotation.value_read)
        self.assertTrue(record["value_redacted"])
        self.assertTrue(record["file"]["name_redacted"])
        self.assertNotIn("sensitive", json.dumps(record))


class TransferPlannerTests(unittest.TestCase):
    def test_import_plan_is_bounded_and_contains_no_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.tif").write_bytes(b"a")
            (root / "b.tif").write_bytes(b"b")
            args = argparse.Namespace(
                paths=[str(root)],
                target="Dataset:id:42",
                max_paths=2,
                max_files=2,
                scan_depth=4,
            )
            plan = plan_transfer.plan_import(args)
            self.assertEqual(plan["total_regular_files"], 2)
            commands = [
                command
                for entry in plan["entries"]
                for command in (
                    entry["local_omero_scan_command"],
                    entry["future_remote_import_command"],
                )
            ]
            for command in commands:
                self.assertNotIn("--password", command)
                self.assertNotIn("-w", command)
                self.assertNotIn("-k", command)
            self.assertFalse(plan["commands_executed"])

    def test_export_plan_reports_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "image-5.ome.xml").write_text("existing")
            args = argparse.Namespace(
                selectors=["Image:5"],
                format="xml",
                output_dir=str(output),
                max_images=1,
            )
            plan = plan_transfer.plan_export(args)
            self.assertEqual(plan["collisions"], 1)
            self.assertFalse(plan["ready_for_remote_export_review"])
            self.assertFalse(plan["commands_executed"])

    def test_import_plan_caps_multiple_top_level_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.tif"
            second = root / "b.tif"
            first.write_bytes(b"a")
            second.write_bytes(b"b")
            args = argparse.Namespace(
                paths=[str(first), str(second)],
                target=None,
                max_paths=2,
                max_files=1,
                scan_depth=4,
            )
            with self.assertRaises(ValueError):
                plan_transfer.plan_import(args)


if __name__ == "__main__":
    unittest.main()
