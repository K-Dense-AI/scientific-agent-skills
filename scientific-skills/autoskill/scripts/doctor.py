import argparse
import os
import sys
from pathlib import Path

import httpx

_VALID_BACKENDS = {"local", "claude", "foundry"}


def default_screenpipe_probe(config):
    sp = config.get("screenpipe", {})
    url = sp.get("url", "http://localhost:3030")
    token = sp.get("token") or os.environ.get("SCREENPIPE_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = httpx.get(f"{url}/health", headers=headers, timeout=5.0)
        if r.status_code == 200:
            return ("ok", url)
        return ("error", f"{url} returned HTTP {r.status_code}")
    except httpx.HTTPError as e:
        return ("error", f"{url}: {e}")


def default_llm_probe(config):
    kind = config.get("backend")
    if kind == "local":
        endpoint = config.get("local", {}).get("endpoint", "http://localhost:1234/v1")
        try:
            r = httpx.get(f"{endpoint}/models", timeout=5.0)
            if r.status_code == 200:
                return ("ok", endpoint)
            return ("error", f"{endpoint} returned HTTP {r.status_code}")
        except httpx.HTTPError as e:
            return ("error", f"{endpoint}: {e}")
    if kind == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return ("error", "ANTHROPIC_API_KEY not set")
        return ("ok", "ANTHROPIC_API_KEY present (not probed)")
    if kind == "foundry":
        if not os.environ.get("FOUNDRY_API_KEY"):
            return ("error", "FOUNDRY_API_KEY not set")
        return ("ok", "FOUNDRY_API_KEY present (not probed)")
    return ("error", f"unknown backend: {kind!r}")


def check(config, *, skills_dir, screenpipe_probe, llm_probe):
    result = {}

    kind = config.get("backend")
    if kind in _VALID_BACKENDS:
        result["config"] = ("ok", f"backend={kind}")
    else:
        result["config"] = ("error", f"unknown backend: {kind!r}")

    skills_dir = Path(skills_dir)
    if skills_dir.is_dir():
        result["skills_dir"] = ("ok", str(skills_dir))
    else:
        result["skills_dir"] = ("error", f"not a directory: {skills_dir}")

    result["screenpipe"] = screenpipe_probe(config)
    result["llm"] = llm_probe(config)
    return result


def _format_report(result: dict) -> str:
    lines = ["autoskill doctor", "================"]
    for key in ("config", "skills_dir", "screenpipe", "llm"):
        status, detail = result[key]
        lines.append(f"  {key:12s}: {status:5s}  {detail}")
    return "\n".join(lines)


def main(argv=None):
    import yaml

    parser = argparse.ArgumentParser(
        prog="autoskill-doctor",
        description="Check that screenpipe, LM Studio, config, and skills dir are ready.",
    )
    parser.add_argument("--config", required=True,
                        help="path to autoskill config.yaml")
    parser.add_argument("--skills-dir", required=True,
                        help="path to scientific-skills/")
    args = parser.parse_args(argv)

    config = yaml.safe_load(Path(args.config).read_text())
    result = check(
        config,
        skills_dir=args.skills_dir,
        screenpipe_probe=default_screenpipe_probe,
        llm_probe=default_llm_probe,
    )

    report = _format_report(result)
    print(report)

    any_error = any(status == "error" for status, _ in result.values())
    if any_error:
        print("\ndoctor: one or more checks failed", file=sys.stderr)
        return 1
    print("\ndoctor: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
