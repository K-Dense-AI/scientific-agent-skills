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

Load in Python:

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

## Local Mode (Read-Only)

Connect to your local Zotero installation without an API key. Only supports read requests.

```python
zot = Zotero(library_id='436', library_type='user', local=True)
items = zot.items(limit=10)  # reads from local Zotero
```

For Zotero 7, enable local API access: Settings → Advanced → "Allow other applications on this computer to communicate with Zotero". See [cli.md](cli.md) and [mcp.md](mcp.md) for richer local access.

## Optional Parameters

```python
zot = Zotero(
    library_id=os.environ['ZOTERO_LIBRARY_ID'],
    library_type='user',
    api_key=os.environ['ZOTERO_API_KEY'],
    preserve_json_order=True,   # use OrderedDict for JSON responses
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
groups = zot.groups()
# Returns list of group libraries accessible to the current key
```

## API Key Scopes

When creating an API key at https://www.zotero.org/settings/keys/new, choose appropriate permissions:

- **Read Only**: For retrieving items and collections
- **Write Access**: For creating, updating, and deleting items
- **Notes Access**: To include notes in read/write operations
- **Files Access**: Required for uploading attachments
