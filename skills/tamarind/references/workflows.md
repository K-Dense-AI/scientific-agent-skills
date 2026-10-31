# Tamarind Bio HTTP workflow recipes

These Python recipes target the official REST contracts reviewed **2026-09-30**.
They were smoke-tested locally using simulated responses, including failure,
normalization, pagination, and asynchronous-result cases. They have **not** been
executed against an authenticated Tamarind account. Scientific submissions below
are illustrative and consume compute when run.

Use Python 3.10+ and `requests`; set `TAMARIND_API_KEY` outside code. On a dedicated
organization deployment set `TAMARIND_BASE_URL` to that host's `/api` base. Save
job names so long runs can be checked in a later session.

## Common helpers

Copy this block into the working script. Validation is part of submission; the
result downloader only handles retrieval and never creates a replacement job.

```python
import json
import os
import re
import time
from pathlib import Path

import requests

BASE = os.environ.get("TAMARIND_BASE_URL", "https://app.tamarind.bio/api").rstrip("/")
HEADERS = {"x-api-key": os.environ["TAMARIND_API_KEY"]}
TERMINAL = {"Complete", "Stopped", "Failed", "Deleted"}


def api(method, path, *, timeout=(10, 60), **kwargs):
    response = requests.request(method, BASE + path, headers=HEADERS,
                                timeout=timeout, **kwargs)
    response.raise_for_status()  # inspect response body on HTTPError
    return response


def clean_name(name):
    # Use conservative names that exact GET /jobs can address.
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", name):
        raise ValueError("Use a nonempty clean name of at most 200 characters")
    return name


def validate_settings(tool_type, settings, name=None):
    payload = {"type": tool_type, "settings": settings}
    if name is not None:
        payload["jobName"] = clean_name(name)
    verdict = api("POST", "/validate-job", json=payload).json()
    if not verdict.get("valid") or verdict.get("unrecognized_settings"):
        raise ValueError(f"Validation needs attention: {verdict}")
    return verdict


def submit_checked(tool_type, settings, name, project_tag=None):
    verdict = validate_settings(tool_type, settings, name)
    stored_name = clean_name(verdict.get("job_name", name))
    payload = {"jobName": stored_name, "type": tool_type,
               "settings": verdict["normalized"]}
    if project_tag is not None:
        payload["projectTag"] = project_tag
    # Persist before submitting; a timeout may still have queued the job.
    Path(f"{stored_name}.submission.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    response = api("POST", "/submit-job", json=payload)
    suffix = " submitted to queue."
    if not response.text.endswith(suffix):
        raise RuntimeError("Unexpected receipt; inspect the persisted name before retrying")
    return clean_name(response.text[:-len(suffix)])


def wait_job(name, *, batch=False, max_seconds=3600, interval=30):
    deadline = time.monotonic() + max_seconds
    while time.monotonic() < deadline:
        row = api("GET", "/jobs", params={"jobName": name}).json()
        if batch:
            status = row.get("batchStatus")
            if status == "Complete":
                return row
            if status in {"Stopped", "AggregationFailed"} or row.get("JobStatus") in {
                "Stopped", "Failed", "Deleted"
            }:
                raise RuntimeError(f"Batch {name}: {row.get('AggregationError') or status}")
        else:
            status = row.get("JobStatus")
            if status in TERMINAL:
                return row
        time.sleep(interval)
    raise TimeoutError(f"Still pending: {name}; resume lookup later, do not resubmit")


def download_result(name, destination, *, file_name=None, max_seconds=3600):
    payload = {"jobName": name}
    if file_name is not None:
        payload["fileName"] = file_name
    deadline = time.monotonic() + max_seconds
    while time.monotonic() < deadline:
        # /result may wait about 290 seconds while assembling an archive.
        response = api("POST", "/result", json=payload, timeout=(10, 310))
        if response.status_code == 202:
            if response.json().get("status") != "preparing":
                raise RuntimeError("Unexpected asynchronous result response")
            time.sleep(30)
            continue
        if response.status_code != 200:
            raise RuntimeError(f"Unexpected result status: {response.status_code}")
        url = response.json()  # JSON string, not .text.strip('"')
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError("Result response did not contain an HTTPS download URL")
        # No Tamarind API key on a storage request. Stream potentially large zips.
        with requests.get(url, stream=True, timeout=(10, 120)) as download:
            download.raise_for_status()
            with Path(destination).open("wb") as handle:
                for chunk in download.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        return
    raise TimeoutError(f"Archive still preparing for {name}; retry retrieval later")


def iter_jobs(**selectors):
    params = {"limit": 1000, **selectors}
    while True:
        page = api("GET", "/jobs", params=params).json()
        yield from page["jobs"]
        cursor = page.get("startKey")
        if not cursor:
            return
        params["startKey"] = cursor
```

A timeout is a local waiting limit, not cancellation. Inspect the persisted name
before retrying a submission. The helpers deliberately do not automatically
retry a state-changing request.

## 1. Discover, inspect, and fold a sequence

```python
tools = api("GET", "/tools").json()
tool = next(t for t in tools if t["name"] == "alphafold")
schema = api("GET", f"/tools/{tool['name']}/schema").json()
# Inspect schema and selected defaults before executing this illustrative job.
sequence = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"
name = submit_checked(tool["name"], {"sequence": sequence}, "ubiquitin-fold")
print("[OK] Submitted", name)
```

