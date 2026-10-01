# llama.cpp

Source: https://pi.dev/docs/latest/llama-cpp

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi supports the llama.cpp **router** server, which discovers multiple GGUF models and loads or unloads them on demand. Use a current llama.cpp build with router support.

## Start the Router

Start `llama-server` **without** `--model`, `-m`, or `-hf`. Passing a model starts single-model mode instead of router mode.

```bash
llama-server \
  --models-dir ~/models \
  --no-models-autoload \
  --jinja \
  --host 127.0.0.1 \
  --port 8080 \
  -ngl 999 \
  -c 32768
```

- `--models-dir` discovers local GGUF files.
- `--no-models-autoload` keeps loading explicit through `/llama`.
- `--jinja` enables compatible chat templates and tool calling.
- `-ngl 999` offloads as many layers as possible to the GPU.
- `-c 32768` sets the context window per loaded model; omit to use the model's native context (may need much more memory).

Single-file models sit directly in the models directory. Multimodal and multi-shard models go in their own subdirectories with all components included. Restart the router after manually adding files; use llama.cpp model presets for per-model context sizes.

## Configure Pi

```text
/login llama.cpp
```

Enter the router URL (default `http://127.0.0.1:8080`) and optional API key. Environment variables configure the same values without `/login`:

```bash
export LLAMA_BASE_URL=http://127.0.0.1:8080
export LLAMA_API_KEY=optional-secret
pi
```

If the server uses an API key, start `llama-server` with the matching `--api-key`. Keep `--host 127.0.0.1` for local-only access.

## Manage Models with `/llama`

- Select an unloaded model to load it; select a loaded model to unload it.
- Select **Download model…** to search Hugging Face, then choose a repository and quantization. Exact `owner/repository[:quant]` values also work.
- Escape during a load or download prompts to confirm cancellation.
- If the router disconnects, `/llama` offers **Retry** and **Close**; Retry reconnects and refreshes state without replaying the interrupted operation.

Hugging Face search uses `HF_TOKEN` when set, then `$HF_TOKEN_PATH`, `$HF_HOME/token`, `$XDG_CACHE_HOME/huggingface/token`, and `~/.cache/huggingface/token`. Search works unauthenticated with lower rate limits. Pi warns before downloading gated repositories. The llama.cpp server performs the download, so its process also needs `HF_TOKEN` for gated repositories.

Pi never silently unloads models and never deletes model files; it asks whether to unload others first. The router may be shared with other clients, so `/llama` always displays the router's current state.

Loaded and sleeping models appear in `/model`; sleeping models wake when selected. With router autoload enabled, unloaded presets also appear and load on selection. With `--no-models-autoload`, load through `/llama` first. Every chat model also appears as a classifier with the same ID and `llama-cpp-classify` API; classifier calls consume context and should be validated for the selected model/task.

## Troubleshooting

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/models
```

- No models in `/llama`: check `--models-dir`, the directory layout, and restart the router.
- Model missing from `/model`: load it with `/llama` first.
- Load fails or uses too much memory: lower `-c` or unload another model.
- Server not in router mode: start it without `--model`, `-m`, or `-hf`.
