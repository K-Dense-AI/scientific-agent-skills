# Review sources and execution boundary

Reviewed 2026-09-30. Current public documentation was checked alongside released
source and installed runtime contracts; a successful page load alone was not
used to validate examples.

## Versions inspected

- `lamindb==2.10.0`, `lamindb-core==2.10.0`
- `lamindb-setup==1.25.7`, `lamin-cli==1.19.3`
- `bionty==2.5.0`, transitively installed `pertdb==2.2.0`
- Python 3.12, pandas 3.0.6, AnnData 0.13.2, IPython 9.17.1

Official metadata: [LaminDB](https://pypi.org/project/lamindb/2.10.0/),
[Bionty](https://pypi.org/project/bionty/2.5.0/),
[release tag](https://github.com/laminlabs/lamindb/tree/2.10.0).
The release tag resolves to `ea00428098485bae94ea83a67b5b806918a78d9c`.

## Sources by contract

| Area | Primary source |
| --- | --- |
| Install, storage, settings, migrations | [Setup](https://docs.lamin.ai/setup), [CLI](https://docs.lamin.ai/cli), [dependencies](https://github.com/laminlabs/lamindb/blob/2.10.0/pyproject.toml) |
| Artifact revisions and accessors | [Artifact source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/artifact.py), [arrays](https://docs.lamin.ai/arrays) |
| Queries, result limits and get behavior | [QuerySet source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/query_set.py), [query guide](https://docs.lamin.ai/query-search) |
| Schemas and curator methods | [Schema source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/schema.py), [curator source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/curators/core.py), [curation guide](https://docs.lamin.ai/curate) |
| Lineage | [Tracking](https://docs.lamin.ai/track), [Run source](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/run.py) |
| Ontology operations | [Bionty](https://github.com/laminlabs/bionty), [ontology guide](https://docs.lamin.ai/manage-ontologies), [curation methods](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/can_curate.py) |
| Module provenance | [pertdb docs](https://docs.lamin.ai/pertdb), [Lamin Labs source](https://github.com/laminlabs/pertdb) |
| Pipelines/integrations | [nf-lamin](https://docs.lamin.ai/nf-lamin), [integration API](https://docs.lamin.ai/lamindb.integrations), links in integrations.md |

## Executed and not executed

The repository's `tests/lamindb/` suite creates a disposable SQLite instance in
a subprocess with fresh working directory, settings, cache, and storage. It
exercises schema acceptance/rejection, data round trips, annotations, revisions,
collections, local Bionty synonyms/hierarchies, and lineage. No existing user
instance or remote service is mutated.

Cloud providers, private Hub authentication, public ontology downloads, optional
SOMA/SpatialData/MuData backends, Nextflow, external ML services, and live Vitessce
serving were not tested end to end. Their retained examples are explicitly
illustrative/source-verified and require environment-specific validation.
No REST endpoints are called by this skill; the API audit covers the Python SDK
and CLI contracts it actually teaches.
