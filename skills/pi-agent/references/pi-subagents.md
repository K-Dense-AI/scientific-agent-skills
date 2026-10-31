# pi-subagents Package

Source: https://pi.dev/packages/pi-subagents (docs: `https://github.com/nicobailon/pi-subagents/tree/main/docs`)

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Delegate work to focused child Pi sessions: code review, scouting, implementation, parallel audits, saved workflows, background jobs. Installing the extension does not start anything automatically — it supplies `subagent` and, on models supporting dynamic tool additions, a small `subagents_enable` loader. Version 0.74.0 requires Pi 0.86.1+; this review used Pi 0.99.2. `toolActivation` is `auto` by default, or `dynamic`/`eager`.

```bash
pi install npm:pi-subagents
```

Users normally ask in plain language ("Use reviewer to review this diff", "Run parallel reviewers for correctness, tests, and complexity"). Pi decides whether to call the tool, which agent to use, and how to compose the work.

## Built-in Agents

| Agent | Purpose |
|---|---|
| `scout` | Fast local codebase recon: relevant files, entry points, data flow, risks, where to start |
| `researcher` | Web/docs research with sources; needs `pi-web-access` for `web_search`/`fetch_content`/`get_search_content` |
| `worker` | Implementation, including approved oracle handoffs; escalates unapproved decisions |
| `reviewer` | Code review and small fixes against task/plan, tests, edge cases, simplicity |
| `oracle` (alias `advisor`) | Second opinion before acting; challenges assumptions, no edits |
| `delegate` | Lightweight general delegate close to parent behavior (append prompt mode) |

Builtins load at the lowest priority and inherit the current Pi default model unless `subagents.defaultModel` or an override says otherwise. Packaged `worker` defaults to fresh context; `oracle` and `advisor` prefer fork context, falling back to fresh only when that implicit preference cannot use a persisted parent leaf. Builtins opt into project-instruction inheritance so they follow repo rules.

Recommended implementation loop: **clarify → scout → worker → fresh reviewers → worker**.

## Execution in 0.74.0

For one child, call `subagent({ agent: "scout", task: "Analyze the auth flow" })`. For composition, write exactly one `js workflow` fenced block in the same assistant reply as one `subagent({ workflow: true })` call:

```js workflow
const scan = await runs.run("scan", { agent: "scout", task: "Analyze auth" });
const reviews = await runs.all([
  { key: "correctness", agent: "reviewer", task: "Review correctness: " + scan.output },
  { key: "tests", agent: "reviewer", task: "Review tests: " + scan.output }
]);
return reviews.map(r => r.output);
```

```javascript
subagent({ workflow: true })
```

`workflow: "./workflows/review.js"` loads a file relative to `cwd`; a string without a path separator resolves a named resource such as `review` or `run-ci`. `workflowScript` and `workflowScriptPath` were **removed**. RPC spawn uses `script` for inline text and `workflow` for a path/resource. Validate without launching with `{ action: "validate", workflow: "./workflows/review.js" }`.

Scripts are JavaScript statement bodies with top-level await and explicit return. Globals include `runs.run`, `runs.all` (ordered array result), `runs.lanes`, `runs.steer`, `runs.status`, `runs.ref`/`refs`, `emit`, `console`, frozen JSON `args`, `state.get/set` for missions, and `prompts.render`. Nested async functions/arrows/methods are rejected for Node/Bun portability. Observe every launched child promise; never read `.output` from an unawaited launch. The sandbox has no filesystem, shell, or arbitrary Pi tools. Only authorized named resources may expose `runs.host`.

Workflows normally run in the background. `async: false` watches in the foreground; composite workflows have no default parent deadline. Set a finite `timeoutMs` when required (maximum 2,147,483,647ms). Explicit child `async: true` returns a **launch receipt** with `ok: false`, `state: "running"`, and empty output; it does not await successful completion. Omit child `async` to await its final result.

`prompts.render` uses `package:<name>`, `user:<name>`, or `project:<name>` for a top-level Markdown prompt, strips frontmatter, and substitutes scalar `{{name}}` values. Pass its returned text as the child's task.

### Key Tool Parameters

