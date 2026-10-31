# Pipeline API Reference

Targets Transformers 5.18.0. Pretrained examples below are illustrative; the local regression suite checks pipeline behavior with small random models. See [review evidence](review.md).

## Overview

Pipelines provide the simplest way to use pre-trained models for inference. They abstract away tokenization, model loading, and post-processing, offering a unified interface for dozens of tasks.

## Basic Usage

Create a pipeline by specifying a task:

```python
from transformers import pipeline

# Explicit checkpoints avoid changing task defaults. Pin revision to a reviewed commit for research.
pipe = pipeline("text-classification", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
result = pipe("This is great!")
```

Or specify a model:

```python
pipe = pipeline("text-classification", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
```

## Supported Tasks

### Natural Language Processing

**text-generation**: Generate text continuations
```python
generator = pipeline("text-generation", model="openai-community/gpt2")
output = generator("Once upon a time", max_new_tokens=50, do_sample=True, num_return_sequences=2)
```

**text-classification**: Classify text into categories
```python
classifier = pipeline("text-classification", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
result = classifier("I love this product!")  # Returns label and score
```

**token-classification**: Label individual tokens (NER, POS tagging)
```python
ner = pipeline("token-classification", model="dslim/bert-base-NER")
entities = ner("Hugging Face is based in New York City")
```

**Extractive question answering:** the old `question-answering` pipeline is removed. For extractive semantics, load `AutoModelForQuestionAnswering`, tokenize question/context with `truncation="only_second"`, and decode valid context spans from start/end logits using offset and sequence-ID mappings. Long documents require overlapping windows and alignment back to the original text; independent argmax can produce an invalid span. Generative QA via a chat model does not supply equivalent calibrated answer spans.

**fill-mask**: Predict masked tokens
```python
unmasker = pipeline("fill-mask", model="google-bert/bert-base-uncased")
result = unmasker("Paris is the [MASK] of France")
```

**Summarization and translation:** `summarization`, `translation*`, and `text2text-generation` pipelines are removed. Existing seq2seq checkpoints still use `AutoModelForSeq2SeqLM.generate()` (see [generation](generation.md)). For instruction-based generation, use a chat checkpoint:

```python
summarizer = pipeline("text-generation", model="Qwen/Qwen2.5-0.5B-Instruct")
messages = [{"role": "user", "content": "Summarize this text: [replace with the source text]"}]
summary = summarizer(messages, max_new_tokens=128, do_sample=False)
print(summary[0]["generated_text"][-1]["content"])
```

**zero-shot-classification**: Classify without training data
```python
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
result = classifier(
    "This is a course about Python programming",
    candidate_labels=["education", "politics", "business"]
)
```

**sentiment-analysis**: Alias for text-classification focused on sentiment
```python
sentiment = pipeline("sentiment-analysis", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
result = sentiment("This product exceeded my expectations!")
```

### Computer Vision

**image-classification**: Classify images
```python
classifier = pipeline("image-classification", model="google/vit-base-patch16-224")
result = classifier("path/to/image.jpg")
# Or use PIL Image or URL
from PIL import Image
result = classifier(Image.open("image.jpg"))
```

**object-detection**: Detect objects in images
```python
detector = pipeline("object-detection", model="facebook/detr-resnet-50")
results = detector("image.jpg")  # Returns bounding boxes and labels
```

**image-segmentation**: Segment images
```python
segmenter = pipeline("image-segmentation", model="facebook/detr-resnet-50-panoptic")
segments = segmenter("image.jpg")
```

**depth-estimation**: Estimate depth from images
```python
depth = pipeline("depth-estimation", model="Intel/dpt-large")
result = depth("image.jpg")
```

For DPT, use `predicted_depth` for the raw tensor. The `depth` PIL output is a per-image min-max visualization, not metric distance; constant depth can make that normalization degenerate. Preserve preprocessing/resolution and do not infer meters without a metric-depth model/calibration.

**zero-shot-image-classification**: Classify images without training
```python
classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
result = classifier("image.jpg", candidate_labels=["cat", "dog", "bird"])
```

CLIP scores are normalized over the supplied candidate prompts; changing that set changes scores. They are not an open-world detection probability.

### Audio

**automatic-speech-recognition**: Transcribe speech
```python
asr = pipeline("automatic-speech-recognition", model="openai/whisper-base")
text = asr("audio.mp3")
```

**audio-classification**: Classify audio
```python
classifier = pipeline("audio-classification", model="MIT/ast-finetuned-audioset-10-10-0.4593")
result = classifier("audio.wav", function_to_apply="sigmoid", top_k=5)
```

AudioSet AST predicts potentially simultaneous events: use independent sigmoid scores. The audio-classification pipeline otherwise defaults to softmax, which forces competition between labels. Match postprocessing to the checkpoint's training objective; neither score is automatically calibrated.

**text-to-speech**: Generate speech from text (with specific models)
```python
tts = pipeline("text-to-speech", model="facebook/mms-tts-eng")
audio = tts("Hello, this is a test")
# audio["audio"] is a waveform array; audio["sampling_rate"] supplies its rate.
```

### Multimodal

**image-text-to-text**: Generative captions or visual questions. The former `visual-question-answering` and `image-to-text` pipelines are removed. Put images inside message content; do not pass a separate images argument alongside chats.

