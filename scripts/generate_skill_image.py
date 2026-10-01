#!/usr/bin/env python3
"""Render a skill's workflow as a diagram, via the OpenRouter Image API.

Local repository tooling; not part of any shipped skill.

Two stages, both through OpenRouter on one OPENROUTER_API_KEY:

1. Read the whole skill -- SKILL.md, everything under references/, and a
   manifest of scripts/ and assets/ -- and have a text model distil it into a
   description of one diagram. An image model cannot digest a few hundred
   kilobytes of markdown, so something has to decide what the diagram shows
   before any pixels are requested.
2. Send that description to the image model.

The image model is fixed to openai/gpt-image-2.5-sunburst, so the parameters
accepted below are that model's advertised set rather than the API-wide
superset. It does not accept ``resolution``, ``size``, ``seed``, or
``output_format``, and OpenRouter rejects unsupported parameters with an
HTTP 400 rather than ignoring them.

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
PROMPT_MODEL = "anthropic/claude-opus-5"

IMAGES_URL = "https://openrouter.ai/api/v1/images"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
IMAGES_DIR = REPO_ROOT / "docs" / "images"

# openai/gpt-image-2.5-sunburst capabilities, from
# GET /api/v1/images/models/openai/gpt-image-2.5-sunburst/endpoints (checked 2026-09-13).
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
    "Checkpoints: a small diamond sitting on the connector between two steps, its label "
    "set just beside it, never inside a card. Approval gates are rose diamonds, "
    "automatic checks slate diamonds. If a legend is given, set it small at the bottom "
    "right with one diamond swatch per entry. "
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
    "text. The flow runs left to right along the first row, drops down at the right "
    "edge, and runs left to right again along the second row, so the numbers always "
    "increase in reading order. Every connector leaves the edge of one card and lands on "
    "the edge of exactly the card it leads to. "
    "Typography: one clean geometric sans-serif for everything except tool chips. "
    "Every line of text must stay comfortably legible when the image is shown at half "
    "size; when space is tight, shrink motifs, never text. "
    "Layout: a strict grid with even gutters, balanced margins on all four sides, and "
    "the whole frame used. "
    "Spell every piece of text exactly as written. The quoted text in the prompt is the "
    "COMPLETE text inventory: render each item once, where the prompt places it, and add "
    "NO other text anywhere. Motifs are unlabelled; plots have no numbers, ticks or "
    "annotations; tables show only the headers given. Never invent example identifiers, "
    "sequences, URLs, citations, code, JSON, prices, measurements, scores, clinical "
    "classifications, dates, or biological relationships. "
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
with its condition in at most 32 characters. At most four checkpoints. Say for each whether it is an \
automatic check or a user approval gate. If both kinds appear, add a two-entry legend \
labelled "Automatic check" and "Needs your approval".
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
- Ground everything in the documentation. Do not invent a step, tool, rule, or \
relationship it does not state, and never substitute a different command or an invented \
abbreviation for a real one. Independent operations must not be chained as consecutive \
steps; preserve any review or resolution gate before downstream work.
- If the skill covers several separate operations or APIs, diagram its main end-to-end \
workflow and give the others one supporting mention at most. API discovery and \
authentication are supporting detail, never the step that produces the result.
- Name each element's role (input, step, checkpoint, output, supporting note), never a \
colour.
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
    the repository caps it at 500 lines anyway. References share what is left.
    """
    sections: list[str] = []
    log: list[str] = []

    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    sections.append(f"===== SKILL.md =====\n{skill_md}")
    log.append(f"SKILL.md ({len(skill_md):,} chars)")

    references = sorted(
        path
        for path in (skill_dir / "references").rglob("*")
        if path.is_file() and path.suffix.lower() in READABLE_SUFFIXES
    )

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
    too expensive to abandon over one transient failure. A failed generation is
    not billed, so a retry costs nothing extra.
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
        "SKILL.md is always sent whole; references share what is left.",
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
