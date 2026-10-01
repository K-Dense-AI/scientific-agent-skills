# CoGAP MCP connection requirements

The skill requires an existing CoGAP MCP service. Installing the skill alone does not create a connection, grant data access, or start a public endpoint. Obtain the service address or local launch instructions and any authorization from the service operator through a private channel.

## Remote connection

Use a client that supports MCP Streamable HTTP and bearer authentication. Configure the operator-issued endpoint in the client's MCP settings. The endpoint normally ends in `/mcp`. Use HTTPS for a remote service.

Supply the bearer credential through the client's supported environment variable, secret store or protected authentication field. Do not place credentials in a URL, skill file, Git commit, shared prompt or published client configuration. Never send a credential to a different host to diagnose a failed connection.

The current service supports bearer authentication; it does not provide an OAuth flow. A client that only supports OAuth or the older SSE transport requires separate compatibility work. Check the current operator documentation rather than assuming every client supports this connection.

## Local connection

An operator may instead provide an installed CoGAP MCP service for stdio. Use that operator's interpreter, module and environment settings in the client's MCP process configuration. The service module is `cogap_mcp`; its default entry point is `python -m cogap_mcp` in an environment where it is already installed.

This repository does not contain or distribute the service implementation. There is no package-install command or downloadable server provided here. Do not assume that a similarly named package is the correct service. Do not extract database credentials from another application to construct a connection.

## Verify before querying

1. Initialize the MCP connection and list the actual tools and their schemas. Server names and tool prefixes are client-specific.
2. Expect `catalog`, `resolve_disease_pair`, `comorbidity_summary`, `mr_results`, `gene_features`, `trend_results`, `risk_model` and `literature_search`. If a required tool is missing, state the limitation rather than inventing a replacement.
3. Start with a bounded catalog query using the exposed schema, for example `kind="diseases", limit=1`. This example is illustrative; use the bounds advertised by the connected service.
4. Inspect the actual result envelope. A usable real-data result has `ok=true` and `mock=false`; retain `sources` and any `warnings`. A connection refusal, database failure or successful empty result must be described separately.

Listing a server in a client's settings is not proof of a successful tool call. A service health check is not proof that every requested scientific module or pair has data.

## Access and limits

The tools return stored CoGAP results and configured literature retrieval. They do not accept arbitrary SQL, URLs, shell commands or uploaded matrices, run new analyses, train models, or expose user chat histories. The service may reject mock results or a disconnected real-data backend. Do not enable demonstration mode to bypass those checks.

Dataset coverage, interpretation, external literature availability and operator access policy must be established from the actual connected service. This public skill contains no scientific dataset and grants no data redistribution rights.
