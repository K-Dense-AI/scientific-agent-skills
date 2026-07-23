# Official Sources and Version Snapshot

Research date: **2026-07-23**

This file records the authoritative basis for skill version 1.2. The snapshot
must not replace checking the target server's own version and discovery
endpoints.

## Current Versions

- **OMERO.server 5.6.18** — May 2026 bug-fix release.
- **OMERO.py / `omero-py` 5.22.1** — released 2026-03-25.
- **OMERO.web 5.31.0** — the version tested with OMERO.server 5.6.18.
- **Bio-Formats 8.5.0** — bundled by OMERO.server 5.6.18.
- **ZeroC IcePy 3.6.5** — exact client binding version in current official
  installation examples and OMERO-linked wheel matrix.

The OMERO.server history explicitly says 5.6.18 was tested with OMERO.py
5.22.1 and OMERO.web 5.31.0. That tested pairing is stronger evidence than
assuming compatibility from package version numbers.

## Release and Package Metadata

- OMERO version history  
  https://omero.readthedocs.io/en/stable/users/history.html  
  Basis for server 5.6.18, tested client/web pairing, and Bio-Formats 8.5.0.

- `omero-py` on PyPI  
  https://pypi.org/project/omero-py/  
  Basis for 5.22.1, 2026-03-25 release date, Python `>=3.10`, IcePy 3.6,
  NumPy/Pillow requirements, OMERODIR notes, and GPL-2.0-or-later package
  license.

- Official OME `omero-py` repository and changelog  
  https://github.com/ome/omero-py  
  https://github.com/ome/omero-py/blob/v5.22.1/CHANGELOG.md  
  Basis for recent Python/NumPy compatibility and historical deprecations.

- Official OME OMERO.server component releases  
  https://github.com/ome/omero-server/releases  
  Cross-check for current server component releases.

## Installation and Compatibility

- OMERO Python language bindings  
  https://omero.readthedocs.io/en/stable/developers/Python.html  
  Basis for the current `omero-py==5.22.1` examples, IcePy 3.6.5 ordering,
  BlitzGateway patterns, objects, annotations, tables, ROIs, pixels, and
  rendering.

- OMERO version requirements  
  https://omero.readthedocs.io/en/stable/sysadmins/version-requirements.html  
  Basis for Python 3.10/3.11 support, Python 3.12 recommendation,
  Python 3.13/3.14 “upcoming” status, Ice 3.6 recommendation, Ice 3.7
  unsupported status, and server platform/runtime matrix.

- OMERO-linked Glencoe Ice binary matrix  
  https://www.glencoesoftware.com/blog/2023/12/08/ice-binaries-for-omero.html  
  Basis for exact prebuilt IcePy 3.6.5 wheel coverage through Python 3.12.
  Glencoe is identified in OME's Python installation page as its commercial
  partner. Select the exact wheel from the linked release repositories.

- OMERO CLI installation  
  https://omero.readthedocs.io/en/stable/users/cli/installation.html  
  Basis for client installation and import/admin prerequisites.

## Connection and Security

- BlitzGateway documentation  
  https://omero.readthedocs.io/en/stable/developers/PythonBlitzGateway.html  
  Basis for context-manager closure, wrappers/lazy loading, stateless versus
  stateful service reuse, and stale stateful proxies after reconnection.

- Server security and firewalls  
  https://omero.readthedocs.io/en/stable/sysadmins/server-security.html  
  Basis for login encryption, optional full transport encryption, session-ID
  exposure on insecure post-login traffic, and default router ports 4063/4064.

- Client/server SSL verification  
  https://omero.readthedocs.io/en/stable/sysadmins/client-server-ssl.html  
  Basis for the warning that standard clients do not automatically verify the
  host and for the documented IceSSL verification properties.

- CLI session management  
  https://omero.readthedocs.io/en/stable/users/cli/sessions.html  
  Basis for prompted login, session files, `omero sessions`, group switching,
  `-k` session reuse, and logout.

## Data, Metadata, ROIs, and Tables

- OMERO Python examples  
  https://omero.readthedocs.io/en/stable/developers/Python.html  
  Primary current examples for bounded `getObjects`, annotations, pixels,
  rendering, tables, and ROI model operations.

