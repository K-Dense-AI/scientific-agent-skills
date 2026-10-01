# Running the upstream Arbor CLI

This skill's bundled `tree.py` is a standard-library bookkeeping helper driven
by the current host agent. The separate upstream runtime supplies its own
coordinator, executors, checkpoints, dashboard and Git/evaluation tools.
Their state files are **not interchangeable**.

Reviewed on 2026-09-30 against [arbor-agent 0.1.4](https://pypi.org/project/arbor-agent/0.1.4/)
and [upstream commit 7cdaf1fa](https://github.com/RUC-NLPIR/Arbor/tree/7cdaf1fa6d779b3d5e340052357bf3fe55dfed93).
The Python distribution is `arbor-agent`; `arbor` on PyPI is an unrelated
neuroscience simulator. Both use the import name `arbor`, so keep them in
separate environments.

## Install

Python 3.10+ and Git are required. The built-in alphaXiv search dependency
requires Python 3.12+, so use 3.12+ when that feature is needed. The native
runtime requires model access; the bundled helper requires no provider key.

```bash
uv tool install arbor-agent==0.1.4
arbor version
arbor doctor
```

The equivalent isolated verification command is
`uv run --isolated --no-project --with arbor-agent==0.1.4 arbor version`.
For source development, clone [RUC-NLPIR/Arbor](https://github.com/RUC-NLPIR/Arbor),
record the commit, and install it into a dedicated virtual environment.

`doctor` checks local installation, Git and credential/config presence. It does
not authenticate a key or probe model availability; even a missing-key warning
can accompany exit code 0. See its [implementation](https://github.com/RUC-NLPIR/Arbor/blob/7cdaf1fa6d779b3d5e340052357bf3fe55dfed93/src/cli/commands/doctor_cmd.py).

## Configure a native run

```bash
arbor setup
```

This writes `~/.arbor/config.yaml`. Current setup choices include `auto`,
`openai-responses`, `openai-chat` and `anthropic`; `auto` may probe an endpoint
and make a model request. Use the provider's configured environment credential
(such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) or the setup flow, without
committing credentials. Compatibility with a proxy depends on its supported
protocol; a base URL alone does not establish Responses/tool support.

The upstream prose configuration guide still lists legacy names such as
`openai` and `litellm`. For this release, prefer the current
[setup implementation](https://github.com/RUC-NLPIR/Arbor/blob/7cdaf1fa6d779b3d5e340052357bf3fe55dfed93/src/cli/commands/setup_cmd.py)
and [example configuration](https://github.com/RUC-NLPIR/Arbor/blob/7cdaf1fa6d779b3d5e340052357bf3fe55dfed93/examples/research_config.example.yaml).
No provider endpoint was exercised during this skill review.

Prepare a clean Git project with a runnable evaluator and explicit development,
gate and final-assessment protocols. A small project `research_config.yaml`
can use the following shape (parsed locally with 0.1.4; the actual experiment
and evaluator are supplied through intake):

```yaml
max_cycles: 3
executor_max_turns: 10
ui:
  interaction_mode: review
```

`max_cycles` limits completed/skipped/failed experiments in the upstream CLI;
it is different from the bundled helper's coordinator-cycle counter.
`--max-turns` caps coordinator turns, while `executor_max_turns` controls an
executor. Do not interpret `merge_threshold: 5.0` as an enforced 5% held-out
gain: the current config describes it as an LLM guideline, and the paper's
Table 6 describes a development-gain threshold for invoking the gate.
Verify the actual candidate/baseline gate evidence before reporting admission.

```bash
arbor --cwd ./benchmark --config ./research_config.yaml --max-cycles 3
```

This starts intake and can launch a real, paid research run after the native
runtime's contract flow; it is **not** a dry run. Set evaluator, protected
files, metric direction, resource limits and Git destination in the contract.
The runtime keeps per-experiment worktrees and a per-run trunk. Promotion of
that trunk into the project's main branch is a separate Git operation.

## Commands and outputs

| Command | Contract |
|---|---|
| `arbor` / `arbor run` | Begin intake and a native research session |
| `arbor setup` | Configure model/provider access |
| `arbor doctor` | Local diagnostics; not an authenticated service test |
| `arbor version` | Print the installed distribution version |
| `arbor report <session> --cwd <project>` | Rebuild `REPORT.md` from a path or session name |
| `arbor replay --demo --html --out demo.html` | Export a bundled recorded run without calling a model |
| `arbor install` | Install upstream's separate `arbor-*` skill suite |
| `arbor mcp` | Run keyless deterministic tools; needs the `arbor-agent[mcp]` extra |
| `arbor web <session>` | Serve a read-only session monitor |

Default native outputs are under `<project>/.arbor/sessions/<run_name>/`:
`REPORT.md`, `events.jsonl`, checkpoint/tree data, and a redacted resolved
configuration at `.coordinator/config_snapshot.yaml`. See the
[output documentation](https://github.com/RUC-NLPIR/Arbor/blob/7cdaf1fa6d779b3d5e340052357bf3fe55dfed93/docs/outputs-and-resume.md).
A report can render from incomplete or empty session data; its existence is
not evidence that any experiment succeeded.

Upstream also offers a keyless host integration (`arbor install` plus optional
`arbor mcp`) that uses the host agent's model rather than making its own model
calls. Installing that suite changes the host's skill inventory; it is optional
and does not replace this collection's helper automatically.

## Verification boundaries

The isolated installed release passed command help/version checks, parsed the
configuration above, rendered a synthetic partial report, and exported the
bundled replay to HTML. Model setup, autonomous experiment dispatch, live
provider requests, MCP registration and runtime Git merges were source-reviewed
only, not executed. This skill does not claim reproduction of the paper.
