#!/usr/bin/env python3
"""Bounded, rate-limited, count-reconciling pagination for this skill's APIs.

The five database adapters here paginate differently -- absolute record offsets
or opaque cursors -- and each reports totals its
own way. Re-deriving the walk per query is how records get silently dropped. The
worst case is bioRxiv: `cursor` is an absolute offset, `/details/` returns 30 per
page but `/pubs/` returns 100, and an out-of-step cursor returns **HTTP 200**, so
stepping by 100 skips records 30-99 of every hundred and looks successful.

Every walk here:

- steps by the page size the response actually reported, never an assumed one
- stops on this API's terminator (Europe PMC may omit the next cursor or echo it
  on an empty page; bioRxiv also stops at its reported total)
- reconciles retrieved against the expected total and **exits 4 on a shortfall**
- refuses to exceed --max-records / --max-calls, and says so rather than
  truncating quietly

    python3 paginate.py --api biorxiv --query 2024-01-01/2024-01-03
    python3 paginate.py --api europepmc --query 'SRC:"PPR" AND "organoid"' --max-records 200
    python3 paginate.py --api openalex --query 'filter=publication_year:2024' --dry-run

Needs network access. No credentials required for bioRxiv, medRxiv, Europe PMC,
Crossref, or OpenAlex; OPENALEX_API_KEY raises the OpenAlex daily budget.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import Reconciliation, emit, fail, redact_url  # noqa: E402

USER_AGENT = "paper-lookup-skill/2.4 (+https://agentskills.io)"
DEFAULT_MAX_RECORDS = 1000
DEFAULT_MAX_CALLS = 50
REQUEST_TIMEOUT = 60


@dataclass
class Page:
    """One response, normalized."""

    records: list[Any]
    total: int | None = None
    #: The next cursor/token/offset, or None when this API says it is done.
    next_state: Any = None
    #: Anything the caller must be told that is not a record.
    notes: list[str] | None = None


@dataclass
class Api:
    name: str
    #: Seconds to wait between requests. Serialized: never parallelize one host.
    delay: float
    build_url: Callable[[str, Any, int], str]
    parse: Callable[[Any, Any], Page]
    initial_state: Any = 0
    note: str = ""


def fetch(url: str, *, headers: dict[str, str] | None = None) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        # Servers may echo credentials in their error bodies. Do not print them.
        raise RuntimeError(f"HTTP {error.code} from {redact_url(url)}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"could not reach {redact_url(url)}") from error
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"response from {redact_url(url)} was not JSON") from error


# --- bioRxiv / medRxiv ------------------------------------------------------
#
# `cursor` is an absolute record offset. The page size is 30 on /details/ and 100
# on /pubs/, and an out-of-step cursor is accepted with HTTP 200 -- so the step
# comes from the response's own `count`, never from a constant.


def _rxiv_url(server: str) -> Callable[[str, Any, int], str]:
    def build(query: str, state: Any, _limit: int) -> str:
        endpoint = "pubs" if query.startswith("pubs:") else "details"
        interval = query[5:] if query.startswith("pubs:") else query
        if interval.startswith("10."):
            return f"https://api.biorxiv.org/{endpoint}/{server}/{urllib.parse.quote(interval, safe='/')}/na/json"
        if interval.isdigit():
            return f"https://api.biorxiv.org/{endpoint}/{server}/{interval}"
        suffix = "/json" if endpoint == "details" else ""
        return f"https://api.biorxiv.org/{endpoint}/{server}/{interval}/{int(state)}{suffix}"

    return build


def _rxiv_parse(payload: Any, state: Any) -> Page:
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected a JSON object, got {type(payload).__name__}")

    if not isinstance(payload.get("collection"), list) or not isinstance(payload.get("messages"), list):
        raise RuntimeError("bioRxiv/medRxiv response lacks messages/collection arrays")
    messages = payload.get("messages") or [{}]
    message = messages[0] if isinstance(messages[0], dict) else {}
    status = message.get("status")
    records = payload.get("collection") or []
    notes: list[str] = []

    if status and status != "ok":
        if status != "no articles found":
            raise RuntimeError("bioRxiv/medRxiv returned a non-success status")
        # "no articles found" arrives with HTTP 200 and an empty collection, which
        # is indistinguishable from a genuine no-match unless status is read.
        notes.append(f"server status: {status!r} (HTTP 200 with an empty collection)")
        return Page(records=[], total=None, next_state=None, notes=notes)

    total = message.get("total")
    total = int(total) if total is not None and str(total).isdigit() else None

    new_papers = message.get("count_new_papers")
    if new_papers is not None:
        notes.append(
            f"count_new_papers={new_papers} counts distinct first-posting preprints while "
            f"total={total} counts every version record; deduplicate by DOI to compare against "
            "count_new_papers"
        )

    reported = message.get("count")
    step = int(reported) if isinstance(reported, int) and reported > 0 else len(records)
    if not records:
        return Page(records=[], total=total, next_state=None, notes=notes)
    if total is None:
        notes.append("endpoint reports no total or continuation; retained one response only")
        return Page(records=records, total=None, next_state=None, notes=notes)

    if step != len(records):
        notes.append(f"response reported count={step} but returned {len(records)} records")
        step = len(records)

    next_state = int(state) + step
    if total is not None and next_state >= total:
        next_state = None
    return Page(records=records, total=total, next_state=next_state, notes=notes)


# --- Europe PMC ------------------------------------------------------------
#
# cursorMark. Exhaustion may omit the next cursor or return an empty result list
# with the cursor echoed back. Accept both forms.


def _europepmc_url(query: str, state: Any, limit: int) -> str:
    params = {
        "query": query,
        "format": "json",
        "pageSize": str(min(limit, 1000)),
        "cursorMark": str(state),
        "resultType": "lite",
    }
    return "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(params)


def _europepmc_parse(payload: Any, state: Any) -> Page:
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected a JSON object, got {type(payload).__name__}")
    # Europe PMC reports errors with HTTP 200 and an errCode in the body.
    if "errCode" in payload:
        raise RuntimeError(
            f"Europe PMC errCode {payload['errCode']}: {payload.get('errMsg', 'no message')}"
        )
    if not isinstance(payload.get("resultList"), dict) or not isinstance(payload.get("hitCount"), int):
        raise RuntimeError("Europe PMC response lacks resultList/hitCount")

    total = payload.get("hitCount")
    records = (payload.get("resultList") or {}).get("result") or []
    next_cursor = payload.get("nextCursorMark")
    notes: list[str] = []

    echoed = (payload.get("request") or {}).get("queryString")
    if echoed:
        notes.append(f"query as parsed by Europe PMC: {echoed!r}")

    if not records or next_cursor in (None, state):
        next_cursor = None
    return Page(
        records=records,
        total=int(total) if isinstance(total, int) else None,
        next_state=next_cursor,
        notes=notes,
    )


# --- OpenAlex --------------------------------------------------------------


def _openalex_url(query: str, state: Any, limit: int) -> str:
    # `query` is a raw parameter string, e.g. `search=crispr` or
    # `filter=publication_year:2024`, so both forms work without a second flag.
    base = "https://api.openalex.org/works?"
    params = dict(urllib.parse.parse_qsl(query, keep_blank_values=True))
    params.update({"per_page": str(min(limit, 100)), "cursor": str(state)})
    params.pop("per-page", None)
    params.pop("page", None)
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        params["api_key"] = key
    return base + urllib.parse.urlencode(params)


def _openalex_parse(payload: Any, _state: Any) -> Page:
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected a JSON object, got {type(payload).__name__}")
    if not isinstance(payload.get("meta"), dict) or not isinstance(payload.get("results"), list):
        raise RuntimeError("OpenAlex response lacks meta/results; it may be an API error")
    meta = payload.get("meta") or {}
    records = payload.get("results") or []
    notes = []
    if meta.get("cost_usd") is not None:
        notes.append(f"OpenAlex reported cost_usd={meta['cost_usd']} for this call")
    next_cursor = meta.get("next_cursor")
    if not records:
        next_cursor = None
    return Page(
        records=records,
        total=meta.get("count") if isinstance(meta.get("count"), int) else None,
        next_state=next_cursor,
        notes=notes,
    )


# --- Crossref --------------------------------------------------------------


def _crossref_url(query: str, state: Any, limit: int) -> str:
    params = dict(urllib.parse.parse_qsl(query, keep_blank_values=True))
    params.update({"rows": str(min(limit, 1000)), "cursor": str(state)})
    params.pop("offset", None)
    if "sample" in params:
        raise RuntimeError("Crossref sample cannot be combined with cursor pagination")
    mail = os.environ.get("CROSSREF_MAILTO")
    if mail:
        params["mailto"] = mail
    return "https://api.crossref.org/works?" + urllib.parse.urlencode(params)


def _crossref_parse(payload: Any, _state: Any) -> Page:
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected a JSON object, got {type(payload).__name__}")
    message = payload.get("message") or {}
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise RuntimeError("Crossref response lacks message.items; it may be an API error")
    records = message.get("items") or []
    next_cursor = message.get("next-cursor")
    requested = message.get("items-per-page")
    if not records or (isinstance(requested, int) and len(records) < requested):
        next_cursor = None
    total = message.get("total-results")
    notes = ["Crossref cursors expire after 5 minutes; a long walk must keep moving"]
    return Page(
        records=records,
        total=int(total) if isinstance(total, int) else None,
        next_state=next_cursor,
        notes=notes,
    )


APIS: dict[str, Api] = {
    "biorxiv": Api(
        name="biorxiv",
        delay=1.0,
        build_url=_rxiv_url("biorxiv"),
        parse=_rxiv_parse,
        initial_state=0,
        note=(
            "query is an interval (2024-01-01/2024-01-03), Nd, N, or a DOI. "
            "Prefix with 'pubs:' to walk /pubs/ instead of /details/."
        ),
    ),
    "medrxiv": Api(
        name="medrxiv",
        delay=1.0,
        build_url=_rxiv_url("medrxiv"),
        parse=_rxiv_parse,
        initial_state=0,
        note="same as biorxiv; always via api.biorxiv.org, never api.medrxiv.org",
    ),
    "europepmc": Api(
        name="europepmc",
        delay=0.5,
        build_url=_europepmc_url,
        parse=_europepmc_parse,
        initial_state="*",
        note="query is Europe PMC query syntax, e.g. 'SRC:\"PPR\" AND \"organoid\"'",
    ),
    "openalex": Api(
        name="openalex",
        delay=0.2,
        build_url=_openalex_url,
        parse=_openalex_parse,
        initial_state="*",
        note="query is a raw parameter string, e.g. 'search=crispr' or 'filter=publication_year:2024'",
    ),
    "crossref": Api(
        name="crossref",
        delay=1.0,
        build_url=_crossref_url,
        parse=_crossref_parse,
        initial_state="*",
        note="query is a raw parameter string, e.g. 'query.bibliographic=attention+is+all+you+need'",
    ),
}


def walk(
    api: Api,
    query: str,
    *,
    page_size: int,
    max_records: int,
    max_calls: int,
    verbose: bool,
) -> tuple[list[Any], Reconciliation, list[str]]:
    records: list[Any] = []
    reconciliation = Reconciliation()
    urls: list[str] = []
    state = api.initial_state
    seen_notes: set[str] = set()

    while True:
        if reconciliation.pages >= max_calls:
            reconciliation.stopped_at_limit = True
            reconciliation.note(
                f"stopped at the --max-calls limit of {max_calls}; the walk is INCOMPLETE"
            )
            break
        if len(records) >= max_records:
            reconciliation.stopped_at_limit = True
            reconciliation.note(
                f"stopped at the --max-records limit of {max_records}; the walk is INCOMPLETE"
            )
            break

        remaining = max_records - len(records)
        try:
            url = api.build_url(query, state, min(page_size, remaining))
        except RuntimeError as error:
            fail(str(error))
        # Record and log the redacted form only. OpenAlex and Crossref authenticate
        # by query string, so the fetched URL carries the credential and this
        # provenance list is printed to the user.
        safe_url = redact_url(url)
        urls.append(safe_url)
        if verbose:
            sys.stderr.write(f"  page {reconciliation.pages + 1}: {safe_url}\n")

        try:
            page = api.parse(fetch(url), state)
        except RuntimeError as error:
            fail(str(error))

        reconciliation.pages += 1
        if page.total is not None and reconciliation.expected is None:
            reconciliation.expected = page.total
        for note in page.notes or []:
            if note not in seen_notes:
                seen_notes.add(note)
                reconciliation.note(note)

        records.extend(page.records)
        if page.next_state is None:
            break
        state = page.next_state
        time.sleep(api.delay)

    # Trim only after the walk, so the reported page count stays truthful.
    if len(records) > max_records:
        reconciliation.stopped_at_limit = True
        reconciliation.note(
            f"last page overshot --max-records; kept the first {max_records} of {len(records)}"
        )
        records = records[:max_records]

    reconciliation.retrieved = len(records)
    return records, reconciliation, urls


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Paginate one of this skill's APIs with the correct step, the correct stop "
            "condition, and count reconciliation. Exits 4 on a reconciliation shortfall."
        ),
        epilog="python3 %(prog)s --api biorxiv --query 2024-01-01/2024-01-03",
    )
    # Not `required=True`: --list-apis is the flag you reach for when you do not yet
    # know what to pass for either of these.
    parser.add_argument("--api", choices=sorted(APIS), help="which API to walk")
    parser.add_argument("--query", help="see --list-apis for the per-API format")
    parser.add_argument("--page-size", type=int, default=100, help="requested page size (default 100)")
    parser.add_argument(
        "--max-records",
        type=int,
        default=DEFAULT_MAX_RECORDS,
        help=f"stop after this many records (default {DEFAULT_MAX_RECORDS})",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=DEFAULT_MAX_CALLS,
        help=f"stop after this many requests (default {DEFAULT_MAX_CALLS})",
    )
    parser.add_argument("-o", "--output", help="write JSON here instead of stdout")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the first URL that would be requested and exit without fetching",
    )
    parser.add_argument("--list-apis", action="store_true", help="describe each API's query format")
    parser.add_argument("-v", "--verbose", action="store_true", help="log each URL to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_apis:
        emit(
            {
                name: {"delay_seconds": api.delay, "query_format": api.note}
                for name, api in sorted(APIS.items())
            },
            args.output,
        )
        return 0

    if not args.api or not args.query:
        fail("--api and --query are both required (use --list-apis to see the query format)", code=2)
    if args.page_size < 1:
        fail("--page-size must be at least 1")
    if args.max_records < 1:
        fail("--max-records must be at least 1")
    if args.max_calls < 1:
        fail("--max-calls must be at least 1")

    api = APIS[args.api]

    if args.dry_run:
        try:
            first_url = api.build_url(args.query, api.initial_state, args.page_size)
        except RuntimeError as error:
            fail(str(error))
        emit(
            {
                "api": api.name,
                "first_url": redact_url(first_url),
                "delay_seconds": api.delay,
                "query_format": api.note,
            },
            args.output,
        )
        return 0

    records, reconciliation, urls = walk(
        api,
        args.query,
        page_size=args.page_size,
        max_records=args.max_records,
        max_calls=args.max_calls,
        verbose=args.verbose,
    )

    emit(
        {
            "api": api.name,
            "query": (
                urllib.parse.urlsplit(redact_url("https://provenance.invalid/?" + args.query)).query
                if args.api in {"openalex", "crossref"} else args.query
            ),
            "provenance": {"urls": urls, "delay_seconds": api.delay},
            "reconciliation": reconciliation.as_dict(),
            "records": records,
        },
        args.output,
    )

    if not reconciliation.ok:
        # Exit 4 is reserved for the unexplained case: the walk terminated on its
        # own and still came up short, which means records went missing. A bound
        # the caller set is not a failure and exits 0 with the partiality recorded.
        fail(
            f"reconciliation failed: the walk ended on its own but retrieved "
            f"{reconciliation.retrieved} of {reconciliation.expected}. Records are missing -- "
            "say so before drawing any conclusion from this result.",
            code=4,
        )
    if reconciliation.stopped_at_limit:
        sys.stderr.write(
            f"note: stopped at a caller-set bound with {reconciliation.retrieved}"
            f"{f' of {reconciliation.expected}' if reconciliation.expected is not None else ''} "
            "records. Report this result as partial.\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
