# IDC MCP Server Guide

IDC operates a hosted [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes IDC discovery and metadata as agent tools. This guide covers how to recognize it, how
to divide work between it and `idc-index`, and what to hand off across that boundary.

The server is optional. Everything in `SKILL.md` works without it.

## Endpoint

| Property | Value |
|----------|-------|
| URL | `https://api.imaging.datacommons.cancer.gov/mcp` |
| Transport | Streamable HTTP (`streamable-http`, sometimes spelled `http`) |
| Authentication | None |
| Server identity | `IDC (Imaging Data Commons)` |

## Identifying the server

Tool names and resource URIs are defined by the server, so they are the same on every host.
Use them, not host-specific naming conventions, to decide whether the server is present.

**Strongest signal — resource URIs.** The server publishes two resources under an `idc://`
scheme:

| URI | Content |
|-----|---------|
| `idc://guide` | Data model and recommended workflow (Markdown) |
| `idc://tables` | Tables available to `run_sql`, with descriptions and column counts (JSON) |

If the host can enumerate MCP resources, a resource with URI `idc://guide` identifies the
server unambiguously.

**Fallback — tool-name fingerprint.** Require three or more of `build_cohort`,
`get_cohort_urls`, `list_analysis_results`, and `get_idc_version`. Do not treat `run_sql`,
`get_stats`, `list_tables`, or `get_citations` as evidence on their own; those names are
generic enough that another server could expose them.

**This is disambiguation, not authentication.** No runtime check can prove the server on the
other end is operated by NCI — a hostile server could serve `idc://guide` and name its tools
anything. The trust anchor is the URL the user configured plus TLS, which is established when
the server is added, not when the skill runs. That is sufficient for routing: the check only
has to distinguish IDC from the user's other installed servers.

**Fail soft.** If identification is ambiguous, or a tool call fails, fall back to `idc-index`
rather than reporting an error. Tool names may change as the server matures.

## Tool inventory

Verified against server version `3.0.0b2`. Treat this as a snapshot, not a contract — call
the server's own listing rather than assuming this list is current.

| Group | Tools |
|-------|-------|
| Version and scale | `get_idc_version`, `get_stats` |
| Collections | `list_collections`, `get_collection`, `list_analysis_results` |
| Attribute grounding | `list_attributes`, `get_attribute_values` |
| Cohorts | `build_cohort`, `get_cohort_urls` |
| SQL | `list_tables`, `get_table_schema`, `run_sql` |
| Clinical data | `list_clinical_tables`, `get_clinical_table_schema`, `get_clinical_table` |
| Attribution | `get_citations`, `get_licenses` |
| Visualization | `get_viewer_url` |

The server ships its own usage instructions, which most hosts inject automatically. Follow
those instructions for tool sequencing (ground with `list_attributes` /
`get_attribute_values` before filtering; check `list_tables` before writing SQL). Do not
re-derive that workflow from `SKILL.md` — the two would drift apart on the server's next
release.

## Division of labor

The server and `idc-index` overlap on metadata queries and diverge everywhere else.

| Task | Use |
|------|-----|
| IDC data version, collection and series counts | Server (`get_idc_version`, `get_stats`) |
| Valid filter values before building a query | Server (`get_attribute_values`) |
| Cohort selection by attribute filters | Server (`build_cohort`) |
| One-off metadata SQL, answer consumed as prose | Server (`run_sql`) |
| Metadata SQL whose result feeds local Python | `idc-index` (`client.sql_query`) |
| Downloading DICOM files | `idc-index` (`client.download_from_selection`) |
| pandas / notebook analysis, plotting | `idc-index` |
| Reading pixel data (pydicom, SimpleITK) | `idc-index` + local files |
| DICOMweb, BigQuery, direct S3/GCS, Parquet | `idc-index` and the relevant reference guide |
| Digital pathology tiling and annotation workflows | `idc-index` + `digital_pathology_guide.md` |
| Reproducible scripts a user will re-run | `idc-index` (a script outlives the session) |

Two rules resolve the overlap:

- **Prefer the server for discovery.** It is hosted against a current IDC release, so it does
  not depend on the `idc-index` version pinned in `SKILL.md`.
- **Prefer `idc-index` when the result must become a Python object.** Round-tripping a
  DataFrame through tool output wastes context and loses types.

## Handing off from the server to `idc-index`

The boundary artifact is a list of `SeriesInstanceUID` values.

```python
# UIDs obtained from the MCP server's build_cohort / run_sql output
series_uids = [
    "1.3.6.1.4.1.14519.5.2.1.7009.2403.334240657131972136850343327463",
    # ...
]

from idc_index import IDCClient
client = IDCClient()

# Confirm size before downloading — the server reports size_TB, but re-check locally
sizes = client.sql_query(f"""
    SELECT COUNT(*) AS series, SUM(series_size_MB)/1000 AS size_GB
    FROM index
    WHERE SeriesInstanceUID IN ({','.join(f"'{u}'" for u in series_uids)})
""")
print(sizes)

client.download_from_selection(
    downloadDir="./data",
    seriesInstanceUID=series_uids,       # a list, not a DataFrame
    dirTemplate="%collection_id/%PatientID/%Modality",
)
```

Run `python scripts/check_version.py` before the first `idc-index` call in a session, even if
discovery happened server-side — the two components version independently.

`get_cohort_urls` also returns ready-made `idc` CLI commands. Those are the better handoff
when the user wants a shell command they can re-run outside the session; see
`references/cli_guide.md`.

Going the other direction, `idc-index` results are already local, so there is rarely a reason
to send them back to the server.

## Version authority

When the server is present, it is the authority on the IDC data version: call
`get_idc_version` rather than quoting the `idc-data-version` value in the `SKILL.md`
frontmatter, which records the release the skill was last verified against.

If the server and a locally installed `idc-index` report different versions, say so and name
both. The mismatch is real — the hosted server tracks IDC releases independently of the user's
installed package — and it changes which answers about "what's new" are correct.

## Host-specific notes

Everything above is portable. The items below are not, and apply only to specific agent
environments.

### Claude Code

- **Tool naming.** MCP tools are exposed as `mcp__<server>__<tool>`, where `<server>` is the
  configured server name with every character outside `A-Za-z0-9_-` replaced by `_`. A CLI
  install named `idc` yields `mcp__idc__build_cohort`; a claude.ai connector named
  `IDC MCP prod` yields `mcp__claude_ai_IDC_MCP_prod__build_cohort`.
- **Enumerating resources.** `ListMcpResourcesTool` returns each resource with a `server`
  field, which is how to find the `idc://guide` resource and the owning server name in one
  call.
- **Adding the server.**
  `claude mcp add --transport http idc https://api.imaging.datacommons.cancer.gov/mcp`
- **Permission rules.** Allow rules need a literal, glob-free server segment: `mcp__idc__*`
  works, `mcp__*` does not. Connector installs need their own
  `mcp__claude_ai_<name>__*` rule, so the rule differs by install path.
- **Detecting via the CLI does not work.** `claude mcp list` reads only file-based
  configuration (`~/.claude.json`, `.mcp.json`). It reports "No MCP servers configured" for a
  claude.ai connector that is connected and working in the same session, so it cannot be used
  as a presence check.

### Other hosts

Any agent that supports MCP over streamable HTTP can use the server. Consult that agent's
documentation for how servers are registered and how tool names are namespaced; the endpoint
URL and the absence of authentication are all the configuration it needs.
