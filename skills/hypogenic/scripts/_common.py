"""Shared, dependency-light helpers for the HypoGeniC skill CLIs.

The helpers perform bounded local file I/O only. They never import HypoGeniC,
contact a network service, enumerate environment variables, load ``.env``
files, or execute text from configs, datasets, hypotheses, or results.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
HYPOGENIC_VERSION = "0.3.5"
HYPOGENIC_COMMIT = "8c3800ccae155e333fac5b530afa8abdaac38300"
HYPOGENIC_WHEEL_SHA256 = (
    "f4ee8d7fa433cd59c58e0a8fe7df2f481ae29e7465a1b30ccbdac2c216a1b755"
)
PY_YAML_VERSION = "6.0.3"

MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_JSON_BYTES = 128 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_NODES = 100_000
MAX_DOCUMENT_DEPTH = 32
MAX_ROWS = 1_000_000
MAX_HYPOTHESES = 10_000
MAX_STRING_CHARS = 100_000
MAX_CORRECT_EXAMPLES = 1_000_000

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
TASK_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,127}$")
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECRET_VALUE_RE = re.compile(
    r"^(?:sk-(?:proj-)?|sk-ant-|sess-|api[_-]?key[:=])[A-Za-z0-9_-]{8,}$",
    re.IGNORECASE,
)

PROVIDER_ENV = {
    "gpt": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "huggingface": None,
    "vllm": None,
}
PROVIDER_DESTINATION = {
    "gpt": "openai_api",
    "claude": "anthropic_api",
    "huggingface": "local_process",
    "vllm": "local_process",
}
REMOTE_PROVIDERS = frozenset({"gpt", "claude"})
LOCAL_PROVIDERS = frozenset({"huggingface", "vllm"})
SPLIT_NAMES = ("train", "validation", "test")
MISSING_PREDICTION = "<missing>"


class CliError(ValueError):
    """A concise, user-correctable CLI validation error."""


def _reject_constant(value: str) -> None:
    raise CliError(f"non-standard JSON constant is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliError("duplicate object key is forbidden (key redacted)")
        result[key] = value
    return result


def _reject_url_or_secret_path(value: str) -> None:
    lowered = value.strip().lower()
    if "\x00" in value:
        raise CliError("paths must not contain a NUL byte")
    if "://" in lowered or lowered.startswith(
        ("http:", "https:", "ftp:", "s3:", "gs:", "file:")
    ):
        raise CliError("URLs are not accepted as local paths")
    if any(part.lower().startswith(".env") for part in Path(value).parts):
        raise CliError(".env files and directories are not accepted")


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_components(path: Path) -> None:
    absolute = _absolute_lexical(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                raise CliError(f"symlink paths are forbidden: {current.name!r}")
        except OSError as exc:
            raise CliError(f"cannot inspect path component {current.name!r}: {exc}") from exc


def _within_root(candidate: Path, root: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CliError("path escapes the declared root directory") from exc


def checked_root(value: str | os.PathLike[str]) -> Path:
    """Resolve an existing local directory used as the I/O boundary."""

    raw = os.fspath(value)
    _reject_url_or_secret_path(raw)
    supplied = _absolute_lexical(Path(raw).expanduser())
    try:
        resolved = supplied.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise CliError(f"cannot access root directory: {exc}") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise CliError("root must be an existing directory")
    _reject_symlink_components(resolved)
    return resolved


def checked_input_file(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    suffixes: Iterable[str],
    max_bytes: int,
) -> Path:
    """Return a bounded regular file inside root, rejecting traversal/symlinks."""

    raw = os.fspath(value)
    _reject_url_or_secret_path(raw)
    path_value = Path(raw).expanduser()
    if ".." in path_value.parts:
        raise CliError("parent-directory traversal is forbidden")
    root_path = checked_root(root)
    path = path_value if path_value.is_absolute() else root_path / path_value
    path = _absolute_lexical(path)
    _within_root(path, root_path)
    _reject_symlink_components(path)
    if path.is_symlink():
        raise CliError(f"input must not be a symlink: {path.name!r}")
    try:
        resolved = path.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise CliError(f"cannot access input file {path.name!r}: {exc}") from exc
    _within_root(resolved, root_path)
    if not stat.S_ISREG(info.st_mode):
        raise CliError(f"input is not a regular file: {path.name!r}")
    allowed = {suffix.lower() for suffix in suffixes}
    if resolved.suffix.lower() not in allowed:
        raise CliError(f"input suffix must be one of: {', '.join(sorted(allowed))}")
    if info.st_size > max_bytes:
        raise CliError(
            f"input {path.name!r} is {info.st_size} bytes; limit is {max_bytes}"
        )
    return resolved


def safe_relative_path(
    value: Any,
    *,
    name: str,
    suffixes: Iterable[str] | None = None,
    allow_dot: bool = False,
) -> str:
    """Validate a lexical relative path without touching the filesystem."""

    if not isinstance(value, str) or not value or len(value) > 1024:
        raise CliError(f"{name} must be a nonempty relative path")
    _reject_url_or_secret_path(value)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CliError(f"{name} must stay relative and contain no '..' segments")
    normalized = path.as_posix()
    if normalized in {"", "."} and not allow_dot:
        raise CliError(f"{name} must name a path below the root")
    if suffixes is not None:
        allowed = {suffix.lower() for suffix in suffixes}
        if path.suffix.lower() not in allowed:
            raise CliError(f"{name} suffix must be one of: {', '.join(sorted(allowed))}")
    return normalized


def resolve_manifest_path(
    value: str,
    *,
    data_root: Path,
    suffixes: Iterable[str],
    max_bytes: int,
) -> Path:
    """Resolve a manifest-owned file beneath an already checked data root."""

    relative = safe_relative_path(value, name="manifest split path", suffixes=suffixes)
    return checked_input_file(
        relative,
        root=data_root,
        suffixes=suffixes,
        max_bytes=max_bytes,
    )


def _validate_plain_document(value: Any) -> Any:
    """Accept only JSON-compatible scalar/container types with global bounds."""

    nodes = 0

    def visit(item: Any, depth: int) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_DOCUMENT_NODES:
            raise CliError(f"document exceeds {MAX_DOCUMENT_NODES} nodes")
        if depth > MAX_DOCUMENT_DEPTH:
            raise CliError(f"document exceeds depth {MAX_DOCUMENT_DEPTH}")
        if item is None or isinstance(item, (str, bool)):
            if isinstance(item, str) and len(item) > MAX_STRING_CHARS:
                raise CliError(f"string exceeds {MAX_STRING_CHARS} characters")
            return item
        if isinstance(item, int):
            return item
        if isinstance(item, float):
            if not math.isfinite(item):
                raise CliError("non-finite numbers are forbidden")
            return item
        if isinstance(item, list):
            return [visit(child, depth + 1) for child in item]
        if isinstance(item, dict):
            result: dict[str, Any] = {}
            for key, child in item.items():
                if not isinstance(key, str):
                    raise CliError("object keys must be strings")
                if key in result:
                    raise CliError("duplicate object key is forbidden (key redacted)")
                result[key] = visit(child, depth + 1)
            return result
        raise CliError(f"unsupported scalar type: {type(item).__name__}")

    return visit(value, 0)


def _load_yaml(text: str) -> Any:
    """Parse YAML with one reviewed PyYAML version and a restricted loader."""

    try:
        import yaml
    except ImportError as exc:
        raise CliError(
            f"YAML requires PyYAML=={PY_YAML_VERSION}; JSON needs no dependency"
        ) from exc
    if getattr(yaml, "__version__", None) != PY_YAML_VERSION:
        raise CliError(
            f"YAML parser must be exactly PyYAML=={PY_YAML_VERSION}; "
            f"found {getattr(yaml, '__version__', 'unknown')}"
        )

    forbidden_tokens = (
        yaml.tokens.AliasToken,
        yaml.tokens.AnchorToken,
        yaml.tokens.TagToken,
    )
    try:
        for token in yaml.scan(text):
            if isinstance(token, forbidden_tokens):
                raise CliError("YAML aliases, anchors, and explicit tags are forbidden")
    except yaml.YAMLError as exc:
        raise CliError("invalid YAML token stream (source content redacted)") from exc

    class UniqueSafeLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader: Any, node: Any, deep: bool = False) -> dict[str, Any]:
        loader.flatten_mapping(node)
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise CliError("YAML mapping keys must be strings")
            if key in mapping:
                raise CliError("duplicate YAML key is forbidden (key redacted)")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueSafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )
    try:
        return yaml.load(text, Loader=UniqueSafeLoader)
    except CliError:
        raise
    except yaml.YAMLError as exc:
        raise CliError("invalid safe YAML (source content redacted)") from exc


def load_structured_document(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    max_bytes: int = MAX_CONFIG_BYTES,
) -> Any:
    """Load strict JSON or restricted YAML from a bounded local file."""

    path = checked_input_file(
        value,
        root=root,
        suffixes={".json", ".yaml", ".yml"},
        max_bytes=max_bytes,
    )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CliError(f"cannot read UTF-8 input {path.name!r}: {exc}") from exc
    try:
        if path.suffix.lower() == ".json":
            document = json.loads(
                text,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
        else:
            document = _load_yaml(text)
    except CliError:
        raise
    except json.JSONDecodeError as exc:
        raise CliError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc
    return _validate_plain_document(document)


def load_json_document(
    value: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] = ".",
    max_bytes: int = MAX_JSON_BYTES,
) -> Any:
    path = checked_input_file(
        value,
        root=root,
        suffixes={".json"},
        max_bytes=max_bytes,
    )
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(
                handle,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
    except CliError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot read strict JSON from {path.name!r}: {exc}") from exc
    return _validate_plain_document(document)


def validate_keys(
    value: Any,
    *,
    required: Iterable[str],
    optional: Iterable[str] = (),
    context: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CliError(f"{context} must be an object")
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise CliError(f"{context} is missing keys: {', '.join(missing)}")
    if unknown:
        raise CliError(f"{context} has unknown keys: {', '.join(unknown)}")
    return value


def bounded_int(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CliError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise CliError(f"{name} must be between {minimum} and {maximum}")
    return value


def finite_number(
    value: Any,
    *,
    name: str,
    minimum: float = 0.0,
    maximum: float = 1_000_000_000.0,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CliError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise CliError(f"{name} must be finite and between {minimum} and {maximum}")
    return number


def nonempty_text(value: Any, *, name: str, maximum: int = 1024) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or "\x00" in value
    ):
        raise CliError(f"{name} must be a nonempty string of at most {maximum} characters")
    if SECRET_VALUE_RE.match(value.strip()):
        raise CliError(f"{name} appears to contain a secret value")
    return value


def strict_bool(value: Any, *, name: str, expected: bool | None = None) -> bool:
    if not isinstance(value, bool):
        raise CliError(f"{name} must be true or false")
    if expected is not None and value is not expected:
        raise CliError(f"{name} must be {str(expected).lower()}")
    return value


def normalized_sha256(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value.lower()) is None:
        raise CliError(f"{name} must be a 64-character SHA-256 hex digest")
    return value.lower()


def normalized_date(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        raise CliError(f"{name} must use YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CliError(f"{name} is not a calendar date") from exc
    return value


def _validate_no_secret_fields(value: Any, *, context: str = "config") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if lowered in {
                "api_key",
                "api_key_value",
                "secret",
                "token",
                "password",
                "credentials",
            }:
                raise CliError(
                    f"{context} contains forbidden secret-bearing field {key!r}; "
                    "use credential_env"
                )
            _validate_no_secret_fields(child, context=f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_secret_fields(child, context=f"{context}[{index}]")
    elif isinstance(value, str) and SECRET_VALUE_RE.match(value.strip()):
        raise CliError(f"{context} appears to contain a secret value")


def validate_run_config(document: Any) -> dict[str, Any]:
    """Validate the skill-local, plan-only run policy schema."""

    top = validate_keys(
        document,
        required=(
            "schema_version",
            "data",
            "provider",
            "limits",
            "pricing",
            "execution",
            "logging",
        ),
        context="run config",
    )
    if top["schema_version"] != SCHEMA_VERSION:
        raise CliError(f"schema_version must be {SCHEMA_VERSION!r}")
    _validate_no_secret_fields(top)

    raw_data = validate_keys(
        top["data"],
        required=(
            "task_config",
            "dataset_manifest",
            "output_directory",
            "test_split_policy",
        ),
        context="data",
    )
    if raw_data["test_split_policy"] != "locked_until_final":
        raise CliError("data.test_split_policy must be 'locked_until_final'")
    data = {
        "task_config": safe_relative_path(
            raw_data["task_config"],
            name="data.task_config",
            suffixes={".json", ".yaml", ".yml"},
        ),
        "dataset_manifest": safe_relative_path(
            raw_data["dataset_manifest"],
            name="data.dataset_manifest",
            suffixes={".json"},
        ),
        "output_directory": safe_relative_path(
            raw_data["output_directory"],
            name="data.output_directory",
        ),
        "test_split_policy": "locked_until_final",
    }

    raw_provider = validate_keys(
        top["provider"],
        required=(
            "type",
            "model",
            "credential_env",
            "data_destination",
            "local_model_path",
        ),
        context="provider",
    )
    provider_type = raw_provider["type"]
    if provider_type not in PROVIDER_ENV:
        raise CliError(f"provider.type must be one of {sorted(PROVIDER_ENV)}")
    model = nonempty_text(raw_provider["model"], name="provider.model", maximum=256)
    expected_env = PROVIDER_ENV[provider_type]
    credential_env = raw_provider["credential_env"]
    if credential_env != expected_env:
        raise CliError(
            f"provider.credential_env for {provider_type!r} must be {expected_env!r}"
        )
    if isinstance(credential_env, str) and ENV_NAME_RE.fullmatch(credential_env) is None:
        raise CliError("provider.credential_env is not a valid named environment variable")
    destination = raw_provider["data_destination"]
    if destination != PROVIDER_DESTINATION[provider_type]:
        raise CliError(
            f"provider.data_destination for {provider_type!r} must be "
            f"{PROVIDER_DESTINATION[provider_type]!r}"
        )
    local_model_path = raw_provider["local_model_path"]
    if provider_type in LOCAL_PROVIDERS:
        local_model_path = safe_relative_path(
            local_model_path,
            name="provider.local_model_path",
        )
    elif local_model_path is not None:
        raise CliError("provider.local_model_path must be null for hosted providers")
    provider = {
        "type": provider_type,
        "model": model,
        "credential_env": credential_env,
        "data_destination": destination,
        "local_model_path": local_model_path,
    }

    raw_limits = validate_keys(
        top["limits"],
        required=(
            "max_requests",
            "max_input_tokens_per_request",
            "max_output_tokens_per_request",
            "max_total_tokens",
            "max_cost_usd",
            "max_concurrent",
            "train_examples",
            "validation_examples",
            "test_examples",
            "max_hypotheses",
        ),
        context="limits",
    )
    limits = {
        "max_requests": bounded_int(
            raw_limits["max_requests"], name="limits.max_requests", minimum=1, maximum=1_000_000
        ),
        "max_input_tokens_per_request": bounded_int(
            raw_limits["max_input_tokens_per_request"],
            name="limits.max_input_tokens_per_request",
            minimum=1,
            maximum=10_000_000,
        ),
        "max_output_tokens_per_request": bounded_int(
            raw_limits["max_output_tokens_per_request"],
            name="limits.max_output_tokens_per_request",
            minimum=1,
            maximum=10_000_000,
        ),
        "max_total_tokens": bounded_int(
            raw_limits["max_total_tokens"],
            name="limits.max_total_tokens",
            minimum=1,
            maximum=10_000_000_000,
        ),
        "max_cost_usd": finite_number(
            raw_limits["max_cost_usd"],
            name="limits.max_cost_usd",
            minimum=0.01,
            maximum=1_000_000.0,
        ),
        "max_concurrent": bounded_int(
            raw_limits["max_concurrent"],
            name="limits.max_concurrent",
            minimum=1,
            maximum=128,
        ),
        "train_examples": bounded_int(
            raw_limits["train_examples"],
            name="limits.train_examples",
            minimum=1,
            maximum=MAX_ROWS,
        ),
        "validation_examples": bounded_int(
            raw_limits["validation_examples"],
            name="limits.validation_examples",
            minimum=1,
            maximum=MAX_ROWS,
        ),
        "test_examples": bounded_int(
            raw_limits["test_examples"],
            name="limits.test_examples",
            minimum=1,
            maximum=MAX_ROWS,
        ),
        "max_hypotheses": bounded_int(
            raw_limits["max_hypotheses"],
            name="limits.max_hypotheses",
            minimum=1,
            maximum=MAX_HYPOTHESES,
        ),
    }

    raw_pricing = validate_keys(
        top["pricing"],
        required=(
            "input_usd_per_million_tokens",
            "output_usd_per_million_tokens",
            "reviewed_on",
            "source",
        ),
        context="pricing",
    )
    input_rate = raw_pricing["input_usd_per_million_tokens"]
    output_rate = raw_pricing["output_usd_per_million_tokens"]
    if (input_rate is None) != (output_rate is None):
        raise CliError("both pricing token rates must be null or both must be numeric")
    if input_rate is None:
        if raw_pricing["reviewed_on"] is not None or raw_pricing["source"] is not None:
            raise CliError("pricing date/source must be null when rates are null")
        pricing = {
            "input_usd_per_million_tokens": None,
            "output_usd_per_million_tokens": None,
            "reviewed_on": None,
            "source": None,
        }
    else:
        pricing = {
            "input_usd_per_million_tokens": finite_number(
                input_rate,
                name="pricing.input_usd_per_million_tokens",
                minimum=0.0,
                maximum=100_000.0,
            ),
            "output_usd_per_million_tokens": finite_number(
                output_rate,
                name="pricing.output_usd_per_million_tokens",
                minimum=0.0,
                maximum=100_000.0,
            ),
            "reviewed_on": normalized_date(
                raw_pricing["reviewed_on"], name="pricing.reviewed_on"
            ),
            "source": nonempty_text(
                raw_pricing["source"], name="pricing.source", maximum=2048
            ),
        }

    raw_execution = validate_keys(
        top["execution"],
        required=(
            "mode",
            "external_calls_authorized",
            "require_separate_confirmation",
            "send_test_split",
        ),
        context="execution",
    )
    if raw_execution["mode"] != "plan_only":
        raise CliError("execution.mode must be 'plan_only'")
    execution = {
        "mode": "plan_only",
        "external_calls_authorized": strict_bool(
            raw_execution["external_calls_authorized"],
            name="execution.external_calls_authorized",
            expected=False,
        ),
        "require_separate_confirmation": strict_bool(
            raw_execution["require_separate_confirmation"],
            name="execution.require_separate_confirmation",
            expected=True,
        ),
        "send_test_split": strict_bool(
            raw_execution["send_test_split"],
            name="execution.send_test_split",
            expected=False,
        ),
    }

    raw_logging = validate_keys(
        top["logging"],
        required=(
            "level",
            "redact_prompts",
            "redact_responses",
            "include_credentials",
        ),
        context="logging",
    )
    if raw_logging["level"] not in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise CliError("logging.level must be INFO, WARNING, ERROR, or CRITICAL")
    logging = {
        "level": raw_logging["level"],
        "redact_prompts": strict_bool(
            raw_logging["redact_prompts"],
            name="logging.redact_prompts",
            expected=True,
        ),
        "redact_responses": strict_bool(
            raw_logging["redact_responses"],
            name="logging.redact_responses",
            expected=True,
        ),
        "include_credentials": strict_bool(
            raw_logging["include_credentials"],
            name="logging.include_credentials",
            expected=False,
        ),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "data": data,
        "provider": provider,
        "limits": limits,
        "pricing": pricing,
        "execution": execution,
        "logging": logging,
    }


def named_env_presence(config: Mapping[str, Any]) -> dict[str, Any]:
    """Check only the validated provider-specific environment variable name."""

    name = config["provider"]["credential_env"]
    if name is None:
        return {"required": False, "name": None, "present": None, "value_included": False}
    if name not in {value for value in PROVIDER_ENV.values() if value is not None}:
        raise CliError("credential environment name is not allowlisted")
    return {
        "required": True,
        "name": name,
        "present": bool(os.getenv(name)),
        "value_included": False,
    }


def _validate_prompt_value(value: Any, *, context: str, depth: int = 0) -> None:
    if depth > 16:
        raise CliError(f"{context} exceeds prompt-template depth 16")
    if isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            raise CliError(f"{context} exceeds {MAX_STRING_CHARS} characters")
        return
    if isinstance(value, list):
        if len(value) > 256:
            raise CliError(f"{context} has more than 256 list entries")
        for index, child in enumerate(value):
            _validate_prompt_value(child, context=f"{context}[{index}]", depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 256:
            raise CliError(f"{context} has more than 256 object entries")
        for key, child in value.items():
            nonempty_text(key, name=f"{context} key", maximum=128)
            _validate_prompt_value(child, context=f"{context}.{key}", depth=depth + 1)
        return
    raise CliError(f"{context} must contain only strings, lists, and objects")


def validate_task_config(document: Any) -> dict[str, Any]:
    """Validate the pinned source's task-config surface without interpreting prompts."""

    top = validate_keys(
        document,
        required=(
            "task_name",
            "train_data_path",
            "val_data_path",
            "test_data_path",
            "prompt_templates",
        ),
        optional=("label_name", "ood_data_path"),
        context="task config",
    )
    task_name = nonempty_text(top["task_name"], name="task_name", maximum=128)
    if TASK_NAME_RE.fullmatch(task_name) is None:
        raise CliError(f"task_name must match {TASK_NAME_RE.pattern}")
    label_name = top.get("label_name", "label")
    if not isinstance(label_name, str) or NAME_RE.fullmatch(label_name) is None:
        raise CliError(f"label_name must match {NAME_RE.pattern}")
    paths = {
        key: safe_relative_path(
            top[key],
            name=key,
            suffixes={".json"},
        )
        for key in ("train_data_path", "val_data_path", "test_data_path")
    }
    if len(set(paths.values())) != 3:
        raise CliError("train, validation, and test paths must be distinct")
    ood_path = None
    if "ood_data_path" in top:
        ood_path = safe_relative_path(
            top["ood_data_path"],
            name="ood_data_path",
            suffixes={".json"},
        )
        if ood_path in set(paths.values()):
            raise CliError("ood_data_path must be distinct from train/validation/test")

    templates = top["prompt_templates"]
    if not isinstance(templates, dict) or not templates or len(templates) > 256:
        raise CliError("prompt_templates must be a nonempty object with at most 256 keys")
    required_templates = {"observations", "batched_generation", "inference"}
    missing_templates = sorted(required_templates - set(templates))
    if missing_templates:
        raise CliError(
            "prompt_templates is missing basic keys: " + ", ".join(missing_templates)
        )
    _validate_prompt_value(templates, context="prompt_templates")
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": task_name,
        "label_name": label_name,
        **paths,
        "ood_data_path": ood_path,
        "prompt_template_keys": sorted(templates),
        "prompt_text_interpreted": False,
    }


