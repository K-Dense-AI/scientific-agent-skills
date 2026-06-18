# Containerization

Source: https://pi.dev/docs/latest/containerization

Pi runs with all permissions by default. Isolation patterns either run the whole Pi process inside a boundary or run Pi on the host while routing tools into a boundary.

## Patterns

- OpenShell: whole Pi process inside policy-controlled sandbox; best for local or remote managed sandboxing.
- Gondolin extension: host Pi with built-in tools and `!` commands routed into a local Linux micro-VM.
- Plain Docker: whole Pi process in a local container.

Extensions run wherever the Pi process runs. If host Pi routes built-ins into a VM, other extension tools still run on host unless they delegate too.

## OpenShell

```bash
openshell gateway add <gateway-url> --name <name>
openshell gateway select <name>
openshell sandbox create --name pi-sandbox --from pi -- pi
```

Remote gateways do not bind-mount local project files automatically. Upload/download project files explicitly. OpenShell can also route inference so raw provider keys stay outside the sandbox.

## Gondolin

```bash
cp -R packages/coding-agent/examples/extensions/gondolin ~/.pi/agent/extensions/gondolin
cd ~/.pi/agent/extensions/gondolin
npm install --ignore-scripts
cd /path/to/project
pi -e ~/.pi/agent/extensions/gondolin
```

The extension mounts host cwd at `/workspace` in the VM and overrides `read`, `write`, `edit`, `bash`, `grep`, `find`, and `ls`. Writes under `/workspace` write through to the host. Requires Node.js >= 23.6.0 and QEMU.

## Docker

```dockerfile
FROM node:24-bookworm-slim
RUN apt-get update   && apt-get install -y --no-install-recommends bash ca-certificates git ripgrep   && rm -rf /var/lib/apt/lists/*
RUN npm install -g --ignore-scripts @earendil-works/pi-coding-agent
WORKDIR /workspace
ENTRYPOINT ["pi"]
```

```bash
docker build -t pi-sandbox -f Dockerfile.pi .
docker run --rm -it   -e ANTHROPIC_API_KEY   -v "$PWD:/workspace"   -v pi-agent-home:/root/.pi/agent   pi-sandbox
```

Mounting host `~/.pi/agent` exposes host auth and session files. Use a named volume for container-local settings and sessions.
