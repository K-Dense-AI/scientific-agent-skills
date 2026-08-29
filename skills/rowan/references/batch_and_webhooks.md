# Batch Submission, Webhooks, and Asynchronous Workflows

Webhook secret management, batch submit/poll/retrieve, the non-blocking fire-and-check
pattern, webhook payloads and signature verification, and webhook best practices.

### Webhook secret management

For webhook signature verification, manage secrets through your user account:

```python
import rowan

# Get your current webhook secret (returns None if none exists)
secret = rowan.get_webhook_secret()
if secret is None:
    secret = rowan.create_webhook_secret()
# These functions return the secret as a plain string.

# Rotate your secret (invalidates old, creates new)
# Use this periodically for security.
secret = rowan.rotate_webhook_secret()

# Verify incoming webhook signatures.
is_valid = rowan.verify_webhook_secret(
    raw_body=b"...",                  # Raw request body (bytes)
    signature_header="sha256=...",    # Value from X-Rowan-Signature
    secret=secret,
)
```

## Batch submission and retrieval

For libraries or analogue series, submit in a loop using the specific workflow function. The generic `rowan.batch_submit_workflow()` and `rowan.submit_workflow()` functions currently return 422 errors from the API — use the named functions (`submit_descriptors_workflow`, `submit_pka_workflow`, etc.) instead.

### Submit a batch

```python
smileses = ["CCO", "CC(=O)O", "c1ccccc1O"]
names = ["ethanol", "acetic acid", "phenol"]

workflows = [
    rowan.submit_descriptors_workflow(rowan.Molecule.from_smiles(smi), name=name)
    for smi, name in zip(smileses, names)
]

print(f"Submitted {len(workflows)} workflows")
```

### Poll batch status

```python
statuses = rowan.batch_poll_status([wf.uuid for wf in workflows])
# Returns aggregate counts — not per-UUID:
# {'queued': 0, 'running': 1, 'complete': 2, 'failed': 0, 'total': 3, ...}

if statuses["complete"] == statuses["total"]:
    print("All workflows done")
elif statuses["failed"] > 0:
    print(f"{statuses['failed']} workflows failed")
```

### Retrieve and collect results

```python
results = []
for wf in workflows:
    try:
        result = wf.result()
        results.append(result.data)
    except rowan.WorkflowError as e:
        print(f"Workflow {wf.uuid} failed: {e}")

# Optionally aggregate into DataFrame
import pandas as pd
df = pd.DataFrame(results)
```

### Non-blocking / fire-and-check pattern

For long-running workflows where you don't want to hold a process open, submit workflows, save their UUIDs, and check back later in a separate process.

**Session 1 — submit and save UUIDs:**

```python
import rowan, json

rowan.api_key = "..."
smileses = ["CCO", "CC(=O)O", "c1ccccc1O"]

workflows = [
    rowan.submit_descriptors_workflow(
        rowan.Molecule.from_smiles(smi), name=f"compound_{i}"
    )
    for i, smi in enumerate(smileses)
]

# Save UUIDs to disk (or a database)
uuids = [wf.uuid for wf in workflows]
with open("workflow_uuids.json", "w") as f:
    json.dump(uuids, f)

print("Submitted. Check back later.")
```

**Session 2 — check status and collect results when ready:**

```python
import rowan, json

rowan.api_key = "..."

with open("workflow_uuids.json") as f:
    uuids = json.load(f)

results = []
for uuid in uuids:
    wf = rowan.retrieve_workflow(uuid)
    if wf.done():
        result = wf.result(wait=False)
        results.append({"uuid": uuid, "data": result.data})
    else:
        print(f"{uuid}: still running ({wf.get_status()})")

print(f"Collected {len(results)} completed results")
```

## Webhooks and asynchronous workflows

For long-running campaigns or when you don't want to keep a process alive, use webhooks to notify your backend when workflows complete.

### Setting up webhooks

Every workflow submission function accepts a `webhook_url` parameter:

```python
wf = rowan.submit_docking_workflow(
    protein=protein,
    pocket=pocket,
    initial_molecule=rowan.Molecule.from_smiles("CCO"),
    webhook_url="https://myserver.com/rowan_callback",
    name="docking with webhook",
)

print(f"Workflow submitted. Result will be POSTed to webhook when complete.")
```

Webhook URLs can be passed to any specific workflow function (`submit_docking_workflow()`, `submit_pka_workflow()`, `submit_descriptors_workflow()`, etc.).

### Webhook authentication with secrets

Rowan supports webhook signature verification to ensure requests are authentic. You'll need to:

1. **Create or retrieve a webhook secret:**

```python
import rowan

# Create a new webhook secret
secret = rowan.create_webhook_secret()  # returns a string
# Store it securely; do not log it.

# Or retrieve an existing secret
secret = rowan.get_webhook_secret()

# Rotate your secret (invalidates old one, creates new)
new_secret = rowan.rotate_webhook_secret()
```

2. **Verify incoming webhook requests:**

```python
import rowan
import hmac
import json

def verify_webhook(request_body: bytes, signature: str, secret: str) -> bool:
    """Verify the HMAC-SHA256 signature of a webhook request."""
    return rowan.verify_webhook_secret(request_body, signature, secret)
```

### Webhook payload and signature

When a workflow completes, Rowan POSTs a JSON payload to your webhook URL with the header:

```text
X-Rowan-Signature: <HMAC-SHA256 signature>
```

The request body contains the complete workflow result:

```json
{
  "workflow_uuid": "wf_12345abc",
  "workflow_type": "docking",
  "workflow_name": "lead docking",
  "status": "COMPLETED_OK",
  "created_at": "2025-04-01T12:00:00Z",
  "completed_at": "2025-04-01T12:15:30Z",
  "data": {
    "scores": [-8.2, -8.0, -7.9],
    "best_pose": {...},
    "metadata": {...}
  }
}
```

### Example webhook handler with signature verification (FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
import rowan
import json

app = FastAPI()
webhook_secret = rowan.get_webhook_secret() or rowan.create_webhook_secret()

@app.post("/rowan_callback")
async def handle_rowan_webhook(request: Request):
    # Get request body and signature
    body = await request.body()
    signature = request.headers.get("X-Rowan-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing X-Rowan-Signature header")

    # Verify signature
    if not rowan.verify_webhook_secret(body, signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse and process
    payload = json.loads(body)
    wf_uuid = payload["workflow_uuid"]
    status = payload["status"]

    if status == "COMPLETED_OK":
        print(f"Workflow {wf_uuid} succeeded!")
        result_data = payload["data"]
        # Process result, update database, trigger next workflow, etc.
    elif status == "FAILED":
        print(f"Workflow {wf_uuid} failed!")
        # Handle failure

    # Respond quickly to prevent retries
    return {"status": "received"}
```

### Webhook best practices

- **Always verify signatures** using `rowan.verify_webhook_secret()` to ensure requests are from Rowan
- **Respond quickly** (< 5 seconds); offload heavy processing to async tasks or background jobs
- **Implement idempotency**: workflows may retry; handle duplicate payloads gracefully using `workflow_uuid`
- **Log all events** for debugging and audit trails
- **Use for long campaigns**: webhooks shine with 50+ workflows; for small jobs, polling with `result()` is simpler
- **Rotate secrets regularly** using `rowan.rotate_webhook_secret()` for security
- **Return 2xx status** to confirm receipt; Rowan may retry on 5xx errors
