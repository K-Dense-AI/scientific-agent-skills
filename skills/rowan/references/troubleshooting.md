# Error Handling and Troubleshooting

Common errors — invalid SMILES, missing API keys, HTTP/API failures, failed
workflows, and polling — with verified handling for `rowan-python` 3.1.13.

## Actual exception classes

`rowan.ValidationError`, `rowan.AuthenticationError`, and
`rowan.InsufficientCreditsError` do **not** exist in SDK 3.1.13. Referencing one
in an `except` clause raises `AttributeError` while handling the original
failure.

| Failure | Exception |
|---|---|
| Bad SMILES or wrong input type for a workflow | `ValueError` |
| Authentication, credit, or other HTTP/API failure | `httpx.HTTPStatusError` |
| Submitted workflow fails server-side | `rowan.WorkflowError` |

## Validate molecules before submission

```python
from rdkit import Chem

smiles = "CCCC(CC"
mol = Chem.MolFromSmiles(smiles)
if mol is None:
    raise ValueError(f"Invalid SMILES: {smiles}")
```

Input types vary by workflow. For example, descriptors require a molecule
object, while pKa accepts a SMILES string:

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
        print(exc.response.status_code, exc.response.text)
        raise
```

The SDK treats an environment variable set to an **empty string** as present.
That produces `401 Could not validate credentials` rather than a clear missing
key error. Check that `ROWAN_API_KEY` is non-empty without printing the key:

```python
import os

api_key = os.environ.get("ROWAN_API_KEY")
if not api_key:
    raise RuntimeError("ROWAN_API_KEY is missing or empty")
```

Use `max_credits=N` on submission calls to bound spend.

## Server-side workflow failures

```python
try:
    result = wf.result()
except rowan.WorkflowError as exc:
    print(f"Workflow failed: {exc}")
    print(f"Status: {wf.get_status()}")
```

## Polling and non-blocking checks

```python
# Block and poll every five seconds.
result = wf.result(wait=True, poll_interval=5)

# Or check without blocking.
if not wf.done():
    print(f"Still running: {wf.get_status()}")
else:
    result = wf.result(wait=False)
```

`WorkflowResult.complete` is a boolean, not a percent-done value. For coarse
status, use `wf.get_status()` and `wf.fetch_latest()`.

## Debugging tips

- Inspect `result.data` when a convenience property is unavailable.
- Save workflow UUIDs and reconnect with `rowan.retrieve_workflow(uuid)`.
- Use `dir(result)` to discover properties for that result class; they differ.
- Validate SMILES locally with RDKit before any paid submission.
