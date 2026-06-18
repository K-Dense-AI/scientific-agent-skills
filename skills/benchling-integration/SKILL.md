---
name: benchling-integration
description: Benchling Python SDK and REST API integration for registry entities, inventory, ELN entries, workflows, Benchling Apps, and Data Warehouse queries. Use when automating lab data with benchling-sdk or the v2 API.
license: MIT
allowed-tools: Read Write Edit Bash
compatibility: Requires a Benchling account, tenant URL, and API key or OAuth app credentials. Install benchling-sdk with uv pip install.
required_environment_variables: [{"name": "BENCHLING_TENANT_URL", "prompt": "Benchling tenant base URL.", "required_for": "full functionality"}, {"name": "BENCHLING_API_KEY", "prompt": "API key auth (alternative to OAuth).", "required_for": "optional features"}, {"name": "BENCHLING_CLIENT_ID", "prompt": "OAuth app client id.", "required_for": "optional features"}, {"name": "BENCHLING_CLIENT_SECRET", "prompt": "OAuth app client secret.", "required_for": "optional features"}, {"name": "BENCHLING_PROD_TENANT_URL", "prompt": "Production tenant URL (multi-env setups).", "required_for": "optional features"}, {"name": "BENCHLING_PROD_API_KEY", "prompt": "Production API key (multi-env setups).", "required_for": "optional features"}, {"name": "BENCHLING_STAGING_TENANT_URL", "prompt": "Staging tenant URL (multi-env setups).", "required_for": "optional features"}, {"name": "BENCHLING_STAGING_API_KEY", "prompt": "Staging API key (multi-env setups).", "required_for": "optional features"}]
metadata: {"version": "1.3", "skill-author": "K-Dense Inc.", "openclaw": {"primaryEnv": "BENCHLING_API_KEY", "envVars": [{"name": "BENCHLING_TENANT_URL", "required": true, "description": "Benchling tenant base URL."}, {"name": "BENCHLING_API_KEY", "required": false, "description": "API key auth (alternative to OAuth)."}, {"name": "BENCHLING_CLIENT_ID", "required": false, "description": "OAuth app client id."}, {"name": "BENCHLING_CLIENT_SECRET", "required": false, "description": "OAuth app client secret."}, {"name": "BENCHLING_PROD_TENANT_URL", "required": false, "description": "Production tenant URL (multi-env setups)."}, {"name": "BENCHLING_PROD_API_KEY", "required": false, "description": "Production API key (multi-env setups)."}, {"name": "BENCHLING_STAGING_TENANT_URL", "required": false, "description": "Staging tenant URL (multi-env setups)."}, {"name": "BENCHLING_STAGING_API_KEY", "required": false, "description": "Staging API key (multi-env setups)."}]}}
---

# Benchling Integration

## Overview

Benchling is a cloud platform for life sciences R&D. Access registry entities (DNA, RNA, proteins), inventory, electronic lab notebooks, and workflows programmatically via the Python SDK and REST API.

