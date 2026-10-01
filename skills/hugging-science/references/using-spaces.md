# Using Hugging Science Spaces

A Space can be Gradio, Docker or static content. An organization listing does not
mean every entry is an inference service or has a public API. Check `sdk`, runtime
and the actual application before passing inputs. Public Spaces can sleep, fail,
queue or require paid compute; they are not an availability or cost guarantee.

## Inspect before calling

```bash
uv pip install 'gradio-client==2.7.1' 'huggingface-hub<2' python-dotenv
```

Metadata-only discovery (no inference or uploads):

```python
from huggingface_hub import HfApi
api = HfApi(token=False)
for space in api.list_spaces(author="hugging-science", limit=100):
    print(space.id, space.sdk)
info = api.space_info("hugging-science/BoltzGen_Demo")
print(info.sdk, info.runtime.stage)
```

`list_spaces` is a paginated iterator; `limit` caps the number yielded, not a promise
of a complete organization inventory. Names are case sensitive: the reviewed
BoltzGen demo is `hugging-science/BoltzGen_Demo`, not `boltzgen-demo`.

When the selected Gradio runtime is available, inspect its schema:

```python
import os
from dotenv import load_dotenv
load_dotenv()
from gradio_client import Client

# token=False suppresses implicit credentials for a public app.
# Use token=os.environ["HF_TOKEN"] only when authentication is needed and authorized.
client = Client("hugging-science/BoltzGen_Demo", token=False,
                analytics_enabled=False, httpx_kwargs={"timeout": 30})
schema = client.view_api(return_format="dict")
print(schema)
```

Gradio Client 2.7.1 uses `token=` (older examples may say `hf_token=`).
`token=None` allows the locally saved/HF_TOKEN credential. Access authentication
and `oauth_token=` are distinct: the latter lets an app act on your behalf and is
only sent to endpoints declaring OAuth requirements. Do not provide an OAuth token
for ordinary inference. Review the actual app/operator and data-transfer scope
regardless of its organization. Follow existing user authorization; clarify only
when the proposed upload or execution is outside that scope.

## BoltzGen: source contract, runtime currently unverified

On 2026-10-01 the public Space repository resolved with runtime `PAUSED`, while `/config` and
`/gradio_api/info` returned HTTP 503. Thus `Client` discovery and end-to-end
inference were **not** validated. Do not substitute an invented `/generate` API.

The [reviewed app source](https://huggingface.co/spaces/hugging-science/BoltzGen_Demo/blob/main/app.py)
registers `run_boltzgen` with five inputs, in order:

1. Design YAML file.
2. Target PDB/CIF file referenced by that YAML.
3. Protocol: `protein-anything`, `peptide-anything` or `nanobody-anything`.
4. Number of candidate designs.
5. Budget: final diversified design count, at most the number of candidates.

Budget is not an LLM token allowance. The run returns a **status string**; it does
not directly return sequences or coordinates. Separate download actions exist.
Their exact generated API names and return arity must be checked in `view_api()`
when the runtime recovers. The reviewed source has shared `/tmp/output` paths and
a download function returning two values for a one-output event; file isolation
and download behavior need verification before relying on a public run.

After the live schema is confirmed, an illustrative call pattern is:

```python
from gradio_client import handle_file

# Set this from the live schema; it is deliberately not a guessed endpoint.
api_name = confirmed_run_api_name
status = client.predict(
    handle_file("design.yaml"), handle_file("target.pdb"),
    "protein-anything", 2, 1, api_name=api_name,
)
print(status)
```

`handle_file` marks an input for upload. A local filename alone may be interpreted
as text. It does not upload until the client call is submitted. Returned Gradio file
components normally download to the client's local output directory; status text
containing a server path is not itself a downloaded file. Use the actual output
schema and verify artifacts belong to the current job.

## Other reviewed organization entries

| Space | What the public metadata/source establishes |
|---|---|
| `hugging-science/anatomy-of-boltzgen` | Static educational site; no Gradio inference API |
| `hugging-science/dataset-quest` | Gradio dataset discovery/submission app; submission is a write |
| `hugging-science/science-release-map` | Docker visualization; old `science-release-heatmap` ID did not resolve publicly |
| `hugging-science/HuggingMod` | Gradio moderation tooling, not scientific inference |

Do not retry a submitted design job blindly after a timeout: inspect its job/status
first to avoid duplicate compute. Duplicating a Space provisions separate resources
and may incur charges; it is a deployment action, not a read-only workaround. When
no runtime/API is available, report that limitation and use the author's local
workflow if it is feasible and within the task.

Sources: [Gradio Client 2.7.1](https://github.com/gradio-app/gradio/blob/gradio_client%402.7.1/client/python/gradio_client/client.py),
[file handling](https://github.com/gradio-app/gradio/blob/gradio_client%402.7.1/client/python/gradio_client/utils.py),
[HfApi Space methods](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api).
