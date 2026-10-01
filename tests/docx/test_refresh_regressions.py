"""Behavioral regressions for comment, revision, and OPC refresh fixes."""
from pathlib import Path
import subprocess
import sys
import zipfile
from unittest.mock import patch

import pytest

pytest.importorskip("defusedxml")
pytest.importorskip("lxml")
import defusedxml.ElementTree as ET

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "docx"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "scripts" / "office"))
import accept_changes
import comment
import merge_runs
from validators.docx import DOCXSchemaValidator
from validators.base import BaseSchemaValidator

W = comment.NS["w"]
P = comment.PACKAGE_NS
C = comment.CONTENT_TYPE_NS


def package(tmp_path, body="<w:p/>"):
    (tmp_path / "word").mkdir(parents=True, exist_ok=True)
    (tmp_path / "word/document.xml").write_text(f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
    (tmp_path / "[Content_Types].xml").write_text(f'<Types xmlns="{C}"/>')
    return tmp_path


def archive(path, body="<w:p/>", other=None):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
        for name, xml in (other or {}).items():
            z.writestr(name, xml)


def test_comment_creates_missing_relationship_part_and_escapes_text(tmp_path):
    package(tmp_path)
    cid, _, _ = comment.add_comment(tmp_path, 'A & B < C', author='A "B"')
    assert cid == 0
    root = ET.parse(tmp_path / "word/comments.xml")
    assert root.find(f".//{{{W}}}t").text == "A & B < C"
    rels = ET.parse(tmp_path / "word/_rels/document.xml.rels")
    assert len(rels.findall(f"{{{P}}}Relationship")) == 4
    comment.add_comment(tmp_path, "Second")
    assert len(ET.parse(tmp_path / "word/_rels/document.xml.rels").findall(f"{{{P}}}Relationship")) == 4


def test_comment_rejects_duplicate_id_without_mutating_parts(tmp_path):
    package(tmp_path)
    comment.add_comment(tmp_path, "First", comment_id=3)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*.xml")}
    with pytest.raises(ValueError, match="already in use"):
        comment.add_comment(tmp_path, "Second", comment_id=3)
    assert all(p.read_bytes() == content for p, content in before.items())


def test_reply_uses_last_paragraph_and_noncanonical_prefix(tmp_path):
    package(tmp_path)
    (tmp_path / "word/comments.xml").write_text(
        f'<x:comments xmlns:x="{W}" xmlns:y="{comment.NS["w14"]}">'
        '<x:comment x:id="7"><x:p y:paraId="00000011"/><x:p y:paraId="00000022"/></x:comment></x:comments>')
    cid, _, _ = comment.add_comment(tmp_path, "Reply", parent_id=7)
    assert cid == 8
    root = ET.parse(tmp_path / "word/commentsExtended.xml")
    assert root.find(f'.//{{{comment.NS["w15"]}}}commentEx').get(f'{{{comment.NS["w15"]}}}paraIdParent') == "00000022"
    assert len(ET.parse(tmp_path / "word/comments.xml").findall(f"{{{W}}}comment")) == 2


def test_comment_nonstandard_part_path_fails_before_writing(tmp_path):
    package(tmp_path)
    rels = tmp_path / "word/_rels/document.xml.rels"
    rels.parent.mkdir()
    rels.write_text(f'<Relationships xmlns="{P}"><Relationship Id="rId1" Type="{comment._COMMENT_RELS[0][0]}" Target="other-comments.xml"/></Relationships>')
    with pytest.raises(ValueError, match="Nonstandard"):
        comment.add_comment(tmp_path, "Do not orphan existing comments")
    assert not (tmp_path / "word/comments.xml").exists()


def test_merge_preserves_foreign_runs_and_distinct_attributes(tmp_path):
    root = package(tmp_path, '<w:p xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        '<m:r><m:t>x</m:t></m:r><m:r><m:t>y</m:t></m:r>'
        '<w:r xml:space="preserve"><w:t>a</w:t></w:r><w:r><w:t>b</w:t></w:r></w:p>')
    count, _ = merge_runs.merge_runs(str(root))
    assert count == 0
    assert len(ET.parse(root / "word/document.xml").findall(f".//{{{W}}}r")) == 2


def test_accept_timeout_preserves_existing_output(tmp_path):
    source, output = tmp_path / "source.docx", tmp_path / "out.docx"
    archive(source, '<w:p><w:ins w:id="1"><w:r><w:t>new</w:t></w:r></w:ins></w:p>')
    output.write_bytes(b"original output")
    with patch.object(accept_changes, "_setup_libreoffice_macro"), patch.object(accept_changes, "run_soffice", side_effect=subprocess.TimeoutExpired("soffice", 1)):
        _, message = accept_changes.accept_changes(str(source), str(output), 1)
    assert message.startswith("Error:")
    assert output.read_bytes() == b"original output"


def test_accept_clean_exit_with_remaining_changes_is_failure(tmp_path):
    source, output = tmp_path / "source.docx", tmp_path / "out.docx"
    archive(source, '<w:p><w:ins w:id="1"><w:r><w:t>new</w:t></w:r></w:ins></w:p>')
    with patch.object(accept_changes, "_setup_libreoffice_macro"), patch.object(accept_changes, "run_soffice", return_value=subprocess.CompletedProcess([], 0, "", "")):
        _, message = accept_changes.accept_changes(str(source), str(output))
    assert "Tracked changes remain" in message
    assert not output.exists()


def test_accept_checks_header_revisions_and_clean_copy_is_byte_preserving(tmp_path):
    source, output = tmp_path / "source.docx", tmp_path / "out.docx"
    archive(source, other={"word/header1.xml": f'<w:hdr xmlns:w="{W}"><w:p><w:rPrChange w:id="1"/></w:p></w:hdr>'})
    assert accept_changes.remaining_revisions(source) == ["word/header1.xml: rPrChange"]
    archive(source)
    with patch.object(accept_changes, "run_soffice", side_effect=AssertionError("No conversion needed")):
        _, message = accept_changes.accept_changes(str(source), str(output))
    assert message.startswith("Successfully")
    assert source.read_bytes() == output.read_bytes()


@pytest.mark.parametrize("anchor", ["commentRangeStart", "commentRangeEnd"])
def test_valid_single_point_comment_anchor(tmp_path, anchor):
    package(tmp_path, f'<w:p><w:{anchor} w:id="0"/><w:r><w:commentReference w:id="0"/></w:r></w:p>')
    (tmp_path / "word/comments.xml").write_text(f'<w:comments xmlns:w="{W}"><w:comment w:id="0"/></w:comments>')
    assert DOCXSchemaValidator(tmp_path).validate_comment_markers()


def test_comment_anchor_without_reference_is_rejected(tmp_path):
    package(tmp_path, '<w:p><w:commentRangeStart w:id="0"/><w:commentRangeEnd w:id="0"/></w:p>')
    (tmp_path / "word/comments.xml").write_text(f'<w:comments xmlns:w="{W}"><w:comment w:id="0"/></w:comments>')
    assert not DOCXSchemaValidator(tmp_path).validate_comment_markers()


def test_comment_reference_without_comment_part_is_rejected(tmp_path):
    package(tmp_path, '<w:p><w:r><w:commentReference w:id="0"/></w:r></w:p>')
    assert not DOCXSchemaValidator(tmp_path).validate_comment_markers()


def test_relationship_targets_decode_and_stay_inside_package(tmp_path):
    (tmp_path / "_rels").mkdir()
    rels = tmp_path / "_rels/.rels"
    (tmp_path / "part space.xml").write_text("<part/>")
    rels.write_text(f'<Relationships xmlns="{P}"><Relationship Id="rId1" Type="urn:test" Target="part%20space.xml"/></Relationships>')
    validator = BaseSchemaValidator(tmp_path)
    assert validator.validate_file_references()
    rels.write_text(f'<Relationships xmlns="{P}"><Relationship Id="rId1" Type="urn:test" Target="%2e%2e/outside.xml"/></Relationships>')
    assert not validator.validate_file_references()


def test_whitespace_repair_respects_element_namespaces(tmp_path):
    drawing = "http://schemas.openxmlformats.org/drawingml/2006/main"
    math = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    sheet = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    xml_space = "{http://www.w3.org/XML/1998/namespace}space"
    file = tmp_path / "text.xml"
    file.write_text(
        f'<root xmlns:w="{W}" xmlns:m="{math}" xmlns:s="{sheet}" '
        f'xmlns:a="{drawing}" xmlns:f="urn:foreign">'
        '<w:t> word </w:t><w:delText> deleted </w:delText>'
        '<w:instrText> field </w:instrText><w:delInstrText> deleted field </w:delInstrText>'
        '<m:t> math </m:t><s:t> sheet </s:t>'
        '<a:t> drawing </a:t><f:t> foreign </f:t><t> unqualified </t>'
        f'<t xmlns="{W}"> default namespace </t></root>'
    )
    validator = BaseSchemaValidator(tmp_path)
    assert validator.repair_whitespace_preservation() == 7
    root = ET.parse(file).getroot()
    assert all(node.get(xml_space) == "preserve" for node in list(root)[:6])
    assert all(node.get(xml_space) is None for node in list(root)[6:9])
    assert list(root)[9].get(xml_space) == "preserve"
    assert validator.repair_whitespace_preservation() == 0
