# AI-Assisted Curation Reference

Use vision-language models to analyze spike-sorting visualizations for borderline units,
complementing quantitative quality metrics.

```
Traditional:  Metrics → Threshold → Labels
AI-Enhanced:  Metrics → Render plots → Vision model → Confidence → Labels
```

> **Credential safety:** never hardcode API keys in analysis scripts — they end up in
> version control and logs. Read them from environment variables that you set in your shell
> (e.g. `export ANTHROPIC_API_KEY=...`). All examples below follow this pattern.

## Agent integration (no API key needed)

When you run this skill inside an agent (Cursor, Claude Code, etc.), the agent can inspect
images directly. Generate a unit summary figure and ask the agent to assess it:

```python
import spikeinterface.widgets as sw
import matplotlib.pyplot as plt

sw.plot_unit_summary(analyzer, unit_id=0)
plt.savefig("unit_0_summary.png", dpi=150, bbox_inches="tight")
# Then ask the agent: "Is unit 0 a well-isolated single unit, MUA, or noise? Consider
# waveform consistency, the refractory gap in the autocorrelogram, and amplitude stability."
```

The agent can assess waveform shape/consistency, refractory-period violations, amplitude
stability over time, and overall isolation quality.

## Programmatic API access

### Render a unit summary image

```python
import io, base64
import matplotlib.pyplot as plt
import spikeinterface.widgets as sw

def render_unit_image(analyzer, unit_id) -> str:
    """Return a base64-encoded PNG summary for one unit."""
    fig = plt.figure(figsize=(12, 8))
    sw.plot_unit_summary(analyzer, unit_id=unit_id, figure=fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")
```

### Anthropic (Claude) example

```python
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])  # set in shell, not in code

PROMPT = (
    "You are an expert electrophysiologist curating a spike-sorted unit. "
    "Based on the waveform, template, autocorrelogram, amplitude-over-time, and ISI "
    "histogram, classify this unit as exactly one of: good (well-isolated single unit), "
    "mua (multi-unit), or noise. Reply with the label and a one-sentence justification."
)

def analyze_unit_visually(analyzer, unit_id, model="claude-opus-4-5"):
    img_b64 = render_unit_image(analyzer, unit_id)
    msg = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    )
    return msg.content[0].text

print(analyze_unit_visually(analyzer, unit_id=0))
```

### OpenAI example

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def analyze_unit_visually_openai(analyzer, unit_id, model="gpt-4o"):
    img_b64 = render_unit_image(analyzer, unit_id)
    resp = client.responses.create(
        model=model,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
                {"type": "input_image", "image_url": f"data:image/png;base64,{img_b64}"},
            ],
        }],
    )
    return resp.output_text
```

> Model names change frequently. Use your provider's current vision-capable model
> (e.g. a current Claude or GPT multimodal model) rather than an old preview ID.

## Cost optimization: only call the model on uncertain units

```python
uncertain = metrics.query(
    "snr > 2 and snr < 8 and isi_violations_ratio > 0.001 and isi_violations_ratio < 0.1"
).index.tolist()

ai_labels = {}
for uid in uncertain:
    ai_labels[uid] = analyze_unit_visually(analyzer, uid)
```

## Hybrid curation: metrics + AI

```python
def hybrid_curation(analyzer, metrics):
    labels = {}
    for unit_id in metrics.index:
        row = metrics.loc[unit_id]
        if row["snr"] > 10 and row["isi_violations_ratio"] < 0.001:
            labels[unit_id] = "good"          # clearly good from metrics
        elif row["snr"] < 1.5:
            labels[unit_id] = "noise"         # clearly noise from metrics
        else:
            labels[unit_id] = analyze_unit_visually(analyzer, unit_id)  # ask the model
    return labels
```

## What each panel tells you

| Panel | Content | What to look for |
|-------|---------|------------------|
| Waveforms | Individual spike waveforms | Consistency, shape |
| Template | Mean ± std | Clean negative peak, physiological shape |
| Autocorrelogram | Spike timing | Gap at 0 ms (refractory period) |
| Amplitudes | Amplitude over time | Stability, no drift |
| ISI histogram | Inter-spike intervals | Refractory gap < ~1.5 ms |

## Best Practices

1. **Use AI for uncertain cases** — don't spend API calls on obvious good/noise units.
2. **Combine with metrics and model-based curation** — AI supplements, not replaces,
   quantitative measures (see [AUTOMATED_CURATION.md](AUTOMATED_CURATION.md)).
3. **Keep a human in the loop** for important analyses.
4. **Record reasoning** for each decision for reproducibility.
5. **Never commit credentials** — keep keys in environment variables.

## References

- [Anthropic Vision API](https://docs.anthropic.com/en/docs/build-with-claude/vision)
- [OpenAI Vision/Images](https://platform.openai.com/docs/guides/images-vision)
- [SpikeInterface model-based curation](https://spikeinterface.readthedocs.io/en/stable/tutorials/curation/plot_1_automated_curation.html)
- [SpikeAgent](https://github.com/SpikeAgent/SpikeAgent) — AI-powered spike-sorting assistant
