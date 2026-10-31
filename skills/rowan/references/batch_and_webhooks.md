# Batch Submission, Webhooks, and Asynchronous Workflows

Targets `rowan-python` 3.2.0. Hosted calls below are illustrative; this refresh
verified SDK contracts and local signature checks without submitting paid work.
See the [workflow reference](https://docs.rowansci.com/api/python/v3/api/workflow/)
and [webhook reference](https://docs.rowansci.com/api/python/v3/api/webhooks/).

## Submit and reconnect to a batch

Prefer named submit functions: they construct and validate each workflow's input
model. Generic `submit_workflow` and `batch_submit_workflow` still exist; they
require the exact workflow schema and are not universally broken. An HTTP 422
is a request-validation failure, not evidence that these functions are disabled.

```python
import json
from pathlib import Path
import rowan

# Work around the Folder annotation defect in SDK 3.2.0.
from datetime import datetime
rowan.Folder.model_rebuild(_types_namespace={"datetime": datetime})

# ROWAN_API_KEY is read from the environment. Use the intended active project.
folder = rowan.get_folder("screening/descriptors")
compounds = {"ethanol": "CCO", "acetic_acid": "CC(=O)O", "phenol": "c1ccccc1O"}
# Durable progress: a retry loads existing identifiers instead of re-submitting them.
manifest = Path("submitted_workflows.json")
submitted = json.loads(manifest.read_text()) if manifest.exists() else {}
for name, smiles in compounds.items():
    if name in submitted:
        continue
    wf = rowan.submit_descriptors_workflow(
        rowan.Molecule.from_smiles(smiles), name=name, folder=folder, max_credits=10,
    )
    submitted[name] = {"uuid": wf.uuid, "smiles": smiles}
    # Save after each acknowledged submission; do not wait until the entire loop finishes.
    manifest.write_text(json.dumps(submitted, indent=2))
```

The example's per-job ceiling is an illustrative budget choice, not a runtime
estimate. Persist the full settings and environment lockfile in a real campaign.
A lost response or crash between acceptance and recording still leaves an
ambiguous submission: reconcile the folder before retrying. The SDK does not
provide an idempotency key in these submission signatures.

```python
# Run later, after loading the same manifest.
uuids = [record["uuid"] for record in submitted.values()]
counts = rowan.batch_poll_status(uuids)
print(counts)  # Aggregate lower-case status counts, not a UUID-to-status mapping.
# Do not infer individual success from an invented count-key schema.
# Check each saved UUID below; returned count keys are server-defined.
```

Inspect individual workflows to collect results and distinguish failures:

```python
results = []
for name, record in submitted.items():
    wf = rowan.retrieve_workflow(record["uuid"])
    if not wf.done():
        print(name, wf.get_status())
        continue
    try:
        result = wf.result(wait=False)
    except rowan.WorkflowError as exc:
        # done() also includes FAILED and STOPPED.
        print(name, str(exc))
        continue
    results.append({"name": name, "uuid": wf.uuid, "data": result.data})
```

## Webhook secrets and submission

Secret management returns a string, or `None` from `get_webhook_secret()` when
unset. Perform provisioning separately from a web server's import/startup path:

```python
secret = rowan.get_webhook_secret()
if secret is None:
    secret = rowan.create_webhook_secret()  # Idempotent if one already exists.
# Store securely for the receiver; never print or commit this secret.
# Explicit rotation invalidates the old secret:
# secret = rowan.rotate_webhook_secret()
```

Named submit functions expose `webhook_url`:

```python
wf = rowan.submit_descriptors_workflow(
    rowan.Molecule.from_smiles("CCO"),
    name="ethanol callback",
    webhook_url="https://example.org/rowan_callback",  # Replace with your receiver.
    max_credits=10,
)
```

The SDK's signature header format is:

```text
X-Rowan-Signature: t=<unix_timestamp>,sha256=<hex_digest>
```

The HMAC-SHA256 message is `timestamp + b"." + raw_body`, not the JSON body
alone. `verify_webhook_secret(raw_body, signature_header, secret,
max_age_seconds=300)` checks the digest and timestamp freshness. Verify the
original bytes before parsing; re-encoding JSON changes the signature input.
The current helper can raise `ValueError` for a non-integer timestamp, so a
receiver must treat that as invalid authentication.

## Minimal receiver (FastAPI)

Requires `fastapi` and an ASGI server in the receiver's own environment.
`ROWAN_WEBHOOK_SECRET` here is receiver configuration populated during the
provisioning step; it is not an SDK-discovered environment variable.

```python
import os
import json
from fastapi import FastAPI, Request, HTTPException
import rowan

app = FastAPI()
webhook_secret = os.environ["ROWAN_WEBHOOK_SECRET"]
if not webhook_secret:
    raise RuntimeError("Missing webhook receiver secret")

@app.post("/rowan_callback")
async def handle_rowan_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Rowan-Signature", "")
    try:
        valid = rowan.verify_webhook_secret(body, signature, webhook_secret)
    except (ValueError, OverflowError):
        valid = False
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")
    # Demonstration receiver only: add durable event storage or queueing here.
    # Reconcile your saved workflow UUIDs through retrieve_workflow().result().
    return {"status": "received"}
```

The official public webhook reference specifies signing but does not publish a
complete event schema or retry schedule. Do not assume fields such as
`workflow_uuid`, `status`, or an embedded `data` result based on a fabricated
sample. Establish the actual event schema in an integration test, then validate
it and deduplicate events. Persist before acknowledging in production, return
promptly, and retrieve authoritative workflow results using your saved UUIDs.

## SDK transport and pagination contracts

These are verified against the released SDK source, not an authenticated server
probe. The default base is `https://api.rowansci.com`, with `X-API-Key`
authentication and no guessed `/v1` prefix. Prefer SDK calls over hand-built requests.

| Operation | Transport and response |
|---|---|
| Named workflow submission | `POST /workflow`; JSON includes `workflow_type`, validated `workflow_data`, applicable molecule/SMILES input, `name`, `folder_uuid`, `max_credits`, `webhook_url`, `is_draft`; response parses as `Workflow` |
| Retrieve/poll | `GET /workflow/{uuid}`; wire keys include `object_status`, `object_type`, `object_data`; SDK exposes `.status`, `.workflow_type`, `.data` |
| Batch status | `POST /workflow/batch_status` with `{"uuids": [...]}`; aggregate counts |
| List workflows | `GET /workflow`; `parent_uuid` is a folder; `page=0`, `size=10` by default; wire response has `workflows`; SDK returns a list |
| Account | `GET /user/me`; returns `User`, including account-specific `enabled_workflows` |
| Webhook secret | `GET`/`POST /user/me/webhook_secret`; rotation is `POST /user/me/webhook_secret/rotate`; SDK unwraps `webhook_secret` |
| Projects | `POST /project` with `name`; `GET /project/{uuid}`; listing uses zero-based `page`/`size` and a `projects` envelope |
| Default project | `GET /user/me/default_project`; returns its root folder UUID for folder/list helpers when no project is active |
| Folders | `POST /folder` with `name` and a parent folder UUID; `GET /folder` lists one page under a parent (`folders` envelope); `get_folder` resolves/creates each path component |
| Protein import | `POST /convert/pdb_file_to_protein` or `/convert/mmcif_file_to_protein` with `name`/`text`, then `POST /protein` with `protein_data`; PDB IDs use `/convert/pdb_id_to_protein?pdb_id=...` |
| Protein retrieve/list | `GET /protein/{uuid}` (optional `workflow_uuid` access context); `GET /protein` with `page=0`, `size=20` defaults and a `proteins` envelope |
| Lazy structures | Calculation retrieval uses `GET /calculation/{uuid}/stjames`; protein results use `GET /protein/{uuid}`; convenience access can therefore cause more requests |
| MSA archives | `GET /workflow/{uuid}/get_msa_files?msa_format=colabfold` (or `chai`/`boltz`); binary tar.gz, not JSON |

List functions fetch one page, not the complete collection. Advance `page` until
empty and traverse subfolders explicitly. Do not convert numeric wire statuses
to invented strings; use the SDK enum names (`COMPLETED_OK`, `FAILED`, `STOPPED`).
