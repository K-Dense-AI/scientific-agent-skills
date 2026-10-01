# Training and Fine-Tuning

Targets Transformers 5.18.0 / Datasets 5.0.1 / Accelerate 1.15.0 / PEFT 0.21.2. Tiny CPU training, evaluation, checkpoint resume, collators, and LoRA are tested locally; Hub dataset/model downloads, distributed runs, trackers, and hyperparameter services are illustrative. See [review evidence](review.md).

## Overview

Fine-tune pre-trained models on custom datasets using the Trainer API. The Trainer handles training loops, gradient accumulation, mixed precision, logging, and checkpointing.

**Metrics:** `datasets.load_metric` is removed. Compute simple metrics locally; optional `evaluate.load("accuracy")` loads an external metric implementation, requires the Evaluate package/network or cache, and should be reviewed/pinned for reproducibility.

**Hub uploads:** `trainer.push_to_hub()` requires authentication (`hf auth login` or `HF_TOKEN`).

## Basic Fine-Tuning Workflow

### Step 1: Load and Preprocess Data

```python
from datasets import load_dataset

# Load dataset
dataset = load_dataset("Yelp/yelp_review_full")
# Tune only on a validation partition of training data, keeping test untouched.
split = dataset["train"].train_test_split(test_size=0.1, seed=42, stratify_by_column="label")
train_dataset = split["train"]
eval_dataset = split["test"]
test_dataset = dataset["test"]

# Tokenize
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("google-bert/bert-base-uncased")

def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=512
    )

train_dataset = train_dataset.map(tokenize_function, batched=True)
eval_dataset = eval_dataset.map(tokenize_function, batched=True)
```

### Step 2: Load Model

```python
from transformers import AutoModelForSequenceClassification

model = AutoModelForSequenceClassification.from_pretrained(
    "google-bert/bert-base-uncased",
    num_labels=5  # Number of classes
)
```

### Step 3: Define Metrics

```python
import numpy as np

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {"accuracy": float(np.mean(predictions == labels))}
```

### Step 4: Configure Training

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="./results",
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    report_to="none",  # Opt in to external trackers explicitly.
    logging_steps=10,
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
)
```

### Step 5: Create Trainer and Train

```python
from transformers import Trainer, DataCollatorWithPadding

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    compute_metrics=compute_metrics,
    processing_class=tokenizer,
    data_collator=DataCollatorWithPadding(tokenizer),
)

# Start training
trainer.train()

# Evaluate
results = trainer.evaluate()
print(results)
```

### Step 6: Save Model

```python
trainer.save_model("./fine_tuned_model")
tokenizer.save_pretrained("./fine_tuned_model")

# Optional external upload, only when intended:
# Set hub_model_id="username/my-finetuned-model" in TrainingArguments first.
# trainer.push_to_hub(commit_message="Upload fine-tuned model")
```

## TrainingArguments Parameters

### Essential Parameters

**output_dir**: Directory for checkpoints and logs
```python
output_dir="./results"
```

**num_train_epochs**: Number of training epochs
```python
num_train_epochs=3
```

**per_device_train_batch_size**: Batch size per GPU/CPU
```python
per_device_train_batch_size=8
```

**learning_rate**: Optimizer learning rate
```python
learning_rate=2e-5  # Common for BERT-style models
learning_rate=5e-5  # Common for smaller models
```

**weight_decay**: Optimizer weight decay (AdamW decouples this from the gradient; it is not generally equivalent to adding an L2 loss penalty)
```python
weight_decay=0.01
```

### Evaluation and Saving

**eval_strategy**: When to evaluate ("no", "steps", "epoch")
```python
eval_strategy="epoch"  # Evaluate after each epoch
eval_strategy="steps"  # Evaluate every eval_steps
```

**save_strategy**: When to save checkpoints
```python
save_strategy="epoch"
save_strategy="steps"
save_steps=500
```

**load_best_model_at_end**: Load best checkpoint after training
```python
load_best_model_at_end=True
metric_for_best_model="accuracy"  # Metric to compare
```

### Optimization

**gradient_accumulation_steps**: Accumulate gradients over multiple steps
```python
gradient_accumulation_steps=4  # Effective batch = per-device batch * accumulation * data-parallel workers (except partial final groups)
```

**fp16**: Enable mixed precision (NVIDIA GPUs without native bfloat16)
```python
fp16=True
```

**bf16**: Enable bfloat16 (preferred on Ampere+ and newer GPUs when supported)
```python
bf16=True
```

**gradient_checkpointing**: Trade compute for memory
```python
gradient_checkpointing=True  # Slower but uses less memory
```

**optim**: Optimizer choice
```python
optim="adamw_torch"  # Explicit portable choice; current Torch>=2.8 default is adamw_torch_fused
optim="adamw_8bit"    # 8-bit Adam (requires bitsandbytes)
optim="adafactor"     # Memory-efficient alternative
```

### Learning Rate Scheduling

**lr_scheduler_type**: Learning rate schedule
```python
lr_scheduler_type="linear"       # Linear decay
lr_scheduler_type="cosine"       # Cosine annealing
lr_scheduler_type="constant"     # No decay
lr_scheduler_type="constant_with_warmup"
```

**warmup_steps**: Integer step count or fractional ratio in [0, 1). `warmup_ratio` was removed in v5.
```python
warmup_steps=500
# Or
warmup_steps=0.1  # 10% of total steps
```

### Logging

**TensorBoard directory**: `logging_dir` was removed from TrainingArguments. Set `TENSORBOARD_LOGGING_DIR=./logs` in the environment before creating Trainer and install TensorBoard if using it.

**logging_steps**: Log every N steps
```python
logging_steps=10
```

**report_to**: Logging integrations
```python
report_to="none"  # Local-only default used here
report_to=["tensorboard"]
report_to=["wandb"]
report_to=["tensorboard", "wandb"]
```

### Distributed Training

**ddp_backend**: Distributed backend
```python
ddp_backend="nccl"  # For multi-GPU
```

**deepspeed**: DeepSpeed config file
```python
deepspeed="ds_config.json"
```

## Data Collators

Handle dynamic padding and special preprocessing:

### DataCollatorWithPadding

Pad sequences to longest in batch:
```python
from transformers import DataCollatorWithPadding

