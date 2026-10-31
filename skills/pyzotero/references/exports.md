# Export Formats

These examples target Pyzotero 1.15.2. Set the format and its parameters together on the read call. Calling `add_parameters(format='bibtex')` and then `top(limit=50)` resets the format to JSON in this release; the result will not have `.entries`.

## BibTeX

```python
import bibtexparser

bibtex_db = zot.top(format='bibtex', limit=50)
# bibtexparser 1.x BibDatabase
for entry in bibtex_db.entries:
    print(entry.get('title'), entry.get('author'))
with open('library.bib', 'w', encoding='utf-8') as f:
    bibtexparser.dump(bibtex_db, f)
```

Use `zot.everything(zot.top(format='bibtex', limit=100))` for a complete paginated remote export. The bibliography reflects Zotero's stored metadata; confirm DOI, author, title, and publication details before citing.

## CSL-JSON

```python
# Direct CSL export wraps the array in an 'items' member.
csl_export = zot.items(format='csljson', limit=50)
csl_items = csl_export['items']

# Or retain Zotero metadata alongside per-item CSL data
records = zot.items(format='json', include='data,csljson', limit=50)
csl_items = [record['csljson'] for record in records]
```

## Bibliography HTML and Citations

```python
# Individual references embedded in JSON (also supported by the local API)
records = zot.items(format='json', include='data,bib', style='apa', limit=50)
bib_entries = [record['bib'] for record in records]

records = zot.items(format='json', include='citation', style='apa', limit=50)
citations = [record['citation'] for record in records]
```

For one complete, style-sorted bibliography, use `format='bib'`. It has no sorting or pagination parameters and is limited to 150 matching items. In 1.15.2 its HTML response is returned as **bytes**, not a list of citation strings:

```python
html_bytes = zot.collection_items('COLKEY', format='bib', style='apa')
html = html_bytes.decode('utf-8')
```

Pass a valid style identifier from the [Zotero style repository](https://www.zotero.org/styles), such as `apa`, `vancouver`, `ieee`, or `nature`; avoid assuming a renamed style alias still exists. `linkwrap='1'` wraps bibliography URLs in links.

## RIS and Other Exports

The [API format table](https://www.zotero.org/support/dev/web_api/v3/basics#export_formats) lists `ris`, `biblatex`, `rdf_dc`, `rdf_zotero`, `wikipedia`, and others. Pyzotero 1.15.2 dispatches by response content type. A live direct `format='ris'` response used `application/x-research-info-systems`, which the SDK tried to parse as JSON and failed. Use per-item JSON `include` instead:

```python
from pathlib import Path

records = zot.everything(zot.items(format='json', include='ris', limit=50))
Path('library.ris').write_text('\n'.join(r['ris'] for r in records), encoding='utf-8')
```

JSON records work with `everything()`. Direct exports may return a dict, bytes, or a BibDatabase depending on their content type; do not pass them all through one generic writer. Direct `biblatex` uses the BibTeX parser in this release. Export formats require a limit (except `bib`).

Legacy `content='ris'`, `content='csljson'`, `content='bib'`, or `content='citation'` forces Atom and returns parsed lists in remote mode. If used, pass `content`, `style`, and `limit` on the **same** call. The local API does not support Atom. Prefer JSON `include` for per-item export data; unlike the SDK's legacy `content` parser, it supports multiple comma-separated members such as `include='data,bib'`.

## Keys and Versions

```python
# Omit the SDK limit for these formats, which the remote API does not cap.
keys_bytes = zot.items(format='keys', limit=None)
keys = keys_bytes.decode('utf-8').splitlines()

# Returns a dict, not a list; do not wrap it in everything().
versions = zot.item_versions()  # equivalent to items(format='versions', limit=None)
```

Source: [API response formats](https://www.zotero.org/support/dev/web_api/v3/basics#request_parameters), [release response dispatch](https://github.com/urschrei/pyzotero/blob/v1.15.2/src/pyzotero/_decorators.py).
