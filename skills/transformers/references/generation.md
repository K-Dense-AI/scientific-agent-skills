# Text Generation

Targets Transformers 5.18.0. Hub examples are illustrative; greedy, sampling, beam search, chat dictionaries, streaming, and static cache are tested with tiny local models. See [review evidence](review.md).

## Overview

Generate text with language models using the `generate()` method. Control output quality and style through generation strategies and parameters.

For quick prototyping, the [Pipeline API](pipelines.md) wraps tokenization and `generate()`; use `model.generate()` directly when you need custom preprocessing or decoding control.

## Basic Generation

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("openai-community/gpt2")
tokenizer = AutoTokenizer.from_pretrained("openai-community/gpt2")

# Tokenize input
inputs = tokenizer("Once upon a time", return_tensors="pt").to(model.device)

# Generate
outputs = model.generate(**inputs, max_new_tokens=50)

# Decode
text = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(text)
```

## Generation Strategies

### Greedy Decoding

Select highest probability token at each step (deterministic):

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=50,
    do_sample=False,  # Explicitly override any checkpoint sampling default
    num_beams=1
)
```

**Use for**: A non-sampling baseline. Greedy decoding does not make content factual, and exact reproducibility also depends on kernels, hardware, versions, and seeds.

### Sampling

Randomly sample from probability distribution:

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=50,
    do_sample=True,
    temperature=0.7,
    top_k=50,
    top_p=0.95
)
```

**Use for**: Creative writing, diverse outputs, open-ended generation.

### Beam Search

Explore multiple hypotheses in parallel:

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=50,
    num_beams=5,
    do_sample=False,
    early_stopping=True
)
```

**Use for**: Comparing candidate seq2seq translations or summaries. More beams do not guarantee better factuality or task quality.

### Former built-in decoding strategies

Contrastive and constrained beam search moved to Hub custom-generation repositories. Legacy `penalty_alpha` / `force_words_ids` settings are not a self-contained offline implementation. Prefer the built-in greedy/sampling/beam paths unless you intentionally review the external implementation and dependencies, pin its code revision, and authorize custom code. See the [current generation strategy guide](https://huggingface.co/docs/transformers/en/generation_strategies); this skill does not execute Hub custom-generation code.

## Key Parameters

### Length Control

**max_new_tokens**: Maximum tokens to generate
```python
max_new_tokens=100  # Generate up to 100 new tokens
```

**max_length**: Total decoder sequence length (prompt + output for decoder-only models; decoder-side length for encoder-decoder models). `max_new_tokens` takes precedence.
```python
max_length=512  # Total sequence length
```

**min_new_tokens**: Minimum tokens to generate
```python
min_new_tokens=50  # Force at least 50 tokens
```

**min_length**: Minimum total length
```python
min_length=100
```

### Temperature

Controls randomness (only with sampling):

```python
temperature=1.0   # Default, balanced
temperature=0.7   # More focused, less random
temperature=1.5   # More creative, more random
```

Lower temperature → more deterministic
Higher temperature → more random

### Top-K Sampling

Consider only top K most likely tokens:

```python
do_sample=True
top_k=50  # Sample from top 50 tokens
```

**Common values**: 40-100 for balanced output, 10-20 for focused output.

### Top-P (Nucleus) Sampling

Consider tokens with cumulative probability ≥ P:

```python
do_sample=True
top_p=0.95  # Sample from smallest set with 95% cumulative probability
```

**Common values**: 0.9-0.95 for balanced, 0.7-0.85 for focused.

### Repetition Penalty

Discourage repetition:

```python
repetition_penalty=1.2  # Penalize repeated tokens
```

**Values**: 1.0 = no penalty, 1.2-1.5 = moderate, 2.0+ = strong penalty.

### Beam Search Parameters

**num_beams**: Number of beams
```python
num_beams=5  # Keep 5 hypotheses
```

**early_stopping**: Stop when num_beams sentences are finished
```python
early_stopping=True
```

**no_repeat_ngram_size**: Prevent n-gram repetition
```python
no_repeat_ngram_size=3  # Don't repeat any 3-gram
```

### Output Control

**num_return_sequences**: Generate multiple outputs
```python
outputs = model.generate(
    **inputs,
    max_new_tokens=50,
    num_beams=5,
    do_sample=False,
    num_return_sequences=3  # Must not exceed num_beams here; uniqueness is not guaranteed
)
```

**pad_token_id**: Specify padding token
```python
pad_token_id=tokenizer.eos_token_id
```

**eos_token_id**: Stop generation at specific token
```python
eos_token_id=tokenizer.eos_token_id
```

## Advanced Features

### Batch Generation

Generate for multiple prompts:

```python
prompts = ["Hello, my name is", "Once upon a time"]
# Decoder-only batch generation uses left padding; this is not a training rule.
tokenizer.padding_side = "left"
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
inputs = tokenizer(prompts, return_tensors="pt", padding=True).to(model.device)

outputs = model.generate(**inputs, max_new_tokens=50, pad_token_id=tokenizer.pad_token_id)

for i, output in enumerate(outputs):
    text = tokenizer.decode(output[inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Prompt {i}: {text}\n")
```

### Streaming Generation

`TextStreamer` writes decoded chunks synchronously:

```python
from transformers import TextStreamer

streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
outputs = model.generate(**inputs, streamer=streamer, max_new_tokens=32, num_beams=1)
```

For UI iteration, `TextIteratorStreamer(tokenizer, timeout=30.0, skip_prompt=True)` is consumed concurrently with `generate()` in a worker thread. A timeout raises `queue.Empty`; capture and propagate the worker exception, join/clean up the worker, and do not treat timeout as a completed answer. Streamers do not support beam search. Chunk boundaries are not guaranteed to equal token boundaries.

### Guidance and Control

**Prevent bad words:**
```python
bad_words = ["offensive", "inappropriate"]
bad_words_ids = [tokenizer.encode(word, add_special_tokens=False) for word in bad_words]

outputs = model.generate(
    **inputs,
    bad_words_ids=bad_words_ids
)
```

### Generation Config

Save and reuse generation parameters:

```python
from transformers import GenerationConfig

# Create config
generation_config = GenerationConfig(
    max_new_tokens=100,
    temperature=0.7,
    top_k=50,
    top_p=0.95,
    do_sample=True
)

# Save
generation_config.save_pretrained("./my_generation_config")

# Load and use
generation_config = GenerationConfig.from_pretrained("./my_generation_config")
outputs = model.generate(**inputs, generation_config=generation_config)
```

## Model-Specific Generation

### Chat Models

Use a checkpoint with a saved chat template (plain GPT-2 does not provide one). In v5 `apply_chat_template(..., tokenize=True)` returns `BatchEncoding`; unpack it and keep its attention mask:

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
]

