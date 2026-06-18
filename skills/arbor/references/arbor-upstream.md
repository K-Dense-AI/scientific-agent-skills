# Running the standalone Arbor CLI (upstream tool)

This skill normally runs HTR **natively** — Claude is the coordinator and
subagents are executors. That's the recommended path: no extra install, no
separate API keys, and you stay in the loop to read evidence between cycles.

But the paper's authors also ship a full implementation as a CLI. Use it instead
when the user explicitly wants to run *the published system* (e.g. to reproduce
paper results), wants Arbor to run fully unattended for many hours via its own
live dashboard, or wants its built-in report/web-UI tooling.

Source: https://github.com/RUC-NLPIR/Arbor

## Install

Requires Python ≥ 3.10 and Git.

```bash
git clone https://github.com/RUC-NLPIR/Arbor.git
cd Arbor
python -m venv .venv && source .venv/bin/activate
pip install -e .
arbor doctor      # verify install, PATH, git, API keys
```

## Configure provider/model/keys

```bash
arbor setup       # writes ~/.arbor/config.yaml (provider, model, base URL, keys)
```

Supported backends: Anthropic, OpenAI / OpenAI-compatible Responses API, and
LiteLLM (DeepSeek, Gemini, Qwen, vLLM, Ollama, local gateways). Keys can also be
set via environment variables.

## Run

1. Prepare a benchmark directory: an initial artifact under a **clean git repo**
   plus an evaluation script (your `E_dev` / `E_test`).
2. Author a project `research_config.yaml` (task description, coordinator
   settings — max cycles, depth, merge thresholds — executor max turns, UI mode).
   See `examples/research_config.example.yaml` in the repo.
3. Start the interactive session:
   ```bash
   arbor
   ```
   Arbor runs an intake conversation, forms a Research Contract, then a live
   dashboard takes over. Each experiment runs in an isolated git worktree;
   verified improvements merge into a per-run trunk.
4. Outputs land in `.arbor/sessions/` with `REPORT.md`, the event log, and
   results. Re-render a past session's report with `arbor report <session>`.

## Key CLI commands

| Command | Purpose |
|---|---|
| `arbor` | Start an interactive research session |
| `arbor setup` | Configure provider / model / keys |
| `arbor doctor` | Diagnose install, PATH, git, API keys |
| `arbor report <session>` | Re-render reports for a past session |
| `arbor version` | Print installed version |

## Codebase map (for the curious / for debugging)

The implementation lives under `src/` (a src-layout; the CLI installs as
`arbor`). The package directories are:
- `core/` — ReAct loop, tools, LLM providers, context management
- `coordinator/` — coordinator agent, the tree, orchestrator, coordinator tools
- `executor/` — executor agent and CLI
- `cli/` — intake, live dashboard, setup, doctor, config
- `events/` — typed event bus and payloads
- `report/`, `webui/` — report generation and read-only run monitor
- `search_agent/` — the minimal ReAct search harness (the `M_0` for the
  BrowseComp / search-agent tasks)
- `plugins/` — domain plugins (e.g. `mle_kaggle.yaml`)
- `skills/` — on-demand markdown playbooks

(top-level `src/` also has `dashboard.py`, `run.py`, `review.py`.)

**Naming note:** the paper and this skill call the persistent state the
**hypothesis tree**; the tool's code and dashboard call the same structure the
**Idea Tree**. They are the same thing. The depth convention also matches the
native skill: root/depth 0 = objective + global insights, depth 1 = research
directions, depth 2+ = concrete tested methods.

## Native vs. upstream — quick guide

- **Native (this skill)**: best default. Lower setup, transparent, you read and
  steer between cycles, reuses your existing Claude Code session and worktrees.
- **Upstream CLI**: choose for paper reproduction, long unattended runs with the
  official dashboard, or when the user specifically asks for the `arbor` tool.
