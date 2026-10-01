# Tested source runtime

MAGeCK 0.5.9.5 was downloaded from the official SourceForge release and built on macOS ARM64
with Python 3.11, NumPy 1.26.4, SciPy 1.13.1, setuptools 69.5.1, and the system C++ compiler.
`count`, paired/unpaired `test` (including compiled RRA), control normalization, sparse-normalization
fallbacks, and a small `mle` smoke ran successfully on review date 2026-10-01. MAGeCK is not a PyPI
dependency installed by this repository's isolated test environment; integration tests skip when the
executable is absent. Put the complete source/conda environment's `bin` on PATH to run them.

The following is the tested installation pattern; choose an environment directory outside the skill.

```bash
uv venv --python 3.11 mageck-env
uv pip install --python mageck-env/bin/python numpy==1.26.4 scipy==1.13.1 setuptools==69.5.1
curl -fL 'https://sourceforge.net/projects/mageck/files/0.5/mageck-0.5.9.5.tar.gz/download' -o mageck.tar.gz
tar -xzf mageck.tar.gz
# This archive contains liulab-mageck-c491c3874dca, not a directory named mageck-0.5.9.5.
cd liulab-mageck-c491c3874dca
../mageck-env/bin/python setup.py install
cd ..
export PATH="$PWD/mageck-env/bin:$PATH"
mageck --version
mageck test --help
```

The upstream installation uses legacy setup.py and emits setuptools deprecation messages. Its
source package compiles RRA and mageckGSEA. A wrapper-only installation without these binaries
cannot perform gene ranking. Bioconda is another upstream-documented route, but was not exercised
for this skill. R/LaTeX rendering, copy-number correction, and realistic multi-factor MLE fits are
outside the tested integration surface. The MLE smoke used 30 genes, five guides each, two samples
per condition and one permutation round; this does not establish FDR calibration.

## Release and source review

On 2026-10-01 the [official release directory](https://sourceforge.net/projects/mageck/files/0.5/)
listed 0.5.9.5 (2021-12-01). Its freshly downloaded archive matched SHA-256
`b06a18036da63959cd7751911a46727aefe2fb1d8dd79d95043c3e3bdaf1d93a`.
The tested source tree is archive directory `liulab-mageck-c491c3874dca`. Runtime help and source
(`argsParser.py`, `mageckCount.py`, `mageckCountIO.py`, `mageckCountNorm.py`, `fileOps.py`, `crisprFunction.py`,
`mleargparse.py`, `mledesignmat.py`, `mleinstanceio.py`) resolve stale details in the wiki:

- The current `test` default is `--remove-zero both`, although the usage table still says `none`.
- Numeric sample names are unsafe: integer contrasts are treated as indices, and an all-numeric
  header may be read as counts. The helper requires nonnumeric names and an explicit header.
- `--control-sgrna` supplies the RRA null as well as an optional normalization reference. A control
  gene cannot mix control and non-control guide IDs, and at least two controls are required.
- Median and control-median normalization can fall back to totals; the helper extracts actual
  factors and fallback warnings from the execution log rather than reporting the request as fact.
- A named MLE design file controls count-column selection/order through its sample labels.

[MAGeCK Home](https://sourceforge.net/p/mageck/wiki/Home/) now points to the separate
[MAGeCK2 project](https://github.com/davidliwei/mageck2). Its PyPI package is `mageck2` (0.3.0 at
review), while the `mageck` PyPI JSON endpoint returned 404. MAGeCK2 is not exercised by this skill;
installing it does not verify the `mageck`/RRA runtime used here. No remote analysis API is used.