def validate_dataset_manifest(document: Any) -> dict[str, Any]:
    top = validate_keys(
        document,
        required=(
            "schema_version",
            "source",
            "root",
            "label_field",
            "identity_fields",
            "splits",
        ),
        context="dataset manifest",
    )
    if top["schema_version"] != SCHEMA_VERSION:
        raise CliError(f"schema_version must be {SCHEMA_VERSION!r}")
    source_obj = validate_keys(
        top["source"],
        required=("repository", "revision", "retrieved_on"),
        context="source",
    )
    repository = nonempty_text(
        source_obj["repository"], name="source.repository", maximum=2048
    )
    if not repository.startswith(
        ("https://github.com/", "https://huggingface.co/")
    ):
        raise CliError("source.repository must be an HTTPS GitHub or Hugging Face URL")
    revision = source_obj["revision"]
    if not isinstance(revision, str) or REVISION_RE.fullmatch(revision.lower()) is None:
        raise CliError("source.revision must be an immutable 40-64 character hex revision")
    root = safe_relative_path(
        top["root"],
        name="manifest root",
        allow_dot=True,
    )
    label_field = top["label_field"]
    if not isinstance(label_field, str) or NAME_RE.fullmatch(label_field) is None:
        raise CliError(f"label_field must match {NAME_RE.pattern}")
    identity_fields = top["identity_fields"]
    if (
        not isinstance(identity_fields, list)
        or not identity_fields
        or len(identity_fields) > 128
    ):
        raise CliError("identity_fields must contain 1 to 128 field names")
    normalized_fields: list[str] = []
    for index, field in enumerate(identity_fields):
        if not isinstance(field, str) or NAME_RE.fullmatch(field) is None:
            raise CliError(f"identity_fields[{index}] must match {NAME_RE.pattern}")
        normalized_fields.append(field)
    if len(set(normalized_fields)) != len(normalized_fields):
        raise CliError("identity_fields must not contain duplicates")
    if label_field in normalized_fields:
        raise CliError("label_field must not be included in identity_fields")

    splits = top["splits"]
    if not isinstance(splits, list) or len(splits) != 3:
        raise CliError("splits must contain exactly train, validation, and test")
    normalized_splits: list[dict[str, str]] = []
    names: list[str] = []
    paths: list[str] = []
    for index, raw_split in enumerate(splits):
        split = validate_keys(
            raw_split,
            required=("name", "path", "sha256"),
            context=f"splits[{index}]",
        )
        name = split["name"]
        if name not in SPLIT_NAMES:
            raise CliError(f"splits[{index}].name must be one of {SPLIT_NAMES}")
        path = safe_relative_path(
            split["path"],
            name=f"splits[{index}].path",
            suffixes={".json"},
        )
        names.append(name)
        paths.append(path)
        normalized_splits.append(
            {
                "name": name,
                "path": path,
                "sha256": normalized_sha256(
                    split["sha256"], name=f"splits[{index}].sha256"
                ),
            }
        )
    if set(names) != set(SPLIT_NAMES) or len(set(names)) != 3:
        raise CliError("splits must name train, validation, and test exactly once")
    if len(set(paths)) != 3:
        raise CliError("split paths must be distinct")
    normalized_splits.sort(key=lambda item: SPLIT_NAMES.index(item["name"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "repository": repository,
            "revision": revision.lower(),
            "retrieved_on": normalized_date(
                source_obj["retrieved_on"], name="source.retrieved_on"
            ),
        },
        "root": root,
        "label_field": label_field,
        "identity_fields": normalized_fields,
        "splits": normalized_splits,
    }


def validate_hypothesis_bank(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict) or not document:
        raise CliError("hypothesis bank root must be a nonempty object")
    if len(document) > MAX_HYPOTHESES:
        raise CliError(f"hypothesis bank exceeds {MAX_HYPOTHESES} entries")
    entries: list[dict[str, Any]] = []
    allowed = {
        "hypothesis",
        "acc",
        "reward",
        "num_visits",
        "correct_examples",
        "num_select",
    }
    required = {
        "hypothesis",
        "acc",
        "reward",
        "num_visits",
        "correct_examples",
    }
    for index, (hypothesis, raw_info) in enumerate(document.items()):
        text = nonempty_text(
            hypothesis,
            name=f"hypothesis key {index}",
            maximum=MAX_STRING_CHARS,
        )
        info = validate_keys(
            raw_info,
            required=required,
            optional=allowed - required,
            context=f"hypothesis[{index}]",
        )
        if info["hypothesis"] != text:
            raise CliError(f"hypothesis[{index}].hypothesis must equal its object key")
        accuracy = finite_number(
            info["acc"], name=f"hypothesis[{index}].acc", minimum=0.0, maximum=1.0
        )
        reward = finite_number(
            info["reward"],
            name=f"hypothesis[{index}].reward",
            minimum=-1_000_000_000.0,
            maximum=1_000_000_000.0,
        )
        visits = bounded_int(
            info["num_visits"],
            name=f"hypothesis[{index}].num_visits",
            minimum=0,
            maximum=MAX_ROWS,
        )
        correct_examples = info["correct_examples"]
        if (
            not isinstance(correct_examples, list)
            or len(correct_examples) > MAX_CORRECT_EXAMPLES
        ):
            raise CliError(
                f"hypothesis[{index}].correct_examples must be a bounded list"
            )
        for example_index, example in enumerate(correct_examples):
            if not isinstance(example, list) or len(example) != 2:
                raise CliError(
                    f"hypothesis[{index}].correct_examples[{example_index}] "
                    "must be [row_index, label]"
                )
            bounded_int(
                example[0],
                name=(
                    f"hypothesis[{index}].correct_examples[{example_index}][0]"
                ),
                minimum=0,
                maximum=MAX_ROWS,
            )
            nonempty_text(
                example[1],
                name=(
                    f"hypothesis[{index}].correct_examples[{example_index}][1]"
                ),
                maximum=256,
            )
        if "num_select" in info:
            bounded_int(
                info["num_select"],
                name=f"hypothesis[{index}].num_select",
                minimum=0,
                maximum=MAX_ROWS,
            )
        normalized = " ".join(text.split()).casefold()
        entries.append(
            {
                "text": text,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "normalized_sha256": hashlib.sha256(
                    normalized.encode("utf-8")
                ).hexdigest(),
                "characters": len(text),
                "words": len(text.split()),
                "accuracy": accuracy,
                "reward": reward,
                "num_visits": visits,
                "correct_example_count": len(correct_examples),
            }
        )
    return entries


def validate_result_document(document: Any) -> dict[str, Any]:
    top = validate_keys(
        document,
        required=(
            "schema_version",
            "dataset_manifest_sha256",
            "hypothesis_bank_sha256",
            "split",
            "records",
        ),
        context="result document",
    )
    if top["schema_version"] != SCHEMA_VERSION:
        raise CliError(f"schema_version must be {SCHEMA_VERSION!r}")
    split = top["split"]
    if split not in SPLIT_NAMES:
        raise CliError(f"split must be one of {SPLIT_NAMES}")
    records = top["records"]
    if not isinstance(records, list) or not records or len(records) > MAX_ROWS:
        raise CliError(f"records must contain 1 to {MAX_ROWS} objects")
    normalized_records: list[dict[str, str | None]] = []
    identifiers: set[str] = set()
    for index, raw_record in enumerate(records):
        record = validate_keys(
            raw_record,
            required=("id", "label", "prediction"),
            context=f"records[{index}]",
        )
        identifier = nonempty_text(
            record["id"], name=f"records[{index}].id", maximum=256
        )
        if identifier in identifiers:
            raise CliError(f"records[{index}].id duplicates an earlier result id (value redacted)")
        identifiers.add(identifier)
        label = nonempty_text(
            record["label"], name=f"records[{index}].label", maximum=256
        )
        if label == MISSING_PREDICTION:
            raise CliError(f"records[{index}].label uses a reserved value")
        prediction = record["prediction"]
        if prediction is not None:
            prediction = nonempty_text(
                prediction,
                name=f"records[{index}].prediction",
                maximum=256,
            )
            if prediction == MISSING_PREDICTION:
                raise CliError(f"records[{index}].prediction uses a reserved value")
        normalized_records.append(
            {"id": identifier, "label": label, "prediction": prediction}
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_manifest_sha256": normalized_sha256(
            top["dataset_manifest_sha256"], name="dataset_manifest_sha256"
        ),
        "hypothesis_bank_sha256": normalized_sha256(
            top["hypothesis_bank_sha256"], name="hypothesis_bank_sha256"
        ),
        "split": split,
        "records": normalized_records,
    }


