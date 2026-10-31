#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Minimal LAPIS client plus the pure helpers the four CLIs share.

Standard library only. Network access to the GenSpectrum family of LAPIS
instances (cov-spectrum.org, genspectrum.org, pathoplexus.org) is required for
the request functions; every helper below the ``--- pure helpers ---`` mark is
offline and independently testable.

The registry and live contracts were reviewed on 2026-10-01. Field names and
lineage indexes are per-instance. Numeric/date fields support ranges, but date
analyses require date-typed columns. Actual response versions are checked before
combining counts. See references/lapis-api.md for deployment-specific behavior.
"""
from __future__ import annotations

import json
import hashlib
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any, Iterable, Sequence

# Instances verified reachable on 2026-10-01. The registry is a convenience,
# not an authority: any LAPIS deployment works via --base-url, and every script
# introspects the schema at runtime rather than trusting this table.
INSTANCES: dict[str, str] = {
    "sars-cov-2": "https://lapis.cov-spectrum.org/open/v2",
    "influenza-a": "https://lapis.genspectrum.org/influenza-a",
    "h1n1pdm": "https://lapis.genspectrum.org/h1n1pdm",
    "h3n2": "https://lapis.genspectrum.org/h3n2",
    "h5n1": "https://lapis.genspectrum.org/h5n1",
    "rsv-a": "https://lapis.pathoplexus.org/rsv-a",
    "rsv-b": "https://lapis.pathoplexus.org/rsv-b",
    "hmpv": "https://lapis.pathoplexus.org/hmpv",
    "measles": "https://lapis.pathoplexus.org/measles",
    "mpox": "https://lapis.pathoplexus.org/mpox",
    "west-nile": "https://lapis.pathoplexus.org/west-nile",
    "dengue": "https://lapis.pathoplexus.org/dengue",
    "ebola-zaire": "https://lapis.pathoplexus.org/ebola-zaire",
    "ebola-sudan": "https://lapis.pathoplexus.org/ebola-sudan",
    "cchf": "https://lapis.pathoplexus.org/cchf",
}

# pango-designation is the authority for SARS-CoV-2 lineage names. Fetched at
# run time, never cached in this repository: withdrawals and redesignations
# land continuously and a stale copy is worse than no copy.
PANGO_ALIAS_URL = (
    "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/"
    "pango_designation/alias_key.json"
)
PANGO_NOTES_URL = (
    "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/"
    "lineage_notes.txt"
)

USER_AGENT = "scientific-agent-skills-pathogen-variant-surveillance/1.3"
TIMEOUT = 60
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 502, 503, 504}

# Collection- and submission-date fields, in the order they should be preferred
# when an instance declares more than one. Anything not listed is still found by
# the substring fallback in pick_date_field().
COLLECTION_DATE_FIELDS = (
    "date",
    "sampleCollectionDateRangeLower",
    "sampleCollectionDate",
    "collectionDate",
    "dateCollected",
)
SUBMISSION_DATE_FIELDS = (
    "dateSubmitted",
    "earliestReleaseDate",
    "ncbiReleaseDate",
    "releasedDate",
    "submittedDate",
    "dateReleased",
)
# Lineage-like columns for instances that declare no lineage index at all.
LINEAGE_FIELDS = (
    "pangoLineage",
    "nextcladePangoLineage",
    "lineage",
    "clade",
    "nextstrainClade",
    "subtype",
    "genotype",
    "serotype",
)
RANGE_TYPES = {"date", "int", "float"}

# Two-sided 95% normal quantile, shared by the interval and the slope CI.
Z_95 = 1.959964


class LapisError(RuntimeError):
    """A LAPIS request failed in a way the caller cannot paper over."""


class SnapshotChanged(LapisError):
    """Responses used in one analysis came from different database versions."""


_DATA_VERSIONS: dict[str, str] = {}


def record_version(base_url: str, payload: Any, headers: Any, path: str) -> None:
    """Compare actual response versions; /sample/info alone cannot pin a query."""
    version = headers.get("lapis-data-version")
    if isinstance(payload, dict):
        info = payload.get("info") or {}
        version = version or info.get("dataVersion") or payload.get("dataVersion")
    if version is None:
        if path in {"sample/aggregated", "sample/aminoAcidMutations", "sample/nucleotideMutations"}:
            raise LapisError("data response has no dataVersion; cannot verify snapshot consistency")
        return
    version = str(version)
    previous = _DATA_VERSIONS.setdefault(base_url, version)
    if version != previous:
        raise SnapshotChanged(f"database changed from {previous} to {version}; rerun the entire analysis")


# --- network ----------------------------------------------------------------


def _encode(params: dict[str, Any]) -> str:
    """Encode query parameters, repeating keys for list values."""
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            pairs.extend((key, str(item)) for item in value if item is not None)
        else:
            pairs.append((key, str(value)))
    return urllib.parse.urlencode(pairs)


def _error_detail(body: bytes) -> str:
    """Pull the human-readable reason out of a LAPIS error body.

    Two envelopes are in use: ``{"error": {...}, "info": {...}}`` and a bare
    RFC 7807 ``{"type": ..., "detail": ...}``. Both carry ``detail``, and on a
    bad filter key that string enumerates every key the instance accepts.
    """
    try:
        payload = json.loads(body.decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return sanitize(body.decode("utf-8", "replace"), limit=400) if body else ""
    if isinstance(payload, dict):
        inner = payload.get("error") if isinstance(payload.get("error"), dict) else payload
        detail = inner.get("detail") or inner.get("title")
        if detail:
            return sanitize(detail, limit=1200)
    return sanitize(json.dumps(payload), limit=1200)


def request(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    """GET a JSON document from a LAPIS instance, retrying transient failures."""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    if params:
        query = _encode(params)
        if query:
            url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    last: str = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                payload = json.load(response)
                record_version(base_url, payload, response.headers, path)
                return payload
        except urllib.error.HTTPError as exc:
            detail = _error_detail(exc.read())
            last = f"HTTP {exc.code}: {detail}"
            if exc.code not in RETRY_STATUS:
                raise LapisError(f"{url}\n  {last}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = str(exc)
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(1.5 * (attempt + 1))
    raise LapisError(f"request failed after {MAX_ATTEMPTS} attempts: {url}\n  {last}")


def resolve_base_url(instance: str | None, base_url: str | None) -> str:
    """Turn ``--instance`` / ``--base-url`` into a URL, or explain the options."""
    # Each CLI invocation starts a fresh consistency check, even in one interpreter.
    _DATA_VERSIONS.clear()
    if base_url:
        return base_url.rstrip("/")
    if not instance:
        raise LapisError("give --instance NAME or --base-url URL")
    try:
        return INSTANCES[instance]
    except KeyError:
        known = ", ".join(sorted(INSTANCES))
        raise LapisError(
            f"unknown instance {instance!r}. Known: {known}. "
            "Any other LAPIS deployment works via --base-url."
        ) from None


_SCHEMA_CACHE: dict[str, dict] = {}


def describe_instance(base_url: str) -> dict:
    """Fetch and cache ``/sample/databaseConfig`` for an instance.

    Returns ``{"name", "openness", "primary_key", "types", "lineage_indexed",
    "features"}`` where ``types`` maps every declared metadata field to its
    declared type. Everything downstream chooses field names from this rather
    than assuming the SARS-CoV-2 vocabulary.
    """
    if base_url in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[base_url]
    schema = request(base_url, "sample/databaseConfig").get("schema", {})
    metadata = schema.get("metadata", [])
    described = {
        "name": schema.get("instanceName", ""),
        "openness": schema.get("opennessLevel", ""),
        "primary_key": schema.get("primaryKey", ""),
        "types": {m["name"]: m.get("type", "string") for m in metadata},
        "lineage_indexed": [m["name"] for m in metadata if m.get("generateLineageIndex")],
        "features": [f.get("name") for f in schema.get("features", [])],
    }
    _SCHEMA_CACHE[base_url] = described
    return described


def data_version(base_url: str) -> str:
    """The instance's current data version, for stamping any result you keep."""
    if base_url in _DATA_VERSIONS:
        return _DATA_VERSIONS[base_url]
    return str(request(base_url, "sample/info").get("dataVersion", ""))


