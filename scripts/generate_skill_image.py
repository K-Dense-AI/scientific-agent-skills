#!/usr/bin/env python3
"""Render a skill's workflow as a diagram, via the OpenRouter Image API.

Local repository tooling; not part of any shipped skill.

Two stages, both through OpenRouter on one OPENROUTER_API_KEY:

1. Read the skill documentation -- SKILL.md, root-level Markdown guides,
   everything under references/, and a manifest of scripts/ and assets/ --
   and have a text model distil it into a
   description of one diagram. An image model cannot digest a few hundred
   kilobytes of markdown, so something has to decide what the diagram shows
   before any pixels are requested.
2. Send that description to the image model.

The image model is fixed to openai/gpt-image-2.5-sunburst, so the parameters
accepted below are that model's advertised set rather than the API-wide
superset. This tool does not expose ``resolution``, ``size``, ``seed``, or
``output_format``. Provider handling of unsupported fields can differ; use
the live endpoint capability record before extending the request body.

Standard library only.

    python scripts/generate_skill_image.py --skill scanpy
    python scripts/generate_skill_image.py --skill scanpy --prompt-only
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

IMAGE_MODEL = "openai/gpt-image-2.5-sunburst"
PROMPT_MODEL = "openai/gpt-6-astra"

IMAGES_URL = "https://openrouter.ai/api/v1/images"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
IMAGES_DIR = REPO_ROOT / "docs" / "images"

# openai/gpt-image-2.5-sunburst capabilities, from
# GET /api/v1/images/models/openai/gpt-image-2.5-sunburst/endpoints (checked 2026-09-30).
ASPECT_RATIOS = ["1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "auto"]
QUALITIES = ["auto", "low", "medium", "high", "xhigh", "max"]
BACKGROUNDS = ["auto", "transparent", "opaque"]
MAX_N = 10
MAX_REFERENCES = 16

# Diagrams live or die on legible labels, so both defaults lean that way: a
# wide frame to lay stages out along, and the quality tier that renders type
# cleanly. Drop to --quality low while iterating on a prompt.
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_QUALITY = "high"

DEFAULT_MAX_CHARS = 150_000

READABLE_SUFFIXES = {".md", ".txt", ".rst", ".yaml", ".yml", ".json", ".csv", ".toml"}

# The diagrams are explainers, not decoration: someone who has never opened the
# skill should be able to read one and know what the agent does, step by step,
# with which tool, where it stops, and what it hands back. So the text carries
# the meaning and the motifs only support it. The earlier minimal style -- ten
# short labels, empty tables, unlabelled cards -- looked tidy and said almost
# nothing. What stays strict is fabrication: text comes verbatim from the
# documentation, and no example data, identifiers or results are drawn.
DIAGRAM_STYLE = (
    "ART DIRECTION — render the above as a clear, information-rich explainer diagram of "
    "the kind found in the best engineering documentation, where the text is the point "
    "and every element earns its place. Flat vector illustration on a soft warm "
    "off-white background, not stark white. "
    "Header: the title large and bold in dark warm charcoal at the top left, the subtitle "
    "on one line directly beneath it in medium grey. "
    "Step cards: white cards with gently rounded corners, a thin border and roomy "
    "padding. Each has a solid circular number badge at its top left in the step colour, "
    "the step title in bold beside the badge, the one-line description beneath in regular "
    "weight, and, where given, the tool chip as a small rounded pill along the bottom of "
    "the card holding the tool name in a clean monospace face. The step's motif sits "
    "small and simple at the card's right, never crowding the text. All step cards are "
    "the same size so the numbered sequence reads as one system. "
    "Roles: steps deep indigo, inputs muted teal, outputs warm amber, automatic checks "
    "slate grey, and human approval gates rose red; each role shows as the badge or "
    "accent colour with a pale tint of the same hue behind its area. "
    "Checkpoint symbols are optional, not a default decoration. Draw a diamond only "
    "when the diagram content explicitly names a checkpoint condition and its route. "
    "When reviews stay inside cards or the content specifies no checkpoints, use "
    "plain directional connectors with triangular arrowheads throughout; there must "
    "be no diamonds on those connectors. Every diamond must have the requested "
    "condition label. A diamond is never an arrowhead or a decorative separator. "
    "Checkpoints: a small diamond sitting on the connector between two steps, its label "
    "set just beside it, never inside a card. Approval gates are rose diamonds, "
    "automatic checks slate diamonds. If a legend is given, set it small at the bottom "
    "right with one diamond swatch per entry. Draw a legend only when the diagram "
    "content explicitly requests one, and include only roles actually shown. If there "
    "is no human approval gate, omit every approval-gate legend entry or swatch. "
    "Inputs and outputs: tinted panels at the start and end of the flow, each item on "
    "its own line as a small file-or-document glyph followed by its name. "
    "Watch-for strip: a full-width band along the bottom with a small uppercase heading "
    "and its notes laid out side by side in equal columns, each note preceded by a small "
    "caution mark. "
    "Motifs: flat, a few clean strokes, recognisable at thumbnail size, never a "
    "photograph and never a detailed chart. They may use a wider categorical palette "
    "from the same family — indigo, teal, amber, rose, sage. "
    "Connectors: thin lines of uniform weight in soft slate with small solid arrowheads, "
    "routed at clean right angles with rounded corners, never crossing a card or any "
    "text. Cards increase left to right in each row. The row-change connector runs "
    "from the last upper card to the first lower card at the far left, through clear "
    "space outside the cards; do not shortcut into the lower-right card. "
    "Every connector leaves the edge of one card and lands on "
    "the edge of exactly the card it leads to. "
    "Draw every explicitly requested feedback or refinement loop back to its named "
    "earlier step; the cards' reading order does not prohibit backward loop arrows. "
    "A conditional feedback arrow must visibly leave the decision node itself, never "
    "branch from that node's incoming connector or an ambiguous shared junction. "
    "Every arrow starts and ends on its named nodes, with no dangling end in whitespace. "
    "Use exactly one arrowhead at the destination; draw a two-headed arrow only for "
    "an explicitly documented bidirectional relationship. "
    "Never place an extra arrowhead at an elbow, crossing, or source edge. In "
    "particular, a long feedback connector has a single arrowhead touching its "
    "earlier destination card; all intervening bends are plain lines. "
    "Feedback routes are dashed and use their own lane, separate from forward "
    "routes and row changes. They never share a line segment or junction with a "
    "forward route. A finish/output card never originates a continuation loop "
    "unless the content explicitly names it as the source. "
    "State badges inside a card are labels, not an implied sequence: do not connect "
    "them with arrows unless the prompt explicitly defines those transitions. In "
    "particular, never draw an arrow from completed or success into failed or error. "
    "Keep each checkpoint on the exact connector named in the prompt: a result check "
    "must follow the operation producing that result. Never move it earlier to fit. "
    "Typography: one clean geometric sans-serif for everything except tool chips. "
    "Every line of text must stay comfortably legible when the image is shown at half "
    "size; when space is tight, shrink motifs, never text. "
    "Layout: a strict grid with even gutters, balanced margins on all four sides, and "
    "the whole frame used. "
    "Spell every piece of text exactly as written. The quoted text in the prompt is the "
    "COMPLETE text inventory: render each item once, where the prompt places it, and add "
    "NO other text anywhere. Motifs are unlabelled; plots have no numbers, ticks or "
    "annotations; tables show only the headers given. If no table headers are explicitly "
    "quoted, leave the header cells blank; never invent field names. Never invent example identifiers, "
    "sequences, URLs, citations, code, JSON, prices, measurements, scores, clinical "
    "classifications, dates, or biological relationships. "
    "Chemical motifs stay abstract and unlabelled; do not invent atom labels, bond "
    "structures, or reaction pairs when no exact validated structure is supplied. "
    "Quantum circuit motifs use circuit-definition record sheets or code-file icons "
    "unless the content supplies a complete validated gate sequence. Never invent, "
    "omit or rearrange gates, controls, measurements or wire connections to make a "
    "decorative circuit; a bare measured zero-state circuit is not a Bell circuit. "
    "If the documented model fixes an array or state dimension, any depicted "
    "operator matrix, ket, register or tensor must match it exactly. Use a plain "
    "record-sheet icon when that dimension is not explicitly specified; a "
    "three-entry ket or three-by-three operator cannot illustrate a two-level model. "
    "Medical imaging and microscopy motifs are simple flat outline icons, never "
    "realistic scan thumbnails, tissue textures, or fabricated analysis-result images. "
    "A missing-data gap in a plot is empty space: end the trace before the gap and "
    "restart it after the gap. Never bridge missing observations with dots, dashes, "
    "a faint stroke, or a solid interpolation line. This applies to every repeated "
    "plot motif, including thumbnails inside export or inspection cards. "
    "When the content requests records without curves or plotted results, never "
    "substitute a generic forecast, learning curve, uncertainty band or trend chart, "
    "even as a small thumbnail drawn inside a file icon. Those imply unsupported "
    "results. Use plain text-line record sheets or empty tables instead. "
    "Repeated motifs of the same graph must preserve exactly its node and edge set, "
    "including isolated nodes, through inspection, scoring, layout and export. "
    "Only alter connectivity or remove records when the named operation explicitly "
    "does so. Layout changes position, not topology; scoring changes attributes, "
    "not which observations exist. "
    "If the prompt supplies no exact graph connectivity, use abstract node/edge "
    "record sheets and file icons instead of drawing an invented network. A "
    "generic graph icon must not masquerade as changing analysis data. "
    "A checkpoint diamond lies on its named step-to-step route only; do not add "
    "a connector from an adjacent input panel or a second shortcut to its next card. "
    "A guarded transition has exactly one route: source card, diamond, destination "
    "card. This replaces the ordinary direct arrow between those cards. If the "
    "diamond route bends below a row, omit the horizontal arrow between the cards "
    "entirely; otherwise the diagram incorrectly permits bypassing the check. "
    "For checkpoints between cards in the same row, reserve a wide horizontal "
    "gutter and place the diamond there, directly between its two cards. Do not "
    "put a same-row checkpoint in a separate lane below the cards. Narrow the "
    "cards and reduce their motifs to make the checkpoint gutter fit. "
    "A checkpoint assigned to the last upper card and first lower card belongs "
    "on the long row-transition connector itself. Never shift that checkpoint "
    "to a gutter between lower-row cards, or move later checkpoints downstream. "
    "No photorealism, no 3D, no isometric perspective, no people, no stock clip art, no "
    "generic gear or cloud or lightbulb icons, no gradients, no drop shadows, no glow, no "
    "decorative background, no watermark."
)

DISTIL_INSTRUCTIONS = """\
You write prompts for an image model that renders technical explainer diagrams.

