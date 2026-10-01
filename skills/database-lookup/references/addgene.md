# Addgene Catalog API

## Access and authentication

Base: `https://api.developers.addgene.org`. Access requires approval and a license
for each requested scope; a normal Addgene account does not grant API access.
Use `Authorization: Token <ADDGENE_API_KEY>`.

## Read endpoints

| GET path | Purpose |
|---|---|
| `/catalog/plasmid/` | Search/list plasmids |
| `/catalog/plasmid/{id}/` | One plasmid |
| `/catalog/plasmid-with-sequences/{id}/` | One plasmid with sequences; requires `catalog:retrieve-with-sequences` |
| `/catalog/viral-prep/` | List viral preparations |
| `/catalog/viral-prep/{id}/` | One viral preparation |

Ordinary catalog reads require `catalog:retrieve` or the sequence-enabled scope.
Use `q` for free text; documented field filters include `name`, `backbone`,
`genes`, `article_pmid`, and `species`. List responses contain `count`, `next`,
`previous`, and `results`. Follow `next`; `page` and `page_size` control pagination.
Use `sort_by=id` for stable pagination; relevance sorting requires `q`.

Illustrative authenticated request (not executed):

```bash
curl --fail-with-body --get 'https://api.developers.addgene.org/catalog/plasmid/' \
  -H "Authorization: Token ${ADDGENE_API_KEY}" \
  --data-urlencode 'q=GFP' --data-urlencode 'sort_by=id' \
  --data-urlencode 'page_size=5'
```

Plasmid records include cloning, insert, sequence, and article data according to
scope; nullable fields and empty arrays are legitimate. Use licensed daily JSON
bulk downloads for large retrievals. The old `/api/plasmids`, `/depositors`, and
`/articles` routes are not the documented developer API.

Reviewed 2026-09-30: [OpenAPI schema](https://docs.developers.addgene.org/docs/schema/)
and [access requirements](https://developers.addgene.org/access-options/).
