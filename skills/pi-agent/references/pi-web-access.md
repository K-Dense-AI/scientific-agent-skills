# pi-web-access Package

Source: https://pi.dev/packages/pi-web-access

Extension adding web search, URL fetching, GitHub repo cloning, PDF extraction, YouTube video understanding, and local video analysis to Pi.

```bash
pi install npm:pi-web-access
```

Works immediately without API keys via Exa MCP. Optional: `brew install ffmpeg yt-dlp` for video frame extraction.

## Tools

### web_search

Searches via Exa, Perplexity, or Gemini with synthesized answers and citations.

```javascript
web_search({ query: "TypeScript best practices 2025" })
web_search({ queries: ["query 1", "query 2"] })
web_search({ query: "latest news", numResults: 10, recencyFilter: "week" })
web_search({ query: "...", domainFilter: ["github.com"], provider: "exa" })
```

Parameters: `query`/`queries`, `numResults`, `recencyFilter` (day/week/month/year), `domainFilter`, `provider` (auto/exa/perplexity/gemini), `includeContent`, `workflow`.

### code_search

Code examples and API references; no API key required.

```javascript
code_search({ query: "React useEffect cleanup pattern" })
code_search({ query: "Express middleware error handling", maxTokens: 10000 })
```

### fetch_content

Readable content from URLs, GitHub repos, YouTube videos, PDFs, and local video files.

```javascript
fetch_content({ url: "https://example.com/article" })
fetch_content({ urls: ["url1", "url2", "url3"] })
fetch_content({ url: "https://github.com/owner/repo" })
fetch_content({ url: "https://youtube.com/watch?v=abc", prompt: "What libraries are shown?" })
fetch_content({ url: "/path/to/recording.mp4", prompt: "What error appears on screen?" })
fetch_content({ url: "https://youtube.com/watch?v=abc", timestamp: "23:41-25:00", frames: 4 })
```

Parameters: `url`/`urls`, `prompt`, `timestamp`, `frames` (max 12), `forceClone`.

### get_search_content

Stored content from previous searches (for content beyond the 30,000-character inline limit): `get_search_content({ responseId: "abc123", urlIndex: 0 })` or `{ responseId, url }`.

## Capabilities

- **GitHub repos**: cloned locally for real file contents — root URLs return tree + README, `/tree/` paths list directories, `/blob/` paths show files; repos over 350MB get lightweight API-based views.
- **YouTube**: visual descriptions, timestamped transcripts, chapter markers via Gemini.
- **Local video**: MP4/MOV/WebM/AVI up to 50MB via Gemini; frame extraction at timestamps with ffmpeg.
- **PDFs**: text extraction saved to `~/Downloads/` as markdown (no OCR).
- **Blocked pages**: automatic retry via Jina Reader, then Gemini URL Context API, for JS-heavy and anti-bot sites.

## CLI Commands

```
/websearch [queries]            # open curator; pre-fill comma-separated queries
/curator                        # toggle curator workflow
/curator on|off|summary-review  # configure curator mode
/search                         # browse stored results interactively
/google-account                 # display active Google account
```

`Ctrl+Shift+W` toggles an activity monitor with live request/response data.

## Configuration

All settings in `~/.pi/web-search.json` are optional. Env vars `EXA_API_KEY`, `GEMINI_API_KEY`, `PERPLEXITY_API_KEY` take precedence over the file.

```json
{
  "exaApiKey": "exa-...",
  "perplexityApiKey": "pplx-...",
  "geminiApiKey": "AIza...",
  "provider": "exa",
  "chromeProfile": "Profile 2",
  "allowBrowserCookies": false,
  "searchModel": "gemini-2.5-flash",
  "summaryModel": "anthropic/claude-haiku-4-5",
  "workflow": "summary-review",
  "curatorTimeoutSeconds": 20,
  "githubClone": { "enabled": true, "maxRepoSizeMB": 350, "cloneTimeoutSeconds": 30, "clonePath": "/tmp/pi-github-repos" },
  "youtube": { "enabled": true, "preferredModel": "gemini-3-flash-preview" },
  "video": { "enabled": true, "preferredModel": "gemini-3-flash-preview", "maxSizeMB": 50 },
  "shortcuts": { "curate": "ctrl+shift+s", "activity": "ctrl+shift+w" }
}
```

Bundled skill `librarian` combines GitHub cloning, web search, and git operations for evidence-backed library investigation with permalink citations.

## Limitations

Chromium cookie extraction requires opt-in (`allowBrowserCookies: true`); age-restricted/private YouTube videos may fail; Gemini handles videos up to ~1 hour; non-code GitHub URLs fall through to standard web extraction.
