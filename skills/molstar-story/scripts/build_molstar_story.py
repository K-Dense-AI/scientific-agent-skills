#!/usr/bin/env python3
"""Build a trusted MolViewStories source tree into portable review artifacts."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote
import zipfile


MOL_VIEW_STORIES_COMMIT = "6edd08a0be4663a3431ae4f9d394e97a0908fd09"
MOLSTAR_VERSION = "5.8.0"
CLI_PACKAGE_VERSION = "1.0.0-dev10"
MIN_DENO_VERSION = (1, 40, 0)
SAFE_NAME_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="trusted story source containing story.yaml and assets/")
    parser.add_argument("output", type=Path, help="output directory")
    parser.add_argument(
        "--mol-view-stories-repo",
        type=Path,
        required=True,
        help="official molstar/mol-view-stories checkout at the pinned commit",
    )
    parser.add_argument("--deno", type=Path, required=True, help="Deno executable (>=1.40)")
    parser.add_argument(
        "--deno-dir",
        type=Path,
        help="optional persistent DENO_DIR cache shared by builds of the pinned runtime",
    )
    parser.add_argument("--name", default="story", help="artifact stem (default: story)")
    parser.add_argument(
        "--full-package",
        action="store_true",
        help="also build MVSX, self-hosted ZIP, and an unpacked HTTP viewer",
    )
    return parser.parse_args()


def run(command: list[str], *, env: dict[str, str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(completed.stdout, end="")
    if completed.returncode:
        raise RuntimeError(
            f"command failed with exit {completed.returncode}: "
            + " ".join(quote(part, safe="/._-") for part in command)
        )
    return completed.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deno_version(deno: Path, env: dict[str, str]) -> str:
    output = run([str(deno), "--version"], env=env)
    first = output.splitlines()[0].strip()
    match = re.fullmatch(r"deno\s+(\d+)\.(\d+)\.(\d+).*", first)
    if not match:
        raise RuntimeError(f"cannot parse Deno version from: {first!r}")
    version = tuple(int(part) for part in match.groups())
    if version < MIN_DENO_VERSION:
        required = ".".join(str(part) for part in MIN_DENO_VERSION)
        raise RuntimeError(f"Deno {required}+ is required; observed {first}")
    return ".".join(str(part) for part in version)


def validate_source(source: Path) -> list[dict[str, object]]:
    story_yaml = source / "story.yaml"
    assets = source / "assets"
    if not story_yaml.is_file():
        raise RuntimeError(f"story source is missing story.yaml: {source}")
    if not assets.is_dir() or not any(path.is_file() for path in assets.iterdir()):
        raise RuntimeError("a local assets/ file is required for portable Story output")

    story_text = story_yaml.read_text(encoding="utf-8")
    if re.search(r"(?m)^scene_defaults\s*:", story_text):
        raise RuntimeError(
            "the pinned MolViewStories CLI ignores scene_defaults for inline scenes; "
            "set linger_duration_ms and transition_duration_ms on each scene"
        )

    records: list[dict[str, object]] = []
    placeholders: list[str] = []
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        relative = path.relative_to(source).as_posix()
        if path.suffix.lower() in {".yaml", ".yml", ".js", ".md", ".json"}:
            text = path.read_text(encoding="utf-8")
            if "REPLACE_" in text:
                placeholders.append(relative)
        records.append(
            {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    if placeholders:
        raise RuntimeError(
            "unresolved REPLACE_ markers remain in: " + ", ".join(placeholders)
        )
    return records


def validate_checkout(repo: Path) -> tuple[Path, Path, Path, str]:
    cli_config = repo / "cli" / "deno.json"
    cli_main = repo / "cli" / "main.ts"
    manager = repo / "@mol-view-stories" / "lib" / "src" / "story-manager.ts"
    html_template = repo / "@mol-view-stories" / "lib" / "src" / "html-template.ts"
    for path in (cli_config, cli_main, manager, html_template):
        if not path.is_file():
            raise RuntimeError(f"incomplete MolViewStories checkout; missing {path}")

    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != MOL_VIEW_STORIES_COMMIT:
        raise RuntimeError(
            "MolViewStories checkout drift: expected "
            f"{MOL_VIEW_STORIES_COMMIT}, observed {commit}"
        )

    config = json.loads(cli_config.read_text(encoding="utf-8"))
    if config.get("version") != CLI_PACKAGE_VERSION:
        raise RuntimeError(
            f"CLI version drift: expected {CLI_PACKAGE_VERSION}, "
            f"observed {config.get('version')!r}"
        )
    imports = config.get("imports", {})
    if not any(f"molstar@{MOLSTAR_VERSION}" in str(value) for value in imports.values()):
        raise RuntimeError(f"Mol* {MOLSTAR_VERSION} is not pinned by cli/deno.json")
    return cli_main, manager, html_template, commit


def safe_extract(archive: Path, destination: Path) -> list[str]:
    extracted: list[str] = []
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            relative = Path(member.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"unsafe path in self-hosted archive: {member.filename}")
            if member.is_dir():
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(handle.read(member))
            extracted.append(relative.as_posix())
    required = {
        "index.html",
        "assets/mvs-stories.js",
        "assets/mvs-stories.css",
        "story/session.mvstory",
    }
    if not required.issubset(extracted) or not any(
        name in extracted for name in ("story/data.mvsx", "story/data.mvsj")
    ):
        raise RuntimeError("self-hosted archive is missing required viewer members")
    return sorted(extracted)


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    repo = args.mol_view_stories_repo.expanduser().resolve()
    deno = args.deno.expanduser().resolve()
    if not SAFE_NAME_RE.fullmatch(args.name):
        raise SystemExit("--name must use only letters, digits, dot, underscore, and hyphen")
    if not source.is_dir():
        raise SystemExit(f"story source is not a directory: {source}")
    if not deno.is_file():
        raise SystemExit(f"Deno executable does not exist: {deno}")

    source_files = validate_source(source)
    cli_main, manager, html_template, commit = validate_checkout(repo)
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if args.deno_dir:
        cache = args.deno_dir.expanduser().resolve()
        cache.mkdir(parents=True, exist_ok=True)
        env["DENO_DIR"] = str(cache)
    observed_deno = deno_version(deno, env)

    mvstory = output / f"{args.name}.mvstory"
    file_openable = output / f"{args.name}_file_openable.html"
    base_command = [
        str(deno),
        "run",
        "--config",
        str(repo / "cli" / "deno.json"),
        "--allow-read",
        "--allow-write",
        "--allow-env",
        "--allow-net",
        str(cli_main),
        "build",
        str(source),
    ]
    mvsx = output / f"{args.name}.mvsx"
    self_hosted = output / f"{args.name}_self_hosted.zip"
    viewer = output / "viewer"
    if args.full_package:
        run(base_command + ["-f", "mvsx", "-o", str(mvsx)], env=env)
    run(base_command + ["-f", "mvstory", "-o", str(mvstory)], env=env)

    exporter = f'''import {{ StoryManager }} from {json.dumps(manager.as_uri())};
import {{ generateStoriesHtml }} from {json.dumps(html_template.as_uri())};

if (!("toBase64" in Uint8Array.prototype)) {{
  (Uint8Array.prototype as unknown as {{ toBase64: () => string }}).toBase64 = function () {{
    const bytes = this as unknown as Uint8Array;
    let binary = "";
    const chunkSize = 0x8000;
    for (let start = 0; start < bytes.length; start += chunkSize) {{
      binary += String.fromCharCode(...bytes.subarray(start, start + chunkSize));
    }}
    return btoa(binary);
  }};
}}

const input = await Deno.readFile(Deno.args[0]);
const manager = await StoryManager.fromMVStory(input);
const output = await manager.toSelfHostedZip({{ molstarVersion: {json.dumps(MOLSTAR_VERSION)} }});
await Deno.writeFile(Deno.args[1], output);
const story = manager.getStory();
const data = await manager.toMVS();
const html = generateStoriesHtml(
  {{ kind: "embed", data }},
  {{
    title: story.metadata.title,
    molstarVersion: {json.dumps(MOLSTAR_VERSION)},
    jsPath: "__MVS_STORIES_JS__",
    cssPath: "__MVS_STORIES_CSS__",
  }},
);
await Deno.writeTextFile(Deno.args[2], html);
'''
    with tempfile.TemporaryDirectory(prefix="molstar_story_export_") as tempdir:
        temp_root = Path(tempdir)
        exporter_path = Path(tempdir) / "export_self_hosted.ts"
        exporter_path.write_text(exporter, encoding="utf-8")
        exported_zip = self_hosted if args.full_package else temp_root / "self_hosted.zip"
        exported_viewer = viewer if args.full_package else temp_root / "viewer"
        run(
            [
                str(deno),
                "run",
                "--config",
                str(repo / "cli" / "deno.json"),
                "--allow-read",
                "--allow-write",
                "--allow-env",
                "--allow-net",
                str(exporter_path),
                str(mvstory),
                str(exported_zip),
                str(file_openable),
            ],
            env=env,
        )
        members = safe_extract(exported_zip, exported_viewer)
        html = file_openable.read_text(encoding="utf-8")
        inline_assets = {
            "__MVS_STORIES_JS__": (
                "text/javascript",
                exported_viewer / "assets" / "mvs-stories.js",
            ),
            "__MVS_STORIES_CSS__": (
                "text/css",
                exported_viewer / "assets" / "mvs-stories.css",
            ),
        }
        for marker, (mime_type, asset) in inline_assets.items():
            if marker not in html:
                raise RuntimeError(f"file-openable viewer is missing marker: {marker}")
            encoded = base64.b64encode(asset.read_bytes()).decode("ascii")
            html = html.replace(marker, f"data:{mime_type};base64,{encoded}")
        if "__MVS_STORIES_" in html or "mvsStories.loadFromData" not in html:
            raise RuntimeError("file-openable viewer did not embed its runtime and MVS data")
        file_openable.write_text(html, encoding="utf-8")

    artifacts = {}
    artifact_paths = [mvstory, file_openable]
    if args.full_package:
        artifact_paths.extend((mvsx, self_hosted, viewer / "index.html"))
    for path in artifact_paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"expected output is empty or missing: {path}")
        artifacts[path.relative_to(output).as_posix()] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }

    manifest = {
        "status": "built_not_browser_accepted",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "trusted_source": True,
        "output_profile": "full_package" if args.full_package else "file_review",
        "source_files": source_files,
        "software": {
            "mol_view_stories_commit": commit,
            "cli_package_version": CLI_PACKAGE_VERSION,
            "molstar_version": MOLSTAR_VERSION,
            "deno_version": observed_deno,
        },
        "artifacts": artifacts,
        "runtime_boundary": (
            f"{file_openable.name} opens directly via file:// with embedded MVS data "
            "and runtime"
            + (
                "; viewer/index.html is the optional HTTP-served package"
                if args.full_package
                else "; HTTP viewer was not built"
            )
        ),
        "acceptance_boundary": "build success is not browser, scene, interaction, or scientific acceptance",
    }
    if args.full_package:
        manifest["viewer_members"] = members
    manifest_path = output / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"built MolViewStories {manifest['output_profile']}: {output}")
    print(f"file-openable browser acceptance still required: {file_openable}")
    if args.full_package:
        print(f"HTTP-served browser acceptance still required: {viewer / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
