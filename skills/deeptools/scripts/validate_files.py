#!/usr/bin/env python3
"""
deepTools File Validation Script

Validates BAM, bigWig, and BED files for deepTools analysis.
Checks for file existence, proper indexing, and basic format requirements.
"""

import os
import sys
import argparse
import gzip
import math
import struct
from pathlib import Path


def check_file_exists(filepath):
    """Check if file exists and is readable."""
    if not Path(filepath).is_file():
        return False, f"File not found: {filepath}"
    if not os.access(filepath, os.R_OK):
        return False, f"File not readable: {filepath}"
    return True, f"[OK] File exists: {filepath}"


def check_bam_index(bam_file):
    """Check index presence only; check_bam_file validates its readability."""
    path = Path(bam_file)
    for index in (Path(str(path) + ".bai"), path.with_suffix(".bai"),
                  Path(str(path) + ".csi"), path.with_suffix(".csi")):
        if index.is_file():
            return True, f"[OK] BAM index found: {index}"
    return False, f"[FAIL] BAM index missing for: {bam_file}\n  Run: samtools index {bam_file}"


def check_bam_file(bam_file):
    """Decode all alignments and check coordinate order and readable index."""
    try:
        import pysam
        with pysam.AlignmentFile(str(bam_file), "rb", require_index=True) as bam:
            if not bam.is_bam or not bam.references:
                raise ValueError("expected BAM with a reference dictionary")
            bam.check_index()
            previous = (-1, -1)
            seen_unplaced = False
            count = 0
            for read in bam.fetch(until_eof=True):
                count += 1
                if read.reference_id < 0:
                    seen_unplaced = True
                    continue
                position = (read.reference_id, read.reference_start)
                if seen_unplaced or position < previous:
                    raise ValueError("BAM is not coordinate sorted; run samtools sort, then index")
                previous = position
            # Exercise indexed access too, rather than just trusting a sidecar name.
            for chrom in bam.references:
                next(bam.fetch(chrom, 0, 1), None)
        return True, f"[OK] BAM decoded and index readable: {bam_file} ({count} alignments)"
    except ImportError:
        return False, "[FAIL] BAM validation requires pysam (installed with deepTools)"
    except (OSError, ValueError) as exc:
        return False, f"[FAIL] Invalid BAM/index: {bam_file}\n  Error: {exc}"


def check_bigwig_file(bw_file):
    """Open the bigWig index/header and sample signal, rather than guessing by size."""
    try:
        import pyBigWig
        # pyBigWig.header() converts floating summary fields to Python integers;
        # nonfinite summaries emitted for an empty normalized strand can crash it.
        # Read this small fixed-format summary safely before entering native code.
        with open(bw_file, 'rb') as handle:
            raw_header = handle.read(64)
            if len(raw_header) != 64:
                raise ValueError("truncated bigWig header")
            magic = raw_header[:4]
            endian = '<' if magic == b'\x26\xfc\x8f\x88' else '>'
            if struct.unpack(endian + 'I', magic)[0] != 0x888FFC26:
                raise ValueError("invalid bigWig magic")
            summary_offset = struct.unpack(endian + 'Q', raw_header[44:52])[0]
            if summary_offset:
                if summary_offset > os.path.getsize(bw_file) - 40:
                    raise ValueError("summary offset outside file")
                handle.seek(summary_offset)
                covered, minimum, maximum, total, squares = struct.unpack(endian + 'Qdddd', handle.read(40))
                if covered == 0:
                    raise ValueError("bigWig contains no covered bases")
                if not all(math.isfinite(x) for x in (minimum, maximum, total, squares)):
                    raise ValueError("nonfinite/invalid signal summary; check empty-strand normalization")
        with pyBigWig.open(str(bw_file)) as bw:
            if not bw.isBigWig() or not bw.chroms():
                raise ValueError("expected bigWig with a chromosome dictionary")
            for chrom, length in bw.chroms().items():
                if length <= 0:
                    raise ValueError("nonpositive chromosome length")
                bw.values(chrom, 0, min(length, 100))
        return True, f"[OK] bigWig header/index readable: {bw_file} (not a full signal scan)"
    except ImportError:
        return False, "[FAIL] bigWig validation requires pyBigWig (installed with deepTools)"
    except (OSError, RuntimeError, ValueError, struct.error) as exc:
        return False, f"[FAIL] Invalid bigWig: {bw_file}\n  Error: {exc}"