def surveillance_filters(schema: dict, filters: dict) -> dict:
    """Avoid counting multiple versions or revoked records when those fields exist."""
    defaults = {}
    if "versionStatus" in schema["types"]:
        defaults["versionStatus"] = "LATEST_VERSION"
    if "isRevocation" in schema["types"]:
        defaults["isRevocation"] = "false"
    if "dataUseTerms" in schema["types"]:
        defaults["dataUseTerms"] = "OPEN"
    return {**defaults, **filters}


def aggregated(
    base_url: str, filters: dict[str, Any], fields: Sequence[str] = ()
) -> list[dict]:
    """Grouped counts. ``fields`` is the group-by, not a projection.

    These helpers retrieve every group and sort client-side for compatibility.
    Modern deployments also support ordered limit/offset queries.
    """
    params = dict(filters)
    if fields:
        params["fields"] = ",".join(fields)
    return request(base_url, "sample/aggregated", params).get("data", [])


def count(base_url: str, filters: dict[str, Any]) -> int:
    """Total sequences matching a filter."""
    rows = aggregated(base_url, filters)
    return int(rows[0]["count"]) if rows else 0


def mutations(
    base_url: str,
    filters: dict[str, Any],
    *,
    amino_acid: bool = True,
    min_proportion: float = 0.05,
) -> list[dict]:
    """Mutations carried by the matching sequences, with per-site proportions.

    Rows carry ``mutation``, ``count``, ``coverage``, ``proportion``,
    ``sequenceName`` (the gene or segment), ``position``, ``mutationFrom`` and
    ``mutationTo``. ``proportion`` is over ``coverage`` — sequences that
    actually resolved that site — not over every matching sequence.
    """
    endpoint = "sample/aminoAcidMutations" if amino_acid else "sample/nucleotideMutations"
    params = dict(filters)
    params["minProportion"] = min_proportion
    return request(base_url, endpoint, params).get("data", [])


