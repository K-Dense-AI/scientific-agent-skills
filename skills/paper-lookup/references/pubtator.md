# PubTator3

NCBI text-mined annotations on PubMed abstracts (and some PMC full text): genes,
diseases, chemicals, species, variants, and cell lines, plus typed relations.
Use it when the user wants *entities in a paper* or papers that mention a
normalized entity (`@CHEMICAL_remdesivir`), not when they want a citation list.

Europe PMC `/textMinedTerms` is a thinner per-article alternative. PubMed search
does not normalize "remdesivir" to a concept ID. PubTator3 APIs are **not** the
old PubTator / `CBBresearch` endpoints.

All figures below verified 2026-09-10.

## Base URL

```
https://www.ncbi.nlm.nih.gov/research/pubtator3-api
```

Docs: https://www.ncbi.nlm.nih.gov/research/pubtator3/api

## Authentication

None.

## Rate Limits

No more than **3 requests per second**. Serialize. For bulk annotation dumps use
the FTP site (`https://ftp.ncbi.nlm.nih.gov/pub/lu/PubTator3/`) rather than the
API.

## Key Endpoints

### 1. Resolve a mention to an entity ID

```
GET /entity/autocomplete/?query={text}&concept={type}&limit={n}
```

`concept` is optional (`chemical`, `disease`, `gene`, `species`, `variant`,
`cellline`).

```
GET /entity/autocomplete/?query=remdesivir&limit=3
```

Returns a JSON array. First hit (verified):

```json
{
  "_id": "@CHEMICAL_remdesivir",
  "biotype": "chemical",
  "db_id": "C000606551",
  "db": "ncbi_mesh",
  "name": "remdesivir"
}
```

Search with `_id` (`@CHEMICAL_remdesivir`), not the display name. Nearby
synonyms (`@CHEMICAL_GS_441524_triphosphate`) are different entities.

### 2. Search papers by text, entity, or relation

```
GET /search/?text={query}&page={n}
```

`text` may be free text, an `@TYPE_name` entity ID, a boolean combination, or a
relation:

```
@CHEMICAL_Doxorubicin AND @DISEASE_Neoplasms
relations:ANY|@CHEMICAL_Doxorubicin|@DISEASE_Neoplasms
relations:ANY|@CHEMICAL_Doxorubicin|DISEASE
```

```
GET /search/?text=@CHEMICAL_remdesivir
```

Verified: `count` 23295, `page_size` 10, `current` 1, `total_pages` 2330,
`results` length 10. First result `pmid` is an **integer** (`37711410`); `_id`
is a string. Page with `page` (1-based). There is no cursor.

Do not use this as a general PubMed replacement. Rank is entity-centric.

### 3. Export annotations for PMIDs

```
GET /publications/export/{format}?pmids={id,id}&full={true|false}
```

`format` is `pubtator`, `biocxml`, or `biocjson`. `full=true` (PMC full text)
works only for `biocxml` / `biocjson`.

```
GET /publications/export/biocjson?pmids=29355051
```

The JSON is **not** a bare BioC document. It is:

```json
{ "PubTator3": [ { "_id": "29355051|None", "id": "29355051", "passages": [...], "relations": [...] } ] }
```

Verified on PMID 29355051: one document, two passages, first passage has 5
annotations. An annotation looks like:

```json
{
  "infons": {
    "type": "Species",
    "database": "ncbi_taxonomy",
    "normalized_id": 112863,
    "biotype": "species"
  },
  "text": "Lycium barbarum",
  "locations": [{"offset": 14, "length": 15}]
}
```

Read `PubTator3[0].passages[].annotations`. A 200 with `"PubTator3": []` is
"no documents," not a transport success you can ignore.

### 4. Related entities

```
GET /relations?e1={entityId}&type={relation}&e2={entity_type}
```

Relation types include `treat`, `cause`, `interact`, `associate`,
`positive_correlate`, `negative_correlate`, `prevent`, `inhibit`, `stimulate`,
`drug_interact`. `e1` must be an autocomplete `_id`.

## Typical Workflow

1. Autocomplete the user's string → `@CHEMICAL_…` / `@DISEASE_…`.
2. Search with that ID (and a relation if they asked "what does X treat?").
3. Export `biocjson` for the PMIDs you will report, and list the annotations.
4. For the paper itself (abstract, OA PDF), go to PubMed / Europe PMC /
   Unpaywall. PubTator is not a full-text store.

## Failure Modes

| What you did | What happens | What to do |
|---|---|---|
| Parsed export JSON as BioC root | No `passages` at the top level | Descend into `PubTator3` |
| Searched `remdesivir` and treated hits as exact-chemical papers | Keyword search, not the concept | Autocomplete, then search `@CHEMICAL_remdesivir` |
| Called the old `pubtator-api` or `CBBresearch` URL | May still 200, but the contract changed | Use `pubtator3-api` |
| `full=true` with `format=pubtator` | No full text | Use `biocjson` or `biocxml` |
| Parallel fan-out | Easy to exceed 3 req/s | Serialize |
