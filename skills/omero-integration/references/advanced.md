# Permissions, Filesets, Web APIs, and High-Risk Operations

This reference covers features that can broaden scope, expose original data,
or mutate server state. Apply the operating contract in `SKILL.md` first.

## Group Permissions

OMERO group permissions are commonly represented as:

- private: `rw----`
- read-only: `rwr---`
- read-annotate: `rwra--`
- read-write: `rwrw--`

The string describes group policy, not a guarantee that a specific operation
is allowed. Ownership, administrator privileges, object state, and link rules
also matter.

Inspect, do not infer:

```python
image = conn.getObject("Image", image_id)
if image is None:
    raise LookupError("Image unavailable")

details = image.getDetails()
permissions = details.getPermissions()
print(
    {
        "group_id": details.getGroup().getId(),
        "owner_id": details.getOwner().getId(),
        "can_edit": permissions.canEdit(),
        "can_annotate": permissions.canAnnotate(),
        "can_link": permissions.canLink(),
        "can_delete": permissions.canDelete(),
    }
)
```

Do not print owner/group names or email addresses unless needed.

## Cross-Group and Substitute-User Operations

`conn.SERVICE_OPTS.setOmeroGroup("-1")` requests all accessible groups. It can
multiply query scope and expose data from collaborations not intended for the
current task. Require explicit cross-group approval, a total cap, and
group IDs in output.

`suConn()` and CLI `--sudo` are privileged impersonation mechanisms. Use only
for an administrator-approved task with:

- initiating administrator identity;
- target user;
- target group;
- exact operation and IDs;
- audit/logging expectations;
- immediate closure of the substitute connection.

Never create a substitute connection merely to work around a permission error.

## Filesets and Original Data

Filesets represent original imported file collections. One fileset may back
multiple images and include nested paths:

```python
fileset = image.getFileset()
if fileset is not None:
    print(fileset.getId())
```

Original-file paths and names can expose acquisition layout or identifiers.
Do not enumerate them in a general inventory.

The current CLI can download one explicit object:

```bash
omero download OriginalFile:123 ./reviewed-file
omero download FileAnnotation:456 ./reviewed-file
omero download Image:789 ./reviewed-empty-directory
omero download Fileset:321 ./reviewed-empty-directory
```

`Image` and `Fileset` may expand to multiple files. First inspect count/size,
then use a dedicated destination with collision/symlink checks. Authenticate
through a prompted stored session; do not add password or key flags.

Direct `RawFileStore` usage must be bounded and closed:

```python
max_bytes = 50 * 1024 * 1024
store = conn.createRawFileStore()
try:
    store.setFileId(original_file_id)
    size = store.size()
    if size > max_bytes:
        raise ValueError("OriginalFile exceeds approved byte limit")
    chunk = store.read(0, min(size, 1024 * 1024))
finally:
    store.close()
```

This sample intentionally reads at most one chunk. A full download needs a
loop with cumulative byte checks and a caller-selected safe path.

## Destructive Commands

`conn.deleteObjects(type, ids, wait=True)` submits an OMERO command. The exact
impact depends on object type, links, ownership, and server graph rules. Do not
promise a cascade/orphan result from intuition.

Required delete workflow:

1. Resolve explicit object type and IDs in one group.
2. Read current object/link summaries and permissions.
3. Show counts and likely related objects from documented queries.
4. Obtain explicit approval for those exact IDs.
5. Submit with `wait=True` or monitor the returned command callback.
6. Inspect command response for errors.
7. Record success/failure per ID.
8. Close callbacks/handles and the gateway.

Never select delete targets by a broad name/namespace query without an ID
review. Never add delete mode to inventory/export scripts.

Unlinking an annotation, table, image, or dataset is a different graph change
from deleting the child. State which one is intended.

## Ownership and Group Changes

Changing ownership or moving data between groups can alter access for many
linked objects. Current CLI documentation says ownership changes require full
admin, an appropriately privileged restricted admin, or group owner.

Before:

- enumerate exact root objects and affected links;
- confirm source and destination groups;
- confirm target owner membership;
- check whether filesets/annotations/tables move with the object graph;
- obtain administrator approval;
- use current documented CLI/API methods, not direct `_obj.details.owner`
  manipulation copied from old examples.

