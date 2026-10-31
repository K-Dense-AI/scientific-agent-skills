"""Small released-CLI regressions; no downloaded sequencing data."""
from pathlib import Path
import gzip
import json
import os
import shutil
import struct
import subprocess
import sys

import pytest

pysam = pytest.importorskip('pysam')
pyBigWig = pytest.importorskip('pyBigWig')
np = pytest.importorskip('numpy')
pytest.importorskip('deeptools')
SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'deeptools'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import validate_files
import workflow_generator


def run(*args, cwd=None):
    result = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                            text=True, timeout=120,
                            env={**os.environ, 'MPLBACKEND': 'Agg', 'PYTHONDONTWRITEBYTECODE': '1'})
    assert result.returncode == 0, f'{args}\n{result.stdout}\n{result.stderr}'
    return result


def make_bam(path, repetitions=1, duplicate=False, variable=0):
    reads = []
    header = {'HD': {'VN': '1.6', 'SO': 'coordinate'}, 'SQ': [{'SN': 'chr1', 'LN': 100000}]}
    for region in range(1, 10):
        n = (region + variable * (region % 3) + 2) * repetitions
        for idx in range(n):
            left = region * 9000 + idx * 100
            length = 160 + (idx % 4) * 20
            for mate, (start, flag) in enumerate(((left, 99 if idx % 2 == 0 else 163), (left + length - 50, 147 if idx % 2 == 0 else 83))):
                read = pysam.AlignedSegment()
                read.query_name = f'r{region}_{idx}'
                read.query_sequence = 'A' * 50
                read.flag = flag | (1024 if duplicate and idx == 0 else 0)
                read.reference_id = 0
                read.reference_start = start
                read.mapping_quality = 60
                read.cigarstring = '50M'
                read.next_reference_id = 0
                read.next_reference_start = left + length - 50 if mate == 0 else left
                read.template_length = length if mate == 0 else -length
                read.query_qualities = pysam.qualitystring_to_array('I' * 50)
                reads.append(read)
    reads.sort(key=lambda r: r.reference_start)
    with pysam.AlignmentFile(str(path), 'wb', header=header) as handle:
        for read in reads:
            handle.write(read)
    pysam.index(str(path))
    return len(reads)


def test_real_bam_bigwig_csi_and_corruption_validation(tmp_path):
    bam = tmp_path / 's.bam'
    make_bam(bam)
    bam.with_suffix('.bam.bai').unlink()
    pysam.index('-c', str(bam))
    ok, messages = validate_files.validate_files(bam_files=[str(bam)])
    assert ok, messages
    bw = tmp_path / 's.bw'
    with pyBigWig.open(str(bw), 'w') as handle:
        handle.addHeader([('chr1', 100000)])
        handle.addEntries(['chr1'], [100], ends=[200], values=[2.0])
    assert validate_files.check_bigwig_file(bw)[0]
    bad_bw = tmp_path / 'nonfinite.bw'
    data = bytearray(bw.read_bytes())
    offset = struct.unpack('<Q', data[44:52])[0]
    struct.pack_into('<d', data, offset + 24, float('nan'))
    bad_bw.write_bytes(data)
    valid, message = validate_files.check_bigwig_file(bad_bw)
    assert not valid and 'nonfinite' in message
    bam.with_suffix('.bam.csi').write_bytes(b'invalid index')
    assert not validate_files.check_bam_file(bam)[0]


def test_marked_duplicate_coverage_and_normalization(tmp_path):
    bam = tmp_path / 's.bam'
    mapped = make_bam(bam, duplicate=True)
    outputs = {}
    for method, extra in [('None', []), ('CPM', []), ('RPKM', []), ('RPGC', ['--effectiveGenomeSize', '100000'])]:
        out = tmp_path / f'{method}.bw'
        run('bamCoverage', '-b', bam, '-o', out, '--binSize', 10, '--normalizeUsing', method,
            '--samFlagExclude', 1024, *extra)
        with pyBigWig.open(str(out)) as handle:
            outputs[method] = handle.values('chr1', 9100, 9101)[0]
            assert handle.values('chr1', 9000, 9001)[0] == 0  # duplicate-marked pair excluded
    retained = mapped - 18
    assert outputs['None'] == 1
    assert outputs['CPM'] == pytest.approx(1e6 / retained, rel=1e-5)
    assert outputs['RPKM'] == pytest.approx(outputs['CPM'] * 100, rel=1e-5)
    assert outputs['RPGC'] == pytest.approx(100000 / (retained * 50), abs=0.005)  # output rounds to 2 decimals
    out = tmp_path / 'ratio.bw'
    run('bamCompare', '-b1', bam, '-b2', bam, '-o', out, '--samFlagExclude', 1024,
        '--scaleFactorsMethod', 'readCount', '--pseudocount', 1)
    with pyBigWig.open(str(out)) as handle:
        assert np.allclose(handle.values('chr1', 9000, 9300), 0)
    run('bamCompare', '-b1', bam, '-b2', bam, '-o', tmp_path / 'difference.bw',
        '--scaleFactorsMethod', 'None', '--normalizeUsing', 'CPM', '--operation', 'subtract')
    # Rolling docs say RPGC is unsupported, but the released Rust command accepts it.
    # Check its numeric result against the same single-BAM coverage settings.
    ratio = tmp_path / 'rpgc_ratio.bw'
    run('bamCompare', '-b1', bam, '-b2', bam, '-o', ratio, '--operation', 'ratio',
        '--normalizeUsing', 'RPGC', '--effectiveGenomeSize', 100000, '--binSize', 10,
        '--samFlagExclude', 1024, '--pseudocount', 0, 1)
    with pyBigWig.open(str(ratio)) as handle:
        expected = outputs['RPGC'] / (outputs['RPGC'] + 1)
        assert handle.values('chr1', 9100, 9101)[0] == pytest.approx(expected, abs=0.005)
    run('estimateReadFiltering', '-b', bam, '--samFlagExclude', 1024, '-o', tmp_path / 'filters.tsv')
    assert (tmp_path / 'filters.tsv').stat().st_size > 0


