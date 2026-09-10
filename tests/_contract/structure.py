"""The structural contract every skill in this repository must satisfy.

Nothing here imports skill code. Scripts are read and parsed with `ast`, never
executed, so the whole contract is safe to run against every skill inside a
single interpreter -- which is what `tests/_meta` does. Per-skill suites that
*do* import their scripts still need one process each; see `tests/conftest.py`.

Every check takes a skill directory and returns a list of human-readable
problems, empty when the skill conforms. Returning problems rather than
asserting keeps the checks reusable: `tests/_meta` reports them per rule and
per skill, so one broken link names the file and the line rather than failing
an opaque assertion.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# The Agent Skills specification defines a closed set of top-level keys. Any
# other key is a validation error, and because strictyaml rejects the whole
# document, it takes `name` and `description` down with it.
ALLOWED_FRONTMATTER_FIELDS = frozenset(
    {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}
)

MAX_SKILL_MD_LINES = 500

# `__import__` is deliberately absent: several skills use it for a legitimate
# availability probe (`try: __import__("torch")`) or to reach pathlib before
# the sys.path insert that makes `_common` importable.
BANNED_BUILTIN_CALLS = frozenset({"eval", "exec"})
BANNED_OS_CALLS = frozenset({"system", "popen"})

# Inline-code and markdown-link references to files the skill ships.
_INLINE_PATH = re.compile(r"`((?:assets|references|scripts)/[A-Za-z0-9_./-]+)`")
_MARKDOWN_LINK = re.compile(r"\]\(((?:assets|references|scripts)/[A-Za-z0-9_./-]+)\)")

# A path in executable position -- `python scripts/thumbnail.py`, `./scripts/run.sh`.
# Inside a fenced block these carry no backticks, so the two patterns above miss
# them, yet they are the references that strand an agent hardest: it runs the
# command and gets "No such file or directory" instead of a document it can work
# around. Matching only the executable slot keeps output paths (`-o assets/x.svg`)
# and prose about deleted files out of the results.
_COMMAND_PATH = re.compile(
    r"(?:^|\s)(?:python[23]?|bash|sh|uv run(?: python)?)\s+"
    r"((?:assets|references|scripts)/[A-Za-z0-9_./-]+)"
    r"|(?:^|\s)\./((?:assets|references|scripts)/[A-Za-z0-9_./-]+)"
)

# An absolute path under someone's home or drive mount is a leaked local
# environment: it names a person, and it cannot work on any other machine.
_PERSONAL_PATH = re.compile(
    r"/(?:mnt/[a-z]/Users|home|Users)/(?!<|\$|\{)([A-Za-z0-9._-]+)/"
)

# Service and platform accounts that legitimately appear in documentation --
# `/home/dnanexus/` is where a DNAnexus worker runs, not somebody's laptop --
# plus the placeholder spellings skills use for "your username".
_IMPERSONAL_ACCOUNTS = frozenset(
    {
        "dnanexus", "ubuntu", "root", "runner", "ec2-user", "jovyan", "vscode",
        "airflow", "nextflow", "opt", "shared", "linuxbrew",
        "user", "username", "you", "me", "youruser", "your-user", "name",
    }
)


def script_bearing_skills(skills_dir: Path = SKILLS_DIR) -> list[Path]:
    """Skill directories that ship at least one file under `scripts/`.

    An empty `scripts/` directory does not count. Git cannot track empty
    directories, so one only ever exists as local cruft, and requiring a test
    suite for a skill that ships no scripts would be nonsense.
    """
    return [
        skill
        for skill in sorted(skills_dir.iterdir())
        if skill.is_dir()
        and (skill / "SKILL.md").is_file()
        and any((skill / "scripts").rglob("*"))
    ]


def all_skill_names(skills_dir: Path = SKILLS_DIR) -> set[str]:
    return {
        skill.name
        for skill in skills_dir.iterdir()
        if skill.is_dir() and (skill / "SKILL.md").is_file()
    }


def documented_skills(skills_dir: Path = SKILLS_DIR) -> list[Path]:
    """Every skill directory, whether or not it ships scripts.

    The document-level rules in `DOCUMENT_RULES` apply here. Restricting them to
    script-bearing skills would leave the docs of a reference-only skill
    unchecked, which is how a broken `references/` link can survive review.
    """
    return [
        skill
        for skill in sorted(skills_dir.iterdir())
        if skill.is_dir() and (skill / "SKILL.md").is_file()
    ]


def _frontmatter(skill: Path) -> str | None:
    """The raw YAML between the opening and closing `---`, or None."""
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[4:end]


def _top_level_entries(frontmatter: str) -> list[tuple[str, str]]:
    """(key, value) for every unindented `key: value` line."""
    entries = []
    for line in frontmatter.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$", line)
        if match:
            entries.append((match.group(1), match.group(2).strip()))
    return entries


def _metadata_scalars(frontmatter: str) -> list[tuple[str, str]]:
    """(key, value) for scalars nested one level under `metadata:`.

    Host manifest blocks (`openclaw`, `hermes`) nest further; their contents
    are deliberately skipped -- the spec exempts them from the string-only
    rule, and they carry booleans on purpose.
    """
    lines = frontmatter.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("metadata:"))
    except StopIteration:
        return []
    scalars = []
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        match = re.match(r"^  ([A-Za-z][A-Za-z0-9_-]*):(.*)$", line)
        if match and match.group(2).strip():
            scalars.append((match.group(1), match.group(2).strip()))
    return scalars


def frontmatter_problems(skill: Path) -> list[str]:
    """Frontmatter parses, uses only spec fields, and is versioned."""
    problems: list[str] = []
    if not (skill / "SKILL.md").is_file():
        return [f"{skill.name}: no SKILL.md"]

    frontmatter = _frontmatter(skill)
    if frontmatter is None:
        return [f"{skill.name}: SKILL.md has no `---` delimited frontmatter"]

    entries = _top_level_entries(frontmatter)
    keys = [key for key, _ in entries]

    for key in keys:
        if key not in ALLOWED_FRONTMATTER_FIELDS:
            problems.append(
                f"{skill.name}: top-level `{key}` is not one of the six spec fields "
                "-- move it under `metadata`"
            )
    for required in ("name", "description", "metadata"):
        if required not in keys:
            problems.append(f"{skill.name}: frontmatter is missing `{required}`")

    values = dict(entries)
    name = values.get("name", "").strip("\"'")
    if name and name != skill.name:
        problems.append(
            f"{skill.name}: frontmatter name is `{name}`, must equal the directory name"
        )

    # strictyaml rejects JSON flow style outright, taking the whole document
    # with it -- so `name` and `description` become unreadable too.
    for key, value in entries:
        if value.startswith(("{", "[")):
            problems.append(
                f"{skill.name}: `{key}` uses JSON flow style; strictyaml rejects it"
            )

    tools = values.get("allowed-tools")
    if tools is not None and ("," in tools or tools.startswith("[")):
        problems.append(
            f"{skill.name}: `allowed-tools` must be a space-separated string"
        )

    scalars = dict(_metadata_scalars(frontmatter))
    if "version" not in scalars:
        problems.append(f"{skill.name}: `metadata.version` is required")
    for key, value in scalars.items():
        # Only values YAML would actually coerce. `1.0.0` has two dots, so it
        # is already a string; `1.0` is a float and must be quoted.
        ambiguous = re.fullmatch(
            r"\d+|\d+\.\d+|true|false|yes|no|on|off|\d{4}-\d{2}-\d{2}", value, re.I
        )
        if ambiguous:
            problems.append(
                f"{skill.name}: `metadata.{key}: {value}` must be quoted to stay a string"
            )
    return problems


def length_problems(skill: Path) -> list[str]:
    """SKILL.md stays under 500 lines; longer material belongs in references/."""
    lines = len((skill / "SKILL.md").read_text(encoding="utf-8").splitlines())
    if lines > MAX_SKILL_MD_LINES:
        return [
            f"{skill.name}: SKILL.md is {lines} lines, over the {MAX_SKILL_MD_LINES}-line "
            "limit -- move reference material into references/"
        ]
    return []


def stray_test_problems(skill: Path) -> list[str]:
    """Tests never live under skills/ -- a skill ships only what an agent loads."""
    strays = [
        str(path.relative_to(skill))
        for path in sorted(skill.rglob("*"))
        if (path.is_dir() and path.name == "tests")
        or (path.is_file() and path.name.startswith("test_") and path.suffix == ".py")
    ]
    return [
        f"{skill.name}: ships {stray}; tests belong in tests/{skill.name}/"
        for stray in strays
    ]


@lru_cache(maxsize=1)
def _tracked_files(skills_dir: Path = SKILLS_DIR) -> frozenset[str] | None:
    """Repo-relative paths git tracks under `skills/`, or None outside a checkout."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--", str(skills_dir)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if listed.returncode != 0:
        return None
    return frozenset(listed.stdout.split())


