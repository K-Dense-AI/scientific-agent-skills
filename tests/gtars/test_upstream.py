"""Small, offline scientific contracts for the documented gtars wheel."""

from __future__ import annotations

import gzip
import tempfile
import unittest
from pathlib import Path

try:
    import gtars
    from gtars.genomic_distributions import consensus
    from gtars.models import Region, RegionSet
    from gtars.refget import RefgetStore, digest_sequence, md5_digest, sha512t24u_digest
    from gtars.tokenizers import Tokenizer, tokenize_fragment_file
except ImportError:
    gtars = None


@unittest.skipIf(gtars is None, "gtars is absent; run the isolated skill suite")
class UpstreamContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def test_half_open_overlap_and_merged_base_metrics(self):
        a = RegionSet.from_vectors(["chr1", "chr1"], [0, 8], [10, 20])
        b = RegionSet.from_regions([Region("chr1", 5, 15, None)])
        adjacent = RegionSet.from_vectors(["chr1"], [20], [30])
        self.assertEqual(a.count_overlaps(b), [1, 1])
        self.assertEqual(a.find_overlaps(b), [[0], [0]])
        self.assertEqual(a.any_overlaps(adjacent), [False, False])
        self.assertEqual([(r.start, r.end) for r in a.union(adjacent)], [(0, 30)])
        self.assertAlmostEqual(a.coverage(b), 0.5)
        self.assertAlmostEqual(a.jaccard(b), 0.5)
        self.assertAlmostEqual(a.overlap_coefficient(b), 1.0)
        self.assertEqual([(r.start, r.end) for r in a.setdiff(b)], [(0, 5), (15, 20)])
        self.assertEqual(consensus([a, b]), [dict(chr="chr1", start=0, end=20, count=2)])

    def test_file_sorting_preserves_rest_but_not_bed6_strand_vector(self):
        bed = self.root / "input.bed"
        bed.write_text("chr2\t10\t20\ta\t0\t-\nchr1\t0\t10\tb\t0\t+\n")
        regions = RegionSet(str(bed))
        self.assertEqual([(r.chr, r.rest) for r in regions],
                         [("chr1", "b\t0\t+"), ("chr2", "a\t0\t-")])
        self.assertEqual(regions.strands, ["*", "*"])
        self.assertEqual(len(regions[0]), 10)
        self.assertEqual(Region("chr1", 0, 10, None), Region("chr1", 0, 10, "name"))
        out = self.root / "roundtrip.bed.gz"
        regions.to_bed_gz(str(out))
        self.assertEqual(len(RegionSet(str(out))), 2)

    def test_sort_does_not_realign_separate_strands_in_documented_release(self):
        regions = RegionSet.from_vectors(["chr1", "chr1"], [20, 0], [30, 10], ["-", "+"])
        self.assertIsNone(regions.sort())
        self.assertEqual([r.start for r in regions], [0, 20])
        self.assertEqual(regions.strands, ["-", "+"])

    def test_pairwise_intersection_truncates_and_keeps_zero_width_misses(self):
        a = RegionSet.from_vectors(["chr1", "chr1"], [0, 20], [10, 30])
        b = RegionSet.from_vectors(["chr2"], [5], [15])
        result = a.pintersect(b)
        self.assertEqual([(r.chr, r.start, r.end) for r in result], [("chr1", 0, 0)])

    def test_tokenizer_preserves_universe_ids_and_drops_partial_misses(self):
        bed = self.root / "universe.bed"
        bed.write_text("chr1\t20\t30\nchr1\t0\t10\n")
        tokenizer = Tokenizer.from_bed(str(bed))
        self.assertEqual(tokenizer.vocab_size, 9)
        self.assertEqual(tokenizer.convert_tokens_to_ids(["chr1:20-30", "chr1:0-10"]), [0, 1])
        special_ids = [getattr(tokenizer, f"{role}_token_id")
                       for role in ("unk", "pad", "mask", "cls", "bos", "eos", "sep")]
        self.assertEqual(len(set(special_ids)), 7)
        mixed = RegionSet.from_vectors(["chr1", "chrX"], [0, 0], [1, 1])
        self.assertEqual(tokenizer.tokenize(mixed), ["chr1:0-10"])
        self.assertEqual(tokenizer(mixed)["input_ids"], [1])
        self.assertEqual(tokenizer(mixed)["attention_mask"], [1])
        missing = RegionSet.from_vectors(["chrX"], [0], [1])
        self.assertEqual(tokenizer(missing)["input_ids"], [tokenizer.unk_token_id])
        self.assertEqual(tokenizer.decode(tokenizer.encode(["chr1:0-10"])), ["chr1:0-10"])
        with self.assertRaises((TypeError, ValueError, RuntimeError)):
            tokenizer.tokenize(["chr1:0-10"])
        config = self.root / "tokenizer.toml"
        config.write_text('universe = "universe.bed"\ntokenizer_type = "bits"\n')
        self.assertEqual(Tokenizer.from_config(str(config)).get_vocab(), tokenizer.get_vocab())
        with gzip.open(self.root / "universe.bed.gz", "wt") as handle:
            handle.write(bed.read_text())
        self.assertEqual(Tokenizer.from_pretrained(str(self.root)).get_vocab(), tokenizer.get_vocab())

    def test_fragment_counts_are_not_weights(self):
        bed = self.root / "universe.bed"
        bed.write_text("chr1\t0\t10\n")
        fragments = self.root / "fragments.tsv"
        fragments.write_text("chr1\t0\t10\tcell-a\t9\nchr1\t0\t10\tcell-a\t1\n")
        self.assertEqual(tokenize_fragment_file(str(fragments), Tokenizer.from_bed(str(bed))),
                         {"cell-a": [0, 0]})

    def test_refget_digest_import_report_pagination_and_disk_roundtrip(self):
        self.assertEqual(sha512t24u_digest("ACGT"), "aKF498dAxcJAqme6QYQ7EZ07-fiw8Kw2")
        self.assertEqual(md5_digest("ACGT"), "f1f8f4bf413b16ad135722aa4591043e")
        self.assertEqual(digest_sequence(b"acgt").metadata.sha512t24u,
                         sha512t24u_digest("ACGT"))
        fasta = self.root / "reference.fa"
        fasta.write_text(">chr1 synthetic\nacgtn\n")
        store = RefgetStore.in_memory()
        report = store.add_sequence_collections_from_fastas([str(fasta)], jobs=1)
        self.assertEqual(len(report), 1)
        self.assertEqual(report.n_collections_new, 1)
        self.assertEqual(report.n_sequences_written, 1)
        self.assertEqual(report.n_sequences_deduped, 0)
        metadata, was_new = report.collections[0]
        self.assertTrue(was_new)
        self.assertEqual(metadata.n_sequences, 1)
        same, added = store.add_sequence_collection_from_fasta(str(fasta), collection_alias="toy:v1")
        self.assertEqual(same.digest, metadata.digest)
        self.assertFalse(added)
        page = store.list_collections(page=0, page_size=1)
        self.assertEqual(page["pagination"], {"page": 0, "page_size": 1, "total": 1})
        self.assertEqual(store.list_collections(page=1, page_size=1)["results"], [])
        digest = store.list_sequences()[0].sha512t24u
        self.assertEqual(store.get_substrings(digest, [(0, 1), (1, 4)]), ["A", "CGT"])
        self.assertEqual(list(store.stream_sequence(digest, start=0, end=5, chunk_size=2)),
                         ["AC", "GT", "N"])
        self.assertEqual(store.get_substring(digest, 2, 2), "")
        self.assertEqual(int(store.stats()["n_sequences_in_memory"]), 1)
        disk = self.root / "store"
        store.write_store_to_dir(str(disk))
        self.assertTrue(RefgetStore.store_exists(str(disk)))
        reopened = RefgetStore.open_local(str(disk))
        self.assertEqual(reopened.get_substring(digest, 0, 5), "ACGTN")
