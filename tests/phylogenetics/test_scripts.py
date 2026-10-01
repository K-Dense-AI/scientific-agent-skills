"""Behavioral tests; command doubles are not live native-tool validation."""

import contextlib
import io
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "phylogenetics"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import phylogenetic_analysis as pipeline

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
TREE = "((A:1,B:1)81/99:1,(C:2,D:2):1);"
FASTA = ">A\nACGTACGT\n>B\nACGTTCGT\n>C\nTCGTACGT\n>D\nTCGTTCGT\n"


@pytest.fixture
def fasta(tmp_path):
    path = tmp_path / "input.fasta"
    path.write_text(FASTA)
    return path


@pytest.fixture
def native_mock():
    def complete(command, **kwargs):
        if command[0] == "mafft":
            kwargs["stdout"].write(Path(command[-1]).read_text())
        elif "--prefix" in command:
            Path(command[command.index("--prefix") + 1] + ".treefile").write_text(TREE)
        else:
            kwargs["stdout"].write(TREE)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
    with mock.patch.object(pipeline.subprocess, "run", side_effect=complete) as run:
        yield run


def test_fasta_validation_counts_records_and_wrapped_sequences(fasta):
    assert pipeline.count_sequences(fasta) == 4
    assert pipeline.validate_fasta(fasta, aligned=True)["A"] == "ACGTACGT"


@pytest.mark.parametrize("content,message", [
    ("", "at least"),
    (FASTA + ">A\nACGT\n", "Duplicate"),
    (FASTA.replace(">A", ">A description"), "whitespace"),
    (FASTA.replace(">A", ">A:B"), "punctuation"),
    ("ACGT\n" + FASTA, "before"),
    (FASTA.replace("ACGTACGT", "----????", 1), "missing"),
    (FASTA.replace("ACGTACGT", "NNNNNNNN", 1), "missing"),
    (FASTA.replace("ACGTACGT", "ACGT*CGT", 1), "Invalid"),
    (FASTA.replace("ACGTACGT", "ACGT", 1), "equal lengths"),
])
def test_invalid_alignment_fails_before_inference(tmp_path, content, message):
    path = tmp_path / "bad.fasta"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        pipeline.validate_fasta(path, aligned=True)


@pytest.mark.parametrize("method,flags", [
    ("auto", ["--auto"]),
    ("linsi", ["--localpair", "--maxiterate", "1000"]),
    ("einsi", ["--genafpair", "--maxiterate", "1000"]),
    ("fftnsi", ["--retree", "2", "--maxiterate", "2"]),
    ("fftns", ["--retree", "2", "--maxiterate", "0"]),
])
def test_mafft_methods_use_real_options(fasta, native_mock, method, flags):
    destination = fasta.with_name("aligned.fasta")
    pipeline.run_mafft(str(fasta), str(destination), method=method, n_threads=2)
    command = native_mock.call_args.args[0]
    assert command == ["mafft", *flags, "--thread", "2", "--inputorder", str(fasta)]
    assert destination.read_text() == FASTA


def test_mafft_rejects_invalid_method_and_in_place_output(fasta, native_mock):
    with pytest.raises(ValueError, match="Unsupported"):
        pipeline.run_mafft(str(fasta), str(fasta.with_suffix(".aln")), method="bad")
    with pytest.raises(ValueError, match="differ"):
        pipeline.run_mafft(str(fasta), str(fasta))
    native_mock.assert_not_called()


@pytest.mark.parametrize("returncode,stderr", [(1, "bad alignment"), (0, "")])
def test_external_failure_or_empty_output_does_not_clobber_existing_file(fasta, returncode, stderr):
    output = fasta.with_suffix(".out")
    output.write_text("previous result")
    result = subprocess.CompletedProcess([], returncode, stdout="", stderr=stderr)
    with mock.patch.object(pipeline.subprocess, "run", return_value=result):
        with pytest.raises(RuntimeError):
            pipeline.run_mafft(str(fasta), str(output))
    assert output.read_text() == "previous result"
    assert {p.name for p in fasta.parent.iterdir()} == {fasta.name, output.name}


@pytest.mark.parametrize("seq_type,alphabet", [("nt", "DNA"), ("aa", "AA")])
def test_iqtree_honors_alphabet_and_preserves_checkpoint(fasta, native_mock, seq_type, alphabet):
    tree = pipeline.run_iqtree(str(fasta), str(fasta.with_suffix("")), seq_type=seq_type)
    command = native_mock.call_args.args[0]
    for flag, value in [("-st", alphabet), ("-m", "MFP"), ("-B", "1000"),
                        ("--alrt", "1000"), ("--seed", "42")]:
        assert command[command.index(flag) + 1] == value
    assert command[0] == "iqtree3"
    assert "--redo" not in command
    assert Path(tree).read_text() == TREE


