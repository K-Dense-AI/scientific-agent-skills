# Modal API Reference

Checked against installed `modal==1.6.0` signatures and official
[Python SDK reference](https://modal.com/docs/sdk/py/latest) /
[release notes](https://modal.com/docs/sdk/py/releases). SDK object construction was
tested without contacting Modal; cloud behavior below is documentation-verified.

## Core Classes

### modal.App

The main unit of deployment. Groups related functions.

```python
app = modal.App("my-app")
```

| Method | Description |
|--------|-------------|
| `app.function(**kwargs)` | Decorator to register a function |
| `app.cls(**kwargs)` | Decorator to register a class |
| `app.local_entrypoint()` | Decorator for local entry point |

### modal.Function

A serverless function backed by an autoscaling container pool.

| Method | Description |
|--------|-------------|
| `.remote(*args)` | Execute in the cloud (sync) |
| `.local(*args)` | Execute locally |
| `.spawn(*args)` | Execute async, returns `FunctionCall` |
| `.map(inputs)` | Parallel execution over inputs |
| `.starmap(inputs)` | Parallel execution with multiple args |
| `.for_each(inputs)` | Like `.map()` but discards outputs |
| `.spawn_map(inputs)` | Submit asynchronous inputs; returns `None`, not result handles |
| `.from_name(app, fn)` | Reference a deployed function (replaces deprecated `.lookup`) |
| `.hydrate()` | Force-fetch server metadata (replaces deprecated `.resolve()`) |
| `.with_options(gpu=, ...)` | New autoscaling variant with overridden config |
| `.with_concurrency(max_inputs=, target_inputs=)` | Override input concurrency at invocation |
| `.with_batching(max_batch_size=, wait_ms=)` | Override dynamic batching at invocation |
| `.update_autoscaler(**kwargs)` | Dynamic scaling update |

### modal.Cls

A serverless class with lifecycle hooks.

```python
@app.cls(gpu="L40S")
class MyClass:
    @modal.enter()
    def setup(self): ...

    @modal.method()
    def run(self, data): ...

    @modal.exit()
    def cleanup(self): ...
```

| Decorator | Description |
|-----------|-------------|
| `@modal.enter()` | Container startup hook |
| `@modal.exit()` | Container shutdown hook |
| `@modal.method()` | Expose as callable method |
| `field: str = modal.parameter()` | Class-level parameter descriptor (not a decorator) |

Look up a deployed Cls with `Model = modal.Cls.from_name("app", "Model")`, then
instantiate before calling: `Model().method.remote(...)`. Override config at invocation
with `Model.with_options(gpu="H200", max_containers=10)`.
SDK 1.6 rejects custom `__init__`; put initialization in `@modal.enter()`.
Variant pools scale independently; `.with_options()` cannot set `min_containers`.

## Image

### modal.Image

Defines the container environment.

| Method | Description |
|--------|-------------|
| `.debian_slim(python_version=)` | Debian base image |
| `.from_registry(tag)` | Docker Hub image |
| `.from_dockerfile(path)` | Build from Dockerfile |
| `.micromamba(python_version=)` | Conda/mamba base |
| `.uv_pip_install(*pkgs)` | Install with uv (recommended) |
| `.pip_install(*pkgs)` | Install with pip |
| `.pip_install_from_requirements(path)` | Install from file |
| `.uv_sync(project_dir)` | Install the project's locked uv environment |
| `.apt_install(*pkgs)` | Install system packages |
| `.run_commands(*cmds)` | Run shell commands |
| `.run_function(fn)` | Run Python during build |
| `.add_local_dir(local, remote)` | Add directory |
| `.add_local_file(local, remote)` | Add single file |
| `.add_local_python_source(module)` | Add Python module |
| `.env(dict)` | Set environment variables |
| `.pipe(recipe_fn)` | Apply a reusable Image recipe |
| `.imports()` | Context manager for remote imports |

> `add_local_dir`/`add_local_file`/`add_local_python_source` replace the deprecated
> `copy_local_*` methods and the removed `modal.Mount` object / `mount=` / `context_mount=`
> parameters.

## Storage

### modal.Volume

Distributed persistent file storage.

```python
vol = modal.Volume.from_name("name", create_if_missing=True)
```

| Method | Description |
|--------|-------------|
| `.from_name(name)` | Reference or create a volume |
| `.commit()` | Force immediate commit |
| `.reload()` | Refresh to see other containers' writes |
| `.with_mount_options(read_only=, sub_path=)` | Read-only or subdirectory mount |

Mount: `@app.function(volumes={"/path": vol})`

### modal.NetworkFileSystem

Legacy shared storage (superseded by Volume).

## Sandboxes

### modal.Sandbox

Isolated, programmatically controlled containers for running untrusted or
dynamically generated code.

```python
app = modal.App.lookup("my-app", create_if_missing=True)
sb = modal.Sandbox.create(app=app, image=modal.Image.debian_slim(), timeout=60, block_network=True)
try:
    proc = sb.exec("python", "-c", "print(2 ** 10)")
    stdout = proc.stdout.read()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("Sandbox command failed")
finally:
    sb.terminate(wait=True)
```

| Method | Description |
|--------|-------------|
| `.create(app=, image=, ...)` | Launch and wait for scheduling (SDK 1.6) |
| `.exec(*cmd)` | Run a command, returns a process handle |
| `.filesystem.read_text(path)` | Read a Sandbox file into a string |
| `.filesystem.write_text(text, path)` | Write a string; content argument comes first |
| `.filesystem.copy_from_local(local, remote)` | Stream a local file to the Sandbox |
| `.filesystem.copy_to_local(remote, local)` | Stream a Sandbox file to local storage |
| `.snapshot_filesystem(timeout=55, ttl=2592000)` | Image snapshot, default retention 30 days |
| `.terminate(wait=True)` | Stop and wait for termination confirmation |

Restrict connectivity with `inbound_cidr_allowlist=[...]` / `outbound_cidr_allowlist=[...]`.
Use `block_network=True` when egress is unnecessary. Allowlisting a private CIDR is
not a substitute for selecting the intended destinations. Network restrictions do
not remove Secrets or data mounted into the container.
`Sandbox.create()` can raise `ResourceExhaustedError` if scheduling fails. The old
`Sandbox.open/ls/mkdir/rm/watch` APIs are removed; use `.filesystem`.
Pass `ttl=None` explicitly if a filesystem snapshot must not expire, and track its
Image ID. See [Sandbox snapshots](https://modal.com/docs/guide/sandbox-snapshots).

## Secrets

### modal.Secret

Secure credential injection.

| Method | Description |
|--------|-------------|
| `.from_name(name)` | Reference a named secret |
| `.from_dict(dict)` | Create inline (dev only) |
| `.from_dotenv()` | Load from .env file |

Usage: `@app.function(secrets=[modal.Secret.from_name("x")])`

Access in function: `os.environ["KEY"]`

## Scheduling

### modal.Cron

```python
schedule = modal.Cron("0 9 * * *")  # Cron syntax
```

### modal.Period

```python
schedule = modal.Period(hours=6)  # Fixed interval
```

Usage: `@app.function(schedule=modal.Cron("..."))`

## Web

### Decorators

| Decorator | Description |
|-----------|-------------|
| `@modal.fastapi_endpoint()` | Simple FastAPI endpoint |
| `@modal.asgi_app()` | Full ASGI app (FastAPI, Starlette) |
| `@modal.wsgi_app()` | Full WSGI app (Flask, Django) |
| `@modal.web_server(port=)` | Custom web server |

### Function Modifiers

| Decorator | Description |
|-----------|-------------|
| `@modal.concurrent(max_inputs=)` | Handle multiple inputs per container |
| `@modal.batched(max_batch_size=, wait_ms=)` | Dynamic input batching |

## GPU Strings

| String | GPU |
|--------|-----|
| `"T4"` | NVIDIA T4 16GB |
| `"L4"` | NVIDIA L4 24GB |
| `"A10"` | NVIDIA A10 24GB |
| `"L40S"` | NVIDIA L40S 48GB |
| `"A100-40GB"` | NVIDIA A100 40GB |
| `"A100-80GB"` | NVIDIA A100 80GB |
| `"H100"` | NVIDIA H100 80GB |
| `"H100!"` | H100 (no auto-upgrade) |
| `"H200"` | NVIDIA H200 141GB |
| `"B200"` | NVIDIA B200 192GB |
| `"B200+"` | B200 or B300, B200 price |
| `"B300"` | NVIDIA B300 288GB, CUDA 13.1+ |
| `"RTX-PRO-6000"` | NVIDIA RTX PRO 6000 Blackwell 96GB |
| `"H100:4"` | 4x H100 |

## CLI Commands

| Command | Description |
|---------|-------------|
| `modal setup` | Authenticate |
| `modal run <file>` | Run local entrypoint |
| `modal serve <file>` | Dev server with hot reload |
| `modal deploy <file>` | Production deployment |
| `modal app list` | List deployed apps |
| `modal app stop <name>` | Stop an app |
| `modal volume create <name>` | Create volume |
| `modal volume ls <name>` | List volume files |
| `modal volume put <name> <file>` | Upload to volume |
| `modal volume get <name> <file>` | Download from volume |
| `modal secret create <name> K=V` | Create secret |
| `modal secret list` | List secrets |
| `modal secret delete <name>` | Delete secret |
| `modal token set` | Set auth token |