def bytecode_problems(skill: Path) -> list[str]:
    """No compiled bytecode ships with a skill.

    "Ships" means committed. Importing a skill's scripts is what creates
    `__pycache__`, and running one by hand outside pytest -- which sets
    `PYTHONDONTWRITEBYTECODE` -- leaves some behind, so scanning the working
    tree would fail on local cruft that is already gitignored. Fall back to a
    filesystem scan only when git cannot answer.
    """
    tracked = _tracked_files()
    candidates = [
        path
        for path in sorted(skill.rglob("*"))
        if path.suffix in {".pyc", ".pyo"} or path.name == "__pycache__"
    ]
    if tracked is not None:
        candidates = [
            path
            for path in candidates
            if str(path.relative_to(REPO_ROOT)) in tracked
            or any(entry.startswith(f"{path.relative_to(REPO_ROOT)}/") for entry in tracked)
        ]
    return [
        f"{skill.name}: ships bytecode artifact {path.relative_to(skill)}"
        for path in candidates
    ]


def link_problems(skill: Path, known_skills: Iterable[str] | None = None) -> list[str]:
    """Every `assets/`, `references/`, or `scripts/` path in the docs resolves.

    Skills routinely point at each other -- bulk-rnaseq documents
    `pathway-enrichment`'s `scripts/run_enrichment.py`, citation-management
    points at `pyzotero` -> `references/exports.md`. A path that does not
    resolve inside this skill is therefore accepted when another skill is
    named on the same line and owns it.
    """
    names = set(known_skills) if known_skills is not None else all_skill_names()
    documents = [
        skill / "SKILL.md",
        *sorted((skill / "references").glob("*.md")),
        *sorted((skill / "assets").glob("*.md")),
    ]

    problems = []
    for document in documents:
        if not document.is_file():
            continue
        for number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            commands = {
                match
                for pair in _COMMAND_PATH.findall(line)
                for match in pair
                if match
            }
            for relative in set(_INLINE_PATH.findall(line)) | set(
                _MARKDOWN_LINK.findall(line)
            ) | commands:
                if (skill / relative).exists():
                    continue
                owners = [
                    other
                    for other in names
                    if other != skill.name
                    and other in line
                    and (SKILLS_DIR / other / relative).exists()
                ]
                if owners:
                    continue
                problems.append(
                    f"{skill.name}: {document.name}:{number} references "
                    f"`{relative}`, which does not exist"
                )
    return problems


