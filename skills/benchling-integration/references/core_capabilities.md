# Core Capabilities

Reviewed against Benchling's current platform documentation and SDK 1.25.0 on
2026-09-30. Executable patterns are centralized in [SDK reference](sdk_reference.md);
all tenant-specific writes are illustrative and require actual schemas and permissions.

## 1. Authentication and setup

Use OAuth app credentials for scheduled jobs and integration services. Actions are
attributed to the app, not an end user. Use delegated authorization for user attribution.
Personal API keys remain available for temporary use. See [authentication](authentication.md)
for current expiration rules, token paths, and legacy OIDC boundaries.

Start with a small list query for an accessible project/resource. An empty authorized
response is valid; do not use nonexistent `users.get_me()` as a connectivity check.

## 2. Registry and entity management

Manage DNA, RNA, AA sequences, custom entities, and mixtures using their typed SDK
services. Read the relevant entity schema through `benchling.schemas` first.

For create-and-register, supply a registry ID plus either a human entity registry ID or
a naming strategy. Preserve the distinction between an API entity ID, a human registry
identifier, and a registry ID. Required fields and naming rules are tenant-specific.

For sequence imports, preserve the original record identifier and evidence of alphabet,
length, topology, translation frame, and any transformations. A successfully registered
construct does not establish the correctness of the sequence or biological annotation.
Use returned IDs to reconcile interrupted imports and avoid accidental duplication.

## 3. Inventory

Containers hold biological contents; locations, boxes, and plates organize storage.
Schema IDs are required for creation of these inventory types. A physical container move
updates `parent_storage_id`; material transfer changes contents/amounts and is performed
through transfer APIs. Check-in/out tracks custody and does not substitute for either.

Resolve storage position/well IDs from actual records. Check quantity units and source
availability before transfers. Do not represent tracked volume or content concentration
by writing a similarly named custom text field. Read back quantities and contents after
an operation, and preserve sample provenance through splits, pooling, and aliquoting.

## 4. Notebook and documentation

Use `entries.create_entry`, `get_entry_by_id`, `list_entries`, and `update_entry`.
Entry creation supports templates and initial tables; metadata updates are not general
rich-text editing. Inspect the supported entry/template models before promising an
arbitrary notebook modification. There is no general `entry_links` service in 1.25.0.

Relationships should use the applicable schema field, table, result, or template
mechanism. Keep experiment provenance linked to the underlying entity and result IDs.

## 5. Workflows and automation

Workflow tasks belong to workflow task groups. Create with `workflow_task_group_id`,
filter with `workflow_task_group_ids` and `status_ids`, and update with
`workflow_task_id`. Resolve statuses from the workflow schema rather than assuming
literal strings such as `pending` or `complete` are IDs.

Workflow tasks (`/workflow-tasks`) are distinct from async processing jobs (`/tasks/{id}`).
Polling returns at completion even if the job failed. Retain a job's ID after timeouts,
inspect its status, and reconcile results before resubmitting a mutation.

## 6. Events and integrations

Benchling recommends webhooks for new apps; AWS EventBridge remains useful for existing
AWS integrations. Payloads, subscription mechanisms, event names, and permissions differ.
Do not substitute generic DNA-created/updated names for documented EventBridge event
names. See [EventBridge](eventbridge.md) for examples using `v2.entity.registered`,
`v2.entry.created`, `v2.entry.updated.fields`, and `v2.workflowTask.updated.status`.

Deduplicate by Benchling event ID, allow out-of-order delivery, and re-fetch authoritative
state. Recover historical EventBridge events within their retention window; recovery is
not a complete backup or an alternative to a reconciliation query.

## 7. Warehouse and analytics

The [warehouse](https://docs.benchling.com/docs/getting-started) is read-only PostgreSQL
with separately issued credentials. It is not a REST endpoint, and API OAuth tokens do
not authenticate database connections. Use the exact host, database, user, TLS settings,
and permissions provided for your tenant; do not invent table names from REST paths.

For scientific exports, record query text, extraction time, schema version, relevant
entity IDs, units, and inclusion/exclusion of archived records. Warehouse replication is
not real-time, so use API reads for immediate post-write validation. Consult the
[warehouse tables](https://docs.benchling.com/docs/wh-registry) for joins and archived/raw
views, and [limits](https://docs.benchling.com/docs/rate-limiting) for connection and
transaction guidance. Keep transactions short and avoid high-frequency polling.
