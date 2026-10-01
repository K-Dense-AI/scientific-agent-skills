#!/usr/bin/env python3
"""
AI-powered slide image generation using Nano Banana 2.

This script generates presentation slides or slide visuals using AI:
- full_slide mode: Generate complete slides with title, content, and visuals (for PDF workflow)
- visual_only mode: Generate just images/figures to place on slides (for PPT workflow)

Supports attaching conceptual or style references. Attachments may be redrawn;
embed original quantitative figures with native slide composition instead.

Uses smart iterative refinement:
1. Generate initial image with Nano Banana 2
2. Quality review using Gemini 3.7 Flash
3. Only regenerate if quality is below threshold
4. Repeat until quality meets standards (max iterations)

Requirements:
    - OPENROUTER_API_KEY environment variable
    - requests library

Usage:
    # Full slide for PDF workflow
    python generate_slide_image_ai.py "Title: Introduction to ML\nKey points: supervised learning, neural networks" -o slide_01.png
    
    # Visual only for PPT workflow
    python generate_slide_image_ai.py "Neural network architecture diagram" -o figure.png --visual-only
    
    # With reference images attached
    python generate_slide_image_ai.py "Draft a conceptual overview in this style" -o slide.png --attach style_reference.png
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, NamedTuple


try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: uv pip install requests")
    sys.exit(1)


class ReviewResult(NamedTuple):
    """The outcome of one quality review.

    A named tuple rather than a bare tuple because the review has several
    failure modes -- the model returns no choices, the request raises, the
    answer arrives in an unexpected shape -- and each of them used to be a
    chance to return the wrong number of values to the caller.

    `score` is None whenever no usable number was parsed, and `reviewed` is
    False whenever the review never produced an answer at all. Neither case
    invents a score: a slide whose quality was not measured is reported as
    unmeasured, not as passing.
    """

    critique: str
    score: Optional[float]
    needs_improvement: bool
    reviewed: bool
    error: Optional[str] = None


# Markdown decoration the reviewer routinely wraps its answer in. Gemini writes
# "**SCORE:** 8.5" far more often than the bare "SCORE: 8.5" the rubric asks
# for, and a pattern that does not allow for it silently scores every image
# at whatever the default happens to be.
_MARKUP = re.compile(r"[*_`#]")

_SCORE_PATTERN = re.compile(r"\bSCORE\s*:?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_LOOSE_SCORE_PATTERN = re.compile(
    r"(?:score|rating|quality)\s*[:\s]\s*(\d+(?:\.\d+)?)\s*(?:/\s*10)?", re.IGNORECASE
)
# The underscore is optional because normalization strips it out of
# NEEDS_IMPROVEMENT along with the surrounding markdown.
_VERDICT_PATTERN = re.compile(
    r"^\s*VERDICT\s*:?\s*(ACCEPTABLE|NEEDS[_ ]?IMPROVEMENT)", re.IGNORECASE | re.MULTILINE
)


def _normalize_review_text(text: str) -> str:
    """Strip markdown decoration so the rubric's fields can be found."""
    return _MARKUP.sub("", text or "")


def _parse_score(text: str) -> Optional[float]:
    """Return the reviewer's 0-10 score, or None when there isn't a usable one.

    None rather than a default: a fabricated score is indistinguishable from a
    real one once it reaches the review log, and a default near the middle of
    the range quietly passes lenient thresholds while failing strict ones.
    """
    normalized = _normalize_review_text(text)
    match = _SCORE_PATTERN.search(normalized) or _LOOSE_SCORE_PATTERN.search(normalized)
    if not match:
        return None
    score = float(match.group(1))
    # A number outside the rubric's range means something other than the score
    # was matched -- a slide number, a percentage, an iteration number.
    return score if 0.0 <= score <= 10.0 else None


def _parse_verdict(text: str) -> Optional[str]:
    """Return ACCEPTABLE / NEEDS_IMPROVEMENT from the verdict line, or None.

    Anchored to the start of a line. The rubric prompt spells out both tokens
    when it explains the response format, so a reviewer that echoes those
    instructions back would fail a perfectly good image under a plain
    substring search.
    """
    match = _VERDICT_PATTERN.search(_normalize_review_text(text))
    if not match:
        return None
    verdict = match.group(1).upper().replace(" ", "").replace("_", "")
    return "NEEDS_IMPROVEMENT" if verdict == "NEEDSIMPROVEMENT" else "ACCEPTABLE"


