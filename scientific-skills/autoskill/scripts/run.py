import datetime as _dt
from pathlib import Path

import httpx

from cluster import cluster_sessions, segment_sessions
from fetch_window import fetch_window
from match_skills import load_skill_descriptions, top_k_matches
from redact import redact
from synthesize import synthesize


class ScreenpipeUnreachable(RuntimeError):
    """Raised when the screenpipe daemon cannot be reached.

    The autoskill skill cannot run without screenpipe. Install it from
    https://github.com/screenpipe/screenpipe and start the daemon before
    invoking this skill.
    """


def _default_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


def _cluster_query(cluster: dict) -> str:
    parts = ["apps: " + ", ".join(cluster["apps"])]
    if cluster.get("example_titles"):
        parts.append("titles: " + "; ".join(cluster["example_titles"]))
    return " | ".join(parts)


def _write_plan(proposed_path: Path, clusters: list[dict]) -> None:
    lines = ["# Dry-run plan", ""]
    for i, c in enumerate(clusters, 1):
        lines += [
            f"## Cluster {i}",
            f"- apps: {', '.join(c['apps'])}",
            f"- sessions: {c['session_count']}",
            f"- total_duration_seconds: {c['total_duration_seconds']}",
            f"- example titles: {'; '.join(c.get('example_titles', []))}",
            "",
        ]
    (proposed_path / "plan.md").write_text("\n".join(lines))


def _write_report(proposed_path: Path, results: list[dict]) -> None:
    lines = ["# autoskill report", ""]
    if not results:
        lines.append("No clusters met the minimum size threshold. Nothing to propose.")
    for r in results:
        c = r["cluster"]
        lines += [
            f"## {', '.join(c['apps'])} — {c['session_count']}× ({c['total_duration_seconds']}s)",
            f"- verdict: **{r['verdict']}**",
        ]
        if r["verdict"] == "reuse":
            lines.append(f"- matched skill: `{r['target']}`")
        else:
            lines.append(f"- draft: `{r['draft_path']}`")
        lines.append("- top matches:")
        for s in r["top_k"]:
            lines.append(f"  - `{s['name']}` (score={s['score']:.2f})")
        lines.append("")
    (proposed_path / "report.md").write_text("\n".join(lines))


def run(config, *, start_time, end_time, out_dir,
        screenpipe_client, backend, embedder, skills_dir,
        screenpipe_token=None, now=None, dry_run=False):
    now = now or _default_now
    try:
        events = fetch_window(screenpipe_client, start_time, end_time,
                              token=screenpipe_token)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        base = getattr(screenpipe_client, "base_url", "http://localhost:3030")
        raise ScreenpipeUnreachable(
            f"cannot reach screenpipe at {base}: {e}. "
            "Install and start the daemon — see "
            "https://github.com/screenpipe/screenpipe — "
            "or point config.yaml's screenpipe.url at your instance."
        ) from e

    for e in events:
        e["text"] = redact(e.get("text", ""))
        e["window_title"] = redact(e.get("window_title", ""))

    cluster_cfg = config.get("cluster", {})
    idle_gap = cluster_cfg.get("idle_gap_minutes", 10) * 60
    min_session = cluster_cfg.get("min_session_minutes", 5) * 60
    min_cluster = cluster_cfg.get("min_cluster_size", 2)

    # fetch_window returns ts as ISO strings; convert to epoch for segmentation
    for e in events:
        if isinstance(e["ts"], str):
            e["ts"] = int(_dt.datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).timestamp())

    sessions = segment_sessions(events, idle_gap_seconds=idle_gap, min_session_seconds=min_session)
    clusters = cluster_sessions(sessions, min_cluster_size=min_cluster)

    proposed_path = Path(out_dir) / now()
    proposed_path.mkdir(parents=True, exist_ok=True)

    if dry_run:
        _write_plan(proposed_path, clusters)
        return proposed_path

    if not clusters:
        _write_report(proposed_path, [])
        return proposed_path

    skills = load_skill_descriptions(Path(skills_dir))
    results = []
    for cluster in clusters:
        query = _cluster_query(cluster)
        top_k = top_k_matches(query, skills, embedder=embedder, k=5)
        decision = synthesize(cluster, top_k, backend=backend)

        entry = {"cluster": cluster, "top_k": top_k, "verdict": decision["verdict"]}
        if decision["verdict"] == "reuse":
            entry["target"] = decision.get("target")
        else:
            kind = "new-skills" if decision["verdict"] == "novel" else "composition-recipes"
            name = decision["name"]
            draft_dir = proposed_path / kind / name
            draft_dir.mkdir(parents=True)
            (draft_dir / "SKILL.md").write_text(decision["skill_body"])
            entry["draft_path"] = str(draft_dir.relative_to(proposed_path))
        results.append(entry)

    _write_report(proposed_path, results)
    return proposed_path


def main(argv=None):
    import argparse
    import sys

    import httpx
    import yaml

    from backends import make_backend

    parser = argparse.ArgumentParser(prog="autoskill")
    parser.add_argument("--start", required=True, help="ISO start time, e.g. 2026-04-17T00:00:00Z")
    parser.add_argument("--end", required=True, help="ISO end time")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--out", default=None,
                        help="output directory for proposals (default: ~/.autoskill/proposed)")
    parser.add_argument("--skills-dir", default=None,
                        help="path to scientific-skills/ (default: parent of this skill's dir)")
    parser.add_argument("--dry-run", action="store_true",
                        help="stop after clustering; do not call the LLM backend")
    args = parser.parse_args(argv)

    config = yaml.safe_load(Path(args.config).read_text())

    here = Path(__file__).resolve()
    skills_dir = Path(args.skills_dir) if args.skills_dir else here.parent.parent.parent
    out_dir = Path(args.out) if args.out else Path.home() / ".autoskill" / "proposed"

    import os
    screenpipe_cfg = config.get("screenpipe", {})
    screenpipe_url = screenpipe_cfg.get("url", "http://localhost:3030")
    screenpipe_token = (screenpipe_cfg.get("token")
                        or os.environ.get("SCREENPIPE_TOKEN"))
    screenpipe_client = httpx.Client(base_url=screenpipe_url, timeout=60.0)

    if args.dry_run:
        backend = None
        embedder = None
    else:
        backend = make_backend(config)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(
            config.get("embeddings", {}).get("model", "sentence-transformers/all-MiniLM-L6-v2")
        )

        def embedder(text: str):
            return list(map(float, model.encode(text)))

    proposed = run(
        config,
        start_time=args.start, end_time=args.end, out_dir=out_dir,
        screenpipe_client=screenpipe_client, backend=backend, embedder=embedder,
        skills_dir=skills_dir, screenpipe_token=screenpipe_token,
        dry_run=args.dry_run,
    )
    print(f"proposals written to: {proposed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
