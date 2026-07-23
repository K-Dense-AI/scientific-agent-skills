# Authentication and Context

## Principles

DNAnexus bearer tokens impersonate the user who created them. They inherit that
user's project access and can launch billable jobs. Treat
`DX_SECURITY_CONTEXT` as a secret:

- Never print, log, serialize, return, or commit it.
- Never place a token directly in source code, notebooks, input JSON, job
  properties, tags, or command output.
- Never read or export the entire environment to locate the token.
- Use only the named DNAnexus credential supplied by the user or secret
  manager.
- Do not send it to any non-DNAnexus endpoint.

`dx env` and `dx env --bash` display the active token. Do not run either command
in captured terminals, CI logs, support bundles, or agent output.

## Interactive Login

Install `dxpy`, then authenticate:

```bash
dx login
dx whoami
dx select
dx pwd
```

`dx login` stores CLI state under `~/.dnanexus_config/`. Use `dx whoami` and
`dx pwd` to verify identity and project without exposing the token.

For SSO accounts, create an API token in **My Profile → API Tokens** if required
by the organization. Keep the login prompt interactive; avoid putting token
values in shell history or transcripts.

## Token Login and Automation

The CLI supports `dx login --token TOKEN`, but placing the literal token on a
command line can expose it through shell history or process inspection.
Preferred automation:

1. Create a short-lived token in the DNAnexus UI.
2. Use a dedicated user/service identity with only the required project access.
3. Store the complete security context in the CI or orchestration secret
   manager under the exact key `DX_SECURITY_CONTEXT`.
4. Inject that single key directly into the process environment.
5. Mask the key in logs and never enable shell tracing around authentication.
6. Verify with `dx whoami`; do not use `dx env`.
7. Remove the secret from the process environment when the operation ends.

Standard user API tokens inherit the creating user's project access; they are
not independently project-scoped. Minimize the dedicated identity's project
memberships and access levels before issuing its token. If an organization
provides a more restricted credential mechanism, prefer the narrowest
available scope.

Tokens created without an explicit expiration expire after one month according
to current platform guidance. Choose a shorter expiration whenever practical.

### Tool-specific variable names

- `dx` and `dxpy` primarily consume the JSON `DX_SECURITY_CONTEXT`.
- The dx-toolkit shell bootstrap maps `DX_AUTH_TOKEN` into
  `DX_SECURITY_CONTEXT` only when `DX_SECURITY_CONTEXT` is absent.
- Download Agent (`dx-download-agent`) checks `DX_API_TOKEN`; when absent, it
  falls back to `~/.dnanexus_config/environment.json`.

These names are all sensitive but are not generic substitutes in every tool.
Inject only the variable required by the selected client, and never mirror one
secret into multiple variables without a concrete compatibility need.

## Configuration Precedence

DNAnexus utilities resolve configuration in this order:

1. Command-line overrides
2. Environment variables already set in the shell
3. `~/.dnanexus_config/environment.json`
4. Built-in defaults

This means a stale `DX_SECURITY_CONTEXT` in the shell overrides a later
interactive `dx login`. A login can appear successful while subsequent
commands still use the older shell credential.

### Diagnose a context mismatch safely

Use only non-secret commands:

```bash
dx whoami
dx pwd
```

If the shell environment should be discarded in favor of the saved CLI state:

```bash
source "$HOME/.dnanexus_config/unsetenv"
dx whoami
dx pwd
```

If the saved CLI state should be discarded instead:

```bash
dx clearenv
```

Do not print either source to compare token values.

## Project Context

Select a project interactively:

```bash
dx select
dx pwd
```

For scripts, prefer explicit project IDs and full paths instead of relying on
ambient context:

```bash
dx ls "project-xxxx:/input"
dx download "project-xxxx:/input/sample.bam" --output "sample.bam"
```

In Python, pass `project="project-xxxx"` to searches, uploads, downloads when
needed for billing context, and executable runs. Explicit context prevents a
script from silently operating on the project selected in another terminal.

## Execution-Environment Credentials

Jobs receive a job-scoped security context from the platform. `dxpy` and `dx`
consume it automatically. App code normally should not parse
`DX_SECURITY_CONTEXT`.

Within an Application Execution Environment:

- Use the system-provided API host and security context unchanged.
- Do not forward the job environment to child processes that do not require it.
- If a subprocess needs only local computation, pass a minimal allowlisted
  environment.
- Never upload environment dumps, crash reports containing environment values,
  or shell traces.
- Do not override the internal API host with a user-controlled hostname.

Job authorization is inherited from the root execution and can expire. Current
documentation limits job authentication tokens to 30 days, which aligns with
the normal maximum job runtime.

## Endpoint Safety

For normal external clients, DNAnexus uses official hosts such as:

- `api.dnanexus.com` for API calls
- `auth.dnanexus.com` for authentication
- `platform.dnanexus.com` for the web interface

Inside jobs, the platform may supply a private API address. Accept only the
system-provided value. Do not build code that combines the token with an
arbitrary URL.

Custom API server overrides are advanced administrative features. Use them only
when the user identifies an approved DNAnexus deployment and explicitly asks
for the override.

## Rotation, Logout, and Revocation

`dx logout` ends the CLI session. If the session used an API token, current
documentation states that logout invalidates that token.

Revoke a token when:

- It may have been exposed.
- Its user or automation no longer needs access.
- The associated script or service has been retired.
- The underlying account permissions changed materially.

Revocation is disruptive: running jobs and active uploads/downloads
authenticated by the token terminate immediately with `AuthError`; charges
already incurred remain billable. Confirm affected executions and transfers
before revoking unless emergency containment is required.

After suspected compromise:

1. Stop exposing the credential.
2. Identify active executions and transfers without printing the token.
3. Rotate or revoke the token.
4. Review project membership and recent executions.
5. Reissue only a short-lived replacement.

## Authentication Failure Checklist

For `AuthError`, `PermissionDenied`, or unexpected project visibility:

1. Run `dx whoami`.
2. Run `dx pwd`.
3. Check whether a shell environment overrides saved CLI state.
4. Confirm the object exists in the stated project and region.
5. Confirm the account has the needed project level:
   - `VIEW` to read
   - `UPLOAD` to add data
   - `CONTRIBUTE` to run and modify project content
   - `ADMINISTER` for membership and administrative operations
6. Check token expiration or revocation.
7. Check organization/TRE policies and download restrictions.
8. Reauthenticate only after preserving evidence needed to understand affected
   jobs or transfers.

Do not respond to authentication failures by broadening permissions
automatically.
