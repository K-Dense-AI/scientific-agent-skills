# MATLAB and Python Integration

The executable planner is pinned to MATLAB R2026a, reviewed on 2026-10-01.
Calling Python from MATLAB and calling MATLAB from Python are different
interfaces with different process, data, and license behavior.

Current R2026b documentation lists CPython 3.10-3.14. At review time, PyPI
still publishes `matlabengine==26.1.12` for R2026a, not R2026b. For R2026b use
the Engine distributed with that installed release and verify its requirements;
the bundled planner deliberately rejects R2026b rather than applying the
R2026a package pin. No MATLAB or Engine runtime was started in this review.

## Exact R2026a compatibility

MathWorks' support table lists 64-bit CPython **3.9, 3.10, 3.11, 3.12,
and 3.13** for:

- MATLAB Interface to Python;
- MATLAB Engine for Python;
- MATLAB Compiler SDK for Python;
- MATLAB Production Server Client Library.

The current MathWorks-maintained PyPI release reviewed here is
`matlabengine==26.1.12`, released 2026-05-08. It requires MATLAB R2026a.
Do not install a floating latest package for a reproducible environment.

```bash
uv pip install "matlabengine==26.1.12"
```

Installation does not include MATLAB or grant a license. Engine requires an
installed R2026a on the same machine; MATLAB Runtime alone is insufficient.
The Python architecture must match MATLAB.

R2026a also ships a preinstalled Engine distribution at the single named path:

```text
<matlabroot>/extern/engines/python/dist
```

Add only that confirmed path to the selected environment when using this
method. Do not print or upload the full `PATH`, `PYTHONPATH`, environment,
license configuration, home directory, or credentials.

## Plan compatibility without execution

```bash
python scripts/plan_python_compatibility.py \
  --matlab-release R2026a \
  --python-version 3.13 \
  --engine-version 26.1.12
```

The planner uses a bundled dated support table. It does not import
`matlab.engine`, inspect the environment, locate installations, start MATLAB,
or check out a license. `--include-launch-snippet` adds an explicitly labeled
launch example to the JSON plan but still does not execute it.

## Calling Python from MATLAB

Review and pin one interpreter before any `py.*` access:

```matlab
environment = pyenv( ...
    Version="/reviewed/venv/bin/python", ...
    ExecutionMode="OutOfProcess");
```

On Windows, a registered version can be selected by version, but a full named
executable is clearer. On macOS/Linux, use the full executable. The Python
build architecture must match MATLAB. MATLAB does not support CPython from the
Microsoft Store.

Interpreter switching:

- in-process: restart MATLAB before changing the loaded interpreter;
- out-of-process: `terminate(pyenv)` can stop the external interpreter, after
  which `pyenv` can be reconfigured.

Out-of-process isolates interpreter crashes and allows reload, but it is not a
security sandbox. Data plus transfer metadata are limited to 2 GiB per
out-of-process transfer. Python modules can perform arbitrary process, file,
network, native, and credential operations.

Never run untrusted `py.*`, `pyrun`, `pyrunfile`, Python modules, wheels, or
requirements files. `pyrun` and `pyrunfile` are dynamic code execution
surfaces.

## Calling MATLAB from Python

Starting Engine is explicit execution:

```python
import matlab.engine

engine = matlab.engine.start_matlab()
try:
    result = engine.sqrt(16.0)
finally:
    engine.quit()
```

`start_matlab()` creates a MATLAB process, can execute startup code, and can
check out a MATLAB license. Never call it merely to probe availability.
Review startup paths/actions and confirm entitlement first.

Engine transfers are limited to 2 GB including supporting information.
Python `None`, Python class objects, and recursive containers are unsupported
Engine input types. These limits are separate from MATLAB-to-Python conversion.

`connect_matlab()` connects to a deliberately shared local MATLAB session;
`find_matlab()` lists shared sessions. Sharing changes the trust boundary and
must be explicitly approved. Do not connect to an unknown session.

Only add narrow reviewed paths:

```python
engine.addpath("/reviewed/project/src", nargout=0)
value = engine.analyzeSignal(
    matlab.double([[1.0], [2.0], [3.0]]),
    nargout=1,
)
```

Do not use recursive path additions. Pass fixed function names, not text to
`eval`, and set `nargout` deliberately. Redirect output to bounded
`io.StringIO` only when needed; logs can contain paths or data.

## MATLAB-to-Python conversion in R2026a

Scalar automatic mappings include:

| MATLAB | Python |
|---|---|
| real `double`/`single` | `float` by default; type hints can select `int` |
| complex float | `complex` |
| integer scalar | `int` |
| logical scalar | `bool` |
| string scalar/character vector | `str` |
| missing string through `py.str` | Python string `"None"`, not the Python `None` singleton |
| `dictionary`/scalar `struct` | `dict` |
| `table`/`timetable` | pandas `DataFrame` |
| `datetime` | `datetime.datetime` |
| `duration` | `datetime.timedelta` |

With NumPy available, numeric/logical MATLAB arrays convert to NumPy arrays
with corresponding precision/sign/complex dtype. Without NumPy, numeric arrays
use Python buffer/memoryview behavior. Since R2025a, array conversion behavior
changed; test code migrated from older vector `array.array` assumptions.

R2026a additions:

