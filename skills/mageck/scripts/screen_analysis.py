"""Validate pooled-screen inputs, quantify QC, and execute MAGeCK RRA testing."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile


def numeric_label(value):
    """Upstream guesses numeric headers as counts and integer labels as indices."""
    try:
        float(value)
        return True
    except ValueError:
        return False


def validate_identifier(value):
    if not value or any(c.isspace() for c in value):
        raise ValueError("Guide and gene IDs must be nonempty and free of whitespace")


def read_counts(path):
    with Path(path).open(newline="") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    if len(rows) < 2 or len(rows[0]) < 4:
        raise ValueError("Expected sgRNA, Gene, and at least two sample columns")
    if [x.lower() for x in rows[0][:2]] != ["sgrna", "gene"]:
        raise ValueError("Count table requires a header beginning sgRNA and Gene")
    samples = rows[0][2:]
    if len(set(samples)) != len(samples) or any(not x or ',' in x or any(c.isspace() for c in x) for x in samples):
        raise ValueError("Sample labels must be unique, nonempty, and free of commas/whitespace")
    if any(numeric_label(x) for x in samples):
        raise ValueError("Numeric sample labels are ambiguous in MAGeCK; rename with a prefix such as sample_1")
    guides, genes, counts = [], [], []
    for line, row in enumerate(rows[1:], 2):
        if len(row) != len(rows[0]) or not row[0] or not row[1]:
            raise ValueError(f"Invalid row {line}: missing fields")
        validate_identifier(row[0]); validate_identifier(row[1])
        try:
            values = [int(v) for v in row[2:]]
        except ValueError as error:
            raise ValueError(f"Row {line}: counts must be integers") from error
        if min(values) < 0:
            raise ValueError(f"Row {line}: negative count")
        guides.append(row[0]); genes.append(row[1]); counts.append(values)
    if len(set(guides)) != len(guides):
        raise ValueError("Duplicate guide IDs")
    if any(sum(col) == 0 for col in zip(*counts)):
        raise ValueError("A sample has zero total reads")
    return samples, guides, genes, counts


def read_library(path):
    """MAGeCK headerless tab-separated guide, sequence, gene library."""
    library, sequences = {}, set()
    with Path(path).open(newline="") as handle:
        for line, row in enumerate(csv.reader(handle, delimiter="\t"), 1):
            if len(row) != 3 or not all(row):
                raise ValueError(f"Library row {line}: expected guide, sequence, gene (no header)")
            guide, seq, gene = row
            validate_identifier(guide); validate_identifier(gene)
            seq = seq.upper()
            if set(seq) - set("ACGT") or guide in library or seq in sequences:
                raise ValueError(f"Library row {line}: invalid DNA, duplicate ID, or ambiguous sequence")
            library[guide] = (seq, gene); sequences.add(seq)
    if not library:
        raise ValueError("Empty library")
    return library


def gini(values):
    ordered = sorted(values)
    return 2 * sum(i * x for i, x in enumerate(ordered, 1)) / (len(ordered) * sum(ordered)) - (len(ordered) + 1) / len(ordered)


def correlation(a, b):
    a = [math.log2(x + 1) for x in a]; b = [math.log2(x + 1) for x in b]
    mean_a, mean_b = statistics.mean(a), statistics.mean(b)
    ac = [x - mean_a for x in a]; bc = [x - mean_b for x in b]
    denominator = math.sqrt(sum(x*x for x in ac) * sum(x*x for x in bc))
    return sum(x*y for x, y in zip(ac, bc)) / denominator if denominator else None


def inspect_screen(count_path, control, treatment, library_path=None, controls_path=None, paired=False):
    samples, guides, genes, counts = read_counts(count_path)
    if not control or not treatment or len(set(control + treatment)) != len(control + treatment):
        raise ValueError("Control and treatment must be nonempty, disjoint lists without duplicates")
    if not set(control + treatment) <= set(samples):
        raise ValueError("Unknown sample label in contrast")
    if paired and len(control) != len(treatment):
        raise ValueError("Paired contrasts need equal counts in matching biological order")
    if library_path:
        library = read_library(library_path)
        if set(library) != set(guides):
            raise ValueError("Count/library guide sets differ; retain zero-count library guides")
        if any(library[g][1] != gene for g, gene in zip(guides, genes)):
            raise ValueError("Count/library gene annotations differ")
    control_guides = []
    if controls_path:
        control_guides = Path(controls_path).read_text().splitlines()
        if not control_guides or len(set(control_guides)) != len(control_guides) or not set(control_guides) <= set(guides):
            raise ValueError("Control-guide file must contain unique known IDs, one per line")
        if len(control_guides) < 2:
            raise ValueError("MAGeCK requires at least two control-guide IDs")
        control_set = set(control_guides)
        control_genes = {gene for guide, gene in zip(guides, genes) if guide in control_set}
        if any(gene in control_genes and guide not in control_set for guide, gene in zip(guides, genes)):
            raise ValueError("A gene cannot mix control and non-control guides in MAGeCK")
        control_rows = [row for guide, row in zip(guides, counts) if guide in control_set]
        if any(sum(col) == 0 for col in zip(*control_rows)):
            raise ValueError("Control-guide counts are zero in a sample")
    columns = dict(zip(samples, zip(*counts)))
    qc = {s: {"reads": sum(v), "zero_fraction": v.count(0)/len(v),
              "median_reads_per_guide": statistics.median(v), "gini": gini(v)} for s, v in columns.items()}
    replicate_correlations = {f"{a} vs {b}": correlation(columns[a], columns[b])
                              for group in (control, treatment) for a, b in itertools.combinations(group, 2)}
    guide_multiplicity = dict(Counter(genes))
    warnings = []
    if min(len(control), len(treatment)) < 2:
        warnings.append("A condition lacks biological replication; dispersion and reproducibility are limited")
    if any(v["zero_fraction"] > .1 for v in qc.values()):
        warnings.append("More than 10% zero-count guides in a sample: review bottlenecks and mapping")
    if any(v is not None and v < .8 for v in replicate_correlations.values()):
        warnings.append("Low within-condition log-count correlation (<0.8): inspect replicate effects")
    if any(v is None for v in replicate_correlations.values()):
        warnings.append("Some replicate correlations are undefined because a sample has constant counts")
    if min(guide_multiplicity.values()) < 3:
        warnings.append("Some genes have fewer than three guides; inspect guide concordance")
    return {"samples": qc, "guides": len(guides), "genes": len(guide_multiplicity),
            "guides_per_gene": guide_multiplicity, "within_condition_log2_count_correlations": replicate_correlations,
            "control": control, "treatment": treatment, "paired": paired,
            "control_guides": len(control_guides), "warnings": warnings}


def normalization_evidence(log, requested, samples):
    """Extract applied scaling from the 0.5.9.5 log, including sparse-count fallback."""
    matches = re.findall(r"Final size factor: ([^\r\n]+)", log)
    factors = [float(x) for x in matches[-1].split()] if matches else []
    if len(factors) != len(samples) or any(not math.isfinite(x) or x <= 0 for x in factors):
        raise RuntimeError("Missing or invalid MAGeCK normalization factors; inspect execution.log")
    fallback = "Switch to total read count normalization." in log
    return {"requested_method": requested,
            "effective_method": "total" if fallback else "median" if requested == "control" else requested,
            "reference_guides": "control_guides" if requested == "control" else "all_guides",
            "fallback_to_total": fallback,
            "sample_size_factors": dict(zip(samples, factors)),
            "warnings": [line for line in log.splitlines() if "WARNING" in line]}


def read_gene_hits(path, fdr):
    hits = {"neg": [], "pos": []}
    seen = set()
    with Path(path).open() as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        for row in rows:
            gene = row["id"]
            if not gene or gene in seen:
                raise ValueError("Missing or duplicate gene in MAGeCK summary")
            seen.add(gene)
            for direction in hits:
                qvalue = float(row[f"{direction}|fdr"])
                lfc = float(row[f"{direction}|lfc"])
                rank = int(row[f"{direction}|rank"])
                if not math.isfinite(qvalue) or not 0 <= qvalue <= 1 or not math.isfinite(lfc) or rank < 1:
                    raise ValueError("Invalid FDR, effect size, or rank in MAGeCK summary")
                if qvalue <= fdr:
                    hits[direction].append({"gene": gene, "fdr": qvalue, "lfc": lfc, "rank": rank})
    if not seen:
        raise ValueError("Empty MAGeCK gene summary")
    return hits


def run_test(count_path, output, control, treatment, library_path=None, controls_path=None,
             paired=False, normalization="median", executable="mageck", fdr=.05):
    if not 0 < fdr < 1:
        raise ValueError("FDR must lie between zero and one")
    if normalization not in {"median", "total", "control", "none"}:
        raise ValueError("Unsupported normalization")
    if normalization == "control" and not controls_path:
        raise ValueError("Control normalization requires control-guide IDs")
    qc = inspect_screen(count_path, control, treatment, library_path, controls_path, paired)
    binary = shutil.which(executable)
    if binary is None:
        raise RuntimeError("MAGeCK executable not found; install MAGeCK 0.5.9.5 and its RRA binary")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    version = subprocess.run([binary, "--version"], text=True, capture_output=True, check=True).stdout.strip()
    # Upstream uses shell commands internally. Fixed staging names avoid its path quoting problems.
    with tempfile.TemporaryDirectory(prefix="mageck-analysis-") as temporary:
        work = Path(temporary)
        shutil.copyfile(count_path, work / "counts.tsv")
        command = [binary, "test", "-k", "counts.tsv", "-c", ",".join(control), "-t", ",".join(treatment),
                   "--norm-method", normalization, "--normcounts-to-file", "--gene-lfc-method", "median",
                   "--remove-zero", "both", "-n", "screen"]
        if paired:
            command.append("--paired")
        if controls_path:
            shutil.copyfile(controls_path, work / "controls.txt")
            command += ["--control-sgrna", "controls.txt"]
        process = subprocess.run(command, cwd=work, capture_output=True, text=True, check=False)
        log = process.stdout + process.stderr
        (output / "execution.log").write_text(log)
        for artifact in work.glob("screen.*"):
            if artifact.is_file():
                shutil.copyfile(artifact, output / artifact.name)
        if process.returncode or not (output / "screen.gene_summary.txt").is_file():
            raise RuntimeError(f"MAGeCK did not complete; inspect {output / 'execution.log'}")
    # 0.5.9.5 normalizes cttab_sel in selected_samples_id = controlgroup + treatgroup
    # order before any paired-guide expansion, rather than in original count-column order.
    normalization_info = normalization_evidence(log, normalization, control + treatment)
    hits = read_gene_hits(output / "screen.gene_summary.txt", fdr)
    report = {"mageck_version": version, "command": command, "count_sha256": hashlib.sha256(Path(count_path).read_bytes()).hexdigest(),
              "library_sha256": hashlib.sha256(Path(library_path).read_bytes()).hexdigest() if library_path else None,
              "control_guides_sha256": hashlib.sha256(Path(controls_path).read_bytes()).hexdigest() if controls_path else None,
              "control_guide_ids": Path(controls_path).read_text().splitlines() if controls_path else [],
              "normalization": normalization_info, "fdr_threshold": fdr, "qc": qc, "hits": hits}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["qc", "test"])
    parser.add_argument("--counts", required=True, type=Path)
    parser.add_argument("--control", nargs="+", required=True)
    parser.add_argument("--treatment", nargs="+", required=True)
    parser.add_argument("--library", type=Path)
    parser.add_argument("--control-guides", type=Path)
    parser.add_argument("--paired", action="store_true")
    parser.add_argument("--normalization", choices=["median", "total", "control", "none"], default="median")
    parser.add_argument("--output", type=Path, help="New directory for test output; JSON path for QC")
    parser.add_argument("--mageck", default="mageck")
    parser.add_argument("--fdr", type=float, default=.05)
    args = parser.parse_args()
    if args.mode == "test":
        if args.output is None:
            parser.error("test requires --output")
        report = run_test(args.counts, args.output, args.control, args.treatment, args.library,
                          args.control_guides, args.paired, args.normalization, args.mageck, args.fdr)
    else:
        report = inspect_screen(args.counts, args.control, args.treatment, args.library, args.control_guides, args.paired)
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
