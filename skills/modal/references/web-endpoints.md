# Modal Web Endpoints

Reviewed against SDK 1.6.0 and official [Web Functions](https://modal.com/docs/guide/webhooks),
[proxy authentication](https://modal.com/docs/guide/webhook-proxy-auth),
[URLs](https://modal.com/docs/guide/webhook-urls) and
[request timeouts](https://modal.com/docs/guide/webhook-timeouts) documentation.
Examples use the Web Function API, which is public unless auth is explicitly enabled.
SDK registration and selected local ASGI handlers were tested; no endpoint was deployed.
Model-dependent fragments are illustrative.

## Table of Contents

- [Simple Endpoints](#simple-endpoints)
- [Deployment](#deployment)
- [ASGI Apps](#asgi-apps-fastapi-starlette-fasthtml)
- [WSGI Apps](#wsgi-apps-flask-django)
- [Custom Web Servers](#custom-web-servers)
- [WebSockets](#websockets)
- [Authentication](#authentication)
- [Streaming](#streaming)
- [Concurrency](#concurrency)
- [Limits](#limits)

## Simple Endpoints

The easiest way to create a web endpoint:

```python
import modal

image = modal.Image.debian_slim().uv_pip_install("fastapi[standard]==0.136.3")
app = modal.App("api-service", image=image)

@app.function()
@modal.fastapi_endpoint()
def hello(name: str = "World"):
    return {"message": f"Hello, {name}!"}
```

FastAPI must be installed in the remote Image. The remaining fragments reuse this
`app`/`image` unless defining their own; imports executed locally also need local packages.

### POST Endpoints

```python
@app.function()
@modal.fastapi_endpoint(method="POST")
def predict(data: dict):
    result = model.predict(data["text"])
    return {"prediction": result}
```

### Query Parameters

Parameters are automatically parsed from query strings:

```python
@app.function()
@modal.fastapi_endpoint()
def search(query: str, limit: int = 10):
    return {"results": do_search(query, limit)}
```

Access via: `https://your-app.modal.run?query=hello&limit=5`
This is a placeholder. Use the URL printed by `modal serve`/`modal deploy` or
`Function.get_web_url()`, rather than constructing the hostname. Scalar typed parameters
are query parameters even for POST; use a `dict` or Pydantic model for a JSON body.

## Deployment

### Development Mode

```bash
modal serve script.py
```

- Creates a temporary public URL
- Hot-reloads on file changes
- Perfect for development and testing
- URL expires when you stop the command

### Production Deployment

```bash
modal deploy script.py
```

- Creates a permanent URL
- Persists the App and URL; compute still scales to zero by default
- Autoscales based on traffic
- URL format: `https://<workspace>--<app-name>-<function-name>.modal.run`

## ASGI Apps (FastAPI, Starlette, FastHTML)

For full framework applications, use `@modal.asgi_app`:

```python
from fastapi import FastAPI

web_app = FastAPI()

@web_app.get("/")
async def root():
    return {"status": "ok"}

@web_app.post("/predict")
async def predict(request: dict):
    return {"result": model.run(request["input"])}

@app.function(image=image, gpu="L40S")
@modal.asgi_app()
def fastapi_app():
    return web_app
```

### With Class Lifecycle

```python
@app.cls(gpu="L40S", image=image)
class InferenceService:
    @modal.enter()
    def load_model(self):
        self.model = load_model()

    @modal.asgi_app()
    def serve(self):
        from fastapi import FastAPI
        app = FastAPI()

        @app.post("/generate")
        async def generate(request: dict):
            return self.model.generate(request["prompt"])

        return app
```

## WSGI Apps (Flask, Django)

```python
from flask import Flask

flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return {"status": "ok"}

flask_image = modal.Image.debian_slim().uv_pip_install("flask")

@app.function(image=flask_image)
@modal.wsgi_app()
def flask_server():
    return flask_app
```

WSGI is synchronous — concurrent inputs run on separate threads.

## Custom Web Servers

For non-standard web frameworks (aiohttp, Tornado, TGI):

```python
server_image = modal.Image.debian_slim(python_version="3.11").uv_pip_install("vllm==0.21.0")

@app.function(image=server_image, gpu="H100")
@modal.web_server(port=8000)
def serve():
    import subprocess
    subprocess.Popen([
        "vllm", "serve", "Qwen/Qwen3-8B",
        "--max-model-len", "4096",
        "--host", "0.0.0.0",  # Must bind to 0.0.0.0, not localhost
        "--port", "8000",
    ])
```

The application must bind to `0.0.0.0` (not `127.0.0.1`).

> **Security:** The command above uses a fixed argument list. Do not interpolate
> unsanitized user input (model names, paths, flags) into `subprocess` arguments —
> validate against an allowlist or pass untrusted values as data, not as command
> arguments, to avoid command injection.

## WebSockets

Modal's web proxy supports WebSockets. Use an ASGI or custom server framework that
implements WebSockets; plain WSGI/Flask handlers do not implement that protocol:

```python
from fastapi import FastAPI, WebSocket

web_app = FastAPI()

@web_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        result = process(data)
        await websocket.send_text(result)

@app.function()
@modal.asgi_app()
def ws_app():
    return web_app
```

- Full WebSocket protocol (RFC 6455)
- Messages up to 2 MiB each
- No RFC 8441 or RFC 7692 support yet

## Authentication

### Proxy Auth Tokens (Built-in)

Modal provides first-class endpoint protection via proxy auth tokens:

```python
@app.function()
@modal.fastapi_endpoint(requires_proxy_auth=True)
def protected(text: str):
    return {"result": text}
```

Create a **Proxy Token** (distinct from the Modal SDK token) in the dashboard or
`modal workspace proxy-tokens` CLI. Clients send its ID/secret as `Modal-Key` and
`Modal-Secret`, or `Authorization: Bearer <proxy-id>.<proxy-secret>`. Missing or invalid
credentials receive 401 before the handler runs. Merely sending these headers does
not protect an endpoint whose decorator omits `requires_proxy_auth=True`.

### Custom Bearer Tokens

```python
from fastapi import Header, HTTPException

@app.function(secrets=[modal.Secret.from_name("auth-secret")])
@modal.fastapi_endpoint(method="POST")
def secure_predict(data: dict, authorization: str = Header(None)):
    import os
    import hmac
    expected = os.environ["AUTH_TOKEN"]
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"result": model.predict(data["text"])}
```

### Client IP Access

Use a FastAPI `Request` and inspect `request.client.host` (if `request.client` is not
None). Do not trust an arbitrary user-supplied header as proof of client identity.

## Streaming

### Server-Sent Events (SSE)

```python
from fastapi.responses import StreamingResponse

@app.function(gpu="H100")
@modal.fastapi_endpoint()
def stream_generate(prompt: str):
    def generate():
        for token in model.stream(prompt):
            yield f"data: {token}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## Concurrency

Handle multiple requests per container using `@modal.concurrent`:

```python
@app.function(gpu="L40S")
@modal.concurrent(max_inputs=10)
@modal.fastapi_endpoint(method="POST")
async def batch_predict(data: dict):
    return {"result": await model.predict_async(data["text"])}
```

## Limits

- Request body: up to 4 GiB
- Response body: unlimited
- Rate limit: 200 requests/second (5-second burst for new accounts)
- Rate limit is workspace-wide and excess HTTP requests return 429; workspace limits can differ
- Cold starts occur when no container is ready (`min_containers` reduces their frequency)
- After 150 seconds a Web Function HTTP request returns a 303 result URL; clients
  must follow redirects. This is separate from the underlying Function timeout.
  CORS-dependent clients cannot rely on that redirect mechanism. Prefer `.spawn()`
  plus a call-ID polling endpoint for long jobs, and handle seven-day output expiry.

The newer `@app.server()` primitive serves latency-sensitive HTTP applications and
requires Proxy Tokens by default; its contract is distinct from these Web Functions.
See the official [Servers guide](https://modal.com/docs/guide/servers) before migrating.