- MATLAB string vectors automatically convert to Python lists;
- `pystringarray` converts MATLAB string arrays to NumPy `StringDType`
  arrays;
- missing string entries need explicit round-trip tests.

The table above concerns Python called **from MATLAB**. Engine calls from
Python use their own conversion table and `matlab.*` array classes; do not
assume pandas, datetime, or dictionary conversions are symmetric. R2026b adds
GPU interchange through CuPy, DLPack, and PyTorch with Parallel Computing
Toolbox; those features are outside the R2026a planner's compatibility claim.

No automatic conversion is documented for multidimensional character/cell
arrays or M-by-N string arrays where both dimensions exceed one. Sparse
arrays, nonscalar structure arrays, categorical arrays, `containers.Map`,
MATLAB objects, and metadata classes are unsupported in the MATLAB-to-Python
interface.

## Python-to-MATLAB conversion

MATLAB automatically converts selected scalar Python returns. Other values use
explicit conversion:

| Python value | MATLAB conversion |
|---|---|
| `py.str` | `string` or `char` |
| Python numeric scalar | `double`, `single`, or integer constructors |
| `py.bytes` | `uint8` |
| `py.numpy.ndarray` | matching MATLAB numeric class or `string` where supported |
| `py.list`/`py.tuple` | numeric/logical/string/cell conversion when homogeneous/compatible |
| mapping protocol / `py.dict` | `dictionary` or `struct` |
| pandas `DataFrame` | `table`/`timetable` with documented conversion |
| Python datetime/timedelta/NumPy time | MATLAB `datetime`/`duration` conversions |

Always test:

- rank and row/column orientation;
- C-order versus column-major interpretation;
- dtype width/sign and complex values;
- `NaN`, `Inf`, `None`, `NaT`, missing strings, and categorical values;
- table index versus timetable row times;
- time zones and units;
- dictionary key restrictions and column-name normalization;
- copies versus shared/buffer-backed memory.

Do not flatten an array to "fix" a shape mismatch without recording the
ordering contract.

## MATLAB Engine array classes

The `matlab` Python package provides MATLAB array classes such as
`matlab.double`, `matlab.single`, signed/unsigned integer classes, and
`matlab.logical`. These are for Engine calls, not general NumPy replacements.

```python
column = matlab.double([[1.0], [2.0], [3.0]])
matrix = matlab.double([[1.0, 2.0], [3.0, 4.0]])
```

Construct the intended dimensions explicitly. Function outputs can be Engine
proxy/object types; convert only through documented APIs.

## Serialization and exchange

- MATLAB does not support saving Python objects into MAT files.
- Never use Python pickle for MATLAB exchange. Pickle deserialization executes
  attacker-controlled behavior.
- For simple data, prefer schema-documented CSV/JSON/Parquet/HDF5.
- For trusted MATLAB arrays, use MAT with explicit version and inventory it
  before loading in another process.
- SciPy `loadmat` is not used by this skill's inventory. It can deserialize
  complex structures and is not a safety scanner.

## Compiler SDK distinction

MATLAB Compiler SDK for Python packages are not MATLAB Engine:

- building requires MATLAB, MATLAB Compiler SDK, and source dependencies;
- deployed components use a compatible MATLAB Runtime under applicable terms;
- generated Python packages are not supported as Python modules called back
  from MATLAB's Python interface;
- Engine itself requires full installed MATLAB, not Runtime.

Confirm product, target release, platform, package, runtime, and license terms.

## Troubleshooting without broad disclosure

Collect only named facts:

- MATLAB release/update and architecture;
- one Python executable path and `major.minor`;
- Engine package version;
- selected `pyenv` status/mode (not all environment values);
- one failing function, input classes/shapes, and redacted traceback;
- whether NumPy/pandas are required and their pinned versions.

Do not ask for `env`, `set`, complete `PATH`, complete `sys.path`, license
files, tokens, home-directory listings, or credentials.

## Sources (reviewed 2026-10-01)

- [Python Compatibility by MATLAB Release](https://www.mathworks.com/support/requirements/python-compatibility.html)
- [Install MATLAB Engine API for Python](https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html)
- [MathWorks `matlabengine` 26.1.12 package](https://pypi.org/project/matlabengine/26.1.12/)
- [Call MATLAB from Python](https://www.mathworks.com/help/matlab/matlab-engine-for-python.html)
- [Get Started with MATLAB Engine](https://www.mathworks.com/help/matlab/matlab_external/get-started-with-matlab-engine-for-python.html)
- [Configure Python for MATLAB](https://www.mathworks.com/help/matlab/matlab_external/install-supported-python-implementation.html)
- [Call Python from MATLAB](https://www.mathworks.com/help/matlab/call-python-libraries.html)
- [Pass Data from MATLAB to Python](https://www.mathworks.com/help/matlab/matlab_external/passing-data-to-python.html)
- [Pass Data from Python to MATLAB](https://www.mathworks.com/help/matlab/matlab_external/pass-data-between-matlab-and-python-from-python.html)
- [Python Interface Limitations](https://www.mathworks.com/help/matlab/matlab_external/limitations-to-python-support.html)
- [MATLAB Engine Limitations](https://www.mathworks.com/help/matlab/matlab_external/limitations-to-the-matlab-engine-for-python.html)
- [Current release highlights](https://www.mathworks.com/products/new_products/latest_features.html)
