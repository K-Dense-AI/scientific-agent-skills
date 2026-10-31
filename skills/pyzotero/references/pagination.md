# Pagination: follow(), everything(), Generators

Pyzotero returns 100 items by default. Use these methods to retrieve more.

## everything() — Retrieve All Results

The simplest way to get all items:

```python
# All items in the library
all_items = zot.everything(zot.items())

# All top-level items
all_top = zot.everything(zot.top())

# All items in a collection
all_col = zot.everything(zot.collection_items('COLKEY'))

# All items matching a search
all_results = zot.everything(zot.items(q='machine learning', itemType='journalArticle'))
```

Use `everything()` with list-returning endpoints (items, collections, tags, searches) and BibTeX databases. Do not pass dict responses (`format=versions`, `deleted`, `settings`) or bytes (`format=keys`): their iteration semantics differ.

## follow() — Sequential Pagination

```python
# Retrieve items in batches, manually advancing the page
first_batch = zot.top(limit=25)
second_batch = zot.follow()   # next 25 items
third_batch = zot.follow()    # next 25 items
```

`follow()` returns `None` when no next-page link exists. `iterfollow()` and `makeiter()` end by raising `StopIteration` through normal generator exhaustion. Do not interleave other reads on the same client while paging: they replace its pagination links.

## iterfollow() — Generator

```python
# Create a generator over follow()
first = zot.top(limit=10)
lazy = zot.iterfollow()

# Retrieve subsequent pages
second = next(lazy)
third = next(lazy)
```

## makeiter() — Generator over Any Method

```python
# Create a generator directly from a method call
gen = zot.makeiter(zot.top(limit=25))

page1 = next(gen)  # first 25 items, fetched AGAIN by makeiter()
page2 = next(gen)  # next 25 items
# Raises StopIteration when exhausted
```

## Manual start/limit Pagination

```python
page_size = 50
offset = 0

while True:
    batch = zot.items(limit=page_size, start=offset)
    if not batch:
        break
    # process batch
    for item in batch:
        process(item)
    offset += page_size
```

## Performance Notes

- `everything()` makes multiple API calls sequentially; large libraries may take time.
- For incremental synchronization, combine `since=version` with `deleted(since=version)` and account for changes during paging; see [read-api.md](read-api.md).
- The raw local API has no default limit, but Pyzotero still injects 100 unless you pass `limit=None`. Local reads can use `zot.items(limit=None)`; remote JSON reads remain paginated.