Check in a later session, or use bounded polling for a short run:

```python
name = "ubiquitin-fold"  # use the stored name returned at submission
row = wait_job(name)
if row["JobStatus"] == "Complete":
    download_result(name, f"{name}.zip")
elif row["JobStatus"] in {"Stopped", "Failed"}:
    download_result(name, f"{name}.log", file_name="output.log")
else:
    print("[FAIL] Job was deleted; no result download attempted")
```

For AF2 multimers join actual chain sequences with `:`. For Boltz/Chai, inspect
the current task selector and schema: sequence is currently the default mode;
YAML/list/molecule modes take different fields. Do not submit literal `...` as a
sequence or substitute a filename into a sequence field.

## 2. Upload a structure

The official upload route redirects; `curl -L` follows it. No folder means the
reference is `target.pdb`; this example uses `inputs/target.pdb`.

```bash
curl --fail-with-body -L -X PUT \
  'https://app.tamarind.bio/api/upload/target.pdb?folder=inputs' \
  -H "x-api-key: $TAMARIND_API_KEY" \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @target.pdb
```

Confirm `GET /files?folder=inputs`, then set the schema's file parameter to the
registered relative path. DiffDock's SMILES branch uses `proteinFile`,
`ligandFormat: "SMILES"`, and `ligandSmiles`; Vina uses `receptorFile` and lowercase
`ligandFormat: "smiles"`. Read the tool's full schema for search-box/default
settings rather than copying parameter names across tools.

## 3. Validate and submit a batch

This example uses the same `sequence` defined above twice to demonstrate request
shape. Real screens should use the intended independent candidate sequences.
Validate at most 1,000 rows per call, splitting further when request or normalized
response sizes require it. Submission also counts design fan-out toward 30,000.

```python
settings = [{"sequence": sequence}, {"sequence": sequence}]
job_names = ["candidate-1", "candidate-2"]
verdict = api("POST", "/validate-job", json={
    "type": "alphafold", "settings": settings, "jobNames": job_names,
}).json()
if "results" not in verdict:
    raise ValueError(verdict.get("error", "Batch validation request was refused"))
rows = verdict["results"]
if (len(rows) != len(settings) or not verdict.get("valid")
        or any(not r.get("valid") or r.get("unrecognized_settings") for r in rows)
        or [r["index"] for r in rows] != list(range(len(settings)))):
    raise ValueError(f"Fix batch validation: {verdict}")
payload = {
    "batchName": "binder-screen", "type": "alphafold", "jobNames": job_names,
    "settings": [r["normalized"] for r in rows],
}
# Add a confirmed organization projectTag if required by account policy.
Path("binder-screen.submission.json").write_text(json.dumps(payload), encoding="utf-8")
receipt = api("POST", "/submit-batch", json=payload).json()
batch_name = receipt.get("batchName", payload["batchName"])
print("[OK] Batch submitted", batch_name)
```

Later, `wait_job(batch_name, batch=True)` waits for aggregation, then
`download_result(batch_name, "binder-screen.zip")` handles archive preparation.
Use `list(iter_jobs(batch=batch_name))` to collect every child page. Stored child
names may differ from the proposed `jobNames`; use the returned rows.

## 4. Resume a campaign with batched status lookups

Persist exact names as JSON after collecting submission receipts. This is a
read-only lookup for up to 1,000 names per call, useful after a lost submission
response as well as during normal polling:

```python
names = json.loads(Path("pending_jobs.json").read_text(encoding="utf-8"))
completed, failed, pending, missing = [], [], [], []
for offset in range(0, len(names), 1000):
    page = api("POST", "/jobs/search", json={"jobNames": names[offset:offset + 1000]}).json()
    missing.extend(page["notFound"])
    for row in page["jobs"]:
        status = row["JobStatus"]
        destination = completed if status == "Complete" else failed if status in TERMINAL else pending
        destination.append(row["JobName"])
print({"complete": len(completed), "failed": len(failed),
       "pending": len(pending), "not_found": len(missing)})
```

Download only `completed` archives, and fetch logs for stopped/failed names after
reading details. Investigate `notFound` (owner, deployment, normalized name,
deletion) before deciding to retry. `/jobs/search` omits `Settings`, `Score`, and
aggregation errors; fetch details only for candidates that need inspection.

## 5. Chain design and evaluation

1. Fold or obtain the target/backbone and inspect its chain/residue numbering.
2. Validate a ProteinMPNN settings object with `pdbFile` set to an uploaded path
   or actual prior-job output, and `designedResidues` mapped to that structure.
3. Download the completed design results and read their generated FASTA/CSV
   sequences. Do not assume a fixed filename; use published output metadata and
   inspect the archive (or a file-list MCP helper if advertised).
4. Submit the sequences as validated folding settings, using the batch recipe.
5. Compare re-folded designs to intended backbone/interface geometry, confidence,
   clashes, and relevant developability criteria. Confidence alone is not binding.

For reusable pipelines read the current graph schema and use the separate
`/pipelines/validate`, `/pipelines/submit`, and `/pipelines/runs/{run_id}` routes.
Do not poll a pipeline run through `/jobs` or assume the same status vocabulary.
