from pathlib import Path
import gzip
import importlib.util
import json
import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'qiime2-amplicon'
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
spec = importlib.util.spec_from_file_location('amplicon_workflow', SKILL_ROOT / 'scripts' / 'amplicon_workflow.py')
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def example(tmp_path, reverse_id='read1', reverse_sequence='TGCATGCA'+'C'*100):
    for name, identifier, sequence in [('f', 'read1', 'ACGTACGT'+'A'*100), ('r', reverse_id, reverse_sequence)]:
        with gzip.open(tmp_path/f'{name}.fastq.gz', 'wt') as f:
            f.write(f'@{identifier}\n{sequence}\n+\n'+len(sequence)*'I'+'\n')
    manifest = tmp_path/'manifest.tsv'
    manifest.write_text('sample-id\tforward-absolute-filepath\treverse-absolute-filepath\nsample1\t'+str(tmp_path/'f.fastq.gz')+'\t'+str(tmp_path/'r.fastq.gz')+'\n')
    metadata = tmp_path/'metadata.tsv'
    metadata.write_text('sample-id\tcondition\n#q2:types\tcategorical\nsample1\tcontrol\n')
    return manifest, metadata


def test_iupac_primer_detection_and_real_overlap(tmp_path):
    manifest, metadata = example(tmp_path)
    result = workflow.validate(manifest, metadata, 'ACGTNCGT', 'TGCATGCA', 100, 100, 180)
    assert result['minimum_predicted_overlap'] == 20
    assert result['samples'][0]['exact_primer_fraction_first_1000'] == [1.0, 1.0]
    assert result['samples'][0]['raw_pairs'] == 1


def test_insufficient_overlap_is_rejected(tmp_path):
    manifest, metadata = example(tmp_path)
    with pytest.raises(ValueError, match='overlap'):
        workflow.validate(manifest, metadata, 'ACGTACGT', 'TGCATGCA', 100, 100, 195)


@pytest.mark.parametrize('problem', ['pair_id', 'metadata', 'truncation', 'same_file'])
def test_read_and_sample_failures(tmp_path, problem):
    manifest, metadata = example(tmp_path, reverse_id='different' if problem == 'pair_id' else 'read1')
    if problem == 'metadata':
        metadata.write_text('sample-id\nother\n')
    if problem == 'same_file':
        manifest.write_text(manifest.read_text().replace('r.fastq.gz', 'f.fastq.gz'))
    with pytest.raises(ValueError):
        workflow.validate(manifest, metadata, 'ACGTACGT', 'TGCATGCA', 120 if problem == 'truncation' else 100, 100, 180)


def test_malformed_fastq_is_rejected(tmp_path):
    path = tmp_path/'bad.fastq'
    path.write_text('@r\nACGT\n+\nIII\n')
    with pytest.raises(ValueError, match='Malformed'):
        list(workflow.fastq(path))


@pytest.mark.parametrize('header', ['@', '@/1', '@   '])
def test_empty_fastq_identifier_is_rejected(tmp_path, header):
    path = tmp_path/'bad.fastq'
    path.write_text(f'{header}\nACGT\n+\nIIII\n')
    with pytest.raises(ValueError, match='identifier'):
        list(workflow.fastq(path))


def test_truncation_requires_both_mates_in_the_same_pair(tmp_path):
    manifest, metadata = example(tmp_path)
    for name, primer, lengths in [('f', 'ACGTACGT', (100, 50)), ('r', 'TGCATGCA', (50, 100))]:
        with gzip.open(tmp_path/f'{name}.fastq.gz', 'wt') as handle:
            for i, length in enumerate(lengths):
                sequence = primer + 'A'*length
                handle.write(f'@read{i}\n{sequence}\n+\n'+len(sequence)*'I'+'\n')
    with pytest.raises(ValueError, match='no read pairs'):
        workflow.validate(manifest, metadata, 'ACGTACGT', 'TGCATGCA', 100, 100, 180)


@pytest.mark.parametrize('change', ['missing_cell', 'extra_cell', 'empty_path', 'reserved_id'])
def test_malformed_manifest_is_rejected(tmp_path, change):
    manifest, metadata = example(tmp_path)
    lines = manifest.read_text().splitlines()
    row = lines[1].split('\t')
    if change == 'missing_cell':
        row.pop()
    elif change == 'extra_cell':
        row.append('ignored')
    elif change == 'empty_path':
        row[1] = ''
    else:
        row[0] = 'sample-id'
    manifest.write_text(lines[0]+'\n'+'\t'.join(row)+'\n')
    with pytest.raises(ValueError):
        workflow.validate(manifest, metadata, 'ACGTACGT', 'TGCATGCA', 100, 100, 180)


