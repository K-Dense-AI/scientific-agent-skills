#!/usr/bin/env python3
"""Validate paired-end amplicons and run a provenance-preserving QIIME 2 workflow."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import subprocess

IUPAC = dict(zip('ACGTRYSWKMBDHVN', ['A', 'C', 'G', 'T', 'AG', 'CT', 'GC', 'AT', 'GT', 'AC', 'CGT', 'AGT', 'ACT', 'ACG', 'ACGT']))
ID_HEADERS = {'id', 'sampleid', 'sample id', 'sample-id', 'featureid', 'feature id', 'feature-id'}
LEGACY_ID_HEADERS = {'#SampleID', '#Sample ID', '#OTUID', '#OTU ID', 'sample_name'}


def id_header(value: str) -> bool:
    return value.lower() in ID_HEADERS or value in LEGACY_ID_HEADERS


def fastq(path: Path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='ascii') as handle:
        while True:
            name = handle.readline()
            if not name:
                break
            sequence, plus, quality = (handle.readline().rstrip('\r\n') for _ in range(3))
            if not name.startswith('@') or not plus.startswith('+') or not sequence or len(sequence) != len(quality):
                raise ValueError(f'Malformed four-line FASTQ record in {path}')
            if set(sequence.upper()) - set('ACGTN') or any(not 33 <= ord(c) <= 126 for c in quality):
                raise ValueError(f'Invalid sequence or Phred+33 characters in {path}')
            tokens = name[1:].split()
            identifier = re.sub(r'/[12]$', '', tokens[0]) if tokens else ''
            if not identifier:
                raise ValueError(f'Empty FASTQ read identifier in {path}')
            yield identifier, sequence.upper()


def primer_match(sequence: str, primer: str) -> bool:
    return len(sequence) >= len(primer) and all(base in IUPAC[p] for base, p in zip(sequence, primer))


def read_metadata(path: Path) -> set[str]:
    with path.open(encoding='utf-8-sig') as handle:
        rows = [[cell.strip() for cell in row] for row in csv.reader(handle, delimiter='\t')]
    rows = [row for row in rows if any(row) and
            (not row[0].startswith('#') or row[0] in LEGACY_ID_HEADERS)]
    if not rows:
        raise ValueError('Metadata is empty')
    if not id_header(rows[0][0]):
        raise ValueError('Use sample-id as the first metadata header')
    columns = rows[0][1:]
    if any(not c or id_header(c) for c in columns) or len({c.lower() for c in columns}) != len(columns):
        raise ValueError('Metadata has empty, reserved, or duplicate column names')
    if any(len(row) != len(rows[0]) for row in rows[1:]):
        raise ValueError('Metadata rows must have the same number of columns as the header')
    samples = [row[0] for row in rows[1:]]
    if not samples or any(not s or id_header(s) for s in samples) or len(samples) != len(set(samples)):
        raise ValueError('Metadata has empty, reserved, or duplicate sample IDs')
    return set(samples)


def validate(manifest: Path, metadata: Path, primer_f: str, primer_r: str,
             trunc_f: int, trunc_r: int, amplicon_max: int, min_overlap: int = 12) -> dict:
    primers = (primer_f.upper(), primer_r.upper())
    if any(not p or set(p) - set(IUPAC) for p in primers):
        raise ValueError('Both primers must be nonempty IUPAC DNA, written 5-prime to 3-prime as sequenced')
    if min(trunc_f, trunc_r, amplicon_max) <= 0 or min_overlap < 12:
        raise ValueError('Positive post-primer truncation/amplicon lengths and overlap >=12 are required')
    overlap = trunc_f + trunc_r - amplicon_max
    if overlap < min_overlap:
        raise ValueError(f'Only {overlap} bp overlap remains; need at least {min_overlap}')
    with manifest.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        fields = ['sample-id', 'forward-absolute-filepath', 'reverse-absolute-filepath']
        if reader.fieldnames != fields:
            raise ValueError(f'PairedEndFastqManifestPhred33V2 requires tab-separated columns {fields}')
        rows = list(reader)
    seen, paths, results = set(), set(), []
    for row in rows:
        if None in row or any(row[key] is None or not row[key].strip() for key in fields):
            raise ValueError('Manifest rows must contain exactly three nonempty tab-separated cells')
        sample = row['sample-id'].strip()
        if sample.startswith('#') or id_header(sample) or sample in seen:
            raise ValueError(f'Reserved or duplicate sample ID: {sample}')
        seen.add(sample)
        files = [Path(row[key].strip()) for key in fields[1:]]
        if any(not p.is_absolute() or not p.is_file() for p in files):
            raise ValueError(f'{sample}: FASTQ paths must be absolute existing files')
        if len({p.resolve() for p in files}) != 2 or any(p.resolve() in paths for p in files):
            raise ValueError(f'{sample}: repeated forward/reverse FASTQ file')
        paths.update(p.resolve() for p in files)
        count, matched, too_short, long_pairs = 0, [0, 0], [0, 0], 0
        for forward, reverse in itertools.zip_longest(fastq(files[0]), fastq(files[1])):
            if forward is None or reverse is None or forward[0] != reverse[0]:
                raise ValueError(f'{sample}: paired read IDs/order/counts do not match')
            count += 1
            long_pairs += all(len(read[1]) - len(primers[i]) >= (trunc_f, trunc_r)[i]
                              for i, read in enumerate((forward, reverse)))
            for i, read in enumerate((forward, reverse)):
                sequence = read[1]
                if count <= 1000:
                    matched[i] += primer_match(sequence, primers[i])
                too_short[i] += len(sequence) - len(primers[i]) < (trunc_f, trunc_r)[i]
        if long_pairs == 0:
            raise ValueError(f'{sample}: no read pairs meet nominal truncation lengths after primer removal')
        results.append({'sample_id': sample, 'raw_pairs': count,
                        'nominal_length_eligible_pairs': long_pairs,
                        'exact_primer_fraction_first_1000': [v/min(count, 1000) for v in matched],
                        'short_fraction_before_quality_filter': [v/count for v in too_short]})
    if not seen or read_metadata(metadata) != seen:
        raise ValueError('Manifest and metadata sample IDs must match exactly')
    warnings = [f"{s['sample_id']}: fewer than 80% exact primer-prefix matches; inspect orientation/adapters"
                for s in results if min(s['exact_primer_fraction_first_1000']) < 0.8]
    return {'samples': results, 'minimum_predicted_overlap': overlap, 'warnings': warnings}


def retention(path: Path, raw_counts: dict[str, int] | None = None) -> dict:
    if raw_counts is not None and any(type(v) is not int or v < 0 for v in raw_counts.values()):
        raise ValueError('Raw read-pair counts must be nonnegative integers')
    with path.open() as handle:
        reader = csv.DictReader((line for line in handle if not line.startswith('#q2:')), delimiter='\t')
        rows = list(reader)
    summaries, warnings = [], []
    for row in rows:
        sample = row.get('sample-id', row.get('sampleid', row.get('#SampleID')))
        if not sample or not sample.strip():
            raise ValueError('DADA2 statistics lack sample IDs')
        sample = sample.strip()
        if 'concatenated' in row:
            raise ValueError('Retention helper requires merged-only DADA2 statistics (retain_unmerged=False)')
        counts = [float(row[key]) for key in ['input', 'filtered', 'denoised', 'merged', 'non-chimeric']]
        if any(not math.isfinite(x) or x < 0 or not x.is_integer() for x in counts):
            raise ValueError('Invalid DADA2 read counts')
        if any(b > a for a, b in zip(counts, counts[1:])):
            raise ValueError('DADA2 retained counts increase between stages')
        if raw_counts is not None and sample not in raw_counts:
            raise ValueError('DADA2 statistics contain samples absent from raw read counts')
        raw = raw_counts[sample] if raw_counts is not None else int(counts[0])
        if counts[0] > raw:
            raise ValueError('DADA2 input exceeds raw read pairs')
        fraction = counts[-1]/raw if raw else 0.0
        basis = 'raw pairs' if raw_counts is not None else 'DADA2 input pairs'
        if fraction < 0.5:
            warnings.append(f'{sample}: retained {fraction:.1%} of {basis}; inspect trimming, quality, merging, chimeras')
        summaries.append({'sample_id': sample, 'raw_pairs': raw if raw_counts is not None else None,
                          'retention_denominator': basis, 'dada2_input': int(counts[0]),
                          'non_chimeric': int(counts[-1]), 'retained_fraction': fraction})
    ids = [r['sample_id'] for r in summaries]
    if not ids or len(ids) != len(set(ids)) or (raw_counts is not None and set(ids) != set(raw_counts)):
        raise ValueError('Missing/duplicate samples in DADA2 statistics')
    return {'samples': summaries, 'warnings': warnings}


def validate_runtime(info: str) -> None:
    versions = {key.strip().replace('_', '-'): value.strip()
                for line in info.splitlines() if ':' in line
                for key, value in [line.split(':', 1)]}
    required = ['rachis version', 'q2cli version', 'cutadapt', 'dada2', 'demux',
                'feature-table', 'feature-classifier', 'taxa', 'types']
    incompatible = [name for name in required
                    if not re.fullmatch(r'2026\.7\.\d+', versions.get(name, ''))]
    if incompatible:
        raise ValueError('This runner requires stable QIIME 2 2026.7 and matching plugins; '
                         'missing or incompatible: ' + ', '.join(incompatible))


def run(args) -> dict:
    qc = validate(args.manifest, args.metadata, args.primer_f, args.primer_r,
                  args.trunc_f, args.trunc_r, args.amplicon_max, args.min_overlap)
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh output directory; retain prior QIIME artifacts and provenance')
    if not args.classifier.is_file():
        raise ValueError('Provide a release-compatible TaxonomicClassifier .qza')
    info = subprocess.run([args.qiime, 'info'], check=True, text=True, capture_output=True).stdout
    validate_runtime(info)
    output.mkdir(parents=True, exist_ok=True)
    (output/'qiime-info.txt').write_text(info)
    (output/'input-qc.json').write_text(json.dumps(qc, indent=2)+'\n')
    commands = []
    def invoke(*parts):
        command = [args.qiime, *map(str, parts)]
        commands.append(command)
        (output/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        with (output/'workflow.log').open('a') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    invoke('tools', 'validate', args.classifier.resolve(), '--level', 'max')
    invoke('tools', 'import', '--type', 'SampleData[PairedEndSequencesWithQuality]',
           '--input-format', 'PairedEndFastqManifestPhred33V2', '--input-path', args.manifest.resolve(),
           '--output-path', output/'demux.qza')
    invoke('cutadapt', 'trim-paired', '--i-demultiplexed-sequences', output/'demux.qza',
           '--p-front-f', '^'+args.primer_f.upper(), '--p-front-r', '^'+args.primer_r.upper(),
           '--p-discard-untrimmed', '--p-cores', args.threads, '--output-dir', output/'cutadapt')
    invoke('demux', 'summarize', '--i-data', output/'cutadapt/trimmed_sequences.qza', '--o-visualization', output/'trimmed.qzv')
    invoke('dada2', 'denoise-paired', '--i-demultiplexed-seqs', output/'cutadapt/trimmed_sequences.qza',
           '--p-trunc-len-f', args.trunc_f, '--p-trunc-len-r', args.trunc_r,
           '--p-trim-left-f', 0, '--p-trim-left-r', 0, '--p-min-overlap', args.min_overlap,
           '--p-n-threads', args.threads, '--output-dir', output/'denoise')
    invoke('feature-table', 'summarize', '--i-table', output/'denoise/table.qza',
           '--m-metadata-file', args.metadata.resolve(), '--o-summary', output/'table.qzv',
           '--o-feature-frequencies', output/'feature-frequencies.qza',
           '--o-sample-frequencies', output/'sample-frequencies.qza')
    invoke('feature-classifier', 'classify-sklearn', '--i-classifier', args.classifier.resolve(),
           '--i-reads', output/'denoise/representative_sequences.qza', '--p-n-jobs', args.threads,
           '--o-classification', output/'taxonomy.qza')
    invoke('taxa', 'barplot', '--i-table', output/'denoise/table.qza', '--i-taxonomy', output/'taxonomy.qza',
           '--m-metadata-file', args.metadata.resolve(), '--o-visualization', output/'taxa.qzv')
    invoke('tools', 'export', '--input-path', output/'denoise/denoising_stats.qza',
           '--output-path', output/'stats')
    artifacts = sorted(output.rglob('*.qza'))
    for artifact in artifacts:
        invoke('tools', 'validate', artifact, '--level', 'max')
    result = retention(output/'stats/stats.tsv', {s['sample_id']: s['raw_pairs'] for s in qc['samples']})
    result.update({'classifier_sha256': digest(args.classifier),
                   'manifest_sha256': digest(args.manifest), 'metadata_sha256': digest(args.metadata),
                   'artifacts': {str(p.relative_to(output)): digest(p) for p in artifacts}})
    (output/'retention-qc.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ['validate', 'run']:
        command = sub.add_parser(action)
        command.add_argument('--manifest', type=Path, required=True)
        command.add_argument('--metadata', type=Path, required=True)
        command.add_argument('--primer-f', required=True)
        command.add_argument('--primer-r', required=True)
        command.add_argument('--trunc-f', type=int, required=True)
        command.add_argument('--trunc-r', type=int, required=True)
        command.add_argument('--amplicon-max', type=int, required=True, help='Maximum expected biological insert length AFTER removing primers')
        command.add_argument('--min-overlap', type=int, default=12)
        if action == 'run':
            command.add_argument('--classifier', type=Path, required=True)
            command.add_argument('--output', type=Path, required=True)
            command.add_argument('--qiime', default='qiime')
            command.add_argument('--threads', type=int, default=1)
    stats = sub.add_parser('retention')
    stats.add_argument('stats_tsv', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'run':
            if args.threads < 1:
                raise ValueError('threads must be positive')
            result = run(args)
        elif args.action == 'validate':
            result = validate(args.manifest, args.metadata, args.primer_f, args.primer_r,
                              args.trunc_f, args.trunc_r, args.amplicon_max, args.min_overlap)
        else:
            result = retention(args.stats_tsv)
    except (ValueError, OSError, EOFError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