data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    data_collator=data_collator,
    eval_dataset=eval_dataset,
    processing_class=tokenizer,
)
```

### DataCollatorForLanguageModeling

For masked language modeling:
```python
from transformers import DataCollatorForLanguageModeling

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=True,
    mlm_probability=0.15
)
```

### DataCollatorForSeq2Seq

For sequence-to-sequence tasks:
```python
from transformers import DataCollatorForSeq2Seq

data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model,
    padding=True
)
```

## Custom Training

### Custom Trainer

Accept `num_items_in_batch` in the current override signature. This example uses a per-microbatch weighted mean and explicitly disables automatic loss-kwargs normalization; use accumulation=1 for its direct weighted-batch interpretation. Unequal microbatch weights/sizes need a deliberately derived accumulated denominator.

```python
import torch
from transformers import Trainer

class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = torch.as_tensor(class_weights, dtype=torch.float32)
        self.model_accepts_loss_kwargs = False

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs["labels"]
        outputs = model(**{key: value for key, value in inputs.items() if key != "labels"})
        logits = outputs.logits
        loss = torch.nn.functional.cross_entropy(
            logits, labels, weight=self.class_weights.to(device=logits.device, dtype=logits.dtype)
        )
        return (loss, outputs) if return_outputs else loss
```

### Custom Callbacks

Monitor and control training:

```python
from transformers import TrainerCallback

class CustomCallback(TrainerCallback):
    def on_epoch_end(self, args, state, control, **kwargs):
        print(f"Epoch {state.epoch} completed")
        # Custom logic here
        return control

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    processing_class=tokenizer,
    data_collator=DataCollatorWithPadding(tokenizer),
    callbacks=[CustomCallback],
)
```

## Advanced Training Techniques

### Parameter-Efficient Fine-Tuning (PEFT)

Use LoRA for efficient fine-tuning. The `query`/`value` targets below match BERT, not every architecture; inspect `named_modules()` and confirm trainable parameters. Adapter checkpoints require the correct base checkpoint and revision to reload.

```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["query", "value"],
    lora_dropout=0.05,
    bias="none",
    task_type="SEQ_CLS"
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # Shows reduced parameter count

# Train normally with Trainer
trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset,
                  eval_dataset=eval_dataset, processing_class=tokenizer,
                  data_collator=DataCollatorWithPadding(tokenizer))
trainer.train()
```

### Gradient Checkpointing

Reduce memory at cost of speed:

```python
model.gradient_checkpointing_enable()