def lineage_definition(base_url: str, column: str) -> dict:
    """The instance's live lineage tree for a column: parents and aliases.

    Only served for columns carrying a lineage index; a 400 means the column
    has none, and there is no ancestry to query.
    """
    return request(base_url, f"sample/lineageDefinition/{column}")


# SHA-256 digests of the fetched bytes, keyed by URL. HTTP ETags are opaque
# validators, not Git object IDs; retaining the files is required for replay.
PANGO_BLOBS: dict[str, str] = {}


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            content = response.read()
            PANGO_BLOBS[url] = hashlib.sha256(content).hexdigest()
            return content.decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LapisError(f"could not fetch {url}: {exc}") from exc


def pango_provenance() -> str:
    """Content digests of the pango-designation files fetched this run."""
    return " ".join(
        f"{url.rsplit('/', 1)[-1]}@sha256:{sha}" for url, sha in sorted(PANGO_BLOBS.items())
    )


def fetch_pango_aliases() -> dict[str, Any]:
    """The live ``alias_key.json`` from pango-designation.

    Values are a string (the unaliased parent path) for ordinary lineages and a
    **list of parents** for recombinants. LAPIS does not carry the recombinant
    parentage — its lineage tree roots every X* lineage — so this file is the
    only place ``XFG -> [LF.7, LP.8.1.2]`` is recorded.
    """
    try:
        return json.loads(_fetch_text(PANGO_ALIAS_URL))
    except (ValueError, TypeError) as exc:
        raise LapisError("invalid Pango alias JSON") from exc


