"""MAFFT alignment, IQ-TREE 3 / FastTree inference, optional ETE3 rendering.

Python 3.12 with ete3==3.1.3 for tree summaries; PyQt5 for rendering.
External executables: mafft plus iqtree3 (or --iqtree-bin iqtree2) / FastTree.
"""

import argparse
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


MAFFT_METHODS = {
    "auto": ["--auto"],
    "linsi": ["--localpair", "--maxiterate", "1000"],
    "einsi": ["--genafpair", "--maxiterate", "1000"],
    "fftnsi": ["--retree", "2", "--maxiterate", "2"],
    "fftns": ["--retree", "2", "--maxiterate", "0"],
}


def check_dependencies(use_fasttree=False, iqtree_bin="iqtree3", fasttree_bin="FastTree"):
    """Check only the selected inference backend, portably."""
    required = ["mafft", fasttree_bin if use_fasttree else iqtree_bin]
    missing = [tool for tool in required if shutil.which(tool) is None]
    if missing:
        raise RuntimeError("Missing executables on PATH: " + ", ".join(missing))
    print("[OK] All dependencies found.")


def count_sequences(fasta_file: str) -> int:
    with open(fasta_file) as handle:
        return sum(line.startswith(">") for line in handle)


def validate_fasta(path, seq_type="nt", aligned=False, min_taxa=4):
    """Reject ambiguous identifiers, empty records, wrong alphabets and ragged MSAs."""
    alphabets = {"nt": set("ACGTURYSWKMBDHVN?-"),
                 "aa": set("ACDEFGHIKLMNPQRSTVWYBXZ?-")}
    if seq_type not in alphabets:
        raise ValueError("Sequence type must be nt or aa")
    records = {}
    name = None
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                name = line[1:]
                if (not name or any(c.isspace() or c in "():,;[]'\"" for c in name)):
                    raise ValueError("Use unique FASTA IDs without whitespace or Newick punctuation")
                if name in records:
                    raise ValueError(f"Duplicate FASTA ID: {name}")
                records[name] = ""
            elif name is None:
                raise ValueError("Sequence before the first FASTA header")
            else:
                records[name] += line.upper()
    if len(records) < min_taxa:
        raise ValueError(f"Need at least {min_taxa} taxa")
    for name, sequence in records.items():
        missing = set("?-") | ({"N"} if seq_type == "nt" else {"X"})
        if not sequence or not (set(sequence) - missing):
            raise ValueError(f"Empty or entirely missing sequence: {name}")
        invalid = set(sequence) - alphabets[seq_type]
        if invalid:
            raise ValueError(f"Invalid {seq_type} symbols in {name}: {sorted(invalid)}")
    if aligned and len({len(sequence) for sequence in records.values()}) != 1:
        raise ValueError("Aligned FASTA sequences must have equal lengths")
    return records


