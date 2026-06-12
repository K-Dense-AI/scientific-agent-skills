# Runtime Adapters

How to run this skill's three delegation roles across coding agents. The
programming principles in `SKILL.md` are runtime-independent; only the dispatch
mechanism and model names below change per runner.

Roles:
- **main-synthesizer** — strongest reasoning; owns judgment, architecture, final synthesis.
- **code-scout** — fast, read-only code scanning / call-path tracing / evidence gathering.
- **docs-scout** — cheap docs / API / book-section lookup.

> **Model IDs move fast.** The identifiers below were current as of **2026-05**.
> Re-check the cited official docs before relying on an exact string — lineups
> change every few weeks.

## Two classes of runtime

1. **SKILL.md-native** — auto-discover a skill *directory* (`SKILL.md` +
   `references/` + `scripts/` + `assets/`) via the agentskills.io standard:
   **Codex CLI, Claude Code, Gemini CLI, OpenHands** (Zed and Roo Code also
   document Agent Skills support).
2. **Rules / modes-based** — no `SKILL.md` loader; model-agnostic (bring your own
   model from any provider). Point them at this skill through their rules /
   custom-mode mechanism: **Cursor, Aider, Continue, Windsurf**.

## Adapter table (role × runtime)

| Role | Codex CLI | Claude Code | Gemini CLI | OpenHands |
|------|-----------|-------------|------------|-----------|
| main-synthesizer | `gpt-5.5` | `claude-opus-4-8` (alias `opus`) | Gemini **Pro** tier | configured strong model |
| code-scout | `gpt-5.3-codex-spark` † | built-in **Explore** agent (Haiku) | Gemini **Flash** | fast model via `SKILL.md` |
| docs-scout | `gpt-5.4-mini` | custom agent · `claude-haiku-4-5` | **Flash-Lite** | configured cheap model |

† `gpt-5.3-codex-spark` is OpenAI's near-instant, text-only model — the fastest
option for read-only scanning — but it **requires ChatGPT Pro** (research
preview, with limited design-partner API access). Without Pro, fall back to
`gpt-5.4-mini`, the model OpenAI documents for subagents: *"Fast, efficient mini
model for responsive coding tasks and subagents."*

For Gemini, use the current Pro / Flash / Flash-Lite identifiers from
`ai.google.dev` — the exact version strings change and are not pinned here.

## Per-runtime notes

### Codex CLI
- **Subagents** are triggered manually ("spawn agents", "delegate in parallel"),
  inspected via `/agent`, configured in an agent file with `model` and
  `model_reasoning_effort` (`low` / `medium` / `high`).
- **Models:** `gpt-5.5` (recommended default / strongest), `gpt-5.4`,
  `gpt-5.4-mini` (fast subagent/scout), `gpt-5.3-codex`, `gpt-5.3-codex-spark`
  (Pro-only preview), `gpt-5.2` (previous).
- **Skill discovery:** `.agents/skills/` scanned from the working directory up to
  the repo root, plus `$HOME/.agents/skills` (user) and `/etc/codex/skills`
  (admin). **Not** `~/.codex/skills` — that path holds only `config.toml` and
  `AGENTS.md`.

### Claude Code
- **Subagents** are Markdown files in `.claude/agents/` (project) or
  `~/.claude/agents/` (user); `name` + `description` required; `model` accepts
  `sonnet` / `opus` / `haiku`, a full ID (`claude-opus-4-8`), or `inherit`.
- **Built-in agents:** `Explore` (Haiku, read-only — the natural code-scout),
  `Plan` (inherits), `general-purpose` (inherits, all tools). There is no
  built-in "docs-researcher"; use a custom Haiku agent for docs-scout.
- **Models:** `claude-opus-4-8` ($5/$25 MTok, synthesizer), `claude-sonnet-4-6`
  (balanced), `claude-haiku-4-5` ($1/$5, scout).
- **Skill discovery:** `~/.claude/skills/<name>/SKILL.md` (personal),
  `.claude/skills/` (project), or a plugin's `skills/` dir.