def label_fingerprint(label: str) -> str:
    return "label-" + hashlib.sha256(label.encode("utf-8")).hexdigest()[:12]


def classification_metrics(records: Sequence[Mapping[str, str | None]]) -> dict[str, Any]:
    """Compute deterministic local classification metrics without dependencies."""

    labels = {str(record["label"]) for record in records}
    labels.update(
        str(record["prediction"])
        for record in records
        if record["prediction"] is not None
    )
    ordered_labels = sorted(labels)
    total = len(records)
    covered = sum(record["prediction"] is not None for record in records)
    correct = sum(record["prediction"] == record["label"] for record in records)
    covered_correct = sum(
        record["prediction"] == record["label"]
        for record in records
        if record["prediction"] is not None
    )

    f1_values: list[float] = []
    for label in ordered_labels:
        true_positive = sum(
            record["label"] == label and record["prediction"] == label
            for record in records
        )
        false_positive = sum(
            record["label"] != label and record["prediction"] == label
            for record in records
        )
        false_negative = sum(
            record["label"] == label and record["prediction"] != label
            for record in records
        )
        denominator = 2 * true_positive + false_positive + false_negative
        f1_values.append(0.0 if denominator == 0 else 2 * true_positive / denominator)

    prediction_labels = ordered_labels + [MISSING_PREDICTION]
    confusion: dict[str, dict[str, int]] = {}
    for true_label in ordered_labels:
        true_key = label_fingerprint(true_label)
        confusion[true_key] = {}
        for predicted_label in prediction_labels:
            predicted_key = (
                MISSING_PREDICTION
                if predicted_label == MISSING_PREDICTION
                else label_fingerprint(predicted_label)
            )
            count = sum(
                record["label"] == true_label
                and (
                    record["prediction"]
                    if record["prediction"] is not None
                    else MISSING_PREDICTION
                )
                == predicted_label
                for record in records
            )
            confusion[true_key][predicted_key] = count

    return {
        "record_count": total,
        "covered_count": covered,
        "missing_prediction_count": total - covered,
        "label_count": len(ordered_labels),
        "label_fingerprints": [label_fingerprint(label) for label in ordered_labels],
        "coverage": round(covered / total, 12),
        "accuracy_all_records": round(correct / total, 12),
        "accuracy_covered_records": (
            None if covered == 0 else round(covered_correct / covered, 12)
        ),
        "macro_f1_all_records": round(sum(f1_values) / len(f1_values), 12),
        "confusion_matrix_redacted": confusion,
    }


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CliError(f"value cannot be represented as strict JSON: {exc}") from exc