```python
captioner = pipeline("image-text-to-text", model="Qwen/Qwen3-VL-2B-Instruct")
messages = [{"role": "user", "content": [
    {"type": "image", "image": "image.jpg"},
    {"type": "text", "text": "Describe this image."},
]}]
caption = captioner(messages, max_new_tokens=64)
```

**document-question-answering**: Answer questions about documents
```python
doc_qa = pipeline("document-question-answering", model="impira/layoutlm-document-qa")
result = doc_qa(image="document.png", question="What is the invoice number?")
```

LayoutLM document QA requires OCR dependencies (`pytesseract` and a Tesseract executable) unless supplying supported precomputed word/box inputs; OCR boxes and image coordinates must agree. A local image file alone is not a preprocessed document.

## Pipeline Parameters

### Common Parameters

**model**: Model identifier or path
```python
pipe = pipeline("task", model="model-id")
```

**device**: CPU/device string, `torch.device`, or accelerator index (-1 means CPU). Never combine an explicit `device` with Accelerate `device_map` dispatch.
```python
pipe = pipeline("task", device=0)  # Use first GPU
```

**device_map**: Automatic device allocation for large models
```python
pipe = pipeline("task", model="large-model", device_map="auto")
```

**dtype**: Model precision (reduces memory; `torch_dtype` is deprecated but still accepted)
```python
import torch
pipe = pipeline("task", dtype=torch.float16)
```

**batch_size**: Process multiple inputs at once
```python
pipe = pipeline("task", batch_size=8)
results = pipe(["text1", "text2", "text3"])
```

**Backend**: Transformers v5 pipelines use PyTorch only (TensorFlow/JAX backends were removed in v5).

## Batch Processing

Process multiple inputs efficiently:

```python
classifier = pipeline("text-classification", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
texts = ["Great product!", "Terrible experience", "Just okay"]
results = classifier(texts)
```

For large datasets, use generators or KeyDataset:

```python
from transformers.pipelines.pt_utils import KeyDataset
import datasets

dataset = datasets.load_dataset("dataset-name", split="test")
pipe = pipeline("task", device=0)

for output in pipe(KeyDataset(dataset, "text")):
    print(output)
```

## Performance Optimization

### GPU Acceleration

Always specify device for GPU usage:
```python
pipe = pipeline("task", device=0)
```

### Mixed Precision

Half precision may reduce memory and improve speed on supported hardware; measure accuracy, latency, and throughput for the actual workload:
```python
import torch
pipe = pipeline("task", dtype=torch.float16, device=0)
```

### Batching Guidelines

- **CPU**: Usually skip batching
- **GPU with variable lengths**: May reduce efficiency
- **GPU with similar lengths**: Significant speedup
- **Real-time applications**: Skip batching (increases latency)

```python
# Good for throughput
pipe = pipeline("task", batch_size=32, device=0)
results = pipe(list_of_texts)
```

### Streaming Output

For text generation, stream tokens as they're generated:

```python
from transformers import AutoTokenizer, TextStreamer, pipeline

tokenizer = AutoTokenizer.from_pretrained("openai-community/gpt2")
streamer = TextStreamer(tokenizer)
generator = pipeline("text-generation", model="openai-community/gpt2", streamer=streamer)
generator("The future of AI", max_new_tokens=100)
```

## Custom Pipeline Configuration

Specify tokenizer and model separately:

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

tokenizer = AutoTokenizer.from_pretrained("model-id")
model = AutoModelForSequenceClassification.from_pretrained("model-id")
pipe = pipeline("text-classification", model=model, tokenizer=tokenizer)
```

Use custom pipeline classes:

```python
from transformers import TextClassificationPipeline

class CustomPipeline(TextClassificationPipeline):
    def postprocess(self, model_outputs, **kwargs):
        # Custom post-processing
        return super().postprocess(model_outputs, **kwargs)

pipe = pipeline("text-classification", model="model-id", pipeline_class=CustomPipeline)
```

## Input Formats

Pipelines accept various input types:

**Text tasks**: Strings or lists of strings
```python
pipe("single text")
pipe(["text1", "text2"])
```

**Image tasks**: URLs, file paths, or PIL Images. Convert NumPy arrays to a correctly scaled/color-ordered PIL image; arbitrary arrays are not universally accepted.
```python
pipe("https://example.com/image.jpg")
pipe("local/path/image.png")
from PIL import Image
pipe(Image.open("image.jpg").convert("RGB"))
# For a uint8 HWC RGB NumPy array:
pipe(Image.fromarray(rgb_array))
```

**Audio tasks**: Encoded file paths/bytes require FFmpeg for relevant pipelines. A raw NumPy waveform must already have the expected sampling rate; use a sampling-rate dictionary where the task supports it.
```python
pipe("audio.mp3")
pipe({"array": audio_array, "sampling_rate": actual_sampling_rate})
```

## Error Handling

For GPU memory errors, reduce the actual batch/context/token budget or recreate the same checkpoint on a supported device. Catch `torch.OutOfMemoryError` only when providing a real retry path; do not silently swap to a task default model. Re-raise unexpected exceptions. Missing files can mean a wrong revision, incomplete local snapshot, missing permissions, or an incompatible task head; inspect the underlying error.

## Best Practices

1. **Use pipelines for prototyping**: Fast iteration without boilerplate
2. **Specify models explicitly**: Default models may change
3. **Enable GPU when available**: Significant speedup
4. **Use batching for throughput**: When processing many inputs
5. **Consider memory usage**: Use float16 or smaller models for large batches
6. **Cache models locally**: Avoid repeated downloads