training_args = TrainingArguments(
    output_dir="./checkpointed-results",
    gradient_checkpointing=True,
    report_to="none",
)
```

### Mixed Precision Training

```python
training_args = TrainingArguments(
    output_dir="./mixed-precision-results",
    bf16=True,  # Only on a backend that supports it; use fp16=True as an alternative.
    report_to="none",
)
```

### DeepSpeed Integration

Optional backend-dependent path, not run on this CPU audit. Save the following as `ds_config.json`; install a compatible DeepSpeed build and launch under its distributed runner. Auto fields let Trainer supply matching values. `device_map="auto"` is not a replacement for distributed training.

```json
{
  "train_batch_size": "auto",
  "train_micro_batch_size_per_gpu": "auto",
  "gradient_accumulation_steps": "auto",
  "optimizer": {"type": "AdamW", "params": {"lr": "auto"}},
  "bf16": {"enabled": "auto"},
  "zero_optimization": {"stage": 2}
}
```

```python
training_args = TrainingArguments(
    output_dir="./distributed-results",
    deepspeed="ds_config.json",
    report_to="none",
)
```

## Training Tips

### Hyperparameter Tuning

Common starting points:
- **Learning rate**: 2e-5 to 5e-5 for BERT-like models, 1e-4 to 1e-3 for smaller models
- **Batch size**: 8-32 depending on GPU memory
- **Epochs**: 2-4 for fine-tuning, more for domain adaptation
- **Warmup**: 10% of total steps

Illustrative local Optuna search (`uv pip install optuna`); do not tune against the held-out test dataset:

```python
def model_init():
    return AutoModelForSequenceClassification.from_pretrained(
        "google-bert/bert-base-uncased",
        num_labels=5
    )

def optuna_hp_space(trial):
    return {
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 5e-5, log=True),
        "per_device_train_batch_size": trial.suggest_categorical("per_device_train_batch_size", [8, 16, 32]),
        "num_train_epochs": trial.suggest_int("num_train_epochs", 2, 5),
    }

trainer = Trainer(model_init=model_init, args=training_args, train_dataset=train_dataset,
                  eval_dataset=eval_dataset, compute_metrics=compute_metrics,
                  processing_class=tokenizer, data_collator=DataCollatorWithPadding(tokenizer))
best_trial = trainer.hyperparameter_search(
    direction="maximize",
    backend="optuna",
    hp_space=optuna_hp_space,
    n_trials=10,
)
```

### Monitoring Training

Use TensorBoard:
```bash
tensorboard --logdir ./logs  # Match TENSORBOARD_LOGGING_DIR used by training
```

Optional Weights & Biases integration (`uv pip install wandb`); this sends run metadata to the configured service unless explicitly configured offline:
```python
import wandb
wandb.init(project="my-project")

training_args = TrainingArguments(
    output_dir="./tracked-results",
    report_to=["wandb"],
)
```

### Resume Training

Resume from checkpoint:
```python
trainer.train(resume_from_checkpoint="./results/checkpoint-1000")
```

## Common Issues

**CUDA out of memory:**
- Reduce batch size
- Enable gradient checkpointing
- Use gradient accumulation
- Use 8-bit optimizers

**Overfitting:**
- Increase weight_decay
- Add dropout
- Use early stopping
- Reduce model size or training epochs

**Slow training:**
- Increase batch size
- Enable mixed precision (fp16/bf16)
- Use multiple GPUs
- Optimize data loading

## Best Practices

1. **Start small**: Test on small dataset subset first
2. **Use evaluation**: Monitor validation metrics
3. **Save checkpoints**: Enable save_strategy
4. **Log extensively**: Use TensorBoard or W&B
5. **Try different learning rates**: Start with 2e-5
6. **Use warmup**: Helps training stability
7. **Enable mixed precision**: Faster training
8. **Consider PEFT**: For large models with limited resources

## Label and evaluation checks

- Preserve the dataset's integer-label mapping in `model.config.id2label`/`label2id`; a resized/random classification head requires training before meaningful predictions.
- For token classification, align words/subtokens and mask ignored positions with -100. For seq2seq, tokenize targets with `text_target` and pad labels with -100 through `DataCollatorForSeq2Seq`.
- `DataCollatorForLanguageModeling(mlm=False)` masks every occurrence of `pad_token_id` in labels. If EOS doubles as PAD, genuine EOS labels are lost; use a distinct pad token (resize embeddings) or mask by `attention_mask` in a task-specific collator.
- Best-checkpoint loading requires compatible evaluation/save schedules; for step schedules, `save_steps` must be a multiple of `eval_steps`.
- A model/tokenizer export is not a resumable Trainer checkpoint with optimizer/scheduler/RNG state. Resume from an actual `checkpoint-*` directory with matching data and training settings.
- Report class-specific metrics/calibration and leakage controls as appropriate; one tiny successful training step is only a mechanics check.