def _resolve_api_key(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve the OpenRouter key from --api-key, the environment, then any .env file.

    The .env scan walks up from the working directory and finally checks the
    script's own directory, so running from anywhere inside a project picks up
    the key at its root. Only the standard library is used: python-dotenv is a
    common omission, and a missing optional dependency should not read as a
    missing credential.
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


class SlideImageGenerator:
    """Generate presentation slides or visuals using AI with iterative refinement.
    
    Two modes:
    - full_slide: Generate complete slide with title, content, visuals (for PDF workflow)
    - visual_only: Generate just the image/figure for a slide (for PPT workflow)
    """
    
    # Quality threshold for presentations (lower than journal/conference papers)
    QUALITY_THRESHOLD = 6.5
    
    # Guidelines for generating full slides (complete slide images)
    FULL_SLIDE_GUIDELINES = """
Create a professional presentation slide image with these requirements:

SLIDE LAYOUT (16:9 aspect ratio):
- Clean, modern slide design
- Clear visual hierarchy: title at top, content below
- Generous margins (at least 5% on all sides)
- Balanced composition with intentional white space

TYPOGRAPHY:
- LARGE, bold title text (easily readable from distance)
- Clear, sans-serif fonts throughout
- High contrast text (dark on light or light on dark)
- Bullet points or key phrases, NOT paragraphs
- Maximum 5-6 lines of text content
- Use the supplied author/presenter; omit it when no name is provided

VISUAL ELEMENTS:
- Use GENERIC, simple images and icons - avoid overly specific or detailed imagery
- MINIMAL extra elements - no decorative borders, shadows, or flourishes
- Visuals should support and enhance the message, not distract
- Professional, clean aesthetic with restraint
- Consistent color scheme (2-3 main colors only)
- Prefer abstract/conceptual visuals over literal representations

PROFESSIONAL MINIMALISM:
- Less is more: favor empty space over additional elements
- No unnecessary decorations, gradients, or visual noise
- Clean lines and simple shapes
- Focused content without visual clutter
- Corporate/academic level of professionalism

PRESENTATION QUALITY:
- Designed for projection (high contrast)
- Bold, impactful design that commands attention
- Professional and polished appearance
- No cluttered or busy layouts
- Consistent styling throughout the deck
"""

    # Guidelines for generating slide visuals only (figures/images for PPT)
    VISUAL_ONLY_GUIDELINES = """
Create a high-quality visual/figure for a presentation slide:

IMAGE QUALITY:
- Clean, professional appearance
- High resolution and sharp details
- Suitable for embedding in a slide

DESIGN:
- Simple, clear composition with MINIMAL elements
- High contrast for projection readability
- No text unless essential to the visual
- Transparent or white background preferred
- GENERIC imagery - avoid overly specific or detailed visuals

PROFESSIONAL MINIMALISM:
- Favor simplicity over complexity
- No decorative elements, shadows, or flourishes
- Clean lines and simple shapes only
- Remove any unnecessary visual noise
- Abstract/conceptual rather than literal representations

STYLE:
- Modern, professional aesthetic
- Colorblind-friendly colors
- Bold but restrained imagery
- Suitable for scientific/professional presentations
- Corporate/academic level of polish
"""
    
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        """
        Initialize the generator.
        
        Args:
            api_key: OpenRouter API key (or use OPENROUTER_API_KEY env var)
            verbose: Print detailed progress information
        """
        self.api_key = _resolve_api_key(api_key)

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found. Please either:\n"
                "  1. Set the OPENROUTER_API_KEY environment variable\n"
                "  2. Add OPENROUTER_API_KEY to your .env file\n"
                "  3. Pass api_key parameter to the constructor\n"
                "Get your API key from: https://openrouter.ai/keys"
            )
        
        self.verbose = verbose
        self._last_error = None
        self.base_url = "https://openrouter.ai/api/v1"
        # Nano Banana 2 for image generation. The slug must be an image-output
        # model; a text-only chat model is rejected with "No endpoints found that
        # support the requested output modalities".
        # https://openrouter.ai/google/gemini-3.1-flash-image
        self.image_model = "google/gemini-3.1-flash-image"
        # Gemini 3.7 Flash for quality review - reads the image, answers in text
        self.review_model = "google/gemini-3.7-flash"
        
    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def _post_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send one non-streaming request; never automatically replay a paid call."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Scientific Slide Generator",
        }
        self._log(f"POST {endpoint} using {payload['model']}")
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint}", headers=headers,
                json=payload, timeout=120,
            )
            try:
                response_json = response.json()
            except ValueError:
                raise RuntimeError(
                    f"API returned non-JSON data (HTTP {response.status_code})"
                ) from None
            if not isinstance(response_json, dict):
                raise RuntimeError("API response must be a JSON object")
            if response.status_code != 200 or "error" in response_json:
                error = response_json.get("error", {})
                detail = error.get("message", "request rejected") if isinstance(error, dict) else str(error)
                # Providers occasionally echo input; do not dump whole bodies or credentials.
                detail = str(detail).replace(self.api_key, "[redacted]")[:500]
                raise RuntimeError(f"API request failed (HTTP {response.status_code}): {detail}")
            return response_json
        except requests.exceptions.Timeout:
            raise RuntimeError("API request timed out after 120 seconds") from None
        except requests.exceptions.RequestException as exc:
            detail = str(exc).replace(self.api_key, "[redacted]")
            raise RuntimeError(f"API request failed: {detail}") from None

    def _make_request(self, model: str, messages: List[Dict[str, Any]],
                      modalities: Optional[List[str]] = None) -> Dict[str, Any]:
        """Use chat completions for the text-and-image vision review."""
        payload = {"model": model, "messages": messages}
        if modalities:
            payload["modalities"] = modalities
        return self._post_request("chat/completions", payload)

    def _extract_image_from_response(self, response: Dict[str, Any]) -> bytes:
        """Decode the dedicated Image API response and enforce this helper's PNG contract.

        The provider may omit media_type; the PNG signature still has to match.
        This is a format check, not a full image-decoder or scientific-content check.
        """
        data = response.get("data")
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            raise RuntimeError("Image API returned no data[0] image")
        item = data[0]
        if item.get("media_type") not in (None, "image/png"):
            raise RuntimeError(f"Expected PNG output; received {item['media_type']}")
        encoded = item.get("b64_json")
        if not isinstance(encoded, str) or not encoded:
            raise RuntimeError("Image API returned no b64_json image")
        try:
            image_data = base64.b64decode(encoded, validate=True)
        except ValueError:
            raise RuntimeError("Image API returned invalid base64 image data") from None
        if not image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Image API output does not have a PNG signature")
        return image_data

    def _image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 data URL."""
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        ext = Path(image_path).suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        if ext not in mime_types:
            raise ValueError(f"Unsupported attachment format: {ext}; use PNG, JPEG, GIF, or WebP")
        mime_type = mime_types[ext]
        
        base64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{base64_data}"
    
    def generate_image(self, prompt: str, attachments: Optional[List[str]] = None) -> Optional[bytes]:
        """Generate one widescreen PNG using the dedicated Image API.

        References guide generation; they are not preserved as original pixels.
        A missing or unsupported reference aborts before a paid request.
        """
        self._last_error = None
        try:
            if attachments and len(attachments) > 14:
                raise ValueError("This image model accepts at most 14 reference images")
            payload = {
                "model": self.image_model, "prompt": prompt,
                "n": 1, "aspect_ratio": "16:9",
            }
            if attachments:
                payload["input_references"] = [
                    {"type": "image_url", "image_url": {"url": self._image_to_base64(path)}}
                    for path in attachments
                ]
            # output_format is not in this model's endpoint capability map.
            # Validate the returned PNG bytes instead of sending unsupported knobs.
            response = self._post_request("images", payload)
            image_data = self._extract_image_from_response(response)
            self._log(f"[OK] Generated PNG ({len(image_data)} bytes)")
            return image_data
        except (RuntimeError, ValueError, OSError) as exc:
            self._last_error = str(exc)
            self._log(f"[FAIL] Generation failed: {self._last_error}")
            return None

    def review_image(self, image_path: str, original_prompt: str, 
                    iteration: int, visual_only: bool = False,
                    max_iterations: int = 2) -> ReviewResult:
        """Review generated image using Gemini 3.7 Flash."""
        image_data_url = self._image_to_base64(image_path)
        threshold = self.QUALITY_THRESHOLD
        
        image_type = "slide visual/figure" if visual_only else "presentation slide"
        
        review_prompt = f"""You are an expert reviewer evaluating a {image_type} for presentation quality.

