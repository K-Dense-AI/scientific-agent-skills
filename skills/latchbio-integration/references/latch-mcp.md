# Latch MCP

Latch provides a remote Model Context Protocol server:

```text
https://mcp.latch.bio/mcp
```

It lets compatible AI clients discover workflows and interact with Latch Data
and executions through an OAuth-authorized tool surface.

## Authentication Boundary

- A Latch account is required.
- MCP uses OAuth in the connected AI client.
- MCP authorization does not authenticate the Latch SDK, CLI, or Console.
- SDK login credentials do not replace MCP authorization.
- Actions launched through MCP incur the same normal Latch charges as the
  corresponding Console or SDK action.

Never copy OAuth tokens between these authentication domains.

## Setup

### Cursor

Add:

```json
{
  "mcpServers": {
    "LatchBio": {
      "url": "https://mcp.latch.bio/mcp"
    }
  }
}
```

Then open **Cursor Settings → Tools & MCP(s)**, select LatchBio, click
**Connect**, and complete OAuth.

### Claude Code

```bash
claude mcp add --transport http latchbio https://mcp.latch.bio/mcp
```

Run `/mcp` and complete OAuth.

### Codex

```bash
codex mcp add latchbio --url https://mcp.latch.bio/mcp
codex mcp login latchbio
```

For another MCP client, configure the same remote HTTP URL and follow that
client's OAuth flow.

## Documented Tools

The current guide lists:

| Tool | Purpose |
|---|---|
| `list_files` | List immediate children of a Latch Data directory |
| `list_workspaces` | List accessible workspaces and the default |
| `list_workflows` | Discover workspace and public workflows |
| `get_workflow_schema` | Retrieve launch metadata and parameter schema |
| `launch_workflow` | Launch with schema-compatible values |
| `list_executions` | Filter executions by workspace, workflow, name, or status |
| `get_execution` | Get status, task nodes, result files, and Console URL |
| `get_task_logs` | Get inline logs or a signed URL for complete logs |

Tool names and schemas can evolve. Discover the connected server's current
tools before calling them.

## Safe Launch Workflow

1. **Select a workspace**
   - Call `list_workspaces`.
   - Prefer the default only when it is clearly the intended target.

2. **Discover rather than guess**
   - Call `list_workflows`.
   - Identify the exact workflow and version.

3. **Fetch the schema**
   - Call `get_workflow_schema`.
   - Use returned types, required values, enums, defaults, and path rules.

4. **Resolve data**
   - Use `list_files` only for the minimum directories needed.
   - It lists metadata, not file contents.
   - Do not browse unrelated or sensitive directories.

5. **Prepare a launch summary**
   - Workspace
   - Workflow and version
   - Input paths and parameters
   - Output destination
   - Expected resource/cost implications

6. **Confirm**
   - Obtain user approval before launching paid compute.
   - Reconfirm unusually large, GPU, or fan-out workloads.

7. **Launch**
   - Call `launch_workflow` once.
   - Preserve the returned execution identifier and Console URL.

8. **Monitor**
   - Poll with `get_execution`.
   - Use `get_task_logs` only for relevant nodes.
   - Avoid repeatedly downloading full logs when an inline excerpt is enough.

## Example Agent Plan

```text
list_workspaces
→ choose workspace 12345
→ list_workflows
→ choose Bulk RNA-seq version X
→ get_workflow_schema
→ validate sample paths and output directory
→ present launch summary and request confirmation
→ launch_workflow
→ get_execution until terminal status
→ get_task_logs only if a task fails
```

## Cost and Data Safety

- Listing resources is read-only; launching is not.
- Do not launch during exploratory discovery.
- Do not expose signed log URLs; they may grant temporary access.
- Do not paste secrets into workflow parameters.
- Confirm paths belong to the selected workspace.
- Avoid broad file listing when exact paths are already known.
- Stop polling after a terminal state.
- Scientific validation still requires inspecting outputs and method
  assumptions after orchestration succeeds.

## When MCP Is Unavailable

Use:

- Latch Console for interactive discovery and launch
- `latch_cli.services.launch.launch_v2` for Python automation
- `latch ls` or `LPath` for data inspection
- Latch Console for execution monitoring; `latch get-executions` remains in
  2.76.8 but is deprecated and scheduled for removal

Do not simulate a missing MCP tool by inventing undocumented HTTP endpoints.

## Official Source

- Latch MCP guide: https://wiki.latch.bio/agent/latch-mcp
