# Paperzilla CLI contracts

Reviewed 2026-10-01 against `pz` **v0.7.1**, commit
`798a8c12c8aa8e18a8fbede4a2bfaaea2950ea5c`. These are the routes used by that
release, not a promise of a stable public REST SDK. Prefer the CLI for this skill;
the public API reference documents feed and MCP integration surfaces.

## Authentication and transport

`pz login` sends `POST /api/auth/otp` with JSON `email`, then
`POST /api/auth/verify` with `email` and `code`. Verification returns
`access_token`, `refresh_token`, and `expires_in`. Refresh uses
`POST /api/auth/refresh` with both existing tokens in the JSON body. Those three
requests do not use a bearer header. The session is stored in
`~/.paperzilla/tokens.json` unless `PZ_TOKENS_PATH` is set.

All data commands in v0.7.1 first load a session and call
`GET /api/auth/cli-access` with `Authorization: Bearer ...`; success requires
`allowed: true`. Commands also send `X-Paperzilla-Client: cli` and a versioned
`User-Agent`. Project, recommendation, feedback, and feed-token requests use
bearer authentication. Canonical public-paper requests omit the bearer header
**after** this authenticated preflight. The current guide's claim that
`pz paper` works without login conflicts with both this release's source and
local binary behavior. Treat login as required for the reviewed CLI.

The default base URL is `https://paperzilla.ai`. `PZ_API_URL` replaces it; do not
send account tokens to an arbitrary replacement host. Missing/expired sessions
can cause interactive login and contaminate stdout, including `--json` exports.
`CLI_UPGRADE_REQUIRED` and `CLI_ENTITLEMENT_UNAVAILABLE` describe access failures,
not zero search results. The CLI can retry a request after a 401 and token
refresh; other service failures are returned to the caller.

## Command-to-request mapping

Paths are relative to the configured base URL. Braced identifiers come from
returned records, never inferred from DOI or title.

| CLI operation | Request | Result or side effect |
| --- | --- | --- |
| `project list` | `GET /api/projects` | API project array; CLI `--json` emits only `id`, `name`, `mode`, `visibility`. No pagination flags in this release. |
| `project {project}` | `GET /api/projects/{project}` | Project record, including keyword/source/category arrays. |
| `feed {project}` | `GET /api/projects/{project}/feed` | `items`, `total`, `limit`, `offset`; query keys `must_read`, `since`, `limit`, `offset`. |
| `feed search --project-id {project}` | `GET /api/projects/{project}/feed/search` | Query `q`, `feedback_filter`, optional `must_read`, `limit`, `offset`; response `items`, `limit`, `offset`, `has_more`, `query`. |
| `paper {paper}` | `GET /api/public/papers/{paper}` | Canonical paper object. |
| `paper {paper} --markdown` | `GET /api/public/papers/{paper}/markdown` | Markdown text when available; `markdown_not_ready` means nothing was queued through this public route. |
| `paper {paper} --project {project}` | `GET /api/projects/{project}/papers/{paper}` | Project recommendation object containing its canonical `paper`. With `--markdown`, subsequently uses the recommendation markdown route. |
| `rec {recommendation}` | `GET /api/project-papers/{recommendation}` | Recommendation object containing canonical `paper`. |
| `rec {recommendation} --markdown` | `GET /api/project-papers/{recommendation}/markdown` | Text or a pending-generation response; this GET can queue generation. |
| `feedback {recommendation} {vote}` | `PUT /api/project-papers/{recommendation}/feedback` | JSON body `vote` and optional `downvote_reason`; returns `vote`, `downvote_reason`, `updated_at`. |
| `feedback clear {recommendation}` | `DELETE /api/project-papers/{recommendation}/feedback` | Backend 204; CLI `--json` supplies a `project_paper_ref`/`cleared` envelope. |
| `feed {project} --atom` | `POST /api/auth/feed-token` | Gets or creates a personal token; CLI constructs `/api/feed/atom/{project}?token=...`, without fetching its XML. |

For compatibility, canonical-paper 404s may cause v0.7.1 to try authenticated
`GET /api/papers/{ref}` or `/api/papers/{ref}/markdown`. A successful fallback
prints a deprecation warning for a recommendation ID. Do not build a new workflow
around these legacy routes; use `rec` with the returned recommendation ID.

## Pagination, identifiers, and output

- Browse accepts zero-based `offset`; positive `limit` is sent to the API, with
  no verified server maximum in the inspected CLI source. Use a modest page size
  and honor the returned values. `since` means recommendation readiness time.
- Search validates explicit `limit` in 1–100, nonnegative `offset`, and trimmed
  query length in 3–200. The Go implementation counts UTF-8 bytes, so multibyte
  queries may reach its limit before 200 visible characters. `has_more`, not a
  total or the text display's count, determines whether more results exist.
- Neither command automatically consumes all pages. Keep a finite page/request
  budget and stop on an empty/nonadvancing page; record a partial export if the
  budget is reached. A changing feed can shift offset-based pages.
- Recommendation `id`/`short_id` differ from nested canonical
  `paper.id`/`paper.short_id`. `paper --project --json` returns a recommendation,
  unlike canonical `paper --json`.
- `--markdown` is mutually exclusive with `--json` for `paper` and `rec`.
  `markdown_queued`/`markdown_already_queued` are rendered as friendly messages
  with successful exit status. Exit code zero alone does not prove full-text
  retrieval. Do not derive scientific claims from those status messages.
- The API documents nullable `pdf_url`; the CLI decodes string fields into Go
  strings, so a missing/null URL can appear as an empty string in CLI JSON.
- Atom output contains a credential, not an ordinary public paper link. Browse
  flags do not constrain this URL. Obtain it only for the requested feed-reader
  workflow, and do not publish it with citations.

## Verification and sources

The official darwin-arm64 v0.7.1 binary was downloaded and checked against its
release SHA-256 list. Version/help and 25 local mock-server cases exercised
project, browse/search, canonical/project-paper, markdown-ready/pending,
feedback/clear, Atom construction, input validation, OTP, refresh, and the
canonical auth preflight. The mock server held only synthetic data and tokens.
No live account login, email, generation job, feedback, or feed-token creation
was performed. Live service authorization, entitlements, and returned scientific
records remain untested. Install/build/update instructions were checked against
official documentation; only the release binary was executed.

- [CLI guide](https://docs.paperzilla.ai/guides/cli)
- [Quickstart](https://docs.paperzilla.ai/guides/cli-getting-started)
- [Public integration scope](https://docs.paperzilla.ai/api-reference/introduction)
- [Atom route and credential semantics](https://docs.paperzilla.ai/api-reference/rss-atom-feed)
- [v0.7.1 release](https://github.com/paperzilla-ai/pz/releases/tag/v0.7.1)
- [CLI command source](https://github.com/paperzilla-ai/pz/tree/v0.7.1/cmd)
- [HTTP client, auth, endpoints and schemas](https://github.com/paperzilla-ai/pz/tree/v0.7.1/internal/api)
- [Session storage](https://github.com/paperzilla-ai/pz/blob/v0.7.1/internal/config/tokens.go)
