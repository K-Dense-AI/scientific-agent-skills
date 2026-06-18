# pi-subagents Package

Source: https://pi.dev/packages/pi-subagents

Extension for delegating tasks to focused child agents with sequential chains, parallel execution, dynamic fanout, worktree isolation, and acceptance gates.

```bash
pi install npm:pi-subagents
```

## Built-in Agents

| Agent | Purpose |
|---|---|
| `scout` | Fast local codebase recon: files, entry points, data flow, risks |
| `researcher` | Web/docs research with sources and a concise brief |
| `planner` | Concrete implementation plan from existing context |
| `worker` | Implementation: file editing and validation |
| `reviewer` | Code review and small fixes against task/plan |
| `context-builder` | Setup pass gathering code context and handoff material |
| `oracle` | Second opinion challenging assumptions; no edits |
| `delegate` | Lightweight general delegate close to parent behavior |

Packaged `planner`, `worker`, `oracle` default to `context: "fork"` (branch from parent session state); others default to `fresh`.

## Commands

```bash
/run <agent> [task]                  # single agent; --bg detached, --fork branch session
/run reviewer[model=anthropic/claude-sonnet-4] summarize this code
/chain scout "scan the codebase" -> planner "create an implementation plan"
/parallel scanner "find security issues" -> reviewer "check code style"
/run-chain <chainName> -- <task>     # saved workflow
/subagents-doctor                    # setup diagnostics
```

Per-step config uses `[key=value,...]` on the agent name: `output=file.md`, `outputMode=file-only|inline`, `reads=a.md+b.md`, `model=...`, `skills=a+b`, `thinking=high`, `progress`.

Natural language also works: "Use reviewer to review this diff", "Run parallel reviewers: one for correctness, one for tests".

Packaged prompt shortcuts: `/parallel-review`, `/review-loop`, `/parallel-research`, `/parallel-context-build`, `/parallel-handoff-plan`, `/gather-context-and-clarify`, `/parallel-cleanup` (add `autofix` to apply synthesized fixes).

## Programmatic API (subagent tool)

```javascript
{ agent: "worker", task: "refactor auth" }
{ tasks: [{ agent: "scout", task: "audit frontend" }, { agent: "reviewer", task: "audit backend" }] }   // parallel; count: N duplicates a task
{ chain: [{ agent: "scout", task: "Gather context" }, { agent: "planner" }, { agent: "worker" }, { agent: "reviewer" }] }
{ chain: [...], timeoutMs: 30000 }
{ agent: "worker", task: "...", maxRuntimeMs: 600000 }
{ action: "list" | "get" | "create" | "update" | "delete" | "status" | "interrupt" | "resume" | "doctor" }
{ action: "resume", id: "<run-id>", message: "follow-up" }
```

Key parameters: `output` (file or `false`), `outputMode` (`inline`/`file-only`), `skill` (string/array/`false`), `model`, `concurrency` (default 4), `worktree`, `context` (`fresh`/`fork`), `chainDir`, `clarify` (default true for chains), `async`, `cwd`, `maxOutput` (default 200KB/5000 lines), `share` (Gist upload, off by default), `acceptance`.

Dynamic fanout: a chain step with `expand: { from: { output: "name", path: "/items" }, item: "target", maxItems: N }` plus `parallel: { agent, task: "Review {target.path}" }` and `collect: { as: "reviews" }` fans out over a prior step's structured output (`as` + `outputSchema`).

## Agent Definition Files

Markdown with YAML frontmatter. Precedence: project `.pi/agents/**/*.md` > user `~/.pi/agent/agents/**/*.md` > builtin.

```yaml
---
name: scout
description: Fast codebase recon
model: claude-haiku-4-5
fallbackModels: openai/gpt-5-mini, anthropic/claude-sonnet-4
thinking: high
tools: read, grep, find, ls, bash      # allowlist; mcp: prefix for direct MCP tools
extensions: mcp:chrome-devtools        # omitted = all; empty = none
skills: safe-bash
systemPromptMode: replace              # or append
inheritProjectContext: false
inheritSkills: false
defaultContext: fork                   # or fresh
output: context.md
defaultReads: context.md
defaultProgress: true
completionGuard: false                 # false for non-implementation validators
interactive: true
maxSubagentDepth: 1
maxExecutionTimeMs: 600000
maxTokens: 50000
---
Your system prompt goes here.
```

