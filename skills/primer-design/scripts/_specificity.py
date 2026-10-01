"""Bounded, ungapped primer binding and inward-facing amplicon enumeration.

Coordinates are zero-based, half-open on the reference's forward strand.
For circular records, start is canonical and end may exceed the record length.
Neither this mismatch model nor BLAST models PCR chemistry or proves specificity.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from _common import revcomp


IUPAC = {
    "A": "A", "C": "C", "G": "G", "T": "T", "R": "AG", "Y": "CT",
    "S": "GC", "W": "AT", "K": "GT", "M": "AC", "B": "CGT", "D": "AGT",
    "H": "ACT", "V": "ACG", "N": "ACGT",
}


class SearchIncomplete(ValueError):
    """The requested screen cannot support a completed-search result."""


def source_oligos(pair):
    """Retain the physical oligo identity behind each local F/R role."""
    return pair.get("source_oligos") or {
        role: {
            "oligo_id": f"{pair['pair_id']}:{role}", "pair_id": pair["pair_id"],
            "primer_role": role, "annealing_sequence": pair[key],
            "tail_5prime": pair.get(key + "_tail", ""),
        }
        for role, key in (("F", "forward"), ("R", "reverse"))
    }


def expand_panel_pairs(pairs, max_combinations):
    """Add all cross-pair oligo combinations without mutating original pairs."""
    count = 2 * len(pairs) * (len(pairs) - 1)
    if count > max_combinations:
        raise SearchIncomplete(
            f"Multiplex requires {count:,} cross-oligo combinations; cap is {max_combinations:,}. "
            "No panel expansion or truncated screen was accepted."
        )
    prefix = "multiplex-cross-"
    while any(pair["pair_id"].startswith(prefix) for pair in pairs):
        prefix = "_" + prefix
    generated = []
    for first, second in combinations(sorted(pairs, key=lambda pair: pair["pair_id"]), 2):
        for first_role in ("F", "R"):
            for second_role in ("F", "R"):
                first_oligo, second_oligo = source_oligos(first)[first_role], source_oligos(second)[second_role]
                generated.append({
                    "pair_id": f"{prefix}{len(generated) + 1:06d}",
                    "forward": first_oligo["annealing_sequence"],
                    "reverse": second_oligo["annealing_sequence"],
                    "forward_tail": first_oligo["tail_5prime"],
                    "reverse_tail": second_oligo["tail_5prime"],
                    "cross_pair": True, "source_oligos": {"F": first_oligo, "R": second_oligo},
                })
    return list(pairs) + generated


def read_expected(path, pairs, references, circular):
    """Read exact intended product intervals; reject unverifiable identifiers."""
    result = {pair["pair_id"]: [] for pair in pairs}
    if path is None:
        return result
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"pair_id", "record_id", "start", "end"}
        header = reader.fieldnames or []
        if set(header) != required or len(header) != len(required):
            raise ValueError("Expected-target TSV requires exactly pair_id, record_id, start, end")
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Wrong expected-target column count, line {line}")
            pair_id, record_id = row["pair_id"], row["record_id"]
            if pair_id not in result or record_id not in references:
                raise ValueError(f"Unknown pair_id or record_id in expected targets, line {line}")
            try:
                start, end = int(row["start"]), int(row["end"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-integer expected coordinates, line {line}") from exc
            length = len(references[record_id])
            if not (0 <= start < length and start < end):
                raise ValueError(f"Invalid expected interval, line {line}")
            if end > (start + length if record_id in circular else length):
                raise ValueError(f"Expected interval exceeds molecule, line {line}")
            interval = {"record_id": record_id, "start": start, "end": end}
            if interval in result[pair_id]:
                raise ValueError(f"Duplicate expected interval, line {line}")
            result[pair_id].append(interval)
    return result


def reference_window(sequence, start, length, circular=False):
    if circular:
        if length > len(sequence):
            return None
        start %= len(sequence)
        end = start + length
        return sequence[start:end] if end <= len(sequence) else sequence[start:] + sequence[:end - len(sequence)]
    if start < 0 or start + length > len(sequence):
        return None
    return sequence[start:start + length]


def score_window(primer, window, strand, settings):
    """Conservative mismatch lower bounds; ambiguity never certifies a base."""
    oriented = window if strand == "+" else revcomp(window)
    mismatches, ambiguous = [], []
    for index, (base, reference_base) in enumerate(zip(primer, oriented), 1):
        if reference_base not in "ACGT":
            ambiguous.append(index)
        if base not in IUPAC[reference_base]:
            mismatches.append(index)
    boundary = len(primer) - settings["three_prime_bases"]
    terminal = [index for index in mismatches if index > boundary]
    if (len(mismatches) > settings["max_mismatches"] or
            len(terminal) > settings["max_three_prime_mismatches"]):
        return None
    possible = sorted(set(mismatches) | set(ambiguous))
    return {
        "mismatches": len(mismatches),
        "mismatch_positions_1based": mismatches,
        "mismatch_positions_from_five_prime_1based": mismatches,
        "mismatch_positions_from_three_prime_1based": sorted(len(primer) - i + 1 for i in mismatches),
        "three_prime_mismatches": len(terminal),
        "three_prime_mismatch_positions_1based": terminal,
        "three_prime_mismatch_positions_from_three_prime_1based": sorted(len(primer) - i + 1 for i in terminal),
        "mismatches_upper_bound": len(possible),
        "three_prime_mismatches_upper_bound": sum(i > boundary for i in possible),
        "ambiguous_positions_1based": ambiguous,
        "ambiguous_positions_from_five_prime_1based": ambiguous,
        "ambiguous_positions_from_three_prime_1based": sorted(len(primer) - i + 1 for i in ambiguous),
        "unresolved_ambiguity": bool(ambiguous),
    }


def make_hit(primer, record_id, sequence, start, strand, circular, settings):
    window = reference_window(sequence, start, len(primer), circular)
    if window is None:
        return None
    score = score_window(primer, window, strand, settings)
    if score is None:
        return None
    start = start % len(sequence) if circular else start
    return {
        "record_id": record_id, "start": start, "end": start + len(primer),
        "strand": strand, "wraps_origin": start + len(primer) > len(sequence),
        **score,
    }


def exhaustive_hits(primers, references, circular, settings):
    """Search every full-length window on both strands within declared bounds."""
    comparisons = sum(
        (len(seq) if record in circular and len(primer) <= len(seq)
         else max(0, len(seq) - len(primer) + 1)) * len(primer) * 2
        for primer in primers for record, seq in references.items()
    )
    if comparisons > settings["max_comparisons"]:
        raise SearchIncomplete(
            f"Exhaustive search requires at most {comparisons:,} base comparisons; "
            f"cap is {settings['max_comparisons']:,}. Increase deliberately or use "
            "the explicitly heuristic BLAST engine. No truncated screen was accepted."
        )
    result = {primer: [] for primer in primers}
    total = 0
    for primer in primers:
        for record, sequence in references.items():
            is_circular = record in circular
            windows = len(sequence) if is_circular else len(sequence) - len(primer) + 1
            if len(primer) > len(sequence):
                continue
            for strand in ("+", "-"):
                for start in range(windows):
                    hit = make_hit(primer, record, sequence, start, strand, is_circular, settings)
                    if hit is not None:
                        total += 1
                        if total > settings["max_hits"]:
                            raise SearchIncomplete("Binding-hit cap exceeded; screen discarded, not truncated")
                        result[primer].append(hit)
    return result, {"base_comparisons_upper_bound": comparisons, "tools": {}}, []


def run_tool(command, timeout):
    try:
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SearchIncomplete(f"{Path(command[0]).name} timed out after {timeout}s") from exc
    except subprocess.CalledProcessError as exc:
        raise SearchIncomplete(
            f"{Path(command[0]).name} failed (exit {exc.returncode}): {exc.stderr[-2000:]}"
        ) from exc
    except OSError as exc:
        raise SearchIncomplete(f"Cannot execute {Path(command[0]).name}: {exc}") from exc
    return completed.stdout.strip()


def blast_hits(primers, references, circular, settings):
    """Use BLAST for candidate discovery, then recheck entire ungapped primers.

    Discovery is heuristic even with unsaturated reporting limits. Both ends of
    clipped HSPs are restored before mismatch counting on the original FASTA.
    Synthetic database IDs prevent pipe/accession conventions from changing IDs.
    """
    if any(len(primer) < 7 for primer in primers):
        raise SearchIncomplete("BLAST's configured 7-base seed requires annealing cores of at least 7 bases")
    program_paths = {}
    for name in ("blastn", "makeblastdb"):
        executable = shutil.which(settings[name])
        if not executable:
            raise SearchIncomplete(f"{name} executable not found: {settings[name]}")
        program_paths[name] = executable
    timeout = settings["blast_timeout"]
    tools = {name: {"executable": path, "version": run_tool([path, "-version"], timeout)}
             for name, path in program_paths.items()}
    primer_map = {f"q{i}": primer for i, primer in enumerate(primers)}
    record_map = {f"r{i}": record for i, record in enumerate(references)}
    hits = {primer: [] for primer in primers}
    seen, target_counts, hsp_counts = set(), defaultdict(set), Counter()
    total_hits, rows, comparisons = 0, 0, 0
    max_length = max(map(len, primers))
    with tempfile.TemporaryDirectory(prefix="primer-specificity-") as temporary:
        temporary = Path(temporary)
        database_fasta, query_fasta = temporary / "reference.fa", temporary / "queries.fa"
        database_path, output = temporary / "reference_db", temporary / "hits.tsv"
        with database_fasta.open("w", encoding="utf-8") as handle:
            for synthetic, record in record_map.items():
                sequence = references[record]
                if record in circular:
                    sequence += sequence[:max_length - 1]
                handle.write(f">{synthetic}\n{sequence}\n")
        with query_fasta.open("w", encoding="utf-8") as handle:
            for query, primer in primer_map.items():
                handle.write(f">{query}\n{primer}\n")
        make_command = [program_paths["makeblastdb"], "-in", str(database_fasta), "-dbtype", "nucl",
                        "-out", str(database_path), "-parse_seqids"]
        blast_command = [
            program_paths["blastn"], "-task", "blastn-short", "-query", str(query_fasta),
            "-db", str(database_path), "-out", str(output), "-strand", "both", "-ungapped",
            "-dust", "no", "-soft_masking", "false", "-word_size", "7", "-evalue", "1000",
            "-max_target_seqs", str(settings["blast_max_target_seqs"]),
            "-max_hsps", str(settings["blast_max_hsps"]),
            "-outfmt", "6 qseqid sseqid qstart qend sstart send gaps",
        ]
        run_tool(make_command, timeout)
        run_tool(blast_command, timeout)
        with output.open(encoding="utf-8") as handle:
            for line in handle:
                rows += 1
                if rows > settings["max_blast_rows"]:
                    raise SearchIncomplete("BLAST output-row cap exceeded; screen discarded")
                fields = line.rstrip("\n").split("\t")
                if len(fields) != 7:
                    raise SearchIncomplete("Unexpected BLAST output format")
                query, subject = fields[:2]
                # BLAST may decorate local identifiers when -parse_seqids is used.
                subject = subject.removeprefix("lcl|")
                if query not in primer_map or subject not in record_map:
                    raise SearchIncomplete("Unrecognized BLAST query/reference identifier")
                qstart, qend, sstart, send, gaps = map(int, fields[2:])
                primer, record = primer_map[query], record_map[subject]
                if gaps or not 1 <= qstart <= qend <= len(primer):
                    raise SearchIncomplete("Unsupported gapped/reversed-query BLAST alignment")
                target_counts[query].add(subject)
                hsp_counts[query, subject] += 1
                strand = "+" if send >= sstart else "-"
                start = sstart - qstart if strand == "+" else sstart + qstart - 1 - len(primer)
                if record in circular:
                    start %= len(references[record])
                key = (primer, record, start, strand)
                if key in seen:
                    continue
                seen.add(key)
                comparisons += len(primer)
                if comparisons > settings["max_comparisons"]:
                    raise SearchIncomplete("BLAST candidate realignment comparison cap exceeded")
                hit = make_hit(primer, record, references[record], start, strand,
                               record in circular, settings)
                if hit is not None:
                    total_hits += 1
                    if total_hits > settings["max_hits"]:
                        raise SearchIncomplete("Binding-hit cap exceeded; screen discarded")
                    hits[primer].append(hit)
        issues = []
        if any(len(records) >= settings["blast_max_target_seqs"] and
               len(records) < len(references) for records in target_counts.values()):
            issues.append("BLAST max_target_seqs reporting limit reached; targets may be omitted")
        if any(count >= settings["blast_max_hsps"] for count in hsp_counts.values()):
            issues.append("BLAST max_hsps reporting limit reached; binding sites may be omitted")
        provenance = {
            "tools": tools, "commands": [make_command, blast_command],
            "blast_rows": rows, "candidate_intervals": len(seen),
            "realignment_base_comparisons": comparisons,
        }
    return hits, provenance, issues


def enumerate_products(pair, hits_by_sequence, references, circular, settings, expected):
    cross_pair = pair.get("cross_pair", False)
    sources = source_oligos(pair)
    hits = []
    for role, key in (("F", "forward"), ("R", "reverse")):
        for hit in sorted(hits_by_sequence[pair[key]],
                          key=lambda h: (h["record_id"], h["start"], h["strand"])):
            hits.append({
                **hit, "primer_role": role, "hit_id": f"{pair['pair_id']}:h{len(hits) + 1}",
                "source_oligo_id": sources[role]["oligo_id"],
                "source_pair_id": sources[role]["pair_id"],
                "source_primer_role": sources[role]["primer_role"],
            })
    by_record = defaultdict(lambda: {"+": [], "-": []})
    for hit in hits:
        by_record[hit["record_id"]][hit["strand"]].append(hit)
    combinations = sum(len(group["+"]) * len(group["-"]) for group in by_record.values())
    if combinations > settings["max_product_combinations"]:
        raise SearchIncomplete(f"Pair {pair['pair_id']}: product-combination cap exceeded")
    products = []
    intended_coordinates = {(item["record_id"], item["start"], item["end"]) for item in expected}
    found_expected = set()
    for record, strands in by_record.items():
        sequence = references[record]
        for plus in strands["+"]:
            for minus in strands["-"]:
                if cross_pair and plus["primer_role"] == minus["primer_role"]:
                    continue  # Single-source-oligo products are already enumerated under its original pair.
                minus_start, end = minus["start"], minus["end"]
                if record in circular and minus_start < plus["end"]:
                    minus_start += len(sequence)
                    end += len(sequence)
                if minus_start < plus["end"]:
                    continue  # Overlapping primer sites are not accepted as PCR products.
                length = end - plus["start"]
                if record in circular and length > len(sequence):
                    continue
                if not settings["min_product"] <= length <= settings["max_product"]:
                    continue
                kind = plus["primer_role"] + "/" + minus["primer_role"]
                coordinates = (record, plus["start"], end)
                intended = not cross_pair and coordinates in intended_coordinates and kind in ("F/R", "R/F")
                if intended:
                    found_expected.add(coordinates)
                classification = "intended" if intended else ("potential_off_target" if expected or cross_pair else "unclassified")
                tails = {"F": pair.get("forward_tail", ""), "R": pair.get("reverse_tail", "")}
                product_sequence = reference_window(sequence, plus["start"], length, record in circular)
                products.append({
                    "product_id": f"{pair['pair_id']}:p{len(products) + 1}",
                    "record_id": record, "start": plus["start"], "end": end,
                    "length": length, "wraps_origin": end > len(sequence),
                    "primer_roles": kind, "left_hit_id": plus["hit_id"], "right_hit_id": minus["hit_id"],
                    "left_source_oligo_id": plus["source_oligo_id"], "right_source_oligo_id": minus["source_oligo_id"],
                    "source_primer_roles": plus["source_primer_role"] + "/" + minus["source_primer_role"],
                    "cross_pair": cross_pair,
                    "classification": classification,
                    "length_with_tails": length + len(tails[plus["primer_role"]]) + len(tails[minus["primer_role"]]),
                    "reference_product_sha256": hashlib.sha256(product_sequence.encode("ascii")).hexdigest(),
                    "unresolved_ambiguity": plus["unresolved_ambiguity"] or minus["unresolved_ambiguity"],
                })
                if len(products) > settings["max_products"]:
                    raise SearchIncomplete(f"Pair {pair['pair_id']}: product cap exceeded; screen discarded")
    missing = [item for item in expected if (item["record_id"], item["start"], item["end"]) not in found_expected]
    if cross_pair:
        status = "potential_off_target" if products else "no_off_target_found_within_search_scope"
    elif not expected:
        status = "no_expected_target"
    elif missing:
        status = "intended_target_not_found"
    elif any(item["classification"] == "potential_off_target" for item in products):
        status = "potential_off_target"
    else:
        status = "no_off_target_found_within_search_scope"
    unresolved = any(h["unresolved_ambiguity"] for h in hits)
    return {
        "pair_id": pair["pair_id"], "status": status,
        "cross_pair": cross_pair, "source_oligos": sources,
        "hit_count": len(hits), "product_count": len(products), "hits": hits,
        "products": products, "expected": expected, "missing_expected": missing,
        "potential_off_target_count": sum(p["classification"] == "potential_off_target" for p in products),
        "unresolved_ambiguity": unresolved,
        "product_combinations_checked": combinations,
        **({"status_before_incomplete": status, "status": "incomplete"} if unresolved else {}),
    }