def sha256_file(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> str:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise CliError(f"cannot stat input file: {exc}") from exc
    if size > max_bytes:
        raise CliError(f"file is {size} bytes; hashing limit is {max_bytes}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CliError(f"cannot hash input file: {exc}") from exc
    return digest.hexdigest()


def summarize_numbers(values: Sequence[float | int]) -> dict[str, float | int | None]:
    if not values:
        return {"minimum": None, "maximum": None, "mean": None}
    return {
        "minimum": min(values),
        "maximum": max(values),
        "mean": round(sum(values) / len(values), 12),
    }


def count_values(values: Iterable[str]) -> list[dict[str, Any]]:
    """Return redacted value counts ordered by descending count then digest."""

    counts = Counter(values)
    rows = [
        {"fingerprint": label_fingerprint(value), "count": count}
        for value, count in counts.items()
    ]
    return sorted(rows, key=lambda row: (-row["count"], row["fingerprint"]))


def strict_json_bytes(document: Any) -> bytes:
    try:
        payload = (
            json.dumps(
                document,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CliError(f"report is not strict JSON: {exc}") from exc
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(f"report exceeds {MAX_REPORT_BYTES} bytes")
    return payload


def emit_json(document: Any, *, stream: Any = None) -> None:
    if stream is None:
        stream = sys.stdout
    print(strict_json_bytes(document).decode("utf-8"), end="", file=stream)


def emit_error(error: Exception) -> int:
    emit_json(
        {
            "ok": False,
            "error": type(error).__name__,
            "message": str(error),
            "network_access": False,
            "model_called": False,
            "secret_values_included": False,
        },
        stream=sys.stderr,
    )
    return 2
