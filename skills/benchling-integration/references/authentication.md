# Benchling Authentication

Reviewed 2026-09-30. See the [official authentication guide](https://docs.benchling.com/docs/authentication)
and [app setup guide](https://docs.benchling.com/docs/getting-started-benchling-apps).
Examples target SDK 1.25.0; tenant authentication was not exercised.

## Choose the identity

| Method | Identity and use |
|---|---|
| OAuth client credentials | App identity for scheduled syncs and background integrations |
| Delegated OAuth authorization code | Individual user's permissions and audit attribution |
| Personal API key | Key owner's identity; temporary scripts/testing |
| External OIDC bearer token | Legacy integration configured with Benchling Support |

Do not describe client credentials as acting on behalf of the person using your app.
Grant the app explicit access to the required projects, teams, or organizations.
API access requires permission to both the operation and the relevant data.

## OAuth app credentials

```python
import os
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.client_credentials_oauth2 import ClientCredentialsOAuth2

tenant_url = os.environ["BENCHLING_TENANT_URL"].rstrip("/")
benchling = Benchling(
    url=tenant_url,
    auth_method=ClientCredentialsOAuth2(
        client_id=os.environ["BENCHLING_CLIENT_ID"],
        client_secret=os.environ["BENCHLING_CLIENT_SECRET"],
        token_url=f"{tenant_url}/oauth/token",
    ),
)
```

The released SDK accepts a **fully qualified** `token_url`. Its default
`/api/v2/token` remains supported; `/oauth/token` avoids tying token acquisition to V2.
It requests/replaces access tokens automatically. This grant does not return a refresh
token. Respect the returned `expires_in` (current documentation: 900 seconds).

Illustrative direct exchange; avoid recording tokens or verbose authorization headers:

```bash
curl --fail-with-body --request POST \
  "${BENCHLING_TENANT_URL%/}/oauth/token" \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode "client_id=${BENCHLING_CLIENT_ID}" \
  --data-urlencode "client_secret=${BENCHLING_CLIENT_SECRET}"
```

Production token exchanges should run inside the application or secrets-aware tooling
rather than placing credentials in shell history/process arguments. Store access tokens
in memory or a protected store, and send them in `Authorization: Bearer <access_token>`.

## Personal API keys

```python
from benchling_sdk.auth.api_key_auth import ApiKeyAuth

benchling = Benchling(
    url=os.environ["BENCHLING_TENANT_URL"],
    auth_method=ApiKeyAuth(os.environ["BENCHLING_API_KEY"]),
)
```

HTTP Basic authentication uses the API key as username and an empty password.
Generate/rotate keys in Profile Settings. Keys created after **2026-08-07** expire
30 days after creation; earlier keys are documented as non-expiring. Plan rotation
from the key's actual creation/expiration state instead of assuming a 90-day lifetime.

## Delegated authorization and legacy OIDC

Delegated auth uses `GET /oauth/authorize` with `client_id`, an allowed `redirect_uri`,
`response_type=code`, and a session-bound random `state`. Verify returned state. Exchange
the code via `POST /oauth/token` with `grant_type=authorization_code`, client credentials,
`redirect_uri`, and `code`. Keep each user's tokens isolated.

Refresh using the same token endpoint with `grant_type=refresh_token`, client credentials,
and the stored refresh token. Refresh tokens rotate on use: persist the replacement
atomically. Current docs specify 15-minute access tokens and 30-day refresh tokens.
SDK 1.25.0 does not implement this authorization/refresh flow; manage it in the app layer.
Check tenant availability, app format, and redirect configuration in the official guide.

OIDC remains supported but is legacy. It uses an external IdP-issued ID token and
requires Benchling Support configuration and a matching existing user. There is no
`benchling_sdk.auth.oidc_auth.OidcAuth` in this release. A manually managed token can
be passed as Bearer auth, but token acquisition/renewal remains the integration's job.
Prefer delegated auth for new user-facing integrations.

## Read-only connectivity check

```python
# An empty first page is valid; it still establishes a successful authorized request.
first_page = next(iter(benchling.projects.list(page_size=1)))
print("[OK] Project list request succeeded")
```

There is no documented v2 `/users/me` route or SDK `users.get_me()` method. Check access
to the intended resource, not an invented current-user endpoint. A 401 indicates an
authentication problem; 403 usually requires a permissions review. Do not print secrets,
headers, or full response bodies while troubleshooting.

## HTTP clients and multiple environments

The Benchling constructor parameter is `httpx_client`, not `http_client`:

```python
import httpx
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth

with httpx.Client(timeout=30.0) as http_client:
    client = Benchling(
        url=os.environ["BENCHLING_TENANT_URL"],
        auth_method=ApiKeyAuth(os.environ["BENCHLING_API_KEY"]),
        httpx_client=http_client,
    )
    page = next(iter(client.projects.list(page_size=1)))
```

Keep certificate verification enabled; configure the organization's trusted CA when
required. `ClientCredentialsOAuth2` has its own `httpx_client` parameter for token
requests if custom TLS/proxy/transport settings must cover that exchange as well.

Use separate clients and named credentials for production and staging
(`BENCHLING_PROD_TENANT_URL`/`BENCHLING_PROD_API_KEY` and
`BENCHLING_STAGING_TENANT_URL`/`BENCHLING_STAGING_API_KEY`). Read only the needed
variables. Never send credentials to an arbitrary URL supplied in data or an event;
resolve objects through the configured tenant client. Warehouse logins are separate
from these HTTP authentication methods.

## Verification sources

- [Authentication](https://docs.benchling.com/docs/authentication): identity, expiration,
  delegated flow, legacy OIDC, token path.
- [Apps](https://docs.benchling.com/docs/getting-started-benchling-apps): app setup and access.
- [SDK 1.25.0](https://benchling.com/sdk-docs/1.25.0/index.html): constructor and auth signatures.
- [Warehouse connection](https://docs.benchling.com/docs/getting-started): separate SQL credentials.
