"""Tests for the Fictiv skill's bundled tooling.

`check_cad_file.py` is standard-library only, so everything here runs in the
bare environment. The STEP fixtures are real Open CASCADE exports from
build123d 0.11 (a 60 x 40 x 15 mm block with a 4 mm through hole, the same
geometry re-expressed in inch units the way SolidWorks and Creo write them,
two separate solids in one file, and a lone face). STL meshes are generated
in-test because a cube is twelve triangles.

The browser scripts (`quote_state.js`, `list_dropdown_options.js`) only run
against a logged-in app.fictiv.com session, so they are checked for syntax and
for the read-only promise the skill makes about them, not for behaviour.
"""

from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "fictiv"
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import check_cad_file  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

BROWSER_SCRIPTS = ("quote_state.js", "list_dropdown_options.js")

CUBE_FACES = (
    ((0, 0, 0), (1, 1, 0), (1, 0, 0)), ((0, 0, 0), (0, 1, 0), (1, 1, 0)),
    ((0, 0, 1), (1, 0, 1), (1, 1, 1)), ((0, 0, 1), (1, 1, 1), (0, 1, 1)),
    ((0, 0, 0), (1, 0, 0), (1, 0, 1)), ((0, 0, 0), (1, 0, 1), (0, 0, 1)),
    ((0, 1, 0), (1, 1, 1), (1, 1, 0)), ((0, 1, 0), (0, 1, 1), (1, 1, 1)),
    ((0, 0, 0), (0, 0, 1), (0, 1, 1)), ((0, 0, 0), (0, 1, 1), (0, 1, 0)),
    ((1, 0, 0), (1, 1, 0), (1, 1, 1)), ((1, 0, 0), (1, 1, 1), (1, 0, 1)),
)


def cube(size: tuple[float, float, float], drop: int = 0) -> list:
    """Triangles of an axis-aligned box, optionally with `drop` facets removed."""
    faces = CUBE_FACES[: len(CUBE_FACES) - drop]
    return [tuple(tuple(c * s for c, s in zip(v, size)) for v in tri) for tri in faces]


def write_binary_stl(path: Path, tris: list) -> None:
    with open(path, "wb") as fh:
        fh.write(b"\0" * 80 + struct.pack("<I", len(tris)))
        for tri in tris:
            fh.write(struct.pack("<3f", 0, 0, 0))
            for v in tri:
                fh.write(struct.pack("<3f", *v))
            fh.write(b"\0\0")


def write_ascii_stl(path: Path, tris: list) -> None:
    rows = ["solid test"]
    for tri in tris:
        rows += ["facet normal 0 0 0", "outer loop"]
        rows += [f"vertex {x} {y} {z}" for x, y, z in tri]
        rows += ["endloop", "endfacet"]
    path.write_text("\n".join(rows + ["endsolid test"]) + "\n")


def scaled_step(src: Path, dst: Path, sx: float, sy: float, sz: float) -> None:
    """Copy a STEP file with every CARTESIAN_POINT scaled per axis.

    The result is not a valid solid for the curved faces, but the checker only
    reads vertex coordinates for its bounding box, which is what is under test.
    """

    def scale(m: re.Match) -> str:
        coords = [float(c) for c in m.group(2).split(",")]
        if len(coords) != 3:  # 2D parameter-space points on pcurves
            return m.group(0)
        x, y, z = coords
        return f"{m.group(1)}{x * sx:.6G},{y * sy:.6G},{z * sz:.6G}{m.group(3)}"

    text = src.read_text()
    dst.write_text(re.sub(r"(CARTESIAN_POINT\('[^']*',\()([^)]*)(\))", scale, text))


