# pi-interview Package

Source: https://pi.dev/packages/pi-interview

Interactive interview form extension: the agent collects structured user responses through forms with single/multi-select, text input, image upload, and info panels, plus rich media (code, diffs, Markdown, images, Chart.js charts, Mermaid diagrams, tables, HTML). Requires pi-agent v0.35.0+.

```bash
pi install npm:pi-interview
pi install npm:glimpseui   # optional: native macOS windows (browser fallback otherwise)
```

## Invocation

Agents call the tool directly:

```javascript
await interview({
  questions: '/path/to/questions.json',
  timeout: 600,    // optional, seconds
  verbose: false   // optional, debug logging
});
```

## Question Schema

```json
{
  "title": "Project Setup",
  "description": "Review my suggestions and adjust as needed.",
  "questions": [
    { "id": "context", "type": "info", "question": "Architecture context", "context": "This project needs SSR and edge deployment support." },
    { "id": "framework", "type": "single", "question": "Which framework?",
      "options": ["React", "Vue", "Svelte"],
      "recommended": "React", "conviction": "strong", "weight": "critical" }
  ]
}
```

Question types: `single` (radio), `multi` (checkbox), `text`, `image` (upload), `info` (non-interactive panel).

| Field | Purpose |
|---|---|
| `id`, `type`, `question` | Identifier, type, question text |
| `options` | Choices for single/multi; strings or `{ label, content }` objects |
| `recommended` | Pre-selected option(s) with badge |
| `conviction` | `"strong"` or `"slight"` — controls pre-selection |
| `weight` | `"critical"` or `"minor"` — visual prominence |
| `context` | Help text |
| `content` | Code/diff/Markdown block: `{ source, lang, file, lines, highlights, showSource }`; `lang: "diff"` renders diffs, `lang: "md"` renders Markdown preview |
| `media` | Object or array: types `image`, `table`, `chart`, `mermaid`, `html`; each supports `position`: `"above"`/`"below"`/`"side"` and `caption`; tables take `{ headers, rows, highlights }` |

## Response Format

```typescript
interface Response { id: string; value: string | string[]; attachments?: string[]; }
```

## Settings

`~/.pi/agent/settings.json`:

```json
{
  "interview": {
    "timeout": 600,
    "port": 19847,
    "snapshotDir": "~/.pi/interview-snapshots/",
    "autoSaveOnSubmit": true,
    "generateModel": "anthropic/claude-haiku-4-5",
    "theme": { "mode": "auto", "name": "default", "lightPath": "/path/to/light.css", "darkPath": "/path/to/dark.css", "toggleHotkey": "mod+shift+l" }
  }
}
```

Timeout precedence: function parameter > settings > default 600s. Built-in themes: `default` (monospace) and `tufte` (serif); modes `dark` (default), `light`, `auto`. Custom themes are CSS files overriding variables like `--bg-body`, `--bg-card`, `--accent`, `--error`.

## Recovery and Snapshots

Abandoned/timed-out interviews save to `~/.pi/interview-recovery/{date}_{time}_{project}_{branch}_{sessionId}.json` (auto-deleted after 7 days). Submissions can auto-save snapshots (`index.html` + `images/`) to `~/.pi/interview-snapshots/`. Resume either by passing the recovery JSON or snapshot `index.html` path as `questions`.

## Keyboard and Limits

`↑`/`↓` navigate options, `⌘+←`/`⌘+→` navigate questions (Ctrl on non-macOS), `Tab` cycles, `Enter`/`Space` selects, `⌘+Enter` submits, `Esc` twice quits, `⌘+Shift+L` toggles theme. Auto-saves via localStorage; detects multi-agent queues.

Image limits: max 12 per submission, 5MB each, 4096×4096 px, PNG/JPG/GIF/WebP.
