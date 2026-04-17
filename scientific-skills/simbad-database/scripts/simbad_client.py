#!/usr/bin/env python3
"""
SIMBAD Database Client

A Python client for querying the SIMBAD astronomical database via both the
script interface and the TAP/ADQL service.

Usage examples:
    # Query an object by name
    results = query_object("M31", output_format="detailed")

    # Cone search around coordinates
    results = query_region(10.68458, 41.26917, radius=5.0, max_results=20)

    # Search by identifier pattern
    results = query_identifiers("NGC 10*", max_results=10)

    # Run an ADQL query via TAP
    data = tap_query("SELECT TOP 10 main_id, ra, dec FROM basic WHERE otype='Galaxy'")

    # Get all identifiers for an object
    ids = get_all_identifiers("M1")
"""

import requests
import sys
import json
import time
from typing import List, Dict, Optional, Any


SCRIPT_URL = "https://simbad.cds.unistra.fr/simbad/sim-script"
TAP_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"

# Characters that could enable script/SQL injection - must not appear in user input
_FORBIDDEN_IN_NAME = frozenset("\n\r\t'\"\\;<>")


def _sanitize_object_name(name: str) -> str:
    """Validate and sanitize object name for script interface (no injection)."""
    if not name or not isinstance(name, str):
        raise ValueError("Object name must be a non-empty string")
    name = " ".join(name.split())  # collapse whitespace
    if len(name) > 128:
        raise ValueError("Object name too long")
    if any(c in _FORBIDDEN_IN_NAME for c in name):
        raise ValueError("Object name contains disallowed characters")
    return name.strip()


def _sanitize_adql_string(s: str) -> str:
    """Escape single quotes for safe use in ADQL string literals."""
    if not s or not isinstance(s, str):
        raise ValueError("Identifier must be a non-empty string")
    if len(s) > 128:
        raise ValueError("Identifier too long")
    # Block newlines, semicolons, backslashes (injection vectors)
    bad = frozenset("\n\r\t\\;<>\"")
    if any(c in bad for c in s):
        raise ValueError("Identifier contains disallowed characters")
    return s.replace("'", "''")  # ADQL string literal escape


FORMAT_STRINGS = {
    "basic": "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE",
    "detailed": "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE | %SP | %FLUXLIST(V)",
    "full": (
        "%IDLIST(1) | %COO(A D;ICRS;J2000) | %OTYPE | %SP "
        "| %FLUXLIST(U;B;V;R;I;J;H;K) | %PM | %PLX | %RV | %MT"
    ),
}


def _execute_script(script: str, timeout: int = 30) -> str:
    """Send a script to the SIMBAD sim-script endpoint and return raw text."""
    response = requests.post(SCRIPT_URL, data={"script": script}, timeout=timeout)
    response.raise_for_status()
    return response.text.strip()


def _parse_script_response(
    text: str, max_results: Optional[int] = None
) -> List[Dict[str, str]]:
    """Parse pipe-delimited SIMBAD script output into a list of dicts."""
    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip() and not line.startswith("::")
    ]

    if any("error" in l.lower() or "not found" in l.lower() for l in lines):
        return []

    results = []
    for line in lines[:max_results] if max_results else lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue

        entry = {
            "main_id": parts[0],
            "coordinates": parts[1],
            "object_type": parts[2],
        }
        if len(parts) > 3:
            entry["spectral_type"] = parts[3]
        if len(parts) > 4:
            entry["flux"] = parts[4]
        if len(parts) > 5:
            entry["additional"] = parts[5:]

        results.append(entry)

    return results


def query_object(
    name: str, output_format: str = "basic"
) -> List[Dict[str, str]]:
    """
    Query SIMBAD for an astronomical object by name.

    Args:
        name: Object name (e.g., "M31", "Sirius", "NGC 1068")
        output_format: "basic", "detailed", or "full"

    Returns:
        List of result dicts with keys like main_id, coordinates, object_type, etc.
    """
    safe_name = _sanitize_object_name(name)
    fmt = FORMAT_STRINGS.get(output_format, FORMAT_STRINGS["basic"])
    script = "\n".join([
        "output console=off script=off",
        f'format object "{fmt}"',
        f"query id {safe_name}",
    ])
    text = _execute_script(script)
    return _parse_script_response(text)


def query_region(
    ra: float,
    dec: float,
    radius: float = 1.0,
    output_format: str = "basic",
    max_results: int = 10,
) -> List[Dict[str, str]]:
    """
    Cone search around a sky position.

    Args:
        ra: Right Ascension in degrees (0-360)
        dec: Declination in degrees (-90 to +90)
        radius: Search radius in arcminutes
        output_format: "basic", "detailed", or "full"
        max_results: Maximum number of results

    Returns:
        List of result dicts
    """
    fmt = FORMAT_STRINGS.get(output_format, FORMAT_STRINGS["basic"])
    script = "\n".join([
        "output console=off script=off",
        f'format object "{fmt}"',
        f"query coo {ra} {dec} radius={radius}m",
    ])
    text = _execute_script(script)
    return _parse_script_response(text, max_results=max_results)


