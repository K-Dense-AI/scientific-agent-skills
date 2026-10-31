# Smart Iterative Refinement Workflow

How the generate-review-refine loop works: the initial generation, the quality review,
the decision to continue or stop, subsequent iterations, and the review log. Then the
advanced generation options (Python API, command-line options, prompt engineering) and
four worked examples.

## Smart Iterative Refinement Workflow

The AI generation system uses **smart iteration** - it regenerates when the score is below the local document threshold or the reviewer explicitly requests improvement, within the two-attempt budget:

### How Smart Iteration Works

```text
Source-backed prompt -> Generate PNG -> Review PNG
                                        |
                    +-------------------+-------------------+
                    |                   |                   |
              Criteria met       Improvement needed   Review unavailable
                    |                   |                   |
               Keep draft       Refine if budget left   Keep unchecked
                                (2 attempts maximum)

Generation error -> Stop; retain any earlier successful draft
All paths -> Review log -> Manual scientific and visual verification
```

### Iteration 1: Initial Generation
**Prompt Construction:**
```
Scientific diagram guidelines + User request
```

**Output:** `diagram_v1.png`

### Quality Review by Gemini 3.7 Flash

Gemini 3.7 Flash evaluates the diagram on:
1. **Scientific Accuracy** (0-2 points) - Correct concepts, notation, relationships
2. **Clarity and Readability** (0-2 points) - Easy to understand, clear hierarchy
3. **Label Quality** (0-2 points) - Complete, readable, consistent labels
4. **Layout and Composition** (0-2 points) - Logical flow, balanced, no overlaps
5. **Professional Appearance** (0-2 points) - Publication-ready quality

**Illustrative review output** (not an actual model run):
```
SCORE: 8.0

STRENGTHS:
- Clear flow from top to bottom
- All phases properly labeled
- Professional typography

ISSUES:
- Participant counts slightly small
- Minor overlap on exclusion box

VERDICT: ACCEPTABLE (for poster, threshold 7.0)
```

### Decision Point: Continue or Stop?

| If Score... | Action |
|-------------|--------|
| >= threshold and no improvement verdict | **STOP** - local review criteria met; inspect manually |
| < threshold or improvement verdict | Refine if another iteration is available |
| No usable review | Keep the image, stop, report unverified quality |
| Generation fails | Stop; retain an earlier successful image if one exists |

**Example:**
- For a **poster** (threshold 7.0): Score of 7.5 → **DONE after 1 iteration!**
- For a **journal** (threshold 8.5): Score of 7.5 → Continue improving

### Subsequent Iterations (Only If Needed)

If quality is below threshold, the system:
1. Extracts specific issues from Gemini 3.7 Flash's review
2. Enhances the prompt with improvement instructions
3. Regenerates with Nano Banana 2
4. Reviews again with Gemini 3.7 Flash
5. Repeats until threshold met or max iterations reached

### Review Log
Every attempt is saved in a JSON review log. This illustrative excerpt omits some fields:
```json
{
  "user_prompt": "CONSORT participant flow diagram...",
  "doc_type": "poster",
  "quality_threshold": 7.0,
  "iterations": [
    {
      "iteration": 1,
      "image_path": "figures/consort_v1.png",
      "score": 7.5,
      "reviewed": true,
      "review_error": null,
      "needs_improvement": false,
      "critique": "SCORE: 7.5\nSTRENGTHS:..."
    }
  ],
  "final_score": 7.5,
  "final_reviewed": true,
  "early_stop": true,
  "early_stop_reason": "Quality score 7.5 meets threshold 7.0 for poster"
}
```

**Note:** With smart iteration, you may see only 1 iteration instead of the full 2 if quality is achieved early!

### When the review does not run

The reviewer is a second model call, and it can fail on its own — a rate limit, a content filter,
an answer in a shape the parser cannot read. The image is generated first and is kept regardless;
what is missing in that case is the *measurement*, so the log says so rather than substituting a
number:

```json
{
  "iterations": [
    {
      "iteration": 1,
      "image_path": "figures/consort_v1.png",
      "score": null,
      "reviewed": false,
      "review_error": "the review model returned no choices",
      "needs_improvement": false,
      "critique": "Review unavailable: the review model returned no choices."
    }
  ],
  "final_score": null,
  "final_reviewed": false
}
```

The run exits 0 — the diagram is real — and prints
`Review unavailable - image kept, quality not verified`. It does **not** regenerate: a reviewer that
did not answer says nothing about the diagram, so another generation would be guesswork. Look at the
image yourself, and re-run if you want a score; first diagnose the failure rather than assuming another paid run will fix it.

`final_reviewed` indicates a numeric review; `quality_met` also requires the threshold and no improvement verdict. Neither means author-approved. `termination_reason` distinguishes `quality_threshold_met`, `review_unavailable`, `max_iterations`, and `generation_failed`. The selected image is the latest successful draft, not automatically the highest-scoring one. A failed second attempt does not discard the first image. A fully failed run exits 1; any retained image exits 0, even below threshold.

