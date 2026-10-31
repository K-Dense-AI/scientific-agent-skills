# Saved Searches

## Retrieving Saved Searches

```python
# Get all saved search metadata (not results)
searches = zot.everything(zot.searches())
# Returns list of dicts with name, key, conditions, version

for search in searches:
    print(search['data']['name'], search['data']['key'])
```

`searches()` returns metadata. The Web API does not execute saved searches. The current **local** API supports `/api/users/0/searches/{searchKey}/items` (or the group equivalent), but Pyzotero 1.15.2 has no dedicated wrapper for that route.

## Creating Saved Searches

Each condition dict must have `condition`, `operator`, and `value`:

```python
conditions = [
    {
        'condition': 'title',
        'operator': 'contains',
        'value': 'machine learning'
    }
]
zot.saved_search('ML Papers', conditions)
```

### Multiple Conditions (AND logic)

```python
conditions = [
    {'condition': 'itemType', 'operator': 'is', 'value': 'journalArticle'},
    {'condition': 'tag', 'operator': 'is', 'value': 'unread'},
    {'condition': 'date', 'operator': 'isInTheLast', 'value': '3 years'},
]
zot.saved_search('Recent Unread Articles', conditions)
```

## Deleting Saved Searches

```python
# Get search keys first
searches = zot.everything(zot.searches())
keys = [s['data']['key'] for s in searches if s['data']['name'] == 'Old Search']
# The SDK's delete_saved_search() omits the required library-version
# precondition in 1.15.2. For REMOTE libraries, issue the documented request:
if keys:
    if len(keys) > 50:
        raise ValueError('Review and delete at most 50 search keys per request')
    version = zot.last_modified_version()
    response = zot.client.delete(
        f'https://api.zotero.org/{zot.library_type}/{zot.library_id}/searches',
        params={'searchKey': ','.join(keys)},
        headers={**zot.default_headers(), 'If-Unmodified-Since-Version': str(version)},
    )
    response.raise_for_status()
    assert response.status_code == 204
```

## Discovering Valid Operators and Conditions

```python
# All available operators
operators = zot.show_operators()

# All available conditions
conditions = zot.show_conditions()

# Operators valid for a specific condition
title_operators = zot.show_condition_operators('title')
# A set of supported operator strings in this SDK release.
```

## Common Condition/Operator Combinations

| Condition | Common Operators |
|-----------|-----------------|
| `title` | `contains`, `doesNotContain`, `is`, `isNot` |
| `tag` | `is`, `isNot` |
| `itemType` | `is`, `isNot` |
| `date` | `isBefore`, `isInTheLast`, `is`, `isNot` |
| `creator` | `contains`, `is` |
| `publicationTitle` | `contains`, `is` |
| `year` | `is`, `isNot`, `contains` |
| `collection` | `is`, `isNot` |
| `fulltextContent` | `contains` |

`show_operators()` is a mapping; `show_conditions()` is a keys view; `show_condition_operators()` returns a set. These use the SDK's bundled condition definitions, not live server discovery. Check `saved_search()`'s creation result for `failed`, as with `create_items()`. The direct remote delete above is illustrative and does not inherit Pyzotero's backoff wrapper; handle 429/503 and their `Retry-After` headers before another request. Never send it to the local API without local authorization and server-ID handling.

Sources: [search writes](https://www.zotero.org/support/dev/web_api/v3/write_requests#search_requests), [local search execution](https://www.zotero.org/support/dev/web_api/v3/local_api).

The SDK 1.15.2 condition table rejects `date/isAfter` despite listing `isAfter` in its global operators. Use a permitted condition/operator pair or an explicitly constructed direct API request after checking the server contract.
