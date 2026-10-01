"""Scientific invariants for the documented ETE 4.4 recipes; no public downloads."""

import io
import tarfile
from pathlib import Path

import pytest

pytest.importorskip("ete4")
from ete4 import GTDBTaxa, NCBITaxa, PhyloTree, Tree
from ete4.parser import nexus
from ete4.treematcher import TreePattern

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "etetoolkit"


def taxdump(path, rows):
    """Minimal NCBI-like archive; identifiers/names are deliberately synthetic."""
    names = "".join(f"{i}\t|\t{name}\t|\t\t|\tscientific name\t|\n"
                    for i, _, name, _ in rows)
    nodes = "".join(f"{i}\t|\t{parent}\t|\t{rank}\t|\n"
                    for i, parent, _, rank in rows)
    with tarfile.open(path, "w:gz") as tar:
        for name, text in (("names.dmp", names), ("nodes.dmp", nodes), ("merged.dmp", "")):
            data = text.encode()
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            tar.addfile(entry, io.BytesIO(data))


def test_ncbi_local_archive_translation_topology_and_annotation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # ETE conversion emits temporary tables in cwd.
    monkeypatch.setattr("requests.get", lambda *a, **k: pytest.fail("Unexpected download"))
    archive = tmp_path / "taxdump.tar.gz"
    rows = [(1, 1, "root", "no rank"), (2, 1, "Example", "genus"),
            (3, 2, "Example alpha", "species"), (4, 2, "Example beta", "species")]
    taxdump(archive, rows)
    dbfile = str(tmp_path / "taxonomy.sqlite")
    ncbi = NCBITaxa(dbfile=dbfile, taxdump_file=str(archive), update=False)
    try:
        assert ncbi.get_name_translator(["Example alpha", "absent"]) == {"Example alpha": [3]}
        assert ncbi.get_lineage(3) == [1, 2, 3]
        assert ncbi.get_rank([3]) == {3: "species"}
        assert set(ncbi.get_descendant_taxa("Example")) == {3, 4}
        topology = ncbi.get_topology([3, 4], intermediate_nodes=True, annotate=True)
        assert {n.props["sci_name"] for n in topology.leaves()} == {"Example alpha", "Example beta"}
        tree = PhyloTree("(3,4);")
        tree.annotate_ncbi_taxa(taxid_attr="name", dbfile=dbfile)
        assert tree.props["sci_name"] == "Example"
        assert Path(dbfile + ".traverse.pkl").is_file()
    finally:
        ncbi.db.close()


