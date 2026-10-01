"""Shared, dependency-light safety helpers for the pydicom skill CLIs."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path, PurePath
from typing import Any

SCHEMA_VERSION = "1.1"
PYDICOM_VERSION = "3.0.2"
NUMPY_VERSION = "2.5.3"
PILLOW_VERSION = "12.3.0"

KIB = 1024
MIB = 1024**2
GIB = 1024**3
DEFAULT_MAX_INPUT_BYTES = 512 * MIB
HARD_MAX_INPUT_BYTES = 16 * GIB
DEFAULT_MAX_OUTPUT_BYTES = 512 * MIB
HARD_MAX_OUTPUT_BYTES = 16 * GIB
DEFAULT_MAX_DECOMPRESSED_BYTES = 256 * MIB
HARD_MAX_DECOMPRESSED_BYTES = 4 * GIB
DEFAULT_MAX_FILES = 1_000
HARD_MAX_FILES = 100_000
DEFAULT_MAX_ELEMENTS = 200_000
HARD_MAX_ELEMENTS = 2_000_000
DEFAULT_MAX_FRAMES = 1_000
HARD_MAX_FRAMES = 1_000_000
MAX_JSON_BYTES = 8 * MIB
MAX_REPORT_BYTES = 32 * MIB
MAX_SEQUENCE_DEPTH = 64

_URI_PREFIXES = (
    "http:",
    "https:",
    "ftp:",
    "file:",
    "s3:",
    "gs:",
    "ssh:",
    "data:",
)
_SIZE_PATTERN = re.compile(r"^\s*(\d+)\s*(B|KIB|MIB|GIB)?\s*$", re.IGNORECASE)
_UID_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)*$")
_SAFE_PLUGIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

TEXT_VRS = frozenset(
    {
        "AE",
        "AS",
        "CS",
        "DA",
        "DT",
        "LO",
        "LT",
        "PN",
        "SH",
        "ST",
        "TM",
        "UC",
        "UI",
        "UR",
        "UT",
    }
)

# These are structural or coding UIDs, not instance identifiers. They must not be
# replaced merely because their VR is UI.
STRUCTURAL_UID_KEYWORDS = frozenset(
    {
        "AffectedSOPClassUID",
        "CodingSchemeUID",
        "ContextGroupExtensionCreatorUID",
        "ContextGroupLocalVersion",
        "ImplementationClassUID",
        "MediaStorageSOPClassUID",
        "PrivateInformationCreatorUID",
        "ReferencedSOPClassUID",
        "RelatedGeneralSOPClassUID",
        "RequestedSOPClassUID",
        "SOPClassUID",
        "TransferSyntaxUID",
    }
)

UID_REMAP_KEYWORDS = frozenset(
    {
        "AcquisitionUID",
        "ConcatenationUID",
        "ContrastBolusAgentNumber",
        "DeviceUID",
        "DimensionOrganizationUID",
        "DoseReferenceUID",
        "FiducialUID",
        "FrameOfReferenceUID",
        "IrradiationEventUID",
        "MediaStorageSOPInstanceUID",
        "ObservationUID",
        "ReferencedDoseReferenceUID",
        "ReferencedFiducialsUID",
        "ReferencedFrameOfReferenceUID",
        "ReferencedGeneralPurposeScheduledProcedureStepTransactionUID",
        "ReferencedObservationUID",
        "ReferencedSOPInstanceUID",
        "SeriesInstanceUID",
        "SOPInstanceUID",
        "SpecimenUID",
        "StorageMediaFileSetUID",
        "StudyInstanceUID",
        "SynchronizationFrameOfReferenceUID",
        "TemplateExtensionCreatorUID",
        "TemplateExtensionOrganizationUID",
        "TrackingUID",
        "TransactionUID",
        "TreatmentPositionGroupUID",
        "TreatmentSessionUID",
        "UID",
    }
)

# A conservative starter profile. It is intentionally not represented as a
# DICOM PS3.15 conformance implementation.
DEFAULT_ACTIONS: dict[str, str] = {
    "AccessionNumber": "empty",
    "AcquisitionContextSequence": "remove",
    "AcquisitionComments": "remove",
    "AdmittingDiagnosesCodeSequence": "remove",
    "AdmittingDiagnosesDescription": "remove",
    "Allergies": "remove",
    "ClinicalTrialProtocolID": "remove",
    "ClinicalTrialProtocolName": "remove",
    "ClinicalTrialSiteID": "remove",
    "ClinicalTrialSiteName": "remove",
    "ClinicalTrialSponsorName": "remove",
    "ClinicalTrialSubjectID": "pseudonym",
    "ClinicalTrialSubjectReadingID": "pseudonym",
    "ContentSequence": "remove",
    "CurrentPatientLocation": "remove",
    "DataSetTrailingPadding": "remove",
    "DeidentificationMethod": "remove",
    "DeidentificationMethodCodeSequence": "remove",
    "DerivationDescription": "remove",
    "DeviceSerialNumber": "remove",
    "DigitalSignaturesSequence": "remove",
    "DocumentTitle": "remove",
    "EncryptedAttributesSequence": "remove",
    "EncapsulatedDocument": "remove",
    "EncapsulatedDocumentLength": "remove",
    "EthnicGroup": "remove",
    "FillerOrderNumberImagingServiceRequest": "empty",
    "GraphicAnnotationSequence": "remove",
    "HL7InstanceIdentifier": "remove",
    "IconImageSequence": "remove",
    "ImageComments": "remove",
    "InstitutionAddress": "remove",
    "InstitutionCodeSequence": "remove",
    "InstitutionName": "remove",
    "InstitutionalDepartmentName": "remove",
    "InsurancePlanIdentification": "remove",
    "IssuerOfAccessionNumberSequence": "remove",
    "IssuerOfAdmissionID": "remove",
    "IssuerOfPatientID": "remove",
    "IssuerOfPatientIDQualifiersSequence": "remove",
    "MACParametersSequence": "remove",
    "MedicalAlerts": "remove",
    "MedicalRecordLocator": "remove",
    "MilitaryRank": "remove",
    "MIMETypeOfEncapsulatedDocument": "remove",
    "NameOfPhysiciansReadingStudy": "remove",
    "Occupation": "remove",
    "OperatorsIdentificationSequence": "remove",
    "OperatorsName": "remove",
    "OriginalAttributesSequence": "remove",
    "OtherPatientIDs": "remove",
    "OtherPatientIDsSequence": "remove",
    "OtherPatientNames": "remove",
    "PatientAddress": "remove",
    "PatientAge": "remove",
    "PatientBirthName": "remove",
    "PatientComments": "remove",
    "PatientID": "pseudonym",
    "PatientInsurancePlanCodeSequence": "remove",
    "PatientMotherBirthName": "remove",
    "PatientName": "pseudonym",
    "PatientReligiousPreference": "remove",
    "PatientSex": "remove",
    "PatientSize": "remove",
    "PatientState": "remove",
    "PatientTelephoneNumbers": "remove",
    "PatientWeight": "remove",
    "PerformedLocation": "remove",
    "PerformedProcedureStepDescription": "remove",
    "PerformedStationAETitle": "remove",
    "PerformedStationGeographicLocationCodeSequence": "remove",
    "PerformedStationName": "remove",
    "PerformingPhysicianIdentificationSequence": "remove",
    "PerformingPhysicianName": "remove",
    "PersonAddress": "remove",
    "PersonIdentificationCodeSequence": "remove",
    "PersonName": "remove",
    "PersonTelephoneNumbers": "remove",
    "PhysiciansOfRecord": "remove",
    "PhysiciansOfRecordIdentificationSequence": "remove",
    "PhysiciansReadingStudyIdentificationSequence": "remove",
    "PlacerOrderNumberImagingServiceRequest": "empty",
    "ProtocolName": "remove",
    "ReasonForImagingServiceRequest": "remove",
    "ReasonForRequestedProcedure": "remove",
    "ReferringPhysicianAddress": "remove",
    "ReferringPhysicianIdentificationSequence": "remove",
    "ReferringPhysicianName": "remove",
    "ReferringPhysicianTelephoneNumbers": "remove",
    "RegionOfResidence": "remove",
    "RequestAttributesSequence": "remove",
    "RequestedProcedureComments": "remove",
    "RequestedProcedureDescription": "remove",
    "RequestedProcedureID": "empty",
    "RequestingPhysician": "remove",
    "RequestingService": "remove",
    "ResponsibleOrganization": "remove",
    "ResponsiblePerson": "remove",
    "ResponsiblePersonRole": "remove",
    "ScheduledPerformingPhysicianIdentificationSequence": "remove",
    "ScheduledPerformingPhysicianName": "remove",
    "ScheduledProcedureStepDescription": "remove",
    "ScheduledProcedureStepID": "empty",
    "SeriesDescription": "remove",
    "ServiceEpisodeDescription": "remove",
    "ServiceEpisodeID": "remove",
    "SmokingStatus": "remove",
    "SpecialNeeds": "remove",
    "SpecimenAccessionNumber": "remove",
    "SpecimenIdentifier": "remove",
    "StationName": "remove",
    "StudyDescription": "remove",
    "StudyID": "empty",
    "TextComments": "remove",
    "TextString": "remove",
    "TextValue": "remove",
    "UnformattedTextValue": "remove",
    "AudioComments": "remove",
    "AudioSampleData": "remove",
}

SENSITIVE_KEYWORDS = frozenset(
    set(DEFAULT_ACTIONS)
    | {
        "PatientBirthDate",
        "PatientBirthTime",
        "PatientIdentityRemoved",
        "StudyDate",
        "StudyTime",
        "SeriesDate",
        "SeriesTime",
        "AcquisitionDate",
        "AcquisitionTime",
        "AcquisitionDateTime",
        "ContentDate",
        "ContentTime",
        "InstanceCreationDate",
        "InstanceCreationTime",
        *UID_REMAP_KEYWORDS,
    }
)

TECHNICAL_KEYWORDS = (
    "SOPClassUID",
    "Modality",
    "Rows",
    "Columns",
    "NumberOfFrames",
    "SamplesPerPixel",
    "PhotometricInterpretation",
    "PlanarConfiguration",
    "BitsAllocated",
    "BitsStored",
    "HighBit",
    "PixelRepresentation",
    "PixelSpacing",
    "RescaleSlope",
    "RescaleIntercept",
    "RescaleType",
    "WindowCenter",
    "WindowWidth",
    "VOILUTFunction",
    "BurnedInAnnotation",
    "RecognizableVisualFeatures",
    "LossyImageCompression",
)


class ToolError(ValueError):
    """Expected validation, dependency, or bounded local-I/O failure."""


def bounded_int(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise ToolError(f"{name} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ToolError(f"{name} must be an integer") from exc
    if not minimum <= result <= maximum:
        raise ToolError(f"{name} must be between {minimum} and {maximum}")
    return result


def parse_size(
    value: str | int,
    *,
    name: str,
    minimum: int = 1,
    maximum: int = HARD_MAX_INPUT_BYTES,
) -> int:
    if isinstance(value, int):
        result = value
    elif isinstance(value, str):
        match = _SIZE_PATTERN.fullmatch(value)
        if not match:
            raise ToolError(f"{name} must be an integer byte count or B/KiB/MiB/GiB")
        result = int(match.group(1))
        unit = (match.group(2) or "B").upper()
        result *= {"B": 1, "KIB": KIB, "MIB": MIB, "GIB": GIB}[unit]
    else:
        raise ToolError(f"{name} must be a byte-size string")
    return bounded_int(result, name=name, minimum=minimum, maximum=maximum)


def require_text(
    value: Any, *, name: str, minimum: int = 1, maximum: int = 1_000
) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ToolError(f"{name} must be a string of length {minimum}..{maximum}")
    if any(ord(character) < 32 for character in value):
        raise ToolError(f"{name} must not contain control characters")
    return value


def safe_plugin_name(value: str) -> str:
    if not _SAFE_PLUGIN.fullmatch(value):
        raise ToolError("decoding plugin name is invalid")
    return value


def _reject_path_text(value: str) -> None:
    stripped = value.strip()
    lowered = stripped.casefold()
    if not stripped or "\x00" in value or stripped.startswith("~"):
        raise ToolError("path must be nonempty, local, and contain no NUL")
    if "://" in lowered or lowered.startswith(_URI_PREFIXES):
        raise ToolError("only local filesystem paths are accepted")
    if ".." in PurePath(stripped).parts:
        raise ToolError("parent traversal is not accepted")


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_components(path: Path) -> None:
    absolute = _absolute(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ToolError("a path component could not be inspected") from exc
        if stat.S_ISLNK(mode):
            raise ToolError("symlink path components are not accepted")


def checked_root(value: str | os.PathLike[str]) -> Path:
    raw = os.fspath(value)
    _reject_path_text(raw)
    candidate = _absolute(Path(raw))
    _reject_symlink_components(candidate)
    try:
        resolved = candidate.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise ToolError("root directory is not accessible") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise ToolError("root must be a directory")
    return resolved


def _within_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ToolError("path escapes the declared root") from exc


def checked_input(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    kind: str = "file",
    max_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> Path:
    raw = os.fspath(value)
    _reject_path_text(raw)
    root_path = checked_root(root)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    candidate = _absolute(candidate)
    _reject_symlink_components(candidate)
    try:
        resolved = candidate.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise ToolError("input path is not accessible") from exc
    _within_root(resolved, root_path)
    if kind == "file" and not stat.S_ISREG(info.st_mode):
        raise ToolError("input must be a regular file")
    if kind == "dir" and not stat.S_ISDIR(info.st_mode):
        raise ToolError("input must be a directory")
    if kind == "any" and not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ToolError("input must be a regular file or directory")
    if stat.S_ISREG(info.st_mode):
        if info.st_nlink != 1:
            raise ToolError("multiply linked input files are not accepted")
        if not 0 <= info.st_size <= max_bytes:
            raise ToolError("input file exceeds the configured byte limit")
    return resolved


def checked_output(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    force: bool = False,
) -> Path:
    raw = os.fspath(value)
    _reject_path_text(raw)
    root_path = checked_root(root)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    candidate = _absolute(candidate)
    _reject_symlink_components(candidate)
    parent = candidate.parent
    try:
        parent = parent.resolve(strict=True)
    except OSError as exc:
        raise ToolError("output parent directory must already exist") from exc
    _within_root(parent, root_path)
    destination = parent / candidate.name
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise ToolError("existing output is not a regular file")
        if not force:
            raise ToolError("refusing to overwrite existing output")
    return destination


def checked_output_directory(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
) -> Path:
    raw = os.fspath(value)
    _reject_path_text(raw)
    root_path = checked_root(root)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    candidate = _absolute(candidate)
    _reject_symlink_components(candidate)
    parent = candidate.parent
    try:
        parent = parent.resolve(strict=True)
    except OSError as exc:
        raise ToolError("output directory parent must already exist") from exc
    _within_root(parent, root_path)
    destination = parent / candidate.name
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise ToolError("existing destination is not a regular directory")
    else:
        try:
            destination.mkdir(mode=0o700)
        except OSError as exc:
            raise ToolError("output directory could not be created") from exc
    return destination.resolve(strict=True)


def paths_overlap(first: Path, second: Path) -> bool:
    first = first.resolve(strict=False)
    second = second.resolve(strict=False)
    return first == second or first in second.parents or second in first.parents


def collect_local_files(
    source: Path,
    *,
    max_files: int,
    max_bytes: int,
    recursive: bool = True,
) -> list[Path]:
    bounded_int(max_files, name="max_files", minimum=1, maximum=HARD_MAX_FILES)
    if source.is_file():
        return [source]
    files: list[Path] = []
    stack = [source]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(
                os.scandir(directory), key=lambda entry: entry.name.casefold()
            )
        except OSError as exc:
            raise ToolError("input directory cannot be scanned") from exc
        for entry in entries:
            try:
                if entry.is_symlink():
                    raise ToolError("symlinks in input directories are rejected")
                if entry.is_dir(follow_symlinks=False):
                    if recursive:
                        stack.append(Path(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                path = Path(entry.path).resolve(strict=True)
                info = path.stat()
                if info.st_nlink != 1:
                    raise ToolError("multiply linked input files are rejected")
                if info.st_size > max_bytes:
                    raise ToolError("an input file exceeds the configured byte limit")
                files.append(path)
                if len(files) > max_files:
                    raise ToolError("input file-count limit exceeded")
            except OSError as exc:
                raise ToolError(
                    "an input directory entry could not be inspected"
                ) from exc
    return sorted(files, key=lambda path: path.as_posix().casefold())


def _reject_json_constant(value: str) -> None:
    raise ToolError(f"non-finite JSON number is not accepted: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ToolError(f"duplicate JSON key is not accepted: {key}")
        result[key] = value
    return result


def load_json(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> Any:
    if path.stat().st_size > max_bytes:
        raise ToolError("JSON input exceeds the configured byte limit")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(
                handle,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
    except ToolError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ToolError("input is not valid bounded UTF-8 JSON") from exc


def json_bytes(document: Any) -> bytes:
    try:
        payload = (
            json.dumps(
                document,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ToolError("report cannot be serialized as strict JSON") from exc
    if len(payload) > MAX_REPORT_BYTES:
        raise ToolError("report exceeds the hard report-size limit")
    return payload


def emit_json(document: Any) -> None:
    sys.stdout.buffer.write(json_bytes(document))


def fail_json(tool: str, exc: Exception) -> int:
    message = (
        str(exc)[:500]
        if isinstance(exc, ToolError)
        else f"operation failed ({type(exc).__name__})"
    )
    emit_json(
        {
            "error": type(exc).__name__,
            "message": message,
            "ok": False,
            "tool": tool,
        }
    )
    return 2


def atomic_write(
    destination: Path,
    payload: bytes,
    *,
    force: bool = False,
    max_bytes: int = MAX_REPORT_BYTES,
) -> None:
    if len(payload) > max_bytes:
        raise ToolError("generated output exceeds the configured byte limit")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        if destination.exists() and not force:
            raise ToolError("refusing to overwrite existing output")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_generated_file(
    destination: Path,
    *,
    writer: Callable[[Path], None],
    validator: Callable[[Path], None] | None = None,
    force: bool = False,
    max_bytes: int = HARD_MAX_OUTPUT_BYTES,
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=destination.suffix or ".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        os.chmod(temporary, 0o600)
        writer(temporary)
        info = temporary.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise ToolError("generated output exceeds the configured byte limit")
        if validator is not None:
            validator(temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        if destination.exists() and not force:
            raise ToolError("refusing to overwrite existing output")
        os.replace(temporary, destination)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError("generated output could not be safely written") from exc
    finally:
        temporary.unlink(missing_ok=True)


def require_pydicom() -> Any:
    try:
        import pydicom
    except ImportError as exc:
        raise ToolError(
            f"pydicom is required; install with: uv pip install pydicom=={PYDICOM_VERSION}"
        ) from exc
    if pydicom.__version__ != PYDICOM_VERSION:
        raise ToolError(
            f"this skill is verified with pydicom=={PYDICOM_VERSION}; "
            f"found {pydicom.__version__}"
        )
    return pydicom


def require_pixel_stack() -> tuple[Any, Any, Any]:
    pydicom = require_pydicom()
    try:
        import numpy
        from PIL import Image
    except ImportError as exc:
        raise ToolError(
            "pixel conversion requires pinned NumPy and Pillow; install with: "
            f"uv pip install pydicom=={PYDICOM_VERSION} "
            f"numpy=={NUMPY_VERSION} Pillow=={PILLOW_VERSION}"
        ) from exc
    return pydicom, numpy, Image


def safe_dcmread(
    path: Path,
    *,
    stop_before_pixels: bool,
    force: bool = False,
    defer_size: str | int | None = None,
    specific_tags: Iterable[str | int] | None = None,
) -> Any:
    pydicom = require_pydicom()
    try:
        return pydicom.dcmread(
            path,
            defer_size=defer_size,
            stop_before_pixels=stop_before_pixels,
            force=force,
            specific_tags=list(specific_tags) if specific_tags is not None else None,
        )
    except Exception as exc:
        raise ToolError("DICOM input could not be parsed") from exc


def element_tag(element: Any) -> str:
    return f"({int(element.tag.group):04X},{int(element.tag.element):04X})"


def valid_uid(value: Any) -> bool:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        return False
    if not _UID_PATTERN.fullmatch(value):
        return False
    return all(
        component == "0" or not component.startswith("0")
        for component in value.split(".")
    )


def derive_uid(original: str, *, key: bytes, scope: str) -> str:
    if not valid_uid(original):
        raise ToolError("an instance UID selected for remapping is invalid")
    digest = hmac.new(
        key,
        b"pydicom-skill-uid-v1\0"
        + scope.encode("utf-8")
        + b"\0"
        + original.encode("ascii"),
        hashlib.sha256,
    ).digest()[:16]
    number = int.from_bytes(digest, "big") or 1
    result = f"2.25.{number}"
    if not valid_uid(result):
        raise ToolError("derived UID is invalid")
    return result


def derive_token(value: str, *, key: bytes, scope: str, length: int = 24) -> str:
    digest = hmac.new(
        key,
        b"pydicom-skill-token-v1\0"
        + scope.encode("utf-8")
        + b"\0"
        + value.encode("utf-8", errors="surrogatepass"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:length].upper()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def frame_count(dataset: Any) -> tuple[int, list[str]]:
    warnings: list[str] = []
    raw = dataset.get("NumberOfFrames", 1)
    try:
        count = int(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ToolError("NumberOfFrames is not an integer") from exc
    if count == 0:
        warnings.append("NumberOfFrames is zero; pydicom treats it as one")
        count = 1
    if count < 1:
        raise ToolError("NumberOfFrames must be positive")
    return count, warnings


def pixel_plan(
    dataset: Any,
    *,
    max_frames: int = HARD_MAX_FRAMES,
    max_decompressed_bytes: int = HARD_MAX_DECOMPRESSED_BYTES,
) -> dict[str, Any]:
    rows = bounded_int(dataset.get("Rows"), name="Rows", minimum=1, maximum=1_000_000)
    columns = bounded_int(
        dataset.get("Columns"), name="Columns", minimum=1, maximum=1_000_000
    )
    samples = bounded_int(
        dataset.get("SamplesPerPixel", 1),
        name="SamplesPerPixel",
        minimum=1,
        maximum=256,
    )
    frames, warnings = frame_count(dataset)
    bounded_int(frames, name="NumberOfFrames", minimum=1, maximum=max_frames)
    if "DoubleFloatPixelData" in dataset:
        bits_allocated = 64
        pixel_element = "DoubleFloatPixelData"
    elif "FloatPixelData" in dataset:
        bits_allocated = 32
        pixel_element = "FloatPixelData"
    else:
        bits_allocated = bounded_int(
            dataset.get("BitsAllocated"),
            name="BitsAllocated",
            minimum=1,
            maximum=64,
        )
        pixel_element = "PixelData"
    pixels_per_frame = rows * columns * samples
    packed_bytes_per_frame = (pixels_per_frame * bits_allocated + 7) // 8
    decoded_item_bytes = (
        1
        if bits_allocated <= 8
        else 2
        if bits_allocated <= 16
        else 4
        if bits_allocated <= 32
        else 8
    )
    bytes_per_frame = pixels_per_frame * decoded_item_bytes
    total_bytes = bytes_per_frame * frames
    if total_bytes > max_decompressed_bytes:
        raise ToolError(
            "estimated decompressed pixel data exceeds the configured limit"
        )
    if frames > 1:
        shape = (
            [frames, rows, columns]
            if samples == 1
            else [frames, rows, columns, samples]
        )
    else:
        shape = [rows, columns] if samples == 1 else [rows, columns, samples]
    return {
        "bits_allocated": bits_allocated,
        "bytes_per_frame": bytes_per_frame,
        "columns": columns,
        "estimated_decompressed_bytes": total_bytes,
        "frames": frames,
        "native_packed_bytes_per_frame": packed_bytes_per_frame,
        "pixel_element": pixel_element,
        "rows": rows,
        "samples_per_pixel": samples,
        "shape": shape,
        "warnings": warnings,
    }


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def validate_profile(document: Any) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise ToolError("action profile must be a JSON object")
    allowed = {"name", "version", "actions", "private_policy", "date_policy"}
    unknown = sorted(set(document) - allowed)
    if unknown:
        raise ToolError(f"action profile has unsupported keys: {', '.join(unknown)}")
    name = require_text(document.get("name"), name="profile name", maximum=128)
    version = require_text(document.get("version"), name="profile version", maximum=32)
    raw_actions = document.get("actions", {})
    if not isinstance(raw_actions, Mapping) or len(raw_actions) > 2_000:
        raise ToolError("profile actions must be an object with at most 2000 entries")
    actions = dict(DEFAULT_ACTIONS)
    valid_actions = {"empty", "keep", "pseudonym", "remove", "uid"}
    for raw_key, raw_action in raw_actions.items():
        key = require_text(raw_key, name="action key", maximum=128)
        action = require_text(raw_action, name=f"action for {key}", maximum=16)
        if action not in valid_actions:
            raise ToolError(f"unsupported action for {key}")
        actions[key] = action
    private_policy = document.get("private_policy", "remove")
    if private_policy not in {"keep", "reject", "remove"}:
        raise ToolError("private_policy must be keep, reject, or remove")
    date_policy = document.get("date_policy", "empty")
    if date_policy not in {"empty", "keep", "shift"}:
        raise ToolError("date_policy must be empty, keep, or shift")
    return {
        "actions": actions,
        "date_policy": date_policy,
        "name": name,
        "private_policy": private_policy,
        "version": version,
    }


def starter_profile() -> dict[str, Any]:
    return {
        "actions": dict(DEFAULT_ACTIONS),
        "date_policy": "empty",
        "name": "bounded-starter",
        "private_policy": "remove",
        "version": "1.1",
    }