Subagents only receive direct MCP tools when listed in `tools:` frontmatter (requires `pi-mcp-adapter`); a global `directTools: true` is insufficient.

## Chain Files

Reusable workflows: project `.pi/chains/**/*.chain.md|.chain.json` > user `~/.pi/agent/chains/`. Markdown chains use `## agent` headings with per-step keys (`phase`, `label`, `as`, `output`, `outputMode`, `reads`, `model`, `skills`, `progress`, `outputSchema`) and a task body. Template variables: `{task}`, `{previous}`, `{chain_dir}`, `{outputs.name}`.

## Configuration

Builtin agent overrides in `~/.pi/agent/settings.json` or `.pi/settings.json`:

```json
{ "subagents": { "agentOverrides": { "reviewer": { "model": "anthropic/claude-sonnet-4", "thinking": "high" } }, "disableBuiltins": false } }
```

Override fields: `model`, `fallbackModels`, `thinking`, `systemPromptMode`, `inheritProjectContext`, `inheritSkills`, `defaultContext`, `disabled`, `skills`, `tools`, `systemPrompt`.

Extension config at `~/.pi/agent/extensions/subagent/config.json`: `asyncByDefault`, `forceTopLevelAsync`, `parallel: { maxTasks, concurrency }`, `defaultSessionDir`, `maxSubagentDepth`, `intercomBridge: { mode: "always"|"fork-only"|"off", instructionFile }`, `worktreeSetupHook` (+ `worktreeSetupHookTimeoutMs`; hook gets stdin JSON with repo/worktree paths and must print `{ "syntheticPaths": [...] }`).

Nesting depth defaults to 2 levels; tighten/relax via `PI_SUBAGENT_MAX_DEPTH` env var, config `maxSubagentDepth`, or per-agent frontmatter (per-agent can only tighten). Children never get the `subagent` tool unless their resolved tools explicitly include it.

## Worktree Isolation

`worktree: true` on parallel tasks or chain steps runs each agent in an isolated git worktree. Requires a git repo with a clean working tree; `node_modules/` is symlinked in; task-level `cwd` overrides must match the shared cwd.

## Acceptance Gates

Attach explicit contracts to any run/step:

```javascript
{ agent: "worker", task: "Implement the fix", acceptance: {
  criteria: ["Patch the bug without widening scope"],
  evidence: ["changed-files", "tests-added", "commands-run", "residual-risks", "no-staged-files"],
  verify: [{ id: "focused", command: "npm test", timeoutMs: 120000 }],
  maxFinalizationTurns: 3
} }
```

Provenance levels reported: `attested`, `checked`, `verified`, `reviewed`, `rejected`.

## Async, Clarify, Observability

`--bg` / `async: true` detaches runs; status files under `<tmpdir>/pi-subagents-<scope>/async-subagent-runs/<id>/` (`status.json`, `events.jsonl`, logs). Chains open a clarify TUI by default to preview/edit steps (`e` edit, `m` model, `t` thinking, `s` skills, `b` background, `Enter` run, `Esc` cancel). Debug artifacts land in `{sessionDir}/subagent-artifacts/` with input/output/jsonl/meta per run; chain artifacts in `<tmpdir>/pi-subagents-<scope>/chain-runs/{runId}/`. Directories older than 24h are cleaned on startup. Events: `subagent:async-started`, `subagent:async-complete`, `subagent:control-intercom`, `subagent:result-intercom`.

Optional companion `pi install npm:pi-intercom` lets children call `contact_supervisor` (reasons: `need_decision`, `progress_update`) and groups completion delivery back to the parent.

Recommended implementation pattern: clarify → planner → worker → fresh reviewers → worker.