def _script_paths(skill: Path, suffix: str = ".py") -> list[Path]:
    return sorted((skill / "scripts").rglob(f"*{suffix}"))


def compile_problems(skill: Path) -> list[str]:
    """Every bundled Python script parses -- a syntax error can never ship."""
    problems = []
    for path in _script_paths(skill):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            problems.append(
                f"{skill.name}: {path.relative_to(skill)} does not parse: "
                f"line {error.lineno}: {error.msg}"
            )
    return problems


def dynamic_execution_problems(skill: Path) -> list[str]:
    """No `eval`, `exec`, `os.system`, or `os.popen` in bundled scripts.

    A narrower rule than the Cisco scanner's, and a complementary one: this is
    deterministic and runs on every skill every time, where the scanner is
    LLM-backed and runs only on changed skills.
    """
    problems = []
    for path in _script_paths(skill):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue  # compile_problems already reports it
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if isinstance(function, ast.Name) and function.id in BANNED_BUILTIN_CALLS:
                problems.append(
                    f"{skill.name}: {path.relative_to(skill)}:{node.lineno} "
                    f"calls {function.id}()"
                )
            if (
                isinstance(function, ast.Attribute)
                and function.attr in BANNED_OS_CALLS
                and isinstance(function.value, ast.Name)
                and function.value.id == "os"
            ):
                problems.append(
                    f"{skill.name}: {path.relative_to(skill)}:{node.lineno} "
                    f"calls os.{function.attr}()"
                )
    return problems