- OMERO.tables  
  https://omero.readthedocs.io/en/stable/developers/Tables.html  
  Basis for current column signatures, reads, queries, paging, global locking,
  and HDF implementation details.

- Structured annotations  
  https://omero.readthedocs.io/en/stable/developers/Model/StructuredAnnotations.html  
  Basis for annotation type hierarchy, namespaces, and link semantics.

- OME ROI model 5.6.3  
  https://docs.openmicroscopy.org/ome-model/5.6.3/developers/roi.html  
  Basis for the eight shape types, optional TheZ/TheT/TheC, RGBA fields, and
  union-of-2D-shapes representation. The page itself was last updated in 2018
  but documents the June 2016 schema still used by OMERO 5.6.

- Current generated `IRoi` API  
  https://docs.openmicroscopy.org/omero-blitz/5.8.5/slice2html/omero/api/IRoi.html  
  Basis for the explicit `IRoi` deprecation warning.

- OMERO application services  
  https://omero.readthedocs.io/en/stable/developers/Modules/Api.html  
  Basis for service categories and current `IRoi`/`IShare` deprecation status.

## CLI Import, Export, and Download

- Import images  
  https://omero.readthedocs.io/en/stable/users/cli/import.html  
  Basis for `omero import`, `-f` serverless scanning, target syntax,
  depth/output options, experimental parallelism warning, and diagnostic
  upload disclosure.

- Import targets  
  https://omero.readthedocs.io/en/stable/users/cli/import-target.html  
  Basis for current-group target behavior and target syntax.

- Export images  
  https://omero.readthedocs.io/en/stable/users/cli/export.html  
  Basis for OME-TIFF/XML-only export and experimental Dataset iteration.

- Current `omero-py==5.22.1` CLI help (`omero download -h`)  
  Verified in an isolated environment on 2026-07-23. Basis for explicit
  OriginalFile, FileAnnotation, Image, and Fileset download forms. This was
  cross-checked against the official `ome/omero-py` package.

## OMERO.web and Public Data

- OMERO.web framework  
  https://omero.readthedocs.io/en/stable/developers/Web.html  
  Basis for treating only `api` and `webgateway` as stable public APIs and
  treating other app URLs as internal.

- OMERO JSON API  
  https://omero.readthedocs.io/en/stable/developers/json-api.html  
  Basis for version discovery, API version headers, CSRF/login behavior,
  pagination/maxLimit, ROI endpoints, and limited create/update object types.

- Publishing data using OMERO.web  
  https://omero.readthedocs.io/en/stable/sysadmins/public.html  
  Basis for dedicated read-only public groups/users, GET-only default, URL
  filters, and publication URL examples.

- OMERO configuration properties  
  https://omero.readthedocs.io/en/stable/sysadmins/config.html  
  Basis for public-user defaults (`enabled=false`, `get_only=true`, and a
  URL filter that allows nothing until configured).

## Research Method

The refresh used focused `parallel-cli search` queries restricted primarily to:

- `omero.readthedocs.io`
- `docs.openmicroscopy.org`
- `ome-model.readthedocs.io`
- `openmicroscopy.org`
- `pypi.org`
- official `github.com/ome/*` repositories

Canonical pages above were then fetched with `parallel-cli extract` using
objectives specific to versions, Python/Ice compatibility, connection
security, BlitzGateway APIs, CLI behavior, tables, ROIs/annotations,
rendering, and OMERO.web/public APIs.

No Parallel JSON research artifacts were written into the repository.

## Known Documentation Tensions

- PyPI declares Python `>=3.10` without an upper bound, while the OMERO support
  matrix currently supports through 3.12 and marks 3.13/3.14 upcoming.
  Installation is also constrained by matching IcePy wheels. This skill uses
  Python 3.12 as the reproducible recommendation.
- Current Python docs still demonstrate `IRoi` while the generated API marks
  the interface deprecated. The skill documents and isolates this dependency
  rather than pretending a replacement is official.
- OMERO.web documents webclient publication links, while separately stating
  that webclient is not a stable public API. Durable publication links should
  use administrator-managed redirects/DOIs.
- `secure=True` encrypts traffic but standard clients do not automatically
  provide full hostname verification. High-assurance deployments need the
  administrator-provided IceSSL trust/name configuration.
