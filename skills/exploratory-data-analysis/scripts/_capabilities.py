#!/usr/bin/env python3
"""Closed capability registry and lightweight format checks for EDA tools."""

from __future__ import annotations

import itertools
import zipfile
from pathlib import Path
from typing import Any

from _common import (
    MAX_COMPRESSION_RATIO,
    MAX_NPZ_MEMBERS,
    MAX_NPZ_UNCOMPRESSED_BYTES,
    CliError,
)


AUTOMATED_FORMATS: dict[str, dict[str, Any]] = {
    ".csv": {
        "format": "CSV",
        "tier": "automated_core",
        "depth": "bounded schema, aggregate profile, missingness, and sensitivity audit",
        "dependency": "Python standard library",
        "reference": "references/general_scientific_formats.md",
    },
    ".tsv": {
        "format": "TSV",
        "tier": "automated_core",
        "depth": "bounded schema, aggregate profile, missingness, and sensitivity audit",
        "dependency": "Python standard library",
        "reference": "references/general_scientific_formats.md",
    },
    ".json": {
        "format": "JSON",
        "tier": "automated_core",
        "depth": "bounded strict parse and structural aggregate profile",
        "dependency": "Python standard library",
        "reference": "references/general_scientific_formats.md",
    },
    ".npy": {
        "format": "NumPy NPY",
        "tier": "automated_optional",
        "depth": "header, shape, dtype, and bounded numeric sample",
        "dependency": "numpy==2.5.3",
        "reference": "references/general_scientific_formats.md",
    },
    ".npz": {
        "format": "NumPy NPZ",
        "tier": "automated_optional",
        "depth": "ZIP bomb preflight plus per-array bounded inspection",
        "dependency": "numpy==2.5.3",
        "reference": "references/general_scientific_formats.md",
    },
    ".h5": {
        "format": "HDF5",
        "tier": "automated_optional",
        "depth": "bounded hierarchy and dataset metadata; no dataset values or external links",
        "dependency": "h5py==3.16.0",
        "reference": "references/general_scientific_formats.md",
    },
    ".hdf5": {
        "format": "HDF5",
        "tier": "automated_optional",
        "depth": "bounded hierarchy and dataset metadata; no dataset values or external links",
        "dependency": "h5py==3.16.0",
        "reference": "references/general_scientific_formats.md",
    },
    ".fasta": {
        "format": "FASTA",
        "tier": "automated_optional",
        "depth": "bounded record sample with length, alphabet, and GC aggregates",
        "dependency": "biopython==1.88",
        "reference": "references/bioinformatics_genomics_formats.md",
    },
    ".fa": {
        "format": "FASTA",
        "tier": "automated_optional",
        "depth": "bounded record sample with length, alphabet, and GC aggregates",
        "dependency": "biopython==1.88",
        "reference": "references/bioinformatics_genomics_formats.md",
    },
    ".fna": {
        "format": "FASTA",
        "tier": "automated_optional",
        "depth": "bounded record sample with length, alphabet, and GC aggregates",
        "dependency": "biopython==1.88",
        "reference": "references/bioinformatics_genomics_formats.md",
    },
    ".fastq": {
        "format": "FASTQ",
        "tier": "automated_optional",
        "depth": "bounded record sample with length, GC, and Phred+33 aggregates",
        "dependency": "biopython==1.88",
        "reference": "references/bioinformatics_genomics_formats.md",
    },
    ".fq": {
        "format": "FASTQ",
        "tier": "automated_optional",
        "depth": "bounded record sample with length, GC, and Phred+33 aggregates",
        "dependency": "biopython==1.88",
        "reference": "references/bioinformatics_genomics_formats.md",
    },
    ".png": {
        "format": "PNG",
        "tier": "automated_optional",
        "depth": "container metadata only; pixels are not decoded",
        "dependency": "pillow==12.3.0",
        "reference": "references/microscopy_imaging_formats.md",
    },
    ".jpg": {
        "format": "JPEG",
        "tier": "automated_optional",
        "depth": "container metadata only; pixels are not decoded",
        "dependency": "pillow==12.3.0",
        "reference": "references/microscopy_imaging_formats.md",
    },
    ".jpeg": {
        "format": "JPEG",
        "tier": "automated_optional",
        "depth": "container metadata only; pixels are not decoded",
        "dependency": "pillow==12.3.0",
        "reference": "references/microscopy_imaging_formats.md",
    },
    ".tif": {
        "format": "TIFF",
        "tier": "automated_optional",
        "depth": "bounded TIFF series/page metadata only; pixels are not decoded",
        "dependency": "tifffile==2026.9.20",
        "reference": "references/microscopy_imaging_formats.md",
    },
    ".tiff": {
        "format": "TIFF",
        "tier": "automated_optional",
        "depth": "bounded TIFF series/page metadata only; pixels are not decoded",
        "dependency": "tifffile==2026.9.20",
        "reference": "references/microscopy_imaging_formats.md",
    },
    ".ome.tif": {
        "format": "OME-TIFF",
        "tier": "automated_optional",
        "depth": "bounded TIFF/OME structural metadata only; OME-XML and pixels are not emitted",
        "dependency": "tifffile==2026.9.20",
        "reference": "references/microscopy_imaging_formats.md",
    },
    ".ome.tiff": {
        "format": "OME-TIFF",
        "tier": "automated_optional",
        "depth": "bounded TIFF/OME structural metadata only; OME-XML and pixels are not emitted",
        "dependency": "tifffile==2026.9.20",
        "reference": "references/microscopy_imaging_formats.md",
    },
}