def _run_to_file(command, output, label):
    """Keep any previous output intact when an executable fails or emits nothing."""
    output = Path(output)
    with tempfile.NamedTemporaryFile(mode="w", dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            result = subprocess.run(command, stdout=handle, stderr=subprocess.PIPE, text=True)
            handle.flush()
            if result.returncode != 0:
                raise RuntimeError(f"{label} failed:\n{result.stderr[-2000:]}")
            if temporary.stat().st_size == 0:
                raise RuntimeError(f"{label} produced an empty output")
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return str(output)


def run_mafft(input_fasta: str, output_fasta: str, n_threads=4, method="auto") -> str:
    """Use documented MAFFT options; auto delegates strategy selection to MAFFT."""
    if method not in MAFFT_METHODS:
        raise ValueError(f"Unsupported MAFFT method: {method}")
    if n_threads < 1:
        raise ValueError("Threads must be positive")
    if Path(input_fasta).resolve() == Path(output_fasta).resolve():
        raise ValueError("Alignment output must differ from input")
    command = ["mafft", *MAFFT_METHODS[method], "--thread", str(n_threads),
               "--inputorder", str(Path(input_fasta).resolve())]
    return _run_to_file(command, output_fasta, "MAFFT")


def run_iqtree(aligned_fasta: str, prefix: str, seq_type="nt", bootstrap=1000,
               n_threads=4, outgroup=None, executable="iqtree3", model="MFP",
               seed=42, redo=False) -> str:
    """Infer an ML tree with SH-aLRT/UFBoot labels; preserve checkpoints by default."""
    if seq_type not in {"nt", "aa"}:
        raise ValueError("Sequence type must be nt or aa")
    if bootstrap < 1000:
        raise ValueError("Ultrafast bootstrap requires at least 1000 replicates")
    if n_threads < 1:
        raise ValueError("Threads must be positive")
    command = [executable, "-s", str(Path(aligned_fasta).resolve()),
               "--prefix", str(Path(prefix).resolve()), "-st", "DNA" if seq_type == "nt" else "AA",
               "-m", model, "-B", str(bootstrap), "-T", str(n_threads),
               "--alrt", "1000", "--seed", str(seed)]
    if outgroup:
        command += ["-o", outgroup]
    if redo:
        command.append("--redo")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"IQ-TREE failed:\n{result.stderr[-2000:]}\n{result.stdout[-2000:]}")
    tree_file = f"{prefix}.treefile"
    if not Path(tree_file).is_file() or Path(tree_file).stat().st_size == 0:
        raise RuntimeError("IQ-TREE did not produce a nonempty .treefile")
    print(f"[OK] IQ-TREE tree: {tree_file}; inspect {prefix}.iqtree for model and support order")
    return tree_file


def run_fasttree(aligned_fasta: str, output_tree: str, seq_type="nt", executable="FastTree") -> str:
    """CAT topology/length optimization followed by Gamma20 rescaling; SH-like support."""
    if seq_type not in {"nt", "aa"}:
        raise ValueError("Sequence type must be nt or aa")
    if Path(aligned_fasta).resolve() == Path(output_tree).resolve():
        raise ValueError("Tree output must differ from input")
    options = ["-nt", "-gtr"] if seq_type == "nt" else ["-lg"]
    return _run_to_file([executable, *options, "-gamma", str(Path(aligned_fasta).resolve())],
                        output_tree, "FastTree")


def load_tree(tree_file):
    """Read slash-delimited IQ-TREE support as labels, never as invented support=1."""
    from ete3 import Tree
    tree = Tree(str(tree_file), format=1)
    names = tree.get_leaf_names()
    if len(names) != len(set(names)):
        raise ValueError("Duplicate tree leaf names")
    for node in tree.iter_descendants():
        if not math.isfinite(node.dist) or node.dist < 0:
            raise ValueError("Branch lengths must be finite and nonnegative")
    return tree


def root_for_display(tree, outgroup=None, midpoint=False):
    """Root explicitly while retaining internal labels on their unrooted splits."""
    if outgroup and midpoint:
        raise ValueError("Choose outgroup or midpoint rooting, not both")
    if not outgroup and not midpoint:
        return tree
    all_names = frozenset(tree.get_leaf_names())
    if outgroup and outgroup not in all_names:
        raise ValueError(f"Outgroup not found: {outgroup}")

    def split_key(node):
        side = frozenset(node.get_leaf_names())
        return min(tuple(sorted(side)), tuple(sorted(all_names - side)))

    labels = {}
    for node in tree.iter_descendants():
        if not node.is_leaf() and node.name:
            key = split_key(node)
            if key in labels and labels[key] != node.name:
                raise ValueError("Conflicting labels on the same root split")
            labels[key] = node.name
    target = outgroup if outgroup else tree.get_midpoint_outgroup()
    if target is None:
        raise ValueError("Cannot midpoint-root this tree")
    tree.set_outgroup(target)
    for node in tree.traverse():
        if not node.is_leaf():
            node.name = "" if node.is_root() else labels.get(split_key(node), "")
    return tree


