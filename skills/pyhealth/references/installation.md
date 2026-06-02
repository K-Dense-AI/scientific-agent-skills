# Installation & Environment Setup

## Python version

PyHealth 2.0 requires **Python 3.12 or 3.13** (`>=3.12,<3.14`). The 1.x line supports Python 3.9+ if a downgrade is unavoidable.

## Recommended: uv

`uv` is the right tool here — it resolves and installs an order of magnitude faster than `pip`, and the lockfile makes runs reproducible across machines.

### New project

```bash
uv init my-pyhealth-project
cd my-pyhealth-project
uv python pin 3.12          # writes .python-version
uv add pyhealth             # resolves PyTorch + transitive deps, writes uv.lock
uv run python train.py      # runs inside the project venv
```

### Existing project

If a `pyproject.toml` already exists:

```bash
uv add pyhealth
```

If only `requirements.txt` exists, either migrate to `pyproject.toml` (preferred) or:

```bash
uv pip install pyhealth
```

### One-off scripts (no project)

```bash
uv run --with pyhealth python script.py
```

This creates an ephemeral environment, runs the script, and disposes the env. Good for quick experiments.

### Legacy 1.x

```bash
uv add 'pyhealth==1.16'     # last 1.x release, Python 3.9+
```

The 1.x and 2.x APIs differ — examples in this skill target 2.x. If a user is on 1.x, mention the version mismatch before debugging.

## GPU / CPU

PyHealth uses PyTorch under the hood. `uv add pyhealth` pulls the default PyTorch wheel, which is CPU-only on macOS and CUDA-enabled on Linux when CUDA is detected.

For explicit CUDA control on Linux:

```bash
# Replace cu121 with the user's CUDA version
uv add 'torch>=2.1' --index https://download.pytorch.org/whl/cu121
uv add pyhealth
```

For Apple Silicon, the default wheel works and uses MPS automatically when `Trainer(device="mps")` is set. CPU is the safe default if device behavior is unclear.

## Dataset access

### Synthetic MIMIC-III (no credentials)

PyHealth hosts a synthetic copy on Google Cloud Storage that any pipeline can hit directly:

```python
root="https://storage.googleapis.com/pyhealth/Synthetic_MIMIC-III/"
```

Use this for demos, tutorials, and any code that needs to run without PhysioNet credentials.

### Real MIMIC-III / MIMIC-IV / eICU

These require completed CITI training and a credentialed PhysioNet account. Once downloaded, point `root=` (or `ehr_root=` for MIMIC-IV) at the local directory containing the CSV/CSV.gz files:

```python
MIMIC4Dataset(
    ehr_root="/path/to/mimic-iv/2.2/hosp",   # not `root`
    tables=["diagnoses_icd", "procedures_icd", "prescriptions"],
    cache_dir="/path/to/cache",              # cache parsed output
)
```

### OMOP-CDM

Standardized schema; point `root=` at the directory containing CDM tables (`person.csv`, `condition_occurrence.csv`, etc.).

## Caching

The first call to `set_task()` is expensive (parses every CSV, applies the task to every patient). Set `cache_dir=` on the dataset constructor to persist the parsed result:

```python
MIMIC3Dataset(root=..., tables=..., cache_dir="./cache/mimic3")
```

Subsequent runs reload from disk in seconds. Without `cache_dir`, every run re-parses from scratch — fine for a one-off script, painful for iteration.

## `dev=True`

All dataset constructors accept `dev=True`, which loads only a small subset of patients. Use this while iterating on pipeline shape; switch to `dev=False` (the default) once the pipeline runs end-to-end.

## Common installation issues

- **"Could not find a version that satisfies the requirement pyhealth"** — Python version is < 3.12. Run `uv python pin 3.12` and reinstall.
- **CUDA OOM during `set_task`** — set_task is CPU-only; this is almost always a `Trainer` issue. Reduce `batch_size` or move to CPU temporarily to localize the problem.
- **Slow first run** — expected; set `cache_dir=` and re-run.
- **`KeyError` on table name** — table names are case-sensitive and dataset-specific. MIMIC-III uses uppercase (`DIAGNOSES_ICD`), MIMIC-IV uses lowercase (`diagnoses_icd`). Check the user's dataset version.
