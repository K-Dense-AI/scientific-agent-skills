# Benchling REST API Reference

Reviewed 2026-09-30 against the [official reference](https://benchling.com/api/reference),
platform guides, and generated **benchling-api-client 2.0.434**, resolved alongside SDK **1.25.0**.
The public reference is a JavaScript application; the published Python client supplied
the endpoint/parameter/model definitions for this audit. Check your tenant's interactive
reference before executing writes, especially on a validated/restricted release.
No authenticated endpoint calls were made. Payloads below are illustrative.

## Version and authentication

This reference covers `https://{tenant}.benchling.com/api/v2`. V3 also exists;
consult its [availability/stability guide](https://docs.benchling.com/docs/v3-api-overview)
and tenant documentation rather than replacing `/v2` with `/v3` in these paths.

Use HTTPS and either Basic auth (API key as username, empty password) or OAuth Bearer
auth. JSON writes use `Content-Type: application/json`. Token exchanges are form encoded
at `/oauth/token`; the SDK's legacy `/api/v2/token` path still works. See
[authentication](authentication.md) for identity, expiry, and token acquisition.

## Responses, pagination, and filters

Single-resource endpoints generally return a resource object; `GET /entries/{id}` is an
exception with an `entry` wrapper. Creation usually returns HTTP 201 and the created
resource. List responses use a **resource-specific collection key**, never a universal `results` key:

```json
{
  "dnaSequences": [{"id": "seq_example", "name": "Construct 001", "bases": "ATCG"}],
  "nextToken": "opaque-token"
}
```

Most paginated lists accept `pageSize` (default 50, maximum 100) and `nextToken`. Preserve
filters when requesting the next page; stop on an empty token. Some lists differ:
`GET /registries` returns `registries` without the standard pagination arguments.
`GET /events` has additional polling semantics described below.

Filters are endpoint-specific. On DNA sequences, `name` matches the full name;
`nameIncludes` supports substring search. `modifiedAt` and `createdAt` are string filters;
consult the tenant reference for their comparison syntax rather than assuming every
timestamp filter is inclusive. Use `archiveReason` for archival filtering according to
the endpoint definition; `archived=false` is not a supported replacement.

### Collection and resource routes

All paths in this table are relative to `/api/v2`. A `GET` collection returns the named
collection; `POST` creates one resource with the type's create model. A resource `GET`
returns one object (with the entry wrapper noted above) and `PATCH` applies its update model.

| Collection | Collection methods | Collection key | Resource path and methods |
|---|---|---|---|
| `/dna-sequences` | GET, POST | `dnaSequences` | `/dna-sequences/{dnaSequenceId}` GET, PATCH |
| `/rna-sequences` | GET, POST | `rnaSequences` | `/rna-sequences/{rnaSequenceId}` GET, PATCH |
| `/aa-sequences` | GET, POST | `aaSequences` | `/aa-sequences/{aaSequenceId}` GET, PATCH |
| `/custom-entities` | GET, POST | `customEntities` | `/custom-entities/{customEntityId}` GET, PATCH |
| `/mixtures` | GET, POST | `mixtures` | `/mixtures/{mixtureId}` GET, PATCH |
| `/containers` | GET, POST | `containers` | `/containers/{containerId}` GET, PATCH |
| `/boxes` | GET, POST | `boxes` | `/boxes/{boxId}` GET, PATCH |
| `/locations` | GET, POST | `locations` | `/locations/{locationId}` GET, PATCH |
| `/plates` | GET, POST | `plates` | `/plates/{plateId}` GET, PATCH |
| `/entries` | GET, POST | `entries` | `/entries/{entryId}` GET, PATCH |
| `/workflow-tasks` | GET, POST | `workflowTasks` | `/workflow-tasks/{workflowTaskId}` GET, PATCH |
| `/folders` | GET, POST | `folders` | `/folders/{folderId}` GET |
| `/projects` | GET | `projects` | `/projects/{projectId}` GET |
| `/users` | GET | `users` | `/users/{userId}` GET |
| `/teams` | GET | `teams` | `/teams/{teamId}` GET |
| `/registries` | GET | `registries` | `/registries/{registryId}` GET |

This is a task-oriented subset, not a claim that these are each service's only methods.
There is no documented `/users/me` endpoint; test auth against an accessible resource.

### Schema routes

Use `GET` on each collection or append `/{schemaId}` for one schema:

| Collection | Collection key |
|---|---|
| `/entity-schemas` | `entitySchemas` |
| `/entry-schemas` | `entrySchemas` |
| `/container-schemas` | `containerSchemas` |
| `/box-schemas` | `boxSchemas` |
| `/location-schemas` | `locationSchemas` |
| `/plate-schemas` | `plateSchemas` |
| `/workflow-task-schemas` | `workflowTaskSchemas` |

There is no generic stable-v2 `/schemas?entityType=...` route. The SDK exposes these as
`benchling.schemas.list_entity_schemas()`, `get_entity_schema_by_id(id)`, and analogous
resource-specific methods. Schema definitions determine field names, value types,
required values, units, and valid workflow statuses.

## Entity create/update/archive

A registered DNA sequence create body for `POST /dna-sequences`:

```json
{
  "name": "Construct 001",
  "bases": "ATCGATCG",
  "isCircular": true,
  "folderId": "lib_example",
  "schemaId": "ts_example",
  "registryId": "src_example",
  "namingStrategy": "NEW_IDS",
  "fields": {"gene_name": {"value": "GFP"}}
}
```

Omit registration arguments to create an unregistered entity. To assign a human registry
identifier explicitly, supply `entityRegistryId` **instead of** `namingStrategy`, together
with `registryId`. These are different concepts, not interchangeable IDs.

`POST /rna-sequences` uses `bases` (RNA alphabet) and `isCircular`.
`POST /aa-sequences` uses `aminoAcids`. `POST /custom-entities` uses `name`, `schemaId`,
`folderId`, and applicable fields. Do not coerce numeric fields to strings globally.
A partial update uses the same field-value envelope, for example:

```json
{"fields": {"passage_number": {"value": 16}}}
```

Sequence filters include `folderId`, `schemaId`, `name`, `nameIncludes`, `modifiedAt`,
`createdAt`, `registryId`, and `archiveReason`; `schemaId` is an optional custom-entity
filter rather than a requirement to list all accessible entities.

Archival endpoints are `POST /dna-sequences:archive`, `/rna-sequences:archive`,
`/aa-sequences:archive`, `/custom-entities:archive`, and `/mixtures:archive`.
Use the appropriate array key (`dnaSequenceIds`, `rnaSequenceIds`, `aaSequenceIds`,
`customEntityIds`, or `mixtureIds`) and an allowed reason:

```json
{"dnaSequenceIds": ["seq_example"], "reason": "Retired"}
```

Allowed `EntityArchiveReason` values in this release include `Made in error`, `Retired`,
`Expended`, `Shipped`, `Contaminated`, `Expired`, `Missing`, and `Other`. Free-form
reasons such as `Cleanup` are not the enum. Read the archival response rather than
assuming deletion; archival preserves records and can affect related data.

For mixture creation, each ingredient uses a separate amount and unit:

```json
{
  "name": "Example formulation",
  "schemaId": "ts_mixture",
  "folderId": "lib_example",
  "ingredients": [{
    "componentEntityId": "bfi_component",
    "amount": "100",
    "units": "mg",
    "catalogIdentifier": null,
    "componentLotContainerId": null,
    "componentLotEntityId": null,
    "componentLotText": null,
    "notes": null
  }]
}
```

## Inventory payloads and actions

For container/box/plate creation, `schemaId` is required. Location creation requires
`name` and `schemaId`. Depending on storage type, add `parentStorageId`, `barcode`,
`name`, or schema `fields`. Query containers and boxes by `ancestorStorageId` and
`barcodes` (comma-separated); `parentStorageId` and singular `barcode` are not the list
filters shown in this SDK. Ancestor filters include nested descendants.

Move a container physically with `PATCH /containers/{containerId}`:

```json
{"parentStorageId": "loc_destination"}
```

Check out with `POST /containers:check-out`:

```json
{"containerIds": ["con_example"], "assigneeId": "usr_example", "comment": "At bench"}
```

Check in with `POST /containers:check-in`:

```json
{"containerIds": ["con_example"], "comments": "Returned"}
```

These operations return HTTP 200 with an empty JSON object `{}` on success. There is no `locationId` parameter
for check-in. Notice the hyphen in each route and different `comment`/`comments` keys.

**Material transfer** has two distinct operations:

- `POST /containers/{destinationContainerId}:transfer`: `ContainerTransfer` body,
  including `destinationContents` plus the applicable source/quantity fields; HTTP 200 with `{}`
  on success.
- `POST /transfers`: a `transfers` array of `MultipleContainersTransfer` objects;
  returns HTTP 202 with a `taskId` for async processing. Limit: 5000 transfers per request.

Illustrative batch body:

```json
{
  "transfers": [{
    "sourceContainerId": "con_source",
    "destinationContainerId": "con_destination",
    "transferQuantity": {"value": 5.0, "units": "uL"}
  }]
}
```

Neither `/containers:transfer` nor `/containers:bulk-transfer` is the corresponding
stable-v2 route. Never use material transfer to represent moving a tube to a box.

Plate creation `wells` is a mapping of positions to well properties, not an array of
`{"position": "A1", "entityId": ...}`. Create/read the plate first, resolve its well
container IDs, then load biological contents through transfer APIs. Storage schema and
well positions must match the actual plate configuration.

## Entries, workflow tasks, folders

`POST /entries` requires `name` and `folderId`; `entryTemplateId`, `initialTables`,
`schemaId`, and `fields` support appropriate template/schema workflows. `PATCH /entries/{id}`
updates supported metadata and schema fields; it is not a general rich-text editor.
`GET /entries` supports `projectId`, `schemaId`, `modifiedAt`, and other documented
filters, but does not expose `folderId` in the stable SDK's list method.
`GET /entry-templates` and `/entry-templates/{entryTemplateId}` discover templates.
There is no general `entry_links` service to attach arbitrary objects to an entry.

`POST /workflow-tasks` requires a task group:

```json
{"workflowTaskGroupId": "wtg_example", "assigneeId": "usr_example"}
```

`GET /workflow-tasks` accepts comma-separated `workflowTaskGroupIds`, `statusIds`, and
`assigneeIds`, plus `schemaId` and pagination. `PATCH /workflow-tasks/{workflowTaskId}`
can set `statusId`, `assigneeId`, `scheduledOn`, and `fields`. Status IDs come from the
workflow task schema; there is no `workflowId` create/list field here.

`POST /folders` takes `name` and `parentFolderId`; the parent determines the project.
Do not add a `projectId` to `FolderCreate`. Folder listing does accept `projectId` and
`parentFolderId` filters.

## Async jobs and events

`GET /tasks/{taskId}` polls an asynchronous server job; it is not the workflow-task
CRUD endpoint. Responses contain `status` (`RUNNING`, `SUCCEEDED`, `FAILED`) and
operation-specific `response`, `errors`, or `message` when applicable. Timeout on the
client does not cancel the job. Keep the task ID and check its final outcome.

`GET /events` returns `events` with `nextToken`. Filters include `createdAt.gte`,
`startingAfter` (event ID), `eventTypes` (comma-separated), `poll`, and `pageSize`.
The SDK spelling is `created_atgte`. Events are sorted by processing order, not by
`createdAt`; never terminate recovery early merely because a timestamp is out of order.
See [event recovery](eventbridge.md) for retention and deduplication.

## Field values

The `fields` mapping is keyed by actual schema field names, with a `value` member:

```json
{
  "passage_number": {"value": 15},
  "comment": {"value": "QC passed"},
  "linked_entities": {"value": ["seq_example"]},
  "selection": {"value": ["sfso_example"]}
}
```

Use schema-defined scalar/list multiplicity. Dropdown values are option IDs, not
human option labels. Numeric fields accept numeric values; date/datetime formats depend
on the field definition. `null` is distinct from omission and may clear a value.
See [schema field types](https://docs.benchling.com/docs/schemas).

## Errors and limits

Failures normally use an `error` object with `message`, `type`, and sometimes
`userMessage`. Do not assume exception-class names like `RateLimitError` appear in JSON.
Check HTTP status before reading success data: 400 invalid request, 401 authentication,
403 permission, 404 missing/inaccessible resource, 429 throttling, and 5xx server errors.
A successful check-in or single-container transfer returns an empty JSON object.

The [V2 limits guide](https://docs.benchling.com/docs/rate-limiting) currently lists
60 requests/30 seconds across user keys per tenant, 300/30 seconds per app, and
1000/30 seconds across apps per tenant. There are separate dynamic throughput limits.
The response headers are `x-rate-limit-limit`, `x-rate-limit-remaining`, and
`x-rate-limit-reset`; **reset is seconds remaining, not an epoch timestamp**.

Use bounded exponential backoff with jitter for 429/transient server failures and honor
server retry guidance when present. Do not invent a JSON `retryAfter` field or recurse
without an attempt limit. Reconcile ambiguous write failures before repeating creates.

## Direct pagination example

This illustrative read-only example uses `httpx`, checks status, and preserves filters:

```python
import os
import httpx

with httpx.Client(
    base_url=os.environ["BENCHLING_TENANT_URL"].rstrip("/") + "/api/v2/",
    auth=(os.environ["BENCHLING_API_KEY"], ""),
    timeout=30.0,
) as client:
    params = {"pageSize": 100, "schemaId": "ts_example"}
    while True:
        response = client.get("dna-sequences", params=params)
        response.raise_for_status()
        data = response.json()
        for sequence in data["dnaSequences"]:
            print(sequence["id"], sequence["name"])
        next_token = data.get("nextToken")
        if not next_token:
            break
        params["nextToken"] = next_token
```
