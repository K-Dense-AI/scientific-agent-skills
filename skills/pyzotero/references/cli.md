# Command-Line Interface

The pyzotero CLI connects to your **local Zotero installation** (Zotero 7+ for reads, Zotero 10+ for writes) (not the remote Web API). It requires a running Zotero desktop app with local API access enabled:

**Zotero → Settings → Advanced → Allow other applications on this computer to communicate with Zotero**

## Installation

```bash
uv add "pyzotero[cli]==1.15.2"
# or run without installing:
uvx --from "pyzotero[cli]==1.15.2" pyzotero search -q "your query"
```

## Searching

```bash
# Search titles and metadata
pyzotero search -q "machine learning"

# Full-text search (includes PDF content)
pyzotero search -q "climate change" --fulltext

# Filter by item type
pyzotero search -q "methodology" --itemtype journalArticle --itemtype book

# Filter by tags (AND logic)
pyzotero search -q "evolution" --tag "reviewed" --tag "high-priority"

# Search within a collection
pyzotero search --collection ABC123 -q "test"

# Paginate results
pyzotero search -q "deep learning" --limit 20 --offset 40

# Output as JSON (for machine processing)
pyzotero search -q "protein" --json
```

## Getting Individual Items

```bash
# Get a single item by key
pyzotero item ABC123

# Get as JSON
pyzotero item ABC123 --json

# Get child items (attachments, notes)
pyzotero children ABC123 --json

# Get multiple items at once (up to 50)
pyzotero subset ABC123 DEF456 GHI789 --json
```

## Collections & Tags

```bash
# List all collections
pyzotero listcollections

# List all tags
pyzotero tags

# Tags in a specific collection
pyzotero tags --collection ABC123
```

## Full-Text Content

```bash
# Get full-text content of an attachment
pyzotero fulltext ABC123
```

## Item Types

```bash
# List all available item types
pyzotero itemtypes
```

## DOI Index

```bash
# Get complete DOI-to-key mapping (useful for caching)
pyzotero doiindex > doi_cache.json
# Returns JSON: {"10.1038/s41592-024-02233-6": {"key": "ABC123", "doi": "..."}}
```

## Output Format

By default the CLI outputs human-readable text including title, authors, date, publication, volume, issue, DOI, URL, and PDF attachment paths.

Use `--json` for structured JSON output suitable for piping to other tools.

## Search Behaviour Notes

- Default search covers top-level item titles and metadata fields only
- `--fulltext` expands search to PDF content; results show parent bibliographic items (not raw attachments)
- Multiple `--tag` flags use AND logic
- Multiple `--itemtype` flags use OR logic

## Authorized Local Writes (Zotero 10+)

The CLI also supports local writes in the reviewed 1.15.2 release. These are illustrative commands, not part of the read-only smoke test:

```bash
# Zotero displays its authorization dialog; choose the scope you intend.
pyzotero authorize --app-name "Research library tool"
pyzotero listitemfields journalArticle
pyzotero createitem items.json --json
pyzotero createcollection "Review papers" --json
pyzotero addtocollection COLKEY ITEMKEY --json
pyzotero removefromcollection COLKEY ITEMKEY --json
pyzotero movetocollection --from OLDCOLKEY --to NEWCOLKEY ITEMKEY --json
```

`items.json` contains an editable item object or array of objects. Validate bibliographic metadata before importing. The stored persistent local key and server ID are in `$XDG_CONFIG_HOME/pyzotero/local-api-key.json` (default `~/.config/pyzotero/local-api-key.json`); a Web API key does not authorize these commands. Collection membership commands update one item at a time.

For Semantic Scholar CLI commands (`related`, `citations`, `references`, `s2search`), network access is required; see the limitations in [mcp.md](mcp.md). Sources: [CLI documentation](https://pyzotero.readthedocs.io/en/latest/#command-line-interface), [release CLI source](https://github.com/urschrei/pyzotero/blob/v1.15.2/src/pyzotero/cli.py).
