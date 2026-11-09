#!/usr/bin/env python3
"""Check evidence bookkeeping. Does not fetch sources or grade scientific truth."""
import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


def check(data):
    errors, cautions = [], []

    def require(ok, message):
        if not ok:
            errors.append(message)

    def fields(obj, names, where):
        if not isinstance(obj, dict):
            errors.append(f"{where}: expected object")
            return False
        for name in names:
            require(isinstance(obj.get(name), str) and bool(obj[name].strip()),
                    f"{where}.{name}: expected nonempty string")
        return True

    def choice(obj, key, allowed, where):
        require(isinstance(obj.get(key), str) and obj[key] in allowed,
                f"{where}.{key}: expected one of {', '.join(sorted(allowed))}")

    def iso(value, where):
        try:
            require(isinstance(value, str) and date.fromisoformat(value).isoformat() == value,
                    f"{where}: expected ISO date")
        except (ValueError, TypeError):
            errors.append(f"{where}: expected ISO date")

    if not isinstance(data, dict):
        return ["root: expected object"], []
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1,
            "schema_version: expected 1")
    context = data.get("context")
    if fields(context, ["question", "decision", "target_setting", "bounds", "stop_reason"], "context"):
        choice(context, "mode", {"scout", "map", "update"}, "context")
        iso(context.get("as_of"), "context.as_of")

    collections = {}
    for name in ["papers", "claims", "propositions", "edges", "tensions", "reading_queue", "searches"]:
        value = data.get(name)
        require(isinstance(value, list), f"{name}: expected list")
        collections[name] = value if isinstance(value, list) else []

    indexes = {}
    for name in ["papers", "claims", "propositions", "edges", "tensions"]:
        index = {}
        for i, obj in enumerate(collections[name]):
            if not fields(obj, ["id"], f"{name}[{i}]"):
                continue
            ident = obj.get("id")
            if isinstance(ident, str) and ident.strip():
                require(ident not in index, f"{name}: duplicate ID {ident}")
                index[ident] = obj
        indexes[name] = index
    papers, claims = indexes["papers"], indexes["claims"]

    def refs(value, index, where, minimum=0):
        require(isinstance(value, list), f"{where}: expected list")
        if not isinstance(value, list):
            return []
        require(len(value) >= minimum, f"{where}: requires at least {minimum} entries")
        good = []
        for ident in value:
            if not isinstance(ident, str) or ident not in index:
                errors.append(f"{where}: unknown reference {ident!r}")
            else:
                good.append(ident)
        require(len(set(good)) == len(good), f"{where}: duplicate references")
        return good

    def inspected(cid):
        pid = claims.get(cid, {}).get("paper_id")
        return isinstance(pid, str) and papers.get(pid, {}).get("access") in {"fulltext", "excerpt"}

    def family(cid):
        claim = claims.get(cid, {})
        pid = claim.get("paper_id")
        paper = papers.get(pid, {}) if isinstance(pid, str) else {}
        return claim.get("evidence_family", paper.get("evidence_family", "unknown"))

    for pid, obj in papers.items():
        fields(obj, ["title", "url", "version", "evidence_family"], pid)
        choice(obj, "access", {"fulltext", "excerpt", "abstract", "metadata", "unavailable"}, pid)
        url = obj.get("url", "")
        if isinstance(url, str):
            parsed = urlparse(url)
            require((parsed.scheme in {"https", "http"} and bool(parsed.netloc)) or
                    (parsed.scheme == "local" and bool(parsed.path)), f"{pid}.url: expected source URL/local URI")
        if obj.get("evidence_family") == "unknown":
            cautions.append(f"{pid}: evidence independence not established")

    for cid, obj in claims.items():
        fields(obj, ["paper_id", "statement", "scope"], cid)
        if "evidence_family" in obj:
            fields(obj, ["evidence_family"], cid)
        pid = obj.get("paper_id")
        require(isinstance(pid, str) and pid in papers, f"{cid}: unknown paper_id")
        choice(obj, "kind", {"empirical", "theoretical", "interpretive"}, cid)
        fields(obj.get("evidence"), ["locator", "observation", "authors_interpretation", "analyst_inference"], f"{cid}.evidence")
        assessment = obj.get("assessment")
        if fields(assessment, ["reason", "limitation"], f"{cid}.assessment"):
            choice(assessment, "strength", {"supported", "provisional", "unsupported"}, f"{cid}.assessment")
            if assessment.get("strength") == "supported":
                require(inspected(cid), f"{cid}: supported claim requires inspected primary text/excerpt")
        uses = obj.get("uses")
        require(isinstance(uses, list) and bool(uses), f"{cid}.uses: requires a decision link")
        for use in uses if isinstance(uses, list) else []:
            if fields(use, ["decision", "transfer_assumption"], f"{cid}.uses"):
                choice(use, "role", {"fact", "mechanism", "method", "evaluation", "boundary", "counterevidence", "analogy"}, f"{cid}.uses")

    conflict_pairs = []
    for tid, obj in indexes["tensions"].items():
        ids = refs(obj.get("claim_ids"), claims, f"{tid}.claim_ids", 2)
        fields(obj, ["comparison", "explanation", "resolution_search"], tid)
        choice(obj, "classification", {"comparable_conflict", "scope_mismatch", "inconclusive", "not_opposed"}, tid)
        if "frontier_candidate" in obj:
            require(type(obj["frontier_candidate"]) is bool, f"{tid}.frontier_candidate: expected boolean")
        if obj.get("classification") == "comparable_conflict":
            require(all(inspected(cid) for cid in ids), f"{tid}: conflict requires inspected primary evidence")
            conflict_pairs.append(set(ids))
        if obj.get("classification") == "comparable_conflict" or obj.get("frontier_candidate") is True:
            alternatives = obj.get("alternatives")
            require(isinstance(alternatives, list) and len(alternatives) >= 2 and
                    all(isinstance(x, str) and x.strip() for x in alternatives), f"{tid}: requires competing explanations")
            fields(obj.get("test"), ["variable", "controls", "predictions", "gap_killer"], f"{tid}.test")

    for eid, obj in indexes["edges"].items():
        ids = refs([obj.get("source"), obj.get("target")], claims, eid, 2)
        evidence = refs(obj.get("evidence_claims"), claims, f"{eid}.evidence_claims", 1)
        fields(obj, ["rationale"], eid)
        choice(obj, "relation", {"supports", "contradicts", "bounds", "depends_on", "imports", "supersedes"}, eid)
        choice(obj, "status", {"source_supported", "hypothesis"}, eid)
        choice(obj, "independence", {"independent", "shared", "unknown"}, eid)
        if obj.get("status") == "source_supported":
            require(all(inspected(cid) for cid in evidence), f"{eid}: source-supported edge requires inspected evidence")
            if obj.get("relation") == "contradicts":
                require(any(set(ids) <= pair for pair in conflict_pairs), f"{eid}: contradiction lacks comparable-conflict card")
        if obj.get("independence") == "independent" and len(ids) == 2:
            families = [family(cid) for cid in ids]
            require(all(isinstance(x, str) and x != "unknown" for x in families), f"{eid}: independence is unestablished")
            require(families[0] != families[1], f"{eid}: shared evidence family cannot be independent")

    for qid, obj in indexes["propositions"].items():
        fields(obj, ["statement", "scope", "independence_assessment", "coverage", "justification"], qid)
        choice(obj, "synthesis", {"convergent", "conditional", "contested", "insufficient"}, qid)
        groups = {}
        for key in ["supporting_claim_ids", "counter_claim_ids", "candidate_claim_ids"]:
            groups[key] = refs(obj.get(key), claims, f"{qid}.{key}")
        support = groups["supporting_claim_ids"]
        counter = groups["counter_claim_ids"]
        require(not set(support) & set(counter), f"{qid}: same claim cannot both support and counter")
        for cid in support + counter:
            assessment = claims[cid].get("assessment")
            strength = assessment.get("strength") if isinstance(assessment, dict) else None
            require(inspected(cid) and strength == "supported", f"{qid}: confirmed evidence must be supported; use candidate_claim_ids for leads")
        count = obj.get("independent_evidence_count")
        require("independent_evidence_count" in obj and (count is None or type(count) is int and count >= 0),
                f"{qid}: independent_evidence_count must be nonnegative integer or null")
        if type(count) is int:
            known_families = {family(cid) for cid in support if isinstance(family(cid), str) and family(cid) != "unknown"}
            require(count <= len(known_families), f"{qid}: independent count exceeds known supporting evidence families")
        if obj.get("synthesis") == "convergent":
            known_families = {family(cid) for cid in support if isinstance(family(cid), str) and family(cid) != "unknown"}
            require(len(known_families) >= 2, f"{qid}: convergence needs multiple known evidence contributions, not repeated reports")
    if claims and not indexes["propositions"]:
        cautions.append("No proposition synthesis; support convergence has not been assessed")

    seen = set()
    for i, obj in enumerate(collections["reading_queue"]):
        where = f"reading_queue[{i}]"
        if fields(obj, ["paper_id", "focus", "reason"], where):
            pid = obj.get("paper_id")
            if isinstance(pid, str):
                require(pid in papers, f"{where}: unknown paper_id")
                require(pid not in seen, f"{where}: duplicate paper in queue")
                seen.add(pid)
            choice(obj, "action", {"deep_read", "targeted_read", "verify_access", "defer", "exclude"}, where)
    for i, obj in enumerate(collections["searches"]):
        where = f"searches[{i}]"
        if fields(obj, ["channel", "query", "source", "outcome"], where):
            iso(obj.get("date"), f"{where}.date")
            refs(obj.get("kept_ids"), papers, f"{where}.kept_ids")
    if not collections["searches"]:
        cautions.append("No search/corpus-review log; coverage cannot be assessed")
    if not papers:
        cautions.append("No papers found; this is an empty map")
    return errors, cautions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 2
    errors, cautions = check(data)
    for message in errors:
        print(f"[FAIL] {message}")
    for message in cautions:
        print(f"[WARN] {message}")
    print(f"[{'FAIL' if errors else 'OK'}] {len(errors)} error(s), {len(cautions)} caution(s). Structure only; source truth not verified.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
