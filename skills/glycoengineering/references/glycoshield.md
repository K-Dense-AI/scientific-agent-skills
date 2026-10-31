# GlycoSHIELD source workflow

Reviewed 2026-10-01 against upstream commit
[`f1ca31aa88a2902ca1962edc7571e8b3eb14d933`](https://gitlab.mpcdf.mpg.de/dioscuri-biophysics/glycoshield-md/-/tree/f1ca31aa88a2902ca1962edc7571e8b3eb14d933).
No release tags were returned; setup.py identifies version 0.1. The PyPI
`glycoshield` package endpoint returned 404. Use the source checkout, not an
unrelated or assumed PyPI distribution.

## Installation and input preparation

Illustrative installation, not performed in this refresh:

```bash
git clone https://gitlab.mpcdf.mpg.de/dioscuri-biophysics/glycoshield-md.git
cd glycoshield-md
git checkout f1ca31aa88a2902ca1962edc7571e8b3eb14d933
uv venv .venv
uv pip install --python .venv/bin/python -e .
```

Upstream declares numpy, scipy, matplotlib and MDAnalysis without version pins.
Record a working environment; compatibility with the newest stack is unverified.
SASA requires a working `gmx` executable from GROMACS on `PATH`, installed
separately. Obtain only the glycan conformer libraries needed, following the
upstream downloader/library instructions; no library download was performed here.
Run from a directory containing only the intended inputs and new outputs; the
SASA code uses fixed scratch filenames in its output directory.

The source input file has one whitespace-separated line per site, with comma
lists within the alignment fields:

```text
A 462,463,464 1,2,3 GLYCAN_LIBRARY/Man5.pdb GLYCAN_LIBRARY/Man5_dt1000.xtc A_463.pdb A_463.xtc
A 491,492,493 1,2,3 GLYCAN_LIBRARY/Man5.pdb GLYCAN_LIBRARY/Man5_dt1000.xtc A_492.pdb A_492.xtc
```

These are upstream N-cadherin examples, not universal residue numbers. Align the
protein chain's flanking residue triplet to the library's corresponding triplet.
Verify PDB residue identifiers, missing residues, insertion codes and glycan
attachment geometry explicitly. FASTA offsets are not PDB residue IDs. Preserve
library identity and frame sampling; accepted counts depend on the library and
clash cutoff and are not measured occupancy or a thermodynamic probability.

## CLI forwarding defect and direct API

At the reviewed commit, `GlycoSHIELD.py:run_glycoshield` accepts threshold, mode,
zmin/zmax, dryrun, shuffle_sugar and ignorewarn, but passes **none of them** into
`glycoshield(...)`. A source-execution check with a stub constructor confirmed the
omission. Consequently, `--mode All --threshold 0.7 --dryrun` still uses class
defaults CG / 3.5 Å / dryrun=False. Do not rely on its parsed options.

Use the implementation directly. This call was signature-checked and exercised
with a mock constructor; scientific execution remains **illustrative**:

```python
from glycoshield import glycoshield

gs = glycoshield(
    protpdb="protein.pdb", protxtc=None, inputfile="sequons_input",
    threshold=0.7, mode="All", zmin=None, zmax=None,
    dryrun=True, shuffle_sugar=False, ignorewarn=False,
    skip=1, path="./",
)
accepted_counts = gs.run()
print(accepted_counts)
```

`All` checks against all protein atoms and the upstream recommended cutoff is
0.7 Å; `CG` checks Cα atoms and pairs with 3.5 Å. These are clash heuristics, not
interchangeable physical models. A direct-API dry run still performs calculations
but suppresses the principal ensemble output. Check the library, counts and
geometry before rerunning explicitly with `dryrun=False` in a dedicated output
directory; ancillary behavior was not tested end-to-end. The current `get_sugar_frames`
shuffles a discarded list, so `shuffle_sugar=True` does not randomize the returned
frame order; the example explicitly leaves it disabled.

## SASA analysis

After real PDB/XTC ensembles exist, use matching per-site lists and identical
protein atom order. Probe radii are in **nm**, unlike clash cutoffs in Å. Three
source defects affect the command-line route:

- `--probelist` defaults to a float, then `.split(',')` is called on it.
- `GMXTEST` passes literal `|`, `grep` and `GROMACS version` tokens to `gmx`,
  because its `Popen` call does not invoke a shell.
- `--endframe` / the library's `maxframe` is passed to `gmx sasa -e`, which is an
  **end time in ps**, not a conformer count. Check XTC timestamps before setting it.
  See the [GROMACS SASA options](https://manual.gromacs.org/current/onlinehelp/gmx-sasa.html).

Illustrative direct call with a local, checked version probe replacing the broken
upstream preflight; only signature and mocked argument forwarding were tested:

```python
import subprocess
import glycoshield.lib as gs_lib


def checked_gromacs():
    subprocess.run(["gmx", "--version"], check=True, capture_output=True, text=True)


original_check = gs_lib.GMXTEST
try:
    gs_lib.GMXTEST = checked_gromacs
    results = gs_lib.glycosasa(
        pdblist=["A_463.pdb", "A_492.pdb"],
        xtclist=["A_463.xtc", "A_492.xtc"],
        plottrace=True, probelist=[0.14, 0.25], ndots=24,
        mode="max", keepoutput=False, maxframe=100.0,
        path="./", run_parallel=False,
    )
finally:
    gs_lib.GMXTEST = original_check
```

The 100.0 ps end time is an example, not a validated frame selection. Keep
`plottrace=True`: the reviewed implementation otherwise uses an uninitialized
`residues` variable. `max` selects the maximum of the separate per-glycan relative
SASA reductions at each residue; it is not the joint shielding of all simultaneous
glycans. The PDB B-factor column holds this reduction multiplied by 100. Its
occupancy column marks whether bare-protein SASA was nonzero, **not biological
glycan occupancy**. Check probe/conformer convergence and finite outputs.
Protein motion, glycoform heterogeneity and library coverage remain separate
uncertainties. Full scientific execution and current GROMACS compatibility were
not established by the source/mocked checks.

Sources inspected: upstream [README](https://gitlab.mpcdf.mpg.de/dioscuri-biophysics/glycoshield-md/-/blob/f1ca31aa88a2902ca1962edc7571e8b3eb14d933/README.md),
[CLI](https://gitlab.mpcdf.mpg.de/dioscuri-biophysics/glycoshield-md/-/blob/f1ca31aa88a2902ca1962edc7571e8b3eb14d933/GlycoSHIELD.py),
[implementation](https://gitlab.mpcdf.mpg.de/dioscuri-biophysics/glycoshield-md/-/blob/f1ca31aa88a2902ca1962edc7571e8b3eb14d933/glycoshield/lib.py),
[SASA CLI](https://gitlab.mpcdf.mpg.de/dioscuri-biophysics/glycoshield-md/-/blob/f1ca31aa88a2902ca1962edc7571e8b3eb14d933/GlycoSASA.py),
and [setup.py](https://gitlab.mpcdf.mpg.de/dioscuri-biophysics/glycoshield-md/-/blob/f1ca31aa88a2902ca1962edc7571e8b3eb14d933/setup.py).