def test_gtdb_local_archive_uses_string_names_and_genome_descendants(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("requests.get", lambda *a, **k: pytest.fail("Unexpected download"))
    archive = tmp_path / "gtdb.tar.gz"
    rows = [(1, 1, "root", "no rank"), (2, 1, "d__Bacteria", "superkingdom"),
            (3, 2, "s__Example alpha", "species"), (4, 2, "s__Example beta", "species"),
            (5, 3, "RS_GCF_000000001.1", "subspecies"),
            (6, 4, "GB_GCA_000000002.1", "subspecies")]
    taxdump(archive, rows)
    dbfile = str(tmp_path / "gtdb.sqlite")
    gtdb = GTDBTaxa(dbfile=dbfile, taxdump_file=str(archive))
    try:
        assert gtdb.get_rank(["s__Example alpha"]) == {"s__Example alpha": "species"}
        assert gtdb.get_name_lineage(["s__Example alpha"]) == [
            {"s__Example alpha": ["root", "d__Bacteria", "s__Example alpha"]}]
        descendants = gtdb.get_descendant_taxa("d__Bacteria")
        assert set(descendants) == {"RS_GCF_000000001.1", "GB_GCA_000000002.1"}
        topology = gtdb.get_topology(list(descendants), annotate=True)
        assert set(topology.leaf_names()) == set(descendants)
        # GTDB's genome-level sci_name is the parent species in ETE 4.4.
        assert {n.props["sci_name"] for n in topology.leaves()} == {"s__Example alpha", "s__Example beta"}
        tree = PhyloTree("(RS_GCF_000000001.1,GB_GCA_000000002.1);")
        tree.annotate_gtdb_taxa(taxid_attr="name", dbfile=dbfile)
        assert tree.props["sci_name"] == "d__Bacteria"
    finally:
        gtdb.db.close()


def test_exact_midpoint_preserves_distances_and_balances_the_diameter():
    tree = Tree("((A:1,B:1):10,C:2);")
    tree.set_midpoint_outgroup()
    assert tree.get_distance(tree["A"], tree["C"]) == 13
    assert tree.get_distance(tree, tree["A"]) == pytest.approx(6.5)
    assert tree.get_distance(tree, tree["C"]) == pytest.approx(6.5)
    old = Tree("((A:1,B:1):10,C:2);")
    old.set_outgroup(old.get_midpoint_outgroup())
    assert old.get_distance(old, old["A"]) != 6.5


def test_parsers_annotations_distances_and_pattern():
    tree = Tree("((A:1,B:1)95:0.2,C:1);", parser="support")
    assert tree.write(parser="support", props=[]) == "((A:1,B:1)95:0.2,C:1);"
    tree["A"].add_props(host="human", score=2)
    restored = Tree(tree.write(parser="support", props=["host"]), parser="support")
    assert restored["A"].props["host"] == "human"
    assert "score" not in restored["A"].props
    matrix = tree.distance_matrix(squared=True)
    names = list(tree.leaf_names())
    assert matrix[names.index("A")][names.index("B")] == 2
    assert matrix[names.index("A")][names.index("C")] == pytest.approx(2.2)
    trees = nexus.load(io.StringIO("#NEXUS\nBegin trees;\nTranslate 1 A, 2 B;\nTree x=(1,2);\nEnd;"), parser=9)
    assert set(trees["x"].leaf_names()) == {"A", "B"}
    pattern_tree = Tree("((K,((A,B),C),D),(E,F));")
    assert [n.id for n in TreePattern("(,,)", safer=True).search(pattern_tree)] == [(0,)]


def test_phylogeny_events_reconciliation_and_speciation_trees():
    tree = PhyloTree("((Hsa|g1,Ptr|g1),(Hsa|g2,Mmu|g1));",
                     sp_naming_function=lambda name: name.split("|", 1)[0])
    events = tree.get_descendant_evol_events(sos_thr=0.0)
    assert [e.etype for e in events].count("D") == 1
    assert [e.etype for e in events].count("S") == 2
    species = PhyloTree("((Hsa,Ptr),Mmu);", sp_naming_function=lambda name: name)
    reconciled, events = tree.reconcile(species)
    assert any(e.etype == "D" for e in events)
    assert any(n.props.get("evoltype") == "L" for n in reconciled.traverse())
    count, duplications, subtrees = tree.get_speciation_trees(
        autodetect_duplications=True, newick_only=False, prop="species")
    assert count == 2
    assert duplications == 1
    assert len(list(subtrees)) == count
    assert len(tree.split_by_dups()) == 2


def test_alignment_species_mapping_and_lineage_collapse():
    tree = PhyloTree("((Hsa|g1,Hsa|g2),Ptr|g1);",
                     sp_naming_function=lambda name: name.split("|", 1)[0])
    tree.link_to_alignment(
        ">Hsa|g1\nACGT\n>Hsa|g2\nACGA\n>Ptr|g1\nACTT\n", alg_format="fasta")
    assert {leaf.name: leaf.props["sequence"] for leaf in tree.leaves()}["Hsa|g2"] == "ACGA"
    collapsed = tree.collapse_lineage_specific_expansions(return_copy=True)
    assert sorted(leaf.species for leaf in collapsed.leaves()) == ["Hsa", "Ptr"]
    assert len(list(tree.leaves())) == 3  # original remains available for provenance


def test_topology_property_cache_monophyly_and_ultrametric():
    tree = Tree("((A:1,B:2)AB:1,C:3)Root;", parser=1)
    tree["A"].add_prop("group", "case")
    tree["B"].add_prop("group", "case")
    tree["C"].add_prop("group", "control")
    assert tree.get_cached_content(prop="name")[tree["AB"]] == {"A", "B"}
    assert tree.check_monophyly(values={"A", "B"}, prop="name")[0]
    assert [n.name for n in tree.get_monophyletic(values={"case"}, prop="group")] == ["AB"]
    copied = tree.copy()
    copied["A"].del_prop("group")
    assert tree["A"].get_prop("group") == "case"
    tree.to_ultrametric(topological=False)
    assert len({round(tree.get_distance(tree, leaf), 6) for leaf in tree.leaves()}) == 1