Read the Agent Skill documentation below and write ONE prompt for a single diagram. A \
scientist who has never seen this skill should be able to study it for thirty seconds and \
come away knowing what the skill does, the steps an agent follows, the tool used at each \
step, where the agent stops for a check or for the user's decision, what it hands back, and \
the few things most likely to go wrong.

Lay the diagram out as follows, and say where each element sits:
- Header, top left: a title naming the skill's purpose in five words or fewer, and beneath \
it a subtitle of at most 90 characters saying what the skill does and on what.
- Inputs panel at the left of the first row: up to four things the user supplies, each \
named concretely (file formats, identifiers, credentials, a logged-in account).
- Main flow: five or six numbered steps in reading order, in two rows -- steps 1 to 3 on \
the first row, left to right, and the rest on the second row, also left to right. Each \
step card has its number, a title of at most 24 characters, one plain line of at most 60 \
characters saying what happens or why it matters, and -- where the documentation names \
one -- a tool chip with the exact script, command, function, file, or UI control used, at \
most 30 characters. Give each step a small, specific motif of what the work looks like at \
that point: a STEP solid with a bounding box, a table with header row, a sequence track, a \
spectrum, a clustered scatter, a quote card with price tiers, a stage tracker. Choose \
motifs this field would recognise.
- Checkpoints: where the documented workflow validates, blocks, or needs the user's \
explicit approval, place a checkpoint on the arrow between the two steps it guards, or on \
the arrow from the last step into the outputs panel -- never inside a card -- labelled \
with its condition in at most 32 characters. At most four checkpoints. Include an automatic \
diamond only for a named executable check; qualitative agent review belongs in a step \
card, not an automatic checkpoint. Include a user approval gate only when the documented \
workflow actually requires approval. A workflow may have no diamonds. Say for each \
checkpoint whether it is an automatic check or a user approval gate. If both kinds appear, add a two-entry legend \
labelled "Automatic check" and "Needs your approval". Name every checkpoint's exact \
source and destination step numbers and titles, for example "step 2 Audit -> check -> \
step 3 Transform"; never locate it only as "after audit" or "before training". Reserve \
space on that specific connector so a check cannot move before its producing step.
- Outputs panel at the right of the second row, fed by the last step: up to four \
artifacts the skill actually returns, named concretely.
- A full-width strip along the bottom headed "Watch for", holding three or four of the \
documentation's most important caveats, limits, or safety rules, each at most 60 \
characters.