**Version note:** Examples target **benchling-sdk 1.25.0** (latest stable on PyPI). Docs: [benchling.com/sdk-docs](https://benchling.com/sdk-docs/). Platform guide: [docs.benchling.com](https://docs.benchling.com/).

## When to Use This Skill

This skill should be used when:
- Working with Benchling's Python SDK or REST API
- Managing biological sequences (DNA, RNA, proteins) and registry entities
- Automating inventory operations (samples, containers, locations, transfers)
- Creating or querying electronic lab notebook entries
- Building workflow automations or Benchling Apps
- Syncing data between Benchling and external systems
- Querying the Benchling Data Warehouse for analytics
- Setting up event-driven integrations with AWS EventBridge

## Core Capabilities

### 1. Authentication & Setup

**Python SDK installation:**

```bash
uv pip install "benchling-sdk==1.25.0"
```

Preview builds (alpha; not for production):

```bash
uv pip install "benchling-sdk" --prerelease allow
```

**Environment variables (scoped reads only):**

Read only the named keys you need — never dump or iterate over the full environment:

```python
import os

tenant_url = os.environ.get("BENCHLING_TENANT_URL")  # e.g. https://your-tenant.benchling.com
api_key = os.environ.get("BENCHLING_API_KEY")

if not tenant_url or not api_key:
    raise ValueError("Set BENCHLING_TENANT_URL and BENCHLING_API_KEY")
```

Obtain an API key from **Profile Settings** in Benchling. For OAuth apps, use the [Developer Console](https://docs.benchling.com/docs/getting-started-benchling-apps) and store `BENCHLING_CLIENT_ID` / `BENCHLING_CLIENT_SECRET` separately.

**Authentication methods:**

API key (scripts and personal automation):

```python
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth

benchling = Benchling(
    url=tenant_url,
    auth_method=ApiKeyAuth(api_key),
)
```

OAuth client credentials (multi-user apps and production integrations):

```python
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.client_credentials_oauth2 import ClientCredentialsOAuth2

benchling = Benchling(
    url=tenant_url,
    auth_method=ClientCredentialsOAuth2(
        client_id=os.environ["BENCHLING_CLIENT_ID"],
        client_secret=os.environ["BENCHLING_CLIENT_SECRET"],
    ),
)
```

**Key points:**
- All API requests require HTTPS; network calls must target your tenant URL only
- Authentication permissions mirror UI permissions
- Verify credentials with `benchling.users.get_me()` before bulk operations

For detailed authentication information including OIDC and security best practices, refer to `references/authentication.md`.

### 2. Registry & Entity Management

Registry entities include DNA sequences, RNA sequences, AA sequences, custom entities, and mixtures. The SDK provides typed classes for creating and managing these entities.

**Creating DNA Sequences:**
```python
from benchling_sdk.models import DnaSequenceCreate

sequence = benchling.dna_sequences.create(
    DnaSequenceCreate(
        name="My Plasmid",
        bases="ATCGATCG",
        is_circular=True,
        folder_id="fld_abc123",
        schema_id="ts_abc123",  # optional
        fields=benchling.models.fields({"gene_name": "GFP"})
    )
)
```

**Registry Registration:**

To register an entity directly upon creation:
```python
sequence = benchling.dna_sequences.create(
    DnaSequenceCreate(
        name="My Plasmid",
        bases="ATCGATCG",
        is_circular=True,
        folder_id="fld_abc123",
        entity_registry_id="src_abc123",  # Registry to register in
        naming_strategy="NEW_IDS"  # or "IDS_FROM_NAMES"
    )
)
```

**Important:** Use either `entity_registry_id` OR `naming_strategy`, never both.

**Updating Entities:**
```python
from benchling_sdk.models import DnaSequenceUpdate

updated = benchling.dna_sequences.update(
    sequence_id="seq_abc123",
    dna_sequence=DnaSequenceUpdate(
        name="Updated Plasmid Name",
        fields=benchling.models.fields({"gene_name": "mCherry"})
    )
)
```

Unspecified fields remain unchanged, allowing partial updates.

**Listing and Pagination:**
```python
# List all DNA sequences (returns a generator)
sequences = benchling.dna_sequences.list()
for page in sequences:
    for seq in page:
        print(f"{seq.name} ({seq.id})")

# Check total count
total = sequences.estimated_count()
```

**Key Operations:**
- Create: `benchling.<entity_type>.create()`
- Read: `benchling.<entity_type>.get_by_id(id)` or `.list()`
- Update: `benchling.<entity_type>.update(id, update_object)`
- Archive: `benchling.<entity_type>.archive(id)`

Entity types: `dna_sequences`, `rna_sequences`, `aa_sequences`, `custom_entities`, `mixtures`

For comprehensive SDK reference and advanced patterns, refer to `references/sdk_reference.md`.

### 3. Inventory Management

Manage physical samples, containers, boxes, and locations within the Benchling inventory system.

**Creating Containers:**
```python
from benchling_sdk.models import ContainerCreate

container = benchling.containers.create(
    ContainerCreate(
        name="Sample Tube 001",
        schema_id="cont_schema_abc123",
        parent_storage_id="box_abc123",  # optional
        fields=benchling.models.fields({"concentration": "100 ng/μL"})
    )
)
```

**Managing Boxes:**
```python
from benchling_sdk.models import BoxCreate

box = benchling.boxes.create(
    BoxCreate(
        name="Freezer Box A1",
        schema_id="box_schema_abc123",
        parent_storage_id="loc_abc123"
    )
)
```

**Transferring Items:**
```python
# Transfer a container to a new location
transfer = benchling.containers.transfer(
    container_id="cont_abc123",
    destination_id="box_xyz789"
)
```

**Key Inventory Operations:**
- Create containers, boxes, locations, plates
- Update inventory item properties
- Transfer items between locations
- Check in/out items
- Batch operations for bulk transfers

### 4. Notebook & Documentation

Interact with electronic lab notebook (ELN) entries, protocols, and templates.

**Creating Notebook Entries:**
```python
from benchling_sdk.models import EntryCreate

entry = benchling.entries.create(
    EntryCreate(
        name="Experiment 2025-10-20",
        folder_id="fld_abc123",
        schema_id="entry_schema_abc123",
        fields=benchling.models.fields({"objective": "Test gene expression"})
    )
)
```

**Linking Entities to Entries:**
```python
# Add references to entities in an entry
entry_link = benchling.entry_links.create(
    entry_id="entry_abc123",
    entity_id="seq_xyz789"
)
```

**Key Notebook Operations:**
- Create and update lab notebook entries
- Manage entry templates
- Link entities and results to entries
- Export entries for documentation

### 5. Workflows & Automation

Automate laboratory processes using Benchling's workflow system.

**Creating Workflow Tasks:**
```python
from benchling_sdk.models import WorkflowTaskCreate

task = benchling.workflow_tasks.create(
    WorkflowTaskCreate(
        name="PCR Amplification",
        workflow_id="wf_abc123",
        assignee_id="user_abc123",
        fields=benchling.models.fields({"template": "seq_abc123"})
    )
)
```

**Updating Task Status:**
```python
from benchling_sdk.models import WorkflowTaskUpdate

updated_task = benchling.workflow_tasks.update(
    task_id="task_abc123",
    workflow_task=WorkflowTaskUpdate(
        status_id="status_complete_abc123"
    )
)
```

**Asynchronous Operations:**

Some operations are asynchronous and return tasks. The SDK default `max_wait_seconds` for polling is **600 seconds** (since SDK 1.11.0):

```python
from benchling_sdk.helpers.tasks import wait_for_task

result = wait_for_task(
    benchling,
    task_id="task_abc123",
    interval_wait_seconds=2,
    max_wait_seconds=300,  # override for long-running serverless handlers
)
```

**Key Workflow Operations:**
- Create and manage workflow tasks
- Update task statuses and assignments
- Execute bulk operations asynchronously
- Monitor task progress

### 6. Events & Integration

Subscribe to Benchling changes via **AWS EventBridge** (customer-owned bus) or **Webhooks** (recommended for new Benchling Apps). EventBridge delivers hydrated v2 API objects; webhooks use thinner payloads.

**Common EventBridge `detail-type` values:**
- `v2.dnaSequence.created`, `v2.dnaSequence.updated`
- `v2.entity.registered`
- `v2.entry.created`, `v2.entry.updated`
- `v2.workflowTask.updated.status`
- `v2.request.created`

**Minimal EventBridge rule** (filter request creation by schema name):

```json
{
  "detail-type": ["v2.request.created"],
  "detail": {
    "schema": {
      "name": ["Validated Request"]
    }
  }
}
```

**Lambda handler skeleton:**

```python
def handler(event, context):
    detail_type = event["detail-type"]
    detail = event["detail"]

    if detail.get("deprecated"):
        # Alert — migrate before Benchling removes this event type
        pass

    if detail.get("excludedProperties"):
        # Payload exceeded 256 KB; re-fetch via detail["request"]["apiURL"]
        pass

    if detail_type == "v2.request.created":
        request_id = (detail.get("request") or {}).get("id")
        # Re-fetch authoritative state — events can be late or out of order
        # request = benchling.requests.get_by_id(request_id)
        return {"request_id": request_id}

    return {"status": "ignored", "detail_type": detail_type}
```

**Setup flow:**
1. Tenant admin creates a subscription at `https://your-tenant.benchling.com/event-subscriptions`
2. Associate the AWS partner event source with a dedicated event bus immediately (within ~12 days)
3. Create rules + targets (Lambda, SQS, SNS) and grant invoke permissions
4. Validate with a CloudWatch Logs rule, then trigger a matching Benchling action

**Recovery:** EventBridge deliveries are not replayed. Use the [List Events API](https://benchling.com/api/reference#/Events/listEvents) for events up to ~2 weeks old after outages.

For payload schema, CloudFormation templates, SDK list/recovery examples, and validation steps, see `references/eventbridge.md`.

### 7. Data Warehouse & Analytics

Query historical Benchling data using SQL through the Data Warehouse.

**Access Method:**
The Benchling Data Warehouse provides SQL access to Benchling data for analytics and reporting. Connect using standard SQL clients with provided credentials.

**Common Queries:**
- Aggregate experimental results
- Analyze inventory trends
- Generate compliance reports
- Export data for external analysis

**Integration with Analysis Tools:**
- Jupyter notebooks for interactive analysis
- BI tools (Tableau, Looker, PowerBI)
- Custom dashboards

## Best Practices

### Error Handling

The SDK automatically retries failed requests:
```python
# Automatic retry for 429, 502, 503, 504 status codes
# Up to 5 retries with exponential backoff
# Customize retry behavior if needed
from benchling_sdk.retry import RetryStrategy

benchling = Benchling(
    url=tenant_url,
    auth_method=ApiKeyAuth(api_key),
    retry_strategy=RetryStrategy(max_retries=3),
)
```

### Pagination Efficiency

Use generators for memory-efficient pagination:
```python
# Generator-based iteration
for page in benchling.dna_sequences.list():
    for sequence in page:
        process(sequence)

# Check estimated count without loading all pages
total = benchling.dna_sequences.list().estimated_count()
```

### Schema Fields Helper

Use the `fields()` helper for custom schema fields:
```python
# Convert dict to Fields object
custom_fields = benchling.models.fields({
    "concentration": "100 ng/μL",
    "date_prepared": "2025-10-20",
    "notes": "High quality prep"
})
```

### Forward Compatibility

The SDK handles unknown enum values and types gracefully:
- Unknown enum values are preserved
- Unrecognized polymorphic types return `UnknownType`
- Allows working with newer API versions

### Security Considerations

- Never commit API keys or OAuth secrets to version control
- Read only named environment variables (`BENCHLING_TENANT_URL`, `BENCHLING_API_KEY`, etc.)
- Route network calls exclusively to your tenant URL
- Rotate keys if compromised; use OAuth for multi-user production apps
- Grant minimal necessary permissions for apps in the Developer Console

## Resources

### references/

Detailed reference documentation for in-depth information:

- **authentication.md** - Comprehensive authentication guide including OIDC, security best practices, and credential management
- **sdk_reference.md** - Detailed Python SDK reference with advanced patterns, examples, and all entity types
- **api_endpoints.md** - REST API endpoint reference for direct HTTP calls without the SDK
- **eventbridge.md** - EventBridge setup, event payload schema, rule examples, Lambda handler, validation, and recovery

Load these references as needed for specific integration requirements.

## Common Use Cases

**1. Bulk Entity Import:**
```python
# Import multiple sequences from FASTA file
from Bio import SeqIO

for record in SeqIO.parse("sequences.fasta", "fasta"):
    benchling.dna_sequences.create(
        DnaSequenceCreate(
            name=record.id,
            bases=str(record.seq),
            is_circular=False,
            folder_id="fld_abc123"
        )
    )
```

**2. Inventory Audit:**
```python
# List all containers in a specific location
containers = benchling.containers.list(
    parent_storage_id="box_abc123"
)

for page in containers:
    for container in page:
        print(f"{container.name}: {container.barcode}")
```

**3. Workflow Automation:**
```python
# Update all pending tasks for a workflow
tasks = benchling.workflow_tasks.list(
    workflow_id="wf_abc123",
    status="pending"
)

for page in tasks:
    for task in page:
        # Perform automated checks
        if auto_validate(task):
            benchling.workflow_tasks.update(
                task_id=task.id,
                workflow_task=WorkflowTaskUpdate(
                    status_id="status_complete"
                )
            )
```

**4. Data Export:**
```python
# Export all sequences with specific properties
sequences = benchling.dna_sequences.list()
export_data = []

for page in sequences:
    for seq in page:
        if seq.schema_id == "target_schema_id":
            export_data.append({
                "id": seq.id,
                "name": seq.name,
                "bases": seq.bases,
                "length": len(seq.bases)
            })

# Save to CSV or database
import csv
with open("sequences.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=export_data[0].keys())
    writer.writeheader()
    writer.writerows(export_data)
```

## Additional Resources

- **Official Documentation:** https://docs.benchling.com
- **Python SDK Reference:** https://benchling.com/sdk-docs/
- **API Reference:** https://benchling.com/api/reference
- **Support:** [email protected]

