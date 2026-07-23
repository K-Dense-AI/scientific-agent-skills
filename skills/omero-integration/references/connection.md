# Connection, Sessions, and Transport Security

This reference is current for the skill snapshot dated 2026-07-23. It uses
`omero-py==5.22.1` and the OMERO.server 5.6.18 documentation.

## Compatibility Before Credentials

OMERO.server and its Python, web, Java, Bio-Formats, and Ice components have
independent release numbers. Do not compare their version strings as if they
were one package.

For the current stable pairing:

- OMERO.server 5.6.18 was tested with OMERO.py 5.22.1 and OMERO.web 5.31.0.
- `omero-py==5.22.1` declares Python `>=3.10`.
- The OMERO matrix supports Python 3.10/3.11 and recommends 3.12.
- Python 3.13/3.14 are listed as upcoming, not supported.
- Ice 3.6 is recommended; Ice 3.7 is unsupported.
- The OMERO-linked Glencoe wheel matrix provides IcePy 3.6.5 wheels through
  Python 3.12 for documented platforms.

For a different server release, read that release's history entry and use its
tested OMERO.py version. A newest-client/old-server pairing may appear to work
but is not the documented compatibility guarantee.

## Installation

Use an isolated Python 3.12 environment and a platform-matched Ice wheel:

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate

# Obtain the matching wheel from the OMERO-linked Ice binary matrix.
uv pip install "/absolute/path/to/zeroc_ice-3.6.5-<matching-tags>.whl"
uv pip install "omero-py==5.22.1"
```

Wheel tags must match all of:

- CPython version (`cp310`, `cp311`, or `cp312`)
- operating system
- architecture
- platform compatibility tags

Do not silently fall back to compiling IcePy if the wheel is rejected. Inspect
the interpreter and platform first. Do not install Ice 3.7 as a substitute.

`OMERODIR` is required for some CLI configuration and must point to a
compatible extracted OMERO.server tree to enable import and admin commands.
It is not required merely to use BlitzGateway against a remote server.

## Named Configuration

The bundled helpers read exactly these variables:

- `OMERO_HOST`: required hostname, without `http://`, `https://`, or path
- `OMERO_PORT`: optional integer, default `4064`
- `OMERO_USER`: username for password authentication
- `OMERO_PASSWORD`: password for password authentication
- `OMERO_SESSION_KEY`: existing session key, alternative to user/password
- `OMERO_SECURE`: boolean, default `true`

Rules:

1. Never crawl for `.env` files or read unrelated environment variables.
2. Never accept a password/session key as a command argument.
3. Never print an environment dump, password, or session key.
4. Treat a session key as a bearer credential and expire/logout when finished.
5. Prefer a secret manager or process-scoped environment over shell history.

## Password Connection

Use `try/finally` when connection success must be checked explicitly:

```python
import os
from omero.gateway import BlitzGateway

conn = BlitzGateway(
    os.environ["OMERO_USER"],
    os.environ["OMERO_PASSWORD"],
    host=os.environ["OMERO_HOST"],
    port=int(os.environ.get("OMERO_PORT", "4064")),
    secure=True,
)

try:
    if not conn.connect():
        raise RuntimeError("OMERO connection failed")

    # Keep reads bounded and group-scoped.
    for image in conn.getObjects(
        "Image",
        opts={"limit": 25, "offset": 0, "order_by": "obj.id"},
    ):
        print(image.getId())
finally:
    conn.close()
```

BlitzGateway can also be a context manager. Its context manager calls
`connect()` and closes the underlying client:

```python
import os
from omero.gateway import BlitzGateway

with BlitzGateway(
    os.environ["OMERO_USER"],
    os.environ["OMERO_PASSWORD"],
    host=os.environ["OMERO_HOST"],
    port=int(os.environ.get("OMERO_PORT", "4064")),
    secure=True,
) as conn:
    for project in conn.getObjects(
        "Project",
        opts={"limit": 10, "offset": 0, "order_by": "obj.id"},
    ):
        print(project.getId())
```

Do not catch an exception merely to print its full representation: connection
errors may include endpoint or identity details. Report the exception class
and a scrubbed message; never include credential values.

## Existing Session

`BlitzGateway.connect()` accepts `sUuid`, the existing session UUID:

```python
import os
from omero.gateway import BlitzGateway

conn = BlitzGateway(
    host=os.environ["OMERO_HOST"],
    port=int(os.environ.get("OMERO_PORT", "4064")),
    secure=True,
)

try:
    if not conn.connect(sUuid=os.environ["OMERO_SESSION_KEY"]):
        raise RuntimeError("Could not join the OMERO session")
    print(conn.getEventContext().groupId)
finally:
    conn.close()
```