Text rules:
- Give every piece of text verbatim in double quotes. That quoted text is the entire text \
inventory, typically 30 to 40 items. Use the documentation's real vocabulary -- actual step \
names, scripts, commands, file formats, UI labels, rules -- never filler like "Input", \
"Process", "Output", "Data".
- A number may appear only as a documented fact copied exactly: a limit, a time window, a \
standard, a version. Never ask for example data, identifiers, measurements, prices, \
scores, dates, or results; data-bearing motifs stay schematic and unlabelled, and tables \
show at most a header row. A diagram must not fabricate evidence or imply that a \
prediction is a measured result.
- Preserve indispensable input dimensions, units, and physical scale when a mismatch \
invalidates the documented model workflow. Put the documented target in the quoted \
input or step text; a generic instruction to check resolution or shape is insufficient \
when the reader needs that exact target to understand the workflow.
- Put required version pins and execution prerequisites inside the input panel or the \
specific step card that establishes them. Do not place critical requirements in floating \
notes between rows or above several cards; give them a definite text slot and keep the \
card concise enough to render every required label.
- For chemistry workflows, use coordinate clouds, record cards, or unlabelled abstract \
shapes as motifs. Do not request molecular bond structures or reaction/tautomer pairs \
unless the documentation supplies an exact validated structure for the drawing.
- For medical imaging and microscopy without supplied specimen images, request slide-file \
icons, empty tile grids and mask-record symbols. Do not request tissue thumbnails, \
stained textures, segmentation overlays or before/after result pictures: those invite \
fabricated biological evidence even when the prompt calls them schematic.
- For network workflows without an exact input graph, request node/edge record sheets \
and abstract file icons, not invented connected-node diagrams. When exact connectivity \
is supplied, preserve its full node/edge set, including isolates, in every repeated motif \
unless an explicit transformation changes that set.
- For quantum workflows, request circuit-definition record sheets or code-file icons \
unless you specify a complete validated gate sequence from the documentation. Do not \
request decorative quantum wires or gate motifs: omitted entangling gates or invented \
connections change the operation, even when every numerical result is left blank.
- When illustrating a model with fixed dimensions, specify the correct matrix/state \
shape for every array motif or use plain record sheets instead. Empty matrix and ket \
grids still imply dimensions; do not let decoration contradict the model's dimensions.
- For forecasting or model-fitting workflows without supplied results, use text-only \
record sheets or empty tables, never forecast curves, uncertainty bands, trend charts \
or learning curves, even inside file icons. Explicitly prohibit those plot thumbnails \
when requesting a record motif so the renderer does not turn a report into fake results.
- Ground everything in the documentation. Do not invent a step, tool, rule, or \
relationship it does not state, and never substitute a different command or an invented \
abbreviation for a real one. Independent operations must not be chained as consecutive \
steps; preserve any review or resolution gate before downstream work.
- Keep conditional behavior conditional: asynchronous polling belongs only to operations \
that return a job or task handle. Mutually exclusive outcomes such as success and failure \
must branch from their shared prior state; never connect them as consecutive stages.
- When only one refinement is permitted, show the initial operation and review followed \
by the conditional refinement and second review as forward stages, with an early-success \
bypass. Do not draw a backward loop that could imply unlimited repetitions. For an \
example that needs no refinement, put the optional second pass in a supporting note.
- Keep API contracts attached to their own operation. Never pair one helper with another \
helper's response fields or outputs. When a short label cannot preserve that distinction, \
describe the check in plain language instead of naming a response attribute.
- Preserve artifact ownership: name an intermediate file in the step that creates it, \
not as a new output of a later step that only reads it. If the output panel collects \
artifacts from the whole workflow, label it "Workflow artifacts" and explicitly include \
collecting those artifacts in the final handoff step. Otherwise list only the final \
step's own outputs, retaining earlier files as supporting text in their producing cards.
- An automatic checkpoint may assert only a property the documented executable actually \
checks. A declared field, schema check, or common-key screen cannot establish that data \
are private, aggregate-only, authorized, authentic, or scientifically valid. Show such \
substantive judgments as an explicitly labelled human-review step when required by the \
documentation, rather than an automatic pass gate. Put any essential limitation in the \
quoted visible text inventory; an unquoted instruction to the renderer is not a caveat \
the reader of the diagram will see.
- Distinguish nonempty inputs or definitions from nonempty scientific results. For \
gating workflows, say "strategy contains gate definitions", never "nonempty gates": \
valid gated populations may contain no events. Preserve undefined percentages for \
empty parent populations. Use plain-language labels when shortening an exact condition \
would change which inputs or results are allowed.
- Motifs must preserve the documented data flow as carefully as the step text. When \
an artifact or processor is fitted on one dataset and reused on others, show one fitted \
artifact with reuse connections; do not depict a separate fit for each dataset. Avoid \
decorative arrows that reverse provenance or imply unperformed computations.
- For plots with missing observations, explicitly require a blank interval between \
disconnected trace segments in every repeated motif. Dotted or dashed bridges imply \
interpolation and must not stand in for missing-data gaps.
- Preserve training, validation and test roles in every label: a validation metric can \
select a checkpoint, but that does not mean the model is trained on validation data. \
Use a title such as "Train and select" when validation guides model selection.
- Preserve the scope of caveats. A rule against reconfiguring or deleting an existing \
resource must not become a blanket ban on authorized use of that resource. Precautions \
for running temporary tests must not contradict the depicted production workflow.
- If the skill covers several separate operations or APIs, diagram its main end-to-end \
workflow and give the others one supporting mention at most. API discovery and \
authentication are supporting detail, never the step that produces the result.
- Choose one concrete worked example before choosing the step cards. Every operation \
and output in the main flow must belong to that example. Optional operations that the \
example does not perform belong in a supporting note, not an extra numbered step.
- Show the actions the agent actually performs. When the worked example invokes a \
bundled helper or CLI, keep that invocation as one step; do not turn its private API \
calls, response parsing, or internal retry decisions into separate agent actions. \
Explain critical internal behavior in that card or a supporting note. Low-level \
format checks belong in the producing card or caveats, not separate flow diamonds.
- Include prerequisites needed by later steps: identifiers must come from an earlier \
step or a named input. A review or inspection is not a user approval gate unless the \
documentation explicitly requires user consent; represent ordinary verification as \
a check, without inventing a permission requirement.
- Before returning the prompt, trace every identifier and prerequisite from input to \
output. Include session creation or model selection when the example needs it; combine \
related operations in one card if necessary. Treat citation review and evidence \
verification as checks, not consent gates. Include an approval legend only when the \
example explicitly asks the user to authorize an action.
- Label checkpoints with the positive condition required to continue, such as \
"Successful results available". Put failure conditions in the caveat strip or on an \
explicit stop branch; never label a forward path with an error. Producing a read-only \
report or a dry-run plan does not require approval. Only show a consent gate before \
an actual authorized write, submission, or other action requiring that consent.
- Distinguish requested targets from achieved results. A desired reference count is a \
target, not a promised output. Placing an order in a cart does not produce an accepted \
order or scientific measurements. Include only outputs actually produced by the \
depicted steps; mark later deliverables as conditional supporting detail.
- Use a high-level label when a short code chip would omit necessary branches, such \
as different cleanup for a newly created versus reused session. Do not simplify a \
conditional API contract into an unconditional call.
- Preserve required shutdown and cleanup order in both labels and code chips. If \
disposing a handle does not close its subprocesses, include the documented shutdown \
operation before disposal; do not suggest that the final call alone is sufficient.
- Name each element's role (input, step, checkpoint, output, supporting note), never a \
colour.
- For a backward continuation or refinement loop, include its source and destination \
step numbers in the visible connector label, for example "Continue: step 5 to step 2". \
Specify a separate dashed lane from the actual source card to the named destination; \
never attach that loop to a finish card or to a row-transition connector.
- Describe structure and content only. Say nothing about colours, fonts, line weights, \
textures, shading or rendering style -- those are art-directed separately, and anything \
you add will fight them.
- Reply with the prompt text only. No preamble, no markdown, no surrounding quotes.

