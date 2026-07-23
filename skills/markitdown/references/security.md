# Security and Privacy

MarkItDown is a converter, not a sandbox. It performs file and network I/O with the privileges of the current process and loads parser dependencies for complex, attacker-controlled formats.

## Threat Model

Treat all of these as untrusted unless provenance is established:

- Paths, filenames, and URIs supplied by users or agents
- Uploaded PDFs, Office files, archives, notebooks, images, audio, and EPUBs
- HTTP response headers and redirects
- Installed plugins
- Markdown produced from external documents
- LLM/OCR responses

Potential impacts include:

- Reading arbitrary local files
- Server-side request forgery (SSRF)
- Access to loopback services or cloud metadata
- Archive/decompression bombs and memory exhaustion
- Parser vulnerabilities
- Credential or document exfiltration to cloud/LLM providers
- Prompt injection carried through converted content
- Arbitrary Python execution through plugins

## API Risk Levels

| API | Input capability | Recommended use |
|---|---|---|
| `convert_local()` | Local path only | Trusted, allowlisted local files |
| `convert_stream()` | Caller-controlled bytes | Preferred for validated uploads |
| `convert_response()` | Existing HTTP response | After caller-enforced network policy |
| `convert_uri()` | `file:`, `data:`, `http:`, `https:` | Trusted and validated URI only |
| `convert()` | Dispatches across all of the above | Trusted polymorphic input only |

Use the narrowest API that satisfies the task.

## Local File Controls

Before `convert_local()`:

1. Resolve the candidate path and the approved root.
2. Confirm the resolved candidate remains under that root.
3. Reject symlinks when their semantics are not explicitly required.
4. Require a regular file; reject devices, FIFOs, sockets, and directories.
5. Enforce an extension/MIME allowlist.
6. Apply a maximum byte size before opening.
7. Open with the least-privileged process account.
8. Keep sensitive directories outside the process's readable namespace.

Do not build a path by concatenating an untrusted filename with a directory string.

The bundled batch and literature scripts use `convert_local()` and skip symlink inputs by default.

## HTTP(S) and SSRF Controls

Do not pass a user-controlled URL directly to `convert()` or `convert_uri()`.

An application-controlled downloader should enforce all of the following:

- Permit only required schemes, preferably HTTPS.
- Reject embedded usernames/passwords and malformed authorities.
- Canonicalize internationalized hostnames.
- Resolve DNS and reject every loopback, private, link-local, multicast, reserved, unspecified, and metadata-service address in IPv4 and IPv6.
- Revalidate the destination on every redirect.
- Defend against DNS rebinding; validation before connection alone is insufficient.
- Disable ambient proxy/environment behavior unless it is an explicit part of policy.
- Use connect and read timeouts.
- Limit redirect count.
- Enforce `Content-Length` when present and a streaming byte limit regardless of the header.
- Limit decompressed size.
- Allowlist response MIME types.
- Verify TLS normally; never disable certificate verification.
- Avoid forwarding credentials across origins.
- Pass the validated `requests.Response` to `convert_response()`.

MarkItDown's own HTTP path calls a Requests session and buffers the complete response before parsing. It does not impose these application-level controls.

## `file:` and `data:` URIs

`file:` URIs can read anything the process user can read. MarkItDown permits an empty authority or `localhost`; this is not a path allowlist.

`data:` URIs can contain arbitrarily large base64 payloads. Decode size grows beyond encoded size, and conversion can create additional copies.

Prefer `convert_local()` or a bounded `convert_stream()` path instead of accepting arbitrary URI strings.

## Streams and Memory

- `convert_stream()` copies a non-seekable stream completely into memory.
- `convert_response()` buffers the complete HTTP response.
- ZIP, large tables, base64 images, and generated Markdown can substantially expand data.
- `--keep-data-uris` preserves full embedded payloads and can expose hidden/sensitive data.

Set input, output, member-count, page-count, time, and memory limits outside MarkItDown.

## Archives

MarkItDown's ZIP converter iterates members and applies nested conversion. Before accepting an untrusted archive, enforce:

- Maximum compressed bytes
- Maximum total uncompressed bytes
- Maximum member count
- Maximum single-member bytes
- Maximum nested archive depth
- Compression-ratio threshold
- File-type allowlist
- Conversion timeout

MarkItDown does not turn an archive into a safe bundle merely because it processes members in memory.

## Parser Supply Chain

Use a pinned MarkItDown release:

```bash
uv pip install "markitdown[all]==0.1.6"
```

Relevant release history:

- 0.1.2 moved XML/OMML parsing to `defusedxml`.
- 0.1.3 required safe ExifTool usage at version 12.24 or later.
- 0.1.4 updated Mammoth and `pdfminer.six` for published vulnerabilities.
- 0.1.6 clarified the project's I/O security posture.

For production:

- Lock transitive dependencies and retain hashes.
- Scan the environment and container image.
- Rebuild when parser security advisories are published.
- Test representative documents after upgrades.

## Plugins

Plugins are arbitrary Python code loaded through package entry points. They run in the same process and can access its files, network, environment, and credentials.

- Keep `enable_plugins=False` by default.
- Pin and review every plugin.
- Inspect install/build hooks and transitive dependencies.
- Run risky plugins in a sandbox with synthetic files.
- Do not install by hashtag or name similarity alone.

The official `markitdown-ocr` plugin still introduces external LLM calls and expands parser dependencies.

## External Processing Map

| Feature | What leaves the process | Destination |
|---|---|---|
| HTTP(S), RSS, Wikipedia, Bing | Request metadata; downloaded response returns | Requested host |
| YouTube conversion | Page and transcript requests | YouTube/transcript service |
| Built-in audio transcription | Recorded audio | Google Web Speech via `SpeechRecognition` |
| LLM image description | Prompt and base64 image | Configured OpenAI-compatible provider |
| `markitdown-ocr` | Prompt plus embedded/full-page images | Configured vision provider |
| Document Intelligence | Complete selected file | Configured Azure resource |
| Content Understanding | Complete selected document/image/audio/video | Configured Azure resource |

Do not describe `[all]` as fully offline. It installs capabilities whose use can make network calls.

## Credentials

- Use only the named credential required by the selected service.
- Prefer workload identity or managed identity for Azure.
- Never enumerate, copy, print, or forward the process environment.
- Never place a key in a command-line argument, source file, Markdown output, manifest, or log.
- Keep provider base URLs fixed to a reviewed endpoint; do not combine a credential with a user-controlled endpoint.
- Scope keys to the minimum service/project and rotate them.

MarkItDown's Azure converters look for the named `AZURE_API_KEY`; otherwise they use `DefaultAzureCredential`. OpenAI-compatible clients use their own provider-specific configuration.

## Sensitive Scientific and Clinical Data

Before cloud, audio, or LLM processing:

- Confirm consent and data-processing agreements.
- Check PHI/PII, genomic-identifiability, unpublished results, export controls, and sponsor restrictions.
- Use an approved region and tenant.
- Minimize pages/modalities sent.
- Understand provider retention and training policies.
- Record the processing method in provenance without recording secrets.

When approval is absent, use a local parser/OCR workflow.

## MCP Server

`markitdown-mcp` has no authentication and exposes broad URI conversion. Even localhost mode can be reached by other local processes/users.

- Prefer STDIO.
- Never bind directly to non-local interfaces.
- Isolate filesystem and network access.
- Mount only the required directory read-only.
- Keep plugins disabled.

See `mcp_and_plugins.md`.

## Prompt Injection in Converted Content

Documents can contain text such as "ignore previous instructions," links to malicious resources, or commands disguised as analysis steps. Conversion preserves that content.

When Markdown is used with an agent or RAG system:

1. Label it as untrusted source material.
2. Separate it from system/developer instructions.
3. Do not grant tools based on instructions found in the document.
4. Require independent authorization for file, shell, network, or credential actions.
5. Preserve source/page provenance for claims.
6. Sanitize active HTML and dangerous links before rendering.

## Output and Logging

Avoid logging:

- Full source paths when they reveal study/patient information
- Document contents
- Base64 data URIs
- Provider request/response bodies
- API keys, authorization headers, or signed URLs

Useful safe provenance:

- Content hash
- Redacted source identifier
- MarkItDown/plugin version
- Converter mode
- Timestamp
- Approved provider/analyzer identifier
- Success/failure category

## Preflight Checklist

- [ ] Source and requester are authorized
- [ ] Narrow conversion API selected
- [ ] Local path or network destination validated
- [ ] Input/output/resource limits applied
- [ ] Plugins disabled or reviewed
- [ ] External transmission disclosed and approved
- [ ] Credentials scoped and not logged
- [ ] Converted Markdown treated as untrusted data
- [ ] Result checked against the source
- [ ] Original retained as authority

## Sources

- MarkItDown security guidance: https://github.com/microsoft/markitdown/blob/v0.1.6/README.md#security-considerations
- MCP security guidance: https://github.com/microsoft/markitdown/blob/v0.1.6/packages/markitdown-mcp/README.md#security-considerations
- Release history: https://github.com/microsoft/markitdown/releases