ORIGINAL REQUEST: {original_prompt}

QUALITY THRESHOLD: {threshold}/10
ITERATION: {iteration}/{max_iterations}

Evaluate this {image_type} on these criteria:

1. **Visual Impact** (0-2 points)
   - Bold, attention-grabbing design
   - Professional appearance
   - Suitable for projection

2. **Clarity** (0-2 points)
   - Easy to understand at a glance
   - Clear visual hierarchy
   - Not cluttered or busy

3. **Readability** (0-2 points)
   - Text is large and readable (if present)
   - High contrast
   - Clean typography

4. **Composition** (0-2 points)
   - Balanced layout
   - Good use of space
   - Appropriate margins

5. **Relevance** (0-2 points)
   - Matches the requested content
   - Appropriate style for presentations
   - Professional quality

RESPOND IN THIS EXACT FORMAT:
SCORE: [total score 0-10]

STRENGTHS:
- [strength 1]
- [strength 2]

ISSUES:
- [issue 1 if any]
- [issue 2 if any]

VERDICT: [ACCEPTABLE or NEEDS_IMPROVEMENT]

If score >= {threshold}, the image is ACCEPTABLE.
If score < {threshold}, mark as NEEDS_IMPROVEMENT with specific suggestions."""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": review_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}}
                ]
            }
        ]
        
        try:
            response = self._make_request(model=self.review_model, messages=messages)
            
            choices = response.get("choices", [])
            if not choices:
                # A normal enough outcome -- a rate limit, a content filter, a
                # provider hiccup. The image itself is fine; only its review is
                # missing, and saying so beats inventing a score.
                reason = "the review model returned no choices"
                self._log(f"[WARN] Review unavailable: {reason}")
                return ReviewResult(
                    f"Review unavailable: {reason}.",
                    None, False, reviewed=False, error=reason,
                )

            message = choices[0].get("message", {})
            content = message.get("content", "")

            reasoning = message.get("reasoning", "")
            if reasoning and not content:
                content = reasoning

            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = "\n".join(text_parts)

            score = _parse_score(content)
            verdict = _parse_verdict(content)

            if score is None and verdict is None:
                reason = "no score or verdict found in the review"
                self._log(f"[WARN] Review unusable: {reason}")
                return ReviewResult(
                    content if content else f"Review unusable: {reason}.",
                    None, False, reviewed=True, error=reason,
                )

            needs_improvement = verdict == "NEEDS_IMPROVEMENT" or (
                score is not None and score < threshold
            )

            shown = f"{score}/10" if score is not None else "not stated"
            self._log(f"[OK] Review complete (Score: {shown}, Threshold: {threshold}/10)")

            return ReviewResult(
                content if content else "Review returned no text",
                score,
                needs_improvement,
                reviewed=True,
                error=None if score is not None else "no score found in the review",
            )
        except Exception as e:
            # A failed review must not fail the run -- the image is already
            # generated -- but it must not read as a pass either.
            self._log(f"[WARN] Review failed: {str(e)}")
            return ReviewResult(
                f"Review failed: {str(e)}",
                None, False, reviewed=False, error=str(e),
            )
    
    def improve_prompt(self, original_prompt: str, critique: str, 
                      iteration: int, visual_only: bool = False) -> str:
        """Improve the generation prompt based on critique."""
        guidelines = self.VISUAL_ONLY_GUIDELINES if visual_only else self.FULL_SLIDE_GUIDELINES
        
        return f"""{guidelines}