Target 250 to 400 words.\
"""

EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}

INPUT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class ScriptError(RuntimeError):
    """A condition the caller can act on, reported without a traceback."""


def find_api_key(explicit: str | None) -> str:
    """Resolve the key from --api-key, then the environment, then a .env file."""
    if explicit:
        return explicit

    from_env = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if from_env:
        return from_env

    for directory in [Path.cwd(), *Path.cwd().parents, REPO_ROOT]:
        env_file = directory / ".env"
        if not env_file.is_file():
            continue
        for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "OPENROUTER_API_KEY":
                value = value.strip().strip('"').strip("'")
                if value:
                    return value

    raise ScriptError(
        "OPENROUTER_API_KEY not found.\n"
        "  export OPENROUTER_API_KEY=your-key\n"
        "  or add OPENROUTER_API_KEY=your-key to the repository .env\n"
        "  or pass --api-key\n"
        "Keys: https://openrouter.ai/keys"
    )


def resolve_skill(name: str) -> Path:
    """Map a skill name or path onto its directory under skills/."""
    candidate = Path(name)
    if candidate.is_dir() and (candidate / "SKILL.md").is_file():
        return candidate.resolve()

    directory = SKILLS_DIR / Path(name).name
    if not (directory / "SKILL.md").is_file():
        raise ScriptError(
            f"No skill named '{name}' — expected {directory / 'SKILL.md'} to exist."
        )
    return directory


def fair_share(sizes: dict[Path, int], budget: int) -> dict[Path, int]:
    """Split budget across files so no one file can starve the others.

    Max-min allocation: everything under an equal share is taken whole, and the
    slack it leaves is handed back to the larger files. The alternative --
    walking the list and truncating until the budget runs out -- silently drops
    the tail, which for an alphabetical references/ directory means a skill
    like database-lookup gets diagrammed from the A's alone.
    """
    allocation: dict[Path, int] = {}
    pending = set(sizes)

    while pending:
        share = budget // len(pending)
        if share <= 0:
            break
        small = [path for path in pending if sizes[path] <= share]
        if not small:
            for path in pending:
                allocation[path] = share
            break
        for path in small:
            allocation[path] = sizes[path]
            budget -= sizes[path]
            pending.discard(path)

    return allocation


def collect_skill_text(skill_dir: Path, max_chars: int) -> tuple[str, list[str]]:
    """Gather the skill's documentation into one string, plus a read log.

    SKILL.md is always included whole; it is the part that has to be right, and
    the repository caps it at 500 lines anyway. Supporting guides share what
    is left, including legacy root-level Markdown files such as PDF forms.md.
    """
    sections: list[str] = []
    log: list[str] = []

    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    sections.append(f"===== SKILL.md =====\n{skill_md}")
    log.append(f"SKILL.md ({len(skill_md):,} chars)")

    references = sorted({
        path for path in (skill_dir / "references").rglob("*")
        if path.is_file() and path.suffix.lower() in READABLE_SUFFIXES
    } | {
        path for path in skill_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".md"
        and path.name != "SKILL.md" and not path.stem.lower().startswith("license")
    })

    if references:
        contents = {
            path: path.read_text(encoding="utf-8", errors="replace") for path in references
        }
        allocation = fair_share(
            {path: len(text) for path, text in contents.items()},
            max(max_chars - len(skill_md), 0),
        )
        for path in references:
            allowance = allocation.get(path, 0)
            rel = path.relative_to(skill_dir)
            if allowance <= 0:
                log.append(f"{rel} (skipped, no budget left)")
                continue
            text = contents[path]
            note = ""
            if len(text) > allowance:
                note = f", truncated from {len(text):,}"
                text = text[:allowance]
            sections.append(f"===== {rel} =====\n{text}")
            log.append(f"{rel} ({len(text):,} chars{note})")

    for extra in ("scripts", "assets"):
        directory = skill_dir / extra
        if not directory.is_dir():
            continue
        names = sorted(
            path.relative_to(skill_dir).as_posix()
            for path in directory.rglob("*")
            if path.is_file()
        )
        if names:
            sections.append(f"===== {extra}/ manifest =====\n" + "\n".join(names))
            log.append(f"{extra}/ manifest ({len(names)} files)")

    return "\n\n".join(sections), log


def chat_completion(
    api_key: str, model: str, system: str, user: str, timeout: float
) -> tuple[str, float | None]:
    """Run one non-streaming chat completion and return the text and its cost."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "usage": {"include": True},
    }
    result = post_json(CHAT_URL, api_key, payload, timeout)

    choices = result.get("choices") or []
    if not choices:
        raise ScriptError(
            f"{model} returned no choices.\n"
            f"Raw response: {json.dumps(result, indent=2)[:800]}"
        )

    content = (choices[0].get("message") or {}).get("content") or ""
    if isinstance(content, list):  # some providers return content parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    content = content.strip()
    if not content:
        raise ScriptError(f"{model} returned an empty prompt.")

    return content, (result.get("usage") or {}).get("cost")


