# pi-web-access Package

Sources: [official package](https://www.npmjs.com/package/pi-web-access/v/0.35.0), [maintainer documentation](https://github.com/nicobailon/pi-web-access).

Reviewed the published 0.35.0 source and README with Pi 0.99.2 on 2026-09-30. Install with `pi install npm:pi-web-access`. External searches, authenticated extraction, model summaries, and video/cloud PDF conversion below are illustrative; this review did not spend provider credits or access browser cookies.

The package provides web search, bounded content extraction, source-evidence artifacts, GitHub views, PDF conversion, and video analysis. Keyless search is available through Exa MCP; OpenAI can reuse Pi's Sign in with ChatGPT credentials (or legacy Codex auth). DuckDuckGo is keyless but explicit-only. Remote services may rate-limit or change availability.

## Tool activation

`toolActivation: "auto"` exposes only `web_enable` at the start of a new session when the model supports dynamic tool addition; otherwise tools register eagerly. `"dynamic"` forces activation, and `"eager"` exposes the full tool set. Continued sessions retain the activation state recorded in their transcript. Discover/enable the tools before calling the examples below.

## Search and evidence

```javascript
web_search({ query: "Pi extension API", workflow: "none" })
web_search({ queries: ["query one", "query two"], workflow: "auto-summary" })
web_search({ query: "recent changes", numResults: 10, recencyFilter: "week" })
web_search({ query: "...", domainFilter: ["github.com", "-old.example.com"], provider: "openai" })
web_search({ query: "...", provider: ["brave", "exa"] })
source_check({ claim: "The API supports streaming", queries: ["API streaming documentation"],
  fetchContent: true, domainFilter: ["docs.example.com"] })
```

`query`/`queries` select the questions; `numResults` defaults to 5 and is capped at 20. `recencyFilter` accepts `day`, `week`, `month`, `year`; prefix a `domainFilter` entry with `-` to exclude. Additional options include `provider`, `includeContent`, `workflow`, and `proxy`.

**The fresh-install workflow default is `none`**: bounded source results return directly, with full content stored for retrieval, without opening the curator or making an extra summary-model call. `summary-review` opens the curator and drafts a summary; `auto-summary` drafts one without the curator. The search provider itself may still use an LLM.

`auto` chooses available providers: configured SearXNG is preferred; OpenAI precedes Exa with suitable ChatGPT login, while Exa precedes API-key OpenAI. Use `searchRouting.providers` for a controlled order instead of depending on the changing default chain. Named providers are strict. Provider arrays run concurrently and cannot contain `auto` or `all`. `all` runs every eligible provider, preserves successful per-provider answers, deduplicates sources, and keeps failures as diagnostics. It can consume multiple configured providers' credits.

In 0.35.0, explicit-only providers excluded from automatic selection and `all` include `parallel-mcp`, `duckduckgo`, `kimi`, `anysearch`, `xcrawl`, `valyu`, `xai`, `mistral`, `brightdata`, `serpbase`, `serpapi`, `serper`, `serply`, `you`, `baizhi`, and `zai`. Browser-cookie access alone does not opt Gemini into `all`. Consult the installed README for each provider's credentials and account eligibility; commercial pricing is not pinned here.

`source_check` gathers passages for **manual semantic review**, not automated fact verification. Its schema allows `supported`, `contradicted`, `unclear`, and `missing-evidence`, but extraction itself produces `unclear` when passages exist or `missing-evidence` when none exist. Artifacts include SHA-256 content hashes, exact offsets, passage IDs, source-quality hints, and retained errors. At most 20 sources are retained and `fetchContent` fetches at most 5 pages. Retrieve the artifact using its `responseId`; paginated artifacts are JSON slices.

## Fetching and retrieval

```javascript
fetch_content({ url: "https://example.com/article" })
fetch_content({ urls: ["https://example.com/one", "https://example.com/two"] })
fetch_content({ url: "https://example.com/api", mode: "raw" })
fetch_content({ url: "https://example.com/guide", mode: "answer", prompt: "What are the installation steps?" })
get_search_content({ responseId: "returned-id", urlIndex: 0, offset: 30000 })
get_search_content({ responseId: "returned-id", url: "https://example.com/guide", findText: ["timeout", "retry"], findMode: "fuzzy" })
```

Modes are `readable` (default), `raw`, and `answer`. Answer mode requires `prompt`; its model order is per-call `answerModel: "provider/model-id"`, configured `fetch.answerProvider` + `fetch.answerModel`, then the active enabled Pi model. It sends fetched text to that model and may incur charges. For PDFs it answers from extracted Markdown, while retaining both the saved file and original extraction.

`fetch.defaultMode` and the nonempty `fetch.allowedModes` list constrain defaults and accepted requests; the default must be allowed. A disabled mode fails before I/O, without substitution. Raw mode uses direct HTTP only, preserves textual bodies including non-2xx responses, reports status in details, and skips specialized source handlers, readability, and hosted fallbacks. Raw/direct-image requests use SSRF checks, hostname policy, redirect checks, timeout, and a 5 MB streamed-response limit. Readable extraction recognizes Cloudflare challenge pages; raw mode preserves them.

`fetch.timeout` is seconds (default 30) for direct HTTP and Jina fallback, not one universal deadline for every extractor. `maxInlineContentChars` defaults to 30,000 and caps at 200,000; it controls initial output and retrieval `limit`. `get_search_content` supports `query`/`queryIndex` for searches and `url`/`urlIndex` for fetched content. `findText` returns bounded matching passages, accepts `exact`, `case-insensitive` (default), or `fuzzy`, and cannot combine with `offset`/`limit`; matches cap at 20,000 characters.

Full content is cached under the Pi config directory in private `web-search-cache`, not embedded in the transcript. The cache expires after one hour and is bounded to 128 entries / 128 MiB, oldest first; POSIX permissions are 0700 for directories and 0600 for files. `PI_WEB_ACCESS_CACHE_ROOT` can isolate process caches. Answer-mode originals remain retrievable. Do not treat a cache ID as permanent evidence storage.

## Source-specific behavior

- GitHub repository URLs clone locally and return a tree, directory, or file view. Repositories above 350 MB use a lightweight API view unless `forceClone: true`; commit-SHA URLs use the API. Private repositories require `gh`. Clones are cached for the session and removed on session change. `githubClone.enabled: false` skips this specialization, allowing ordinary extraction.
- GitHub PR/issue URLs use noninteractive `gh pr view` / `gh issue view`, with a smaller field set for older `gh`. A bounded public REST fallback omits checks. The rendered document prioritizes status, body, changes, reviews, comments, and requested comment anchors, then stores full text for offsets/find. `githubPrIssue.enabled: false` skips this specialization.
- YouTube supports common watch, short, live, embed, and shortened URL forms. Video analysis tries Gemini Web when cookies are enabled, then Gemini API, then text-only Perplexity. Local video uses Gemini API uploads, then cookie-enabled Gemini Web; model analysis defaults to a 50 MB limit.
- `timestamp` accepts seconds, `MM:SS`, `H:MM:SS`, or a range; `frames` is capped at 12. Local frame extraction requires `ffmpeg`; YouTube also requires `yt-dlp`. Frame extraction can operate on larger local videos independently of model upload limits.
- PDF extraction saves Markdown in a temporary `pi-web-pdf` directory. `pdf.provider: "auto"` tries keyed Datalab, keyed Gemini, then local `unpdf`; a pinned remote engine skips the other remote engine but may fall back locally on extraction failure (not credential/config errors or cancellation). `unpdf` extracts text without OCR or reliable layout. Inspect tables, math, page order, and truncation for every engine. Remote engines upload document bytes; deletion is best-effort. `pdf.maxSizeMB` defaults to 20 and caps at 50; `pdf.maxPages` defaults to 100 and applies the first-N-page bound across engines. Datalab timeout defaults to 120,000 ms and caps at 300,000 ms. Verify current billing with the provider before a large run.

## Configuration and credentials

The new default is `~/.pi/agent/web-search.json`. The legacy `~/.pi/web-search.json` is a fallback; `PI_CODING_AGENT_DIR` overrides the directory, and an existing XDG configuration can take precedence. Restart Pi after changing registration or configuration.

```json
{
  "toolActivation": "auto",
  "workflow": "none",
  "braveApiKey": "$BRAVE_API_KEY",
  "searchRouting": {
    "providers": ["brave", "exa"],
    "fallbackOn": ["transient", "quota", "network", "invalid-response"]
  },
  "fetchRouting": { "allowRemoteHostedProviders": false },
  "fetch": { "defaultMode": "readable", "allowedModes": ["readable", "raw", "answer"], "timeout": 30 },
  "maxInlineContentChars": 30000,
  "allowBrowserCookies": false,
  "browserCookies": { "browser": "chrome", "profile": "Default" },
  "pdf": { "enabled": true, "maxSizeMB": 20, "maxPages": 100, "provider": "unpdf" }
}
```

Provider API-key fields accept `$NAME` / `${NAME}`, trusted `!command`, or literal keys; `$$` and `$!` escape prefixes. Explicit sources override legacy environment variables and fail that provider locally on resolution errors. Otherwise provider environment variables precede literal configuration values. Command resolvers run for the selected provider request, not at load time, with a 5-second deadline, 16 KiB output limit, reduced environment, and one nonempty stdout line. `OP_SESSION_*` and `OP_SERVICE_ACCOUNT_TOKEN` are forwarded when present; a resolver inherits those credentials' full permissions. Noncredential fields are literal.

`provider` (alias `searchProvider`) takes precedence over routing. `searchRouting` continues only on the listed typed failures. `webSearch.allowedProviders` is an authoritative, nonempty, duplicate-free search allowlist applied to explicit calls, auto/all/routing, source checks, and curator. It neither makes explicit-only providers automatic nor restricts fetch/summary models.

`openaiResponsesUrl` is an explicit Responses-compatible endpoint override (default `https://api.openai.com/v1/responses`), not automatically copied from Pi's model provider. `openaiUseProviderBaseUrl: true` opts into provider-base routing; the explicit URL still wins. `openaiSearchModel` sends its selected ID verbatim, so confirm model/tool support at the chosen gateway. Experimental `openaiUseAlphaSearch` is off by default and uses a distinct search endpoint/protocol; enable only with a server supporting the package's documented implementation. Do not assume that every Responses gateway supports web search.

`braveBaseUrl`, `exaBaseUrl`, and `tavilyBaseUrl` (or their corresponding uppercase env vars) support HTTPS gateways: Brave appends `/web/search`, Exa/Tavily append `/search`. Exa's override applies only to keyed direct API requests, not keyless MCP. Invalid overrides fail; cross-origin redirects strip credentials. `geminiBaseUrl`/`GOOGLE_GEMINI_BASE_URL` configure compatible Gemini API gateways.

`summaryModel` controls curator/auto-summary generation, with provider routing and Pi's enabled-model allowlist authoritative. `summaryInstructions` adds summary guidance. `summaryGenerationDeadlineMs` defaults to 30,000 and caps at 600,000; unavailable models or failures use a deterministic selected-source fallback. Search, summary, and answer-model choices are separate.

Disable individual `tools.webSearch`, `tools.sourceCheck`, `tools.fetchContent`, `tools.getSearchContent`, commands, `image`, or `pdf` with `{ "enabled": false }`. `toolNames` can rename public tools. Legacy `webSearch.enabled` disables search and source checks unless tool-specific overrides exist. Image disable also blocks frames/thumbnails.

## Extraction privacy and network policy

Local extraction uses Readability, discovery relations, and Next.js RSC parsing. Configured Firecrawl/Crawl4AI can provide self-hosted extraction. `fetchRouting.providers` controls ordering; supported names include `http`, `firecrawl`, `crawl4ai`, `jina`, `tinyfish`, `search1api`, `querit`, `kagi`, `ollama`, `parallel`, `parallel-mcp`, `brightdata`, and `gemini`. Parallel MCP must be explicit. Firecrawl is cache-only unless fresh scraping is explicitly enabled. Third-party hosted fetchers stay disabled for remote targets until `fetchRouting.allowRemoteHostedProviders: true`; their own redirects and egress cannot be validated by the local preflight alone.

`fetchContent.domainPolicy` accepts hostname allow/deny lists (host and subdomains); deny wins and redirects are rechecked. This adds restrictions to the SSRF guard and does not apply to local files. `ssrf.allowRanges` allows narrowly specified private/synthetic ranges; all-address ranges are rejected.

A per-call or config `proxy` string routes extension HTTP(S) requests through `curl`; `""` forces direct. It does not route Pi's model traffic. Localhost and `NO_PROXY` hosts bypass the proxy. `ssrf.trustEnvProxy` only relaxes local DNS preflight under its documented proxy conditions; it does **not** configure proxy transport and still blocks literal private targets/localhost. Environment proxy variables alone do not reliably route Node fetch.

Browser cookies require explicit opt-in (`allowBrowserCookies` or `PI_ALLOW_BROWSER_COOKIES=1`). Use `browserCookies.browser` / `.profile`; the old top-level `chromeProfile` is rejected. Presets include Chrome, Helium, Brave, Arc, Chromium, and Edge where supported; profiles are directory names, not arbitrary paths.

For authenticated fetching, configure named `authFetch` profiles with allowed hosts and call `fetch_content({ url, auth: "profile-name" })`; `auth: true` requires exactly one profile. The local direct path requires HTTPS, blocks cross-origin redirects, and never sends cookies or authenticated content to hosted extractors. Profile objects support `hosts`, optional `chromeProfile`, `redirects: "same-origin"`, and `cache: "session" | "off"`.

## Curator commands

`/websearch [queries]` opens the curator; `/curator [on|off|summary-review]` changes workflow; `/search` browses stored results; `/google-account` selects the Gemini Web account. `Ctrl+Shift+W` toggles request activity. Browser-open failures print the curator URL.

By default the curator binds loopback and uses an unguessable session token over HTTP. `curatorRemote: true` binds all interfaces and prints the hostname; `{ "host": "private-host", "bind": "private-ip" }` separates printed host from binding. Anyone holding the token and reaching that endpoint can search with configured credentials and change returned summaries; use an appropriate private connection. Remote mode prints the URL, changes idle timeout from 20 to 60 seconds, and only auto-opens a browser when `autoOpenBrowser: true`. Local `autoOpenBrowser: false` likewise prints the URL without changing binding.
