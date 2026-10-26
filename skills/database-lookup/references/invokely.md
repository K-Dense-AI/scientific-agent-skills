# Invokely Official Statistics

## Role and access

Invokely is a hosted access layer for official statistical data. It routes requests across statistical publishers and returns source details with each figure. Treat the publisher named in the result as the data authority; cite `source.citation` or `source.url`, and identify Invokely as the retrieval service when that context is useful. Source and indicator coverage varies by place and period.

The MCP endpoint is `https://invokely.ai/mcp`. It requires an API key or OAuth through a supported client. The no-account trial is `https://invokely.ai/mcp/trial`, limited to 25 calls per day per IP address. The account Free plan includes 500 MCP calls per month and lists a burst limit of 300 requests per minute. MCP calls use the account's call allowance.

The REST API base is `https://invokely.ai/api/v1`. REST statistical data queries require Builder, Pro, or prepaid credits. Catalog lookups are free, and CSV, Excel, and chart exports are included on every plan. MCP and REST expose the same six statistics operations and share usage accounting for data calls. Check the current [pricing page](https://invokely.ai/pricing) before planning sustained use.

For an MCP client that requires local stdio, the separate [MIT-licensed Node.js 22 connector](https://github.com/estevecastells/invokely-mcp-connector) forwards requests to the hosted service. It contains client code, not the Invokely backend. Workspace tools are separate from the six statistics operations and are outside this lookup workflow.

## Choosing and calling an operation

Use the hosted MCP tools for these statistics tasks:

| Tool | Use |
|---|---|
| `search_indicators` | Find an indicator ID by a natural-language query. Pass `geography` when the place matters so results reflect availability for that place. |
| `resolve_place` | Disambiguate a place name or inspect its normalized identity and official codes. Other statistics tools also accept place names directly. |
| `get_value` | Retrieve one figure for an indicator and place, latest by default or for a specified period. |
| `get_series` | Retrieve a time series for one place. Check its source, frequency, `total_points`, `truncated`, and any gap notes. |
| `compare` | Compare one indicator across 2 to 10 places for the same period. Preserve `comparable` and explain when it is false. |
| `rank_places` | Rank places of a selected level within an area. The optional `limit` defaults to 10; check `total` against the number of returned values before describing a ranking as complete. |

Start with indicator discovery, then resolve the place only when needed. Use the returned indicator ID in a retrieval call. For example, the documented request `get_value` with `{"indicator":"population","place":"Mataró"}` asks for the latest population figure for Mataró. Use `get_series` when the question is about change over time, and `compare` or `rank_places` only when their place, level, and period semantics match the question.

The published documentation describes coverage for the United States at national, state, and county levels, plus population for cities of 10,000 or more; EU countries and regions; Spain at municipality, province, region, and national levels; national and regional series for the United Kingdom, Canada, Australia, Ireland, and New Zealand; and every country plus the World through World Bank data. It does not promise every indicator for every geography. Use `search_indicators` with the requested place and inspect any availability notes instead of inferring coverage from country membership.

## Provenance and completeness

For a figure response, keep the indicator name, place, period, unit, source publisher, source title, source URL, retrieval date, and ready-made citation. Mention a status such as provisional, estimated, or low reliability when present. Derived indicators can include their inputs. For `compare`, preserve source differences and notes when `comparable` is false. For `get_series`, distinguish observed points from any separately requested projections and report gaps or truncation. For `rank_places`, do not report a limited list as exhaustive when `total` is larger than the returned values.

For REST clients, use the operation parameters and response schemas in Invokely's current [OpenAPI document](https://invokely.ai/openapi.json). The interactive tool descriptions, examples, response fields, coverage, and citation rules are in the [developer documentation](https://invokely.ai/docs#tools); source publishers are listed on the [sources page](https://invokely.ai/sources).
