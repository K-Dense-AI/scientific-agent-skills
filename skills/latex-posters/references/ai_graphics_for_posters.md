# AI Graphics for Posters

AI generation is optional and appropriate for conceptual illustrations. Scientific
results come from analysis code and original observations. Use the scientific-schematics
skill for detailed diagram authoring when available, or the helpers shipped here.

## Choose the correct visual source

| Visual | Recommended source | Required checks |
| --- | --- | --- |
| Numerical plot, statistical summary | Analysis code and verified data | Values, units, scales, uncertainty, sample size, provenance |
| Microscopy, spectra, instrument data | Original research output | Faithful processing, scale bars, provenance |
| Exact pathway, workflow, architecture | TikZ/vector editor or reviewed AI draft | Nodes, edges, labels, omitted steps, scientific meaning |
| Conceptual illustration | Optional AI image generation | Accuracy, misleading implications, rights, visual clarity |
| Title, metric callout, citation, QR code | LaTeX, plotting code, `qrcode` | Exact text/value/URL and final-size legibility |
| Institution/company logo | Official asset | Correct identity, permission, print resolution |

Do not choose or suppress comparison methods solely to fit a graphic. Simplify the
presentation while preserving information needed to interpret the finding. Axes,
units, legends, baselines, denominators, and uncertainty must remain where needed.

## Before generation

1. State the single idea and intended final printed width/height.
2. Identify the essential components and labels. Three or four large components is
   often a useful starting point, not a scientific constraint.
3. Split crowded diagrams without removing necessary qualifications or making a
   hypothesis look like an established result.
4. Use exact short labels, strong contrast, ample spacing, and simple shapes. Put
   longer explanations into editable LaTeX captions.
5. Ensure the prompt contains only information appropriate to send to the service.

## Helper contract (reviewed 2026-09-30)

`generate_schematic.py` delegates to `generate_schematic_ai.py`. Requirements are
Python 3.10+, `requests`, network access, and `OPENROUTER_API_KEY`. The scripts resolve
the key from the environment or a project `.env`; prefer those over command-line keys.

- Generation: `POST https://openrouter.ai/api/v1/images`, Bearer authentication,
  JSON `model`, `prompt`, `n: 1`; non-streaming response `data[0].b64_json` and optional
  `media_type`. The helper verifies PNG signature and requires a `.png` output path.
- Model: `google/gemini-3.1-flash-image` (Nano Banana 2). Current endpoint records
  allow one image per call; `output_format` is absent from those provider capability
  maps, so the helper relies on the provider default and validates the bytes.
- Review: `POST https://openrouter.ai/api/v1/chat/completions`, the same auth, model
  `google/gemini-3.7-flash`, a user message with text and an `image_url` PNG data URL.
  Review text is read from `choices[0].message.content`.
- `--doc-type poster` selects the helper's 7/10 review heuristic. It is not an
  externally validated quality standard. Maximum `--iterations` is 1 or 2; a failed
  refinement keeps the preceding saved draft. No automatic paid-request retries.
- The helper writes the PNG, versioned drafts, and `*_review_log.json`. Review failure,
  score below threshold, or generation failure is recorded. Check `quality_met`,
  `final_reviewed`, and `termination_reason` rather than treating exit 0 as approval.

The official API contracts and public model/provider catalogues were checked; no
paid calls through the bundled schematic helpers were executed for this refresh.
There is no pagination in these two inference calls. Model discovery is a separate
read operation, not a prerequisite automatically performed by the helper.

## Illustrative call

Run from the skill root, using an output path in the poster project. This costs API
credits and was not executed in the refresh:

```bash
python scripts/generate_schematic.py \
  "Conceptual A0 poster workflow. Three large boxes: SAMPLE, MEASURE, ANALYZE. Clear left-to-right arrows, generous white space, dark readable labels. No numerical data, extra claims, or figure caption." \
  -o /path/to/project/figures/methods.png --doc-type poster --iterations 1
```

A request for “80 pt” or “300 DPI” is a visual cue, not a guaranteed physical font
size or resolution. The helper does not expose a resolution option. Determine
actual pixels and placed width before deciding whether the image is suitable.
For example, a 2048-pixel-wide image placed at 12 inches has about 171 PPI regardless
of the file's nominal DPI metadata. Prefer vector artwork or regenerate at a suitable
resolution with a capable tool when the available raster image is insufficient.

## Review before assembly

Open the generated image and verify each node, arrow, label, symbol, and implication
against the intended scientific content. An automated vision review can miss errors.
Check spelling, contrast, visibility of labels, and space around the edges. If changes
are necessary, correct editable vector elements or regenerate and inspect again.

After inclusion, inspect a rendered poster at its intended size and viewing distance.
“25% zoom” on an arbitrary display is not a calibrated physical-size test. For a
25% printed proof, viewing from 1 foot approximates a full-size viewing distance
of 4 feet. Check an actual-size crop for image sharpness and QR scanning.

## Assembly

These are illustrative fragments inside the appropriate poster class:

```latex
% tikzposter: a precise caption remains editable
\block{Methods}{
  \begin{tikzfigure}[Conceptual overview; see the text for study details.]
    \includegraphics[width=0.85\linewidth]{figures/methods.png}
  \end{tikzfigure}
}

% baposter: the named box is positioned relative to an existing intro box
\headerbox{Methods}{name=methods,column=0,below=intro}{
  \centering
  \includegraphics[width=0.85\linewidth]{figures/methods.png}
}
```

Do not delete the scripts/data needed to regenerate quantitative figures. Preserve
image-generation prompt/model metadata with the project if AI artwork is included.

## Official sources

- [OpenRouter image generation](https://openrouter.ai/docs/guides/overview/multimodal/image-generation)
- [OpenRouter image inputs for vision review](https://openrouter.ai/docs/guides/overview/multimodal/image-understanding)
- [Current image-provider capabilities](https://openrouter.ai/api/v1/images/models/google/gemini-3.1-flash-image/endpoints)
- [General model catalogue](https://openrouter.ai/api/v1/models)
