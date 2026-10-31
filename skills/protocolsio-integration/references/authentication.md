# Authentication and Credential Safety

Verified **2026-09-30** against the official
[Developer resources](https://www.protocols.io/developers) page and
[API authentication reference](https://apidoc.protocols.io/).

## Access Model

The official documentation names two bearer-token modes:

| Mode | Officially documented use | Safe default |
|---|---|---|
| Client access token | The Developer resources page says it can read all public data. The API authentication section additionally says it can access the creating user's private content. | Treat it as public-read unless the exact account/endpoint behavior and permissions have been verified. |
| OAuth access token | Public content plus the authorizing user's permitted private content. | Use only for a multi-user application or a user-approved private/write workflow. |

The two official descriptions of client-token private access are not perfectly
aligned. Do not use that ambiguity as authorization. Check the returned access
flags and the user's intended scope before touching private content.

“Public protocol” describes the resource's visibility; it does not imply that a
REST call is anonymous. The current list/get endpoint sections require
`Authorization: Bearer ...`. The official PDF section documents signed-in and
signed-out rates, so the bundled client allows anonymous access only when
`export-pdf --anonymous` is explicit.

## Named Variables

The bundled scripts read only `PROTOCOLS_IO_ACCESS_TOKEN`, the bearer token
used by the read helper. They do not read OAuth client credentials or refresh
tokens. A separately reviewed confidential application should keep those
credentials in its own secret-manager scope and perform OAuth exchange there.

Never:

- put any value in source, JSON payloads, command arguments, shell history,
  notebooks, chat, screenshots, logs, exception text, or output;
- enumerate unrelated environment variables;
- load or search for `.env` files;
- print a value, prefix, suffix, length, hash, or decoded form;
- send a protocols.io bearer token to an attachment URL, S3 URL, redirect, or
  any host other than the explicitly validated protocols.io API origin.

Configure secrets through the execution host's credential manager. Validate
presence locally:

```bash
python3 -B scripts/validate_auth_config.py --require read
```

The validator reads only the named access token, reports a boolean, performs
no network access, and never loads `.env`.

## OAuth 2.0 Contract

The current official flow documents:

1. Create/configure the client on
   `https://www.protocols.io/developers`.
2. Register the exact redirect URL there.
3. Direct the user to
   `https://www.protocols.io/api/v3/oauth/authorize`.
4. Send `client_id`, `redirect_url`, `response_type=code`,
   `scope=readwrite`, and a high-entropy, single-use `state`.
5. Verify returned `state` before accepting the authorization `code`.
6. Exchange the code server-side at
   `POST https://www.protocols.io/api/v3/oauth/token` using
   `grant_type=authorization_code`, `client_id`, `client_secret`, and `code`.
7. Refresh at the same endpoint with `grant_type=refresh_token`,
   `client_id`, `client_secret`, and `refresh_token`.

Use the documented parameter name `redirect_url`; do not silently substitute
`redirect_uri`. The token response documents `access_token`, `token_type`,
`expires_in`, `scope`, `refresh_token`, `refresh_expires_in`, and `user`.

The reference's example scope is `readwrite`. No finer REST scope list was
found in the official materials reviewed. Therefore:

- use a client token for public-only discovery;
- do not initiate OAuth merely because an access token is absent;
- use `readwrite` only for an authorized user-context workflow requiring OAuth;
  private read workflows still receive this broad documented scope;
- enforce narrower authorization in the application even if the upstream
  token is broad;
- recheck the live developer page before production authorization, because
  scope support can change.

Do not perform OAuth token exchange in a browser-only client or general agent
transcript. Keep the client secret and token endpoint in a confidential
server-side component with redacted observability.

## Lifetime and Refresh

The official authentication page says an OAuth access token resets after about
one year, returns an `expires_in` value, and warns one month before expiry with
`warning_code: 1`. It documents API `status_code: 1219` and “token is expired”
after expiry. Treat the response fields—not a hardcoded calendar interval—as
authoritative.

On refresh, the documentation says old tokens stop working. Store the newly
returned access and refresh credentials atomically, then revoke or discard the
old pair. Never log the response body.

## Header Handling

Endpoint examples use the standard `Authorization: Bearer ...` header. The
authentication introduction contains a label typo (“Authentication”), so use
the endpoint contract and standard header name.

Build the header only inside the HTTP transport immediately before a validated
request. Redact it from plans, tracing, error reports, and mocks. Disable
redirects; do not assume a same-site redirect is safe for a bearer credential.

## Least-Privilege Checklist

Before any authenticated operation:

1. identify whether the resource is public, private, shared, or tenant-scoped;
2. choose client access for public reads and OAuth only when user context is
   necessary;
3. verify owner/workspace access flags returned by the API;
4. restrict protocol IDs, workspace URI, tenant origin, page/item count, and
   response bytes;
5. separate read credentials from any service capable of writes;
6. require a current snapshot and fresh confirmation for every mutation;
7. rotate credentials after suspected disclosure and remove exposed logs.

## Source Notes

- [Developer resources](https://www.protocols.io/developers), accessed
  2026-09-30 — REST API link, client access, credential creation, OAuth setup.
- [API authentication and OAuth reference](https://apidoc.protocols.io/),
  accessed 2026-09-30 — token modes, `readwrite`, authorize/token paths,
  response fields, lifetime/refresh behavior.
- [Official MCP server](https://www.protocols.io/mcp-server),
  accessed 2026-09-30 through rendered extraction — endpoint/auth, public
  read tools, temporary Claude Connector unavailability. Its public-content
  tool descriptions are narrower than the API page's OAuth access statement;
  verify actual tool permissions before relying on private MCP reads.
