# Model Loading and Management

Targets Transformers 5.18.0. Hub/accelerator/export examples are illustrative; tiny local model APIs are exercised by `tests/transformers/`. See [review evidence](review.md).

## Overview

The transformers library provides flexible model loading with automatic architecture detection, device management, and configuration control.

## Loading Models

### AutoModel Classes

Use AutoModel classes for automatic architecture selection:

```python
from transformers import AutoModel, AutoModelForSequenceClassification, AutoModelForCausalLM

# Base model (no task head)
model = AutoModel.from_pretrained("google-bert/bert-base-uncased")

# Sequence classification
model = AutoModelForSequenceClassification.from_pretrained("distilbert/distilbert-base-uncased")

# Causal language modeling (GPT-style)
model = AutoModelForCausalLM.from_pretrained("openai-community/gpt2")

# Masked language modeling (BERT-style)
from transformers import AutoModelForMaskedLM
model = AutoModelForMaskedLM.from_pretrained("google-bert/bert-base-uncased")

# Sequence-to-sequence (T5-style)
from transformers import AutoModelForSeq2SeqLM
model = AutoModelForSeq2SeqLM.from_pretrained("google-t5/t5-small")
```

### Common AutoModel Classes

**NLP Tasks:**
- `AutoModelForSequenceClassification`: Text classification, sentiment analysis
- `AutoModelForTokenClassification`: NER, POS tagging
- `AutoModelForQuestionAnswering`: Extractive QA
- `AutoModelForCausalLM`: Text generation (GPT, Llama)
- `AutoModelForMaskedLM`: Masked language modeling (BERT)
- `AutoModelForSeq2SeqLM`: Translation, summarization (T5, BART)

**Vision Tasks:**
- `AutoModelForImageClassification`: Image classification
- `AutoModelForObjectDetection`: Object detection
- `AutoModelForImageSegmentation`: Image segmentation

**Audio Tasks:**
- `AutoModelForAudioClassification`: Audio classification
- `AutoModelForSpeechSeq2Seq`: Speech recognition

**Multimodal:**
- `AutoModelForImageTextToText`: Generative image captioning and visual chat, paired with `AutoProcessor`
- `AutoModelForVisualQuestionAnswering`: Architecture-specific direct VQA models

## Loading Parameters

### Basic Parameters

**pretrained_model_name_or_path**: Model identifier or local path
```python
model = AutoModel.from_pretrained("google-bert/bert-base-uncased")  # From Hub
model = AutoModel.from_pretrained("./local/model/path")  # From disk
```

**num_labels**: Number of output labels for classification
```python
model = AutoModelForSequenceClassification.from_pretrained(
    "google-bert/bert-base-uncased",
    num_labels=3
)
```

**cache_dir**: Custom cache location
```python
model = AutoModel.from_pretrained("model-id", cache_dir="./my_cache")
```

### Device Management

**device_map**: Automatic device allocation for large models
```python
# Automatically distribute across GPUs and CPU
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-1.5B",
    device_map="auto"
)

# Accelerate device maps are for inference, not distributed Trainer training.
# Sequential placement
model = AutoModelForCausalLM.from_pretrained(
    "model-id",
    device_map="sequential"
)

# A complete one-device map; split maps must name real model modules and cover all weights.
model = AutoModel.from_pretrained("model-id", device_map={"": "cpu"})
```

Manual device placement:
```python
import torch
model = AutoModel.from_pretrained("model-id")
model.to("cuda:0")  # Move to GPU 0
model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
```

### Precision Control

**dtype**: Set model precision (preferred in v5; `torch_dtype` still works but is deprecated)
```python
import torch

# Float16 (half precision)
model = AutoModel.from_pretrained("model-id", dtype=torch.float16)

# BFloat16 (better range than float16)
model = AutoModel.from_pretrained("model-id", dtype=torch.bfloat16)

# Auto (use original dtype)
model = AutoModel.from_pretrained("model-id", dtype="auto")
```

### Attention Implementation

**attn_implementation**: Choose attention mechanism
```python
# SDPA (supported architectures; backend/shape determine speed)
model = AutoModel.from_pretrained("model-id", attn_implementation="sdpa")

# Flash Attention 2 (requires flash-attn package)
model = AutoModel.from_pretrained("model-id", attn_implementation="flash_attention_2")

# Eager (explicit reference implementation; SDPA is often selected by default)
model = AutoModel.from_pretrained("model-id", attn_implementation="eager")
```

### Memory Optimization

Transformers v5 manages efficient loading internally; legacy `low_cpu_mem_usage` is ignored. `device_map="auto"` can dispatch to accelerators/CPU/disk according to available memory; supply `max_memory` and `offload_folder` when needed, inspect `model.hf_device_map`, and keep inputs on the entry device. Do not call `.to(...)` on an already dispatched model.

**BitsAndBytesConfig**: 8-bit and 4-bit quantization (requires optional `bitsandbytes`; `uv pip install bitsandbytes==0.50.2`)
```python
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(load_in_8bit=True)

model = AutoModelForCausalLM.from_pretrained(
    "model-id",
    device_map="auto",
    quantization_config=quantization_config
)
```