inputs = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors="pt"
).to(model.device)

outputs = model.generate(**inputs, max_new_tokens=100)
response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
```

### Encoder-Decoder Models

For T5, BART, etc.:

```python
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

model = AutoModelForSeq2SeqLM.from_pretrained("google-t5/t5-small")
tokenizer = AutoTokenizer.from_pretrained("google-t5/t5-small")

# T5 uses task prefixes
input_text = "translate English to French: Hello, how are you?"
inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

outputs = model.generate(**inputs, max_new_tokens=50)
translation = tokenizer.decode(outputs[0], skip_special_tokens=True)
```

## Optimization

### Caching

Enable KV cache for faster generation:

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    use_cache=True  # Default, faster generation
)
```

### Static Cache

For a supported architecture, allocate capacity for the full decoder sequence. Cache memory is allocated lazily; old `max_batch_size` and `device` kwargs are not required:

```python
from transformers import StaticCache

cache = StaticCache(config=model.config, max_cache_len=inputs["input_ids"].shape[1] + 100)

outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    past_key_values=cache
)
```

### Attention Implementation

Use Flash Attention for speed:

```python
model = AutoModelForCausalLM.from_pretrained(
    "model-id",
    attn_implementation="flash_attention_2"
)
```

## Generation Recipes

### Creative Writing

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=200,
    do_sample=True,
    temperature=0.8,
    top_k=50,
    top_p=0.95,
    repetition_penalty=1.2
)
```

### Non-sampling Baseline

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    do_sample=False,  # Greedy
    repetition_penalty=1.1
)
```

### Diverse Outputs

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    num_beams=5,
    num_return_sequences=5,
    temperature=1.5,
    do_sample=True
)
```

### Long-Form Generation

Check prompt length plus token budget against the model context window; larger output budgets consume cache memory.

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=1000,
    do_sample=True,
    temperature=0.8,
    top_p=0.95,
    repetition_penalty=1.2
)
```

### Translation/Summarization

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    num_beams=5,
    do_sample=False,
    early_stopping=True,
    no_repeat_ngram_size=3
)
```

## Common Issues

**Repetitive output:**
- Increase repetition_penalty (1.2-1.5)
- Use no_repeat_ngram_size (2-3)
- Inspect the prompt/template and repeated-token distribution
- Lower temperature

**Poor quality:**
- Use beam search (num_beams=5)
- Lower temperature
- Adjust top_k/top_p

**Too deterministic:**
- Enable sampling (do_sample=True)
- Increase temperature (0.7-1.0)
- Adjust top_k/top_p

**Slow generation:**
- Reduce batch size
- Enable use_cache=True
- Use Flash Attention
- Reduce max_new_tokens

## Best Practices

1. **Start with defaults**: Then tune based on output
2. **Evaluate the strategy**: Use held-out task metrics and check factual claims against evidence
3. **Set max_new_tokens**: Avoid unnecessarily long generation
4. **Enable caching**: For faster sequential generation
5. **Tune temperature**: Most impactful parameter for sampling
6. **Use beam search carefully**: More memory/compute; benchmark whether it improves task quality
7. **Test different seeds**: For reproducibility with sampling
8. **Monitor memory**: Large beams use significant memory
