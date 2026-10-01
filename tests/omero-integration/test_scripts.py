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
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "omero-integration"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import export_image_metadata  # noqa: E402
import inventory  # noqa: E402
import plan_transfer  # noqa: E402
from omero_common import (  # noqa: E402
    ConfigError,
    atomic_write_json,
    config_summary,
    gateway_session,
    json_safe,
    load_connection_config,
    take_bounded,
)

import skill_contract


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


class SessionLifecycleTests(unittest.TestCase):
    def test_shared_session_is_released_without_being_killed(self):
        config = load_connection_config(
            require_auth=True,
            environ={"OMERO_HOST": "omero.example.org", "OMERO_SESSION_KEY": "synthetic-key"},
        )
        gateway = Mock()
        gateway.connect.return_value = True
        module = ModuleType("omero.gateway")
        module.BlitzGateway = Mock(return_value=gateway)
        with patch.dict(sys.modules, {"omero.gateway": module}):
            with self.assertRaises(RuntimeError):
                with gateway_session(config, allow_insecure_transport=False):
                    raise RuntimeError("synthetic failure")
        gateway.connect.assert_called_once_with(sUuid="synthetic-key")
        gateway.close.assert_called_once_with(hard=False)

    def test_owned_session_is_closed_after_failed_login(self):
        config = load_connection_config(
            require_auth=True,
            environ={"OMERO_HOST": "omero.example.org", "OMERO_USER": "test", "OMERO_PASSWORD": "test"},
        )
        gateway = Mock()
        gateway.connect.return_value = False
        module = ModuleType("omero.gateway")
        module.BlitzGateway = Mock(return_value=gateway)
        with patch.dict(sys.modules, {"omero.gateway": module}):
            with self.assertRaises(RuntimeError):
                with gateway_session(config, allow_insecure_transport=False):
                    self.fail("failed login must not yield a gateway")
        gateway.close.assert_called_once_with(hard=True)


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
    def test_annotation_type_falls_back_when_upstream_class_is_none(self):
        annotation_class = type("FileAnnotationWrapper", (FakeAnnotation,), {"OMERO_CLASS": None})
        record = export_image_metadata.annotation_record(
            annotation_class(), include_values=False, include_owner_names=False,
            include_file_names=False, max_string_length=128, max_value_items=10,
        )
        self.assertEqual(record["type"], "FileAnnotation")
        self.assertEqual(record["file"]["original_file_id"], 77)

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


class RoiTests(unittest.TestCase):
    def test_roi_call_uses_selected_group_context(self):
        image = FakeImage(123)
        image.listAnnotations = lambda: iter(())
        connection = Mock(SERVICE_OPTS={"omero.group": "42"})
        connection.getObject.return_value = image
        service = Mock()
        service.findByImage.return_value = SimpleNamespace(rois=[])
        args = export_image_metadata.build_parser().parse_args(
            ["--image-id", "123", "--output", "result.json"]
        )
        result = export_image_metadata.export_one_image(connection, service, 123, args)
        service.findByImage.assert_called_once_with(123, None, connection.SERVICE_OPTS)
        self.assertEqual(result["returned_rois"], 0)

    def test_transform_and_truncated_points_are_reported(self):
        transform = SimpleNamespace(**{
            "get" + field: lambda value=value: value
            for field, value in zip(("A00", "A01", "A02", "A10", "A11", "A12"), (0, -1, 10, 1, 0, 20))
        })
        shape = type("PolygonI", (), {
            "getTransform": lambda self: transform,
            "getPoints": lambda self: "1,2 3,4 5,6 " * 20,
            "getTheZ": lambda self: None,
        })()
        record = export_image_metadata.shape_record(shape, include_labels=False, max_string_length=32)
        self.assertEqual(record["transform"], {"a00": 0, "a01": -1, "a02": 10, "a10": 1, "a11": 0, "a12": 20})
        self.assertIsNone(record["the_z"])
        self.assertTrue(record["geometry_truncated"])
        self.assertTrue(record["label_redacted"])

    def test_actual_omero_shape_and_annotation_models_when_installed(self):
        try:
            from omero.model import AffineTransformI, RectangleI, TagAnnotationI
            from omero.rtypes import rdouble, rlong, rstring
            from omero.gateway import TagAnnotationWrapper
        except ImportError:
            self.skipTest("optional OMERO.py and IcePy not installed")
        shape = RectangleI()
        shape.setX(rdouble(1.5))
        shape.setY(rdouble(2.5))
        shape.setWidth(rdouble(10))
        shape.setHeight(rdouble(20))
        transform = AffineTransformI()
        for field, value in zip(("A00", "A01", "A02", "A10", "A11", "A12"), (1, 0, 10, 0, 1, 20)):
            getattr(transform, "set" + field)(rdouble(value))
        shape.setTransform(transform)
        record = export_image_metadata.shape_record(shape, include_labels=False, max_string_length=32)
        self.assertEqual(record["geometry"]["x"], 1.5)
        self.assertEqual(record["transform"]["a12"], 20)
        self.assertFalse(record["geometry_truncated"])
        model = TagAnnotationI()
        model.setId(rlong(9))
        model.setTextValue(rstring("private-label"))
        annotation = TagAnnotationWrapper(obj=model)
        record = export_image_metadata.annotation_record(
            annotation, include_values=False, include_owner_names=False,
            include_file_names=False, max_string_length=128, max_value_items=10,
        )
        self.assertEqual(record["type"], "TagAnnotation")
        self.assertNotIn("private-label", json.dumps(record))


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
                self.assertEqual(command[command.index("--depth") + 1], "4")
                self.assertNotIn("--password", command)
                self.assertNotIn("-w", command)
                self.assertNotIn("-k", command)
            self.assertFalse(plan["commands_executed"])

    def test_skipped_symlink_prevents_ready_import_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "a.tif"
            source.write_bytes(b"a")
            try:
                (root / "linked.tif").symlink_to(source)
            except OSError:
                self.skipTest("symlinks unavailable")
            args = argparse.Namespace(paths=[str(root)], target=None, max_paths=1, max_files=1, scan_depth=4)
            plan = plan_transfer.plan_import(args)
            self.assertEqual(plan["skipped_symlinks"], 1)
            self.assertFalse(plan["ready_for_remote_import_review"])

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


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
