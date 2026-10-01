"""Local execution and SDK registration of documented Modal examples; no cloud calls."""
import asyncio
import importlib.util
import re
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

modal = pytest.importorskip("modal")
httpx = pytest.importorskip("httpx")
fastapi = pytest.importorskip("fastapi")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "modal"


def blocks(relative):
    return re.findall(r"```python\n(.*?)\n```", (SKILL_ROOT / relative).read_text(), re.S)


def snippet(relative, marker):
    matches = [block for block in blocks(relative) if marker in block]
    assert len(matches) == 1
    return matches[0]


def load_code(tmp_path, code):
    name = f"modal_documented_example_{len(list(tmp_path.iterdir()))}"
    path = tmp_path / f"{name}.py"
    path.write_text(code)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Local Modal tests must not contact the cloud")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.mark.parametrize("index", range(len(blocks("references/examples.md"))))
def test_workload_definitions_register_without_cloud(tmp_path, index):
    module = load_code(tmp_path, blocks("references/examples.md")[index])
    assert isinstance(module.app, modal.App)


def test_documented_hello_executes_locally(tmp_path):
    module = load_code(tmp_path, snippet("references/getting-started.md", 'app = modal.App("hello-world")'))
    assert module.greet.local("Researcher") == "Hello, Researcher! This ran in the cloud."


@pytest.mark.parametrize("marker", ["def bounded_compute", "def bounded_memory", "def full_pipeline"])
def test_resource_configurations_register(tmp_path, marker):
    code = "import modal\napp = modal.App()\n" + snippet("references/resources.md", marker)
    load_code(tmp_path, code)


def test_schedules_and_dynamic_variants_construct_locally():
    modal.Cron("0 9 * * *", timezone="America/New_York")
    modal.Period(hours=6)
    function = modal.Function.from_name("my-app", "process")
    variant = function.with_options(cpu=(1.0, 4.0), memory=(8192, 16384), max_containers=2)
    assert variant is not function
    assert isinstance(variant.with_concurrency(max_inputs=10, target_inputs=8), modal.Function)
    assert isinstance(function.with_batching(max_batch_size=32, wait_ms=100), modal.Function)


def test_vllm_service_uses_sampling_params_and_local_method(tmp_path, monkeypatch):
    calls = []
    class SamplingParams:
        def __init__(self, **kwargs):
            self.options = kwargs
    class LLM:
        def __init__(self, **kwargs):
            calls.append(("load", kwargs))
        def generate(self, prompts, *, sampling_params):
            calls.append(("generate", prompts, sampling_params.options))
            return [SimpleNamespace(outputs=[SimpleNamespace(text="mock completion")])]
    monkeypatch.setitem(sys.modules, "vllm", SimpleNamespace(LLM=LLM, SamplingParams=SamplingParams))
    module = load_code(tmp_path, snippet("references/examples.md", 'app = modal.App("vllm-service")'))
    result = module.LLMService().api.local({"prompt": "Prepared prompt", "max_tokens": 23})
    assert result == {"text": "mock completion"}
    assert calls[-1] == ("generate", ["Prepared prompt"], {"max_tokens": 23, "temperature": 0.7})


def test_web_simple_query_and_bearer_body_contract(tmp_path, monkeypatch):
    source = snippet("references/web-endpoints.md", 'app = modal.App("api-service"')
    source += "\n" + snippet("references/web-endpoints.md", "def secure_predict(")
    module = load_code(tmp_path, source)
    module.model = SimpleNamespace(predict=lambda text: text.upper())
    monkeypatch.setenv("AUTH_TOKEN", "test-only-token")
    api = fastapi.FastAPI()
    # Access the original functions via the installed SDK, preserving FastAPI signatures.
    api.get("/")(module.hello._raw_f_)
    api.post("/predict")(module.secure_predict._raw_f_)
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as client:
            assert (await client.get("/", params={"name": "Ada"})).json() == {"message": "Hello, Ada!"}
            for headers in [{}, {"Authorization": "Bearer incorrect"}]:
                assert (await client.post("/predict", json={"text": "signal"}, headers=headers)).status_code == 401
            response = await client.post("/predict", json={"text": "signal"}, headers={"Authorization": "Bearer test-only-token"})
            assert response.json() == {"result": "SIGNAL"}
            assert (await client.post("/predict", params={"text": "not-a-body"})).status_code == 422
    asyncio.run(check())


def test_protected_decorator_sets_proxy_auth(tmp_path):
    source = "import modal\napp = modal.App()\n" + snippet("references/web-endpoints.md", "def protected(")
    module = load_code(tmp_path, source)
    assert module.protected._raw_f_("value") == {"result": "value"}
    from modal._utils.async_utils import synchronizer
    # Inspect the serialized SDK configuration; proxy enforcement itself is remote.
    assert synchronizer._translate_in(module.protected)._webhook_config.requires_proxy_auth


def test_sandbox_example_waits_and_cleans_up_after_failure(tmp_path, monkeypatch):
    sb = Mock()
    proc = sb.exec.return_value
    proc.stdout.read.return_value = "1024\n"
    proc.returncode = 1
    monkeypatch.setattr(modal.App, "lookup", Mock(return_value=modal.App()))
    create = Mock(return_value=sb)
    monkeypatch.setattr(modal.Sandbox, "create", create)
    code = "import modal\n" + snippet("SKILL.md", 'app = modal.App.lookup("sandbox-demo"')
    with pytest.raises(RuntimeError, match="Sandbox command failed"):
        load_code(tmp_path, code)
    assert create.call_args.kwargs["block_network"] is True
    assert create.call_args.kwargs["timeout"] == 60
    sb.filesystem.write_text.assert_called_once_with("print(2 ** 10)\n", "/tmp/job.py")
    proc.wait.assert_called_once_with()
    sb.terminate.assert_called_once_with(wait=True)