def distil_diagram_prompt(
    skill_dir: Path, document: str, api_key: str, model: str, timeout: float
) -> tuple[str, float | None]:
    """Turn the skill's documentation into a description of one diagram."""
    user = f"Agent Skill: {skill_dir.name}\n\n{document}"
    return chat_completion(api_key, model, DISTIL_INSTRUCTIONS, user, timeout)


def encode_reference(source: str) -> str:
    """Return a reference image as a URL the API accepts."""
    if source.startswith(("http://", "https://", "data:")):
        return source

    path = Path(source)
    if not path.is_file():
        raise ScriptError(f"Reference image not found: {source}")

    mime = INPUT_MIME.get(path.suffix.lower())
    if mime is None:
        raise ScriptError(
            f"Unsupported reference image type '{path.suffix}' ({source}). "
            f"Supported: {', '.join(sorted(INPUT_MIME))}"
        )

    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4


def post_json(url: str, api_key: str, payload: dict, timeout: float) -> Any:
    """POST the payload and decode the JSON response.

    Rate limits and upstream hiccups are retried with exponential backoff:
    running many skills at once will meet 429s, and a whole-repository batch is
    too expensive to abandon over one transient failure. An ambiguous transport
    failure may occur after processing; retries are not a billing guarantee.
    """
    body_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    last: ScriptError | None = None
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            time.sleep(min(2**attempt + random.uniform(0, 1.5), 45))
        request = urllib.request.Request(url, data=body_bytes, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            detail = raw
            try:
                detail = json.loads(raw).get("error", {}).get("message") or raw
            except (json.JSONDecodeError, AttributeError):
                pass
            last = ScriptError(f"OpenRouter returned HTTP {exc.code}: {detail}")
            if exc.code not in RETRY_STATUS:
                raise last from exc
        except urllib.error.URLError as exc:
            last = ScriptError(f"Could not reach OpenRouter: {exc.reason}")
        except json.JSONDecodeError as exc:
            last = ScriptError(f"OpenRouter returned a non-JSON response: {exc}")
        except OSError as exc:
            # A reset mid-read arrives raw rather than wrapped in URLError, and
            # a burst of simultaneous connections provokes exactly that.
            last = ScriptError(f"Connection failed: {type(exc).__name__}: {exc}")

    raise last or ScriptError("Request failed for an unknown reason.")


def output_paths(base: Path, media_type: str, count: int, warn: bool = True) -> list[Path]:
    """Name the output files, defaulting the extension to the returned format."""
    extension = EXTENSIONS.get(media_type, ".png")
    stem = base.with_suffix("")
    suffix = base.suffix or extension

    if warn and base.suffix and base.suffix.lower() != extension:
        print(
            f"Note: model returned {media_type} but the output path ends in "
            f"'{base.suffix}'; writing the returned bytes under that name.",
            file=sys.stderr,
        )

    if count == 1:
        return [stem.with_suffix(suffix)]
    return [stem.parent / f"{stem.name}_{i + 1}{suffix}" for i in range(count)]


def save_images(result: dict, base: Path) -> list[Path]:
    """Decode data[].b64_json into files and return the paths written."""
    items = result.get("data") or []
    if not items:
        raise ScriptError(
            "Response contained no images.\n"
            f"Raw response: {json.dumps(result, indent=2)[:800]}"
        )

    paths = output_paths(base, items[0].get("media_type", "image/png"), len(items))
    written: list[Path] = []

    for item, path in zip(items, paths):
        payload = item.get("b64_json")
        if not payload:
            continue
        if payload.startswith("data:") and "," in payload:
            payload = payload.split(",", 1)[1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(payload))
        written.append(path)

    if not written:
        raise ScriptError("Response carried image entries but none contained data.")
    return written


def generate_for_skill(
    skill_dir: Path | None,
    args: argparse.Namespace,
    api_key: str,
    output: Path,
    verbose: bool,
) -> dict[str, Any]:
    """Run both stages for one skill and report what it produced and cost."""
    started = time.monotonic()
    text_cost: float | None = None

    if args.prompt is not None:
        subject = args.prompt
    else:
        assert skill_dir is not None
        document, log = collect_skill_text(skill_dir, args.max_chars)
        if verbose:
            print(f"Read {len(log)} files, {len(document):,} chars from {skill_dir.name}")
            print(f"Distilling a diagram with {args.prompt_model}")
        subject, text_cost = distil_diagram_prompt(
            skill_dir, document, api_key, args.prompt_model, args.timeout
        )

    if verbose:
        print(f"\nPrompt:\n{subject}\n")

    if args.prompt_only:
        return {"prompt": subject, "text_cost": text_cost, "paths": [], "skipped": False}

    payload = build_payload(
        f"{subject}\n\n{args.style}" if args.style else subject, args
    )
    if verbose:
        print(f"Drawing with {IMAGE_MODEL} -> {output}")

    result = post_json(IMAGES_URL, api_key, payload, args.timeout)
    written = save_images(result, output)

    return {
        "prompt": subject,
        "text_cost": text_cost,
        "image_cost": (result.get("usage") or {}).get("cost"),
        "paths": written,
        "seconds": time.monotonic() - started,
        "skipped": False,
    }


def all_skill_dirs() -> list[Path]:
    """Every directory under skills/ that actually carries a SKILL.md."""
    return sorted(
        path for path in SKILLS_DIR.iterdir() if (path / "SKILL.md").is_file()
    )


def run_batch(skill_dirs: list[Path], args: argparse.Namespace, api_key: str) -> int:
    """Generate for many skills at once, reporting each as it lands.

    Workers return records rather than printing, so progress lines from
    concurrent skills cannot interleave into each other.
    """
    pending = []
    skipped = []
    for skill_dir in skill_dirs:
        destination = default_output(skill_dir)
        if args.skip_existing and destination.exists():
            skipped.append(skill_dir.name)
        else:
            pending.append((skill_dir, destination))

    if skipped:
        print(f"Skipping {len(skipped)} skill(s) that already have an image.")
    if not pending:
        print("Nothing to do.")
        return 0

    print(f"Generating {len(pending)} skill(s) with {args.jobs} in flight.\n")

    stagger = iter(range(len(pending)))

    def work(item: tuple[Path, Path]) -> tuple[Path, dict | None, str | None]:
        skill_dir, destination = item
        # Opening every worker's first connection in the same instant gets the
        # whole opening wave reset, so spread the start of the batch out.
        time.sleep(min(next(stagger, 0), args.jobs) * 1.5)
        try:
            record = generate_for_skill(skill_dir, args, api_key, destination, False)
            return skill_dir, record, None
        except ScriptError as exc:
            return skill_dir, None, str(exc)
        except Exception as exc:  # a worker must not take the batch down with it
            return skill_dir, None, f"{type(exc).__name__}: {exc}"

    total_cost = 0.0
    failures: list[tuple[str, str]] = []
    done = 0

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(work, item) for item in pending]
        for future in as_completed(futures):
            skill_dir, record, error = future.result()
            done += 1
            marker = f"[{done}/{len(pending)}]"
            if error is not None:
                failures.append((skill_dir.name, error))
                print(f"{marker} FAILED {skill_dir.name}: {error}")
                continue
            cost = sum(
                value
                for key in ("text_cost", "image_cost")
                if (value := record.get(key)) is not None
            )
            total_cost += cost
            written = ", ".join(path.name for path in record["paths"])
            print(
                f"{marker} {skill_dir.name} -> {written} "
                f"(${cost:.4f}, {record['seconds']:.0f}s)"
            )

    print(f"\nDone. {done - len(failures)} generated, {len(failures)} failed.")
    print(f"Total cost: ${total_cost:.2f}")
    if failures:
        print("\nFailures:")
        for name, error in failures:
            print(f"  {name}: {error}")
        print(
            "\nRe-run the same command to retry only these "
            "(--skip-existing leaves finished skills alone)."
        )
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            f"Diagram a skill: read it with {PROMPT_MODEL}, draw it with {IMAGE_MODEL}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read the whole skill and diagram it into docs/images/scanpy.png
  python scripts/generate_skill_image.py --skill scanpy

  # See what the reader made of the skill, without generating an image
  python scripts/generate_skill_image.py --skill scanpy --prompt-only

  # List the files that would be read, no API calls at all
  python scripts/generate_skill_image.py --skill scanpy --dry-run

  # Skip the reading stage and say what to draw yourself
  python scripts/generate_skill_image.py --skill scanpy \\
      "Five stages left to right, labelled \\"h5ad\\", \\"QC\\", \\"PCA\\", \\"UMAP\\", \\"Leiden\\""

  # Every skill, six at a time, resuming where a previous run stopped
  python scripts/generate_skill_image.py --all --skip-existing -j 6

  # A few named skills in one batch
  python scripts/generate_skill_image.py --skill scanpy qiskit anndata

  # Three candidates to choose between
  python scripts/generate_skill_image.py --skill qiskit --n 3

  # Cheap iteration while tuning the look
  python scripts/generate_skill_image.py --skill qiskit --quality low
