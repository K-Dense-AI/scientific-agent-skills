#!/usr/bin/env python3
"""Validate RELION SPA inputs, run refinement/postprocessing, and inspect half-map FSC."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import re
import subprocess


def read_map(path: Path, max_voxels: int | None = None):
    import mrcfile
    import numpy as np
    with mrcfile.mmap(path, permissive=False) as handle:
        if max_voxels is not None and handle.data.size > max_voxels:
            raise ValueError("Python diagnostic limited to 256-cubed maps; use relion_image_handler --fsc for larger maps")
        data = handle.data.copy()
        voxel = tuple(float(handle.voxel_size[axis]) for axis in ('x', 'y', 'z'))
        origin = tuple(float(handle.header.origin[axis]) for axis in ('x', 'y', 'z'))
        axes = tuple(int(handle.header[axis]) for axis in ('mapc', 'mapr', 'maps'))
    if data.ndim != 3 or len(set(data.shape)) != 1 or min(data.shape) < 4 or data.shape[0] % 2:
        raise ValueError(f'{path}: expected an even-sized cubic 3D map')
    if not np.isfinite(data).all() or not all(math.isfinite(x) for x in voxel + origin):
        raise ValueError(f'{path}: nonfinite map or header')
    if min(voxel) <= 0 or not np.allclose(voxel, voxel[0], rtol=1e-5):
        raise ValueError(f'{path}: positive isotropic voxel size required')
    if axes != (1, 2, 3):
        raise ValueError(f'{path}: noncanonical map axes; explicitly reorder before analysis')
    return data, voxel[0], origin


def validate_star(path: Path, project: Path, check_stacks: bool = True) -> dict:
    import mrcfile
    import numpy as np
    import starfile
    blocks = starfile.read(path, always_dict=True)
    if not {'optics', 'particles'}.issubset(blocks):
        raise ValueError('Requires RELION 3.1+ data_optics and data_particles blocks')
    optics, particles = blocks['optics'], blocks['particles']
    needed_optics = {'rlnOpticsGroup', 'rlnVoltage', 'rlnSphericalAberration', 'rlnAmplitudeContrast',
                     'rlnImagePixelSize', 'rlnImageSize', 'rlnImageDimensionality'}
    needed_particles = {'rlnOpticsGroup', 'rlnImageName', 'rlnDefocusU', 'rlnDefocusV', 'rlnDefocusAngle'}
    if not needed_optics.issubset(optics.columns) or not needed_particles.issubset(particles.columns):
        raise ValueError('Missing optics/acquisition/CTF columns for a 2D-particle SPA refinement')
    if len(optics) == 0 or len(particles) == 0 or optics.rlnOpticsGroup.duplicated().any():
        raise ValueError('Empty tables or duplicate optics group IDs')
    for frame, columns in [(optics, needed_optics), (particles, needed_particles - {'rlnImageName'})]:
        for column in columns:
            values = np.asarray(frame[column], dtype=float)
            if not np.isfinite(values).all():
                raise ValueError(f'Nonfinite values in {column}')
    if any(optics.rlnOpticsGroup <= 0) or any(optics.rlnOpticsGroup % 1):
        raise ValueError('Optics group IDs must be positive integers')
    if not set(particles.rlnOpticsGroup).issubset(set(optics.rlnOpticsGroup)):
        raise ValueError('Particle references an undefined optics group')
    if any(optics.rlnImagePixelSize <= 0) or any(optics.rlnVoltage <= 0) or any(optics.rlnSphericalAberration < 0):
        raise ValueError('Pixel size/voltage must be positive and spherical aberration nonnegative')
    if any((optics.rlnAmplitudeContrast < 0) | (optics.rlnAmplitudeContrast >= 1)):
        raise ValueError('Amplitude contrast must be in [0,1)')
    if any(optics.rlnImageDimensionality != 2) or any(optics.rlnImageSize < 4) or any(optics.rlnImageSize % 2):
        raise ValueError('This runner requires 2D particles with an even box size >=4')
    if any(particles.rlnDefocusU <= 0) or any(particles.rlnDefocusV <= 0):
        raise ValueError('Underfocus values must be positive Angstroms; verify CTF import units/sign')
    if particles.rlnImageName.duplicated().any():
        raise ValueError('Duplicate particle image references can leak between half sets')
    subsets = None
    if 'rlnRandomSubset' in particles:
        values = set(particles.rlnRandomSubset)
        if values != {1, 2}:
            raise ValueError('Existing rlnRandomSubset must contain both half sets, encoded 1 and 2')
        subsets = {str(k): int(v) for k, v in particles.rlnRandomSubset.value_counts().items()}
    groups = optics.set_index('rlnOpticsGroup')
    stack_cache, canonical_images = {}, set()
    for row in particles.itertuples(index=False):
        match = re.fullmatch(r'([1-9][0-9]*)@(.+)', str(row.rlnImageName))
        if not match:
            raise ValueError(f'Expected 1-based index@stack.mrcs: {row.rlnImageName}')
        index, stack_name = int(match[1]), match[2]
        stack = Path(stack_name)
        stack = stack if stack.is_absolute() else project / stack
        identity = (index, stack.resolve())
        if identity in canonical_images:
            raise ValueError('Duplicate particle image after path normalization')
        canonical_images.add(identity)
        if check_stacks:
            if stack not in stack_cache:
                with mrcfile.mmap(stack, permissive=False) as handle:
                    shape = handle.data.shape
                    # MRC may expose a single image as 2D rather than a stack of length one.
                    stack_cache[stack] = ((1, *shape) if len(shape) == 2 else shape)
            shape = stack_cache[stack]
            box = int(groups.loc[row.rlnOpticsGroup, 'rlnImageSize'])
            if len(shape) != 3 or index > shape[0] or shape[1:] != (box, box):
                raise ValueError(f'Particle stack index/box does not agree with optics: {row.rlnImageName}')
    warnings = []
    if any((optics.rlnVoltage < 60) | (optics.rlnVoltage > 400)):
        warnings.append('Unusual voltage; confirm kV rather than V')
    if any(particles.rlnDefocusU > 100000) or any(particles.rlnDefocusV > 100000):
        warnings.append('Defocus exceeds 10 micrometers; inspect CTF fits and units')
    return {'particles': len(particles), 'optics_groups': len(optics), 'half_sets': subsets,
            'pixel_sizes_angstrom': sorted(set(float(x) for x in optics.rlnImagePixelSize)),
            'box_sizes': sorted(set(int(x) for x in optics.rlnImageSize)), 'warnings': warnings}


def check_halves(first: Path, second: Path, mask: Path | None = None, max_voxels: int | None = None):
    import numpy as np
    a, pixel, origin = read_map(first, max_voxels)
    b, other_pixel, other_origin = read_map(second, max_voxels)
    if a.shape != b.shape or not np.isclose(pixel, other_pixel) or not np.allclose(origin, other_origin):
        raise ValueError('Half maps disagree in grid, pixel size, or origin')
    if np.array_equal(a, b):
        raise ValueError('Half maps are identical; provide independent unfiltered half reconstructions')
    if np.std(a) == 0 or np.std(b) == 0:
        raise ValueError('Constant half map has no measurable signal')
    if mask:
        m, mp, mo = read_map(mask)
        if m.shape != a.shape or not np.isclose(pixel, mp) or not np.allclose(origin, mo):
            raise ValueError('Mask grid differs from half maps')
        if m.min() < 0 or m.max() > 1 or m.max() == m.min():
            raise ValueError('Mask must be nonconstant and lie in [0,1]')
        if not np.any((m > 0) & (m < 1)):
            raise ValueError('Mask has no soft edge; generate a soft solvent mask')
    return a, b, pixel


def fsc(first: Path, second: Path, output: Path) -> dict:
    import numpy as np
    a, b, pixel = check_halves(first, second, max_voxels=256**3)
    n = a.shape[0]
    fa, fb = np.fft.rfftn(a), np.fft.rfftn(b)
    z, y, x = np.ogrid[-n//2:n-n//2, -n//2:n-n//2, 0:n//2+1]
    shells = np.floor(np.sqrt(z*z+y*y+x*x)+0.5).astype(int)
    # Shift only the fully represented axes; weight interior rFFT x planes twice.
    fa, fb = np.fft.fftshift(fa, axes=(0,1)), np.fft.fftshift(fb, axes=(0,1))
    weights = np.ones(fa.shape); weights[:,:,1:-1] = 2
    cross = np.bincount(shells.ravel(), weights=(weights*(fa*np.conj(fb)).real).ravel())
    power_a = np.bincount(shells.ravel(), weights=(weights*abs(fa)**2).ravel())
    power_b = np.bincount(shells.ravel(), weights=(weights*abs(fb)**2).ravel())
    counts = np.bincount(shells.ravel(), weights=weights.ravel())
    denominator = np.sqrt(power_a*power_b)
    values = np.divide(cross, denominator, out=np.full_like(cross, np.nan), where=denominator>0)
    rows = [{'shell': k, 'frequency_inv_angstrom': k/(n*pixel),
             'fsc': float(values[k]) if np.isfinite(values[k]) else None,
             'fourier_samples': int(counts[k])} for k in range(n//2+1)]
    crossing = None
    for previous, current in zip(rows[1:], rows[2:]):
        a_fsc, b_fsc = previous['fsc'], current['fsc']
        if a_fsc is not None and b_fsc is not None and a_fsc >= 0.143 > b_fsc:
            frequency = previous['frequency_inv_angstrom'] + (0.143-a_fsc)/(b_fsc-a_fsc)/(n*pixel)
            crossing = 1/frequency
            break
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter='\t')
        writer.writeheader(); writer.writerows(rows)
    return {'unmasked_diagnostic_fsc_0143_angstrom': crossing, 'nyquist_angstrom': 2*pixel,
            'warning': 'Diagnostic unmasked FSC; use corrected RELION postprocessing FSC for reported global resolution',
            'shells': len(rows)}


def run_native_command(command: list[str], output: Path, project: Path, executable: str) -> None:
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use an empty output directory; preserve prior jobs for restart/provenance')
    version = subprocess.run([executable, '--version'], capture_output=True, text=True, check=True)
    version_text = version.stdout + version.stderr
    if '5.0.1' not in version_text:
        raise ValueError('This runner targets RELION5.0.1; verify the installed executable before adapting it')
    output.mkdir(parents=True, exist_ok=True)
    (output/'version.txt').write_text(version_text)
    (output/'command.json').write_text(json.dumps(command, indent=2)+'\n')
    with (output/'run.log').open('w') as log:
        subprocess.run(command, cwd=project, stdout=log, stderr=subprocess.STDOUT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    star = sub.add_parser('validate-star')
    star.add_argument('star', type=Path); star.add_argument('--project', type=Path, default=Path.cwd())
    star.add_argument('--metadata-only', action='store_true', help='Explicitly omit opening particle stacks')
    comparison = sub.add_parser('fsc')
    comparison.add_argument('half1', type=Path); comparison.add_argument('half2', type=Path)
    comparison.add_argument('--output', type=Path, required=True)
    refine = sub.add_parser('refine')
    refine.add_argument('--star', type=Path, required=True); refine.add_argument('--reference', type=Path, required=True)
    refine.add_argument('--diameter', type=float, required=True, help='Particle diameter in Angstroms')
    refine.add_argument('--symmetry', default='C1'); refine.add_argument('--initial-lowpass', type=float, default=40.0)
    refine.add_argument('--threads', type=int, default=1); refine.add_argument('--executable', default='relion_refine_mpi')
    refine.add_argument('--mpirun', default='mpirun'); refine.add_argument('--mpi-ranks', type=int, default=3)
    refine.add_argument('--seed', type=int, default=1)
    refine.add_argument('--project', type=Path, default=Path.cwd()); refine.add_argument('--output', type=Path, required=True)
    post = sub.add_parser('postprocess')
    post.add_argument('--half1', type=Path, required=True); post.add_argument('--half2', type=Path, required=True)
    post.add_argument('--mask', type=Path, required=True); post.add_argument('--output', type=Path, required=True)
    post.add_argument('--executable', default='relion_postprocess')
    args = parser.parse_args()
    try:
        if args.action == 'validate-star':
            result = validate_star(args.star, args.project, not args.metadata_only)
        elif args.action == 'fsc':
            result = fsc(args.half1, args.half2, args.output)
        elif args.action == 'refine':
            result = validate_star(args.star, args.project)
            reference, pixel, _ = read_map(args.reference)
            if result['box_sizes'] != [reference.shape[0]] or any(abs(p-pixel)>1e-5*pixel for p in result['pixel_sizes_angstrom']):
                raise ValueError('Reference box/pixel size must match all particle optics groups for this bounded runner')
            if not 0 < args.diameter < reference.shape[0]*pixel or args.initial_lowpass < 2*pixel or args.threads<1 or args.mpi_ranks<3 or args.mpi_ranks%2 == 0:
                raise ValueError('Invalid diameter, lowpass, threads or MPI ranks (use odd ranks >=3)')
            if not re.fullmatch(r'(?:[CD][1-9][0-9]*|[TO]|I[1-4]?)', args.symmetry):
                raise ValueError('Use an explicit supported RELION point-group symmetry such as C1, D2, O, I1')
            command = [args.mpirun, '-np', str(args.mpi_ranks), args.executable, '--o', str(args.output.resolve()/'run'), '--i', str(args.star.resolve()),
                       '--ref', str(args.reference.resolve()), '--auto_refine', '--split_random_halves', '--ctf',
                       '--firstiter_cc', '--ini_high', str(args.initial_lowpass), '--sym', args.symmetry,
                       '--particle_diameter', str(args.diameter), '--flatten_solvent', '--zero_mask',
                       '--oversampling', '1', '--healpix_order', '2', '--auto_local_healpix_order', '4',
                       '--offset_range', '5', '--offset_step', '2', '--j', str(args.threads), '--random_seed', str(args.seed)]
            run_native_command(command, args.output.resolve(), args.project.resolve(), args.executable)
            if not all((args.output/f'run_half{k}_class001_unfil.mrc').is_file() for k in (1,2)):
                raise ValueError('Refinement exited without converged unfiltered half maps; inspect run.log/optimiser')
            result['refined_particles'] = validate_star(args.output/'run_data.star', args.project)
            result['runtime_warnings'] = list(dict.fromkeys(line.split('WARNING:', 1)[1].strip()
                for line in (args.output/'run.log').read_text().splitlines() if 'WARNING:' in line))
            result['command'] = command
        else:
            _, _, pixel = check_halves(args.half1, args.half2, args.mask)
            command = [args.executable, '--i', str(args.half1.resolve()), '--i2', str(args.half2.resolve()),
                       '--mask', str(args.mask.resolve()), '--angpix', str(pixel), '--o', str(args.output.resolve()/'postprocess')]
            run_native_command(command, args.output.resolve(), Path.cwd(), args.executable)
            if not (args.output/'postprocess.star').is_file():
                raise ValueError('Postprocess did not produce postprocess.star')
            result = {'command': command, 'pixel_size_angstrom': pixel}
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
