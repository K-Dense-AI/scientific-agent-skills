# Materials Project API: bounded queries, provenance, and computed-data limits

This reference targets `mp-api==0.46.5` (released 2026-08-18) with
`pymatgen==2026.9.24` and `pymatgen-core==2026.9.23`. `mp-api` requires Python
3.11+ and depends on `pymatgen>2024.2.20`.

Use the separate official client:

```python
from mp_api.client import MPRester
```

Do not use a legacy Materials Project client import from older pymatgen
examples.

Verification on 2026-09-30 used current official guides, the current OpenAPI
schema captured during this review, installed 0.46.5 SDK source and mocked
transports. A repeat OpenAPI request returned HTTP 403; protected endpoints were
not exercised with credentials. Network examples in
this reference are illustrative, not authenticated end-to-end tests.

## Installation

Pin the tested client and materials stack:

```bash
uv add "pymatgen==2026.9.24" "pymatgen-core==2026.9.23" "mp-api==0.46.5"
uv lock
uv sync --frozen
```

The 0.46.5 package metadata declares direct dependencies including
`pymatgen>2024.2.20`, `monty>=2024.12.10`, `emmet-core>=0.87.1`,
`requests>=2.23.0`, `orjson>=3.10,<4`, `pyarrow>=20`, and
`deltalake>=1.4,<1.6`, plus boto3 and typing extensions. A lockfile is needed
to freeze transitive artifacts.

## Authentication: one named secret