## Advanced AI Generation Usage

### Python API

```python
from scripts.generate_schematic_ai import ScientificSchematicGenerator

# Illustrative paid call; credentials are resolved from the environment/.env.
generator = ScientificSchematicGenerator(verbose=True)

# Generate with iterative refinement (max 2 iterations)
results = generator.generate_iterative(
    user_prompt="Transformer architecture diagram",
    output_path="figures/transformer.png",
    iterations=2
)

# Access results
print(f"Final score: {results['final_score']}/10")
print(f"Final image: {results['final_image']}")

# Review individual iterations
for iteration in results['iterations']:
    if iteration.get("success"):
        print(f"Iteration {iteration['iteration']}: {iteration['score']}/10")
        print(f"Critique: {iteration['critique']}")
    else:
        print(f"Generation error: {iteration['error']}")
```

### Command-Line Options

```bash
# Basic usage (default threshold 7.5/10)
python scripts/generate_schematic.py "diagram description" -o output.png

# Specify document type for appropriate quality threshold
python scripts/generate_schematic.py "diagram" -o out.png --doc-type journal      # 8.5/10
python scripts/generate_schematic.py "diagram" -o out.png --doc-type conference   # 8.0/10
python scripts/generate_schematic.py "diagram" -o out.png --doc-type poster       # 7.0/10
python scripts/generate_schematic.py "diagram" -o out.png --doc-type presentation # 6.5/10

# Custom max iterations (1-2)
python scripts/generate_schematic.py "complex diagram" -o diagram.png --iterations 2

# Verbose output (see all API calls and reviews)
python scripts/generate_schematic.py "flowchart" -o flow.png -v

# Combine options
python scripts/generate_schematic.py "neural network" -o nn.png --doc-type journal --iterations 2 -v
```

### Setup and Cost

```bash
# Get a key at https://openrouter.ai/keys
export OPENROUTER_API_KEY='sk-or-v1-your_key_here'

# Alternatively store OPENROUTER_API_KEY in a private, untracked .env file.
# --api-key also exists, but command-line arguments can enter shell history.

# The only Python dependency
uv pip install requests
```

Each successful generation normally makes **two API calls**: one image generation and one vision review. A diagram that
passes on the first try therefore costs two calls, and the maximum for any single run is four. A generation error stops without automatic retry. The
image model dominates the bill. Check current image-endpoint billing units and review-model pricing for
`google/gemini-3.1-flash-image` and `google/gemini-3.7-flash` on OpenRouter — it changes, and any
figure written here would go stale.

### Prompt Engineering Tips

**1. Be Specific About Layout:**
```
✓ "Flowchart with vertical flow, top to bottom"
✓ "Architecture diagram with encoder on left, decoder on right"
✓ "Circular pathway diagram with clockwise flow"
```

**2. Include Quantitative Details:**
```
✓ "Neural network with input layer (784 nodes), hidden layer (128 nodes), output (10 nodes)"
✓ "Flowchart showing n=500 screened, n=150 excluded, n=350 randomized"
✓ "Circuit with 1kΩ resistor, 10µF capacitor, 5V source"
```

**3. Specify Visual Style:**
```
✓ "Minimalist block diagram with clean lines"
✓ "Detailed biological pathway with protein structures"
✓ "Technical schematic with engineering notation"
```

**4. Request Specific Labels:**
```
✓ "Label all arrows with activation/inhibition"
✓ "Include layer dimensions in each box"
✓ "Show time progression with timestamps"
```

**5. Mention Color Requirements:**
```
✓ "Use colorblind-friendly colors"
✓ "Grayscale-compatible design"
✓ "Color-code by function: blue for input, green for processing, red for output"
```

## AI Generation Examples

These paid-generation commands are illustrative; they were not sent to OpenRouter during validation. Reconcile each scientific example with the actual experiment before use.

### Example 1: CONSORT Flowchart
```bash
python scripts/generate_schematic.py \
  "CONSORT participant flow diagram for randomized controlled trial. \
   Start with 'Assessed for eligibility (n=500)' at top. \
   Show 'Excluded (n=150)' with reasons: age<18 (n=80), declined (n=50), other (n=20). \
   Then 'Randomized (n=350)' splits into two arms: \
   'Treatment group (n=175)' and 'Control group (n=175)'. Each group received its allocated intervention (n=175); did not receive (n=0). \
   Each arm shows 'Discontinued intervention' (n=0) and 'Lost to follow-up for primary outcome' (n=15 and n=10), with illustrative reason 'outcome visit not attended'. \
   End with 'Analyzed for primary outcome' (n=160 and n=165); excluded from this analysis due to missing primary outcome (n=15 and n=10). Do not imply missing follow-up always excludes an intention-to-treat analysis. \
   Use blue boxes for process steps, orange for exclusion, green for final analysis." \
  -o figures/consort.png
```

