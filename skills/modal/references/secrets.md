# Modal Secrets

Reviewed against SDK 1.6.0 and official [Secrets](https://modal.com/docs/guide/secrets)
and [Secret API](https://modal.com/docs/reference/modal.Secret) documentation.
The snippets are illustrative; no Secrets were created or credentials transmitted.

## Overview

Modal Secrets securely deliver credentials and sensitive data to functions as environment variables. Secrets are stored encrypted and only available to your workspace.

## Creating Secrets

### Via CLI

```bash
# Create with key-value pairs
modal secret create my-api-keys API_KEY=placeholder DB_PASSWORD=placeholder

# Enter a value in an editor (keep real values out of shell history)
modal secret create my-env-keys 'API_KEY=-'

# List all secrets
modal secret list

# Delete a secret
modal secret delete my-api-keys
```

`KEY=-` opens an editor so values need not appear in shell history. For programmatic
use, read only the required key and use `Secret.from_dict`; avoid copying the full
environment or an unrelated project `.env` into a remote workload.

### Via Dashboard

Navigate to https://modal.com/secrets to create and manage secrets. Templates are available for common services (Postgres, MongoDB, Hugging Face, Weights & Biases, etc.).

### Programmatic (Inline)

```python
# From a dictionary (useful for development)
import os
secret = modal.Secret.from_dict({"API_KEY": os.environ["API_KEY"]})

# From a .env file
secret = modal.Secret.from_dotenv()

# From a named secret (created via CLI or dashboard)
secret = modal.Secret.from_name("my-api-keys", required_keys=["API_KEY"])
```

## Using Secrets in Functions

### Basic Usage

```python
@app.function(secrets=[modal.Secret.from_name("my-api-keys")])
def call_api():
    import os
    import requests
    api_key = os.environ["API_KEY"]
    # Use the key
    response = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    response.raise_for_status()
    return response.json()
```

### Multiple Secrets

```python
@app.function(secrets=[
    modal.Secret.from_name("openai-keys"),
    modal.Secret.from_name("database-creds"),
])
def process():
    import os
    openai_key = os.environ["OPENAI_API_KEY"]
    db_url = os.environ["DATABASE_URL"]
    ...
```

Secrets are applied in order — if two secrets define the same key, the later one wins.

### With Classes

```python
@app.cls(secrets=[modal.Secret.from_name("huggingface")])
class ModelService:
    @modal.enter()
    def load(self):
        import os
        token = os.environ["HF_TOKEN"]
        self.model = AutoModel.from_pretrained("model-name", token=token)
```

### From .env File

```python
# Searches upward from the current working directory; install python-dotenv locally.
@app.function(secrets=[modal.Secret.from_dotenv()])
def local_dev():
    import os
    api_key = os.environ["API_KEY"]
```

`Secret.from_dotenv(path="./workload-config", filename=".env")` sets the search starting
directory, but still searches parent directories. Verify the intended file exists.
It reads all entries in the discovered file, so keep only intended remote credentials
there. Modal platform tokens (`MODAL_TOKEN_*`) normally belong in the client profile,
not in a workload Secret.

The `.env` file format (placeholder values):

```dotenv
API_KEY=sk-xxx
DATABASE_URL=postgres://user:pass@host/db
DEBUG=false
```

## Common Secret Templates

| Service | Typical Keys |
|---------|-------------|
| OpenAI | `OPENAI_API_KEY` |
| Hugging Face | `HF_TOKEN` |
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Postgres | `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` |
| Weights & Biases | `WANDB_API_KEY` |
| GitHub | `GITHUB_TOKEN` |

## Security Notes

- Secrets are encrypted at rest and in transit
- Only accessible to functions in your workspace
- Never log or print secret values
- Use `.from_name()` in production (not `.from_dict()`)
- Rotate secrets regularly via the dashboard or CLI
