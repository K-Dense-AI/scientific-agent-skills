#!/usr/bin/env python3
"""Agent-oriented RMBase CLI. Python standard library; no daemon or credentials."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from client import CATALOG, MOD_TYPES, Client, catalog, context
from datasets import dataset_route
from parsers import validate_bed
from transport import BASE, RMBaseError, Transport, utc_now


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise RMBaseError("invalid_arguments", message)


def parser():
    root = Parser(description=__doc__, prog="rmbase")
    sub = root.add_subparsers(dest="command", required=True, parser_class=Parser)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--assembly", default="hg38", help="Exact RMBase assembly (default: human hg38).")
    common.add_argument("--species", help="Optional exact species name; checked against assembly.")
    common.add_argument("--cache-dir", type=Path)
    common.add_argument("--offline", action="store_true", help="Use local datasets or exact saved responses only.")
    common.add_argument("--refresh", action="store_true", help="Refresh a query/dataset instead of reusing its cache.")
    common.add_argument("--timeout", type=float, default=30)
    common.add_argument("--retries", type=int, default=1)
    common.add_argument("--limit", type=int, default=50, help="Local output slice (1–500); not a server limit.")
    common.add_argument("--offset", type=int, default=0)
    formats = common.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true", help="JSON is the default.")
    formats.add_argument("--tsv", action="store_true")
    common.add_argument("--out", type=Path)
    common.add_argument("--provenance-out", type=Path, help="Required with TSV; saves the JSON envelope without records.")

    def command(name, description):
        return sub.add_parser(name, parents=[common], help=description, description=description)

    p = command("catalog", "Show audited species, assemblies and exact form options without network access.")
    p.add_argument("module", nargs="?")
    p = command("gene", "Query RNA modifications on a gene; use enzyme separately for protein activity.")
    p.add_argument("gene")
    p.add_argument("--mode", choices=["genename", "geneid", "transcript"], default="genename")
    p.add_argument("--source", choices=["auto", "local", "remote"], default="auto")
    p.add_argument("--modification", choices=["m6a", "m1a", "m5c", "m7g", "pseudo", "nm", "editing", "other"])
    p = command("modification", "Retrieve one observed RMBase modification ID via an HTML adapter.")
    p.add_argument("modification_id")
    p.add_argument("--type", choices=sorted(MOD_TYPES), required=True)
    p = command("sites", "Query a modification/cell combination; the server returns a full filtered array.")
    p.add_argument("--type", choices=sorted(MOD_TYPES), required=True)
    p.add_argument("--cell", required=True)
    p.add_argument("--min-support", type=int, default=1)
    p.add_argument("--max-support", type=int, default=1000)
    p = command("enzyme", "Query the website's enzyme-catalysis records.")
    p.add_argument("enzyme")
    p = command("snorna", "Query snoRNA guidance records; optional exact-name filtering is local.")
    p.add_argument("name", nargs="?")
    p = command("cluster", "Query an offered cluster type; output limits are local.")
    p.add_argument("type")
    p = command("motif", "Retrieve enriched motif sequences, statistics and matrix links.")
    p.add_argument("type", nargs="?")
    p.add_argument("--datasets", action="store_true", help="Return m6A experiment metadata instead of enriched motifs.")
    p = command("interaction", "Query one RBP or miRNA, or a variant form's exact filters.")
    p.add_argument("kind", choices=["rbp", "mirna", "variant"])
    p.add_argument("name", help="RBP symbol, miRNA name, or cancer label for the variant form.")
    p.add_argument("--category", required=True, help="Exact website choice; use catalog rbp/mirna/variant.")
    p.add_argument("--subtype", choices=["know", "unknow"], default="know")
    p.add_argument("--min-support", type=int, default=1)
    p = command("colocalization", "Query a human cell/histone/RNA modification combination.")
    p.add_argument("--cell", required=True)
    p.add_argument("--histone", required=True)
    p.add_argument("--modification", required=True)
    p = command("cancer", "Retrieve TCGA records for an RNA-modifying protein; coordinate assembly is unspecified.")
    p.add_argument("gene")
    p.add_argument("--section", choices=["DIFF", "SCNA", "CNV"], default="DIFF")
    p = command("datasets", "List official gene/transcript archive URLs for an assembly; no download.")
    p = command("sync", "Cache one official gene/transcript archive after schema validation.")
    p.add_argument("--kind", choices=["genes", "trans"], default="genes")
    p.add_argument("--archive", type=Path, help="Import an existing archive; provenance marks origin as user-supplied.")
    for name in ("annotation", "metagene", "gene-tool"):
        p = command(name, "Validate input or submit once to the existing CGI. Audit status: HTTP 503; task lifecycle unverified.")
        p.add_argument("input", type=Path)
        p.add_argument("--validate-only", action="store_true")
        p.add_argument("--public-data", action="store_true", help="Input is authorized for transmission over public HTTP.")
    p = command("task", "Report the unverified task lifecycle honestly; does not poll the server.")
    p.add_argument("task_id")
    return root


def execute(args):
    if args.offline and args.refresh:
        raise RMBaseError("invalid_arguments", "--offline and --refresh cannot be combined.")
    if args.tsv and not args.provenance_out:
        raise RMBaseError("provenance_required", "TSV output requires --provenance-out FILE.")
    if args.out and args.provenance_out and args.out.resolve() == args.provenance_out.resolve():
        raise RMBaseError("output_collision", "Data and provenance must use different output files.")
    http = Transport(args.cache_dir, args.timeout, args.retries, args.offline, args.refresh)
    client = Client(http, args.assembly, args.species, args.limit, args.offset)
    cmd = args.command
    if cmd == "catalog":
        return {"schema_version": "1.0", "status": "ok", "command": cmd,
                "records": [catalog(args.module, args.assembly if args.module else None)]}
    if cmd == "gene":
        return client.gene(args.gene, args.mode, args.source, args.modification)
    if cmd == "modification":
        return client.modification(args.modification_id, args.type)
    if cmd == "sites":
        return client.sites(args.type, args.cell, args.min_support, args.max_support)
    if cmd in {"enzyme", "cluster", "snorna"}:
        value = getattr(args, {"enzyme": "enzyme", "cluster": "type", "snorna": "name"}[cmd])
        return client.lookup(cmd, value)
    if cmd == "motif":
        if args.datasets and args.type:
            raise RMBaseError("invalid_arguments", "Choose motif TYPE or motif --datasets.")
        return client.lookup("motif-datasets" if args.datasets else "motif", args.type)
    if cmd == "interaction":
        return client.lookup(args.kind, args.name, category=args.category, subtype=args.subtype, support=args.min_support)
    if cmd == "colocalization":
        return client.colocalization(args.cell, args.histone, args.modification)
    if cmd == "cancer":
        return client.cancer(args.gene, args.section)
    if cmd in {"sync", "datasets"}:
        context("gene", args.assembly, args.species)
        if args.assembly not in CATALOG["downloads"]["downModGeneObj"]:
            raise RMBaseError("invalid_assembly", "No gene/transcript download is listed for this assembly.")
        if cmd == "sync":
            data = client.datasets.sync(args.assembly, args.kind, args.archive)
            return client.result(cmd, [data], {"assembly": args.assembly, "kind": args.kind}, "LOCAL_DATASET")
        return client.result(cmd, [{"kind": kind, "url": BASE + dataset_route(args.assembly, kind)} for kind in ("genes", "trans")],
                             {"assembly": args.assembly}, "LOCAL_CATALOG")
    if cmd in {"annotation", "metagene", "gene-tool"}:
        if args.validate_only:
            context("tools", args.assembly, args.species)
            if cmd == "gene-tool":
                raise RMBaseError("unsupported_validation", "Use gene --mode geneid for individual IDs; BED validation applies to annotation/metagene.")
            if args.input.stat().st_size >= 2_000_000:
                raise RMBaseError("invalid_bed", "BED6 must be smaller than 2 MB.")
            count = validate_bed(args.input.read_bytes())
            return client.result(cmd, [{"valid": True, "intervals": count, "coordinate_system": "BED: 0-based, half-open"}],
                                 {"validation_only": True}, "LOCAL_VALIDATION")
        return client.submit(cmd, args.input, public_data=args.public_data)
    return client.task(args.task_id)


def tsv_text(records):
    columns = sorted({key for row in records for key in row})
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, columns, dialect="excel-tab", lineterminator="\n")
    writer.writeheader()
    for row in records:
        writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value
                         for key, value in row.items()})
    return stream.getvalue()


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        result = execute(args)
        output = tsv_text(result["records"]) if args.tsv else json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.provenance_out:
            envelope = {key: value for key, value in result.items() if key != "records"}
            args.provenance_out.write_text(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if args.out:
            args.out.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        return 0
    except RMBaseError as exc:
        print(json.dumps({"schema_version": "1.0", "status": "error", "queried_at": utc_now(), "error": exc.as_dict()}, sort_keys=True))
        return exc.exit_code
    except OSError as exc:
        print(json.dumps({"schema_version": "1.0", "status": "error", "error": {"code": "io_error", "message": str(exc)}}, sort_keys=True))
        return 6


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