### Example 2: Neural Network Architecture
```bash
python scripts/generate_schematic.py \
  "Transformer encoder-decoder architecture diagram. \
   Left side: Encoder stack with input embedding, positional encoding, \
   multi-head self-attention, add & norm, feed-forward, add & norm. \
   Right side: Decoder stack with output embedding, positional encoding, \
   masked self-attention, add & norm, cross-attention (receiving from encoder), \
   add & norm, feed-forward, add & norm, linear & softmax. \
   Show cross-attention connection from encoder to decoder with dashed line. \
   Use light blue for encoder, light red for decoder. \
   Label all components clearly." \
  -o figures/transformer.png --iterations 2
```

### Example 3: Biological Pathway

This simplified prompt follows the mechanism distinction in [Reactome's RAF/MAP kinase cascade](https://reactome.org/content/detail/R-HSA-5673001); it is not a complete pathway or a substitute for a curated diagram.
```bash
python scripts/generate_schematic.py \
  "MAPK signaling pathway diagram. \
   Simplified pathway: activated EGFR receptor at cell membrane (top), then GRB2/SOS. \
   Arrow to RAS-GTP labeled nucleotide exchange, then activation arrow to RAF. \
   RAF kinase node. \
   Arrow to MEK kinase. \
   Arrow to ERK kinase. \
   Final arrow to nucleus showing gene transcription. \
   Label RAF-to-MEK and MEK-to-ERK arrows phosphorylation; do not label RAS nucleotide exchange as phosphorylation. Mark this as a simplified pathway, omitting downstream transcription factors. \
   Use rounded rectangles for proteins, different colors for each. \
   Include membrane boundary line at top." \
  -o figures/mapk_pathway.png
```

### Example 4: System Architecture
```bash
python scripts/generate_schematic.py \
  "IoT system architecture block diagram. \
   Bottom layer: Sensors (temperature, humidity, motion) in green boxes. \
   Middle layer: Microcontroller (ESP32) in blue box. \
   Connections to WiFi module (orange box) and Display (purple box). \
   Top layer: Cloud server (gray box) connected to mobile app (light blue box). \
   Show data flow arrows between all components. \
   Label connections with protocols: I2C, UART, WiFi, HTTPS." \
  -o figures/iot_architecture.png
```

---

## OpenRouter contract (reviewed 2026-09-30)

- **Generate:** `POST https://openrouter.ai/api/v1/images`, JSON body `model`, `prompt`, `n: 1`, `Authorization: Bearer ...`. The non-streaming response contains `data[]` with `b64_json` and optional `media_type`; usage may include cost. The helper saves the first PNG and fails clearly for another MIME type or invalid base64/signature. It does not decode all PNG pixels or claim a DPI value.
- **Review:** `POST https://openrouter.ai/api/v1/chat/completions`, `model` plus `messages[].content` containing a `text` block and `image_url.url` data URL. Text is read from `choices[0].message.content`. These calls do not use the Image API response schema.
- **Discovery:** public `GET /api/v1/images/models` returns `data[]`; `GET /api/v1/images/models/google/gemini-3.1-flash-image/endpoints` returns `endpoints[]`. The model capability map is a union; each endpoint map is authoritative. Both current Google endpoints allow `n=1`, up to 14 input references, and resolution/aspect-ratio controls. `output_format` is absent, so this helper does not send it. Resolution and reference-image options are not exposed by this CLI.
- **Compatibility:** the current chat schema still lists image output in `modalities`; no retirement is claimed. This implementation uses the dedicated generation API described by the current guide. The helper's Gemini model calls were not tested with a paid end-to-end run.
- **Failures:** one request per attempt, 120-second Requests connect/read inactivity timeout (not a total wall-clock deadline), no automatic transport retry. JSON/API/format errors are logged. A timeout is an ambiguous remote outcome; investigate before rerunning. Model IDs and review prompts are recorded for reproducibility, but re-running is stochastic.

Official sources: [image guide](https://openrouter.ai/docs/guides/overview/multimodal/image-generation), [image request schema](https://openrouter.ai/docs/api/api-reference/images/generate-an-image), [chat schema](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion), [vision inputs](https://openrouter.ai/docs/guides/overview/multimodal/image-understanding), [image model catalog](https://openrouter.ai/api/v1/images/models), [chosen image endpoints](https://openrouter.ai/api/v1/images/models/google/gemini-3.1-flash-image/endpoints), and [general model catalog](https://openrouter.ai/api/v1/models). Public catalog/endpoint reads and offline mocked contract tests passed. No paid end-to-end run or review-quality benchmark of this helper was performed; repository workflow-diagram regeneration uses separate tooling and models.