def test_metadata_comments_and_whitespace_follow_qiime_id_rules(tmp_path):
    manifest, metadata = example(tmp_path)
    metadata.write_text('# experiment\n Sample-ID \tcondition\n#q2:types\tcategorical\n sample1 \tcontrol\n\t\n')
    result = workflow.validate(manifest, metadata, 'ACGTACGT', 'TGCATGCA', 100, 100, 180)
    assert result['samples'][0]['nominal_length_eligible_pairs'] == 1
    metadata.write_text('sample-id\nsample1\n sample1 \n')
    with pytest.raises(ValueError, match='duplicate'):
        workflow.read_metadata(metadata)


@pytest.mark.parametrize('text', ['sample-id\tcondition\tCondition\nsample1\ta\tb\n',
                                      'sample-id\tcondition\nsample1\n', 'sample-id\nid\n'])
def test_metadata_structure_failures(tmp_path, text):
    metadata = tmp_path/'metadata.tsv'
    metadata.write_text(text)
    with pytest.raises(ValueError):
        workflow.read_metadata(metadata)


def test_retention_separates_raw_and_trimmed_losses(tmp_path):
    stats = tmp_path/'stats.tsv'
    stats.write_text('sample-id\tinput\tfiltered\tdenoised\tmerged\tnon-chimeric\n#q2:types\tnumeric\tnumeric\tnumeric\tnumeric\tnumeric\nsample1\t80\t60\t55\t40\t30\n')
    result = workflow.retention(stats, {'sample1': 100})
    assert result['samples'][0]['retained_fraction'] == 0.3
    assert result['warnings']
    with pytest.raises(ValueError, match='exceeds'):
        workflow.retention(stats, {'sample1': 50})
    stats.write_text(stats.read_text().replace('\t40\t30', '\t40\t45'))
    with pytest.raises(ValueError, match='increase'):
        workflow.retention(stats)


def test_standalone_retention_does_not_invent_raw_count(tmp_path):
    stats = tmp_path/'stats.tsv'
    stats.write_text('sample-id\tinput\tfiltered\tdenoised\tmerged\tnon-chimeric\nsample1\t80\t60\t55\t40\t30\n')
    result = workflow.retention(stats)
    assert result['samples'][0]['raw_pairs'] is None
    assert result['samples'][0]['retained_fraction'] == 30/80
    assert result['samples'][0]['retention_denominator'] == 'DADA2 input pairs'
    with pytest.raises(ValueError, match='nonnegative integers'):
        workflow.retention(stats, {'sample1': -1})
    with pytest.raises(ValueError, match='absent'):
        workflow.retention(stats, {'different': 100})
    stats.write_text(stats.read_text().replace('non-chimeric', 'concatenated\tnon-chimeric').replace('\t30\n', '\t0\t30\n'))
    with pytest.raises(ValueError, match='merged-only'):
        workflow.retention(stats)


def runtime_info():
    # Text format verified in q2cli 2026.7.0 builtin/info.py; no QIIME execution.
    return '\n'.join(f'{name}: 2026.7.0' for name in [
        'rachis version', 'q2cli version', 'cutadapt', 'dada2', 'demux',
        'feature-table', 'feature-classifier', 'taxa', 'types'])


def test_runtime_requires_framework_cli_and_all_used_plugins():
    workflow.validate_runtime(runtime_info())
    workflow.validate_runtime(runtime_info().replace('feature-table', 'feature_table'))
    for info in [runtime_info().replace('dada2: 2026.7.0', 'dada2: 2026.10.0.dev0'),
                 runtime_info().replace('q2cli version: 2026.7.0', ''),
                 runtime_info().replace('2026.7.0', '2026.7.0.dev0'),
                 'Python version: 3.12.13\nConfig: /environments/2026.7/']:
        with pytest.raises(ValueError, match='missing or incompatible'):
            workflow.validate_runtime(info)


def test_bundled_fixture_integrity_validation_and_retention(tmp_path):
    fixtures = Path(__file__).parent/'fixtures'
    provenance = json.loads((fixtures/'provenance.json').read_text())
    for name, expected in provenance['files_sha256'].items():
        assert workflow.digest(fixtures/name) == expected
    pairs = {}
    for path in fixtures.glob('*.fastq.gz'):
        sample = path.name.split('_')[0]
        direction = 0 if '_R1_' in path.name else 1
        pairs.setdefault(sample, [None, None])[direction] = str(path.resolve())
    manifest = tmp_path/'manifest.tsv'
    manifest.write_text('sample-id\tforward-absolute-filepath\treverse-absolute-filepath\n' +
                        ''.join('\t'.join([sample, *paths])+'\n' for sample, paths in sorted(pairs.items())))
    qc = workflow.validate(manifest, fixtures/'sample-metadata.tsv', provenance['primer_forward'],
                           provenance['primer_reverse'], 150, 150, provenance['maximum_insert_length'])
    assert len(qc['samples']) == 10
    assert sum(s['raw_pairs'] for s in qc['samples']) == 1000
    assert qc['minimum_predicted_overlap'] == 46
    assert not qc['warnings']
    retained = workflow.retention(fixtures/'paired-default-stats.tsv')
    assert len(retained['samples']) == 11  # Includes the documented empty BLANK.
    assert sum(s['non_chimeric'] for s in retained['samples']) == 243
