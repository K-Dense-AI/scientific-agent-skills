# Tested source runtime

MAGeCK 0.5.9.5 was downloaded from the official SourceForge release and built on macOS ARM64
with Python 3.11, NumPy 1.26.4, SciPy 1.13.1, setuptools 69.5.1, and the system C++ compiler.
Both `count` and `test` (including compiled RRA) ran successfully. MAGeCK is not a PyPI dependency
installed by this repository's isolated test environment; those integration tests skip when the
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
for this skill. R/LaTeX rendering and MLE are outside the tested integration surface.
