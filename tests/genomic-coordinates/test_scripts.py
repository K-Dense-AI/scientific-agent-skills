"""Unit tests for the genomic-coordinates skill scripts.

Everything runs offline against the fixtures in ``fixtures/``. The reference
FASTA is ten bases long and deliberately contains a ``CACACAC`` repeat, which is
what makes the left-alignment cases interesting.

    uv run --with pytest python -m pytest tests/genomic-coordinates -q
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "genomic-coordinates"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_script(name: str):
    """Load a bundled script as a module regardless of cwd."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = _load_script("_common")
convert_coords = _load_script("convert_coords")
normalize_variant = _load_script("normalize_variant")
check_contigs = _load_script("check_contigs")
audit_intervals = _load_script("audit_intervals")


def run_main(module, argv):
    """Invoke a script's main() and capture (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module.main(argv)
    return code, out.getvalue(), err.getvalue()


def rows_from_tsv(text):
    lines = [line for line in text.strip().splitlines() if line]
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:]]


# ---------------------------------------------------------------------------
# coordinate conversion
# ---------------------------------------------------------------------------


class ConventionTests(unittest.TestCase):
    def test_round_trip_through_canonical_is_identity(self):
        for name, conv in common.CONVENTIONS.items():
            with self.subTest(format=name):
                start, end = (10, 20) if conv.half_open else (11, 20)
                canonical = common.to_canonical(conv, start, end)
                self.assertEqual(common.from_canonical(conv, *canonical), (start, end))

    def test_only_the_start_moves_between_conventions(self):
        bed = common.get_convention("bed")
        gff = common.get_convention("gff")
        start, end = common.from_canonical(gff, *common.to_canonical(bed, 999, 1000))
        self.assertEqual((start, end), (1000, 1000))

    def test_length_is_convention_independent(self):
        bed = common.to_canonical(common.get_convention("bed"), 999, 1000)
        gff = common.to_canonical(common.get_convention("gff"), 1000, 1000)
        self.assertEqual(bed, gff)
        self.assertEqual(bed[1] - bed[0], 1)

    def test_samtools_region_spans_both_endpoints(self):
        # The samtools manual: chr3:1000-2000 is a 1001 bp region.
        conv = common.get_convention("samtools")
        contig, start, end, _ = common.parse_region("chr3:1000-2000", conv)
        start0, end0 = common.to_canonical(conv, start, end)
        self.assertEqual(contig, "chr3")
        self.assertEqual(end0 - start0, 1001)

    def test_unknown_format_is_rejected(self):
        with self.assertRaises(ValueError):
            common.get_convention("bed12ish")


class RegionStringTests(unittest.TestCase):
    def test_thousands_separators_are_accepted(self):
        conv = common.get_convention("ucsc")
        self.assertEqual(
            common.parse_region("chr7:5,530,601-5,530,625", conv)[1:3],
            (5530601, 5530625),
        )

    def test_ensembl_double_dot_and_strand(self):
        conv = common.get_convention("ensembl")
        contig, start, end, strand = common.parse_region("1:100..200:-", conv)
        self.assertEqual((contig, start, end, strand), ("1", 100, 200, "-"))

    def test_start_without_end_is_refused(self):
        # In samtools, chr2:1000000 runs to the end of the contig -- not one base.
        with self.assertRaises(ValueError) as caught:
            common.parse_region("chr2:1000000", common.get_convention("samtools"))
        self.assertIn("end of the contig", str(caught.exception))

    def test_bare_contig_is_refused(self):
        with self.assertRaises(ValueError):
            common.parse_region("chr2", common.get_convention("samtools"))

    def test_braced_hla_contig_round_trips(self):
        conv = common.get_convention("samtools")
        contig, start, end, _ = common.parse_region("{HLA-DRB1*12:17}:100-200", conv)
        self.assertEqual(contig, "HLA-DRB1*12:17")
        self.assertEqual(
            common.format_region(contig, start, end), "{HLA-DRB1*12:17}:100-200"
        )

    def test_unbraced_colon_bearing_name_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            common.parse_region(
                "HLA-DRB1*12:17:100-200", common.get_convention("samtools")
            )
        self.assertIn("ambiguous", str(caught.exception))


class ConvertCoordsCliTests(unittest.TestCase):
    def test_bed_to_gff(self):
        code, out, _ = run_main(convert_coords, ["--from", "bed", "--to", "gff",
                                                 "chr1", "999", "1000"])
        self.assertEqual(code, 0)
        row = rows_from_tsv(out)[0]
        self.assertEqual(row["output"], "1000-1000")
        self.assertEqual(row["length"], "1")

    def test_ucsc_region_to_bed(self):
        code, out, _ = run_main(
            convert_coords,
            ["--from", "ucsc", "--to", "bed", "chr7:5,530,601-5,530,625"],
        )
        self.assertEqual(code, 0)
        row = rows_from_tsv(out)[0]
        self.assertEqual(row["output"], "5530600-5530625")
        self.assertEqual(row["length"], "25")

    def test_zero_length_bed_feature_is_unrepresentable_in_gff(self):
        code, out, _ = run_main(convert_coords, ["--from", "bed", "--to", "gff",
                                                 "chr1", "500", "500"])
        self.assertEqual(code, 1)
        row = rows_from_tsv(out)[0]
        self.assertEqual(row["status"], "unrepresentable")

    def test_zero_length_survives_a_half_open_target(self):
        code, out, _ = run_main(convert_coords, ["--from", "bed", "--to", "pyranges",
                                                 "chr1", "500", "500"])
        self.assertEqual(code, 0)
        self.assertEqual(rows_from_tsv(out)[0]["status"], "zero_length")

    def test_inverted_interval_is_invalid(self):
        code, out, _ = run_main(convert_coords, ["--from", "gff", "--to", "bed",
                                                 "chr1", "200", "100"])
        self.assertEqual(code, 1)
        self.assertEqual(rows_from_tsv(out)[0]["status"], "invalid")

    def test_list_covers_every_convention(self):
        code, out, _ = run_main(convert_coords, ["--list"])
        self.assertEqual(code, 0)
        for name in common.CONVENTIONS:
            self.assertIn(name, out)

    def test_json_output_is_parseable(self):
        _, out, _ = run_main(convert_coords, ["--from", "bed", "--to", "gff",
                                              "chr1", "0", "10", "--format", "json"])
        self.assertEqual(json.loads(out)[0]["length"], 10)

    def test_reads_a_bed_file(self):
        code, out, _ = run_main(
            convert_coords,
            ["--from", "bed", "--to", "gff", "--input", str(FIXTURES / "clean.bed")],
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(rows_from_tsv(out)), 3)


# ---------------------------------------------------------------------------
# variant normalisation
# ---------------------------------------------------------------------------


REF_FASTA = FIXTURES / "tiny.fa"


class ReferenceTests(unittest.TestCase):
    def test_fetch_is_zero_based_half_open(self):
        reference = common.Reference(REF_FASTA)
        # GGCACACACT
        self.assertEqual(reference.fetch("chr1", 0, 2), "GG")
        self.assertEqual(reference.fetch("chr1", 9, 10), "T")
        self.assertEqual(reference.length("chr1"), 10)

    def test_reference_requires_exact_contig_names(self):
        reference = common.Reference(REF_FASTA)
        with self.assertRaises(common.ReferenceError):
            reference.fetch("1", 0, 2)

    def test_past_the_end_is_an_error_naming_the_assembly(self):
        reference = common.Reference(REF_FASTA)
        with self.assertRaises(common.ReferenceError) as caught:
            reference.fetch("chr1", 5, 40)
        self.assertIn("assembly", str(caught.exception))

    def test_missing_contig_names_the_likely_cause(self):
        reference = common.Reference(REF_FASTA)
        with self.assertRaises(common.ReferenceError) as caught:
            reference.fetch("chr22", 0, 1)
        self.assertIn("check_contigs", str(caught.exception))

    def test_indexed_and_unindexed_readers_agree(self):
        """A .fai must give the same bases as reading the FASTA sequentially."""
        with tempfile.TemporaryDirectory() as temporary:
            fasta = Path(temporary) / "wrapped.fa"
            sequence = "ACGT" * 25
            fasta.write_text(
                ">chr1\n" + "\n".join(sequence[i:i + 10] for i in range(0, 100, 10)) + "\n"
            )
            plain = common.Reference(fasta)
            # offset of the first base = len(">chr1\n") = 6; 10 bases per line, 11 wide
            Path(str(fasta) + ".fai").write_text("chr1\t100\t6\t10\t11\n")
            indexed = common.Reference(fasta)
            for start, end in [(0, 4), (8, 15), (0, 100), (95, 100), (37, 38)]:
                self.assertEqual(
                    indexed.fetch("chr1", start, end),
                    plain.fetch("chr1", start, end),
                    f"disagreement on [{start}, {end})",
                )


class NormalisationTests(unittest.TestCase):
    """Reference is GGCACACACT -- a CACACAC repeat at positions 3-9."""

    def setUp(self):
        self.reference = common.Reference(REF_FASTA)

    def normalise(self, pos, ref, alt, **kwargs):
        return normalize_variant.normalize(
            self.reference, "chr1", pos, ref, alt, **kwargs
        )

    def test_deletion_left_aligns_through_the_repeat(self):
        result = self.normalise(7, "CAC", "C")
        self.assertEqual((result["pos"], result["ref"], result["alt"]), (2, "GCA", "G"))
        self.assertEqual(result["shifted"], 5)
        self.assertEqual(result["type"], "deletion")

    def test_every_spelling_of_one_deletion_agrees(self):
        forms = [(7, "CAC", "C"), (5, "CAC", "C"), (3, "CAC", "C"), (2, "GCA", "G")]
        results = {
            (r["pos"], r["ref"], r["alt"])
            for r in (self.normalise(*form) for form in forms)
        }
        self.assertEqual(results, {(2, "GCA", "G")})

    def test_insertion_left_aligns(self):
        result = self.normalise(9, "C", "CAC")
        self.assertEqual((result["pos"], result["ref"], result["alt"]), (2, "G", "GCA"))
        self.assertEqual(result["type"], "insertion")

    def test_untrimmed_snv_becomes_parsimonious(self):
        result = self.normalise(3, "CA", "CT")
        self.assertEqual((result["pos"], result["ref"], result["alt"]), (4, "A", "T"))
        self.assertEqual(result["type"], "snv")
        self.assertEqual(result["shifted"], -1)

    def test_normalised_snv_is_untouched(self):
        result = self.normalise(3, "C", "A")
        self.assertEqual((result["pos"], result["ref"], result["alt"]), (3, "C", "A"))
        self.assertEqual(result["shifted"], 0)

    def test_normalisation_is_idempotent(self):
        once = self.normalise(7, "CAC", "C")
        twice = self.normalise(once["pos"], once["ref"], once["alt"])
        self.assertEqual(
            (once["pos"], once["ref"], once["alt"]),
            (twice["pos"], twice["ref"], twice["alt"]),
        )

    def test_cannot_shift_past_the_contig_start(self):
        result = self.normalise(1, "G", "GAC")
        self.assertEqual(result["pos"], 1)
        self.assertEqual(result["ref_check"], "ok")

    def test_window_limits_the_shift_and_says_so(self):
        result = self.normalise(7, "CAC", "C", window=2)
        self.assertLessEqual(result["shifted"], 2)
        self.assertIn("window", result["detail"])

    def test_ref_mismatch_is_reported_not_normalised(self):
        result = self.normalise(3, "A", "T")
        self.assertEqual(result["ref_check"], "MISMATCH")
        self.assertEqual(result["shifted"], 0)
        self.assertIn("assembl", result["detail"])

    def test_symbolic_allele_passes_through(self):
        result = self.normalise(7, "CAC", "<DEL>")
        self.assertEqual(result["type"], "symbolic")
        self.assertEqual(result["ref_check"], "skipped")
        self.assertEqual(result["pos"], 7)

    def test_spanning_deletion_allele_passes_through(self):
        self.assertEqual(self.normalise(7, "C", "*")["type"], "symbolic")

    def test_ref_equal_to_alt_is_rejected(self):
        with self.assertRaises(normalize_variant.VariantError):
            self.normalise(3, "C", "C")

    def test_zero_position_is_rejected(self):
        with self.assertRaises(normalize_variant.VariantError):
            self.normalise(0, "C", "A")


class NormaliseCliTests(unittest.TestCase):
    def test_compare_declares_identity(self):
        code, out, err = run_main(
            normalize_variant,
            ["--fasta", str(REF_FASTA), "--compare", "chr1:7:CAC:C", "chr1:2:GCA:G"],
        )
        self.assertEqual(code, 0)
        self.assertIn("identical", err)
        self.assertEqual(len(rows_from_tsv(out)), 2)

    def test_compare_declares_difference(self):
        code, _, err = run_main(
            normalize_variant,
            ["--fasta", str(REF_FASTA), "--compare", "chr1:7:CAC:C", "chr1:3:C:A"],
        )
        self.assertEqual(code, 0)
        self.assertIn("distinct", err)

    def test_mismatch_sets_a_failing_exit_code(self):
        code, out, _ = run_main(
            normalize_variant, ["--fasta", str(REF_FASTA), "chr1", "3", "A", "T"]
        )
        self.assertEqual(code, 1)
        self.assertEqual(rows_from_tsv(out)[0]["ref_check"], "MISMATCH")

    def test_split_expands_multiallelic_alt(self):
        code, out, _ = run_main(
            normalize_variant,
            ["--fasta", str(REF_FASTA), "--split", "chr1", "7", "CAC", "C,CACAC"],
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(rows_from_tsv(out)), 2)

    def test_reads_a_vcf(self):
        code, out, _ = run_main(
            normalize_variant,
            ["--fasta", str(REF_FASTA), "--input", str(FIXTURES / "tiny.vcf")],
        )
        rows = rows_from_tsv(out)
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["normalized"], "chr1:2:GCA:G")

    def test_missing_reference_is_a_usage_error(self):
        code, _, err = run_main(
            normalize_variant, ["--fasta", "/nonexistent.fa", "chr1", "1", "G", "A"]
        )
        self.assertEqual(code, 2)
        self.assertIn("not found", err)


# ---------------------------------------------------------------------------
# assembly identification
# ---------------------------------------------------------------------------


class BuildTableTests(unittest.TestCase):
    def test_every_build_lists_the_same_chromosomes(self):
        keys = [set(lengths) for lengths in check_contigs.BUILDS.values()]
        self.assertTrue(all(k == keys[0] for k in keys))
        self.assertEqual(len(keys[0]), 24)

    def test_builds_are_mutually_distinguishable(self):
        """No two assemblies may share a full primary-chromosome signature."""
        signatures = {
            build: tuple(sorted(lengths.items()))
            for build, lengths in check_contigs.BUILDS.items()
        }
        self.assertEqual(len(set(signatures.values())), len(signatures))

    def test_grch37_and_grch38_differ_on_chr1(self):
        self.assertNotEqual(
            check_contigs.BUILDS["GRCh37/hg19"]["1"],
            check_contigs.BUILDS["GRCh38/hg38"]["1"],
        )


class IdentifyTests(unittest.TestCase):
    def test_hg19_is_identified_by_its_mitochondrion(self):
        code, out, _ = run_main(
            check_contigs, ["--identify", str(FIXTURES / "hg19.chrom.sizes")]
        )
        row = rows_from_tsv(out)[0]
        self.assertEqual(code, 0)
        self.assertEqual(row["assembly"], "hg19")
        self.assertIn("16571", row["detail"])
        self.assertEqual(row["naming"], "chr-prefixed")

    def test_grch37_is_identified_by_its_mitochondrion(self):
        _, out, _ = run_main(
            check_contigs, ["--identify", str(FIXTURES / "GRCh37.fa.fai")]
        )
        row = rows_from_tsv(out)[0]
        self.assertEqual(row["assembly"], "GRCh37")
        self.assertEqual(row["naming"], "plain")

    def test_grch38_is_identified(self):
        _, out, _ = run_main(
            check_contigs, ["--identify", str(FIXTURES / "hg38.chrom.sizes")]
        )
        self.assertEqual(rows_from_tsv(out)[0]["assembly"], "GRCh38/hg38")

    def test_grch37_and_hg19_are_reported_as_incompatible(self):
        code, _, err = run_main(
            check_contigs,
            [str(FIXTURES / "GRCh37.fa.fai"), str(FIXTURES / "hg19.chrom.sizes")],
        )
        self.assertEqual(code, 1)
        self.assertIn("naming differs", err)
        self.assertIn("16569", err)

    def test_matching_files_are_compatible(self):
        code, _, err = run_main(
            check_contigs,
            [str(FIXTURES / "hg19.chrom.sizes"), str(FIXTURES / "hg19.chrom.sizes")],
        )
        self.assertEqual(code, 0)
        self.assertIn("no contig incompatibilities", err)

    def test_vcf_header_lengths_are_read(self):
        _, out, _ = run_main(
            check_contigs, ["--identify", str(FIXTURES / "grch38.vcf")]
        )
        row = rows_from_tsv(out)[0]
        self.assertEqual(row["kind"], "vcf header")
        self.assertEqual(row["assembly"], "GRCh38/hg38")

    def test_grch38_vcf_against_hg19_genome_fails(self):
        code, _, err = run_main(
            check_contigs,
            [str(FIXTURES / "grch38.vcf"), "--genome", str(FIXTURES / "hg19.chrom.sizes")],
        )
        self.assertEqual(code, 1)
        self.assertIn("different assemblies", err)

    def test_bed_max_coordinate_is_not_treated_as_a_contig_length(self):
        """A BED whose features are well inside the contigs must not look like a
        length conflict just because the numbers are smaller."""
        code, _, err = run_main(
            check_contigs,
            [str(FIXTURES / "clean.bed"), "--genome", str(FIXTURES / "hg19.chrom.sizes")],
        )
        self.assertEqual(code, 0)
        self.assertIn("no contig incompatibilities", err)

    def test_bed_past_the_contig_end_is_caught(self):
        code, _, err = run_main(
            check_contigs,
            [str(FIXTURES / "overflow.bed"), "--genome", str(FIXTURES / "hg19.chrom.sizes")],
        )
        self.assertEqual(code, 1)
        self.assertIn("past the end", err)

    def test_unknown_extension_is_refused(self):
        with self.assertRaises(SystemExit):
            run_main(check_contigs, [str(FIXTURES / "readme.txt")])


# ---------------------------------------------------------------------------
# file auditing
# ---------------------------------------------------------------------------


class AuditBedTests(unittest.TestCase):
    def test_clean_bed_has_no_findings(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "clean.bed")])
        self.assertEqual(code, 0)
        self.assertIn("no findings", out)

    def test_one_based_data_in_a_bed_is_flagged(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "onebased.bed")])
        rules = {row["rule"] for row in rows_from_tsv(out)}
        self.assertIn("many_zero_length", rules)

    def test_bed12_absolute_block_starts_are_fatal(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "bad_blocks.bed")])
        self.assertEqual(code, 1)
        self.assertIn("first_block_offset", {r["rule"] for r in rows_from_tsv(out)})

    def test_valid_bed12_passes(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "valid12.bed")])
        self.assertEqual(code, 0)
        self.assertIn("no findings", out)

    def test_space_separated_bed_is_named_as_such(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "spaced.bed")])
        self.assertEqual(code, 1)
        rules = {row["rule"] for row in rows_from_tsv(out)}
        self.assertIn("space_separated", rules)
        self.assertNotIn("too_few_columns", rules)


class AuditGffTests(unittest.TestCase):
    def test_zero_start_proves_zero_based_data(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "bad.gtf")])
        self.assertEqual(code, 1)
        rows = {row["rule"]: row for row in rows_from_tsv(out)}
        self.assertIn("start_below_one", rows)
        self.assertIn("1-based", rows["start_below_one"]["detail"])

    def test_end_before_start_is_fatal_regardless_of_strand(self):
        _, out, _ = run_main(audit_intervals, [str(FIXTURES / "bad.gtf")])
        self.assertIn("end_before_start", {r["rule"] for r in rows_from_tsv(out)})

    def test_clean_gtf_passes(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "clean.gtf")])
        self.assertEqual(code, 0)
        self.assertIn("no findings", out)


class AuditVcfTests(unittest.TestCase):
    def test_vep_dash_allele_is_fatal(self):
        code, out, _ = run_main(audit_intervals, [str(FIXTURES / "messy.vcf")])
        self.assertEqual(code, 1)
        rows = {row["rule"] for row in rows_from_tsv(out)}
        self.assertIn("bad_alt_allele", rows)
        self.assertIn("pos_below_one", rows)
        self.assertIn("mixed_contig_naming", rows)

    def test_untrimmed_alleles_are_warned_about(self):
        _, out, _ = run_main(audit_intervals, [str(FIXTURES / "messy.vcf")])
        rows = {row["rule"]: row for row in rows_from_tsv(out)}
        self.assertEqual(rows["not_parsimonious"]["severity"], "warn")

    def test_contig_order_not_coordinate_order_drives_the_sort_check(self):
        """Moving to a new contig is not 'unsorted'; revisiting one is."""
        _, out, _ = run_main(audit_intervals, [str(FIXTURES / "clean.vcf")])
        rules = {row["rule"] for row in rows_from_tsv(out)}
        self.assertNotIn("unsorted", rules)
        self.assertNotIn("interleaved_contigs", rules)

    def test_interleaved_contigs_are_caught(self):
        _, out, _ = run_main(audit_intervals, [str(FIXTURES / "interleaved.vcf")])
        self.assertIn("interleaved_contigs", {r["rule"] for r in rows_from_tsv(out)})


class AuditCliTests(unittest.TestCase):
    def test_format_can_be_forced(self):
        code, out, _ = run_main(
            audit_intervals, [str(FIXTURES / "clean.bed"), "--format", "bed"]
        )
        self.assertEqual(code, 0)

    def test_unknown_extension_is_refused(self):
        with self.assertRaises(SystemExit):
            run_main(audit_intervals, [str(FIXTURES / "tiny.fa")])

    def test_missing_file_is_a_usage_error(self):
        code, _, err = run_main(audit_intervals, ["/nonexistent.bed"])
        self.assertEqual(code, 2)
        self.assertIn("no such file", err)

    def test_examples_are_capped(self):
        code, out, _ = run_main(
            audit_intervals, [str(FIXTURES / "many_bad.gtf"), "--max-examples", "2"]
        )
        rows = [r for r in rows_from_tsv(out) if r["rule"] == "start_below_one"]
        self.assertEqual(len(rows), 3)  # two examples plus the suppression notice
        self.assertEqual(rows[-1]["line"], "...")

    def test_suppressed_findings_still_count_towards_the_exit_code(self):
        code, _, err = run_main(
            audit_intervals, [str(FIXTURES / "many_bad.gtf"), "--max-examples", "1"]
        )
        self.assertEqual(code, 1)
        self.assertIn("10 fatal", err)


class BoundaryRegressionTests(unittest.TestCase):
    def test_invalid_origins_and_inverted_inclusive_intervals(self):
        for src, start, end in [("bed", -1, 10), ("gff", 0, 2), ("gff", 2, 1)]:
            with self.subTest(src=src, start=start, end=end):
                code, out, _ = run_main(convert_coords, ["--from", src, "--to", "bed",
                                                         "chr1", str(start), str(end)])
                self.assertEqual(code, 1)
                self.assertEqual(rows_from_tsv(out)[0]["output"], "")

    def test_ensembl_numeric_strand_roundtrip(self):
        code, out, _ = run_main(convert_coords, ["--from", "ensembl", "--to", "ensembl",
                                                 "X:1000000..1000100:-1"])
        self.assertEqual(code, 0)
        self.assertEqual(rows_from_tsv(out)[0]["output"], "X:1000000..1000100:-1")

    def test_unimplemented_native_file_reader_is_rejected(self):
        with self.assertRaises(SystemExit):
            convert_coords.read_intervals(str(FIXTURES / "clean.bed"), common.get_convention("sam"))

    def test_colon_in_bed_name_is_not_a_region_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "name.bed"
            path.write_text("HLA-DRB1*12:17\t0\t10\n")
            self.assertEqual(convert_coords.read_intervals(str(path), common.get_convention("bed"))[0],
                             ("HLA-DRB1*12:17", 0, 10, None))

    def test_structural_vcf_is_not_converted_to_anchor_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sv.vcf"
            path.write_text("chr1\t3\t.\tC\t<DEL>\t.\t.\tEND=9\n")
            with self.assertRaises(SystemExit):
                convert_coords.read_intervals(str(path), common.get_convention("vcf"))

    def test_literal_alleles_reject_unsplit_empty_and_invalid(self):
        ref = common.Reference(REF_FASTA)
        for alt in ["A,T", "", "-", "Z", "*garbage", "<DEL"]:
            with self.subTest(alt=alt), self.assertRaises(normalize_variant.VariantError):
                normalize_variant.normalize(ref, "chr1", 3, "C", alt)

    def test_breakends_are_skipped_without_changing_case(self):
        ref = common.Reference(REF_FASTA)
        for alt in ["C[chr2:10[", "]chr2:10]C", "C.", ".C"]:
            with self.subTest(alt=alt):
                result = normalize_variant.normalize(ref, "chr1", 3, "C", alt)
                self.assertEqual(result["alt"], alt)
                self.assertEqual(result["ref_check"], "skipped")

    def test_limited_normalization_cannot_claim_equivalence(self):
        code, out, err = run_main(normalize_variant, ["--fasta", str(REF_FASTA), "--window", "2",
            "--compare", "chr1:7:CAC:C", "chr1:2:GCA:G"])
        self.assertEqual(code, 1)
        self.assertIn("incomplete", out)
        self.assertIn("cannot compare", err)

    def test_real_contig_start_does_not_claim_window_exhaustion(self):
        result = normalize_variant.normalize(common.Reference(REF_FASTA), "chr1", 2, "G", "GG")
        self.assertEqual(result["pos"], 1)
        self.assertEqual(result["ref_check"], "ok")
        self.assertEqual(result["detail"], "")

    def test_right_padded_contig_start_variant(self):
        result = normalize_variant.normalize(common.Reference(REF_FASTA), "chr1", 1, "GG", "G")
        self.assertEqual((result["pos"], result["ref"], result["alt"]), (1, "GG", "G"))

    def test_window_must_be_positive(self):
        with self.assertRaises(SystemExit):
            run_main(normalize_variant, ["--fasta", str(REF_FASTA), "--window", "0", "chr1", "3", "C", "A"])

    def test_colon_contig_variant_spec(self):
        self.assertEqual(normalize_variant.parse_spec("HLA-DRB1*12:17:3:C:A"),
                         ("HLA-DRB1*12:17", 3, "C", "A"))

    def test_duplicate_fasta_and_bad_index_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ref.fa"
            path.write_text(">chr1\nACGT\n>chr1\nTGCA\n")
            with self.assertRaises(common.ReferenceError):
                common.Reference(path)
            path.write_text(">chr1\nACGT\n")
            Path(str(path) + ".fai").write_text("chr1\t4\t6\t0\t5\n")
            with self.assertRaises(common.ReferenceError):
                common.Reference(path)

    def test_narrowpeak_signal_columns_are_not_thick_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "peaks.narrowPeak"
            path.write_text("chr1\t10\t20\tp\t100\t.\t2.5\t3.2\t1.5\t4\n")
            code, out, _ = run_main(audit_intervals, [str(path)])
            self.assertEqual(code, 0, out)
            path.write_text("chr1\t10\t20\tp\t100\t.\t2.5\t3.2\t1.5\t10\n")
            self.assertEqual(run_main(audit_intervals, [str(path)])[0], 1)

    def test_embedded_gff_fasta_is_not_read_as_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ref.gff3"
            path.write_text("##gff-version 3\nchr1\tx\tgene\t1\t10\t.\t+\t.\tID=g\n##FASTA\n>chr1\nACGT\n")
            self.assertEqual(run_main(audit_intervals, [str(path)])[0], 0)
            self.assertEqual(len(convert_coords.read_intervals(str(path), common.get_convention("gff3"))), 1)

    def test_circular_gff_overflow_is_not_declared_wrong_assembly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "circular.gff3"
            path.write_text("chr1\tx\tregion\t1\t100\t.\t+\t.\tID=r;Is_circular=true\nchr1\tx\tgene\t90\t120\t.\t+\t.\tID=g\n")
            findings = audit_intervals.Findings(5)
            audit_intervals.audit_gff(path, findings, {"1": 100}, "gff3")
            self.assertEqual(findings.fatal, 0)
            self.assertIn("circular_extent_unchecked", findings.counts)

    def test_bed12_rejects_overlapping_and_negative_blocks(self):
        for sizes, offsets in [("60,50", "0,50"), ("-1,50", "0,50")]:
            fields = ["chr1", "0", "100", "x", "0", "+", "0", "100", "0", "2", sizes, offsets]
            findings = audit_intervals.Findings(5)
            audit_intervals.audit_bed12(findings, 1, fields, 0, 100)
            self.assertIn("bad_block_geometry", findings.counts)

    def test_partial_vcf_header_does_not_hide_bad_record_contigs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partial.vcf"
            path.write_text("##contig=<ID=chr1,length=10>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchr2\t1\t.\tA\tC\t.\t.\t.\n")
            code, _, err = run_main(check_contigs, [str(path)])
            self.assertEqual(code, 1)
            self.assertIn("share no contigs", err)
            with path.open("a") as handle:
                handle.write("chr1\t1\t.\tA\tC\t.\t.\t.\n")
            code, _, err = run_main(check_contigs, [str(path)])
            self.assertEqual(code, 1)
            self.assertIn("absent", err)

    def test_vcf_reference_span_checked_even_with_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "overflow.vcf"
            path.write_text("##contig=<ID=chr1,length=10>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchr1\t9\t.\tAAA\tA\t.\t.\t.\n")
            code, _, err = run_main(check_contigs, [str(path)])
            self.assertEqual(code, 1)
            self.assertIn("past the end", err)

    def test_missing_observed_contig_detected_in_either_file_order(self):
        left = (Path("data.bed"), {"chr1": 5, "chr2": 5}, "intervals", False)
        right = (Path("ref.fai"), {"chr1": 10}, "sizes", True)
        for files in [[left, right], [right, left]]:
            self.assertTrue(any("absent" in p for p in check_contigs.compare(files)))

    def test_primary_length_outlier_not_accepted_as_same_build(self):
        sizes = dict(check_contigs.BUILDS["GRCh38/hg38"])
        sizes["1"] -= 1
        self.assertEqual(check_contigs.identify(sizes, True)[0], "CONFLICT")

    def test_mitochondrial_alias_mismatch_is_detected(self):
        problems = check_contigs.compare([(Path("a"), {"MT": 16569}, "sizes", True),
                                         (Path("b"), {"M": 16569}, "sizes", True)])
        self.assertTrue(any("exact names" in p for p in problems))

    def test_custom_reference_naming_style_does_not_invalidate_matching_subset(self):
        self.assertEqual(check_contigs.compare([
            (Path("regions.bed"), {"chr1": 5}, "intervals", False),
            (Path("custom.fai"), {"chr1": 10, "spikein": 100}, "sizes", True),
        ]), [])

    def test_ambiguous_left_extension_cannot_create_non_vcf_allele(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ambiguous.fa"
            path.write_text(">chr1\nRCCC\n")
            with self.assertRaises(normalize_variant.VariantError):
                normalize_variant.normalize(common.Reference(path), "chr1", 3, "CC", "C")


# ---------------------------------------------------------------------------
# skill structure
# ---------------------------------------------------------------------------


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_name_matches_the_directory(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"^---\nname: genomic-coordinates\n")

    def test_version_is_a_quoted_string(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r'\n  version: "\d+\.\d+"\n')

    def test_skill_md_is_within_the_line_budget(self):
        lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
        self.assertLess(len(lines), 500)

    def test_no_tests_ship_inside_the_skill(self):
        self.assertEqual(list(SKILL_ROOT.rglob("test_*.py")), [])
        self.assertEqual(list(SKILL_ROOT.rglob("*.pyc")), [])

    def test_local_markdown_links_resolve(self):
        pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        docs = [SKILL_ROOT / "SKILL.md", *sorted((SKILL_ROOT / "references").glob("*.md"))]
        for path in docs:
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                with self.subTest(doc=path.name, target=target):
                    self.assertTrue((path.parent / target.split("#")[0]).exists())

    def test_every_referenced_file_exists(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in re.findall(r"`(references/[\w.-]+|scripts/[\w.-]+)`", text):
            with self.subTest(path=name):
                self.assertTrue((SKILL_ROOT / name).exists())

    def test_every_script_is_mentioned_in_the_skill(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for script in SCRIPTS_DIR.glob("*.py"):
            if script.name.startswith("_"):
                continue
            with self.subTest(script=script.name):
                self.assertIn(script.name, text)

    def test_scripts_import_nothing_outside_the_standard_library(self):
        third_party = {"numpy", "pandas", "pysam", "requests", "scipy", "yaml"}
        for script in SCRIPTS_DIR.glob("*.py"):
            text = script.read_text(encoding="utf-8")
            for module in re.findall(r"^\s*(?:import|from)\s+([\w.]+)", text, re.M):
                with self.subTest(script=script.name, module=module):
                    self.assertNotIn(module.split(".")[0], third_party)


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
