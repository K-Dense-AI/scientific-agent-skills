# Installation and environment

Reviewed for the released **PyHealth 2.0.2** wheel on 2026-09-30. Its metadata
requires Python `>=3.12,<3.14` and `torch~=2.7.1`, which excludes Torch 2.8 and later.
The tested macOS CPU environment resolved Torch 2.7.1 and torchvision 0.22.1.
Do not independently upgrade to the newest Torch or copy CUDA 12.1 commands from
older PyHealth examples. The [release metadata](https://pypi.org/project/pyhealth/2.0.2/)
is authoritative for this pin; `/en/latest/` documentation may describe newer source.

## Project setup

```bash
uv init --python 3.12 my-pyhealth-project
cd my-pyhealth-project
uv add 'pyhealth==2.0.2'
uv run python -c 'import torch; import importlib.metadata as m; print(m.version("pyhealth"), torch.__version__)'
```

Keep the generated lockfile. To run independently of the surrounding project's
Python requirement or dependencies:

```bash
uv run --no-project --isolated --python 3.12 --with pyhealth==2.0.2 python train.py
```

PyHealth 1.x has different datasets, task functions, schemas and model arguments.
Treat an existing 1.x environment as a separate migration; these examples target
2.0.2 and do not claim legacy compatibility.

## CPU, CUDA and MPS

Start with `Trainer(..., device="cpu")`. GPU selection at runtime does not determine
which wheel the installer downloads. For Linux CUDA/ROCm, choose a supported
**Torch 2.7.1 / torchvision 0.22.1** pair from the
[official previous-version installer](https://pytorch.org/get-started/previous-versions/),
and configure the package index appropriately for that environment. CUDA installation
was not tested in this review.

On Apple Silicon, check `torch.backends.mps.is_available()` before explicitly passing
`device="mps"`; the trainer's automatic device choice is CUDA-or-CPU. MPS operation
coverage is model-dependent and was not tested here. Optional graph models may need
`pyhealth[graph]==2.0.2`; pretrained text/image models can require separate downloads.

## Data access and layout

The public PyHealth `Synthetic_MIMIC-III` bucket is an unauthenticated collection of
CSV files, not a clinical production dataset or JSON API:
`https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/`.
The 2.0.2 loader tries configured `.csv.gz` files and then `.csv` alternatives.

Real MIMIC and eICU require the relevant PhysioNet access conditions (credentialing,
training and the data use agreement). Confirm access and release-specific conditions
on the [dataset landing page](https://physionet.org/content/mimiciv/); download through
an authorized channel and pass a local path. Do not embed access credentials in code.

For MIMIC-IV the root must contain `hosp/` **and** `icu/` because the default config
loads `hosp/patients.csv.gz`, `hosp/admissions.csv.gz`, `icu/icustays.csv.gz` plus
requested clinical tables. PyHealth's bundled MIMIC-IV config is labeled 2.2;
compatibility with all newer PhysioNet releases has not been established here.

```python
from pyhealth.datasets import MIMIC4EHRDataset
base = MIMIC4EHRDataset(
    root="./data/mimic-iv",  # contains hosp/ and icu/
    tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="./cache/mimic4", num_workers=1,
)
```

This constructor was checked against released source; restricted data parsing was
not executed. MIMIC-III uses lowercase selectors with uppercase source filenames.
OMOP uses its own bundled config: inspect it before assuming a particular CDM export
naming convention.

## Caching and small runs

`BaseDataset(cache_dir=None)` uses a persistent platform-specific user cache.
An explicit cache root gains a dataset UUID subdirectory; task/schema/processor
caches live below it. It is incorrect that omitting `cache_dir` always reparses.
The dataset cache key includes root, tables, dataset name and `dev`, but not the raw
file contents or full config contents. A task source edit need not invalidate the
task cache either. Choose a new cache root after changing those inputs and record
raw-data checksums/release and task version with each run.

`dev=True` limits BaseDataset processing to 1000 patients; it is not a guarantee
that only 1000 patients' CSV bytes are downloaded or scanned. Not every wrapper
exposes it: `SleepEDFDataset`, for example, has no `dev` or `cache_dir` parameter.
Use a `main()` guard for executable examples because dataset processing can spawn
workers on macOS/Windows. `num_workers=1` is a useful initial setting, not a guarantee
that every upstream library avoids subprocesses.