- **Claude-only `SKILL.md` frontmatter** (`model`, `effort`, `context: fork`,
  `agent`, `allowed-tools`, `user-invocable`) is **ignored by other runtimes**, so
  it is safe to add as a Claude-specific adapter in a shared file.

### Gemini CLI
- **Activation:** when a task matches a skill's `description`, Gemini calls the
  `activate_skill` tool automatically (with a confirmation prompt). Users cannot
  invoke `activate_skill` manually. Gemini CLI also has subagents.
- **Skill discovery:** `~/.gemini/skills/` (user) or the `~/.agents/skills/`
  alias; `.gemini/skills/` (workspace) or the `.agents/skills/` alias.
- **Models:** Pro tier (synthesis) vs Flash / Flash-Lite (scouting). Verify the
  current IDs at `ai.google.dev`.

### OpenHands
- Implements the **AgentSkills standard** (`SKILL.md` + `scripts/`/`references/`/
  `assets/`) plus an optional `triggers` keyword field for auto-activation;
  model-mediated via `invoke_skill()`. Skills load from a local directory,
  persistent storage, or a community GitHub repo. Model is whatever OpenHands is
  configured with.

### Rules / modes-based runtimes
These are model-agnostic — set `main-synthesizer` to your configured strongest
model and `code-scout`/`docs-scout` to your configured fast/cheap model, then
load this skill through the runtime's own mechanism:
- **Cursor** — custom modes + rules (`.cursor/rules` / `AGENTS.md`); model picked
  from the menu (multi-provider).
- **Aider** — chat modes `code` / `ask` / `architect` / `help`; model via
  `--model` / `/model`. Architect mode's strong **architect model** +
  fast **editor model** (`--editor-model`) maps naturally onto
  synthesizer + scout.
- **Continue** — `config.yaml` models with roles (`chat`/`edit`/`apply`/…),
  multi-provider; `rules` are concatenated into the system message.
- **Windsurf (Cascade)** — Code/Chat modes; customize via Memories & Rules, MCP,
  and Workflows; model picked from the menu.

## Portable `SKILL.md` frontmatter rules

To load across the strictest native runtime (upstream agentskills.io + Codex):
- `name` = the skill **directory name**, lowercase letters / digits / hyphens,
  ≤ 64 chars, and **must not contain the substrings `anthropic` or `claude`**
  (a Claude Code validation rule). `programmer` satisfies all of these.
- `description` — non-empty, ≤ 1024 chars; state **when to use and when not to**.
  Claude Code truncates the `description` + when-to-use listing at 1,536 chars.
- Keep the `SKILL.md` **body lean** and push deep material into `references/`
  (loaded on demand), code into `scripts/`, templates into `assets/` —
  progressive disclosure is shared by all four native runtimes.
- Extra frontmatter fields are tolerated (the "exactly name + description"
  reading was refuted), which is what makes Claude-only adapter fields safe.

## One directory, many runtimes

`.agents/skills/` is the lowest-common-denominator location: it is **Codex's
primary discovery path** and **Gemini CLI's interop alias**, so a single
directory is found by both.

- User scope: `~/.agents/skills/programmer/` → Codex **and** Gemini CLI.
- Claude Code: copy to `~/.claude/skills/programmer/` (copy, don't rely on
  symlinks — Claude's symlink/cross-project discovery has known edge bugs).
- In a repo: `.agents/skills/programmer/` → Codex and Gemini workspace scope.
- OpenHands: its configured skills directory.

## Sources (primary, verified 2026-05)

- Codex models — https://developers.openai.com/codex/models
- Codex subagents — https://developers.openai.com/codex/concepts/subagents
- Codex skills — https://developers.openai.com/codex/skills
- Claude models — https://platform.claude.com/docs/en/about-claude/models/overview
- Claude subagents — https://code.claude.com/docs/en/sub-agents
- Claude skills — https://code.claude.com/docs/en/skills
- Gemini CLI skills — https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md
- Gemini models — https://ai.google.dev/gemini-api/docs/models
- OpenHands skills — https://docs.openhands.dev/sdk/guides/skill
- Agent Skills standard — https://agentskills.io/specification