Bitsandbytes is not CUDA-only: release 0.50.2 supplies Linux, Windows, and macOS ARM64 wheels, with backend/feature-specific support. CPU quantization was smoke-tested on this review host; CUDA, ROCm, XPU, Gaudi, and MPS paths were not. Check the [release installation matrix](https://huggingface.co/docs/bitsandbytes/v0.50.2/installation). Quantized inference does not itself train adapters.

**4-bit QLoRA-style loading**: use `BitsAndBytesConfig` instead of direct `load_in_4bit` arguments
```python
import torch
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_type="nf4"
)

model = AutoModelForCausalLM.from_pretrained(
    "model-id",
    quantization_config=quantization_config,
    device_map="auto"
)
```

## Model Configuration

### Loading with Custom Config

```python
from transformers import AutoConfig, AutoModel

# Load and modify config
config = AutoConfig.from_pretrained("google-bert/bert-base-uncased")
config.hidden_dropout_prob = 0.2
config.attention_probs_dropout_prob = 0.2

# Initialize model with custom config
model = AutoModel.from_pretrained("google-bert/bert-base-uncased", config=config)
```

### Initializing from Config Only

```python
config = AutoConfig.from_pretrained("openai-community/gpt2")
model = AutoModelForCausalLM.from_config(config)  # Random weights
```

## Model Modes

### Training vs Evaluation Mode

Models load in evaluation mode by default:

```python
model = AutoModel.from_pretrained("model-id")
print(model.training)  # False

# Switch to training mode
model.train(True)

# Switch back to evaluation mode (equivalent to eval mode on nn.Module)
model.train(False)
```

Evaluation mode disables dropout and uses stored batch norm statistics where those layers exist. It does not disable autograd; use `torch.inference_mode()` for inference. `model.train(False)` is equivalent to `model.eval()` in PyTorch.

## Saving Models

### Save Locally

```python
model.save_pretrained("./my_model")
```

This creates:
- `config.json`: Model configuration
- `model.safetensors` (or shards plus an index): Model weights

Save the matching tokenizer/processor too. v5 saves safetensors; `safe_serialization` is no longer a public control. Legacy pickle-based loading is a separate compatibility/security consideration.

### Save to Hugging Face Hub

```python
model.push_to_hub("username/model-name")

# With custom commit message
model.push_to_hub("username/model-name", commit_message="Update model")

# Private repository
model.push_to_hub("username/model-name", private=True)
```

## Model Inspection

### Parameter Count

```python
# Total parameters
total_params = model.num_parameters()

# Trainable parameters only
trainable_params = model.num_parameters(only_trainable=True)

print(f"Total: {total_params:,}")
print(f"Trainable: {trainable_params:,}")
```

### Memory Footprint

```python
memory_bytes = model.get_memory_footprint()
memory_mb = memory_bytes / 1024**2
print(f"Memory: {memory_mb:.2f} MB")
```

### Model Architecture

```python
print(model)  # Print full architecture

# Access specific components
print(model.config)
print(model.base_model)
```

## Forward Pass

Basic inference:

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("model-id")
model = AutoModelForSequenceClassification.from_pretrained("model-id")

import torch
inputs = tokenizer("Sample text", return_tensors="pt").to(model.device)
model.eval()
with torch.inference_mode():
    outputs = model(**inputs)

logits = outputs.logits
predictions = logits.argmax(dim=-1)
```

## Model Formats

### SafeTensors vs PyTorch

SafeTensors is faster and safer:

```python
# Save as safetensors (recommended)
model.save_pretrained("./model")

# Reload this local safetensors export
model = AutoModel.from_pretrained("./model")
```

### ONNX Export

The legacy `transformers.onnx` exporter is removed. Use the separate [Optimum ONNX exporter](https://huggingface.co/docs/optimum-onnx/onnx/usage_guides/export_a_model) in its own compatible environment. Illustrative CLI (export/runtime not executed in this review):

```bash
uv pip install "optimum-onnx[onnxruntime]"
optimum-cli export onnx --model distilbert/distilbert-base-uncased-finetuned-sst-2-english --task text-classification ./onnx-model
```

Check that the chosen architecture/opset is supported and compare ONNX outputs with the original model on representative inputs; successful conversion alone does not validate numerical equivalence.

## Best Practices

1. **Use AutoModel classes**: Automatic architecture detection
2. **Specify `dtype` explicitly**: Control precision and memory (avoid deprecated `torch_dtype` in new code)
3. **Use device_map="auto"**: For large models
4. **Inspect dispatch**: Bound `max_memory` and disk offload; do not use inference dispatch as a training strategy
5. **Use safetensors format**: Faster and safer serialization
6. **Check model.training**: Ensure correct mode for task
7. **Consider quantization**: For deployment on resource-constrained devices
8. **Cache models locally**: Set `HF_HOME` (Hub cache at `$HF_HOME/hub`)

## Common Issues

**CUDA out of memory:**
```python
import torch
from transformers import BitsAndBytesConfig

# Use smaller precision
model = AutoModel.from_pretrained("model-id", dtype=torch.float16)

# Or use quantization
quantization_config = BitsAndBytesConfig(load_in_8bit=True)
model = AutoModel.from_pretrained("model-id", quantization_config=quantization_config)

# Or use CPU
model = AutoModel.from_pretrained("model-id", device_map="cpu")
```

**Slow loading:** Reuse an existing cached snapshot, inspect download/disk/dispatch costs, and avoid repeatedly initializing the model. `low_cpu_mem_usage` does not change v5 loading.

**Model not found:**
```python
# Verify the exact repository ID on huggingface.co
# Check authentication for private models
from huggingface_hub import login
login()
```
