#!/usr/bin/env python3
"""Exercise a file-openable MolViewStories export offline and capture its scenes."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import time


VIEWPORTS = {
    "desktop": {"width": 1280, "height": 900},
    "narrow": {"width": 390, "height": 844},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story", type=Path, help="file-openable Story HTML")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-scenes", type=int)
    parser.add_argument(
        "--scene",
        type=int,
        action="append",
        help="1-based scene to inspect; repeatable; defaults to all scenes",
    )
    parser.add_argument("--viewport", choices=sorted(VIEWPORTS), default="desktop")
    parser.add_argument("--timeout-ms", type=int, default=60000)
    parser.add_argument("--load-settle-ms", type=int, default=8000)
    parser.add_argument("--scene-settle-ms", type=int, default=1500)
    parser.add_argument(
        "--camera-tolerance",
        type=float,
        default=0.05,
        help="maximum Euclidean error for camera position, target, and up vector",
    )
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument(
        "--chromium-software-webgl",
        action="store_true",
        help="enable Chromium's SwiftShader WebGL backend for headless qualification",
    )
    return parser.parse_args()


def pixel_report(png: bytes) -> dict[str, object]:
    try:
        from PIL import Image, ImageStat
    except ImportError as exc:
        raise SystemExit(
            "Pillow is required for check_story.py canvas checks; install Pillow "
            "before running browser acceptance"
        ) from exc
    image = Image.open(BytesIO(png)).convert("RGB")
    sample = image.copy()
    sample.thumbnail((160, 160))
    pixels = list(sample.getdata())
    common, _count = Counter(pixels).most_common(1)[0]
    non_background = sum(
        1
        for pixel in pixels
        if sum((pixel[index] - common[index]) ** 2 for index in range(3)) > 100
    ) / len(pixels)
    stddev = [round(value, 2) for value in ImageStat.Stat(sample).stddev]
    unique = len(set(pixels))
    return {
        "size": list(image.size),
        "stddev_rgb": stddev,
        "non_background_fraction": round(non_background, 4),
        "unique_sample_colors": unique,
        "passed": (
            image.width >= 100
            and image.height >= 100
            and statistics_mean(stddev) > 2.0
            and non_background > 0.002
            and unique > 16
        ),
    }


def statistics_mean(values: list[float]) -> float:
    return sum(values) / len(values)


def clear_owned_outputs(output_dir: Path, viewport: str) -> None:
    for path in output_dir.glob(f"scene_*_{viewport}_canvas.png"):
        path.unlink()
    for path in output_dir.glob(f"scene_*_{viewport}_viewport.png"):
        path.unlink()
    report = output_dir / f"story_check_{viewport}.json"
    if report.exists():
        report.unlink()


def webgl_report(page) -> dict[str, object]:
    return page.locator("canvas").first.evaluate(
        """canvas => {
          const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
          if (!gl) return { available: false };
          const debug = gl.getExtension('WEBGL_debug_renderer_info');
          return {
            available: true,
            version: gl.getParameter(gl.VERSION),
            renderer: gl.getParameter(gl.RENDERER),
            unmasked_renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
          };
        }"""
    )


def camera_state(page, scene_index: int) -> dict[str, object]:
    return page.evaluate(
        """sceneIndex => {
          const plugin = window.mvsStories.getContext()
            .state.viewers._value[0].model.plugin;
          const entry = plugin.managers.snapshot.state.entries
            .toArray()[sceneIndex];
          return {
            live: plugin.canvas3d.camera.getSnapshot(),
            target: entry?.snapshot?.camera?.current ?? null,
            busy: plugin.behaviors.state.isBusy.value,
          };
        }""",
        scene_index,
    )


def vector_error(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def wait_for_camera(page, scene_index: int, timeout_ms: int, tolerance: float) -> dict[str, object]:
    started = time.monotonic()
    state = camera_state(page, scene_index)
    if state["target"] is None:
        previous = state["live"]
        stable_reads = 0
        waited_ms = 0
        errors = {key: float("inf") for key in ("position", "target", "up")}
        while waited_ms < timeout_ms:
            page.wait_for_timeout(100)
            state = camera_state(page, scene_index)
            errors = {
                key: vector_error(state["live"][key], previous[key])
                for key in ("position", "target", "up")
            }
            waited_ms = round((time.monotonic() - started) * 1000)
            stable_reads = (
                stable_reads + 1
                if max(errors.values()) <= tolerance and not state["busy"]
                else 0
            )
            if stable_reads >= 3:
                return {
                    "method": "camera_stability",
                    "converged": True,
                    "waited_ms": waited_ms,
                    "tolerance": tolerance,
                    "errors": {
                        key: round(value, 6) for key, value in errors.items()
                    },
                }
            previous = state["live"]
        return {
            "method": "camera_stability",
            "converged": False,
            "waited_ms": round((time.monotonic() - started) * 1000),
            "tolerance": tolerance,
            "errors": {key: round(value, 6) for key, value in errors.items()},
            "busy": state["busy"],
        }
    errors: dict[str, float] = {}
    waited_ms = 0
    while waited_ms < timeout_ms:
        errors = {
            key: vector_error(state["live"][key], state["target"][key])
            for key in ("position", "target", "up")
        }
        waited_ms = round((time.monotonic() - started) * 1000)
        if max(errors.values()) <= tolerance and not state["busy"]:
            return {
                "method": "target_snapshot",
                "converged": True,
                "waited_ms": waited_ms,
                "tolerance": tolerance,
                "errors": {key: round(value, 6) for key, value in errors.items()},
            }
        if waited_ms >= timeout_ms:
            break
        page.wait_for_timeout(100)
        state = camera_state(page, scene_index)
    return {
        "method": "target_snapshot",
        "converged": False,
        "waited_ms": round((time.monotonic() - started) * 1000),
        "tolerance": tolerance,
        "errors": {key: round(value, 6) for key, value in errors.items()},
        "busy": state["busy"],
    }


def wait_for_canvas_stability(page, canvas, scene_index: int, timeout_ms: int):
    """Wait for representation work to stop changing the rendered canvas."""
    started = time.monotonic()
    minimum_ms = min(750, timeout_ms)
    stable_reads = 0
    previous_digest: str | None = None
    latest_png = canvas.screenshot()
    waited_ms = 0
    digest = hashlib.sha256(latest_png).hexdigest()
    while waited_ms < timeout_ms:
        state = camera_state(page, scene_index)
        latest_png = canvas.screenshot()
        digest = hashlib.sha256(latest_png).hexdigest()
        waited_ms = round((time.monotonic() - started) * 1000)
        stable_reads = (
            stable_reads + 1
            if digest == previous_digest and not state["busy"]
            else 0
        )
        if waited_ms >= minimum_ms and stable_reads >= 3:
            return (
                {
                    "method": "canvas_digest_stability",
                    "converged": True,
                    "waited_ms": waited_ms,
                    "stable_reads": stable_reads,
                    "sha256": digest,
                },
                latest_png,
            )
        if waited_ms >= timeout_ms:
            break
        previous_digest = digest
        page.wait_for_timeout(200)
    return (
        {
            "method": "canvas_digest_stability",
            "converged": False,
            "waited_ms": round((time.monotonic() - started) * 1000),
            "stable_reads": stable_reads,
            "sha256": digest,
            "busy": state["busy"],
        },
        latest_png,
    )


def main() -> int:
    args = parse_args()
    if args.expected_scenes is not None and args.expected_scenes <= 0:
        raise SystemExit("--expected-scenes must be positive")
    if (
        args.timeout_ms <= 0
        or args.load_settle_ms < 0
        or args.scene_settle_ms < 0
        or args.camera_tolerance <= 0
    ):
        raise SystemExit("timeout must be positive and settle delays non-negative")
    story = args.story.expanduser().resolve()
    if not story.is_file():
        raise SystemExit(f"Story HTML does not exist: {story}")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    clear_owned_outputs(output_dir, args.viewport)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required for check_story.py; install Playwright and "
            "a Chromium browser before running browser acceptance"
        ) from exc

    report: dict[str, object] = {
        "story": str(story),
        "transport": {"scheme": "file", "offline_context": True},
        "viewport": {"name": args.viewport, **VIEWPORTS[args.viewport]},
        "expected_scenes": args.expected_scenes,
        "selected_scenes": [],
        "requests": [],
        "failed_requests": [],
        "console_errors": [],
        "page_errors": [],
        "scenes": [],
    }
    with sync_playwright() as playwright:
        launch: dict[str, object] = {"headless": True}
        if args.browser_executable:
            launch["executable_path"] = str(args.browser_executable.expanduser().resolve())
        if args.chromium_software_webgl:
            launch["args"] = [
                "--use-angle=swiftshader-webgl",
                "--enable-unsafe-swiftshader",
                "--enable-webgl",
                "--ignore-gpu-blocklist",
            ]
        browser = playwright.chromium.launch(**launch)
        try:
            context = browser.new_context(
                viewport=VIEWPORTS[args.viewport], device_scale_factor=1, offline=True
            )
            page = context.new_page()
            page.on(
                "request",
                lambda request: report["requests"].append(
                    {"url": request.url, "resource_type": request.resource_type}
                ),
            )
            page.on(
                "requestfailed",
                lambda request: report["failed_requests"].append(
                    {"url": request.url, "failure": request.failure}
                ),
            )
            page.on(
                "console",
                lambda message: (
                    report["console_errors"].append(message.text)
                    if message.type == "error"
                    else None
                ),
            )
            page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
            response = page.goto(story.as_uri(), wait_until="load", timeout=args.timeout_ms)
            report["transport"]["document_status"] = response.status if response else None
            page.wait_for_timeout(args.load_settle_ms)

            selector = page.locator("select").filter(visible=True).first
            selector.wait_for(state="visible", timeout=args.timeout_ms)
            options = selector.locator("option").all_text_contents()
            observed = len(options)
            report["scene_count_observed"] = observed
            report["option_labels"] = options
            if args.expected_scenes is not None and observed != args.expected_scenes:
                report["scene_count_error"] = (
                    f"observed {observed} scenes, expected {args.expected_scenes}"
                )
            selected = args.scene or list(range(1, observed + 1))
            invalid = [index for index in selected if index < 1 or index > observed]
            if invalid:
                raise SystemExit(f"scene indices out of range 1..{observed}: {invalid}")
            report["selected_scenes"] = selected

            canvas = page.locator("canvas").first
            canvas.wait_for(state="visible", timeout=args.timeout_ms)
            report["webgl"] = webgl_report(page)
            for scene_index in selected:
                selector.select_option(index=scene_index - 1)
                camera = wait_for_camera(
                    page,
                    scene_index - 1,
                    max(args.scene_settle_ms, 1),
                    args.camera_tolerance,
                )
                visual, canvas_png = wait_for_canvas_stability(
                    page,
                    canvas,
                    scene_index - 1,
                    max(args.scene_settle_ms, 1),
                )
                selected_label = selector.locator("option:checked").inner_text()
                viewport_png = page.screenshot(full_page=False)
                canvas_name = f"scene_{scene_index:02d}_{args.viewport}_canvas.png"
                viewport_name = f"scene_{scene_index:02d}_{args.viewport}_viewport.png"
                (output_dir / canvas_name).write_bytes(canvas_png)
                (output_dir / viewport_name).write_bytes(viewport_png)
                pixels = pixel_report(canvas_png)
                description = page.locator("body").inner_text().strip()
                scene = {
                    "index": scene_index,
                    "selected_label": selected_label,
                    "description_excerpt": description[:1200],
                    "canvas_screenshot": canvas_name,
                    "viewport_screenshot": viewport_name,
                    "pixels": pixels,
                    "camera": camera,
                    "visual": visual,
                    "passed": bool(
                        pixels["passed"]
                        and camera["converged"]
                        and visual["converged"]
                    ),
                }
                report["scenes"].append(scene)

            interaction_exercised = False
            box = canvas.bounding_box()
            if box:
                center_x = box["x"] + box["width"] / 2
                center_y = box["y"] + box["height"] / 2
                page.mouse.move(center_x, center_y)
                page.mouse.down()
                page.mouse.move(center_x + 35, center_y + 20, steps=5)
                page.mouse.up()
                page.mouse.wheel(0, -250)
                page.mouse.click(center_x, center_y)
                page.wait_for_timeout(300)
                interaction_exercised = True
            report["interaction_exercised"] = interaction_exercised
            context.close()
        finally:
            browser.close()

    report["passed"] = bool(
        report["webgl"].get("available")
        and report["interaction_exercised"]
        and not report.get("scene_count_error")
        and not report["failed_requests"]
        and not report["console_errors"]
        and not report["page_errors"]
        and report["scenes"]
        and all(scene["passed"] for scene in report["scenes"])
    )
    report_path = output_dir / f"story_check_{args.viewport}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
