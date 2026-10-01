# Search & Request Parameters

Supported parameters can be passed directly to a Read API call, or configured for the next call with `add_parameters()`. Pass a format and its options together on one call: a later call with keyword arguments can reset a preconfigured export to JSON in 1.15.2.

```python
# Inline parameters (valid for one call only)
results = zot.items(q='climate change', limit=50, sort='date', direction='desc')

# Configure the next call
zot.add_parameters(limit=50, sort='dateAdded')
results = zot.items()
```

## Available Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | str | Quick search — titles and creator fields by default |
| `qmode` | str | `'titleCreatorYear'` (default) or `'everything'` (full-text) |
| `itemType` | str | Filter by item type. See search syntax for operators |
| `tag` | str or list | Filter by tag(s). Multiple tags = AND logic |
| `since` | int | Return only objects modified after this library version |
| `sort` | str | Sort field (see below) |
| `direction` | str | `'asc'` or `'desc'` |
| `limit` | int | 1–100, or `None` |
| `start` | int | Zero-based offset into result set (default 0) |
| `format` | str | Response format (see exports.md) |
| `itemKey` | str | Comma-separated item keys (up to 50) |
| `content` | str | Legacy Atom content; remote API only |
| `include` | str | JSON members such as `'data,bib'`, `'citation'`, or `'csljson'` |
| `style` | str | CSL style name (used with `content='bib'`) |
| `linkwrap` | str | `'1'` to wrap URLs in `<a>` tags in bibliography output |

## Sort Fields

`dateAdded`, `dateModified`, `title`, `creator`, `itemType`, `date`, `publisher`,
`publicationTitle`, `journalAbbreviation`, `language`, `accessDate`,
`libraryCatalog`, `callNumber`, `rights`, `addedBy`; `numItems` applies to tag lists.

## Tag Search Syntax

```python
# Single tag
zot.items(tag='machine learning')

# Multiple tags — AND logic (items must have all tags)
zot.items(tag=['climate', 'adaptation'])

# OR logic (items with any tag)
zot.items(tag='climate || adaptation')

# Exclude a tag
zot.items(tag='-retracted')
```

## Item Type Filtering

```python
# Single type
zot.items(itemType='journalArticle')

# OR multiple types
zot.items(itemType='journalArticle || book')

# Exclude a type
zot.items(itemType='-note')
```

Common item types: `journalArticle`, `book`, `bookSection`, `conferencePaper`,
`thesis`, `report`, `dataset`, `preprint`, `note`, `attachment`, `webpage`,
`patent`, `statute`, `case`, `hearing`, `interview`, `letter`, `manuscript`,
`map`, `artwork`, `audioRecording`, `videoRecording`, `podcast`, `film`,
`radioBroadcast`, `tvBroadcast`, `presentation`, `encyclopediaArticle`,
`dictionaryEntry`, `forumPost`, `blogPost`, `instantMessage`, `email`,
`document`, `computerProgram`, `bill`, `newspaperArticle`, `magazineArticle`

## Examples

```python
# Recent journal articles matching query, sorted by date
zot.items(q='CRISPR', itemType='journalArticle', sort='date', direction='desc', limit=20)

# Items modified since a known library version
zot.items(since=4000)

# Items with a specific tag, offset for pagination
zot.items(tag='to-read', limit=25, start=25)

# Full-text search
zot.items(q='gene editing', qmode='everything', limit=10)
```

For tag endpoints, `qmode='contains'` is the default; prefix matching requires `qmode='startsWith'`. Read parameters are endpoint-specific, not valid on every method. `limit=None` omits the limit: it does **not** fetch a whole remote JSON item list (the server defaults to 25). Local and remote quick search implementations may return different matches. Source: [search, sorting, and pagination contracts](https://www.zotero.org/support/dev/web_api/v3/basics#search_parameters).
