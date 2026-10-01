"""Execute documented examples against small synthetic data, without service calls."""
import ast
import gzip
import io
from pathlib import Path
import re
import textwrap
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

Bio = pytest.importorskip("Bio")
from Bio import Align, Entrez, Phylo, SeqIO, bgzf
from Bio.Blast import NCBIWWW
from Bio.PDB import Atom, Chain, Model, Residue, Structure
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord
import numpy as np

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "biopython"


def blocks(filename):
    return [textwrap.dedent(b) for b in re.findall(
        r"```python\n(.*?)```", (SKILL_ROOT / filename).read_text(), re.S
    )]


def block(filename, marker):
    return next(b for b in blocks(filename) if marker in b)


def run_block(filename, marker, **namespace):
    exec(compile(block(filename, marker), filename, "exec"), namespace)
    return namespace


def function(filename, name, **namespace):
    code = block(filename, f"def {name}(")
    node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), filename, "exec"), namespace)
    return namespace[name]


def test_python_fences_compile():
    for path in SKILL_ROOT.rglob("*.md"):
        for code in blocks(str(path.relative_to(SKILL_ROOT))):
            ast.parse(code)


def test_compression_and_format_conversion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = ">a\nATGC\n>b\nGGTT\n"
    with gzip.open("sequences.fasta.gz", "wt") as handle:
        handle.write(data)
    with bgzf.open("sequences.fasta.bgz", "w") as handle:
        handle.write(data)
    run_block("references/sequence_io.md", 'import gzip')
    Path("input.fasta").write_text(data)
    for fmt in ("genbank", "embl"):
        assert SeqIO.convert("input.fasta", "fasta", f"out.{fmt}", fmt, molecule_type="DNA") == 2
        assert [str(r.seq) for r in SeqIO.parse(f"out.{fmt}", fmt)] == ["ATGC", "GGTT"]


def test_reverse_complement_preserves_quality_and_maps_features():
    record = SeqRecord(Seq("AAGT"), id="a", letter_annotations={"phred_quality": [10, 20, 30, 40]})
    record.features = [SeqFeature(SimpleLocation(0, 2, strand=1), type="gene")]
    ns = run_block("references/sequence_io.md", 'record.id = "new_id"', record=record)
    reverse = ns["record"]
    assert str(reverse.seq) == "ACTT"
    assert reverse.letter_annotations["phred_quality"] == [40, 30, 20, 10]
    assert reverse.features[0].location == SimpleLocation(2, 4, strand=-1)


def test_pairwise_scoring_and_undefined_identity():
    ns = run_block("references/alignment.md", '# Set scoring parameters', aligner=Align.PairwiseAligner())
    assert ns["aligner"].open_internal_gap_score == -2
    assert ns["aligner"].open_left_gap_score == 0
    identity = function("references/alignment.md", "pairwise_identity")
    assert identity("A-CG", "ATCT") == pytest.approx(2 / 3)
    assert np.isnan(identity("--", "AA"))
    with pytest.raises(ValueError):
        identity("AC", "A")


def test_advanced_current_apis():
    ns = run_block("references/advanced.md", '# Create a feature')
    assert ns["feature"].location.strand == 1
    assert len(ns["feature_seq"]) == 40
    assert run_block("references/advanced.md", 'from Bio.SeqUtils import GC_skew', Seq=Seq)["skew"] == pytest.approx([-1 / 9])
    run_block("references/advanced.md", 'from Bio.Align import PairwiseAligner')
    ns = run_block("references/advanced.md", 'from Bio.SeqUtils.ProtParam import ProteinAnalysis')
    assert sum(ns["analyzed_seq"].amino_acids_percent.values()) == pytest.approx(100)


def test_orf_coordinates_and_length_threshold():
    find = function("references/advanced.md", "find_orfs")
    seq = Seq("ATGAAATAACCCGGGTTATTT")
    candidates = find(seq, min_length=4)
    assert candidates
    for candidate in candidates:
        assert candidate["length"] >= 4
        expected = seq[candidate["start"]:candidate["end"]]
        if candidate["strand"] == -1:
            expected = expected.reverse_complement()
        assert candidate["sequence"] == expected
        assert "*" not in expected.translate()
    assert find(Seq("ATG"), min_length=4) == []


