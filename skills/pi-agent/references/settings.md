# Settings

Source: https://pi.dev/docs/latest/settings

Pi uses JSON settings files. Project settings override global settings; nested objects merge.

| Location | Scope |
|---|---|
| `~/.pi/agent/settings.json` | Global |
| `.pi/settings.json` | Project |

## Project Trust

Project settings are trust-gated. Interactive startup asks according to `defaultProjectTrust` when project inputs exist and no saved trust decision applies. Non-interactive modes use `defaultProjectTrust` and do not prompt. `--approve` and `--no-approve` override for one run.

## Core Settings

Model/thinking: `defaultProvider`, `defaultModel`, `defaultThinkingLevel`, `hideThinkingBlock`, `thinkingBudgets`.

UI/display: `theme`, `quietStartup`, `defaultProjectTrust`, `collapseChangelog`, `enableInstallTelemetry`, `doubleEscapeAction`, `treeFilterMode`, `editorPaddingX`, `autocompleteMaxVisible`, `showHardwareCursor`.

Compaction: `compaction.enabled`, `compaction.reserveTokens`, `compaction.keepRecentTokens`.

Branch summary: `branchSummary.reserveTokens`, `branchSummary.skipPrompt`.

Retry: `retry.enabled`, `retry.maxRetries`, `retry.baseDelayMs`, `retry.provider.timeoutMs`, `retry.provider.maxRetries`, `retry.provider.maxRetryDelayMs`.

Message delivery: `steeringMode`, `followUpMode`, `transport`, `httpIdleTimeoutMs`, `websocketConnectTimeoutMs`.

Terminal/images: `terminal.showImages`, `terminal.imageWidthCells`, `terminal.clearOnShrink`, `images.autoResize`, `images.blockImages`.

Shell: `shellPath`, `shellCommandPrefix`, `npmCommand`.

Sessions: `sessionDir`; precedence is `--session-dir`, `PI_CODING_AGENT_SESSION_DIR`, then setting.

Resources: `packages`, `extensions`, `skills`, `prompts`, `themes`, `enableSkillCommands`.

## Network/Telemetry

`enableInstallTelemetry` only controls anonymous install/update ping. Use `PI_SKIP_VERSION_CHECK=1` to disable version checks. Use `--offline` or `PI_OFFLINE=1` to disable startup network operations including update checks, package update checks, and install/update telemetry.

## Example

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-5",
  "defaultThinkingLevel": "medium",
  "theme": "dark",
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  },
  "retry": { "enabled": true, "maxRetries": 3 },
  "enabledModels": ["claude-*", "gpt-4o"],
  "packages": ["pi-skills"]
}
```