def _reference(
    format_name: str,
    reference: str,
    note: str,
) -> dict[str, str]:
    return {
        "format": format_name,
        "tier": "reference_only",
        "depth": note,
        "dependency": "manual or separately validated domain tooling",
        "reference": reference,
    }


REFERENCE_ONLY_FORMATS: dict[str, dict[str, str]] = {
    # General tabular/array containers
    ".parquet": _reference(
        "Apache Parquet",
        "references/general_scientific_formats.md",
        "documented pandas/Polars/Arrow workflow; no bundled parser",
    ),
    ".feather": _reference(
        "Apache Feather",
        "references/general_scientific_formats.md",
        "documented columnar workflow; no bundled parser",
    ),
    ".xlsx": _reference(
        "Excel OOXML",
        "references/general_scientific_formats.md",
        "manual workbook review required, including formulas and hidden content",
    ),
    ".xls": _reference(
        "Legacy Excel",
        "references/general_scientific_formats.md",
        "manual workbook review required; macros are never executed",
    ),
    ".zarr": _reference(
        "Zarr",
        "references/general_scientific_formats.md",
        "directory/store format is not accepted by bundled file inspectors",
    ),
    ".nc": _reference(
        "NetCDF",
        "references/general_scientific_formats.md",
        "documented xarray/netCDF workflow; no bundled parser",
    ),
    ".mat": _reference(
        "MATLAB MAT",
        "references/general_scientific_formats.md",
        "manual version-aware workflow; no bundled parser",
    ),
    ".fits": _reference(
        "FITS",
        "references/general_scientific_formats.md",
        "documented Astropy workflow; no bundled parser",
    ),
    # Bioinformatics/genomics
    ".sam": _reference(
        "SAM",
        "references/bioinformatics_genomics_formats.md",
        "use a pinned SAM/BAM validator; no bundled parser",
    ),
    ".bam": _reference(
        "BAM",
        "references/bioinformatics_genomics_formats.md",
        "use a pinned SAM/BAM validator; no bundled parser",
    ),
    ".cram": _reference(
        "CRAM",
        "references/bioinformatics_genomics_formats.md",
        "reference-aware validation required; no bundled parser",
    ),
    ".vcf": _reference(
        "VCF",
        "references/bioinformatics_genomics_formats.md",
        "use a pinned VCF validator; no bundled parser",
    ),
    ".bcf": _reference(
        "BCF",
        "references/bioinformatics_genomics_formats.md",
        "use a pinned VCF/BCF validator; no bundled parser",
    ),
    ".bed": _reference(
        "BED",
        "references/bioinformatics_genomics_formats.md",
        "assembly-aware interval validation required; no bundled parser",
    ),
    ".gff": _reference(
        "GFF",
        "references/bioinformatics_genomics_formats.md",
        "version-aware annotation validation required; no bundled parser",
    ),
    ".gff3": _reference(
        "GFF3",
        "references/bioinformatics_genomics_formats.md",
        "version-aware annotation validation required; no bundled parser",
    ),
    ".gtf": _reference(
        "GTF",
        "references/bioinformatics_genomics_formats.md",
        "annotation-specific validation required; no bundled parser",
    ),
    ".h5ad": _reference(
        "AnnData H5AD",
        "references/bioinformatics_genomics_formats.md",
        "generic HDF5 metadata is not AnnData semantic validation",
    ),
    ".loom": _reference(
        "Loom",
        "references/bioinformatics_genomics_formats.md",
        "generic HDF5 metadata is not Loom semantic validation",
    ),
    ".mtx": _reference(
        "Matrix Market",
        "references/bioinformatics_genomics_formats.md",
        "matrix and sidecar alignment require domain tooling",
    ),
    # Chemistry/molecular
    ".pdb": _reference(
        "Legacy PDB",
        "references/chemistry_molecular_formats.md",
        "wwPDB-aware structural validation required; no bundled parser",
    ),
    ".cif": _reference(
        "CIF or PDBx/mmCIF",
        "references/chemistry_molecular_formats.md",
        "extension is ambiguous; dictionary-aware validation required",
    ),
    ".mmcif": _reference(
        "PDBx/mmCIF",
        "references/chemistry_molecular_formats.md",
        "wwPDB dictionary-aware validation required; no bundled parser",
    ),
    ".mol": _reference(
        "MDL Molfile",
        "references/chemistry_molecular_formats.md",
        "chemistry-aware validation required; no bundled parser",
    ),
    ".sdf": _reference(
        "Structure Data File",
        "references/chemistry_molecular_formats.md",
        "chemistry-aware validation required; no bundled parser",
    ),
    ".smi": _reference(
        "SMILES table",
        "references/chemistry_molecular_formats.md",
        "line notation requires chemistry-aware parsing; no bundled parser",
    ),
    ".xyz": _reference(
        "XYZ coordinates",
        "references/chemistry_molecular_formats.md",
        "units and record boundaries require explicit confirmation",
    ),
    ".dcd": _reference(
        "DCD trajectory",
        "references/chemistry_molecular_formats.md",
        "topology-dependent trajectory tooling required",
    ),
    ".xtc": _reference(
        "XTC trajectory",
        "references/chemistry_molecular_formats.md",
        "topology-dependent trajectory tooling required",
    ),
    ".trr": _reference(
        "TRR trajectory",
        "references/chemistry_molecular_formats.md",
        "topology-dependent trajectory tooling required",
    ),
    # Imaging beyond the bounded metadata inspectors
    ".nd2": _reference(
        "Nikon ND2",
        "references/microscopy_imaging_formats.md",
        "vendor-aware reader required; no bundled parser",
    ),
    ".czi": _reference(
        "Zeiss CZI",
        "references/microscopy_imaging_formats.md",
        "vendor-aware reader required; no bundled parser",
    ),
    ".lif": _reference(
        "Leica LIF",
        "references/microscopy_imaging_formats.md",
        "vendor-aware reader required; no bundled parser",
    ),
    ".dcm": _reference(
        "DICOM",
        "references/microscopy_imaging_formats.md",
        "PHI-aware DICOM tooling and policy required",
    ),
    ".nii": _reference(
        "NIfTI",
        "references/microscopy_imaging_formats.md",
        "orientation-aware neuroimaging tooling required",
    ),
    ".nii.gz": _reference(
        "Compressed NIfTI",
        "references/microscopy_imaging_formats.md",
        "compressed content is not decompressed by bundled tools",
    ),
    ".mrc": _reference(
        "MRC",
        "references/microscopy_imaging_formats.md",
        "electron-microscopy-aware tooling required",
    ),
    ".svs": _reference(
        "Aperio SVS",
        "references/microscopy_imaging_formats.md",
        "whole-slide reader and privacy review required",
    ),
    ".ndpi": _reference(
        "Hamamatsu NDPI",
        "references/microscopy_imaging_formats.md",
        "whole-slide reader and privacy review required",
    ),
    # Spectroscopy/proteomics/metabolomics
    ".mzml": _reference(
        "HUPO-PSI mzML",
        "references/spectroscopy_analytical_formats.md",
        "schema/CV-aware mass-spectrometry tooling required",
    ),
    ".mzxml": _reference(
        "mzXML",
        "references/spectroscopy_analytical_formats.md",
        "legacy MS tooling required; no bundled parser",
    ),
    ".jdx": _reference(
        "JCAMP-DX",
        "references/spectroscopy_analytical_formats.md",
        "technique/version-aware JCAMP parser required",
    ),
    ".dx": _reference(
        "JCAMP-DX",
        "references/spectroscopy_analytical_formats.md",
        "technique/version-aware JCAMP parser required",
    ),
    ".spc": _reference(
        "SPC",
        "references/spectroscopy_analytical_formats.md",
        "vendor/variant-aware reader required",
    ),
    ".mgf": _reference(
        "Mascot Generic Format",
        "references/spectroscopy_analytical_formats.md",
        "MS-specific parser required; no bundled parser",
    ),
    ".raw": _reference(
        "Ambiguous vendor RAW",
        "references/spectroscopy_analytical_formats.md",
        "extension alone cannot identify the vendor format",
    ),
    ".mzid": _reference(
        "mzIdentML",
        "references/proteomics_metabolomics_formats.md",
        "schema/CV-aware identification tooling required",
    ),
    ".mzidentml": _reference(
        "mzIdentML",
        "references/proteomics_metabolomics_formats.md",
        "schema/CV-aware identification tooling required",
    ),
    ".pepxml": _reference(
        "pepXML",
        "references/proteomics_metabolomics_formats.md",
        "search-engine-aware parser required",
    ),
    ".protxml": _reference(
        "protXML",
        "references/proteomics_metabolomics_formats.md",
        "protein-inference-aware parser required",
    ),
    ".mztab": _reference(
        "mzTab or mzTab-M",
        "references/proteomics_metabolomics_formats.md",
        "version-aware PSI validation required; generic TSV parsing is insufficient",
    ),
    ".featurexml": _reference(
        "OpenMS featureXML",
        "references/proteomics_metabolomics_formats.md",
        "OpenMS-aware parser required",
    ),
}


