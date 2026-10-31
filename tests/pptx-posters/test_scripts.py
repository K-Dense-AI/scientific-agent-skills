"""Dependency-free synthetic tests for manifest and PPTX security helpers."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pptx-posters"
SCRIPTS = SKILL_ROOT / "scripts"
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from _common import (  # noqa: E402
    CliError,
    atomic_write_bytes,
    load_json_file,
    resolve_local_asset,
)
from _manifest import (  # noqa: E402
    manifest_content_hash,
    validate_manifest_document,
)
from _pptx import MAX_MEMBERS, inspect_pptx, require_safe_pptx  # noqa: E402
from check_palette import audit_palette, main as palette_main  # noqa: E402
from plan_export import build_export_plan  # noqa: E402
from synthetic_posters import build_manifest  # noqa: E402

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>
"""
ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>
"""
PRESENTATION = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
  <p:sldSz cx="9144000" cy="7315200"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
"""
PRESENTATION_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>
"""
SLIDE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr/>
    <p:sp>
      <p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
      <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="9144000" cy="914400"/></a:xfrm></p:spPr>
      <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="1800"/><a:t>Synthetic title</a:t></a:r></a:p></p:txBody>
    </p:sp>
  </p:spTree></p:cSld>
</p:sld>
"""


def write_minimal_pptx(
    path: Path,
    *,
    content_types: str = CONTENT_TYPES,
    root_relationships: str = ROOT_RELS,
    extras: dict[str, bytes] | None = None,
) -> None:
    members = {
        "[Content_Types].xml": content_types.encode("utf-8"),
        "_rels/.rels": root_relationships.encode("utf-8"),
        "ppt/presentation.xml": PRESENTATION.encode("utf-8"),
        "ppt/_rels/presentation.xml.rels": PRESENTATION_RELS.encode("utf-8"),
        "ppt/slides/slide1.xml": SLIDE.encode("utf-8"),
    }
    members.update(extras or {})
    with zipfile.ZipFile(
        path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


class ManifestTests(unittest.TestCase):
    def test_core_metadata_string_limits_fail_before_generation(self) -> None:
        for field in ("title", "subject", "authors"):
            with self.subTest(field=field):
                manifest = build_manifest(manifest_content_hash)
                manifest["document"][field] = (
                    ["A" * 127, "B" * 127] if field == "authors" else "A" * 256
                )
                if field == "title":
                    manifest["elements"][0]["text"] = manifest["document"][field]
                manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
                with self.assertRaisesRegex(CliError, "255 characters"):
                    validate_manifest_document(
                        manifest,
                        manifest_path=Path("poster.json"),
                        verify_assets=False,
                    )

    def test_core_metadata_boundary_is_accepted_verbatim(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["document"].update(
            title="A" * 255, subject="B" * 255, authors=["A" * 126, "B" * 127]
        )
        manifest["elements"][0]["text"] = manifest["document"]["title"]
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        report = validate_manifest_document(
            manifest, manifest_path=Path("poster.json"), verify_assets=False
        )
        self.assertTrue(report["valid"])
        self.assertEqual(len("; ".join(manifest["document"]["authors"])), 255)

    def test_asset_final_symlink_is_rejected_even_within_manifest_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.png"
            original.write_bytes(b"local test asset")
            linked = root / "linked.png"
            linked.symlink_to(original.name)
            with self.assertRaisesRegex(CliError, "symlink"):
                resolve_local_asset(root / "poster.json", linked.name, suffixes={".png"})
            self.assertEqual(
                resolve_local_asset(root / "poster.json", original.name, suffixes={".png"}),
                original.resolve(),
            )

    def test_complete_synthetic_manifest_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "poster.json"
            manifest = build_manifest(manifest_content_hash)
            report = validate_manifest_document(
                manifest,
                manifest_path=path,
                verify_assets=False,
                require_approval=True,
            )
        self.assertTrue(report["valid"])
        self.assertEqual(report["approval_status"], "approved")
        self.assertEqual(report["counts"]["elements"], 2)

    def test_placeholder_fails_closed(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["document"]["title"] = "REPLACE_ME_TITLE"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "placeholder"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_unknown_exact_source_id_is_rejected(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["elements"][1]["source_ids"] = ["SRC-MISSING"]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "unknown exact source"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_title_must_be_first_in_reading_order(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["elements"][0]["reading_order"] = 2
        manifest["elements"][1]["reading_order"] = 1
        manifest["elements"].reverse()
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "title element"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_asset_requires_explicit_provenance(self) -> None:
        manifest = build_manifest(
            manifest_content_hash,
            include_image=True,
        )
        del manifest["assets"][0]["provenance"]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "provenance"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_long_description_is_source_bound_and_follows_image(self) -> None:
        manifest = build_manifest(
            manifest_content_hash,
            include_image=True,
        )
        manifest["elements"][2]["height_in"] = 4.5
        manifest["elements"][2]["long_description_element_id"] = "image-description"
        manifest["elements"].append(
            {
                "id": "image-description",
                "type": "text",
                "reading_order": 4,
                "x_in": 4.5,
                "y_in": 6.25,
                "width_in": 5.0,
                "height_in": 1.25,
                "source_ids": ["SRC-ASSET"],
                "author_approved": True,
                "allow_in_bleed": False,
                "role": "caption",
                "text": (
                    "Synthetic long description bound to the local test-image source."
                ),
                "font_size_pt_design": 18.0,
                "font_face": "Arial",
                "bold": False,
                "align": "left",
                "vertical_align": "top",
                "contrast_pair_id": "black_on_white",
                "line_color_id": None,
                "line_width_pt": 0,
                "margin_in": 0.1,
            }
        )
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "poster.json"
            report = validate_manifest_document(
                manifest,
                manifest_path=path,
                verify_assets=False,
            )
            self.assertTrue(report["valid"])
            manifest["elements"][3]["source_ids"] = ["SRC-CONTENT"]
            manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
            with self.assertRaisesRegex(CliError, "every source_id"):
                validate_manifest_document(
                    manifest,
                    manifest_path=path,
                    verify_assets=False,
                )

    def test_content_change_invalidates_author_approval(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["elements"][1]["text"] += " Changed."
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "approval.content_sha256"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_control_characters_are_rejected_before_generation(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["document"]["title"] = "Unsafe\u0001title"
        manifest["elements"][0]["text"] = "Unsafe\u0001title"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "control character"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_remote_asset_path_is_rejected(self) -> None:
        manifest = build_manifest(
            manifest_content_hash,
            include_image=True,
            image_path="https://invalid.example/image.png",
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "relative local path"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_qr_requires_exact_visible_fallback_url(self) -> None:
        manifest = build_manifest(
            manifest_content_hash,
            include_image=True,
        )
        asset = manifest["assets"][0]
        asset["role"] = "qr_code"
        asset["qr_target"] = "https://example.invalid/exact"
        image = manifest["elements"][2]
        image["height_in"] = 5.0
        image["fallback_text_element_id"] = "qr-fallback"
        manifest["elements"].append(
            {
                "id": "qr-fallback",
                "type": "text",
                "reading_order": 4,
                "x_in": 4.5,
                "y_in": 6.5,
                "width_in": 5.0,
                "height_in": 1.0,
                "source_ids": ["SRC-ASSET"],
                "author_approved": True,
                "allow_in_bleed": False,
                "role": "qr_fallback",
                "text": "Destination: https://example.invalid/exact",
                "font_size_pt_design": 18.0,
                "font_face": "Arial",
                "bold": False,
                "align": "left",
                "vertical_align": "middle",
                "contrast_pair_id": "black_on_white",
                "line_color_id": None,
                "line_width_pt": 0,
                "margin_in": 0.1,
            }
        )
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "poster.json"
            report = validate_manifest_document(
                manifest,
                manifest_path=path,
                verify_assets=False,
            )
            self.assertTrue(report["valid"])
            manifest["elements"][3]["text"] = "Destination omitted"
            manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
            with self.assertRaisesRegex(CliError, "exact QR target"):
                validate_manifest_document(
                    manifest,
                    manifest_path=path,
                    verify_assets=False,
                )

    def test_bad_declared_contrast_is_rejected(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["palette"]["colors"]["black"] = "#777777"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "below"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_bad_contrast_can_be_reported_by_palette_audit(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["palette"]["colors"]["black"] = "#777777"
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            validation = validate_manifest_document(
                manifest,
                manifest_path=Path(directory) / "poster.json",
                verify_assets=False,
                enforce_contrast=False,
            )
        self.assertTrue(validation["valid"])
        report = audit_palette(manifest)
        self.assertFalse(report["pass"])

    def test_palette_cli_uses_finding_exit_code(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["palette"]["colors"]["black"] = "#777777"
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "poster.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = palette_main([str(path)])
        self.assertEqual(result, 1)

    def test_template_is_not_valid_content(self) -> None:
        template_path = SKILL_ROOT / "assets" / "poster_manifest_template.json"
        _, template = load_json_file(template_path)
        with self.assertRaises(CliError):
            validate_manifest_document(
                template,
                manifest_path=template_path,
                verify_assets=False,
                require_approval=False,
            )

    def test_uniform_physical_scaling_is_explicit(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["physical_output"]["trim_width_in"] = 20.0
        manifest["physical_output"]["trim_height_in"] = 16.0
        manifest["requirements"]["conference"]["max_width_in"] = 20.0
        manifest["requirements"]["conference"]["max_height_in"] = 16.0
        manifest["requirements"]["printer"]["trim_width_in"] = 20.0
        manifest["requirements"]["printer"]["trim_height_in"] = 16.0
        manifest["requirements"]["printer"]["scaling_allowed"] = True
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            report = validate_manifest_document(
                manifest,
                manifest_path=Path(directory) / "poster.json",
                verify_assets=False,
            )
        self.assertEqual(report["physical_output"]["print_scale"], 2.0)

    def test_nonuniform_physical_scaling_is_rejected(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["physical_output"]["trim_width_in"] = 20.0
        manifest["physical_output"]["trim_height_in"] = 15.0
        manifest["requirements"]["conference"]["max_width_in"] = 20.0
        manifest["requirements"]["conference"]["max_height_in"] = 15.0
        manifest["requirements"]["printer"]["trim_width_in"] = 20.0
        manifest["requirements"]["printer"]["trim_height_in"] = 15.0
        manifest["requirements"]["printer"]["scaling_allowed"] = True
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CliError, "aspect ratios"):
                validate_manifest_document(
                    manifest,
                    manifest_path=Path(directory) / "poster.json",
                    verify_assets=False,
                )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"key": 1, "key": 2}', encoding="utf-8")
            with self.assertRaisesRegex(CliError, "duplicate JSON key"):
                load_json_file(path)


class OutputSafetyTests(unittest.TestCase):
    def test_output_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            atomic_write_bytes(path, b"first")
            with self.assertRaisesRegex(CliError, "overwrite"):
                atomic_write_bytes(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")


class PaletteAndPlanTests(unittest.TestCase):
    def test_scaled_pdf_plan_separates_canvas_from_final_artboard(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        manifest["physical_output"].update(trim_width_in=20.0, trim_height_in=16.0)
        manifest["requirements"]["conference"].update(
            max_width_in=20.0, max_height_in=16.0, required_delivery_format="PDF"
        )
        manifest["requirements"]["printer"].update(
            trim_width_in=20.0, trim_height_in=16.0, scaling_allowed=True
        )
        manifest["approval"]["content_sha256"] = manifest_content_hash(manifest)
        validation = validate_manifest_document(
            manifest, manifest_path=Path("poster.json"), verify_assets=False
        )
        plan = build_export_plan(manifest, validation)
        self.assertEqual(plan["dimensions"]["uniform_print_scale_percent"], 200.0)
        self.assertEqual(plan["pdf_preflight"], {
            "exported_by_tool": False,
            "canvas_width_pt": 720.0,
            "canvas_height_pt": 576.0,
            "final_artboard_width_pt": 1440.0,
            "final_artboard_height_pt": 1152.0,
            "full_size_pdf_requires_scaling": True,
        })

    def test_palette_reports_reference_contrast(self) -> None:
        manifest = build_manifest(manifest_content_hash)
        report = audit_palette(manifest)
        self.assertTrue(report["pass"])
        self.assertEqual(
            report["declared_contrast_pairs"][0]["ratio"],
            21.0,
        )

    def test_cmyk_requirement_blocks_readiness(self) -> None:
        manifest = build_manifest(
            manifest_content_hash,
            printer_color_mode="CMYK",
        )
        with tempfile.TemporaryDirectory() as directory:
            validation = validate_manifest_document(
                manifest,
                manifest_path=Path(directory) / "poster.json",
                verify_assets=False,
            )
        plan = build_export_plan(manifest, validation)
        self.assertFalse(plan["ready_for_manual_export"])
        self.assertEqual(plan["blockers"][0]["code"], "CMYK_CONVERSION_REQUIRED")
        self.assertEqual(plan["font_preflight"]["declared_font_faces"], ["Arial"])
        self.assertFalse(plan["font_preflight"]["fonts_embedded_by_generator"])
        self.assertFalse(
            plan["media_profile"]["audio_video_or_linked_media_allowed"]
        )


class PptxSecurityTests(unittest.TestCase):
    def test_minimal_macro_free_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "safe.pptx"
            write_minimal_pptx(path)
            report = inspect_pptx(path)
            self.assertTrue(report["safe"], report["findings"])
            self.assertEqual(report["accessibility"]["slide_title_count"], 1)
            self.assertEqual(
                report["accessibility"]["text_runs_missing_language"],
                [],
            )
            require_safe_pptx(path)

    def test_pptm_extension_is_rejected_without_opening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.pptm"
            write_minimal_pptx(path)
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertEqual(report["findings"][0]["code"], "FILE_EXTENSION")

    def test_external_relationship_is_rejected(self) -> None:
        relationships = ROOT_RELS.replace(
            "</Relationships>",
            (
                '<Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/hyperlink" Target="https://invalid.example/" '
                'TargetMode="External"/></Relationships>'
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "external.pptx"
            write_minimal_pptx(path, root_relationships=relationships)
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "EXTERNAL_RELATIONSHIP",
            {finding["code"] for finding in report["findings"]},
        )

    def test_invalid_relationship_target_mode_is_rejected(self) -> None:
        relationships = ROOT_RELS.replace(
            "</Relationships>",
            (
                '<Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/image" Target="ppt/media/image1.png" '
                'TargetMode="Unknown"/></Relationships>'
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target-mode.pptx"
            write_minimal_pptx(path, root_relationships=relationships)
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "RELATIONSHIP_TARGET_MODE_INVALID",
            {finding["code"] for finding in report["findings"]},
        )

    def test_remote_linked_image_is_rejected(self) -> None:
        relationships = ROOT_RELS.replace(
            "</Relationships>",
            (
                '<Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/image" Target="https://invalid.example/image.png" '
                'TargetMode="External"/></Relationships>'
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "linked-image.pptx"
            write_minimal_pptx(path, root_relationships=relationships)
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "REMOTE_LINKED_IMAGE",
            {finding["code"] for finding in report["findings"]},
        )

    def test_macro_content_hidden_in_pptx_is_rejected(self) -> None:
        macro_types = CONTENT_TYPES.replace(
            "</Types>",
            (
                '<Override PartName="/ppt/vbaProject.bin" '
                'ContentType="application/vnd.ms-office.vbaProject"/></Types>'
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "macro-disguised.pptx"
            write_minimal_pptx(
                path,
                content_types=macro_types,
            )
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("FORBIDDEN_CONTENT_TYPE", codes)

    def test_ole_markup_without_payload_is_rejected(self) -> None:
        slide = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<p:sld xmlns:p="http://schemas.openxmlformats.org/'
            b'presentationml/2006/main"><p:oleObj/></p:sld>'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ole-markup.pptx"
            write_minimal_pptx(
                path,
                extras={"ppt/slides/slide1.xml": slide},
            )
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "FORBIDDEN_PRESENTATION_MARKUP",
            {finding["code"] for finding in report["findings"]},
        )

    def test_non_utf8_entity_bearing_xml_is_rejected(self) -> None:
        unsafe_slide = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<!DOCTYPE p:sld [<!ENTITY x "unsafe">]>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/'
            'presentationml/2006/main">&x;</p:sld>'
        ).encode("utf-16")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "utf16-entity.pptx"
            write_minimal_pptx(
                path,
                extras={"ppt/slides/slide1.xml": unsafe_slide},
            )
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "XML_PART_INVALID",
            {finding["code"] for finding in report["findings"]},
        )

    def test_traversal_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "traversal.pptx"
            write_minimal_pptx(path, extras={"../escape.txt": b"unsafe"})
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "ZIP_TRAVERSAL",
            {finding["code"] for finding in report["findings"]},
        )

    def test_unknown_package_part_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unknown-part.pptx"
            write_minimal_pptx(path, extras={"ppt/unknown.dat": b"opaque"})
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "UNKNOWN_PACKAGE_PART",
            {finding["code"] for finding in report["findings"]},
        )

    def test_strict_profile_requires_exactly_one_slide(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "two-slides.pptx"
            write_minimal_pptx(
                path,
                extras={"ppt/slides/slide2.xml": SLIDE.encode("utf-8")},
            )
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "SLIDE_COUNT",
            {finding["code"] for finding in report["findings"]},
        )

    def test_image_signature_must_match_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-image.pptx"
            write_minimal_pptx(
                path,
                extras={"ppt/media/image1.png": b"not-a-png"},
            )
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "IMAGE_SIGNATURE",
            {finding["code"] for finding in report["findings"]},
        )

    def test_embedded_binary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "embedded.pptx"
            write_minimal_pptx(
                path,
                extras={"ppt/embeddings/embeddedObject1.bin": b"unsafe"},
            )
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("FORBIDDEN_PACKAGE_PART", codes)
        self.assertIn("FORBIDDEN_BINARY_PART", codes)

    def test_excessive_compression_ratio_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bomb.pptx"
            write_minimal_pptx(
                path,
                extras={"ppt/media/repetitive.txt": b"0" * (1024 * 1024)},
            )
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "ZIP_COMPRESSION_RATIO",
            {finding["code"] for finding in report["findings"]},
        )

    def test_declared_member_count_is_bounded_before_materialization(self) -> None:
        extras = {
            f"ppt/media/empty-{index}.png": b""
            for index in range(MAX_MEMBERS)
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "too-many-members.pptx"
            write_minimal_pptx(path, extras=extras)
            report = inspect_pptx(path)
        self.assertFalse(report["safe"])
        self.assertIn(
            "ZIP_MEMBER_LIMIT",
            {finding["code"] for finding in report["findings"]},
        )


if __name__ == "__main__":
    unittest.main()
