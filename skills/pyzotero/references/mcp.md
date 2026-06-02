# MCP Server

Pyzotero 1.12+ ships an optional [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes your **local Zotero library** and Semantic Scholar integration as tools for LLM clients (e.g., Claude Desktop).

## Requirements

- **Zotero 7** with local API access enabled:
  - Zotero → Settings → Advanced → **Allow other applications on this computer to communicate with Zotero**
- Python 3.10+ (required by `pyzotero[mcp]`)

The MCP server reads from your local Zotero installation — it does not use the remote Web API or an API key.

## Installation

```bash
# In a project
uv add "pyzotero[mcp]"

# As a standalone tool
uv tool install "pyzotero[mcp]"
```

Run without installing:

```bash
uvx --from "pyzotero[mcp]" pyzotero-mcp
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
      "args": ["--from", "pyzotero[mcp]", "pyzotero-mcp"]
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
| `find_related` | Find semantically similar papers (SPECTER2 embeddings) |
| `get_citations` | Find papers that cite a given paper |
| `get_references` | Find papers referenced by a given paper |
| `search_semantic_scholar` | Search Semantic Scholar's paper index |

Semantic Scholar tools can optionally check whether results already exist in your local Zotero library (`check_library` parameter, enabled by default).

## MCP vs Web API vs CLI

| Mode | Access | API key | Best for |
|------|--------|---------|----------|
| Web API (`Zotero(...)`) | Remote library sync | Required | Automation, bulk CRUD, group libraries |
| CLI (`pyzotero[cli]`) | Local Zotero 7 | Not required | Shell scripts, quick local search |
| MCP (`pyzotero[mcp]`) | Local Zotero 7 | Not required | LLM agents in sandboxed apps |

For remote library management from Python, use the Web API client documented in the other reference files. Use MCP or CLI when you need fast access to locally indexed PDFs and full-text search without network calls.