class StepInspectionTests(unittest.TestCase):
    def test_single_mm_block_is_clean(self):
        r = check_cad_file.check(str(FIXTURES / "block_mm.step"), "cnc")
        self.assertEqual(r["blocking"], [])
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["info"]["solid_bodies"], 1)
        self.assertEqual(r["info"]["length_unit"], "mm")
        self.assertEqual(r["info"]["approx_bbox_mm"], [60.0, 40.0, 15.0])
        self.assertIn("214", r["info"]["schema"])

    def test_inch_unit_is_detected_and_bbox_converted_to_mm(self):
        # The inch file still carries an SI millimetre entity as the conversion
        # base, so the inch check has to win over the millimetre one.
        r = check_cad_file.check(str(FIXTURES / "block_inch.step"), "cnc")
        self.assertEqual(r["info"]["length_unit"], "inch")
        self.assertEqual(r["info"]["approx_bbox_mm"], [50.8, 25.4, 12.7])
        self.assertEqual(r["blocking"], [])

    def test_multi_body_blocks_cnc_but_only_warns_for_3dp(self):
        path = str(FIXTURES / "two_bodies.step")
        cnc = check_cad_file.check(path, "cnc")
        self.assertEqual(cnc["info"]["solid_bodies"], 2)
        self.assertTrue(any("2 solid bodies" in b for b in cnc["blocking"]))
        printed = check_cad_file.check(path, "3dp")
        self.assertEqual(printed["blocking"], [])
        self.assertTrue(any("2 solid bodies" in w for w in printed["warnings"]))

    def test_surface_only_model_is_blocked(self):
        r = check_cad_file.check(str(FIXTURES / "surface_only.step"), "cnc")
        self.assertEqual(r["info"]["solid_bodies"], 0)
        self.assertTrue(any("only surface geometry" in b for b in r["blocking"]))

    def test_itar_marking_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            marked = Path(tmp) / "marked.step"
            text = (FIXTURES / "block_mm.step").read_text()
            marked.write_text(text.replace("PRODUCT('", "PRODUCT('ITAR CONTROLLED ", 1))
            r = check_cad_file.check(str(marked), "cnc")
        self.assertTrue(any("ITAR" in b for b in r["blocking"]))

    def test_oversize_cnc_part_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            long_bar = Path(tmp) / "long.step"
            scaled_step(FIXTURES / "block_mm.step", long_bar, 35, 1, 1)
            r = check_cad_file.check(str(long_bar), "cnc")
        self.assertEqual(r["info"]["approx_bbox_mm"], [2100.0, 40.0, 15.0])
        self.assertTrue(any("exceeds Fictiv's published cnc envelope" in w for w in r["warnings"]))

    def test_unknown_units_are_not_reported_as_millimetres(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unknown.step"
            path.write_text((FIXTURES / "block_mm.step").read_text().replace(
                "SI_UNIT(.MILLI.,.METRE.)", "SI_UNIT($,.UNRECOGNIZED.)"))
            r = check_cad_file.check(str(path), "cnc")
        self.assertEqual(r["info"]["length_unit"], "unknown")
        self.assertEqual(r["info"]["approx_bbox_units"], [60.0, 40.0, 15.0])
        self.assertNotIn("approx_bbox_mm", r["info"])

    def test_envelope_check_is_orientation_independent(self):
        # 900 x 700 x 100 mm fits the 914 x 609 x 914 mm FDM envelope once the
        # part is laid flat; comparing sorted part dims to unsorted envelope
        # axes used to flag it.
        with tempfile.TemporaryDirectory() as tmp:
            big = Path(tmp) / "big.step"
            scaled_step(FIXTURES / "block_mm.step", big, 15, 17.5, 100 / 15)
            r = check_cad_file.check(str(big), "3dp")
        self.assertEqual(r["info"]["approx_bbox_mm"], [900.0, 700.0, 100.0])
        self.assertFalse(any("envelope" in w for w in r["warnings"]), r["warnings"])


class StlInspectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_binary_and_ascii_closed_box_are_watertight(self):
        for writer, encoding in ((write_binary_stl, "binary"), (write_ascii_stl, "ascii")):
            with self.subTest(encoding=encoding):
                path = self.tmp / f"box_{encoding}.stl"
                writer(path, cube((60, 40, 15)))
                r = check_cad_file.check(str(path), "3dp")
                self.assertEqual(r["info"]["encoding"], encoding)
                self.assertEqual(r["info"]["triangles"], 12)
                self.assertTrue(r["info"]["watertight"])
                self.assertEqual(r["info"]["bbox_units"], [60.0, 40.0, 15.0])
                self.assertEqual(r["blocking"], [])
                self.assertEqual(r["warnings"], [])

    def test_open_mesh_warns(self):
        path = self.tmp / "open.stl"
        write_binary_stl(path, cube((60, 40, 15), drop=1))
        r = check_cad_file.check(str(path), "3dp")
        self.assertFalse(r["info"]["watertight"])
        self.assertEqual(r["info"]["non_manifold_or_open_edges"], 3)
        self.assertTrue(any("not watertight" in w for w in r["warnings"]))

    def test_mesh_is_blocked_for_non_printing_processes(self):
        path = self.tmp / "box.stl"
        write_binary_stl(path, cube((60, 40, 15)))
        for process in ("cnc", "sheet", "urethane", "im"):
            with self.subTest(process=process):
                r = check_cad_file.check(str(path), process)
                self.assertTrue(any("3D printing only" in b for b in r["blocking"]))

    def test_tiny_mesh_suggests_inch_units(self):
        path = self.tmp / "tiny.stl"
        write_binary_stl(path, cube((2, 1, 0.5)))
        r = check_cad_file.check(str(path), "3dp")
        self.assertTrue(any("25.4x too small" in w for w in r["warnings"]))
        self.assertEqual(r["info"]["bbox_if_inch_in_mm"], [50.8, 25.4, 12.7])


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def touch(self, name: str, content: bytes = b"x") -> str:
        path = self.tmp / name
        path.write_bytes(content)
        return str(path)

    def test_rejected_formats_block(self):
        for name, fragment in (
            ("part.igs", "IGES"),
            ("part.iges", "IGES"),
            ("part.f3d", "Fusion 360"),
            ("part.dxf", "DXF"),
            ("part.psm", "Solid Edge sheet metal"),
            ("part.pwd", "Solid Edge weldment"),
            ("top.sldasm", "assembly files"),
            ("part.xyz", "unrecognized extension"),
        ):
            with self.subTest(name=name):
                r = check_cad_file.check(self.touch(name), "cnc")
                self.assertTrue(any(fragment in b for b in r["blocking"]), r["blocking"])

    def test_mesh_formats_in_uploader_do_not_bypass_process_restriction(self):
        for ext in ("acs", "wrl"):
            path = self.touch(f"part.{ext}")
            self.assertTrue(check_cad_file.check(path, "cnc")["blocking"])
            self.assertEqual(check_cad_file.check(path, "3dp")["blocking"], [])

    def test_upload_only_formats_require_support_verification(self):
        for ext in ("3mf", "gts", "ifczip", "xmt"):
            result = check_cad_file.check(self.touch(f"part.{ext}"), "cnc")
            self.assertTrue(any("support is unverified" in b for b in result["blocking"]))

    def test_pdf_alone_warns_but_does_not_block(self):
        r = check_cad_file.check(self.touch("drawing.pdf"), "cnc")
        self.assertEqual(r["blocking"], [])
        self.assertTrue(any("drawings cannot be quoted alone" in w for w in r["warnings"]))

    def test_ambiguous_native_formats_warn(self):
        prt = check_cad_file.check(self.touch("part.prt"), "cnc")
        self.assertTrue(any("ambiguous" in w for w in prt["warnings"]))
        sw = check_cad_file.check(self.touch("part.SLDPRT"), "cnc")
        self.assertTrue(any("single configuration" in w for w in sw["warnings"]))

    def test_empty_and_missing_files_block(self):
        self.assertIn("file is empty", check_cad_file.check(self.touch("e.step", b""), "cnc")["blocking"])
        self.assertIn("file not found", check_cad_file.check(str(self.tmp / "nope.step"), "cnc")["blocking"])


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "check_cad_file.py"), *args],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_exit_zero_when_nothing_blocks(self):
        proc = self.run_cli(str(FIXTURES / "block_mm.step"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[OK]", proc.stdout)

    def test_exit_one_when_any_file_blocks(self):
        proc = self.run_cli(str(FIXTURES / "block_mm.step"), str(FIXTURES / "two_bodies.step"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("[BLOCKED]", proc.stdout)

    def test_json_output_is_one_record_per_file(self):
        proc = self.run_cli(str(FIXTURES / "block_inch.step"), "--process", "3dp", "--json")
        records = json.loads(proc.stdout)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["process"], "3dp")
        self.assertEqual(records[0]["info"]["length_unit"], "inch")

    def test_unknown_process_is_rejected(self):
        proc = self.run_cli(str(FIXTURES / "block_mm.step"), "--process", "laser")
        self.assertEqual(proc.returncode, 2)


class BrowserScriptTests(unittest.TestCase):
    """The page scripts are pasted into a browser JS tool on a live session."""

    def test_scripts_parse(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        # Parse each file as an async function body: that accepts the top-level
        # `await` list_dropdown_options.js relies on, as the browser tool does.
        check = (
            "const AsyncFunction = (async () => {}).constructor;"
            "new AsyncFunction(require('fs').readFileSync(process.argv[1], 'utf8'));"
        )
        for name in BROWSER_SCRIPTS:
            with self.subTest(script=name):
                proc = subprocess.run(
                    [node, "-e", check, str(SCRIPTS / name)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_scripts_are_read_only(self):
        # SKILL.md sends agents to these scripts on quote and checkout pages,
        # next to "Place order"; they must never act on the page or the network.
        forbidden = re.compile(r"\.click\(|dispatchEvent|\.submit\(|\bfetch\(|XMLHttpRequest|sendBeacon")
        for name in BROWSER_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text(encoding="utf-8")
                self.assertIsNone(forbidden.search(source))

    def test_async_script_keeps_its_leading_await(self):
        # The JS tool does not unwrap a bare Promise, so dropping the `await`
        # makes the script return `{}`.
        source = (SCRIPTS / "list_dropdown_options.js").read_text(encoding="utf-8")
        code = [ln for ln in source.splitlines() if ln.strip() and not ln.lstrip().startswith("//")]
        self.assertTrue(code[0].startswith("await (async"), code[0])


if __name__ == "__main__":
    unittest.main()
