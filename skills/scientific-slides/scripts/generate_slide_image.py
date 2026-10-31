#!/usr/bin/env python3
"""
Slide image generation using Nano Banana 2.

Generate presentation slides or visuals by describing them in natural language.
Nano Banana 2 handles everything automatically with smart iterative refinement.

Two modes:
- Default (full slide): Generate complete slides with title, content, visuals (for PDF workflow)
- Visual only: Generate just images/figures to place on slides (for PPT workflow)

Supports attaching reference images for context (Nano Banana 2 will see these).

Usage:
    # Generate full slide for PDF workflow
    python generate_slide_image.py "Title: Introduction\\nKey points: AI, ML, Deep Learning" -o slide_01.png
    
    # Generate visual only for PPT workflow
    python generate_slide_image.py "Neural network diagram" -o figure.png --visual-only
    
    # With reference images attached
    python generate_slide_image.py "Create a slide about this data" -o slide.png --attach chart.png
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Variables forwarded to the generation subprocess. The child needs the
# OpenRouter credential; the rest keep networking, TLS, and locale working.
# Copying the whole parent environment instead would hand the child every
# unrelated secret that happens to be exported in the calling shell.
FORWARDED_ENV_VARS = (
    "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "no_proxy",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
    # Windows needs these for sockets, temp files, and interpreter startup.
    "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
    "APPDATA", "LOCALAPPDATA", "USERPROFILE", "TEMP", "TMP",
)


def resolve_api_key(explicit=None):
    """Resolve the OpenRouter key from --api-key, the environment, then any .env file.

    The .env scan walks up from the working directory and finally checks the
    script's own directory, so running from anywhere inside a project picks up
    the key at its root. The child process is handed the resolved value through
    build_subprocess_env, so it never has to repeat this search.
    """
    if explicit:
        return explicit

    from_env = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if from_env:
        return from_env

    cwd = Path.cwd()
    for directory in [cwd, *cwd.parents, Path(__file__).resolve().parent]:
        env_file = directory / ".env"
        if not env_file.is_file():
            continue
        try:
            content = env_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw in content.splitlines():
            line = raw.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "OPENROUTER_API_KEY":
                value = value.strip().strip('"').strip("'")
                if value:
                    return value

    return None


def build_subprocess_env(api_key):
    """Return a minimal environment for the AI generation subprocess."""
    env = {name: os.environ[name] for name in FORWARDED_ENV_VARS if name in os.environ}
    if api_key:
        env["OPENROUTER_API_KEY"] = api_key
    return env


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate presentation slides or visuals using Nano Banana 2 AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
How it works:
  Describe your slide or visual in natural language.
  Nano Banana 2 generates it automatically with:
  - Smart iteration (only regenerates if quality is below threshold)
  - Quality review by Gemini 3.7 Flash
  - PNG draft for visual and scientific verification

Modes:
  Default (full slide):  Generate complete slide with title, content, visuals
                         Use for PDF workflow where each slide is an image
  
  Visual only:           Generate just the image/figure
                         Use for PPT workflow where you add text separately

Attachments:
  Use --attach to provide reference images that Nano Banana 2 will see.
  This allows you to say "create a slide about this chart" and attach the chart.

Examples:
  # Full slide (default) - for PDF workflow
  python generate_slide_image.py "Title: Machine Learning\\nPoints: supervised, unsupervised, reinforcement" -o slide_01.png
  
  # Visual only - for PPT workflow  
  python generate_slide_image.py "Flowchart showing data pipeline" -o figure.png --visual-only
  
  # With reference images attached
  python generate_slide_image.py "Create a slide explaining this chart" -o slide.png --attach chart.png
  python generate_slide_image.py "Combine these into a comparison" -o compare.png --attach before.png --attach after.png
  
  # Multiple slides for PDF
  python generate_slide_image.py "Title slide: AI Conference 2025" -o slides/01_title.png
  python generate_slide_image.py "Title: Introduction\\nOverview of deep learning" -o slides/02_intro.png

Environment Variables:
  OPENROUTER_API_KEY    Required for AI generation
        """
    )
    
    parser.add_argument("prompt", help="Description of the slide or visual to generate")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("--attach", action="append", dest="attachments", metavar="IMAGE",
                       help="Attach image file(s) as context (can use multiple times)")
    parser.add_argument("--visual-only", action="store_true",
                       help="Generate just the visual/figure (for PPT workflow)")
    parser.add_argument("--iterations", type=int, default=2,
                       help="Maximum refinement iterations (default: 2, max: 2)")
    parser.add_argument("--api-key", help="OpenRouter API key (or use OPENROUTER_API_KEY env var)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    if not 1 <= args.iterations <= 2:
        parser.error("--iterations must be 1 or 2")
    if Path(args.output).suffix.lower() != ".png":
        parser.error("--output must end in .png; format conversion is not supported")
    
    # Check for API key — resolves --api-key, the environment, then any .env file
    api_key = resolve_api_key(args.api_key)
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found")
        print("\nFor AI generation, you need an OpenRouter API key.")
        print("Get one at: https://openrouter.ai/keys")
        print("\nSet it with:")
        print("  export OPENROUTER_API_KEY='your_api_key'")
        print("\nOr add OPENROUTER_API_KEY=your_api_key to a .env file")
        print("Or use --api-key flag")
        sys.exit(1)
    
    # Find AI generation script
    script_dir = Path(__file__).parent
    ai_script = script_dir / "generate_slide_image_ai.py"
    
    if not ai_script.exists():
        print(f"Error: AI generation script not found: {ai_script}")
        sys.exit(1)
    
    # Build command
    cmd = [sys.executable, str(ai_script), args.prompt, "-o", args.output]
    
    # Add attachments
    if args.attachments:
        for att in args.attachments:
            cmd.extend(["--attach", att])
    
    if args.visual_only:
        cmd.append("--visual-only")
    
    cmd.extend(["--iterations", str(args.iterations)])
    
    if args.verbose:
        cmd.append("-v")
    
    # Execute — pass API key via environment to avoid exposure in process listings
    try:
        result = subprocess.run(cmd, check=False, env=build_subprocess_env(api_key))
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error executing AI generation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
