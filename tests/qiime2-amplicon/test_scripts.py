from pathlib import Path
import gzip
import importlib.util
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
