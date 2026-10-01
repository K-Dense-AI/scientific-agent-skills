# Benchling Python SDK Reference

Targets **1.25.0**, the stable release verified on 2026-09-30. Python requirement:
`>=3.9,<4`. Install with `uv pip install "benchling-sdk==1.25.0"`.
Examples assume an initialized `benchling` client from [authentication](authentication.md).
All IDs and schema fields are placeholders. Model serialization and request construction
were tested offline; server behavior remains illustrative until checked in your tenant.

Source of truth: [versioned SDK reference](https://benchling.com/sdk-docs/1.25.0/index.html)
and the released `benchling-sdk` / `benchling-api-client` Python packages. The
[interaction guide](https://docs.benchling.com/docs/common-sdk-interactions-and-examples)
explains the patterns; use installed signatures when guide snippets differ.

## Schemas and fields

```python
from benchling_sdk.helpers.serialization_helpers import fields

custom_fields = fields({
    "concentration": {"value": 100.0},
    "notes": {"value": "QC passed"},
})
schema = benchling.schemas.get_entity_schema_by_id("ts_example")
```

Use actual field names, numeric types, units, multiplicity, and dropdown **option IDs**
from the schema. `fields()` is a serializer, not schema validation. A field named
`concentration` may be a custom number; it is not the inventory contents concentration.
Omitting a field preserves it on a partial update; `{"value": None}` explicitly clears it
when allowed. Do not confuse `fields` with the free-text `custom_fields` property.

## Registry entities

### DNA: create, register, read, update, archive

```python
from benchling_sdk.models import (
    DnaSequenceCreate, DnaSequenceUpdate, EntityArchiveReason, NamingStrategy,
)
from benchling_sdk.helpers.serialization_helpers import fields

payload = DnaSequenceCreate(
    name="Construct-001",
    bases="ATCGATCG",
    is_circular=True,
    folder_id="lib_example",
    schema_id="ts_example",
    registry_id="src_example",
    naming_strategy=NamingStrategy.NEW_IDS,
    fields=fields({"gene_name": {"value": "GFP"}}),
)
sequence = benchling.dna_sequences.create(payload)
print(sequence.id, sequence.entity_registry_id)
sequence = benchling.dna_sequences.get_by_id(sequence.id)
updated = benchling.dna_sequences.update(
    dna_sequence_id=sequence.id,
    dna_sequence=DnaSequenceUpdate(
        fields=fields({"gene_name": {"value": "mCherry"}}),
    ),
)
```

For an unregistered entity omit `registry_id` and the naming arguments. For an explicit
human registry ID, replace `naming_strategy` with `entity_registry_id="CONSTRUCT001"`.
These are mutually exclusive. Required schema fields are enforced during registration.
`sequence.id` is the API ID; `sequence.entity_registry_id` is the human registry ID.

Archival is a separate requested operation, with an iterable of IDs and an enum:

```python
benchling.dna_sequences.archive(
    dna_sequence_ids=["seq_example"],
    reason=EntityArchiveReason.RETIRED,
)
```

### RNA, proteins, and custom entities

```python
from benchling_sdk.models import (
    RnaSequenceCreate, RnaSequenceUpdate, AaSequenceCreate,
    CustomEntityCreate, CustomEntityUpdate,
)

rna = benchling.rna_sequences.create(RnaSequenceCreate(
    name="gRNA-001", bases="AUCGAUCG", is_circular=False,
    folder_id="lib_example",
))
benchling.rna_sequences.update(
    rna_sequence_id=rna.id,
    rna_sequence=RnaSequenceUpdate(name="gRNA-001-validated"),
)
protein = benchling.aa_sequences.create(AaSequenceCreate(
    name="Peptide-001", amino_acids="MSKGEELFTGVVPIL",
    folder_id="lib_example",
))
cell_line = benchling.custom_entities.create(CustomEntityCreate(
    name="HEK293T-Clone5", schema_id="ts_cellline", folder_id="lib_example",
    fields=fields({"passage_number": {"value": 15}}),
))
benchling.custom_entities.update(
    entity_id=cell_line.id,
    entity=CustomEntityUpdate(fields=fields({"passage_number": {"value": 16}})),
)
```

### Mixtures

`IngredientWriteParams` uses separate amount and units, with explicit nullable provenance
fields. There is no `IngredientCreate` in this release.

```python
from benchling_sdk.models import MixtureCreate, IngredientWriteParams, IngredientMeasurementUnits

ingredient = IngredientWriteParams(
    component_entity_id="bfi_component",
    amount="100", units=IngredientMeasurementUnits.MG,
    catalog_identifier=None, component_lot_container_id=None,
    component_lot_entity_id=None, component_lot_text=None, notes=None,
)
mixture = benchling.mixtures.create(MixtureCreate(
    name="Example formulation", schema_id="ts_mixture", folder_id="lib_example",
    ingredients=[ingredient],
))
```

Resolve ingredient identity/lot and measurement dimensions before transfer or formulation;
serialization does not establish material balance or concentration correctness.

## Inventory

### Storage and physical movement

```python
from benchling_sdk.models import ContainerCreate, ContainerUpdate, BoxCreate, LocationCreate

location = benchling.locations.create(LocationCreate(
    name="Freezer A - Shelf 2", schema_id="locsch_example",
    parent_storage_id="loc_freezer",
))
box = benchling.boxes.create(BoxCreate(
    name="Box 01", schema_id="boxsch_example", parent_storage_id=location.id,
))
container = benchling.containers.create(ContainerCreate(
    name="Sample 001", schema_id="consch_example", parent_storage_id=box.id,
))
moved = benchling.containers.update(
    container_id=container.id,
    container=ContainerUpdate(parent_storage_id="loc_destination"),
)
for page in benchling.containers.list(ancestor_storage_id=box.id):
    for item in page:
        print(item.id, item.name)
```

When placing a container into a box, resolve the supported box position identifier from
the box contents/reference; don't guess coordinates or assume every box has free space.

### Check out and in

```python
from benchling_sdk.models import ContainersCheckout, ContainersCheckin

benchling.containers.checkout(ContainersCheckout(
    assignee_id="usr_example", container_ids=["con_example"], comment="At bench",
))
benchling.containers.checkin(ContainersCheckin(
    container_ids=["con_example"], comments="Returned",
))
```

Check-in does not take a `location_id`. Change physical storage separately if needed.

### Plates and material transfer

```python
from benchling_sdk.models import PlateCreate

plate = benchling.plates.create(PlateCreate(
    name="PCR plate", schema_id="pltsch_example", barcode="PLATE001",
))
```

`PlateCreate.wells`, when used, is a `PlateCreateWells` mapping of positions to well
creation properties (for example barcodes), not a list of `WellCreate` entity assignments.
Read back well/container IDs, then transfer contents with the container service.

```python
from benchling_sdk.models import MultipleContainersTransfer, ContainerQuantity, ContainerQuantityUnits

transfer_task = benchling.containers.transfer_into_containers([
    MultipleContainersTransfer(
        source_container_id="con_source",
        destination_container_id="con_destination",
        transfer_quantity=ContainerQuantity(units=ContainerQuantityUnits.UL, value=5.0),
    ),
])
completion = transfer_task.wait_for_completion(max_wait_seconds=60)
if not completion.success:
    raise RuntimeError("Benchling material transfer failed; inspect completion.errors")
```

This calls `POST /api/v2/transfers` and returns a `TaskHelper`. Check `completion.success` and
`completion.errors` before consuming `completion.response`. Single-destination transfer uses
`transfer_into_container(destination_container_id, ContainerTransfer(...))`, with
`destination_contents`; it is a different payload. Neither method moves a tube to a box.

## Notebook

```python
from benchling_sdk.models import EntryCreate, EntryUpdate

entry = benchling.entries.create_entry(EntryCreate(
    name="Cloning experiment", folder_id="lib_example",
))
entry = benchling.entries.get_entry_by_id(entry.id)
updated_entry = benchling.entries.update_entry(
    entry_id=entry.id, entry=EntryUpdate(name="Cloning experiment - reviewed"),
)
for page in benchling.entries.list_entries(project_id="src_project", page_size=10):
    for item in page:
        print(item.id, item.name)
    break
```

Use `entry_template_id` and `initial_tables` for supported template-based creation.
`EntryUpdate` updates metadata/schema fields; it is not arbitrary rich-text editing.
There is no `benchling.entry_links` service in 1.25.0. Use supported schema link fields
or template/table mechanisms for the intended relationship. Discover actual template
requirements with `entries.get_entry_template_by_id` and `entries.list_entry_templates`.

## Workflow tasks versus async tasks

```python
from benchling_sdk.models import WorkflowTaskCreate, WorkflowTaskUpdate

task = benchling.workflow_tasks.create(WorkflowTaskCreate(
    workflow_task_group_id="wtg_example", assignee_id="usr_example",
))
updated_task = benchling.workflow_tasks.update(
    workflow_task_id=task.id,
    workflow_task=WorkflowTaskUpdate(status_id="wts_complete"),
)
for page in benchling.workflow_tasks.list(
    workflow_task_group_ids=["wtg_example"], status_ids=["wts_pending"],
):
    for item in page:
        print(item.id)
```

Resolve status IDs from the workflow task schema. There is no `workflow_id` filter or
`name`/`schema_id` constructor field on `WorkflowTaskCreate` in this SDK. The task group
provides workflow context. Validate scientific completion before changing a status.

Async server jobs are a separate service and endpoint:

```python
from benchling_sdk.models import AsyncTaskStatus
from benchling_sdk.errors import WaitForTaskExpiredError

try:
    finished = benchling.tasks.wait_for_task(
        task_id="task_example", interval_wait_seconds=2, max_wait_seconds=60,
    )
    if finished.status != AsyncTaskStatus.SUCCEEDED:
        raise RuntimeError(f"Benchling job ended with {finished.status}")
except WaitForTaskExpiredError:
    # The server job can continue after the local timeout. Save its ID for later polling.
    print("[FAIL] Polling deadline reached; inspect task_example before resubmission")
```

The default polling deadline is 600 seconds. `wait_for_task` returns on terminal failure
as well as success; do not treat return alone as a successful operation.

## Pagination, errors, and retries

```python
sequences = benchling.dna_sequences.list(schema_id="ts_example", page_size=50)
try:
    total = sequences.estimated_count
except NotImplementedError:
    total = None
for page in sequences:
    for seq in page:
        print(seq.id, seq.name)
```

The iterator is consumable once; create another for another pass. Count access may fetch
a page and counts are approximate. `returning` can omit model attributes; do not access
an unrequested property as if it were a complete resource.

```python
from benchling_sdk.errors import BenchlingError

try:
    sequence = benchling.dna_sequences.get_by_id("seq_example")
except BenchlingError as error:
    print(f"[FAIL] Benchling HTTP status {error.status_code}")
    raise
```

`BenchlingError` covers HTTP failures; transport and parsing errors can still surface
separately. Avoid logging request headers or sensitive response bodies.

```python
from benchling_sdk.helpers.retry_helpers import RetryStrategy

retry_strategy = RetryStrategy(max_tries=3, backoff_factor=1.0)
```

Pass this to `Benchling(..., retry_strategy=retry_strategy)`. Default `max_tries=5`
counts total attempts; default retry codes are 429, 502, 503, and 504. Set
`retry_strategy=None` to disable. Retrying a write after an ambiguous failure requires
reconciliation; do not assume every create is idempotent.

## Direct requests and model compatibility

For a documented endpoint not wrapped by a service, use its exact path and response
shape. `api.get_response` returns a `Response` whose `parsed` value is a dictionary:

```python
response = benchling.api.get_response(url="/api/v2/projects?pageSize=1")
projects = response.parsed["projects"]
```

`get_modeled(url, target_type)` and `post_modeled(url, target_type, body=...)` use
SDK deserializable models. Use the endpoint's actual response model; a list envelope is not a single resource. Unknown enums/polymorphic responses are preserved where
supported, but new values still need application handling; successful deserialization
does not mean the integration understands their scientific meaning.