def test_iqtree_overrides_are_explicit(fasta, native_mock):
    pipeline.run_iqtree(str(fasta), str(fasta.with_suffix("")), executable="iqtree2",
                         redo=True, outgroup="A", model="GTR+G4", seed=8, bootstrap=2000)
    command = native_mock.call_args.args[0]
    assert command[0] == "iqtree2"
    assert "--redo" in command
    assert command[command.index("-o") + 1] == "A"
    assert command[command.index("-m") + 1] == "GTR+G4"
    assert command[command.index("-B") + 1] == "2000"
    assert command[command.index("--seed") + 1] == "8"


def test_iqtree_rejects_invalid_bootstrap_before_call(fasta, native_mock):
    with pytest.raises(ValueError, match="at least 1000"):
        pipeline.run_iqtree(str(fasta), "run", bootstrap=99)
    native_mock.assert_not_called()


def test_iqtree_checks_that_a_tree_was_produced(fasta):
    with mock.patch.object(pipeline.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")):
        with pytest.raises(RuntimeError, match="nonempty"):
            pipeline.run_iqtree(str(fasta), str(fasta.with_suffix("")))


@pytest.mark.parametrize("seq_type,options", [("nt", ["-nt", "-gtr"]), ("aa", ["-lg"])])
def test_fasttree_model_depends_on_alphabet(fasta, native_mock, seq_type, options):
    pipeline.run_fasttree(str(fasta), str(fasta.with_suffix(".tree")), seq_type)
    assert native_mock.call_args.args[0] == ["FastTree", *options, "-gamma", str(fasta)]


def test_dependency_check_only_requires_selected_backend():
    with mock.patch.object(pipeline.shutil, "which", return_value="/tool") as which:
        pipeline.check_dependencies(use_fasttree=True)
    assert which.call_args_list == [mock.call("mafft"), mock.call("FastTree")]
    with mock.patch.object(pipeline.shutil, "which", return_value=None):
        with pytest.raises(RuntimeError, match="iqtree3"):
            pipeline.check_dependencies()


@pytest.fixture
def tree_file(tmp_path):
    pytest.importorskip("ete3")
    path = tmp_path / "tree.nwk"
    path.write_text(TREE)
    return path


def test_slash_support_labels_survive_loading_and_roundtrip(tree_file):
    tree = pipeline.load_tree(tree_file)
    assert "81/99" in [n.name for n in tree.iter_descendants()]
    assert "81/99" in tree.write(format=1)
    assert tree.get_leaf_names() == ["A", "B", "C", "D"]


def test_summary_does_not_reroot_or_ignore_zero_edges(tree_file):
    tree_file.write_text("((A:0,B:1)81/99:1,(C:2,D:2):1);")
    stats = pipeline.tree_summary(tree_file)
    assert stats == {"n_taxa": 4, "total_branch_length": 7, "mean_branch_length": 7/6,
                     "max_branch_length": 2}


def test_missing_outgroup_is_an_error_never_midpoint_fallback(tree_file):
    with pytest.raises(ValueError, match="Outgroup not found"):
        pipeline.root_for_display(pipeline.load_tree(tree_file), outgroup="missing")


@pytest.mark.parametrize("options", [{"outgroup": "C"}, {"midpoint": True}])
def test_rerooting_preserves_distances_and_support_split(tree_file, options):
    tree = pipeline.load_tree(tree_file)
    before = {(a,b): tree.get_distance(a,b) for a in "ABCD" for b in "ABCD" if a != b}
    pipeline.root_for_display(tree, **options)
    assert {(a,b): tree.get_distance(a,b) for a,b in before} == before
    supported = [set(n.get_leaf_names()) for n in tree.iter_descendants() if n.name == "81/99"]
    assert supported
    assert all(s in ({"A", "B"}, {"C", "D"}) for s in supported)


def test_no_implicit_midpoint_root(tree_file):
    tree = pipeline.load_tree(tree_file)
    before = tree.write(format=1)
    assert pipeline.root_for_display(tree).write(format=1) == before


def test_negative_branch_length_is_rejected(tree_file):
    tree_file.write_text("(A:-1,B:1,C:2);")
    with pytest.raises(ValueError, match="nonnegative"):
        pipeline.load_tree(tree_file)


def test_missing_qt_does_not_claim_an_image(tree_file):
    import ete3
    if hasattr(ete3, "TreeStyle"):
        pytest.skip("No missing-Qt path in this environment")
    with contextlib.redirect_stdout(io.StringIO()) as output:
        result = pipeline.visualize_tree(str(tree_file), str(tree_file.with_suffix(".png")))
    assert result is None
    assert "PyQt5" in output.getvalue()
    assert not tree_file.with_suffix(".png").exists()


@pytest.mark.parametrize("extra,executables", [([], ["mafft", "iqtree3"]),
    (["--fasttree"], ["mafft", "FastTree"]), (["--aligned"], ["iqtree3"])])
def test_pipeline_wires_reviewed_alignment_and_selected_backend(fasta, native_mock, extra, executables):
    argv = ["pipeline", str(fasta), "--output-dir", str(fasta.parent / "results"),
            "--no-visualization", *extra]
    with mock.patch.object(sys, "argv", argv), mock.patch.object(pipeline, "tree_summary"):
        pipeline.main()
    assert [call.args[0][0] for call in native_mock.call_args_list] == executables
    if "--aligned" not in extra:
        assert "input_aligned.fasta" in native_mock.call_args_list[-1].args[0][-1] or any(
            "input_aligned.fasta" in a for a in native_mock.call_args_list[-1].args[0])


def test_cli_validates_outgroup_before_calling_tools(fasta, native_mock):
    with mock.patch.object(sys, "argv", ["pipeline", str(fasta), "--outgroup", "missing"]):
        with pytest.raises(SystemExit) as error:
            pipeline.main()
    assert error.value.code == 2
    native_mock.assert_not_called()


@pytest.mark.parametrize("method", list(pipeline.MAFFT_METHODS))
def test_native_mafft_method_when_available(fasta, method):
    if pipeline.shutil.which("mafft") is None:
        pytest.skip("MAFFT executable is not installed")
    destination = fasta.with_name(f"{method}.fasta")
    pipeline.run_mafft(str(fasta), str(destination), n_threads=1, method=method)
    aligned = pipeline.validate_fasta(destination, aligned=True)
    assert list(aligned) == ["A", "B", "C", "D"]
    assert {name: seq.replace("-", "") for name, seq in aligned.items()} == pipeline.validate_fasta(fasta)


@pytest.mark.parametrize("seq_type", ["nt", "aa"])
@pytest.mark.parametrize("backend", ["iqtree3", "FastTree"])
def test_native_pipeline_when_executables_available(tmp_path, seq_type, backend):
    """Small reproducible smoke data; not an inference-accuracy benchmark."""
    import random
    if any(pipeline.shutil.which(exe) is None for exe in ["mafft", backend]):
        pytest.skip(f"Native integration requires MAFFT and {backend} on PATH")
    pytest.importorskip("ete3")
    rng = random.Random(7)
    alphabet = "ACGT" if seq_type == "nt" else "ACDEFGHIKLMNPQRSTVWY"
    ancestor = "".join(rng.choice(alphabet) for _ in range(300))
    records = []
    for i in range(6):
        sequence = "".join(rng.choice(alphabet) if rng.random() < 0.12 else c for c in ancestor)
        records.append(f">sample_{i}\n{sequence}\n")
    source = tmp_path / "input.fasta"
    source.write_text("".join(records))
    argv = ["pipeline", str(source), "--type", seq_type, "--threads", "1",
            "--no-visualization", "--output-dir", str(tmp_path / "output")]
    if backend == "FastTree":
        argv.append("--fasttree")
    elif seq_type == "aa":
        argv += ["--model", "LG+G4"]
    with mock.patch.object(sys, "argv", argv):
        pipeline.main()
    suffix = "tree" if backend == "FastTree" else "treefile"
    tree = pipeline.load_tree(tmp_path / "output" / f"input.{suffix}")
    assert set(tree.get_leaf_names()) == {f"sample_{i}" for i in range(6)}
    labels = [n.name for n in tree.iter_descendants() if not n.is_leaf()]
    if backend == "iqtree3":
        assert any("/" in label for label in labels)
    else:
        assert all(0 <= float(label) <= 1 for label in labels if label)
    assert pipeline.tree_summary(tmp_path / "output" / f"input.{suffix}")["total_branch_length"] > 0