def shadow_module_problems(skill: Path) -> list[str]:
    """No script shadows a standard-library module.

    Tests and the scripts themselves put `scripts/` on `sys.path`, so a file
    named `json.py` or `csv.py` there wins over the real module for the rest
    of the process.
    """
    return [
        f"{skill.name}: scripts/{path.name} shadows the standard-library module "
        f"`{path.stem}`"
        for path in sorted((skill / "scripts").glob("*.py"))
        if path.stem in sys.stdlib_module_names
    ]


def personal_path_problems(skill: Path) -> list[str]:
    """No script or document hardcodes somebody's home directory.

    A path like `/mnt/c/Users/<name>/Data/kg.csv` names a real person and works
    on exactly one machine. Placeholders are fine -- `/home/$USER/`,
    `/Users/<you>/` -- so the pattern skips anything that looks templated.
    """
    documents = [
        skill / "SKILL.md",
        *sorted((skill / "references").glob("*.md")),
        *_script_paths(skill),
        *_script_paths(skill, ".sh"),
    ]
    problems = []
    for document in documents:
        if not document.is_file():
            continue
        for number, line in enumerate(
            document.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            for match in _PERSONAL_PATH.finditer(line):
                if match.group(1).lower() in _IMPERSONAL_ACCOUNTS:
                    continue
                problems.append(
                    f"{skill.name}: {document.relative_to(skill)}:{number} hardcodes "
                    f"the local path `{match.group(0)}`"
                )
    return problems


def shell_script_problems(skill: Path) -> list[str]:
    """Bundled shell scripts have a shebang, the executable bit, and parse."""
    problems = []
    for path in _script_paths(skill, ".sh"):
        relative = path.relative_to(skill)
        first_line = path.read_text(encoding="utf-8").splitlines()[:1]
        if not first_line or not first_line[0].startswith("#!"):
            problems.append(f"{skill.name}: {relative} has no shebang")
        if not path.stat().st_mode & 0o111:
            problems.append(f"{skill.name}: {relative} is not executable")
        syntax = subprocess.run(
            ["bash", "-n", str(path)], capture_output=True, text=True, timeout=30
        )
        if syntax.returncode != 0:
            problems.append(
                f"{skill.name}: {relative} fails `bash -n`: {syntax.stderr.strip()}"
            )
    return problems


#: Rule name -> check. `tests/_meta` iterates this so a new rule is picked up
#: repo-wide by adding one entry.
CHECKS: dict[str, Callable[[Path], list[str]]] = {
    "frontmatter": frontmatter_problems,
    "skill_md_length": length_problems,
    "no_tests_under_skills": stray_test_problems,
    "no_bytecode": bytecode_problems,
    "local_links_resolve": link_problems,
    "scripts_compile": compile_problems,
    "no_dynamic_execution": dynamic_execution_problems,
    "no_stdlib_shadowing": shadow_module_problems,
    "no_personal_paths": personal_path_problems,
    "shell_scripts": shell_script_problems,
}

# Rules that read only SKILL.md, `references/`, and `assets/`. They hold for every
# skill; the rest of `CHECKS` inspects `scripts/` and is meaningful only where a
# skill ships some.
DOCUMENT_RULES = frozenset(
    {
        "frontmatter",
        "skill_md_length",
        "no_tests_under_skills",
        "local_links_resolve",
        "no_personal_paths",
    }
)
