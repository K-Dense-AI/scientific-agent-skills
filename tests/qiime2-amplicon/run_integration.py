"""Execute or independently verify the bounded real QIIME 2 regression workflow."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "qiime2-amplicon"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fasta_sequences(text):
    sequences, current = [], []
    for line in text.splitlines():
        if line.startswith(">"):
            if current:
                sequences.append("".join(current))
            current = []
        else:
            current.append(line.strip())
    if current:
        sequences.append("".join(current))
    return set(sequences)


def stats_rows(path):
    with path.open(newline="") as handle:
        return {row["sample-id"]: row for row in csv.DictReader(handle, delimiter="\t")
                if not row["sample-id"].startswith("#")}


def verify(results):
    expected = stats_rows(FIXTURES / "paired-default-stats.tsv")
    expected.pop("BLANK")
    observed = stats_rows(results / "stats" / "stats.tsv")
    assert set(observed) == set(expected), "DADA2 sample IDs changed"
    for sample, row in expected.items():
        for stage in ("input", "filtered", "denoised", "merged", "non-chimeric"):
            assert int(observed[sample][stage]) == int(row[stage]), (sample, stage, observed[sample][stage], row[stage])
    artifact = results / "denoise" / "representative_sequences.qza"
    with zipfile.ZipFile(artifact) as archive:
        names = [name for name in archive.namelist() if "/data/" in name and name.endswith((".fasta", ".fa"))]
        assert len(names) == 1, names
        actual_sequences = fasta_sequences(archive.read(names[0]).decode())
    expected_sequences = fasta_sequences((FIXTURES / "paired-default.fasta").read_text())
    assert actual_sequences == expected_sequences, "Recovered ASV sequences differ from upstream regression fixture"
    for name in ("taxonomy.qza", "table.qzv", "taxa.qzv", "feature-frequencies.qza", "sample-frequencies.qza", "retention-qc.json", "commands.json", "qiime-info.txt"):
        assert (results / name).is_file(), name
    expected_feature_ids = {hashlib.md5(sequence.encode()).hexdigest() for sequence in expected_sequences}
    with zipfile.ZipFile(results / "taxonomy.qza") as archive:
        names = [name for name in archive.namelist() if name.endswith("/data/taxonomy.tsv")]
        assert len(names) == 1, names
        taxonomy = list(csv.DictReader(io.StringIO(archive.read(names[0]).decode()), delimiter="\t"))
        assert {row["Feature ID"] for row in taxonomy} == expected_feature_ids, "Taxonomy feature IDs do not match ASVs"
        assert all(row["Taxon"].startswith("d__SyntheticFixture") for row in taxonomy), "Smoke classifier lost its known domain labels"
    artifacts = list(results.rglob("*.qza"))
    for artifact in artifacts:
        with zipfile.ZipFile(artifact) as archive:
            assert any(name.endswith("/provenance/action/action.yaml") for name in archive.namelist()), artifact
    return {"samples": len(observed), "asvs": len(actual_sequences),
            "non_chimeric_reads": sum(int(row["non-chimeric"]) for row in observed.values()),
            "upstream_sequence_and_stage_counts_match": True,
            "taxonomy_feature_ids_and_synthetic_domain_labels_match": True,
            "artifacts_with_action_provenance": len(artifacts),
            "taxonomy_accuracy_evaluated": False}


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    reads = output / "reads"
    reads.mkdir()
    pairs = {}
    for source in sorted(FIXTURES.glob("*.fastq.gz")):
        target = reads / source.name
        shutil.copy2(source, target)
        sample = source.name.split("_")[0]
        direction = "forward" if "_R1_" in source.name else "reverse"
        with gzip.open(target, "rt") as handle:
            assert sum(1 for _ in handle) == 400
        pairs.setdefault(sample, {})[direction] = str(target.resolve())
    manifest = output / "manifest.tsv"
    with manifest.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["sample-id", "forward-absolute-filepath", "reverse-absolute-filepath"])
        writer.writerows([sample, pair["forward"], pair["reverse"]] for sample, pair in sorted(pairs.items()))
    commands = [
        ["qiime", "tools", "import", "--type", "FeatureData[Sequence]", "--input-path", str(FIXTURES / "paired-default.fasta"), "--output-path", str(output / "reference-seqs.qza")],
        ["qiime", "tools", "import", "--type", "FeatureData[Taxonomy]", "--input-format", "HeaderlessTSVTaxonomyFormat", "--input-path", str(FIXTURES / "smoke-taxonomy.tsv"), "--output-path", str(output / "reference-taxonomy.qza")],
        ["qiime", "feature-classifier", "fit-classifier-naive-bayes", "--i-reference-reads", str(output / "reference-seqs.qza"), "--i-reference-taxonomy", str(output / "reference-taxonomy.qza"), "--o-classifier", str(output / "smoke-classifier.qza")],
        [sys.executable, str(SKILL_ROOT / "scripts" / "amplicon_workflow.py"), "run", "--manifest", str(manifest), "--metadata", str(FIXTURES / "sample-metadata.tsv"), "--primer-f", "ACGTTGCAACGTTGCAAC", "--primer-r", "TGCAACGTTGCAACGTTG", "--trunc-f", "150", "--trunc-r", "150", "--amplicon-max", "254", "--classifier", str(output / "smoke-classifier.qza"), "--output", str(output / "results")],
    ]
    (output / "fixture-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    for command in commands:
        subprocess.run(command, check=True)
    return verify(output / "results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="Fresh directory for an actual QIIME run")
    mode.add_argument("--verify-only", type=Path, help="Existing skill results directory")
    args = parser.parse_args()
    evidence = verify(args.verify_only) if args.verify_only else run(args.output.resolve())
    print(json.dumps(evidence, indent=2))