def fetch_lineage_notes() -> dict[str, dict[str, str]]:
    """Parse ``lineage_notes.txt`` into ``{name: {status, note}}``.

    Names prefixed ``*`` have been withdrawn or redesignated. Those entries are
    the reason a model's remembered lineage facts are not merely stale but
    wrong, so they are surfaced rather than filtered out.
    """
    parsed: dict[str, dict[str, str]] = {}
    for line in _fetch_text(PANGO_NOTES_URL).splitlines():
        if not line.strip() or line.startswith("Lineage\t"):
            continue
        name, _, note = line.partition("\t")
        name = name.strip()
        if not name:
            continue
        withdrawn = name.startswith("*")
        parsed[name.lstrip("*")] = {
            "status": "withdrawn" if withdrawn else "designated",
            "note": note.strip(),
        }
    return parsed


# --- pure helpers -----------------------------------------------------------


def supports_range(schema: dict, field: str) -> bool:
    """True when ``<field>From`` / ``<field>To`` exist for this field.

    LAPIS derives range filters from the declared type, so a date recorded as a
    string (H5N1's ``sampleCollectionDate``) has none.
    """
    return schema.get("types", {}).get(field) in RANGE_TYPES


def range_keys(field: str) -> tuple[str, str]:
    """The inclusive lower/upper filter keys for a range-capable field."""
    return f"{field}From", f"{field}To"


def pick_date_field(schema: dict, role: str = "collection", preferred: str | None = None) -> str:
    """Choose a range-capable date field for ``collection`` or ``submission``.

    Raises rather than guessing: a silently wrong date column produces a
    plausible time series of the wrong thing.
    """
    types = schema.get("types", {})
    if preferred:
        if preferred not in types:
            raise LapisError(f"{preferred!r} is not a field on this instance")
        if types[preferred] != "date":
            raise LapisError(
                f"{preferred!r} is typed {types[preferred]!r} on this instance, so LAPIS "
                f"cannot use it as a date range filter"
            )
        return preferred

    ordered = COLLECTION_DATE_FIELDS if role == "collection" else SUBMISSION_DATE_FIELDS
    for name in ordered:
        if types.get(name) == "date":
            return name
    needles = ("collect",) if role == "collection" else ("submit", "release")
    for name, kind in sorted(types.items()):
        low = name.lower()
        if kind == "date" and any(n in low for n in needles) and "_seg" not in low:
            return name
    raise LapisError(
        f"no range-capable {role} date field on this instance; "
        f"date-typed fields are: {sorted(n for n, t in types.items() if t == 'date')}"
    )


def looks_like_lineage(name: str) -> bool:
    """True for field names that plausibly hold a lineage, clade, or genotype.

    Deliberately loose, because the naming is not standardised across
    deployments: seasonal influenza splits the call per segment (``cladeHA``,
    ``cladeNA``), CCHF names it after the segment (``lineage_S``), mpox carries
    both ``clade`` and ``outbreakLineage``. Per-segment quality columns
    (``completeness_seg3``) are excluded.
    """
    low = name.lower()
    # "nextcladeQcOverallScore" contains "clade" and is not a lineage call.
    if any(token in low for token in ("_seg", "qc", "score", "coverage", "version")):
        return False
    return any(
        token in low for token in ("clade", "lineage", "genotype", "serotype", "subtype")
    )


def lineage_field_candidates(schema: dict) -> list[tuple[str, bool]]:
    """Every plausible lineage column as ``(name, indexed)``, best first.

    Indexed columns come first because only they support descendant queries.
    Within a tier, the names this skill knows outrank the ones it guessed, and
    an HA-derived clade outranks NA — for influenza the HA clade is the one
    that antigenic and vaccine-strain discussion refers to.
    """
    types = schema.get("types", {})
    indexed = set(schema.get("lineage_indexed", []))
    known = {name: rank for rank, name in enumerate(LINEAGE_FIELDS)}

    def sort_key(name: str) -> tuple:
        return (
            0 if name in indexed else 1,
            known.get(name, len(LINEAGE_FIELDS)),
            0 if name.upper().endswith("HA") else 1,
            name,
        )

    names = [n for n in types if looks_like_lineage(n)]
    return [(n, n in indexed) for n in sorted(names, key=sort_key)]


