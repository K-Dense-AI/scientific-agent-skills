# ROR (Research Organization Registry)

Open registry of research organizations. Use it to turn an affiliation string
into a ROR ID (`https://ror.org/05a0ya142`) or to look up one org. It is not
a paper database. OpenAlex and Crossref already *carry* ROR IDs on works;
this API is how you mint or check the ID itself.

All figures below verified 2026-09-10. Use the **v2** routes.

## Base URL

```
https://api.ror.org/v2
```

Docs: https://ror.readme.io/docs/rest-api

## Authentication

None. Heartbeat: `GET https://api.ror.org/heartbeat` → `OK`.

## Rate Limits

2000 requests / 5 minutes / IP. Traffic spikes around midnight UTC. For bulk
matching, run the API locally (Docker) rather than hammering the public host.

## Identifier

A ROR ID is `https://ror.org/` plus nine characters (`0` + 6 alphanumeric +
2 check-ish chars), e.g. `https://ror.org/05a0ya142`. The path
`/v2/organizations/05a0ya142` accepts the suffix alone.

## Key Endpoints

### 1. Keyword / identifier search

```
GET /v2/organizations?query={text}
```

Searches **only** `names` and `external_ids` (GRID, ISNI, Wikidata, Crossref
Funder ID). It does not search addresses, websites, or relationships.

Unquoted common words explode. Verified:

| `query` | `number_of_results` | First hit |
|---|---|---|
| `Broad Institute` | 13016 | Broad Institute (lucky, not guaranteed) |
| `"Broad Institute"` | 3 | Broad Institute |

Never take `items[0]` as the match without reading `names` and `status`.
Quote the string (`%22…%22`) when the user gave a proper name.

Default page is 20 active records. Filter and page per
https://ror.readme.io/docs/api-filtering and
https://ror.readme.io/docs/api-paging. Pass `all_status=true` if you need
inactive / withdrawn orgs in a list.

### 2. Affiliation matcher (unstructured strings)

```
GET /v2/organizations?affiliation={raw affiliation}
```

Best for "Broad Institute of MIT and Harvard, Cambridge, MA" dumped from a
PDF. As of 2026-05-26 this parameter defaults to the **single search**
strategy.

The JSON is **not** the same as `?query=`. Each item is a match wrapper:

```json
{
  "substring": "Broad Institute of MIT and Harvard, Cambridge, MA",
  "score": 1.0,
  "matching_type": "SINGLE SEARCH",
  "chosen": true,
  "organization": { "id": "https://ror.org/05a0ya142", "names": […], "status": "active" }
}
```

Read `items[].organization` and `chosen`. `items[0].id` is absent — that is
how a naive parse reports "no ROR ID" after a successful match.

Verified: 10 items, first `chosen` true, organization is Broad Institute.

### 3. One organization

```
GET /v2/organizations/{ror_id_or_suffix}
```

```
GET /v2/organizations/05a0ya142
```

Always returns the record, including `inactive` / `withdrawn`. Lists hide
those statuses by default; a single-id GET does not. Check `status` before
writing the ID into metadata.

v2 records have `names[]` (with types: ror_display, alias, acronym, label),
not a top-level `name`. `/organizations/{id}` without `/v2` currently still
returns the v2 shape; call `/v2/` so a future default change does not flip
the schema under you.

## Typical Workflow

1. Proper name or GRID/ISNI → `?query="…"` and inspect the shortlist.
2. Messy affiliation line → `?affiliation=` and keep rows with
   `chosen: true` (or a high `score` you are willing to stand behind).
3. Known ROR ID → GET the record and confirm `status: active`.
4. Then, if the user wanted papers from that org, search OpenAlex /
   Crossref with the ROR ID. Do not search ROR for papers.

## Failure Modes

| What you did | What happens | What to do |
|---|---|---|
| Unquoted `University` / `Institute` query | Thousands of hits | Quote the name; do not auto-pick |
| Read `items[0].id` on an affiliation response | `null` | Use `items[0].organization.id` |
| Wrote an inactive ROR from a single-id GET | Record exists, `status` is not `active` | Read `status` |
| Used v1 field `name` | Missing | Use `names[].value` |
