# Read API Methods

## Retrieving Items

```python
# One page of items (100 per call by default; excludes trash)
items = zot.items()

# Top-level items only (excludes attachments/notes that are children)
top = zot.top(limit=25)

# A specific item by key
item = zot.item('ITEMKEY')

# Up to 50 specific items in ONE request
subset = zot.items(itemKey=','.join(['KEY1', 'KEY2', 'KEY3']))
# get_subset([...]) instead makes one single-item request per key (up to 50).

# Items from trash
trash = zot.trash()

# Deleted items (requires 'since' parameter)
deleted = zot.deleted(since=1000)

# Items from "My Publications"
pubs = zot.publications()  # user libraries only

# Count all items
count = zot.count_items()

# Count top-level items
n = zot.num_items()
```

## Item Data Structure

Items are returned as dicts. Data lives in `item['data']`:

```python
item = zot.item('VDNIEAPH')  # a dict, not a one-element list
title = item['data'].get('title', '')
item_type = item['data']['itemType']
creators = item['data'].get('creators', [])
tags = item['data']['tags']
key = item['data']['key']
version = item['data']['version']
collections = item['data']['collections']
doi = item['data'].get('DOI', '')
```

## Child Items

```python
# Get child items (notes, attachments) of a parent
children = zot.children('PARENTKEY')
```

## Retrieving Collections

```python
# One page of collections (including subcollections)
collections = zot.collections()

# Top-level collections only
top_collections = zot.collections_top()

# A specific collection
collection = zot.collection('COLLECTIONKEY')

# Sub-collections of a collection
sub = zot.collections_sub('COLLECTIONKEY')

# All collections and sub-collections in a flat list
all_cols = zot.all_collections()
# Or from a specific collection down:
all_cols = zot.all_collections('COLLECTIONKEY')

# Items in a specific collection (not sub-collections)
col_items = zot.collection_items('COLLECTIONKEY')

# Top-level items in a specific collection
col_top = zot.collection_items_top('COLLECTIONKEY')

# Count items in a collection
n = zot.num_collectionitems('COLLECTIONKEY')
```

## Retrieving Tags

```python
# All tags in the library
tags = zot.everything(zot.tags())

# Tags from a specific item
item_tags = zot.item_tags('ITEMKEY')

# Tags in a collection
col_tags = zot.collection_tags('COLLECTIONKEY')
```

## Retrieving Groups

```python
# Use a client initialized with the USER ID, not a group ID.
groups = zot.everything(zot.groups())
# /users/{userID}/groups: inspect each group's access before writing.
```

## Version Information

```python
# Last modified version of the library
version = zot.last_modified_version()

# Item versions dict {key: version}
item_versions = zot.item_versions()

# Collection versions dict {key: version}
col_versions = zot.collection_versions()

# Changes since a known version (for syncing)
changed_items = zot.item_versions(since=1000)
```

## Library Settings

```python
settings = zot.settings()
# Returns a setting-name mapping; values carry version and value.
# Available settings depend on the library; do not assume a fixed set.
# Use 'since' to get only changes:
new_settings = zot.settings(since=500)
```

## Saved Searches

```python
searches = zot.searches()
# Retrieves saved search metadata (not results)
```

## Endpoint and Sync Boundaries

All library routes use `/users/{userID}` or `/groups/{groupID}` under `https://api.zotero.org`. Item reads use `/items`, `/items/top`, `/items/trash`, `/items/{key}`, and `/items/{key}/children`. Collections use `/collections`, `/collections/top`, `/collections/{key}`, `/collections/{key}/collections`, and `/collections/{key}/items[/top]`. Tags use `/tags`, `/items/{key}/tags`, or `/collections/{key}/tags`. `settings()`, `searches()`, and `deleted(since=...)` use the corresponding library routes. `publications()` uses `/users/{userID}/publications/items`.

`deleted()` returns a dict of deleted keys grouped by object type, not item records. A complete incremental sync needs changed objects **and** deletions, plus `includeTrashed=1` when tracking trash transitions. Save the library version from the completed read sequence, not a later unrelated call; restart/reconcile if versions change during pagination. See [official syncing rules](https://www.zotero.org/support/dev/web_api/v3/syncing). `last_modified_version()` makes its own multi-object read.
