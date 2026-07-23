# MCP Server and Plugin System

## Official MCP Package

The Microsoft monorepo publishes `markitdown-mcp`. As of July 23, 2026, the package version is `0.0.1a4`; it depends on `markitdown[all]>=0.1.1,<0.2.0`.

Pin both packages to ensure the documented converter version:

```bash
uv pip install \
  "markitdown==0.1.6" \
  "markitdown-mcp==0.0.1a4"
```

The server exposes exactly one tool:

```text
convert_to_markdown(uri: str) -> str
```

Accepted URI schemes are `http:`, `https:`, `file:`, and `data:`.

## Transport Modes

### STDIO

STDIO is the default and preferred local transport:

```bash
markitdown-mcp
```

Generic MCP client configuration:

```json
{
  "mcpServers": {
    "markitdown": {
      "command": "markitdown-mcp",
      "args": []
    }
  }
}
```

The MCP client launches the server with the same filesystem and network permissions as the client process unless additional sandboxing is applied.

### Streamable HTTP and SSE

```bash
markitdown-mcp --http --host 127.0.0.1 --port 3001
```

Endpoints:

- Streamable HTTP: `http://127.0.0.1:3001/mcp`
- SSE: `http://127.0.0.1:3001/sse`

`--sse` is a deprecated alias for `--http`.

## MCP Security Model

The server:

- Has no authentication
- Runs with the current user's privileges
- Can read files accessible to that user through `file:` URIs
- Can fetch network resources accessible to that process
- Accepts broad URI input with no built-in application allowlist

Requirements:

1. Prefer STDIO.
2. Keep HTTP/SSE bound to `127.0.0.1` or `localhost`.
3. Never expose it on `0.0.0.0`, a LAN interface, or the public Internet without a separately designed authenticated gateway and strict input policy.
4. Run it in a container, VM, or sandbox when processing agent-controlled URIs.
5. Mount only the required input directory, preferably read-only.
6. Deny sensitive network ranges and metadata endpoints.
7. Do not give the server access to home-directory secrets, SSH keys, cloud credentials, or broad research storage.

Localhost is not authentication: other processes or users on the same machine may still reach the port.

## MCP Plugins

The MCP process disables MarkItDown plugins by default. It enables them only when the named variable is explicitly set to a truthy value:

```bash
MARKITDOWN_ENABLE_PLUGINS=true markitdown-mcp
```

Do this only for installed, reviewed plugins. Enabling plugins loads Python entry points into the server process, expanding both code-execution and file/network capabilities.

## Container Isolation

The official guide recommends Docker for desktop-agent use. A secure deployment should:

- Build from a reviewed, pinned `v0.1.6` source checkout.
- Run as a non-root user.
- Mount a narrow input directory read-only.
- Use a read-only root filesystem when practical.
- Drop unnecessary Linux capabilities.
- Restrict outbound networking.
- Avoid mounting the Docker socket, home directory, or credential stores.

Example runtime shape after building a trusted image:

```bash
docker run --rm -i \
  --read-only \
  --cap-drop ALL \
  -v "/absolute/path/to/documents:/workdir:ro" \
  markitdown-mcp:0.1.6
```

The conversion URI inside the container would use a path under `/workdir`.

## Plugin Discovery

Plugins are Python distributions registered under the `markitdown.plugin` entry-point group.

List discovered plugins without enabling them:

```bash
markitdown --list-plugins
python scripts/inspect_installation.py
```

Enable plugins for one CLI conversion:

```bash
markitdown --use-plugins input.rtf -o output.md
```

Enable in Python:

```python
from markitdown import MarkItDown

converter = MarkItDown(enable_plugins=True)
result = converter.convert_local("input.rtf")
print(result.markdown)
```

## Plugin Trust Checklist

Before installing a plugin:

- Confirm the exact package name; defend against typosquatting.
- Verify the publisher and source repository.
- Review `pyproject.toml`, entry points, dependencies, and install hooks.
- Inspect converters for filesystem, subprocess, environment, and network access.
- Pin an exact version and retain a lockfile/hash in production.
- Test in an isolated environment with non-sensitive documents.
- Re-run review after every update.

Do not install arbitrary packages merely because they use the `#markitdown-plugin` tag.

## Plugin Interface Version 1

### Converter

```python
from typing import Any, BinaryIO

from markitdown import (
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)


class ExampleConverter(DocumentConverter):
    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        return (stream_info.extension or "").lower() == ".example"

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        payload = file_stream.read()
        return DocumentConverterResult(
            markdown=payload.decode("utf-8", errors="replace")
        )
```

`accepts()` must restore the stream position if it reads any bytes.

### Module registration

```python
from markitdown import MarkItDown

__plugin_interface_version__ = 1


def register_converters(markitdown: MarkItDown, **kwargs) -> None:
    markitdown.register_converter(ExampleConverter())
```

### `pyproject.toml`

```toml
[project.entry-points."markitdown.plugin"]
example = "example_markitdown_plugin"
```

MarkItDown calls `register_converters()` when a plugin-enabled instance is constructed and forwards the constructor keywords.

## Converter Priority

Lower values run first:

- Official OCR plugin: `-1.0`
- Specific built-in formats: `0.0`
- Generic text/HTML/ZIP converters: `10.0`

Registering a converter before built-ins can change the parser selected for existing formats. Treat priority as part of the plugin's security and compatibility review.

## Official OCR Plugin

`markitdown-ocr==0.1.0` is an official plugin from the Microsoft monorepo:

```bash
uv pip install \
  "markitdown==0.1.6" \
  "markitdown-ocr==0.1.0" \
  "openai==2.41.1"
```

It sends document images/pages to the configured OpenAI-compatible vision provider. Configuration and disclosure requirements are in `cloud_and_ocr.md`.

## Sources

- MCP guide at v0.1.6: https://github.com/microsoft/markitdown/tree/v0.1.6/packages/markitdown-mcp
- MCP server implementation: https://github.com/microsoft/markitdown/blob/v0.1.6/packages/markitdown-mcp/src/markitdown_mcp/__main__.py
- Sample plugin at v0.1.6: https://github.com/microsoft/markitdown/tree/v0.1.6/packages/markitdown-sample-plugin