Do not write private model fields to bypass service-level policy.

## HQL and Query Service

Use fixed HQL and typed parameters:

```python
import omero.sys

parameters = omero.sys.ParametersI()
parameters.addLong("image_id", image_id)

query = "select i from Image i where i.id = :image_id"
model_image = conn.getQueryService().findByQuery(query, parameters)
```

Never interpolate names, namespaces, IDs, ordering, or arbitrary user text
into HQL. Map user choices to allowlisted fixed query templates. Apply a
server-side result limit to list queries.

## Deprecated Service Surface

The current generated API marks at least these interfaces deprecated:

- `IRoi`
- `IShare`

`IRoi.findByImage` remains in current official Python examples, but should be
isolated and version-checked. Do not build new sharing workflows on
`IShare`; use current administrator-supported OMERO.web/public-data features
instead.

Deprecation does not mean immediate removal. It means callers must not claim
long-term stability or invent a replacement.

## OMERO.web: What Is Publicly Supported

Official OMERO.web developer documentation says only these included apps are
stable public APIs:

- `api`
- `webgateway`

Other apps, including `webclient`, expose internal URLs and methods that may
change in minor releases. A URL currently used by the UI is not automatically
a supported integration endpoint.

### JSON API

The documented OMERO JSON API:

- is implemented by the `api` Django app;
- advertises supported major versions at `GET /api/`;
- advertises starting URLs at `GET /api/v0/`;
- reports the full API version in `X-OMERO-ApiVersion`;
- uses `limit` and `offset` pagination;
- reports `totalCount`, `limit`, `offset`, and server `maxLimit`;
- requires a CSRF token for POST/PUT/DELETE;
- documents login at `/api/v0/login/`;
- supports read endpoints for documented model types, including ROI listing;
- currently limits object creation/update to Projects, Datasets, and Screens.

Official docs describe create/read/update/delete access but also explicitly
limit type coverage. Do not call it a complete generic REST interface, assume
OAuth, assume token authentication, or infer endpoints not listed by the
server's discovery response.

Use HTTPS. A JSON API password is sent in the documented login POST and must
never be logged. Honor the returned `maxLimit`; apply a smaller client cap.

### WebGateway

`webgateway` provides documented rendered images and JSON data. Confirm the
current endpoint page before implementing, cap image size/quality, and use
HTTPS. Do not substitute a webclient AJAX route.

## Public Data and Links

Publishing is an administrator configuration, not a client-side “make public”
API call. Current official guidance:

- create a dedicated read-only group;
- create/add a public user with only intended data access;
- `omero.web.public.enabled` defaults to false;
- public users default to GET-only;
- `omero.web.public.url_filter` must explicitly allow routes and otherwise
  matches nothing;
- download/export routes can be excluded;
- a dedicated public OMERO.web deployment may be appropriate.

OME shows examples such as `webclient/?show=project-...` for publication
navigation, but the webclient itself is explicitly not a stable public API.
Do not promise that such links are permanent integration contracts. For
durable publication URLs, use administrator-owned redirects/DOIs and test them
after upgrades.

Never generate a public link merely because an object is readable to the
current authenticated user. Confirm:

- the public user is enabled;
- its group membership permits the object;
- GET-only remains enabled;
- URL filter permits only intended routes;
- download/export routes are intentionally allowed or blocked;
- the institution approves public release.

## OMERO CLI Import/Admin Boundary

Installing `omero-py` provides the CLI framework, but import/admin commands
also depend on a compatible extracted OMERO.server tree through `OMERODIR`.
Do not point `OMERODIR` at an arbitrary or mismatched server distribution.

Remote client commands and local server administration have different risk.
Before any admin command, confirm it is being run on the intended host with the
intended server installation/configuration.

## Advanced Operation Checklist

- Current server/client/API docs verified
- Exact user, group, object type, and IDs
- Cross-group/impersonation separately authorized
- Permission checks do not replace authorization
- Original-file count/bytes and destination reviewed
- Fixed queries with typed parameters
- Deprecated services isolated and documented
- Only `api`/`webgateway` treated as stable OMERO.web APIs
- Public access configured by administrators, not inferred
- Destructive commands previewed, confirmed, monitored, and recorded
- Every stateful service/callback/connection closed
