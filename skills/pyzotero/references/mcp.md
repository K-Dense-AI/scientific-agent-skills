# MCP Server

Pyzotero 1.15.2 ships an optional [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes your **local Zotero library** and Semantic Scholar integration as tools for LLM clients (e.g., Claude Desktop).

## Requirements

- **Zotero 7+** for local reads, **Zotero 10+** for local writes, with local API access enabled:
  - Zotero → Settings → Advanced → **Allow other applications on this computer to communicate with Zotero**
- Python 3.10+ (required by `pyzotero[mcp]`)

Zotero-library tools read the local desktop API without a key. Semantic Scholar tools call an external network API. The server starts read-only; local write tools require explicit enablement and a separate local authorization key.

## Installation

```bash
# In a project
uv add "pyzotero[mcp]==1.15.2"

# As a standalone tool
uv tool install "pyzotero[mcp]==1.15.2"
```

Run without installing:

```bash
uvx --from "pyzotero[mcp]==1.15.2" pyzotero-mcp
```

## Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

**If `pyzotero-mcp` is installed:**

```json
{
  "mcpServers": {
    "zotero": {
      "command": "pyzotero-mcp"
    }
  }
}
```

**Without installing (via uvx):**

```json
{
  "mcpServers": {
    "zotero": {
      "command": "uvx",
      "args": ["--from", "pyzotero[mcp]==1.15.2", "pyzotero-mcp"]
    }
  }
}
```

## Available Tools

### Zotero Library Tools

| Tool | Description |
|------|-------------|
| `search` | Search the local library by query, item type, collection, tag, or full-text content |
| `get_item` | Get a single item by key |
| `get_children` | Get child items (attachments, notes) of an item |
| `list_collections` | List all collections |
| `list_tags` | List all tags, optionally filtered by collection |
| `get_fulltext` | Get full-text content of a PDF or other attachment |

### Semantic Scholar Tools

| Tool | Description |
|------|-------------|
| `find_related` | Request recommended papers for a seed paper |
| `get_citations` | Find papers that cite a given paper |
| `get_references` | Find papers referenced by a given paper |
| `search_semantic_scholar` | Search Semantic Scholar's paper index |

Semantic Scholar tools can optionally check whether results already exist in your local Zotero library (`check_library` parameter, enabled by default).

## MCP vs Web API vs CLI

| Mode | Access | API key | Best for |
|------|--------|---------|----------|
| Web API (`Zotero(...)`) | Remote library | Private reads/writes | Automation, bulk CRUD, group libraries |
| CLI (`pyzotero[cli]`) | Local Zotero | Local key for writes | Shell scripts, quick local search |
| MCP (`pyzotero[mcp]`) | Local Zotero + external Semantic Scholar | Local key for enabled writes | LLM agents in sandboxed apps |

For remote library management from Python, use the Web API client documented in the other reference files. Local library searches can work without external network access. Semantic Scholar lookups always need the network.

## Tool Arguments and Results

`search(query='', fulltext=False, itemtype='', collection='', tag='', limit=50, offset=0)` returns JSON text with `count` and `items`. For MCP, `tag='reviewed,unread'` means AND; `itemtype='journalArticle || book'` means OR. This differs from the CLI's repeated flags. Parse the tool's JSON text before using fields; failed calls can return an `error` object instead.

Semantic Scholar tools return `papers` with counts and optional local-library annotations, not raw Zotero items. The installed implementation uses:

| Tool | External API request | Response handling / limit |
|------|----------------------|---------------------------|
| `find_related` | GET `/graph/v1/paper/{id}`, then POST `/recommendations/v1/papers` with `positivePaperIds` | Normalizes `recommendedPapers`; up to 500 |
| `get_citations` | GET `/graph/v1/paper/{id}/citations` | Extracts `data[].citingPaper`; one page, up to 1000 |
| `get_references` | GET `/graph/v1/paper/{id}/references` | Extracts `data[].citedPaper`; one page, up to 1000 |
| `search_semantic_scholar` | GET `/graph/v1/paper/search` | Extracts `data`; up to 100, relevance search |

Host: `https://api.semanticscholar.org`. Pyzotero 1.15.2's integration does not send a Semantic Scholar API key or expose an API-key option, so do not imply a Zotero key authenticates these requests. Handle public-service rate limits. `check_library=False` avoids a local DOI-index scan. DOI absence and normalization can make local-library matching incomplete.

The MCP tools do not expose an offset for citations/references/search and are not exhaustive literature search tools. Citation/reference `total` in the helper reflects the returned page, not a global count. `min_citations` filters fetched results locally. Leave the MCP `sort` argument empty: the wrapper sends it to relevance `/paper/search`, whose current official schema does not support sorting. Do not promise globally citation-ranked results.

## Enabling Writes

For an explicitly intended local write workflow, install both extras and obtain a persistent key:

```bash
uv tool install "pyzotero[cli,mcp]==1.15.2"
pyzotero authorize --app-name "Research assistant"
# Choose Always Allow in Zotero if persistent access is intended.
pyzotero-mcp --enable-writes
```

The server reads the stored key/server-ID pair created by the CLI. Alternatively, `PYZOTERO_LOCAL_API_KEY` and `PYZOTERO_LOCAL_SERVER_ID` override the file. Keep those values private. With `--enable-writes`, additional tools are registered: `list_item_fields`, `create_item`, `update_item`, `add_tags`, `create_collection`, `add_to_collection`, `remove_from_collection`, `move_to_collection`, and `add_attachment`. Attachment paths must be absolute; files are copied into Zotero storage.

`delete_item` is registered only with `--enable-deletes`, which also enables writes. It permanently erases items and can propagate via sync; it does not move them to trash.

Sources: [Pyzotero MCP documentation](https://pyzotero.readthedocs.io/en/latest/#mcp-server), [Graph schema](https://api.semanticscholar.org/graph/v1/swagger.json), [recommendations schema](https://api.semanticscholar.org/recommendations/v1/swagger.json).