def test_promoters_orientation_and_uncertain_location(tmp_path):
    extract = function("references/advanced.md", "extract_promoters")
    record = SeqRecord(Seq("AAAACCCCGGGGTTTT"), id="a", annotations={"molecule_type": "DNA"})
    record.features = [SeqFeature(SimpleLocation(4, 8, strand=1), type="gene"),
                       SeqFeature(SimpleLocation(8, 12, strand=-1), type="gene")]
    path = tmp_path / "genes.gb"
    SeqIO.write(record, path, "genbank")
    assert [str(x["sequence"]) for x in extract(path, 4)] == ["AAAA", "AAAA"]
    record.annotations["topology"] = "circular"
    SeqIO.write(record, path, "genbank")
    with pytest.raises(ValueError, match="linear"):
        extract(path)


def test_codon_usage_rejects_incomplete_cds(tmp_path):
    analyze = function("references/advanced.md", "analyze_codon_usage", SeqIO=SeqIO)
    path = tmp_path / "cds.fa"
    path.write_text(">a\natgatgtaa\n")
    assert analyze(path) == {"ATG": pytest.approx(2 / 3), "TAA": pytest.approx(1 / 3)}
    path.write_text(">a\nATGA\n")
    with pytest.raises(ValueError):
        analyze(path)


def test_tree_construction_copy_and_collapse():
    ns = run_block("references/phylogenetics.md", 'dm = DistanceMatrix(', Phylo=Phylo)
    assert ns["tree"].count_terminals() == 4
    tree = Phylo.read(io.StringIO("((Species_A:1,Species_B:1):0.001,Species_C:2,Species_D:2);"), "newick")
    ns = run_block("references/phylogenetics.md", '# Prune (remove)', tree=tree)
    assert tree.count_terminals() == 4
    assert ns["tree_copy"].count_terminals() == 3
    collapse = function("references/phylogenetics.md", "collapse_short_branches")
    before = len(tree.get_nonterminals())
    collapse(tree)
    assert len(tree.get_nonterminals()) == before - 1


def test_rooted_rf_is_not_unrooted_or_branch_distance():
    rf = function("references/phylogenetics.md", "robinson_foulds_distance")
    a = Phylo.read(io.StringIO("((a:1,b:1):1,c:1);"), "newick", rooted=True)
    b = Phylo.read(io.StringIO("((a:5,b:2):4,c:3);"), "newick", rooted=True)
    c = Phylo.read(io.StringIO("((a:1,c:1):1,b:1);"), "newick", rooted=True)
    assert rf(a, b) == 0
    assert rf(a, c) == 2
    c.rooted = False
    with pytest.raises(ValueError):
        rf(a, c)


def structure_fixture():
    structure = Structure.Structure("tiny")
    model = Model.Model(0)
    chain = Chain.Chain("A")
    structure.add(model)
    model.add(chain)
    for n, name, het, coord, element in [(1, "ALA", " ", [1., 0, 0], "C"),
                                        (2, "LIG", "H_LIG", [0., 0, 0], "O")]:
        residue = Residue.Residue((het, n, " "), name, " ")
        atom = Atom.Atom("CA" if name == "ALA" else "O", np.array(coord), 10., 1., " ", "CA  ", n, element=element)
        residue.add(atom)
        chain.add(residue)
    return structure


def test_ligand_same_chain_is_not_excluded_and_mass_is_element_specific():
    structure = structure_fixture()
    find = function("references/structure.md", "find_binding_site")
    found = find(structure, "A", ("H_LIG", 2, " "), distance=2)
    assert [r.resname for r in found] == ["ALA"]
    com = function("references/structure.md", "center_of_mass", np=np)
    atoms = list(structure.get_atoms())
    assert com(structure)[0] == pytest.approx(atoms[0].mass / sum(a.mass for a in atoms))
    atoms[0].mass = float("nan")
    with pytest.raises(ValueError):
        com(structure)


