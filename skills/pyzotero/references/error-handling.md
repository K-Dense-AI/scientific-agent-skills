# Error Handling

Pyzotero 1.15.2 exports exceptions from `pyzotero.errors` (also from `pyzotero`). Use the current `Error` suffixes; old names such as `ResourceNotFound` do not exist.

| Exception | Meaning |
|-----------|---------|
| `PyZoteroError` | Base class for SDK errors |
| `UserNotAuthorisedError` | 401/403, invalid key or insufficient permissions |
| `HTTPError` | Other mapped HTTP error |
| `ParamNotPassedError` | Missing method argument/data |
| `CallDoesNotExistError` | Unsupported method for this library/mode |
| `ResourceNotFoundError` | 404, missing resource or missing full-text content |
| `ConflictError` | 409, target library locked |
| `PreConditionFailedError` | 412, stale version or reused write token |
| `TooManyItemsError` | SDK batch-size check, normally over 50 |
| `InvalidItemFieldsError` | Unknown field names |
| `TooManyRetriesError` | SDK retries exhausted |
| `LocalAPIKeyRequiredError` | Local write needs a valid local key |
| `LocalAPIDeniedError` | User declined local authorization |
| `ServerIDMismatchError` | Local database differs from cached server ID |
| `ServerIDRequiredError` | Local write missing server-ID precondition |

## Read Errors

```python
import httpx2
from pyzotero.errors import ResourceNotFoundError, UserNotAuthorisedError

try:
    item = zot.item('ITEMKEY')
except ResourceNotFoundError:
    print('Item not found')
except UserNotAuthorisedError:
    print('Check the key and library permissions')
except httpx2.TransportError:
    print('Network request failed; retry the read when connectivity returns')
```

Many mapped errors retain the HTTP exception in `__cause__`. Inspect response status and headers when needed, but redact credentials before logging request URLs or full exception bodies (`key_info()` embeds the key in its path).

## Version Conflicts

```python
from pyzotero.errors import PreConditionFailedError, ServerIDMismatchError

try:
    zot.update_item(item)
except ServerIDMismatchError:
    # Subclass of PreConditionFailedError: handle it first.
    raise RuntimeError('Local Zotero database changed; discard cached objects and versions')
except PreConditionFailedError:
    fresh_item = zot.item(item['key'])
    # Compare the original, intended, and fresh values before merging.
    # Do not automatically overwrite a concurrent edit with new_title.
    raise RuntimeError('Concurrent edit detected; reconcile before another write')
```

## Invalid Fields

```python
from pyzotero.errors import InvalidItemFieldsError

template = zot.item_template('journalArticle')  # remote API only
template['badField'] = 'bad value'
try:
    zot.check_items([template])
except InvalidItemFieldsError:
    print('Remove unknown fields before creating the item')
```

This validation does not replace checking `failed` in batch write JSON. HTTP 200 and `update_items()` returning `True` do not establish that every object was updated.

## Rate Limits and Retry Boundaries

Honor `Backoff` even on successful responses, and `Retry-After` on 429/503. Pyzotero's read and decorated Boolean-write paths record server delays and retry 429 responses, eventually raising `TooManyRetriesError`. Some other paths, including `create_items()`, `saved_search()`, and `new_fulltext()`, do not run that retry loop in 1.15.2: inspect the returned response/`zot.request` where applicable, and do not interpret an error payload as a valid result.

Do not wrap all calls in a short fixed exponential retry: it can violate server delays or repeat writes whose outcome is unknown. Reconcile timeouts before replaying creates/uploads, and retry only known failures. `TooManyRequestsError` exists but is not the ordinary terminal error from the SDK's 429 retry loop. Do not retry local authorization dialogs automatically.

Sources: [Zotero backoff rules](https://www.zotero.org/support/dev/web_api/v3/basics#rate_limiting), [Pyzotero error implementation](https://github.com/urschrei/pyzotero/blob/v1.15.2/src/pyzotero/errors.py).
