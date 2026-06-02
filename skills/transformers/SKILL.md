---
name: transformers
description: Hugging Face Transformers for loading Hub models, running pipeline inference, text generation, and Trainer fine-tuning on NLP, vision, audio, and multimodal tasks. Use when working with AutoModel, pipelines, tokenizers, or TrainingArguments—not for general ML outside the Transformers library.
license: Apache-2.0 license
compatibility: Requires Python 3.10+, PyTorch 2.4+, and transformers 5.x. Gated or private Hub models need an HF token (hf auth login or HF_TOKEN).
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
---

# Transformers

## Overview

The Hugging Face Transformers library provides access to thousands of pre-trained models for tasks across NLP, computer vision, audio, and multimodal domains. Use this skill to load models, perform inference, and fine-tune on custom data.

## Installation

Tested against **transformers 5.9.x** (stable; May 2026). Requires **Python 3.10+** and **PyTorch 2.4+**.

```bash
uv pip install "transformers[torch]>=5.9" huggingface_hub datasets evaluate accelerate
```

For vision tasks, add:

```bash
uv pip install timm pillow
```

For audio tasks, add:

```bash
uv pip install librosa soundfile
```

Check your version:

```python
import transformers
print(transformers.__version__)
```

## Authentication

Many models on the Hugging Face Hub are gated or private. Authenticate before loading them.

**Recommended:** CLI login (stores token in `~/.cache/huggingface/token`):

```bash
hf auth login
```

**Python:**

```python
from huggingface_hub import login
login()  # Interactive prompt; do not hardcode tokens in scripts
```

**Servers / CI:** set `HF_TOKEN` in the environment (never commit tokens to git or shell profiles):

```bash
export HF_TOKEN="..."  # Read token from a secret manager, not source code
```

Get tokens at: https://huggingface.co/settings/tokens

**Security:** Never paste tokens into notebooks, repos, or shared configs. Prefer `hf auth login` over exporting tokens in `.bashrc` or `.zshrc`.

## Transformers v5

Transformers v5 is **PyTorch-only** (TensorFlow and JAX backends were removed). For upgrades from v4, see the [v5 migration guide](https://github.com/huggingface/transformers/blob/main/MIGRATION_GUIDE_V5.md). New projects should pair **transformers 5.x** with **huggingface_hub 1.x**.

**Gated or custom architectures:** accept the model license on the Hub, then load with `trust_remote_code=True` only when the model card requires custom code you have reviewed.

**Cache location:** set `HF_HOME` for a writable cache root (Hub files default under `$HF_HOME/hub`).

## Quick Start

Use the Pipeline API for fast inference without manual configuration:

```python
from transformers import pipeline

# Text generation (prefer max_new_tokens for causal LMs)
generator = pipeline("text-generation", model="Qwen/Qwen2.5-1.5B")
result = generator("The future of AI is", max_new_tokens=50)

# Text classification
classifier = pipeline("text-classification")
result = classifier("This movie was excellent!")

# Question answering
qa = pipeline("question-answering")
result = qa(question="What is AI?", context="AI is artificial intelligence...")
```

## Core Capabilities

### 1. Pipelines for Quick Inference

Use for simple, optimized inference across many tasks. Supports text generation, classification, NER, question answering, summarization, translation, image classification, object detection, audio classification, and more.

**When to use**: Quick prototyping, simple inference tasks, no custom preprocessing needed.

See `references/pipelines.md` for comprehensive task coverage and optimization.

### 2. Model Loading and Management

Load pre-trained models with fine-grained control over configuration, device placement, and precision.

**When to use**: Custom model initialization, advanced device management, model inspection.

See `references/models.md` for loading patterns and best practices.

### 3. Text Generation

Generate text with LLMs using various decoding strategies (greedy, beam search, sampling) and control parameters (temperature, top-k, top-p).

**When to use**: Creative text generation, code generation, conversational AI, text completion.

See `references/generation.md` for generation strategies and parameters.

### 4. Training and Fine-Tuning

Fine-tune pre-trained models on custom datasets using the Trainer API with automatic mixed precision, distributed training, and logging.

**When to use**: Task-specific model adaptation, domain adaptation, improving model performance.

See `references/training.md` for training workflows and best practices.

### 5. Tokenization

Convert text to tokens and token IDs for model input, with padding, truncation, and special token handling.

**When to use**: Custom preprocessing pipelines, understanding model inputs, batch processing.

See `references/tokenizers.md` for tokenization details.

## Common Patterns

### Pattern 1: Simple Inference
For straightforward tasks, use pipelines:
```python
pipe = pipeline("task-name", model="model-id")
output = pipe(input_data)
```

### Pattern 2: Custom Model Usage
For advanced control, load model and tokenizer separately:
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("model-id")
model = AutoModelForCausalLM.from_pretrained("model-id", device_map="auto")

inputs = tokenizer("text", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=100)
result = tokenizer.decode(outputs[0])
```

### Pattern 3: Fine-Tuning
For task adaptation, use Trainer:
```python
from transformers import Trainer, TrainingArguments

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=8,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

trainer.train()
```

## Reference Documentation

For detailed information on specific components:
- **Pipelines**: `references/pipelines.md` - All supported tasks and optimization
- **Models**: `references/models.md` - Loading, saving, and configuration
- **Generation**: `references/generation.md` - Text generation strategies and parameters
- **Training**: `references/training.md` - Fine-tuning with Trainer API
- **Tokenizers**: `references/tokenizers.md` - Tokenization and preprocessing