def pick_lineage_field(schema: dict, preferred: str | None = None) -> tuple[str, bool]:
    """Choose the lineage/clade column. Returns ``(field, has_lineage_index)``.

    The index flag decides whether a trailing ``*`` expands to descendants or
    matches nothing, so it travels with the field name everywhere.
    """
    types = schema.get("types", {})
    if preferred:
        if preferred not in types:
            raise LapisError(f"{preferred!r} is not a field on this instance")
        return preferred, preferred in set(schema.get("lineage_indexed", []))
    candidates = lineage_field_candidates(schema)
    if not candidates:
        raise LapisError(
            "no lineage-like column on this instance; pass --lineage-field with one of: "
            + ", ".join(sorted(types))
        )
    return candidates[0]


def lineage_filter(value: str, has_index: bool, include_sublineages: bool) -> str:
    """Build the lineage filter value, refusing the query that lies.

    ``XFG*`` on an indexed column means XFG and every descendant. The same
    string on an unindexed column is a literal match against a name no sequence
    carries, and LAPIS answers 0 without complaint.
    """
    stripped = value.rstrip("*")
    wants_children = include_sublineages or value.endswith("*")
    if not wants_children:
        return stripped
    if not has_index:
        raise LapisError(
            f"{value!r} asks for sublineages, but this column carries no lineage index, "
            "so a trailing '*' would match nothing and report 0. Query the exact name, "
            "or enumerate descendants yourself."
        )
    return f"{stripped}*"


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Used instead of the normal approximation because surveillance weeks are
    routinely small or zero-count, where Wald intervals leave the unit interval
    and report zero width at p=0.
    """
    if total <= 0:
        return (0.0, 1.0)
    k, n = float(successes), float(total)
    denom = n + z * z
    centre = (k + z * z / 2.0) / denom
    half = (z / denom) * math.sqrt(k * (n - k) / n + z * z / 4.0)
    return (max(0.0, centre - half), min(1.0, centre + half))


def iso_week_start(value: str) -> str | None:
    """Monday of the ISO week containing an ISO date, or None if unparseable.

    LAPIS returns nulls and partial dates for sequences whose collection date
    was never reported; those are counted separately, never silently binned.
    """
    if not value or len(value) < 10:
        return None
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return None
    return (parsed - timedelta(days=parsed.weekday())).isoformat()


def bin_weekly(rows: Iterable[dict], date_key: str) -> tuple[dict[str, int], int]:
    """Sum ``count`` into ISO weeks. Returns ``(weeks, undated)``."""
    weeks: dict[str, int] = {}
    undated = 0
    for row in rows:
        week = iso_week_start(str(row.get(date_key) or ""))
        n = int(row.get("count") or 0)
        if week is None:
            undated += n
            continue
        weeks[week] = weeks.get(week, 0) + n
    return weeks, undated


def week_range(start: str, end: str) -> list[str]:
    """Every ISO week start from ``start`` to ``end`` inclusive, gaps included."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    out: list[str] = []
    cursor = first - timedelta(days=first.weekday())
    while cursor <= last:
        out.append(cursor.isoformat())
        cursor += timedelta(days=7)
    return out


