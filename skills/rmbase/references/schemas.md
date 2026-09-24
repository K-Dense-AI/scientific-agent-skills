# Output and cache contracts

JSON is the default. Successful query envelopes include `schema_version`, `status`
(`ok` or `no_records`), `command`, `query`, `records`, `pagination`, `provenance`,
and `warnings`. Catalogue output is a local metadata response without scientific
query provenance. Output object keys and record ordering are deterministic;
timestamps and changing upstream data necessarily vary.

`pagination.total_records` is the size of the retrieved, locally filtered result,
not a database-wide count. `complete` is false when an offset or limit omits rows.
The client never issues speculative page/start/length parameters. Repeated pages
reuse the cached full response. Byte-limit errors never return partial success.

Provenance includes RMBase version, query time, species/assembly, access mode,
request method and parameters, URL, retrieval time, response SHA-256, response size,
HTTP Last-Modified/ETag when supplied, and cache use. Record-specific source IDs,
dataset IDs and PMIDs remain in records. The database PMID is not assigned as
experimental support for every record. Dataset version is null when the publisher
does not supply one; a checksum and download date identify the captured content.

HTML-valued JSON fields become `{text, links}` objects; script/style content is
ignored. Modification detail output retains labelled `fields`, nested
`related_tables`, and `pmids`. Links are references, never instructions or executable
code. Numeric strings such as very small motif p-values are preserved without
floating-point underflow.

TSV requires `--provenance-out FILE`. Arrays/objects inside a TSV cell are JSON;
tabs and newlines are CSV-quoted. `--out FILE` writes data; the provenance sidecar
contains the envelope without records. Treat exported cells as untrusted data
when importing into spreadsheet applications.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Successful query, including explicit no-records results |
| 2 | Invalid inputs or arguments |
| 3 | Network, HTTP, rate limit, or client rate-lock failure |
| 4 | Unexpected schema, malformed response, inconsistent counts |
| 5 | Response/archive size or archive safety limit |
| 6 | Missing/corrupt cache or local I/O error |
| 7 | Analysis task response/lifecycle has not been verified |

Errors are JSON on stdout with `status: error` and an `error` object. CLI help is
human-readable and does not perform a network request.

## Cache

Default location is `~/.cache/rmbase`; `--cache-dir` overrides it. It holds exact
request responses, SHA-256 metadata, official dataset archives and a rate-limit
lock/timestamp. No authentication/session state is required. Response freshness is
24 hours unless offline; dataset refresh is explicit. `--offline --refresh` is
invalid. A checksum detects local corruption, not the authenticity of HTTP content.

The gene and transcript archives have one 22-column TSV table. No archive member
is extracted to disk. Symlinks and multiple tables are rejected. Limits are 64 MB
compressed and 256 MB declared expanded size; an unexpected format fails clearly.
`sync --archive PATH` imports an existing archive but marks origin as user-supplied;
it does not falsely claim to have downloaded or authenticated that file.

Gene columns: gene ID, gene name, transcript IDs, biotype, region; paired count/list
columns for m6A, m1A, m5C, m7G, Pseudo, Nm, RNA-editing, other; final total.
Transcript files instead begin transcript ID, gene ID, gene name. This mapping
comes from the official download page. Gene query comparisons are exact and
case-sensitive; ID versions are retained.