USER REQUEST: {original_prompt}

ITERATION {iteration}: Based on previous feedback, address these specific improvements:
{critique}

Generate an improved version that addresses all the critique points."""
    
    def generate_slide(self, user_prompt: str, output_path: str,
                      visual_only: bool = False,
                      iterations: int = 2,
                      attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a slide image or visual with iterative refinement.
        
        Args:
            user_prompt: Description of the slide/visual to generate
            output_path: Path to save final image
            visual_only: If True, generate just the visual (for PPT workflow)
            iterations: Maximum refinement iterations (default: 2)
            attachments: Optional list of image file paths to attach as context
            
        Returns:
            Dictionary with generation results and metadata
        """
        if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 2:
            raise ValueError("iterations must be 1 or 2")
        output_path = Path(output_path)
        if output_path.suffix.lower() != ".png":
            raise ValueError("Output path must end in .png; format conversion is not supported")
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = output_path.stem
        extension = output_path.suffix or ".png"
        
        mode = "visual_only" if visual_only else "full_slide"
        guidelines = self.VISUAL_ONLY_GUIDELINES if visual_only else self.FULL_SLIDE_GUIDELINES
        
        results = {
            "user_prompt": user_prompt,
            "mode": mode,
            "quality_threshold": self.QUALITY_THRESHOLD,
            "image_model": self.image_model,
            "review_model": self.review_model,
            "quality_met": False,
            "termination_reason": None,
            "attachments": attachments or [],
            "iterations": [],
            "final_image": None,
            # None, not 0.0 -- a run whose review never completed has no score,
            # and a number here would be read as one the reviewer gave.
            "final_score": None,
            "final_reviewed": False,
            "success": False,
            "early_stop": False
        }
        
        current_prompt = f"""{guidelines}

USER REQUEST: {user_prompt}

Generate a high-quality {'visual/figure' if visual_only else 'presentation slide'} that meets all the guidelines above."""
        
        print(f"\n{'='*60}")
        print(f"Generating Slide {'Visual' if visual_only else 'Image'}")
        print(f"{'='*60}")
        print(f"Description: {user_prompt[:100]}{'...' if len(user_prompt) > 100 else ''}")
        print(f"Mode: {mode}")
        if attachments:
            print(f"Attachments: {len(attachments)} image(s)")
            for att in attachments:
                print(f"  - {att}")
        print(f"Quality Threshold: {self.QUALITY_THRESHOLD}/10")
        print(f"Max Iterations: {iterations}")
        print(f"Output: {output_path}")
        print(f"{'='*60}\n")
        
        # Track temporary files for cleanup
        temp_files = []
        final_image_data = None
        
        for i in range(1, iterations + 1):
            print(f"\n[Iteration {i}/{iterations}]")
            print("-" * 40)
            
            print(f"Generating image with Nano Banana 2...")
            image_data = self.generate_image(current_prompt, attachments=attachments)
            
            if not image_data:
                error_msg = self._last_error or 'Image generation failed'
                print(f"[FAIL] Generation failed: {error_msg}")
                results["iterations"].append({
                    "iteration": i,
                    "success": False,
                    "error": error_msg
                })
                results["termination_reason"] = "generation_failed"
                break
            
            # Save to temporary file for review (will be cleaned up)
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix=extension)
            os.close(temp_fd)
            temp_path = Path(temp_path)
            temp_files.append(temp_path)
            
            with open(temp_path, "wb") as f:
                f.write(image_data)
            print(f"[OK] Generated image (iteration {i})")
            
            print(f"Reviewing image with {self.review_model}...")
            review = self.review_image(
                str(temp_path), user_prompt, i, visual_only, iterations
            )
            if review.score is not None:
                print(f"[OK] Score: {review.score}/10 (threshold: {self.QUALITY_THRESHOLD}/10)")
            else:
                print(f"[WARN] Review unavailable - image kept, quality not verified")
                print(f"  Reason: {review.error}")

            results["iterations"].append({
                "iteration": i,
                "critique": review.critique,
                "score": review.score,
                "reviewed": review.reviewed,
                "review_error": review.error,
                "needs_improvement": review.needs_improvement,
                "success": True
            })

            # Keep this draft even when the next refinement request fails.
            final_image_data = image_data
            results["final_score"] = review.score
            results["final_reviewed"] = review.reviewed and review.score is not None
            results["success"] = True
            results["quality_met"] = (
                results["final_reviewed"] and review.score >= self.QUALITY_THRESHOLD
                and not review.needs_improvement
            )

            if not review.needs_improvement:
                results["termination_reason"] = (
                    "quality_threshold_met" if results["quality_met"] else "review_unavailable"
                )
                if review.score is not None:
                    print(f"\n[OK] Quality meets threshold ({review.score} >= {self.QUALITY_THRESHOLD})")
                else:
                    # Regenerating cannot fix a reviewer that did not answer.
                    print(f"\n[WARN] Stopping without a verified score - review the image yourself")
                final_image_data = image_data
                results["final_score"] = review.score
                results["final_reviewed"] = review.reviewed and review.score is not None
                results["success"] = True
                results["early_stop"] = True
                break

            if i == iterations:
                results["termination_reason"] = "max_iterations"
                print(f"\n[WARN] Maximum iterations reached")
                final_image_data = image_data
                results["final_score"] = review.score
                results["final_reviewed"] = review.reviewed and review.score is not None
                results["success"] = True
                break

            print(f"\n[WARN] Review requests improvement (score: {review.score}; threshold: {self.QUALITY_THRESHOLD})")
            print(f"Improving prompt...")
            current_prompt = self.improve_prompt(user_prompt, review.critique, i + 1, visual_only)
        
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
        
        # Save only the final image to output path
        if results["success"] and final_image_data:
            with open(output_path, "wb") as f:
                f.write(final_image_data)
            results["final_image"] = str(output_path)
            print(f"\n[OK] Final image: {output_path}")
        
        log_path = output_dir / f"{base_name}_review_log.json"
        log_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"[OK] Review log: {log_path}")

        print(f"\n{'='*60}")
        print(f"Generation Complete!")
        if results["final_score"] is not None:
            print(f"Final Score: {results['final_score']}/10")
        else:
            print(f"Final Score: unavailable (the review did not produce one)")
        if results["early_stop"]:
            success_count = len([r for r in results['iterations'] if r.get('success')])
            print(f"Iterations Used: {success_count}/{iterations} (early stop)")
        print(f"{'='*60}\n")
        
        return results


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate presentation slides or visuals using Nano Banana 2 AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a full slide (for PDF workflow)
  python generate_slide_image_ai.py "Title: Machine Learning Basics\\nKey points: supervised learning, neural networks, deep learning" -o slide_01.png
  
  # Generate just a visual/figure (for PPT workflow)
  python generate_slide_image_ai.py "Neural network architecture diagram with input, hidden, and output layers" -o figure.png --visual-only
  
  # With reference images attached (Nano Banana 2 will see these)
  python generate_slide_image_ai.py "Create a slide explaining this chart with key insights" -o slide.png --attach chart.png
  python generate_slide_image_ai.py "Combine these images into a comparison slide" -o compare.png --attach before.png --attach after.png
  
  # With custom iterations
  python generate_slide_image_ai.py "Title slide for AI Conference 2025" -o title.png --iterations 2
  
  # Verbose output
  python generate_slide_image_ai.py "Data flow diagram" -o flow.png -v