def query_identifiers(
    pattern: str,
    output_format: str = "basic",
    max_results: int = 10,
) -> List[Dict[str, str]]:
    """
    Search for objects matching a wildcard identifier pattern.

    Args:
        pattern: Identifier with wildcards (e.g., "NGC 10*", "HD 20945*")
        output_format: "basic", "detailed", or "full"
        max_results: Maximum number of results

    Returns:
        List of result dicts
    """
    safe_pattern = _sanitize_object_name(pattern)
    fmt = FORMAT_STRINGS.get(output_format, FORMAT_STRINGS["basic"])
    script = "\n".join([
        "output console=off script=off",
        f'format object "{fmt}"',
        f"query id wildcard {safe_pattern}",
    ])
    text = _execute_script(script)
    return _parse_script_response(text, max_results=max_results)


def tap_query(
    adql_query: str,
    max_results: int = 100,
    fmt: str = "json",
) -> Any:
    """
    Execute an ADQL query on SIMBAD via TAP.

    Args:
        adql_query: ADQL query string
        max_results: Maximum number of rows
        fmt: Output format ("json" or "votable")

    Returns:
        Parsed JSON dict (if fmt="json") or raw VOTable string
    """
    params = {
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "QUERY": adql_query,
        "FORMAT": fmt,
        "MAXREC": max_results,
    }
    response = requests.post(TAP_URL, data=params, timeout=60)
    response.raise_for_status()

    if fmt == "json":
        try:
            return response.json()
        except ValueError:
            return response.text
    return response.text


def get_all_identifiers(name: str) -> List[str]:
    """
    Retrieve all known catalog identifiers for an object.

    Args:
        name: Object name (e.g., "M31")

    Returns:
        List of identifier strings
    """
    safe_name = _sanitize_adql_string(name)
    result = tap_query(
        f"SELECT i.id FROM ident AS i "
        f"JOIN basic AS b ON i.oidref = b.oid "
        f"WHERE b.main_id = '{safe_name}'",
        max_results=500,
        fmt="json",
    )

    if isinstance(result, dict) and "data" in result:
        return [row[0] for row in result["data"]]
    return []


def batch_query_objects(
    names: List[str],
    output_format: str = "basic",
    delay: float = 0.5,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Query multiple objects with rate-limiting.

    Args:
        names: List of object names
        output_format: "basic", "detailed", or "full"
        delay: Seconds to wait between queries

    Returns:
        Dict mapping object name to its result list
    """
    results = {}
    for name in names:
        results[name] = query_object(name, output_format)
        if delay > 0:
            time.sleep(delay)
    return results


def main():
    """Command-line interface for SIMBAD queries."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Query the SIMBAD astronomical database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --object "M31" --format detailed
  %(prog)s --region 10.68 41.27 --radius 5.0 --max 20
  %(prog)s --pattern "NGC 10*" --max 5
  %(prog)s --adql "SELECT TOP 10 main_id, ra, dec FROM basic WHERE otype='Galaxy'"
  %(prog)s --identifiers "M1"
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--object", "-o", help="Query object by name")
    group.add_argument(
        "--region",
        "-r",
        nargs=2,
        type=float,
        metavar=("RA", "DEC"),
        help="Cone search at RA DEC (degrees)",
    )
    group.add_argument("--pattern", "-p", help="Identifier wildcard pattern")
    group.add_argument("--adql", "-a", help="ADQL query for TAP")
    group.add_argument("--identifiers", "-i", help="Get all IDs for an object")

    parser.add_argument(
        "--format",
        "-f",
        default="basic",
        choices=["basic", "detailed", "full"],
        help="Output detail level (default: basic)",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=1.0,
        help="Search radius in arcminutes (default: 1.0)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="Max results (default: 10)",
    )

    args = parser.parse_args()

    try:
        if args.object:
            results = query_object(args.object, args.format)
            print(json.dumps(results, indent=2))

        elif args.region:
            ra, dec = args.region
            results = query_region(
                ra, dec, radius=args.radius,
                output_format=args.format, max_results=args.max,
            )
            print(json.dumps(results, indent=2))

        elif args.pattern:
            results = query_identifiers(
                args.pattern, output_format=args.format, max_results=args.max,
            )
            print(json.dumps(results, indent=2))

        elif args.adql:
            results = tap_query(args.adql, max_results=args.max)
            print(json.dumps(results, indent=2))

        elif args.identifiers:
            ids = get_all_identifiers(args.identifiers)
            for ident in ids:
                print(ident)

    except requests.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