An API key is required and is available from the logged-in Materials Project
[dashboard](https://next-gen.materialsproject.org/dashboard).

The approved pattern is:

```python
from mp_api.client import MPRester

# Inject MP_API_KEY before execution; keep this workflow on the official host.
with MPRester(endpoint="https://api.materialsproject.org/") as rester:
    pass
```

Operational rules:

- use only the environment variable `MP_API_KEY`
- inject it through the user's shell/session secret manager
- never accept it as a command-line argument
- never embed it in code, notebooks, URLs, cache files, or manifests
- never traverse dot-env files or dump the environment
- never print the key or unredacted exceptions that might contain it
- do not send it anywhere except the official Materials Project API endpoint

The bundled query CLI follows these rules and reads the variable only after
`--execute`.

## Query contract before network

Before any request, disclose:

1. endpoint and `mp-api` version
2. all filters
3. exact response fields
4. `num_chunks`, `chunk_size`, and maximum serialized bytes
5. cache reads/writes
6. output path and no-overwrite behavior
7. API-key source by name, never value
8. data license, citation, provenance, and scientific limitations

The dry-run planner:

```bash
python scripts/mp_query.py \
  --chemsys Li-Fe-O \
  --energy-above-hull 0 0.05 \
  --fields formula_pretty,energy_above_hull,band_gap,origins \
  --limit 25
```

Only an explicit execution permits the disclosed network workflow:

```bash
python scripts/mp_query.py \
  --material-id mp-149 \
  --fields formula_pretty,structure,origins,last_updated \
  --limit 1 --output mp-149.json --execute
```

The CLI has no implicit result cache. The explicit bounded JSON output is the
reusable artifact. `MPRester` initialization performs compatibility and
heartbeat/database-version metadata requests before the bounded summary
search. The CLI discloses those requests, disables the platform-detail user
agent and local database-version notification log, and records the server's
database version.

The CLI pins `endpoint` explicitly so SDK endpoint configuration cannot redirect
its credential. Initialization makes separate unauthenticated `GET /heartbeat`
calls for server/emmet version, database version and controlled-dataset metadata.
Those calls do not use the session retry/timeout mechanism; apply a process
deadline for automation. If heartbeat is denied, the SDK may report an empty
database version; retain that limitation rather than invent a release.

## Summary searches

The official docs identify summary data as the main property overview for a
material:

```python
from mp_api.client import MPRester

with MPRester() as rester:
    docs = rester.materials.summary.search(
        material_ids=["mp-149", "mp-13"],
        fields=[
            "material_id",
            "formula_pretty",
            "energy_above_hull",
            "band_gap",
            "origins",
            "last_updated",
        ],
        all_fields=False,
        num_chunks=1,
        chunk_size=25,
    )
```

`material_ids` accepts one ID or a list in the current signature. Both numeric
IDs (`mp-149`) and alphabetical AlphaIDs (`mp-aaaaaaft`) are supported. The SDK
normalizes them through emmet; these two examples identify the same record.
Preserve the user's query and returned identifier instead of enforcing a
digits-only pattern. The result is a list of Pydantic document objects based
on `SummaryDoc`; selected-field results can use a reduced `MPDataDoc` model.

### Property filters

Verified public `SummaryRester.search` parameters include:

```python
with MPRester() as rester:
    docs = rester.materials.summary.search(
        chemsys="Li-Fe-O",
        elements=["Li", "O"],
        exclude_elements=["F"],
        energy_above_hull=(0.0, 0.05),
        band_gap=(0.5, 3.0),
        is_stable=None,
        fields=["material_id", "formula_pretty", "energy_above_hull", "band_gap"],
        all_fields=False,
        num_chunks=1,
        chunk_size=25,
    )
```

Other current filters include formula, crystal system, density, deprecation,
dielectric ranges, elastic ranges, metal/direct-gap flags, property
availability, magnetic ordering, element/site counts, space group, theoretical
status, energy ranges, volume, and surface-property ranges. Consult the exact
installed signature instead of passing guessed keywords.

`exclude_elements` is a list of element symbols; it is not a Boolean flag.

`available_fields` lists fields the endpoint can return. It does not mean every
field is a valid filter:

```python
with MPRester() as rester:
    returnable_fields = rester.materials.summary.available_fields
```

Requesting all fields is the documented default and can be expensive. Always
pass a short `fields` list and bound chunks.

The REST search is a `GET /materials/summary/` with `x-api-key` authentication
and URL query parameters, not a JSON POST. The SDK joins lists (for example
`material_ids`, `elements`, `exclude_elements`) with commas and expands range
tuples to endpoint-specific `_min`/`_max` parameters. Responses contain a
`data` array and `meta.total_doc`; the SDK returns the document list.
`num_chunks=None` retrieves all pages; `num_chunks=1, chunk_size=25` bounds this
workflow. Pagination uses `_limit`/`_skip`; current `search()` also exposes
`_page` and `_sort_fields`. List splitting or retries can make one SDK search
more than one HTTP request. A full page does not prove the query is exhaustive.
The saved-byte cap applies after receipt and serialization.

For direct REST requests, `_limit` defaults to 100 and is capped at 1000.
`_page`/`_per_page` take precedence over `_limit`/`_skip`; do not combine both
pagination styles. `id_format=legacy|alpha` changes response ID formatting,
not which input IDs are accepted. This REST parameter is not a documented
`SummaryRester.search()` argument in 0.46.5.

## Serialization

Use the public Pydantic model interface:

```python
payload = [document.model_dump(mode="json") for document in docs]
```

Then write strict JSON with `allow_nan=False`, a byte bound, and a new output
path. Include query, fields, retrieval time, endpoint, client versions, and
license/citation. Do not use deprecated generic dictionary shims, pickle, or a
general object decoder on untrusted cached data.

## Structures

```python
from mp_api.client import MPRester

with MPRester() as rester:
    structure = rester.get_structure_by_material_id(
        "mp-149",
        final=True,
        conventional_unit_cell=False,
    )
```

Alternatively request `structure` as an explicit summary field. Preserve:

- material ID
- whether the final/initial and conventional/primitive representation was
  requested
- `origins` and task IDs
- retrieval and database release
- parser/API warnings

Validate the returned structure locally. A Materials Project structure is a
computed relaxed representation, not necessarily the experimental setting,
lattice parameters, disorder, temperature, or composition model.

This convenience method searches `/materials/core/` for `structure` when
`final=True`, or `initial_structures` when false. The former returns one
`Structure`, the latter a list; unavailable data can return `None`.

## Entries and phase diagrams

```python
from mp_api.client import MPRester

with MPRester() as rester:
    entries = rester.get_entries_in_chemsys(
        "Li-Fe-O",
        compatible_only=True,
        conventional_unit_cell=False,
    )
```

Version 0.46.5 changed this workflow: the default thermotype is the joint
`GGA_GGA+U_R2SCAN` hull. An unfiltered full-system query with
`compatible_only=True` normally returns entries from MP's precomputed phase
diagram, keeping all subsystems on one energy scale. If that diagram is missing,
or `property_data`/`conventional_unit_cell` require reshaping, the client runs
`MaterialsProjectDFTMixingScheme` locally; it warns about possible hull changes
and dropped entries. This can query/cache Delta-table data, unlike the bundled
summary-only CLI.

To explicitly select the earlier GGA/GGA+U correction convention:

```python
with MPRester() as rester:
    entries = rester.get_entries_in_chemsys(
        "Co-N",
        additional_criteria={
            "thermo_types": ["GGA_GGA+U"]
        },
    )
```

Extra filters on mixed thermotypes or `compatible_only=False` bypass the
consistent full-system path; those entries are not immediately hull-ready.
Retrieve the full consistent set before post-filtering for reporting, and keep
all competitors for hull construction. Do not pool all three thermotypes into
one hull. The non-mixed path uses `/materials/thermo/`; the prebuilt mixed path
uses the `materialsproject-build` Delta table `objects/phase-diagrams`, selected
by chemical system, thermotype and database version. These are SDK-managed data
locations, not REST endpoints to invent. Record all arguments, correction data,
origins and database release; cache and analyze the resulting entries offline.

`use_gibbs` requests a GibbsComputedStructureEntry model estimate at 300–2000 K,
not a measured free energy. `property_data` selects supported thermo fields.
The convenience method has no summary-CLI result cap; bound the chemical system
and expected dataset independently.

## Band structures and DOS

Official convenience methods include:

```python
with MPRester() as rester:
    bands = rester.get_bandstructure_by_material_id("mp-149", load_projections=False)
    dos = rester.get_dos_by_material_id("mp-149", load_projections=False)
```

In 0.46.5 missing metadata or task data raises `MPRestError`; catch it without
turning absence into a zero gap or DOS. The client first searches
`/materials/electronic_structure/` for the task, then queries SDK-managed Delta
tables under `materialsproject-parsed/core/electronic-structure/` for
`bandstructures` or `total-dos`; projections use additional tables only when
requested. Default DOS retrieval returns `Dos`, not necessarily `CompleteDos`.
Preserve task origins, spin/SOC, path convention, functional and database release.
These convenience calls have different network/cache costs from a summary
property query.

## Provenance with origins

The official query guide recommends requesting `origins` to connect a summary
property to a calculation task:

```python
with MPRester() as rester:
    summaries = rester.materials.summary.search(
        material_ids=["mp-149"],
        fields=["material_id", "structure", "origins"],
        all_fields=False,
        num_chunks=1,
        chunk_size=1,
    )
```

An origin can identify the task used for a property. A corresponding thermo
document's `run_type` distinguishes categories such as GGA, GGA+U, or r2SCAN.
Do not assume all properties on one summary document came from one calculation
or functional.

## Other routes

The client exposes endpoint-specific resters under `rester.materials`, with
routes documented for thermo, electronic structure, elasticity, dielectric,
magnetism, phonons, surfaces, XAS, synthesis-related data, and others.
Signatures and document models vary. Inspect the current route documentation
and request only supported fields.

Do not copy old endpoint examples or invent filter names. Endpoint availability
and schema can evolve independently of the Python wrapper.

## Errors, retries, and rate handling

Use the current exception:

```python
from mp_api.client.core.exceptions import MPRestError

try:
    with MPRester() as rester:
        docs = rester.materials.summary.search(
            material_ids=["mp-149"],
            fields=["material_id"],
            all_fields=False,
            num_chunks=1,
            chunk_size=1,
        )
except MPRestError:
    # Report a bounded, credential-redacted failure.
    raise
```

Official 0.46.5 client source configures retries for HTTP 429, 502, and 504 and
respects `Retry-After` for its API session (heartbeat is separate). It wraps request failures as `MPRestError` and advises
smaller requests on connection timeout.

Safety rules:

- rely on the pinned client's bounded retry behavior
- do not add an unbounded retry loop
- do not claim a numeric service quota unless current official documentation
  publishes one
- reduce fields/chunk size on timeout or oversized responses
- stop after a persistent authorization, schema, or validation error
- redact `MP_API_KEY` from any exception text

The current [large-download guide](https://docs.materialsproject.org/downloading-data/using-the-api/tips-for-large-downloads)
says rate limiting starts at 25 requests/second. Treat HTTP 429 and
`Retry-After` as authoritative, not that number as a guaranteed quota.

## Cache policy

Caching can improve reproducibility but creates a data-governance obligation.
Before using a cache, disclose:

- exact path, schema, size limit, and retention
- cache key: endpoint, filters, fields, client version, and database release
- whether stale data is acceptable
- license/citation metadata
- whether structures or contributed data are stored

Never cache credentials. Never treat a cache as current without checking its
retrieval time and database version. `mp-api` exposes a local full-dataset cache
path for bulk/delta-table workflows; the bundled summary-query CLI does not
request those downloads and intentionally uses no hidden result cache.

## License, attribution, and citation

Materials Project states that its data is licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and that contributed
data is owned by its respective contributors.

The official FAQ says citations are appropriate wherever Materials Project
data, methods, or output are used. Preserve:

- canonical Materials Project citation
- property/tool-specific citations from the material/citation page
- database release citation
- material IDs and task/property origins
- retrieval date and query

See [How to Cite](https://materialsproject.org/about/cite) and
[Database Versions](https://docs.materialsproject.org/changes/database-versions).

## Computed-data limitations

Materials Project documents that:

- core properties are calculated in-house using simulation methods
- typical/systematic errors must be assessed from property publications
- PBE lattice parameters often show systematic overestimation, with larger
  interlayer errors where van der Waals interactions are poorly described
- PBE band gaps are systematically underestimated
- summary/aggregated values can change as calculations and database releases
  are updated
- space groups depend on `symprec`; the MP pipeline commonly uses `0.1 Å`

Therefore:

- computed stability is not experimental stability or synthesizability
- predicted structures are not proof of existence
- missing data is not zero
- a material ID does not guarantee one immutable property record
- cite the database version and property methodology

## Minimal provenance envelope

```json
{
  "retrieved_at_utc": "2026-09-30T00:00:00Z",
  "endpoint": "https://api.materialsproject.org/materials/summary/",
  "filters": {"material_ids": ["mp-149"]},
  "fields": ["material_id", "formula_pretty", "origins", "last_updated"],
  "limit": 1,
  "client": {
    "mp-api": "0.46.5",
    "pymatgen": "2026.9.24",
    "pymatgen-core": "2026.9.23"
  },
  "database_version": "record from current MP release metadata",
  "license": "CC BY 4.0",
  "citation": "https://materialsproject.org/about/cite"
}
```

Do not include the API key.

## Sources (verified 2026-09-30)

- [mp-api 0.46.5 on PyPI](https://pypi.org/project/mp-api/)
- [Official mp-api repository](https://github.com/materialsproject/api)
- [Current REST schema](https://api.materialsproject.org/openapi.json)
- [mp-api 0.46.5 source](https://github.com/materialsproject/api/tree/v0.46.5/mp_api/client)
- [Materials Project identifier conventions](https://docs.materialsproject.org/data-production/identifiers)
- [Getting started](https://docs.materialsproject.org/downloading-data/using-the-api/getting-started)
- [Querying data](https://docs.materialsproject.org/downloading-data/using-the-api/querying-data)
- [mp-api route reference](https://materialsproject.github.io/api/)
- [Materials Project FAQ](https://docs.materialsproject.org/frequently-asked-questions)
- [Materials Project calculation details](https://docs.materialsproject.org/methodology/materials-methodology/calculation-details)
- [How to Cite](https://materialsproject.org/about/cite)
- [Database versions](https://docs.materialsproject.org/changes/database-versions)
- [Materials Project home and CC BY statement](https://materialsproject.org/)