def visualize_tree(tree_file: str, output_png: str, outgroup=None, midpoint=False):
    """Render labels verbatim; return the image path only on successful rendering."""
    try:
        from ete3 import TreeStyle, TextFace
    except ImportError as exc:
        print(f"ETE3 rendering unavailable ({exc}). Skipping visualization.")
        print("Install in Python 3.12: uv pip install ete3==3.1.3 PyQt5")
        return None
    tree = root_for_display(load_tree(tree_file), outgroup, midpoint)
    style = TreeStyle()
    style.show_leaf_name = True
    style.show_branch_support = False
    style.mode = "r"
    for node in tree.iter_descendants():
        if not node.is_leaf() and node.name:
            node.add_face(TextFace(node.name), column=0, position="branch-top")
    try:
        tree.render(output_png, tree_style=style, w=800, units="px")
    except Exception as exc:
        print(f"Visualization failed: {exc}")
        return None
    print(f"[OK] Visualization: {output_png}")
    return output_png


def tree_summary(tree_file: str) -> dict:
    """Summarize original non-root branches, including zero-length edges."""
    try:
        tree = load_tree(tree_file)
        lengths = [node.dist for node in tree.iter_descendants()]
        stats = {"n_taxa": len(tree), "total_branch_length": sum(lengths),
                 "mean_branch_length": sum(lengths) / len(lengths) if lengths else 0,
                 "max_branch_length": max(lengths, default=0)}
        print(f"Tree summary (original topology): {stats}")
        return stats
    except (ImportError, ValueError, OSError) as exc:
        print(f"Could not compute tree stats: {exc}")
        return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="FASTA with unique whitespace-free taxon IDs")
    parser.add_argument("--type", choices=["nt", "aa"], default="nt")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--bootstrap", type=int, default=1000, help="UFBoot replicates, >=1000")
    parser.add_argument("--fasttree", action="store_true")
    parser.add_argument("--iqtree-bin", default="iqtree3")
    parser.add_argument("--fasttree-bin", default="FastTree")
    parser.add_argument("--model", default="MFP", help="IQ-TREE model or ModelFinder Plus")
    parser.add_argument("--seed", type=int, default=42, help="IQ-TREE random seed")
    parser.add_argument("--redo", action="store_true", help="Explicitly overwrite IQ-TREE results")
    root = parser.add_mutually_exclusive_group()
    root.add_argument("--outgroup", help="One taxon ID; validate its biological suitability")
    root.add_argument("--midpoint", action="store_true", help="Midpoint-root the display only")
    parser.add_argument("--mafft-method", default="auto", choices=list(MAFFT_METHODS))
    parser.add_argument("--aligned", action="store_true", help="Use a reviewed MSA without realignment")
    parser.add_argument("--no-visualization", action="store_true")
    parser.add_argument("--output-dir", default="phylo_results")
    args = parser.parse_args()
    if args.threads < 1 or (not args.fasttree and args.bootstrap < 1000):
        parser.error("Threads must be positive; IQ-TREE UFBoot requires >=1000 replicates")
    try:
        records = validate_fasta(args.input, args.type, aligned=args.aligned)
        if args.outgroup and args.outgroup not in records:
            raise ValueError(f"Outgroup not found: {args.outgroup}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    prefix = str(Path(args.output_dir) / Path(args.input).stem)
    aligned = args.input if args.aligned else run_mafft(
        args.input, f"{prefix}_aligned.fasta", args.threads, args.mafft_method)
    validated = validate_fasta(aligned, args.type, aligned=True)
    if set(validated) != set(records):
        raise RuntimeError("Alignment changed the taxon IDs")
    if args.fasttree:
        tree_file = run_fasttree(aligned, f"{prefix}.tree", args.type, args.fasttree_bin)
    else:
        tree_file = run_iqtree(aligned, prefix, args.type, args.bootstrap, args.threads,
                              args.outgroup, args.iqtree_bin, args.model, args.seed, args.redo)
    if not args.no_visualization:
        visualize_tree(tree_file, f"{prefix}_tree.png", outgroup=args.outgroup, midpoint=args.midpoint)
    tree_summary(tree_file)
    print(f"[OK] Alignment: {aligned}\n[OK] Inferred tree: {tree_file}")
    print("Retain the original tree, tool logs, model, support method, seed and alignment provenance.")


if __name__ == "__main__":
    main()