def suffix_key(path: Path) -> str:
    """Return a registered compound or simple suffix, failing closed otherwise."""

    name = path.name.casefold()
    keys = sorted(
        {*AUTOMATED_FORMATS, *REFERENCE_ONLY_FORMATS},
        key=len,
        reverse=True,
    )
    for key in keys:
        if name.endswith(key):
            return key
    raise CliError("unknown format; no content sniffing or generic fallback is allowed")


def capability_for_path(path: Path) -> dict[str, Any]:
    """Return a copy of the closed capability entry for a path."""

    key = suffix_key(path)
    entry = AUTOMATED_FORMATS.get(key) or REFERENCE_ONLY_FORMATS[key]
    return {"suffix": key, **entry}


def _first_nonempty_text_byte(path: Path, *, limit: int = 8192) -> bytes | None:
    with path.open("rb") as handle:
        chunk = handle.read(limit)
    for line in chunk.splitlines():
        stripped = line.lstrip()
        if stripped:
            return stripped[:1]
    return None


def validate_magic(path: Path, suffix: str) -> None:
    """Check unambiguous signatures without guessing an unsupported format."""

    try:
        with path.open("rb") as handle:
            prefix = handle.read(16)
    except OSError as exc:
        raise CliError("the input header could not be read") from exc

    if suffix == ".npy" and not prefix.startswith(b"\x93NUMPY"):
        raise CliError("the NPY signature does not match the declared suffix")
    if suffix == ".npz" and not prefix.startswith(b"PK"):
        raise CliError("the NPZ ZIP signature does not match the declared suffix")
    if suffix in {".h5", ".hdf5"}:
        signature = b"\x89HDF\r\n\x1a\n"
        found = False
        with path.open("rb") as handle:
            for offset in itertools.takewhile(
                lambda value: value < max(path.stat().st_size, 1),
                (0, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536),
            ):
                handle.seek(offset)
                if handle.read(8) == signature:
                    found = True
                    break
        if not found:
            raise CliError("the HDF5 signature does not match the declared suffix")
    if suffix in {".fasta", ".fa", ".fna"}:
        if _first_nonempty_text_byte(path) != b">":
            raise CliError("the FASTA record marker does not match the declared suffix")
    if suffix in {".fastq", ".fq"}:
        if _first_nonempty_text_byte(path) != b"@":
            raise CliError("the FASTQ record marker does not match the declared suffix")
    if suffix == ".png" and not prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        raise CliError("the PNG signature does not match the declared suffix")
    if suffix in {".jpg", ".jpeg"} and not prefix.startswith(b"\xff\xd8\xff"):
        raise CliError("the JPEG signature does not match the declared suffix")
    if suffix in {".tif", ".tiff", ".ome.tif", ".ome.tiff"}:
        valid = (
            prefix.startswith(b"II*\x00")
            or prefix.startswith(b"MM\x00*")
            or prefix.startswith(b"II+\x00")
            or prefix.startswith(b"MM\x00+")
        )
        if not valid:
            raise CliError("the TIFF signature does not match the declared suffix")