Joining a session does not make it safe to log the key. If a low-level
`omero.client` is supplied through `BlitzGateway(client_obj=client)`, the
gateway does not necessarily own every other use of that client. Close it only
when ownership is clear; the official context-manager example is appropriate
when nothing else uses the client.

## CLI Login Without a Password Argument

The CLI stores sessions locally. Let it prompt:

```bash
omero login -s "$OMERO_HOST" -p "$OMERO_PORT" -u "$OMERO_USER"
omero sessions list
omero sessions file
omero logout
```

Do not use `-w` or `--password`. Although the CLI supports
`OMERO_PASSWORD`, avoid putting the secret in a persistent shell profile.

The CLI also supports joining a session with `-k`, but entering a session key
on the command line exposes it in shell history and process listings. Prefer a
short-lived, protected workflow and never paste the key into logs.

By default, session files are under `~/omero/sessions`. `OMERO_USERDIR` or
`OMERO_SESSIONDIR` can change the location. Protect any custom directory with
user-only permissions and remove stale sessions with `omero logout`.

## Group Context

The default connection group comes from the session event context:

```python
ctx = conn.getEventContext()
print(ctx.groupId)  # Avoid printing the session ID.
```

Set one explicit accessible group before scoped queries:

```python
group_id = 42
conn.SERVICE_OPTS.setOmeroGroup(str(group_id))
```

`-1` requests cross-group behavior. It is not a harmless convenience:

```python
# Only after the user explicitly requests all accessible groups:
conn.SERVICE_OPTS.setOmeroGroup("-1")
```

Do not set `-1` by default, and do not combine it with an unbounded query.
Record the original group if temporarily changing context and restore it
before subsequent writes.

The CLI can switch its current session group:

```bash
omero group list
omero sessions group 42
```

Confirm the target group before import, link creation, table writes, ownership
changes, or script execution.

## What `secure=True` Does

Official OMERO security documentation distinguishes authentication from later
traffic:

- Login and password changes use SSL by default.
- After login, other traffic is unencrypted by default for performance.
- In that mode, the session ID is the critical value sent in clear text.
- `BlitzGateway(..., secure=True)` requests encryption for all transfers.
- Servers can redirect/disable insecure connections.
- Default router ports are 4063 (insecure) and 4064 (SSL), but admins may
  change or prefix them.
- OMERO.web HTTPS normally uses port 443 and is a separate transport path.

Therefore, default to `secure=True` and the administrator-provided SSL router
port. Do not infer security merely from the number `4064`.

## Certificate and Host Verification

Encryption is not the same as server identity verification. OME explicitly
states that standard OMERO clients do not automatically verify the host, so a
man-in-the-middle attack remains possible without additional configuration.

The official developer guidance lists these Ice properties for certificate
validation:

- `IceSSL.Ciphers=HIGH` (or a supported explicit cipher family)
- `IceSSL.VerifyPeer=1`
- `IceSSL.VerifyDepthMax=0`
- `IceSSL.UsePlatformCAs=1`, or `IceSSL.CAs=/path/to/cacert.pem`
- `IceSSL.CheckCertName=1` for exact hostname checking
- `IceSSL.TrustOnly=...` for documented alternative name restrictions
- optionally `IceSSL.Protocols=tls1_2` if required by server policy

These are site-specific low-level client settings. Do not invent them from a
hostname or disable verification to make a connection succeed. Ask the OMERO
administrator for the CA, expected certificate name, router port, and policy.
The bundled helpers enforce encrypted transport by default but do not claim to
configure hostname verification.

For OMERO.web, use an administrator-managed HTTPS deployment with a recognized
certificate. Never send JSON API credentials over plain HTTP.

## Stateful Services and Reconnection

BlitzGateway reuses stateless `get...Service()` proxies. Stateful services such
as rendering engines, raw stores, thumbnail stores, tables, and other
`create...` services should be created, used, and closed in the shortest
practicable scope.

Gateway recovery may recreate its own services after a connection failure.
Client-held stateful proxies can then be stale. Do not retain them across long
idle periods or reconnects.

Generic pattern:

```python
store = conn.createRawFileStore()
try:
    store.setFileId(original_file_id)
    # Perform one explicitly bounded read.
finally:
    store.close()
```

Closing the gateway is still mandatory even if every stateful child was closed.

## Connection Failure Checklist

Without exposing credentials:

1. Validate `OMERO_HOST` has no URL scheme/path and `OMERO_PORT` is in range.
2. Confirm the server release and tested OMERO.py pairing.
3. Confirm Python and Ice wheel tags match.
4. Confirm the SSL router port and `secure=True`.
5. Confirm the account is active and has access to the selected group.
6. For an existing session, confirm it is still valid without printing it.
7. For certificate verification, confirm CA and expected certificate name.
8. Close the failed connection before retrying.
9. Do not retry authentication in a tight loop; server throttling may apply.
