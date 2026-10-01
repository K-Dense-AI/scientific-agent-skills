# Authentication & Setup

> **Security:** Never hardcode API keys in source code or commit them to version control. Use environment variables or a `.env` file scoped to `ZOTERO_*` keys only. Placeholder values like `ABC1234XYZ` below are illustrative — substitute your real credentials from env vars.

## Credentials

Obtain from https://www.zotero.org/settings/keys (or create a key at https://www.zotero.org/settings/keys/new):

| Credential | Where to Find |
|-----------|---------------|
| **User ID** | "Your userID for use in API calls" section |
| **API Key** | Create new key at /settings/keys/new, or via Settings → Security → Applications → "Create new key" at https://www.zotero.org/settings/security |
| **Group Library ID** | Integer after `/groups/` in group URL (e.g. `https://www.zotero.org/groups/169947`) |

## Environment Variables (recommended)

Store in `.env` or export in shell:

```
ZOTERO_LIBRARY_ID=436
ZOTERO_API_KEY=your_api_key_here
ZOTERO_LIBRARY_TYPE=user
```

For `.env` loading, install `python-dotenv` (`uv add python-dotenv`). It does not come with Pyzotero. Load in Python:

```python
import os
from dotenv import load_dotenv
from pyzotero import Zotero

load_dotenv()

zot = Zotero(
    library_id=os.environ['ZOTERO_LIBRARY_ID'],
    library_type=os.environ.get('ZOTERO_LIBRARY_TYPE', 'user'),
    api_key=os.environ['ZOTERO_API_KEY'],
)
```

## Library Types

```python
import os

# Personal library
zot = Zotero(
    os.environ['ZOTERO_LIBRARY_ID'],
    'user',
    os.environ['ZOTERO_API_KEY'],
)

# Group library — use the group ID as library_id
zot = Zotero('169947', 'group', os.environ['ZOTERO_API_KEY'])
```

**Important**: A `Zotero` instance is bound to a single library. To access multiple libraries, create multiple instances.

## Local Mode

Zotero 7+ supports unauthenticated local reads at `http://127.0.0.1:23119/api`. User ID `0` selects the local personal library, including an unsynced library. Group libraries still use their numeric group ID.

```python
zot = Zotero(library_id='0', library_type='user', local=True)
items = zot.items(limit=10)  # reads from local Zotero
```

Enable local API access: Settings → Advanced → "Allow other applications on this computer to communicate with Zotero". See [cli.md](cli.md) and [mcp.md](mcp.md) for richer local access.

## Optional Parameters

```python
zot = Zotero(
    library_id=os.environ['ZOTERO_LIBRARY_ID'],
    library_type='user',
    api_key=os.environ['ZOTERO_API_KEY'],
    locale='en-US',             # localise field names (e.g. 'fr-FR' for French)
)
```

## Key Permissions

Check what the current API key can access:

```python
info = zot.key_info()
# Returns dict with user info and group access permissions
```

Check accessible groups:

```python
# Call on a USER client: groups() builds /users/{library_id}/groups.
groups = zot.everything(zot.groups())
# Includes accessible groups and public groups the key owner belongs to.
```

## API Key Scopes

When creating an API key at https://www.zotero.org/settings/keys/new, choose appropriate permissions:

- **Read Only**: For retrieving items and collections
- **Write Access**: For creating, updating, and deleting items
- **Notes Access**: To include notes in read/write operations
- **Files Access**: Required for private stored-file access; uploads also need write access.

Public library reads can omit `api_key`. Pyzotero sends `Zotero-API-Version: 3` and uses bearer authentication for a supplied Web API key. `key_info()` uses `/keys/{key}` internally in 1.15.2, so avoid logging request URLs or exception bodies from that call. The API also supports `/keys/current` with header authentication.

`preserve_json_order` is deprecated; ordinary Python dictionaries retain insertion order.

## Local Writes (Zotero 10+)

Local keys are distinct from zotero.org keys. For an authorized write workflow:

```python
zot = Zotero('0', 'user', local=True)
auth = zot.authorize_local('Research library tool')  # Zotero displays its permission dialog
item = {
    'itemType': 'journalArticle', 'title': 'Example reference',
    'creators': [], 'tags': [], 'collections': [], 'relations': {},
}
result = zot.create_items([item])
if result.get('failed'):
    raise RuntimeError(result['failed'])
```

“Allow” yields a single-use key; “Always Allow” yields a reusable key (`auth['remember']`). Persist a reusable key securely together with `zot.server_id`, then pass `local_api_key` and `server_id` on the next run. Pyzotero discovers and sends `Zotero-Server-ID` before writes. A mismatch requires discarding that server's cached objects and versions. Local versions must never be reused for Web API writes or another local database. Do not loop on authorization dialogs.

The local API lacks `/items/new`: `item_template()`, `attachment_simple()`, and `attachment_both()` are unavailable. Build data using `item_types()` / `item_type_fields()`; for files use `upload_attachments()`. The local API also lacks Atom, so use `format='json'` with `include`, not Pyzotero's `content` exports.

Sources: [local API](https://www.zotero.org/support/dev/web_api/v3/local_api), [Pyzotero local guidance](https://pyzotero.readthedocs.io/en/latest/#the-local-zotero-api).
