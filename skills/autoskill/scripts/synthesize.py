import json
import re

VALID_VERDICTS = {"reuse", "compose", "novel"}


class SynthesisError(Exception):
    pass


def _build_prompt(cluster, top_k_skills):
    apps = ", ".join(cluster["apps"])
    titles = "; ".join(cluster.get("example_titles", []))
    candidates = "\n".join(
        f"- {s['name']} (score={s['score']:.2f}): {s['description']}"
        for s in top_k_skills
    )
    return f"""You are classifying an observed user workflow against an existing skill library.

Cluster:
- apps: {apps}
- sessions: {cluster['session_count']}
- total_duration_seconds: {cluster['total_duration_seconds']}
- example titles: {titles}

Candidate existing skills (ranked by semantic similarity):
{candidates}

Decide one of:
- "reuse": an existing skill already covers this workflow.
- "compose": no single skill covers it, but chaining existing skills does. Draft a thin SKILL.md that invokes them in order.
- "novel": not covered; draft a full new SKILL.md.

Respond with a single JSON object:
- reuse: {{"verdict": "reuse", "target": "<skill-name>"}}
- compose: {{"verdict": "compose", "name": "<new-skill-name>", "skill_body": "<SKILL.md body>"}}
- novel: {{"verdict": "novel", "name": "<new-skill-name>", "skill_body": "<SKILL.md body>"}}
"""


def _extract_json(text: str) -> dict:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise SynthesisError(f"no JSON object found in response: {text!r}")
        candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise SynthesisError(f"invalid JSON in response: {e}") from e


def synthesize(cluster, top_k_skills, backend):
    prompt = _build_prompt(cluster, top_k_skills)
    response = backend(prompt)
    payload = _extract_json(response)

    verdict = payload.get("verdict")
    if verdict not in VALID_VERDICTS:
        raise SynthesisError(f"unknown verdict: {verdict!r}")

    result = {"verdict": verdict, "skill_body": None}
    if verdict == "reuse":
        result["target"] = payload.get("target")
    else:
        result["name"] = payload.get("name")
        result["skill_body"] = payload.get("skill_body")
    return result