def test_matrix_strand_orientation_and_named_subset(tmp_path):
    bw = tmp_path / 's.bw'
    with pyBigWig.open(str(bw), 'w') as handle:
        handle.addHeader([('chr1', 1000)])
        handle.addEntries(['chr1', 'chr1'], [0, 500], ends=[500, 1000], values=[2.0, 4.0])
    bed = tmp_path / 'regions.bed'
    bed.write_text('chr1\t500\t600\tplus\t0\t+\nchr1\t400\t500\tminus\t0\t-\n')
    matrix = tmp_path / 'matrix.gz'
    run('computeMatrix', 'reference-point', '-S', bw, bw, '-R', bed,
        '-o', matrix, '-b', 100, '-a', 100, '--binSize', 50, '--referencePoint', 'TSS',
        '--sortRegions', 'keep', '--samplesLabel', 'sample1', 'sample3')
    with gzip.open(matrix, 'rt') as handle:
        header = json.loads(next(handle)[1:])
        values = [list(map(float, line.rstrip().split('\t')[6:])) for line in handle]
    assert header['sample_labels'] == ['sample1', 'sample3']
    assert values[0] == [2, 2, 4, 4] * 2
    assert values[1] == [4, 4, 2, 2] * 2
    run('computeMatrixOperations', 'subset', '-m', matrix, '--samples', 'sample3', '-o', tmp_path / 'subset.gz')
    with gzip.open(tmp_path / 'subset.gz', 'rt') as handle:
        assert json.loads(next(handle)[1:])['sample_labels'] == ['sample3']
    run('bigwigAverage', '-b', bw, bw, '-o', tmp_path / 'mean.bw', '--scaleFactors', '1:0.5', '--binSize', 50)
    with pyBigWig.open(str(tmp_path / 'mean.bw')) as handle:
        assert handle.values('chr1', 100, 101)[0] == pytest.approx(1.5)
    run('bigwigCompare', '-b1', bw, '-b2', bw, '-o', tmp_path / 'ratio.bw', '--operation', 'log2', '--fixedStep')
    with pyBigWig.open(str(tmp_path / 'ratio.bw')) as handle:
        assert handle.values('chr1', 100, 101)[0] == 0
    run('multiBigwigSummary', 'BED-file', '-b', bw, bw, '--BED', bed, '-o', tmp_path / 'summary.npz')
    # Summary output is genomic order, not the original BED row order.
    assert np.array_equal(np.load(tmp_path / 'summary.npz')['matrix'], [[2, 2], [4, 4]])
    run('computeMatrix', 'scale-regions', '-S', bw, '-R', bed, '-o', tmp_path / 'scaled.gz',
        '-m', 100, '--binSize', 50, '--sortRegions', 'keep')
    with gzip.open(tmp_path / 'scaled.gz', 'rt') as handle:
        next(handle)
        values = [list(map(float, line.rstrip().split('\t')[6:])) for line in handle]
    assert values == [[4, 4], [2, 2]]


@pytest.mark.skipif(shutil.which('samtools') is None, reason='external samtools not installed')
def test_all_generated_workflows_execute_on_tiny_paired_inputs(tmp_path):
    for idx, name in enumerate(('Input', 'ChIP1', 'ChIP2')):
        make_bam(tmp_path / f'{name}.bam', duplicate=True, variable=idx)
    bed = tmp_path / 'genes.bed'
    bed.write_text(''.join(f'chr1\t{i * 9000}\t{i * 9000 + 1000}\tg{i}\t0\t{"+" if i % 2 else "-"}\n' for i in range(1, 10)))
    common = {'input_bam': 'Input.bam', 'chip_bam': 'ChIP1.bam', 'chip_bams': ['ChIP1.bam', 'ChIP2.bam'],
              'rnaseq_bam': 'ChIP1.bam', 'atac_bam': 'ChIP1.bam', 'genes_bed': 'genes.bed', 'peaks_bed': 'genes.bed',
              'threads': 1, 'genome_size': 100000}
    for workflow, generator in [('chipseq_qc', workflow_generator.generate_chipseq_qc_workflow),
                                ('chipseq_analysis', workflow_generator.generate_chipseq_analysis_workflow),
                                ('rnaseq_coverage', workflow_generator.generate_rnaseq_coverage_workflow),
                                ('atacseq', workflow_generator.generate_atacseq_workflow)]:
        script = tmp_path / f'{workflow}.sh'
        generator(str(script), {**common, 'output_dir': workflow})
        result = run('bash', script, cwd=tmp_path)
        assert 'complete' in result.stdout
        output = tmp_path / workflow
        assert any(output.iterdir())
        for image in output.glob('*.png'):
            assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        for bigwig in output.glob('*.bw'):
            assert validate_files.check_bigwig_file(bigwig)[0]
    assert validate_files.check_bam_file(tmp_path / 'atacseq' / 'atacseq_shifted.bam')[0]


def test_rpgc_templates_require_explicit_reference_size(tmp_path):
    result = subprocess.run([sys.executable, str(SKILL_ROOT / 'scripts' / 'workflow_generator.py'),
                             'chipseq_analysis', '-o', str(tmp_path / 'workflow.sh')], capture_output=True, text=True)
    assert result.returncode != 0
    assert '--genome-size is required' in result.stderr