`agent`, `action`, `topic`, `config`, `context` (`fresh`/`fork`/`profile` — an explicit value overrides every workflow child; otherwise global `defaultSubagentContext` precedes each child's `defaultContext`), `missionId`, `mission` (object or `false`), `handoffPath`, `view` (`fleet`/`transcript`), `lines` (default 80, max 500), `agentScope`, `async`, `chatProgress`, `timeoutMs`/`maxRuntimeMs`, `toolTimeoutMs`, `turnBudget`, `toolBudget`, `usageBudget`, `cwd`, `maxOutput` (200 KB / 5000 lines), `artifacts`, `includeProgress`, `share`, `sessionDir`, `acceptance`, `gate`, plus per-item `output`, `outputMode`, `skill`, `model`, `worktree`, `resume`.

Budgets: `turnBudget` is `{ maxTurns, graceTurns }` (warn at `maxTurns`, terminate at the next assistant boundary after the grace window); `toolBudget` is `{ soft?, hard, block? }` (block defaults to `read`/`grep`/`find`/`ls`; `"*"` blocks everything, final assistant text never blocked); `usageBudget` is root-only `{ tokens?: { soft?, hard }, costUsd?: { soft?, hard } }` where soft limits are status-only and hard limits prevent later child launches without stopping running ones. **Do not** set turn, hard tool, or tight usage budgets on mutation-capable children (implementation workers, fix workers, reviewers with edit authority) — none of those measure whether a delivery slice is buildable, and a default tool budget blocks read/search tools rather than mutations. Bound writers with a narrow task and an outer `timeoutMs` instead, and request a checkpoint via `steer` before the deadline.

`context: "fork"` fails fast when the parent session is not persisted, the leaf is missing, or the branched session cannot be created — it never silently downgrades to `fresh`. Forking strips signed Anthropic `thinking`/`redacted_thinking` replay blocks; the child keeps its requested thinking level and reasons afresh. Implicit global/profile fork preferences may fall back to fresh when there is no persisted parent leaf; an explicit fork request never silently downgrades.

`outputMode: "file-only"` returns a compact pointer (`Output saved to: /abs/report.md (48.2 KB, 2847 lines)…`) instead of inline text; failed runs and save errors still return inline output for debugging. A read-only child does not need filesystem access for `output` — it returns the artifact in its final response and the runtime persists it.

### Retained Children

Completed workflow children from the current parent session stay addressable. `{ action: "children.list" }` lists up to the last 10 with run ids; a later workflow continues one by passing `resume` instead of `agent`:

```js workflow
let writer = await runs.run("implement", { agent: "worker", task: "Implement the accepted contract" });
for (const pass of [1, 2]) {
  const task = await prompts.render("project:writer-followup", { pass, previous: writer.output });
  writer = await runs.run("followup-" + pass, { resume: writer.runId, task });
}
return writer;
```

Run the block with `subagent({ workflow: true })` in the same reply.

Each resume can return a new retained run id, so loops must continue from the latest `runId`. `resume` and `agent` are mutually exclusive, the revived child keeps its stored agent/model/tool contract, and `gate` is rejected on resume items. Top-level `{ action: "resume" }` stays detached and returns a background receipt — use it for a simple challenge outside a script; use `runs.run({ resume })` only when the script must await the revived output. `steer` with `mode: "follow_up"` only queues text for the next `resume`; it does not revive a completed child.

## Commands

```bash
/run <agent> [task] [--bg] [--fork]     # one child
/subagents-fleet                        # live fleet inspector
/subagents-stop [run-id]                # stop a top-level async run
/subagents-detach [run-id]              # leave a foreground run running
/subagents-doctor                       # read-only setup diagnostics
/subagents-guide [topic]                # packaged docs for the installed version
/subagents-refine <agent>               # project-local refinement overlay
/subagents-models [agent]               # live runtime model mapping
/subagents-watchdog [status|on|off|recommend-model|model ...|session model ...|check]
/subagents-refresh-provider-models <provider> [--force]
/subagents-generate-profiles <provider> | /subagents-load-profile <name> | /subagents-check-profile <name>
/prompt-workflow <template> [args]      # run a subagent prompt template
```

Per-run overrides use bracket syntax on the agent name: `/run reviewer[model=anthropic/claude-sonnet-4:high] "Review this diff"`.

Packaged prompt shortcuts: `/parallel-review`, `/review-loop`, `/parallel-research`, `/gather-context-and-clarify`, `/parallel-cleanup` (add `autofix` to `/parallel-review` or `/parallel-cleanup` to apply only the synthesized fixes worth doing now).

`/subagents-guide` and `{ action: "guide", topic }` read the packaged docs for the installed version. Topics: `overview`, `workflows`, `agents`, `missions`, `observability`, `tool-reference`, `configuration`, `models`, `watchdog`, `extension-api`.

## Management, Status, and Control Actions

```javascript
{ action: "list" | "get" | "create" | "update" | "delete" | "eject" | "enable" | "disable" | "reset" }
{ action: "children.list" }
{ action: "refine" | "refine.show" | "refine.rollback", agent: "reviewer" }
{ action: "status" }                                            // all active runs
{ action: "status", view: "fleet" }
{ action: "status", id: "<run-id>", view: "transcript", index: 0, lines: 80 }
{ action: "interrupt" | "stop", id: "<run-id>" }
{ action: "resume", id: "<run-id>", index: 1, message: "follow-up" }
{ action: "steer", id: "<run-id>", mode: "steer" | "follow_up" | "auto", message: "guidance" }
{ action: "grant-spawn-budget", additional: 10 }
{ action: "doctor" }
{ action: "watchdog.recommend-model" } | { action: "watchdog.configure", model: "recommended", scope: "session" | "user" | "project" }
{ action: "mission.create" | "mission.list" | "mission.show" | "mission.update"
  | "mission.resolve-decision" | "mission.attach-run" | "mission.close" }
{ action: "schedule.create" | "schedule.list" | "schedule.show" | "schedule.history"
  | "schedule.pause" | "schedule.resume" | "schedule.run" | "schedule.run-due" | "schedule.delete" }
{ action: "inspector.open" | "inspector.status" | "inspector.close", id, index, focus }
{ action: "project.open" | "project.status" | "project.close", cwd, message }
```

`create` uses `config.scope` (not `agentScope`); `config.package` registers the runtime name as `{package}.{name}`; `config.aliases` accepts a comma-separated string, array, or `false`. Clear optional string fields with `false` or `""`. `eject` copies a bundled builtin or package agent verbatim into the user/project agent dir as an editable shadow; `reset` deletes the scope's custom file and/or override entry, restoring the bundled default (it refuses when no bundled default exists — use `delete` for purely custom agents). These accept `agentScope: "user" | "project"` and operate on one scope at a time; a project-scope disable survives a user-scope enable.

`status` resolves exact foreground ids, top-level async ids, and nested run ids before prefix matching. `stop` is stronger than `interrupt`: it is not a resumable pause, rejects foreground and nested targets, and stopped runs must be restarted as new runs. `resume` revives a paused, completed, or failed child from its stored session file by starting a *new* child process, taking an exclusive cross-process lease on the canonical session file. `steer` waits up to three seconds for correlated acceptance and returns a request id with `delivered`/`scheduled`/`pending`/`partial`/`recovered`/`failed` plus `deliveryStatus: "delivered" | "queued"`; the FIFO holds 20 messages and the persisted `steering` ledger retains 20 requests. `append-step`, `approve-checkpoint`, and `reject-checkpoint` require `legacyChainControls: true`.

`bg_wait` is the only registered wait tool in 0.74.0 (the former `subagent_wait` name is not registered). It blocks on background work: `{ all: true }`, `{ id }`, `{ timeoutMs }`. Background runs are detached — prefer returning control and letting Pi deliver the completion notification, and use `bg_wait` only when the current turn must have results before it ends. `{ id, nonBlocking: true }` resolves the prefix once, returns a subscription token immediately, and wakes the session on completion/failure/attention/timeout. Blocking-window expiry returns non-error `window_elapsed` while work continues. `stopOnAttention` defaults to true; supervisor/contact requests stop the wait even when false. Headless sessions auto-drain current-session work at `agent_end` with their own strict deadline.

## Agent Definition Files

Markdown with YAML frontmatter. Precedence low → high: builtin (the installed package's `agents/`), installed package (`pi-subagents.agents` or `pi.subagents.agents` in `package.json`), user (`~/.pi/agent/agents/**/*.md`), project (`.pi/agents/**/*.md`; legacy `.agents/**/*.md` is also read, project config wins collisions). `agentScope: "user" | "project" | "both"` controls discovery.

```yaml
---
name: scout
package: code-analysis        # registers as code-analysis.scout
description: Fast codebase recon
aliases: explorer, code-scout
tools: read, grep, find, ls, bash, mcp:chrome-devtools
extensions:                   # omitted = all; empty = none; list = allowlist
subagentOnlyExtensions: ./tools/child-only-search.ts
model: claude-haiku-4-5
fallbackModels: openai/gpt-5-mini, anthropic/claude-sonnet-4
thinking: high
systemPromptMode: replace     # or append (keeps Pi's base prompt)
inheritProjectContext: false
inheritSkills: false
skills: safe-bash, review-checklist
skillPath: ./skills, ../shared-skills
defaultContext: fork
output: context.md
defaultReads: context.md
defaultProgress: true
async: true
timeoutMs: 900000
toolTimeoutMs: 600000
turnBudget: {"maxTurns":20,"graceTurns":2}
acceptance: {"level":"none","reason":"lightweight lookup"}
acceptanceRole: read-only     # or writer
completionGuard: false        # false for non-implementation validators
interactive: true             # parsed, not enforced
maxSubagentDepth: 1
memory: { scope: project, path: security-reviewer }
permission: { write: allow, edit: ask }
---
Your system prompt goes here.
```

Scalar list fields (`tools`, `excludeTools`, `allowedAgents`, `defaultReads`, `skills`, `skillPath`, `fallbackModels`, `extensions`, `subagentOnlyExtensions`) accept comma-separated or YAML block-list form. Model ids match fuzzily (provider separator, id separator, case, trailing date stamps); a qualified provider query never switches providers.

Custom agents start with a clean prompt: they do not inherit Pi's base prompt, project instruction files, or the skills catalog unless `systemPromptMode: append`, `inheritProjectContext: true`, or `inheritSkills: true`.

Tool selection: omitting `tools` gives Pi's normal builtins; an explicit list is a strict allowlist; an empty field emits `--no-tools`. Allowlisting a name does not load the extension that registers it — load it through normal discovery, `extensions`, `subagentOnlyExtensions`, or a path-like `tools` entry. `mcp:` entries select direct MCP tools (uses the loaded `pi-mcp-adapter` first; without it, Pi 0.99 native MCP supports `mcp:server` and `mcp:server/tool`. A global adapter `directTools: true` is not sufficient, and an `mcp:` entry named `subagent` does not authorize nested fanout). Children never get the `subagent` tool unless their resolved builtin `tools` explicitly includes it. Missing providers fail the run before the first model turn.

`excludeTools` removes names after tool resolution and can narrow the default tool set without replacing it. Unknown names are ignored; exact runtime-tool names must be excluded explicitly.

Per-agent memory (`memory: { scope: "project" | "user", path }`) injects the first 200 lines of `MEMORY.md` from `<project>/.pi/agent-memory/<path>` or `~/.pi/agent/agent-memory/<path>` into the child prompt. Agents with write tools are told they may append dated entries; read-only agents get a read-only block. Paths are validated against traversal and symlink escape, and the directory is created lazily by the agent's own `write`.

### Refinement Overlays

`/subagents-refine <agent>` (or `{ action: "refine" }`) layers bounded project-local guidance on one agent's system prompt without editing its file. It collects bounded evidence from that agent's recent project runs, then launches a fresh read-only proposal child to draft small guidance edits. Proposals are validated first — edits attempting to override safety, policy, tool, output, acceptance, developer, or system instructions are rejected, as are edits targeting all agents or base agent files. The overlay lands at `.pi/subagents/refinements/<agent>.md` with revision metadata and snapshots, and is injected at launch as a `<pi-subagents-refinement>` block scoped to the project. `refine.show` prints the overlay and history; `refine.rollback` restores the previous revision; deleting the file removes the refinement.

## Settings

`~/.pi/agent/settings.json` or `.pi/settings.json` (project wins):

```json
{
  "subagents": {
    "defaultModel": "deepseek-v4-flash",
    "defaultThinking": "medium",
    "defaultExtensions": [],
    "disableThinking": false,
    "disableBuiltins": false,
    "projectRootResolution": "git-root",
    "agentOverrides": {
      "reviewer": { "model": "anthropic/claude-sonnet-4", "thinking": "high", "fallbackModels": ["openai/gpt-5-mini"] }
    },
    "watchdog": { "enabled": true, "main": { "model": "anthropic/claude-opus-4-8", "thinking": "high" } },
    "modelScope": { "enforce": true, "strict": true, "allow": ["anthropic/*", "openai/gpt-5-*"] }
  }
}
```

Model precedence, strongest first: per-run override → agent frontmatter `model` → `agentOverrides.<name>.model` → `subagents.defaultModel` → the parent session model.

Override fields: `description`, `model`, `fallbackModels`, `thinking`, `systemPromptMode`, `inheritProjectContext`, `inheritSkills`, `defaultContext`, `acceptanceRole`, `disabled`, `skills`, `tools`, `systemPrompt`, `extensions`. Use `false` to clear an inherited `defaultContext`/`acceptanceRole`, and `tools: "inherit"` on a builtin to drop its bundled allowlist for Pi's normal builtins. Matching user and project agents also receive override fields their frontmatter leaves unset. `disableThinking: true` clears bundled builtin thinking defaults for providers that reject `:level` suffixes.

`modelScope.allow` supports the `scoped` token for the parent Pi model scope (unscoped means `inherit`) and is glob-matched (only `*` is special, case-insensitive) against the resolved `provider/id`. Explicitly passed models that match nothing error and abort; models from frontmatter, `defaultModel`, the inherited session model, or fallback chains only warn — unless `strict: true`, which rejects every out-of-scope resolved model and fails the run on an invalid fallback. `enforce: true` requires a non-empty `allow`.

`projectRootResolution` defaults to `"nearest"` (nearest parent with `.pi` or `.agents`); set `"git-root"` in the repository root `.pi/settings.json` so monorepos and worktrees anchor package discovery, project agents, and `agentOverrides` at the git worktree root.

Recommended model tiering: a cheap model at low thinking for recon/mechanical edits, a mid-tier at medium for most delegations, a top reasoning model at high only for hard tasks arriving with explicit completion criteria (they loop on vague goals), and an intent-reading model for ambiguous UX/product/planning work. Give intent-tier agents cross-provider `fallbackModels` so subscription limits degrade gracefully; fresh context limits inherited assumptions; current fork sanitization removes signed thinking without disabling new reasoning.

Profiles live in `~/.pi/agent/profiles/pi-subagents/` and cached provider catalogs in `.../providers/`. Workflow: `/subagents-refresh-provider-models <provider>` → `/subagents-generate-profiles <provider>` → `/subagents-load-profile <provider>.quota`; `/subagents-check-profile` re-checks assigned models against the registry and a live probe.

## Extension Config

`~/.pi/agent/extensions/subagent/config.json`:

| Key | Notes |
|---|---|
| `toolDescriptionMode` | `full` (default), `compact`, or `custom` (reads `subagent-tool-description.md`; safety guidance is always retained) |
| `legacyChainControls` | Default `false`; enables the legacy `append-step`/checkpoint schema |
| `inlineToolDisplay` | `"rich"` default, or `"summary"` for one stable row per run |
| `mainWindowRenderer` | `{ horizontalSpacing: 0–4, compactResultMaxLines }` for the chat call/result renderer only |
| `foregroundDetachShortcut` | Optional detach shortcut (e.g. `"ctrl+b"`; conflicts with Pi's editor cursor-left binding) |
| `asyncByDefault` | Default `true`; `false` restores foreground-by-default for the internal single-run primitive |
| `forceTopLevelAsync` | Forces depth-0 runs into background and `clarify: false` |
| `fleetView`, `fleetViewPlacement`, `fleetKeybindings`, `asyncWidget` | FleetView display and inspector keys |
| `waitTool` | `{ enabled: false }` (or `false`) makes `bg_wait` return immediately without a subscription; `defaultTimeoutMs` sets the blocking window (fallback 30 minutes). `PI_SUBAGENT_WAIT_TOOL_ENABLED` overrides per process |
| `timeoutMs` | Global default deadline replacing the 30-minute backstop for foreground and plain single-agent async runs; composite async runs stay unbounded at the top level |
| `toolTimeoutMs` | Hard per-tool-call deadline. Without it, known-fast builtins (`read`, `grep`, `find`, `ls`, `edit`, `write`, `structured_output`) get five minutes; `bash`, custom, and MCP tools get attention notices only. `contact_supervisor`, `intercom`, and `bg_wait` are exempt |
| `globalConcurrencyLimit` | Default `20`; caps concurrent workflow and durable legacy children. A workflow-only per-call override is supported |
| `maxSubagentSpawnsPerSession` | Cumulative launches per parent session (unlimited by default); `grant-spawn-budget` adds capacity up to the original cap |
| `maxSubagentSpawnsPerRun` | Cumulative logical children in one run tree; default `64`. Claims are never refunded |
| `maxActiveAsyncRunsPerSession` | Concurrent top-level async runs (unset/`0` = unlimited); slots release only on terminal state plus observed process-terminal proof |
| `scheduledRuns` | `{ enabled, maxPending, storeRoot }` for durable schedules |
| `parallel` | `{ maxTasks: 8, concurrency: 4 }`; per-call `concurrency` wins |
| `defaultSessionDir`, `singleRunOutputBaseDir`, `artifactDir` | Session/output/artifact locations; `artifactDir` is `"session"` (default), `"project"`, or `"temp"` |
| `maxSubagentDepth` | Nesting limit when no `PI_SUBAGENT_MAX_DEPTH` applies; per-agent frontmatter can only tighten |
| `intercomBridge` | `{ mode: "always" \| "fork-only" \| "off", instructionFile, resultDelivery }` |
| `worktreeBaseDir`, `worktreeSetupHook`, `worktreeSetupHookTimeoutMs` | Worktree base dir and setup hook |
| `missions` | `{ enabled, directory, globalIndex, globalIndexDir, retainTerminal: 200 }` |
| `authorityPolicy` | Fixed action map of `auto`/`confirm`/`forbid` for `discardWorktree`, `destructiveCleanup`, `spawnBudgetGrant`, `scheduleCreate`, `stopRun`, `steerRun` |
| `completionBatch` | Smart batching of async-completion notices; failures and pauses bypass it |
| `permissions` | Native child tool permission rules (see below) |

Environment: `PI_SUBAGENT_MAX_DEPTH` (nesting; default 2), `PI_SUBAGENT_MAX_SPAWNS_PER_SESSION`, `PI_SUBAGENT_MAX_SPAWNS_PER_RUN`, `PI_SUBAGENT_TOOL_TIMEOUT_MS`, `PI_SUBAGENT_WAIT_TOOL_ENABLED`, `PI_SUBAGENT_PI_BINARY` (override the child Pi launch command), `PI_SUBAGENT_TASK_DELIVERY` (`auto` default writes tasks over 8000 chars to a temp `task.md`; `file` always does, for hosts whose EDR kills children with long argv), `PI_SUBAGENTS_WORKTREE_DIR`. `PI_SUBAGENT_DEPTH` is internal — do not set it.

The worktree setup hook runs once per created worktree with an absolute, `~/`, or repo-relative path (bare command names rejected). stdin is JSON with `repoRoot`, `worktreePath`, `agentCwd`, `branch`, `index`, `runId`, `baseCommit`; stdout must be one JSON object such as `{ "syntheticPaths": [".venv", ".env.local"] }`, whose worktree-relative paths are removed before diff capture. Tracked files can never be marked synthetic. Default timeout 30000 ms.

## Worktrees and Acceptance Gates

Set `worktree: true` on `runs.run`/`runs.all` items (or at the top level to make it the default, overridable per child with `worktree: false`) to give each writing child its own managed git worktree. Each branches from clean HEAD, journals ownership before launch, captures a patch and handoff manifest, then removes cleanly captured temporary worktrees and branches; the manifest path stays in the child's `artifactPaths`. Keep one writer when parallel writes are not intentionally isolated. `action: "worktree.discard"` requires the aggregate `handoffPath`.

```javascript
{ agent: "worker", task: "Implement the fix", acceptance: {
  level: "verified",
  criteria: ["Patch the bug without widening scope"],
  evidence: ["changed-files", "tests-added", "commands-run", "residual-risks", "no-staged-files"],
  verify: [{ id: "focused", command: "npm test", timeoutMs: 120000 }]
} }
```

Levels are `auto` (default), `none`, `attested`, `checked`, and `verified`; review is a separate gate under `acceptance.review`. Inference uses only declared `acceptanceRole`: `writer` gets checked evidence, plus required reviewer gating when async or dynamic; `read-only` gets none; an omitted role gets lightweight attestation. Task wording, perceived risk, and agent names do not change inference. The role does not grant or revoke tools.

`gate: "npm test"` is shorthand for one host-run verification command (`acceptance.level: "verified"` with that single command). Results are memoized per tracked workspace state and effective environment, so an unchanged tree does not rerun it; with `worktree: true` it runs inside the child's worktree. `gate` cannot combine with `acceptance` except deprecated `false`, and is rejected on retained `resume` items. Object gates `{ command, output: "json", schema?, timeoutMs? }` validate bounded stdout as structured output; they cannot coexist with `outputSchema`.

Evidence statuses: `claimed`, `attested`, `checked`, `verified` (runtime verification commands passed — child-reported success does not count), `review-required`, `reviewed`, `rejected`. Bare `"none"` is rejected (use `{ level: "none", reason }`); `"reviewed"` is not a settable policy level. For `attested` or stricter, the child prompt asks for a fenced `acceptance-report` JSON block; fences are stripped from output artifacts while per-child metadata keeps the full acceptance ledger. Explicit failed gates fail the run; inferred gates stay observable without failing it. Checked writers reject staged files by default. `preserveStagedIndex: true` explicitly permits a reviewed starting index only if its Git tree is unchanged at completion; it does not stage or restore anything and is unsuitable for concurrent writers sharing a worktree.

## Missions and Schedules

Ordinary workflow launches create one enclosing mission by default, stored under `~/.pi/agent/missions/projects/<project-hash>/` and linking objectives, run ids, lifecycle status, decisions, artifact paths, and delivery receipts. Children do not create separate missions. `details.missionId` is authoritative and human receipts end with `Mission: <id> (<status>)`. Pass `mission: false` for an ephemeral workflow with no mission and no `state` global, or `missions.enabled: false` to disable automatic creation (explicit fields and actions still work). Automatic persistence failures are reported as `details.missionWarning` without blocking the run; explicit `missionId`/`mission` requests are strict before launch.

An explicit `mission` object needs exactly one non-empty `title` or `summary` (`objective` and `labels` optional). `goal: true` requires `budget: { tokens }` and turns the mission into a continuation driver: after each parent turn an idle goal mission emits one needs-attention notice with its title, remaining budget, and next ready action (from `state.nextReadyAction`, `state.nextAction`, a ready state item, an open decision, or linked-run state). Reaching the budget sets `budget-exhausted` and stops notices. The extension never launches or replans goal work itself.

`state.get(key)` / `state.set(key, value)` give a workflow durable JSON state through its mission, shared across later workflows attached with the same `missionId`. Each `set` takes the state-file lock and merges with the latest on-disk state; missing keys return `undefined`, and the whole state file is capped at 256 KiB.

Durable schedules are enabled by default under `.pi/subagents/schedules/<id>/` (or `scheduledRuns.storeRoot`):

```javascript
{ action: "schedule.create", id: "evening-review", name: "Evening review", at: "+30m",
  workflow: "./workflows/review.js" }
{ action: "schedule.create", id: "backlog", every: "6h", catchUp: "latest", workflow: "./workflows/review.js" }
```

Fixed intervals support `m`/`h`/`d`/`w` and advance from the planned time without completion drift. Scheduled runs always launch async with fresh context and disable automatic mission creation. `overlap` is fixed to `skip`; `catchUp` supports `latest` (default) and `none`; `schedule.run-due` lets an external launcher start due work without making pi-subagents a daemon. Calendar/cron recurrence, queue/replace overlap, and a schedule TUI inspector are deferred.

For substantial work in another codebase, prefer a Herdr project pane (`project.open`) over ordinary child nesting; use an explicit `cwd` only for small bounded cross-project work.

## Watchdog and Child Permissions

The watchdog is an opt-in adversarial reviewer for repo edits — **not** the `reviewer` agent, and not configured by `defaultModel`/`agentOverrides.reviewer`. It runs at the `agent_end` boundary only when the repo's final state changed during the turn; multiple edits coalesce into one review, unchanged/reverted diffs are skipped, and `.pi/subagents/`/`tmp/` artifacts do not trigger it. In orchestrated runs each writing child can review its own worktree while the parent reviews the aggregate diff.

Use a strong complementary model: `/subagents-watchdog recommend-model` (inspect the installed recommendation and available authenticated models; avoid hardcoding a recommendation across releases). `session model recommended` changes only this session; `model recommended` saves to settings without enabling. Settings keys: `watchdog.main.model`/`.thinking` (omitting `main.model` uses the session model; setting it without a thinking suffix runs with thinking off), `watchdog.children.model`, `watchdog.children.overrides.<agent>.model`.

Scope monitoring keeps a bounded in-memory current-scope artifact from real user prompts and prepends it to review input (`watchdog.scope.enabled`), so the reviewer can flag `scope-drift`; newer prompts supersede older ones and watchdog auto-follow prompts are not recorded as scope. `watchdog.cadence.everyNTools` adds Scopey-style non-blocking reviews every N tool results, delivered transcript-visibly via `steer` after the current tool boundary — pick a cheap model for frequent monitoring. `watchdog.autoFollow` (`blockers`, `maxAttempts`, `stalemateRepeats`) can queue a visible follow-up asking the agent to address a blocker, stopping on repeated identical blockers.

LSP diagnostics: when enabled, the watchdog checks changed TypeScript/JavaScript files for fresh language-server diagnostics before the model review, auto-detecting `typescript-language-server` from `node_modules/.bin` or `PATH` (never installing anything or scanning the workspace). Errors become blockers, warnings concerns; bound with `watchdog.lsp.enabled`, `timeoutMs`, `maxFiles`, `maxDiagnostics`.

Native child permissions are opt-in and apply only to Pi child runtimes. Configure non-bash rules under `permissions.rules` in the extension config (`"read": "allow"`, `"write": "ask"`, `"edit": "deny"`), overridable by an agent's `permission:`/`permissions:` frontmatter block. Omitted and unknown tools default to `allow`, explicit `allow` removes an inherited restriction, and the gate is not registered when no `ask`/`deny` rule resolves. An `ask` pauses that exact call and sends a bounded, redacted preview to a one-call arbiter owned by the child watchdog, which returns only approve/deny — enable and configure `subagents.watchdog.children` first, since a disabled watchdog, missing model/auth, timeout, or malformed response denies the call. Decisions are written to bounded audit JSONL with `decisionSource: "watchdog"`. `bash` is always passed through and bash rules are rejected rather than parsed — use `pi-guard` for command-level policy. External CLI profiles are opaque processes, so a launch with effective `ask`/`deny` rules is rejected rather than claiming enforcement.

## Supervisor Coordination

Native, no `pi-intercom` required: children call `contact_supervisor({ reason, message })` with `reason` ∈ `need_decision`, `interview_request`, `progress_update`; the parent replies with `subagent_supervisor({ action: "reply", replyTo, message })` or checks `{ action: "pending" }`. Requests are scoped to the exact Pi session id that spawned the child, so a second Pi session in the same repository does not receive them. If no external `pi-intercom` owns the name, the native channel also exposes `intercom` as a compatibility fallback. A foreground child may detach while awaiting a reply: reply first, then `bg_wait({ id: runId })`. Children should not ask for clarification when the only conflict is review-only/no-edit versus progress- or artifact-writing instructions — no-edit wins.

Child-safety boundaries are enforced at runtime: spawned children never receive the bundled `pi-subagents` skill; forked child context is filtered to strip parent-only orchestration instructions, slash/status/control messages, and prior parent `subagent` tool history; and children get boundary instructions that they are not the orchestrator. The exception is an agent whose resolved builtin `tools` includes `subagent`, which gets a child-safe tool bounded by `maxSubagentDepth`.

## Observability

FleetView below the editor (or above, via `fleetViewPlacement`) keeps active work visible as a compact summary; with the editor empty, `↓`/`←` expands it into `main` plus active children with agent, state, elapsed time, and token totals, `↑↓`/`jk` selects, and `Enter` inspects. `/subagents-fleet` opens the live inspector: `Shift+K`/`Shift+J` scroll a line, `PgUp`/`PgDn` a page, `x`/`Ctrl+O` toggle tool details, `r` refresh, `Esc` close, `s` compose an acknowledged message to a live async child (Tab cycles `steer`/`follow_up`/`auto`), `D` stop after confirmation, `H` open a Herdr inspector pane (Herdr 0.7.5+). `Ctrl+Alt+F` opens it mid-turn. Successful background completions stay quiet so inactive tabs are not marked unread; failures and pauses notify immediately.

Async runs write lifecycle artifacts under `<tmpdir>/pi-subagents-<scope>/async-subagent-runs/<id>/`: `status.json`, `events.jsonl`, `output-<n>.log`, `subagent-log-<runId>.md`, with the final summary as `<runId>.json` in Pi's results directory (`details.asyncDir` points at the run directory). Stable v1 status fields: `lifecycleArtifactVersion`, `runId`/`id`, `sessionId`, `mode`, `state`, timestamps, `durationMs`, `cwd`, `asyncDir`, `sessionFile`, `outputFile`, `workflowGraph`, `steps`, `results`, `totalTokens`, `totalCost`, `model`/`attemptedModels`/`modelAttempts`, `toolCount`, `turnCount`, optional `launchResolvedExtensions` and `runtimeAcknowledgedExtensions`, and nested `children`. Read these files rather than scraping terminal output, and ignore unknown fields.

The result file is consumed and deleted once its completion notice is delivered; before deletion the watcher writes a versioned replay record under `<resultsDir>/completion-replay/<runId>.json` and a bounded output archive under `<resultsDir>/output-archives/<runId>.json` (64 KiB of result tail when no child output/session file exists). `bg_wait` surfaces a slim projection in `details.completions`. Lifecycle artifact v3 adds `process-terminal-candidate.json` and `process-terminal.json`; a proof is `observed` only when the live parent saw the runner's `close` event, every recorded child writer has a close record, and any tracked session lease is free — otherwise `unknown`. Never infer exit from `endedAt`, result-file existence, PID disappearance, or lease absence.

Child-protocol bounds: a child JSONL line above 16 MiB fails with `protocolError` code `protocol_output_limit` (oversized `turn_end`/`agent_end` aggregates are replaced with bounded lifecycle records while preserving `agent_end.willRetry`); stderr retains its latest 128 KiB; `agent_settled` is the terminal watermark on current Pi builds.

Debug artifacts live under `{sessionDir}/subagent-artifacts/`, `.pi/subagents/artifacts/` for project-scoped runs, or a temp dir: `{runId}_{agent}_input.md`, `_output.md`, `.jsonl`, `_meta.json` (timing, usage, exit code, final/attempted models, fallback outcomes, resolved acceptance ledger). For npm package projects, project-scoped artifacts need a `.npmignore`/`files` rule — pi-subagents warns when package settings could publish `.pi/subagents/`.

## Extension Integration

Versioned in-process event-bus RPC: listen for `subagents:rpc:v1:ready`, emit on `subagents:rpc:v1:request` (`{ version: 1, requestId, method, params }`), read `subagents:rpc:v1:reply:<requestId>`. Methods: `ping`, `status`, `cost`, `spawn` (inline `script` or a `workflow` path/resource, async-only), `steer`, `interrupt`, `stop`, `resume`. `cost` returns versioned parent/child spend plus `unresolvedAsyncChildren`; unresolved usage is not zero. `ping.capabilities` advertises `events.asyncComplete`, `launchResolvedExtensions`, `runtimeAcknowledgedExtensions`, `processTerminalProof`, `nonRecoveringSteer`, `resume`, and `fleetStatus: { version: 1 }` (successful `status` replies then include a bounded `data.fleet` DTO that never exposes run, async, or tool IDs). RPC steering disables pause-and-revive recovery so the caller keeps authority over the child it spawned.

Also exported:

- `pi-subagents/preflight` — `resolveSubagentLaunchContract(...)` resolves an ordinary single-agent launch contract side-effect-free (agent identity and shadowed candidates, parsed-definition digest, context/model/tools/skills/MCP/extensions, artifact and async paths, capability-ceiling audit data, `launchContractDigest`). Failure codes: `missing_agent`, `ambiguous_agent`, `missing_skill`, `denied_required_tool`, `invalid_artifact_dir`, `invalid_cwd`, `unsupported_mode`; host-only facts appear as `host_required` diagnostics.
- `pi-subagents/delegation` — `SUBAGENT_DELEGATION_REQUEST_EVENT` / `SUBAGENT_DELEGATION_RESPONSE_EVENT` run one configured foreground leaf agent. `ownerRunId` + `nodeId` is the logical identity (`requestId` is one attempt; a second active attempt gets `duplicate_node`), result mode is explicit (`text` stays literal, `structured` returns schema-validated JSON), schemas cap at 64 KiB and values at 1 MiB. Foreground-only; requires an active extension context.
- `pi-subagents/capability-ceiling` — `registerSubagentCapabilityCeiling({ sessionId, source, ceiling })` enforces a session-scoped ceiling (`allowedAgents`, `allowedTools`, `denyExtensions`). Active registrations intersect allowlists and OR `denyExtensions`; non-allowlisted agents fail before spawn and stay visible in `list` as non-executable; the snapshot propagates monotonically to nested/async children.
- `pi-subagents/background-work` — `registerBackgroundWorkProvider({ name, wakeChannels, listActiveWork, reconcile })` makes another extension's jobs visible to `bg_wait`, keyed by stable provider-local id plus owning session id.
- `pi-subagents/project-panes` — `PROJECT_PANES_API_VERSION` (currently `1`), `openProjectPane`, `getProjectPaneStatus`, `closeProjectPane`.

Bus events: `subagent:async-started` (payload includes truncated `task` and workflow-level `goal`), `subagent:async-complete`, `subagent:control-intercom`, `subagent:result-intercom`, `subagent:process-terminal`, plus child-emitted `subagent:acknowledge-extension`. `pi.events` is in-process only — use file artifacts or `pi-intercom` across processes.

Herdr integration: when `HERDR_ENV=1` and `HERDR_PANE_ID` are set, pi-subagents reports active async-run counts through pane metadata, emits `herdr:blocked`/`herdr:busy`, and restores state after `/reload` or `/resume`. Herdr 0.7.5+ adds on-demand inspector panes (`inspector.open/status/close`, a raw dashboard reading lifecycle artifacts — closing it never stops the run) and project panes (`project.open/status/close`, a Pi session rooted in another repo that owns its own subagents; bindings at `<projectRoot>/.pi/subagents/project-panes/herdr.json`).

## Skills and the Bundled Skill

Skills are `SKILL.md` files selected per agent; discovery is project-first (project config `skills/`, project/task packages, project settings, `~/.pi/agent/skills/`, user packages, user settings). Set them via agent defaults, per-run `skill: "tmux, safe-bash"`, or `skill: false`; top-level `skill` in a chain is additive and a step-level value overrides. Missing skills warn instead of failing. When an agent has an explicit `tools` allowlist plus resolved skills, `read` is added so skill files can be loaded. Agent-local `skillPath` candidates never enter Pi's global catalog — pair `inheritSkills: false` with explicit `skills` and `skillPath` for a child that should receive only its private skills.

The package bundles a `pi-subagents` skill for the **orchestrating parent only**, covering delegation patterns, prompt-workflow recipes, role-agent prompting, safety boundaries, intercom conventions, and control/diagnostics.

## External CLI Runners

An agent profile can run a local one-shot command instead of a Pi child:

```yaml
runner:
  type: external-cli
  command: node
  args: ["./scripts/local-reviewer.mjs"]
  promptDelivery: stdin
async: true
```

They are async-only, receive one combined system/task prompt over stdin, and use argv arrays without a shell. Supported: status artifacts, stdout/stderr logs, timeout, stop (full output goes to log files; in-memory final stdout/stderr keep the last 64 KiB). Not supported: foreground/clarify, steer/resume/interrupt-as-pause, Pi models/tools/extensions, skills, structured output, nested subagents, fallback models, and native permission enforcement.

## Recursion Guard

Subagents can call `subagent` only when their resolved builtin tools explicitly include it — intended for delegated fanout agents, not ordinary workers or reviewers. Nesting defaults to two levels (main → subagent → sub-subagent); deeper calls are blocked with guidance to finish directly. Nested runs appear in the parent status tree, and `status`, `interrupt`, and `resume` can target one by its nested id. Configure with `PI_SUBAGENT_MAX_DEPTH`, `config.maxSubagentDepth`, or agent frontmatter (which can only tighten).

## Session Sharing

`share: true` exports the full session to HTML, uploads it to a secret GitHub Gist through your `gh` credentials, and returns a `https://shittycodingagent.ai/session/?<gistId>` URL. Disabled by default — session data may contain source code, paths, environment variables, or credentials.


## Upgrade and capability boundaries

Current configuration can set `disabledFeatures` to remove tool feature groups. Disabling `workflow-scripts` replaces scripts with top-level `tasks` (parallel) and `chain` (sequential/parallel blocks); those forms are otherwise not the public execution API. `scheduledRuns.enabled: false` also removes scheduling fields.

Children follow parent project trust. Adapter MCP selectors read `mcp-adapter.json`; native selectors read Pi `mcp.json`. Native extension-registered MCP servers work in background children. `codemode` is available to child tools when allowed, but `subagent`, `subagents_enable`, supervisor/contact, and structured-output tools are model-only and cannot be invoked inside codemode.

A runtime replacement (`/reload`/resume/project switch) marks an async workflow stopped with `workflow.stopCause: "runtime-replaced"` while its awaited async children continue. Relaunching the same script and JSON args in that session can reuse successfully finished or still-running keyed children; failures rerun. A completed/user-stopped workflow does not grant this reuse. Check workflow receipts and terminal proof instead of interpreting successful dispatch as delivered work.

All authenticated child launches are illustrative. This audit loaded the extension, validated both documented workflow bodies, executed the first with mocked child results, and checked nested-async rejection. It did not bill hosted child/watchdog calls or execute worktree, schedule, supervisor, Herdr, or sharing flows.
