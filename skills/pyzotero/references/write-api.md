# Write API Methods

## Creating Items

For the remote API, use `item_template()` to get a valid template. The local API lacks `/items/new`; build data from the type/field endpoints instead (see [authentication.md](authentication.md)). All write examples below are illustrative and must use an authorized target library.

```python
# Get a template for a specific item type
template = zot.item_template('journalArticle')

# Fill in fields
template['title'] = 'Example article (illustrative metadata)'
template['date'] = '2024'
# Populate DOI, title, journal, and authors together from a verified source;
# never pair a real DOI with fabricated bibliographic metadata.
template['creators'] = [
    {'creatorType': 'author', 'firstName': 'Jane', 'lastName': 'Doe'},
    {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Smith'},
]

# Validate fields before creating (raises InvalidItemFieldsError if invalid)
zot.check_items([template])

# Create the item
resp = zot.create_items([template])
# Response maps are indexed by each input's string index: '0', '1', ...
if resp.get('failed'):
    raise RuntimeError(f"Creation failures: {resp['failed']}")
new_key = resp['successful']['0']['key']
# successful holds saved objects; legacy success maps indices to keys.
# unchanged maps indices to existing keys when no change was needed.
```

### Create Multiple Items at Once

```python
templates = []
for data in paper_data_list:
    t = zot.item_template('journalArticle')
    t['title'] = data['title']
    t['DOI'] = data['doi']
    templates.append(t)

for start in range(0, len(templates), 50):
    resp = zot.create_items(templates[start:start + 50])
    if resp.get('failed'):
        raise RuntimeError(f"Batch starting at {start}: {resp['failed']}")
```

### Create Child Items

```python
# Create a note as a child of an existing item
note_template = zot.item_template('note')
note_template['note'] = '<p>My annotation here</p>'
zot.create_items([note_template], parentid='PARENTKEY')
```

## Updating Items

```python
# Retrieve, modify, update
item = zot.item('ITEMKEY')
item['data']['title'] = 'Updated Title'
item['data']['abstractNote'] = 'New abstract text.'
success = zot.update_item(item)  # returns True or raises error

# Update many existing items while retaining per-item status
items = zot.items(itemType='journalArticle', limit=10)
for item in items:
    item['data']['extra'] = item['data'].get('extra', '') + '\nProcessed'
for start in range(0, len(items), 50):
    result = zot.create_items([i['data'] for i in items[start:start + 50]])
    if result.get('failed'):
        raise RuntimeError(result['failed'])
```

## Deleting Items

```python
# Permanent deletion of one item: use its object version
item = zot.item('ITEMKEY')
zot.delete_item(item)

# Multiple deletion uses a LIBRARY version, not the first item's version.
# Review the exact selected keys first; at most 50 per request.
items = zot.items(tag='to-delete', limit=50)
library_version = int(zot.request.headers['Last-Modified-Version'])
if items:
    zot.delete_item(items, last_modified=library_version)

# To trash instead of permanently delete:
item = zot.item('ITEMKEY')
item['data']['deleted'] = 1  # use 0 to restore
zot.update_item(item['data'])
```

## Item Types and Fields

```python
# All available item types
item_types = zot.item_types()
# [{'itemType': 'artwork', 'localized': 'Artwork'}, ...]

# All available fields
fields = zot.item_fields()

# Valid fields for a specific item type
journal_fields = zot.item_type_fields('journalArticle')

# Valid creator types for an item type
creator_types = zot.item_creator_types('journalArticle')
# [{'creatorType': 'author', 'localized': 'Author'}, ...]

# All localised creator field names
creator_fields = zot.creator_fields()

# Attachment link modes (needed for attachment templates)
link_modes = zot.item_attachment_link_modes()

# Template for an attachment
attach_template = zot.item_template('attachment', linkmode='imported_file')
```

## Optimistic Locking

Single-item `last_modified` is the **item version**. The normal read/modify/write example already sends it; an explicit override must come from that same item's read:

```python
# Only update if this item's version still matches
zot.update_item(item, last_modified=item['version'])
# Raises PreConditionFailedError on a stale version.
```

## Notes

- `create_items()` accepts up to 50 items per call; batch if needed.
- `update_items()` auto-chunks at 50 but returns a coarse Boolean without checking each `failed` mapping in 1.15.2. Use `create_items()` with keyed, versioned data in explicit batches when every result must be reconciled.
- If a dict passed to `create_items()` contains a `key` matching an existing item, it will be updated rather than created.
- `check_items()` checks field names against the global field set, not all type-specific values or scientific metadata. Server failures remain possible.
- Item `PATCH` leaves omitted fields unchanged, but supplied arrays replace entire creator/tag/collection lists. Re-fetch after writes before further edits.
- A timeout does not establish whether a write happened. Pyzotero generates a new write token on another `create_items()` call, so blindly repeating an unkeyed create can duplicate records. Reconcile first; retry only verified failures.
- Batch POST preconditions use the library version when supplied; per-object `version` values are usually simpler. HTTP 200 can still contain failed entries.

Sources: [write request/response contracts](https://www.zotero.org/support/dev/web_api/v3/write_requests), [Pyzotero 1.15.2 source](https://github.com/urschrei/pyzotero/blob/v1.15.2/src/pyzotero/_client.py).