""",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="What to draw. Omit it to have the skill read and distilled instead.",
    )
    parser.add_argument(
        "--skill",
        metavar="NAME",
        nargs="+",
        help="One or more skill names or directories. Sets what gets read and "
        "where each image lands.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Every skill under skills/ that has a SKILL.md.",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=6,
        metavar="N",
        help="Skills generated concurrently in batch mode (default: 6)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Leave skills that already have an image alone. Makes a batch resumable.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output path. Defaults to docs/images/<skill>.png. "
        "An existing image for the skill is replaced.",
    )
    parser.add_argument(
        "--style",
        default=DIAGRAM_STYLE,
        help='Rendering style appended to the prompt. Pass --style "" to send it verbatim.',
    )
    parser.add_argument(
        "--prompt-model",
        default=PROMPT_MODEL,
        metavar="SLUG",
        help=f"Model that reads the skill and writes the diagram prompt "
        f"(default: {PROMPT_MODEL})",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"Documentation budget sent to the reader (default: {DEFAULT_MAX_CHARS:,}). "
        "SKILL.md is always sent whole; supporting guides share what is left.",
    )
    parser.add_argument(
        "--input",
        "-i",
        action="append",
        metavar="IMAGE",
        help=f"Reference image: path, HTTP(S) URL, or data URL. "
        f"Repeatable, up to {MAX_REFERENCES}.",
    )
    parser.add_argument("--n", type=int, help=f"Images per request, 1-{MAX_N} (default 1)")
    parser.add_argument(
        "--aspect-ratio",
        choices=ASPECT_RATIOS,
        default=DEFAULT_ASPECT_RATIO,
        help=f"default: {DEFAULT_ASPECT_RATIO}",
    )
    parser.add_argument(
        "--quality",
        choices=QUALITIES,
        default=DEFAULT_QUALITY,
        help=f"default: {DEFAULT_QUALITY}, which keeps small labels legible",
    )
    parser.add_argument(
        "--background",
        choices=BACKGROUNDS,
        help="auto (default), transparent, or opaque.",
    )
    parser.add_argument("--output-compression", type=int, metavar="0-100")
    parser.add_argument("--api-key", help="Overrides OPENROUTER_API_KEY and any .env file")
    parser.add_argument("--timeout", type=float, default=300.0, help="Seconds (default 300)")
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Read the skill and print the diagram prompt, but generate no image.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the files that would be read and the destination. No API calls.",
    )
    return parser


def default_output(skill_dir: Path | None) -> Path:
    """One flat directory, one image per skill, named for the skill."""
    if skill_dir is None:
        return Path("generated_image.png")
    return IMAGES_DIR / f"{skill_dir.name}.png"


def validate(args: argparse.Namespace) -> None:
    """Check the numeric arguments up front, so --dry-run catches them too."""
    if args.n is not None and not 1 <= args.n <= MAX_N:
        raise ScriptError(f"--n must be between 1 and {MAX_N}, got {args.n}.")
    if args.output_compression is not None and not 0 <= args.output_compression <= 100:
        raise ScriptError("--output-compression must be between 0 and 100.")
    if args.input and len(args.input) > MAX_REFERENCES:
        raise ScriptError(
            f"{IMAGE_MODEL} accepts at most {MAX_REFERENCES} reference images, "
            f"got {len(args.input)}."
        )
    if args.max_chars < 1_000:
        raise ScriptError("--max-chars must be at least 1000.")
    if args.jobs < 1:
        raise ScriptError("--jobs must be at least 1.")


def build_payload(prompt: str, args: argparse.Namespace) -> dict:
    """Assemble the image request, omitting everything the caller left unset."""
    payload: dict[str, Any] = {"model": IMAGE_MODEL, "prompt": prompt}

    optional = {
        "n": args.n,
        "aspect_ratio": args.aspect_ratio,
        "quality": args.quality,
        "background": args.background,
        "output_compression": args.output_compression,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    if args.input:
        payload["input_references"] = [
            {"type": "image_url", "image_url": {"url": encode_reference(source)}}
            for source in args.input
        ]

    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        validate(args)

        if args.all:
            if args.skill:
                raise ScriptError("Use --all or --skill, not both.")
            skill_dirs = all_skill_dirs()
        else:
            skill_dirs = [resolve_skill(name) for name in (args.skill or [])]

        if args.prompt is None and not skill_dirs:
            raise ScriptError(
                "Give a prompt, or --skill / --all to read skills and diagram them."
            )

        batch = len(skill_dirs) > 1
        if batch:
            if args.prompt is not None:
                raise ScriptError("A positional prompt applies to one skill, not many.")
            if args.output:
                raise ScriptError("--output names one file; drop it for a batch.")
            if args.dry_run:
                print(f"Would generate {len(skill_dirs)} skills into {IMAGES_DIR}:")
                for skill_dir in skill_dirs:
                    print(f"  {skill_dir.name} -> {default_output(skill_dir).name}")
                print("Dry run — nothing sent, nothing billed.")
                return 0
            return run_batch(skill_dirs, args, find_api_key(args.api_key))

        skill_dir = skill_dirs[0] if skill_dirs else None
        output = Path(args.output) if args.output else default_output(skill_dir)

        if args.dry_run:
            print(f"Skill:  {skill_dir if skill_dir else '(none)'}")
            print(f"Output: {output}")
            if args.prompt is not None:
                print(f"Prompt: {args.prompt}")
            elif skill_dir is not None:
                document, log = collect_skill_text(skill_dir, args.max_chars)
                print(f"Reader: {args.prompt_model}")
                print(f"Would read {len(log)} files, {len(document):,} chars:")
                for entry in log[:25]:
                    print(f"  {entry}")
                if len(log) > 25:
                    print(f"  ... and {len(log) - 25} more")
            print("Dry run — nothing sent, nothing billed.")
            return 0

        api_key = find_api_key(args.api_key)

        if args.skip_existing and output.exists():
            print(f"{output} already exists; nothing to do (--skip-existing).")
            return 0

        record = generate_for_skill(skill_dir, args, api_key, output, verbose=True)

        text_cost = record.get("text_cost")
        if args.prompt_only:
            if text_cost is not None:
                print(f"Reader cost: ${text_cost:.4f}")
            print("Stopping before image generation (--prompt-only).")
            return 0

        for path in record["paths"]:
            print(f"Saved {path}")

        parts = []
        if text_cost is not None:
            parts.append(f"reader ${text_cost:.4f}")
        if record.get("image_cost") is not None:
            parts.append(f"image ${record['image_cost']:.4f}")
        if parts:
            total = sum(
                value
                for key in ("text_cost", "image_cost")
                if (value := record.get(key)) is not None
            )
            print(f"Cost: {' + '.join(parts)} = ${total:.4f}")
        return 0

    except ScriptError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