Environment:
  OPENROUTER_API_KEY    OpenRouter API key (required)
        """
    )
    
    parser.add_argument("prompt", help="Description of the slide or visual to generate")
    parser.add_argument("-o", "--output", required=True, help="Output image path")
    parser.add_argument("--attach", action="append", dest="attachments", metavar="IMAGE",
                       help="Attach image file(s) as context for generation (can use multiple times)")
    parser.add_argument("--visual-only", action="store_true",
                       help="Generate just the visual/figure (for PPT workflow)")
    parser.add_argument("--iterations", type=int, default=2,
                       help="Maximum refinement iterations (default: 2)")
    parser.add_argument("--api-key", help="OpenRouter API key (or set OPENROUTER_API_KEY)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Resolves --api-key, the environment, then any .env file
    api_key = _resolve_api_key(args.api_key)
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found")
        print("\nSet it with:")
        print("  export OPENROUTER_API_KEY='your_api_key'")
        print("\nOr add OPENROUTER_API_KEY=your_api_key to a .env file")
        print("Or provide via --api-key flag")
        sys.exit(1)
    
    if args.iterations < 1 or args.iterations > 2:
        print("Error: Iterations must be between 1 and 2")
        sys.exit(1)
    
    # Validate attachments exist
    if args.attachments:
        for att in args.attachments:
            if not Path(att).exists():
                print(f"Error: Attachment file not found: {att}")
                sys.exit(1)
    
    try:
        generator = SlideImageGenerator(api_key=api_key, verbose=args.verbose)
        results = generator.generate_slide(
            user_prompt=args.prompt,
            output_path=args.output,
            visual_only=args.visual_only,
            iterations=args.iterations,
            attachments=args.attachments
        )
        
        if results["success"]:
            print(f"\n[OK] Success! Image saved to: {args.output}")
            if not results["quality_met"]:
                print("[WARN] Quality criteria not verified or not met; inspect the saved draft.")
            sys.exit(0)
        else:
            print(f"\n[FAIL] Generation failed. Check review log for details.")
            sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
