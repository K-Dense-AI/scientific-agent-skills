# Error Handling and Troubleshooting

Common errors — invalid SMILES, missing API keys, HTTP/API failures, failed
workflows, and polling. Contracts were checked against `rowan-python` 3.2.0
source and offline tests; hosted calls below are illustrative.

## Actual exception classes

`rowan.ValidationError`, `rowan.AuthenticationError`, and
`rowan.InsufficientCreditsError` do **not** exist in SDK 3.2.0. Referencing one
in an `except` clause raises `AttributeError` while handling the original
failure.

| Failure | Exception |
|---|---|
| Missing coordinates, method/input mismatch, invalid settings | `ValueError` (including Pydantic validation errors), sometimes `TypeError` for unsupported objects |
| No configured API key | `ValueError` before sending a request |
| Authentication, credit, or other HTTP/API failure | `httpx.HTTPStatusError` |
| Failed/stopped workflow, draft result request, or no result data yet | `rowan.WorkflowError` |
| Network/timeout error | `httpx.RequestError` |
| Generic submission rejected by an account feature gate | `PermissionError` (named submitters can still raise `HTTPStatusError`) |

## Validate molecules before submission

```python
from rdkit import Chem

smiles = "CCCC(CC"
mol = Chem.MolFromSmiles(smiles)
if mol is None:
    raise ValueError(f"Invalid SMILES: {smiles}")
```

Input types vary by workflow. For example, descriptors require a molecule
with coordinates, while pKa requires a SMILES string only for `starling` or
`chemprop_nevolianis2025` (the default `gxtb_wagen2026` requires 3D):

```python
import rowan

try:
    rowan.submit_descriptors_workflow("CCO")
except ValueError as exc:
    print(f"Input problem: {exc}")

wf = rowan.submit_descriptors_workflow(rowan.Molecule.from_smiles("CCO"))
```

## Authentication and API errors

```python
import httpx
import rowan

try:
    user = rowan.whoami()
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 401:
        print("Bad or missing API key — check ROWAN_API_KEY")
    else:
        # Includes credit limits and other API failures; inspect the response.
        print(exc.response.status_code)  # Inspect response details privately; they can contain inputs.
        raise
```

The SDK treats an environment variable set to an **empty string** as present.
It can therefore send an empty credential instead of raising a missing-key
error locally. Check that `ROWAN_API_KEY` is non-empty without printing the key:

```python
import os

api_key = os.environ.get("ROWAN_API_KEY")
if not api_key:
    raise RuntimeError("ROWAN_API_KEY is missing or empty")
```

Use `max_credits=N` on submission calls for a per-workflow ceiling, and track
campaign totals separately. `rowan.api_credentials(key, project_uuid=...)` offers
context-local credentials in a shared process; it rejects an empty key.

## Server-side workflow failures

```python
try:
    result = wf.result()
except rowan.WorkflowError as exc:
    print(f"Workflow failed: {exc}")
    print(f"Status: {wf.get_status()}")
    # exc.logfile holds backend diagnostics; review privately if needed.
```

## Polling and non-blocking checks

```python
# Block and poll every five seconds.
result = wf.result(wait=True, poll_interval=5)

# Or check without blocking.
if not wf.done():
    print(f"Still running: {wf.get_status()}")
else:
    try:
        result = wf.result(wait=False)
    except rowan.WorkflowError as exc:
        print(f"Finished without a successful result: {exc}")
```

`WorkflowResult.complete` is a boolean, not a percent-done value. For coarse
status, use `wf.get_status()`. `wf.fetch_latest()` returns a refreshed copy by
default; assign it back or pass `in_place=True`. `done()` also includes failed
and stopped workflows. Neither polling method provides an overall deadline;
use an application-controlled deadline for bounded monitoring.

## Debugging tips

- Inspect `result.data` when a convenience property is unavailable.
- Save workflow UUIDs and reconnect with `rowan.retrieve_workflow(uuid)`.
- Use `dir(result)` to discover properties for that result class; they differ.
- Validate SMILES locally with RDKit before any paid submission.

## Completed-result schema mismatch

In 3.2.0, a completed response that fails the installed `stjames` model raises
`ValueError` with a schema-mismatch message. Record both package versions and
the workflow UUID, then check compatible releases. Do not silently replace
missing scientific values with zero. For a still-running response, use `.data`
until typed fields become available. Clearing a result's structure cache does
not refresh the underlying workflow snapshot; retrieve a new result for that.

Do not blindly retry a submission after a transport timeout: it may already
have been accepted. Reconcile the saved campaign folder/UUIDs first.

## Rowan 3.2.0 Folder initialization defect

With the released 3.2.0 source and Pydantic 2.13.5, `Folder` construction raises
`PydanticUserError: Folder is not fully defined`. The SDK imports `datetime`
only under `TYPE_CHECKING` while using it in a runtime Pydantic field. This was
reproduced locally without API access. Until using an upstream release that
fixes it, initialize the model once before folder operations:

```python
import rowan
from datetime import datetime

rowan.Folder.model_rebuild(_types_namespace={"datetime": datetime})
```

This resolves the missing type without changing the installed package. The
project, batch, and campaign examples include this locally tested workaround.