def test_atom_rotation_uses_array_translation():
    structure = structure_fixture()
    run_block("references/structure.md", '# Rotate structure', structure=structure)
    assert np.isfinite(next(structure.get_atoms()).coord).all()


def test_zero_dihedral_is_retained():
    get = function("references/structure.md", "get_phi_psi")
    class Peptide(list):
        def get_phi_psi_list(self):
            return [(0.0, 1.0), (None, 1.0)]
    peptide = Peptide([SimpleNamespace(resname="ALA"), SimpleNamespace(resname="GLY")])
    get.__globals__["Polypeptide"] = SimpleNamespace(PPBuilder=lambda: SimpleNamespace(build_peptides=lambda chain: [peptide]))
    assert get([[object()]]) == [("ALA", 0.0, 1.0)]


@pytest.mark.parametrize("name,kwargs", [
    ("einfo", {"db": "pubmed"}),
    ("esearch", {"db": "pubmed", "term": "biopython", "retmax": 10}),
    ("esummary", {"db": "pccompound", "id": "2244"}),
    ("efetch", {"db": "pubmed", "WebEnv": "mock-history", "query_key": "1", "retmode": "text", "rettype": "medline"}),
    ("elink", {"dbfrom": "nuccore", "db": "protein", "id": ["123", "456"]}),
    ("epost", {"db": "pubmed", "id": ["19304878", "18606172"]}),
    ("espell", {"db": "pubmed", "term": "biopythn"}),
])
def test_entrez_routes_and_serialization(monkeypatch, name, kwargs):
    monkeypatch.setattr(Entrez, "email", "offline-test@example.invalid")
    monkeypatch.setattr(Entrez, "api_key", None)
    monkeypatch.setattr(Entrez, "_open", lambda request: request)
    request = getattr(Entrez, name)(**kwargs)
    assert urlparse(request.full_url).path.endswith(f"/{name}.fcgi")
    payload = request.data.decode() if request.data else urlparse(request.full_url).query
    values = parse_qs(payload)
    if name == "elink":
        assert values["id"] == ["123", "456"]
    if name == "epost":
        assert request.method == "POST"
    if name == "efetch":
        assert values["WebEnv"] == ["mock-history"]


def test_pubmed_limit_stops_before_pagination(monkeypatch):
    monkeypatch.setattr(Entrez, "esearch", lambda **kwargs: io.BytesIO())
    monkeypatch.setattr(Entrez, "read", lambda handle: {"Count": "10001"})
    with pytest.raises(ValueError, match="Partition"):
        run_block("references/databases.md", '# Batch processing for large searches', Entrez=Entrez)


def test_qblast_explicit_xml2_response_contract(monkeypatch):
    requests = []
    def fake_open(request):
        requests.append(parse_qs(request.data.decode()))
        if len(requests) == 1:
            return io.BytesIO(b"RID = MOCKRID\nRTOE = 0\n")
        return io.BytesIO(b"<?xml version='1.0'?><BlastXML2/>")
    monkeypatch.setattr(NCBIWWW, "urlopen", fake_open)
    monkeypatch.setattr(NCBIWWW.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(NCBIWWW.qblast, "previous", 0)
    with NCBIWWW.qblast("blastn", "nt", "ATGC", format_type="XML2_S") as handle:
        assert "BlastXML2" in handle.read()
    assert [r["CMD"] for r in requests] == [["Put"], ["Get"]]
    assert requests[1]["FORMAT_TYPE"] == ["XML2_S"]


def test_motif_pseudocounts_genepop_and_restriction():
    ns = run_block("references/advanced.md", '# Create motif from instances')
    ns = run_block("references/advanced.md", '# Create position weight matrix', motif=ns["motif"])
    motif = ns["motif"]
    expected = sum(sum(motif.pwm[base, j] * np.log2(motif.pwm[base, j] / 0.25)
                       for base in "ACGT") for j in range(len(motif)))
    assert ns["ic"] == pytest.approx(expected)
    run_block("references/advanced.md", '# Analyze sequence for restriction sites')
    from Bio.PopGen import GenePop
    record = GenePop.read(io.StringIO("tiny\nLocus1\nPop\na, 0102\n"))
    assert record.populations[0][0][1] == [(1, 2)]