def check_bed_file(bed_file):
    """Basic validation of BED file format."""
    try:
        opener = gzip.open if str(bed_file).endswith('.gz') else open
        count = 0
        with opener(bed_file, 'rt') as f:
            for i, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith('#') or line.split()[0] in ('track', 'browser'):
                    continue
                fields = line.split('\t')
                if len(fields) < 3:
                    return False, f"[FAIL] BED line {i}: expected at least 3 columns"
                try:
                    start, end = int(fields[1]), int(fields[2])
                except ValueError:
                    return False, f"[FAIL] BED line {i}: start and end must be integers"
                if start < 0:
                    return False, f"[FAIL] BED line {i}: start must be nonnegative"
                if start >= end:
                    return False, f"[FAIL] BED line {i}: start >= end ({start} >= {end})"
                if not fields[0] or any(c.isspace() for c in fields[0]):
                    return False, f"[FAIL] BED line {i}: invalid chromosome name"
                if len(fields) >= 6 and fields[5] not in ('+', '-', '.'):
                    return False, f"[FAIL] BED line {i}: strand must be +, - or ."
                count += 1
        if not count:
            return False, f"[FAIL] BED file is empty: {bed_file}"
        return True, f"[OK] BED intervals valid: {bed_file} ({count} regions; BED12 blocks not checked)"

    except Exception as e:
        return False, f"[FAIL] Error reading BED file: {bed_file}\n  Error: {str(e)}"


def validate_files(bam_files=None, bigwig_files=None, bed_files=None):
    """
    Validate all provided files.

    Args:
        bam_files: List of BAM file paths
        bigwig_files: List of bigWig file paths
        bed_files: List of BED file paths

    Returns:
        Tuple of (success: bool, messages: list)
    """
    all_success = True
    messages = []

    # Validate BAM files
    if bam_files:
        messages.append("\n=== Validating BAM Files ===")
        for bam_file in bam_files:
            # Check existence
            success, msg = check_file_exists(bam_file)
            messages.append(msg)
            if not success:
                all_success = False
                continue

            success, msg = check_bam_file(bam_file)
            messages.append(msg)
            if not success:
                all_success = False
                continue

            # Check index
            success, msg = check_bam_index(bam_file)
            messages.append(msg)
            if not success:
                all_success = False

    # Validate bigWig files
    if bigwig_files:
        messages.append("\n=== Validating bigWig Files ===")
        for bw_file in bigwig_files:
            # Check existence
            success, msg = check_file_exists(bw_file)
            messages.append(msg)
            if not success:
                all_success = False
                continue

            # Basic bigWig check
            success, msg = check_bigwig_file(bw_file)
            messages.append(msg)
            if not success:
                all_success = False

    # Validate BED files
    if bed_files:
        messages.append("\n=== Validating BED Files ===")
        for bed_file in bed_files:
            # Check existence
            success, msg = check_file_exists(bed_file)
            messages.append(msg)
            if not success:
                all_success = False
                continue

            # Check BED format
            success, msg = check_bed_file(bed_file)
            messages.append(msg)
            if not success:
                all_success = False

    return all_success, messages


def main():
    parser = argparse.ArgumentParser(
        description="Validate files for deepTools analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate BAM files
  python validate_files.py --bam sample1.bam sample2.bam

  # Validate all file types
  python validate_files.py --bam input.bam chip.bam --bed peaks.bed --bigwig signal.bw

  # Validate from a directory
  python validate_files.py --bam *.bam --bed *.bed
        """
    )

    parser.add_argument('--bam', nargs='+', help='BAM files to validate')
    parser.add_argument('--bigwig', '--bw', nargs='+', help='bigWig files to validate')
    parser.add_argument('--bed', nargs='+', help='BED files to validate')

    args = parser.parse_args()

    # Check if any files were provided
    if not any([args.bam, args.bigwig, args.bed]):
        parser.print_help()
        sys.exit(1)

    # Run validation
    success, messages = validate_files(
        bam_files=args.bam,
        bigwig_files=args.bigwig,
        bed_files=args.bed
    )

    # Print results
    for msg in messages:
        print(msg)

    # Summary
    print("\n" + "="*50)
    if success:
        print("[OK] All validations passed!")
        sys.exit(0)
    else:
        print("[FAIL] Some validations failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
