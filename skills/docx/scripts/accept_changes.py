"""Accept tracked changes through LibreOffice; publish only verified output.

Requires LibreOffice (soffice), defusedxml, and a writable temporary directory.
LibreOffice can change layout on import/export; render the result before delivery.
"""

import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException

from office.soffice import run_soffice

WORD_NAMESPACES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}
REVISION_ELEMENTS = {
    "ins", "del", "moveFrom", "moveTo", "moveFromRangeStart", "moveFromRangeEnd",
    "moveToRangeStart", "moveToRangeEnd", "cellIns", "cellDel", "cellMerge",
    "numberingChange", "pPrChange", "rPrChange", "sectPrChange", "tblPrChange",
    "tblGridChange", "tblPrExChange", "trPrChange", "tcPrChange", "customXmlInsRangeStart",
    "customXmlInsRangeEnd", "customXmlDelRangeStart", "customXmlDelRangeEnd",
    "customXmlMoveFromRangeStart", "customXmlMoveFromRangeEnd",
    "customXmlMoveToRangeStart", "customXmlMoveToRangeEnd",
}

ACCEPT_CHANGES_MACRO = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
    Sub AcceptAllTrackedChanges()
        Dim document As Object
        Dim dispatcher As Object
        Dim loadArgs(1) As New com.sun.star.beans.PropertyValue
        loadArgs(0).Name = "Hidden"
        loadArgs(0).Value = True
        loadArgs(1).Name = "MacroExecutionMode"
        loadArgs(1).Value = 0
        document = StarDesktop.loadComponentFromURL("__DOCUMENT_URL__", "_blank", 0, loadArgs())
        dispatcher = createUnoService("com.sun.star.frame.DispatchHelper")
        dispatcher.executeDispatch(document.CurrentController.Frame, ".uno:AcceptAllTrackedChanges", "", 0, Array())
        document.store()
        document.close(True)
        StarDesktop.terminate()
    End Sub
</script:module>"""


def remaining_revisions(path: Path) -> list[str]:
    """Check every Word XML part, including header/footer/note stories."""
    found = []
    with zipfile.ZipFile(path) as archive:
        if "word/document.xml" not in archive.namelist():
            raise ValueError("DOCX has no word/document.xml")
        for name in archive.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            root = ET.fromstring(archive.read(name))
            for elem in root.iter():
                if not isinstance(elem.tag, str) or not elem.tag.startswith("{"):
                    continue
                namespace, local = elem.tag[1:].split("}", 1)
                if namespace in WORD_NAMESPACES and local in REVISION_ELEMENTS:
                    found.append(f"{name}: {local}")
    return found


def _setup_libreoffice_macro(profile: Path, timeout: float, document_url: str) -> None:
    result = run_soffice(
        ["--headless", f"-env:UserInstallation={profile.as_uri()}", "--terminate_after_init"],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"LibreOffice profile initialization failed: {result.stderr.strip()}")
    macro_dir = profile / "user" / "basic" / "Standard"
    if not macro_dir.is_dir():
        raise RuntimeError("LibreOffice did not create its Basic macro library")
    macro = ACCEPT_CHANGES_MACRO.replace("__DOCUMENT_URL__", xml_escape(document_url))
    (macro_dir / "Module1.xba").write_text(macro, encoding="utf-8")


def accept_changes(input_file: str, output_file: str, timeout: float = 60) -> tuple[None, str]:
    input_path = Path(input_file)
    output_path = Path(output_file).absolute()
    if not input_path.is_file():
        return None, f"Error: Input file not found: {input_file}"
    if input_path.suffix.lower() != ".docx" or output_path.suffix.lower() != ".docx":
        return None, "Error: Input and output must both be .docx files"
    if timeout <= 0:
        return None, "Error: Timeout must be positive"
    try:
        revisions = remaining_revisions(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Staging beside the destination makes os.replace atomic on its filesystem.
        with tempfile.TemporaryDirectory(prefix="accept-changes-", dir=output_path.parent) as work:
            staging = Path(work) / "document.docx"
            shutil.copy2(input_path, staging)
            if revisions:
                with tempfile.TemporaryDirectory(prefix="accept-changes-profile-", ignore_cleanup_errors=True) as profile:
                    profile_path = Path(profile).resolve()
                    _setup_libreoffice_macro(profile_path, timeout, staging.as_uri())
                    result = run_soffice(
                        ["--headless", "--norestore", f"-env:UserInstallation={profile_path.as_uri()}",
                         "vnd.sun.star.script:Standard.Module1.AcceptAllTrackedChanges?language=Basic&location=application"],
                        capture_output=True, text=True, timeout=timeout, check=False,
                    )
                    if result.returncode:
                        raise RuntimeError(f"LibreOffice failed: {result.stderr.strip()}")
                remaining = remaining_revisions(staging)
                if remaining:
                    raise RuntimeError("Tracked changes remain after LibreOffice save: " + "; ".join(remaining[:5]))
            os.replace(staging, output_path)
    except subprocess.TimeoutExpired:
        return None, "Error: LibreOffice timed out; output was not replaced"
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, ET.ParseError, DefusedXmlException) as exc:
        return None, f"Error: {exc}"
    return None, f"Successfully accepted all tracked changes: {input_file} -> {output_file}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Accept all tracked changes in a DOCX file")
    parser.add_argument("input_file", help="Input DOCX file with tracked changes")
    parser.add_argument("output_file", help="Output DOCX file (clean, no tracked changes)")
    parser.add_argument("--timeout", type=float, default=60, help="Seconds per LibreOffice operation (default: 60)")
    args = parser.parse_args()
    _, message = accept_changes(args.input_file, args.output_file, args.timeout)
    print(message)
    if message.startswith("Error:"):
        raise SystemExit(1)