def preflight_npz(path: Path) -> dict[str, Any]:
    """Reject encrypted, traversing, oversized, or high-ratio NPZ members."""

    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise CliError("the NPZ container is not a valid bounded ZIP archive") from exc
    if not members or len(members) > MAX_NPZ_MEMBERS:
        raise CliError(
            f"the NPZ member count must be between 1 and {MAX_NPZ_MEMBERS}"
        )
    total_uncompressed = 0
    highest_ratio = 0.0
    member_names: set[str] = set()
    for member in members:
        member_path = Path(member.filename)
        normalized_name = member.filename.replace("\\", "/")
        normalized_parts = Path(normalized_name).parts
        if (
            member.is_dir()
            or member_path.is_absolute()
            or normalized_name.startswith("/")
            or ":" in normalized_name
            or ".." in normalized_parts
        ):
            raise CliError("the NPZ contains an invalid member path")
        if normalized_name in member_names:
            raise CliError("the NPZ contains duplicate member names")
        member_names.add(normalized_name)
        if member.flag_bits & 0x1:
            raise CliError("encrypted NPZ members are not accepted")
        if not member.filename.casefold().endswith(".npy"):
            raise CliError("every NPZ member must be an NPY array")
        total_uncompressed += member.file_size
        denominator = max(member.compress_size, 1)
        highest_ratio = max(highest_ratio, member.file_size / denominator)
    if total_uncompressed > MAX_NPZ_UNCOMPRESSED_BYTES:
        raise CliError(
            "the NPZ declared uncompressed size exceeds the safety limit"
        )
    if highest_ratio > MAX_COMPRESSION_RATIO:
        raise CliError("the NPZ compression ratio exceeds the safety limit")
    return {
        "member_count": len(members),
        "declared_uncompressed_bytes": total_uncompressed,
        "maximum_compression_ratio": round(highest_ratio, 3),
    }


def automated_capability_rows() -> list[dict[str, Any]]:
    """Return deterministic rows for the public capability matrix."""

    return [
        {"suffix": suffix, **AUTOMATED_FORMATS[suffix]}
        for suffix in sorted(AUTOMATED_FORMATS)
    ]
