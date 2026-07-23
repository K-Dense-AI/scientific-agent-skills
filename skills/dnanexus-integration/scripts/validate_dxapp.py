#!/usr/bin/env python3
"""Offline validation and safety linting for a DNAnexus dxapp.json file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Optional


NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
APP_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
VERSION_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
SECRET_KEY_RE = re.compile(
    r"(?:^|[_-])(token|password|passwd|secret|private[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)

CLASSES = {
    "int",
    "float",
    "string",
    "boolean",
    "hash",
    "file",
    "record",
    "applet",
    "array:int",
    "array:float",
    "array:string",
    "array:boolean",
    "array:hash",
    "array:file",
    "array:record",
    "array:applet",
}
ACCESS_LEVELS = {"NONE", "VIEW", "UPLOAD", "CONTRIBUTE", "ADMINISTER"}
INTERPRETERS = {"bash", "python3"}
SUPPORTED_RELEASES = {"20.04", "24.04"}
RESTARTABLE_FAILURES = {
    "ExecutionError",
    "UnresponsiveWorker",
    "JMInternalError",
    "AppInternalError",
    "AppInsufficientResourceError",
    "JobTimeoutExceeded",
    "SpotInstanceInterruption",
    "*",
}
PLACEHOLDER_VALUES = {
    "",
    "changeme",
    "example",
    "placeholder",
    "redacted",
    "<secret>",
    "<token>",
}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


class Validator:
    def __init__(self, manifest: Any, kind: str) -> None:
        self.manifest = manifest
        self.requested_kind = kind
        self.issues: list[Issue] = []

    def add(
        self,
        severity: str,
        code: str,
        path: str,
        message: str,
    ) -> None:
        self.issues.append(Issue(severity, code, path, message))

    def error(self, code: str, path: str, message: str) -> None:
        self.add("error", code, path, message)

    def warning(self, code: str, path: str, message: str) -> None:
        self.add("warning", code, path, message)

    def validate(self) -> tuple[str, list[Issue]]:
        if not isinstance(self.manifest, dict):
            self.error(
                "root-type",
                "$",
                "the manifest root must be a JSON object",
            )
            return "unknown", self.issues

        kind = self.determine_kind()
        self.validate_metadata(kind)
        self.validate_specs(kind)
        self.validate_run_spec()
        self.validate_regional_options()
        self.validate_access()
        self.validate_https_app()
        self.scan_for_embedded_secrets(self.manifest)
        return kind, self.issues

    def determine_kind(self) -> str:
        if self.requested_kind != "auto":
            return self.requested_kind
        if "version" in self.manifest:
            return "app"
        return "applet"

    def validate_metadata(self, kind: str) -> None:
        name = self.manifest.get("name")
        if not isinstance(name, str) or not name:
            self.error("missing-name", "$.name", "name is required")
        elif not APP_NAME_RE.fullmatch(name):
            self.error(
                "invalid-name",
                "$.name",
                "name may contain only letters, digits, '.', '_', and '-'",
            )

        version = self.manifest.get("version")
        if kind == "app":
            if not isinstance(version, str):
                self.error(
                    "missing-version",
                    "$.version",
                    "a version string is required for apps",
                )
            elif not VERSION_RE.fullmatch(version):
                self.error(
                    "invalid-version",
                    "$.version",
                    "app version must follow semantic version syntax",
                )
        elif version is not None and not isinstance(version, str):
            self.error(
                "invalid-version",
                "$.version",
                "version must be a string when supplied",
            )

        if "resources" in self.manifest:
            self.warning(
                "deprecated-resources",
                "$.resources",
                "top-level resources is deprecated; move it under "
                "regionalOptions.<region>.resources",
            )

    def validate_specs(self, kind: str) -> None:
        for spec_name in ("inputSpec", "outputSpec"):
            value = self.manifest.get(spec_name)
            if value is None:
                if kind == "app":
                    self.error(
                        "missing-spec",
                        f"$.{spec_name}",
                        f"{spec_name} is required for apps (use [] if empty)",
                    )
                else:
                    self.warning(
                        "missing-spec",
                        f"$.{spec_name}",
                        f"{spec_name} is recommended for applets and required "
                        "for workflow compatibility",
                    )
                continue
            if not isinstance(value, list):
                self.error(
                    "spec-type",
                    f"$.{spec_name}",
                    f"{spec_name} must be a JSON array",
                )
                continue
            self.validate_parameter_list(spec_name, value)

    def validate_parameter_list(
        self,
        spec_name: str,
        parameters: list[Any],
    ) -> None:
        seen: set[str] = set()
        is_output = spec_name == "outputSpec"

        for index, parameter in enumerate(parameters):
            path = f"$.{spec_name}[{index}]"
            if not isinstance(parameter, dict):
                self.error(
                    "parameter-type",
                    path,
                    "parameter descriptor must be a JSON object",
                )
                continue

            name = parameter.get("name")
            if not isinstance(name, str) or not NAME_RE.fullmatch(name):
                self.error(
                    "parameter-name",
                    f"{path}.name",
                    "parameter name must match ^[A-Za-z_][A-Za-z0-9_]*$",
                )
            elif name in seen:
                self.error(
                    "duplicate-parameter",
                    f"{path}.name",
                    f"duplicate parameter name {name!r}",
                )
            else:
                seen.add(name)

            class_name = parameter.get("class")
            if class_name not in CLASSES:
                self.error(
                    "parameter-class",
                    f"{path}.class",
                    f"class must be one of: {', '.join(sorted(CLASSES))}",
                )

            if "optional" in parameter and not isinstance(parameter["optional"], bool):
                self.error(
                    "optional-type",
                    f"{path}.optional",
                    "optional must be a boolean",
                )

            if is_output:
                for unsupported in ("default", "suggestions", "choices"):
                    if unsupported in parameter:
                        self.error(
                            "output-only-field",
                            f"{path}.{unsupported}",
                            f"{unsupported} is not supported in outputSpec",
                        )

    def validate_run_spec(self) -> None:
        run_spec = self.manifest.get("runSpec")
        if not isinstance(run_spec, dict):
            self.error(
                "missing-runspec",
                "$.runSpec",
                "runSpec is required and must be a JSON object",
            )
            return

        has_file = isinstance(run_spec.get("file"), str) and bool(run_spec["file"])
        has_code = isinstance(run_spec.get("code"), str) and bool(run_spec["code"])
        if not has_file and not has_code:
            self.error(
                "missing-entry-source",
                "$.runSpec",
                "runSpec requires a non-empty file or code field",
            )
        elif has_file and has_code:
            self.warning(
                "multiple-entry-sources",
                "$.runSpec",
                "both file and code are supplied; keep one authoritative entry source",
            )

        interpreter = run_spec.get("interpreter")
        if interpreter not in INTERPRETERS:
            self.error(
                "interpreter",
                "$.runSpec.interpreter",
                f"interpreter must be one of: {', '.join(sorted(INTERPRETERS))}",
            )

        distribution = run_spec.get("distribution")
        if distribution != "Ubuntu":
            self.error(
                "distribution",
                "$.runSpec.distribution",
                'distribution must be "Ubuntu"',
            )

        release = run_spec.get("release")
        if release not in SUPPORTED_RELEASES:
            self.error(
                "release",
                "$.runSpec.release",
                "release must be 20.04 or 24.04",
            )
        elif release == "20.04":
            self.warning(
                "legacy-release",
                "$.runSpec.release",
                "Ubuntu 20.04 remains supported but 24.04 is preferred for new apps",
            )

        if run_spec.get("version") != "0":
            self.error(
                "aee-version",
                "$.runSpec.version",
                'current supported AEE version is the string "0"',
            )

        if "systemRequirements" in run_spec:
            self.warning(
                "deprecated-system-requirements",
                "$.runSpec.systemRequirements",
                "runSpec.systemRequirements is deprecated in dxapp.json; "
                "use regionalOptions.<region>.systemRequirements",
            )

        restartable = run_spec.get("restartableEntryPoints")
        if restartable is not None and restartable not in {"master", "all"}:
            self.error(
                "restartable-entry-points",
                "$.runSpec.restartableEntryPoints",
                'restartableEntryPoints must be "master" or "all"',
            )
        if restartable == "all":
            self.warning(
                "restart-idempotency",
                "$.runSpec.restartableEntryPoints",
                "all entry points must be idempotent before enabling all",
            )

        self.validate_exec_depends(run_spec.get("execDepends"))
        self.validate_execution_policy(run_spec.get("executionPolicy"))
        self.validate_timeout_policy(run_spec.get("timeoutPolicy"))

    def validate_exec_depends(self, dependencies: Any) -> None:
        if dependencies is None:
            return
        if not isinstance(dependencies, list):
            self.error(
                "exec-depends-type",
                "$.runSpec.execDepends",
                "execDepends must be a JSON array",
            )
            return

        for index, dependency in enumerate(dependencies):
            path = f"$.runSpec.execDepends[{index}]"
            if not isinstance(dependency, dict):
                self.error(
                    "dependency-type",
                    path,
                    "dependency must be a JSON object",
                )
                continue
            if not isinstance(dependency.get("name"), str):
                self.error(
                    "dependency-name",
                    f"{path}.name",
                    "dependency name is required",
                )
            if "version" not in dependency and "tag" not in dependency:
                self.warning(
                    "floating-dependency",
                    path,
                    "runtime dependency is not version/tag pinned; prefer a "
                    "pinned asset or bundled dependency for production",
                )

    def validate_execution_policy(self, policy: Any) -> None:
        if policy is None:
            return
        if not isinstance(policy, dict):
            self.error(
                "execution-policy-type",
                "$.runSpec.executionPolicy",
                "executionPolicy must be a JSON object",
            )
            return

        max_restarts = policy.get("maxRestarts")
        if max_restarts is not None and (
            not isinstance(max_restarts, int)
            or isinstance(max_restarts, bool)
            or not 0 <= max_restarts < 10
        ):
            self.error(
                "max-restarts",
                "$.runSpec.executionPolicy.maxRestarts",
                "maxRestarts must be a non-negative integer below 10",
            )

        restart_on = policy.get("restartOn")
        if restart_on is None:
            return
        if not isinstance(restart_on, dict):
            self.error(
                "restart-on-type",
                "$.runSpec.executionPolicy.restartOn",
                "restartOn must be a JSON object",
            )
            return

        for reason, count in restart_on.items():
            path = f"$.runSpec.executionPolicy.restartOn.{reason}"
            if reason not in RESTARTABLE_FAILURES:
                self.warning(
                    "unknown-restart-reason",
                    path,
                    "failure reason is not in the current documented restartable set",
                )
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                self.error(
                    "restart-count",
                    path,
                    "restart count must be a non-negative integer",
                )

    def validate_timeout_policy(self, policy: Any) -> None:
        if policy is None:
            return
        if not isinstance(policy, dict):
            self.error(
                "timeout-policy-type",
                "$.runSpec.timeoutPolicy",
                "timeoutPolicy must be a JSON object",
            )
            return

        for entry_point, duration in policy.items():
            path = f"$.runSpec.timeoutPolicy.{entry_point}"
            if not isinstance(duration, dict) or not duration:
                self.error(
                    "timeout-duration",
                    path,
                    "timeout must be a non-empty JSON object",
                )
                continue
            for unit, value in duration.items():
                if unit not in {"days", "hours", "minutes"}:
                    self.error(
                        "timeout-unit",
                        f"{path}.{unit}",
                        "timeout units are days, hours, or minutes",
                    )
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or value < 0
                ):
                    self.error(
                        "timeout-value",
                        f"{path}.{unit}",
                        "timeout value must be a non-negative number",
                    )

    def validate_regional_options(self) -> None:
        regional = self.manifest.get("regionalOptions")
        if regional is None:
            return
        if not isinstance(regional, dict) or not regional:
            self.error(
                "regional-options-type",
                "$.regionalOptions",
                "regionalOptions must be a non-empty JSON object",
            )
            return

        requirements_regions: set[str] = set()
        for region, options in regional.items():
            path = f"$.regionalOptions.{region}"
            if not isinstance(region, str) or ":" not in region:
                self.warning(
                    "region-name",
                    path,
                    "region should use a provider-qualified identifier such "
                    "as aws:us-east-1",
                )
            if not isinstance(options, dict):
                self.error(
                    "region-options-type",
                    path,
                    "region options must be a JSON object",
                )
                continue
            requirements = options.get("systemRequirements")
            if requirements is not None:
                requirements_regions.add(region)
                self.validate_system_requirements(
                    requirements,
                    f"{path}.systemRequirements",
                )

        if requirements_regions and len(requirements_regions) != len(regional):
            missing = sorted(set(regional) - requirements_regions)
            self.error(
                "inconsistent-regional-requirements",
                "$.regionalOptions",
                "systemRequirements is present for only some regions; missing "
                + ", ".join(missing),
            )

    def validate_system_requirements(
        self,
        requirements: Any,
        path: str,
    ) -> None:
        if not isinstance(requirements, dict) or not requirements:
            self.error(
                "system-requirements-type",
                path,
                "systemRequirements must be a non-empty JSON object",
            )
            return

        for entry_point, request in requirements.items():
            request_path = f"{path}.{entry_point}"
            if not isinstance(request, dict):
                self.error(
                    "resource-request-type",
                    request_path,
                    "entry-point resource request must be a JSON object",
                )
                continue
            selectors = [
                key
                for key in (
                    "instanceType",
                    "instanceTypeSelector",
                    "clusterSpec",
                )
                if key in request
            ]
            if len(selectors) > 1:
                self.error(
                    "resource-selector-conflict",
                    request_path,
                    "instanceType, instanceTypeSelector, and clusterSpec are "
                    "mutually exclusive",
                )

            selector = request.get("instanceTypeSelector")
            if selector is not None:
                self.validate_instance_selector(
                    selector,
                    f"{request_path}.instanceTypeSelector",
                )

    def validate_instance_selector(self, selector: Any, path: str) -> None:
        if not isinstance(selector, dict):
            self.error(
                "instance-selector-type",
                path,
                "instanceTypeSelector must be a JSON object",
            )
            return
        allowed = selector.get("allowedInstanceTypes")
        if (
            not isinstance(allowed, list)
            or not allowed
            or not all(isinstance(item, str) and item for item in allowed)
        ):
            self.error(
                "allowed-instance-types",
                f"{path}.allowedInstanceTypes",
                "allowedInstanceTypes must be a non-empty array of strings",
            )
            return
        if len(set(allowed)) != len(allowed):
            self.warning(
                "duplicate-instance-type",
                f"{path}.allowedInstanceTypes",
                "duplicate instance types do not provide an additional fallback",
            )

    def validate_access(self) -> None:
        access = self.manifest.get("access")
        if access is None:
            return
        if not isinstance(access, dict):
            self.error(
                "access-type",
                "$.access",
                "access must be a JSON object",
            )
            return

        network = access.get("network")
        if network is not None:
            if not isinstance(network, list) or not all(
                isinstance(host, str) for host in network
            ):
                self.error(
                    "network-type",
                    "$.access.network",
                    "network must be an array of host strings",
                )
            elif "*" in network:
                self.warning(
                    "broad-network",
                    "$.access.network",
                    "unrestricted network access needs explicit justification",
                )

        for field in ("project", "allProjects"):
            value = access.get(field)
            if value is not None and value not in ACCESS_LEVELS:
                self.error(
                    "access-level",
                    f"$.access.{field}",
                    f"{field} must be one of: " + ", ".join(sorted(ACCESS_LEVELS)),
                )

        if access.get("project") == "ADMINISTER":
            self.warning(
                "admin-project-access",
                "$.access.project",
                "ADMINISTER access is rarely needed by an analysis app",
            )
        if access.get("allProjects") not in {None, "NONE"}:
            self.warning(
                "all-projects-access",
                "$.access.allProjects",
                "cross-project access needs explicit justification",
            )
        if access.get("developer") is True:
            self.warning(
                "developer-access",
                "$.access.developer",
                "developer access allows advanced app operations",
            )

    def validate_https_app(self) -> None:
        https_app = self.manifest.get("httpsApp")
        if https_app is None:
            return
        if not isinstance(https_app, dict):
            self.error(
                "https-app-type",
                "$.httpsApp",
                "httpsApp must be a JSON object",
            )
            return
        ports = https_app.get("ports")
        if (
            not isinstance(ports, list)
            or not ports
            or not all(port in {443, 8080, 8081} for port in ports)
        ):
            self.error(
                "https-ports",
                "$.httpsApp.ports",
                "HTTPS app ports must be a non-empty subset of 443, 8080, and 8081",
            )

    def scan_for_embedded_secrets(
        self,
        value: Any,
        path: str = "$",
    ) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if SECRET_KEY_RE.search(str(key)) and self.looks_embedded(child):
                    self.warning(
                        "embedded-secret",
                        child_path,
                        "possible credential value is embedded in dxapp.json; "
                        "use an explicit protected input or secret mechanism",
                    )
                self.scan_for_embedded_secrets(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.scan_for_embedded_secrets(child, f"{path}[{index}]")

    @staticmethod
    def looks_embedded(value: Any) -> bool:
        if value is None or isinstance(value, bool):
            return False
        if isinstance(value, str):
            return value.strip().lower() not in PLACEHOLDER_VALUES
        return isinstance(value, (int, float, dict, list))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("manifest", type=Path, help="path to dxapp.json")
    parser.add_argument(
        "--kind",
        choices=("auto", "app", "applet"),
        default="auto",
        help="validation profile; auto treats manifests with version as apps",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero for warnings as well as errors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON",
    )
    return parser


def load_manifest(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize(issues: Iterable[Issue]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0}
    for issue in issues:
        counts[issue.severity] += 1
    return counts


def print_text(
    path: Path,
    kind: str,
    issues: list[Issue],
) -> None:
    counts = summarize(issues)
    print(f"Manifest: {path}")
    print(f"Kind: {kind}")
    print(f"Errors: {counts['error']}")
    print(f"Warnings: {counts['warning']}")
    for issue in issues:
        print(f"{issue.severity.upper()}: {issue.path}: [{issue.code}] {issue.message}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = args.manifest.expanduser()

    try:
        manifest = load_manifest(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        if args.json:
            print(
                json.dumps(
                    {
                        "manifest": str(path),
                        "kind": "unknown",
                        "valid": False,
                        "errors": 1,
                        "warnings": 0,
                        "issues": [
                            {
                                "severity": "error",
                                "code": "parse",
                                "path": "$",
                                "message": str(error),
                            }
                        ],
                    },
                    indent=2,
                )
            )
        else:
            print(f"validate_dxapp: {error}", file=sys.stderr)
        return 2

    validator = Validator(manifest, args.kind)
    kind, issues = validator.validate()
    counts = summarize(issues)
    valid = counts["error"] == 0 and (not args.strict or counts["warning"] == 0)

    if args.json:
        print(
            json.dumps(
                {
                    "manifest": str(path),
                    "kind": kind,
                    "valid": valid,
                    "errors": counts["error"],
                    "warnings": counts["warning"],
                    "issues": [asdict(issue) for issue in issues],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print_text(path, kind, issues)

    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
