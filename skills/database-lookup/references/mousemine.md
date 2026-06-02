# MouseMine (Mouse Genome Informatics, InterMine-based)

## Base URL
```
https://www.mousemine.org/mousemine/service
```

## Auth
No auth for most queries. Free account token needed for saved lists.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/search?q={query}&format=json` | Keyword search across all objects |
| `/template/results?name={template}&op1=LOOKUP&value1={value}&format=json` | Run pre-built template query |
| `/query/results` (POST) | Run custom PathQuery (XML) |
| `/model` | Retrieve data model |

## Example Calls
```
# Keyword search for Brca1
https://www.mousemine.org/mousemine/service/search?q=Brca1&format=json

# Template: Gene → GO terms
https://www.mousemine.org/mousemine/service/template/results?name=Gene_GO&op1=LOOKUP&value1=Pax6&format=json
```

## Custom Query (POST)
```
POST /query/results
Content-Type: application/x-www-form-urlencoded
query=<query model="genomic" view="Gene.symbol Gene.name" sortOrder="Gene.symbol asc"><constraint path="Gene.organism.name" op="=" value="Mus musculus"/></query>&format=json
```

## Response Format
JSON: `{"results": [...], "statusCode": 200}`. Also supports XML, TSV, CSV via `format` param.

## Rate Limits
No published limits. Be reasonable.
