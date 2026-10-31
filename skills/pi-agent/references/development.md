# Development

Source: https://github.com/earendil-works/pi/tree/v0.99.2 (README.md, CONTRIBUTING.md, AGENTS.md, package.json and pi-test.sh; development is no longer a current docs page)

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Use this when working on Pi itself.

## Setup

```bash
git clone https://github.com/earendil-works/pi
cd pi
npm install
npm run build
```

Run from source:

```bash
/path/to/pi/pi-test.sh
```

The script can be run from any directory and preserves the caller's cwd.

## Forking and Rebranding

Configure `package.json`:

```json
{
  "piConfig": {
    "name": "pi",
    "configDir": ".pi"
  }
}
```

Change `name`, `configDir`, and `bin` for a fork. This affects CLI banner, config paths, and environment variable names.

## Path Resolution

Pi has npm install, standalone binary, and Node type-stripping source execution modes. Always use `src/config.ts` helpers such as `getPackageDir` and `getThemeDir` for package assets. Do not use `__dirname` directly for assets.

## Debugging and Tests

`/debug` writes rendered TUI lines and last LLM messages to `~/.pi/agent/pi-debug.log`.

```bash
npm run check
./test.sh
npm test
npm --prefix packages/coding-agent test -- test/specific.test.ts
```

These are upstream developer commands, not commands executed by this review. `npm run check` includes formatting writes, and the full test/build workflows can use native tools or network services. For a targeted test, run from the owning package.

## Project Structure

```text
packages/
  ai/            # LLM provider abstraction
  agent/         # Agent loop and message types
  tui/           # Terminal UI components
  coding-agent/  # CLI and interactive mode
  codemode/      # QuickJS tool composition
  mcp/           # Native MCP clients
  protocol/      # Shared wire definitions
  client/        # Client integration
  server/        # Server integration
```
