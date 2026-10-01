# Smart Iterative Refinement

The generate-review-refine loop, the command-line reference, and configuration.

## Smart Iterative Refinement

The diagram below shows the successful review path. If generation fails, the loop stops
without replaying the paid call; the latest saved draft is retained. If review produces
no usable score or verdict, the loop stops with quality unverified. A verdict requesting
changes can trigger refinement even without a score. A saved PNG is not a factual check.

### How It Works

```text
Generate PNG with Nano Banana 2
    -> Review with Gemini 3.7 Flash
    -> Score meets target AND no improvements requested?
       YES: retain PNG, quality_met=true
       NO: refine prompt while budget remains
           (otherwise retain draft, quality_met=false)
```

### Quality Review Criteria

Gemini 3.7 Flash evaluates each infographic on:

1. **Visual Hierarchy & Layout** (0-2 points)
   - Clear visual hierarchy
   - Logical reading flow
   - Balanced composition

2. **Typography & Readability** (0-2 points)
   - Readable text
   - Bold headlines
   - No overlapping

3. **Data Visualization** (0-2 points)
   - Prominent numbers
   - Clear charts/icons
   - Proper labels

4. **Color & Accessibility** (0-2 points)
   - Professional colors
   - Sufficient contrast
   - Colorblind-friendly

5. **Overall Impact** (0-2 points)
   - Professional appearance
   - Free of visual bugs
   - Achieves communication goal

### Review Log

Each generation produces a JSON review log:
```json
{
  "user_prompt": "5 benefits of exercise...",
  "infographic_type": "list",
  "style": "healthcare",
  "doc_type": "marketing",
  "quality_threshold": 8.5,
  "iterations": [
    {
      "iteration": 1,
      "image_path": "figures/exercise_v1.png",
      "score": 8.7,
      "needs_improvement": false,
      "critique": "SCORE: 8.7\nSTRENGTHS:..."
    }
  ],
  "final_score": 8.7,
  "quality_met": true,
  "termination_reason": "quality_met",
  "image_model": "google/gemini-3.1-flash-image",
  "review_model": "google/gemini-3.7-flash",
  "early_stop": true,
  "early_stop_reason": "Quality score 8.7 meets threshold 8.5"
}
```

---

## Command-Line Reference

```bash
python skills/infographics/scripts/generate_infographic.py [OPTIONS] PROMPT

Arguments:
  PROMPT                    Description of the infographic content

Options:
  -o, --output PATH         Output .png path (required)
  -t, --type TYPE           Infographic type preset
  -s, --style STYLE         Industry style preset
  -p, --palette PALETTE     Colorblind-safe palette
  -b, --background COLOR    Background color (default: white)
  --doc-type TYPE           Document type for quality threshold
  --iterations N            Positive generation-attempt budget (default: 3)
  -r, --research           Gather candidate facts with Sonar Pro
  --context-image PATH     Reference image; repeat up to 14 times
  --api-key KEY             OpenRouter API key
  -v, --verbose             Verbose output
  --list-options            List all available options
```

`success` means a draft was saved. `quality_met` is true only for a usable score at or
above the target with no requested improvements. `termination_reason` is `quality_met`,
`review_unavailable`, `max_iterations`, or `generation_failed`. Even a passing score
requires source, spelling, number, geometry, contrast, and accessibility checks.

`--context-image` supports local PNG, JPEG, GIF, and WebP references, sent as base64
`input_references` to the Image API. Up to 14 references are supported by the currently
reviewed Gemini providers; the script sends one output request per iteration. Generated
PNG dimensions are provider-selected: a requested pixel size written in a prompt is not
an API-enforced size. Inspect the actual artifact before print or platform delivery.

### List All Options

```bash
python skills/infographics/scripts/generate_infographic.py --list-options
```

---

## Configuration

### API Key Setup

Set your OpenRouter API key:
```bash
export OPENROUTER_API_KEY='your_api_key_here'
```

Get an API key at: https://openrouter.ai/keys

---