def flag_low_coverage(weekly_totals: dict[str, int], fraction: float = 0.4) -> dict[str, bool]:
    """Flag low counts relative to the older half; this is not completeness."""
    if not weekly_totals:
        return {}
    ordered = sorted(weekly_totals)
    settled = ordered[: max(1, len(ordered) // 2)]
    counts = sorted(weekly_totals[w] for w in settled)
    mid = len(counts) // 2
    median = counts[mid] if len(counts) % 2 else (counts[mid - 1] + counts[mid]) / 2
    threshold = median * fraction
    return {week: weekly_totals[week] <= 0 or weekly_totals[week] < threshold for week in ordered}


def logit_slope(
    points: Sequence[tuple[float, int, int]],
    *,
    min_successes: int = 5,
    min_nonzero_weeks: int = 3,
) -> dict[str, float] | None:
    """Weighted least-squares slope of log-odds against time.

    ``points`` are ``(t_weeks, successes, total)``. Proportions are shifted by
    the Haldane-Anscombe 0.5 so that 0 and 1 remain finite, and each point is
    weighted by the inverse variance of its logit, ``n*p*(1-p)``.

    This is a **descriptive** slope, not a fitness estimate. It absorbs any
    change in who is sequencing, where, and how fast they report, and it
    assumes the composition of the denominator is stable across the window.

    Returns None unless there is something to fit. The success thresholds are
    not decoration: with the continuity correction alone, a lineage observed
    **zero** times in every week still yields p = 0.5/(n+1), which drifts purely
    with the denominator. A shrinking denominator then manufactures a tight,
    confident-looking positive slope for a lineage nobody has seen. Requiring
    real observations is what stops that number from being printed.
    """
    usable = [(t, k, n) for t, k, n in points if n > 0]
    if len(usable) < 3:
        return None
    if sum(k for _, k, _ in usable) < min_successes:
        return None
    if sum(1 for _, k, _ in usable if k > 0) < min_nonzero_weeks:
        return None

    rows = []
    for t, k, n in usable:
        p = (k + 0.5) / (n + 1.0)
        weight = n * p * (1.0 - p)
        if weight <= 0:
            continue
        rows.append((t, math.log(p / (1.0 - p)), weight))
    if len(rows) < 3:
        return None

    sw = sum(w for _, _, w in rows)
    mean_t = sum(w * t for t, _, w in rows) / sw
    mean_y = sum(w * y for _, y, w in rows) / sw
    sxx = sum(w * (t - mean_t) ** 2 for t, _, w in rows)
    if sxx <= 0:
        return None
    sxy = sum(w * (t - mean_t) * (y - mean_y) for t, y, w in rows)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_t

    # Quasi-binomial dispersion, clamped at 1. With inverse-variance weights the
    # model's own scale is 1, so an estimate below 1 is underdispersion -- almost
    # always a short series that happens to sit near the line, not evidence the
    # slope is better determined than binomial sampling allows. Letting it
    # through would report a CI narrower than the data can support. Above 1 it
    # is kept, so real overdispersion widens the interval as it should.
    residual = sum(w * (y - intercept - slope * t) ** 2 for t, y, w in rows)
    dof = len(rows) - 2
    dispersion = max(residual / dof, 1.0) if dof > 0 else 1.0
    stderr = math.sqrt(dispersion / sxx)
    return {
        "slope_per_week": slope,
        "stderr": stderr,
        "dispersion": dispersion,
        "ci_low": slope - Z_95 * stderr,
        "ci_high": slope + Z_95 * stderr,
        "n_weeks": float(len(rows)),
    }


def unalias(name: str, aliases: dict[str, Any]) -> str:
    """Expand a Pango alias to its full dotted path under A or B.

    ``PQ.17`` unaliases to ``XDV.1.5.1.1.8.1.17``; applied repeatedly it walks
    back to ``B.1.1.529...``. Recombinants stop the walk: their alias entry is a
    list of parents, not a path, so ``XFG.1.1`` expands no further.
    """
    head, _, tail = name.partition(".")
    target = aliases.get(head)
    if not isinstance(target, str) or not target:
        return name
    return f"{target}.{tail}" if tail else target


def unalias_full(name: str, aliases: dict[str, Any], limit: int = 20) -> str:
    """Apply :func:`unalias` until it reaches a fixed point."""
    current = name
    for _ in range(limit):
        expanded = unalias(current, aliases)
        if expanded == current:
            return current
        current = expanded
    return current


def recombinant_parents(name: str, aliases: dict[str, Any]) -> list[str]:
    """Parents of a recombinant lineage, or [] for an ordinary one."""
    head = name.partition(".")[0]
    target = aliases.get(head)
    if isinstance(target, list):
        seen: list[str] = []
        for parent in target:
            if parent not in seen:
                seen.append(parent)
        return seen
    return []


def parent_chain(name: str, definition: dict, limit: int = 60) -> list[str]:
    """Walk a LAPIS lineage definition from a lineage up to its root."""
    chain: list[str] = []
    current = name
    for _ in range(limit):
        parents = (definition.get(current) or {}).get("parents") or []
        if not parents:
            break
        current = parents[0]
        if current in chain:
            break
        chain.append(current)
    return chain


def children_map(definition: dict) -> dict[str, list[str]]:
    """Invert a lineage definition into parent -> children.

    Worth building once and passing around: the SARS-CoV-2 definition holds
    thousands of entries, so rebuilding it per lineage turns a list of names into
    quadratic work.
    """
    children: dict[str, list[str]] = {}
    for lineage, entry in definition.items():
        for parent in (entry or {}).get("parents") or []:
            children.setdefault(parent, []).append(lineage)
    return children


def descendants(
    name: str, definition: dict, children: dict[str, list[str]] | None = None
) -> list[str]:
    """Every lineage whose parent chain passes through ``name``.

    Pass ``children`` from :func:`children_map` when resolving several names.
    """
    if children is None:
        children = children_map(definition)
    found: set[str] = set()
    stack = list(children.get(name, []))
    while stack:
        node = stack.pop()
        if node in found:
            continue
        found.add(node)
        stack.extend(children.get(node, []))
    return sorted(found)


def top_values(rows: Sequence[dict], field: str, limit: int) -> list[str]:
    """The ``limit`` most frequent non-null values of a grouped-by field.

    Used to discover what is actually circulating before naming anything, so a
    situation report starts from the data rather than from a remembered list.
    """
    ranked = sorted(
        (r for r in rows if r.get(field) not in (None, "")),
        key=lambda r: -int(r.get("count") or 0),
    )
    return [str(r[field]) for r in ranked[:limit]]


# Every C0 and C1 control character, tabs and newlines included -- a single
# newline in a label is enough to forge a row in TSV output.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def sanitize(value: object, limit: int = 400) -> str:
    """Flatten a value to one printable line for table and TSV rendering.

    Cell values reach here from a remote instance: lineage labels, field names,
    and error ``detail`` strings. Two reasons to flatten them.

    Correctness: a tab or newline inside a label silently corrupts TSV columns.

    Safety: this output is read by an agent, so remote text is untrusted input.
    Stripping control characters and collapsing line breaks stops a hostile or
    malformed instance from forging rows, headers, or anything that reads as
    structure rather than data. It is not a substitute for pointing
    ``--base-url`` only at deployments you trust.

    JSON output deliberately skips this — the encoder escapes control
    characters already, so values stay faithful for machine consumers.
    """
    text = "" if value is None else str(value)
    text = re.sub(r"\s{2,}", " ", _CONTROL_CHARS.sub(" ", text)).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def format_table(rows: Sequence[dict], columns: Sequence[str]) -> str:
    """Render rows as an aligned plain-text table."""
    header = list(columns)
    body = [[sanitize(r.get(c)) for c in header] for r in rows]
    widths = [
        max(len(header[i]), *(len(r[i]) for r in body)) if body else len(header[i])
        for i in range(len(header))
    ]
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(header)).rstrip()]
    for row in body:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return "\n".join(lines)


def emit(rows: Sequence[dict], columns: Sequence[str], fmt: str) -> str:
    """Render rows as ``table``, ``tsv``, or ``json``."""
    if fmt == "json":
        return json.dumps([{c: r.get(c) for c in columns} for r in rows], indent=2)
    if fmt == "tsv":
        lines = ["\t".join(columns)]
        lines += ["\t".join(sanitize(r.get(c)) for c in columns) for r in rows]
        return "\n".join(lines)
    return format_table(rows, columns)
