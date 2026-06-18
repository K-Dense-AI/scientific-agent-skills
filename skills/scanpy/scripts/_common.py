#!/usr/bin/env python3
"""
Shared helpers for the scanpy script toolkit.

Every CLI script in this directory imports from this module so that data
loading, saving, figure configuration, and logging behave consistently.
This file is NOT a CLI itself; import it:

    from _common import load_anndata, save_anndata, configure_scanpy, info
"""

import os
import sys


def info(msg):
    """Print a progress message to stderr-friendly stdout with a marker."""
    print(f"[scanpy] {msg}", flush=True)


def die(msg, code=1):
    """Print an error and exit."""
    print(f"Error: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def _import_scanpy():
    try:
        import scanpy as sc  # noqa: F401
        return sc
    except ImportError:
        die('scanpy not installed. Install with: uv pip install "scanpy[leiden]"')


def configure_scanpy(figdir="figures", dpi=120, verbosity=1, autosave=False,
                     file_format="png"):
    """Apply consistent scanpy settings and return the scanpy module.

    Note: autosave is left off by default because the toolkit scripts pass
    explicit ``save=`` suffixes to plotting calls for predictable filenames.
    """
    sc = _import_scanpy()
    sc.settings.verbosity = verbosity
    sc.settings.set_figure_params(dpi=dpi, facecolor="white")
    sc.settings.figdir = figdir
    sc.settings.file_format_figs = file_format
    if autosave:
        sc.settings.autosave = True
    os.makedirs(figdir, exist_ok=True)
    return sc


def load_anndata(path, var_names="gene_symbols"):
    """Load an AnnData object, dispatching on the file extension / layout.

    Supported inputs:
      * ``.h5ad``                  -> sc.read_h5ad
      * ``.h5`` (10x CellRanger)   -> sc.read_10x_h5
      * ``.csv`` / ``.tsv`` / ``.txt`` -> sc.read_csv / read_text
      * ``.loom``                  -> sc.read_loom
      * ``.mtx``                   -> sc.read (matrix market)
      * a directory                -> sc.read_10x_mtx (10x mtx folder)
    """
    sc = _import_scanpy()
    if not os.path.exists(path):
        die(f"input not found: {path}")

    lower = path.lower()
    if os.path.isdir(path):
        info(f"Reading 10x mtx directory: {path}")
        return sc.read_10x_mtx(path, var_names=var_names)
    if lower.endswith(".h5ad"):
        return sc.read_h5ad(path)
    if lower.endswith(".h5"):
        info("Reading 10x HDF5 (.h5)")
        return sc.read_10x_h5(path)
    if lower.endswith(".loom"):
        return sc.read_loom(path)
    if lower.endswith(".csv"):
        return sc.read_csv(path)
    if lower.endswith((".tsv", ".txt")):
        return sc.read_text(path)
    if lower.endswith(".mtx") or lower.endswith(".mtx.gz"):
        return sc.read(path)
    die(f"unrecognized input format: {path}")


def save_anndata(adata, path):
    """Write an AnnData object to .h5ad, creating parent dirs as needed."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    adata.write_h5ad(path)
    info(f"Wrote {path}  ({adata.n_obs} cells x {adata.n_vars} genes)")


def add_io_args(parser, default_output=None):
    """Attach the standard input/output/figdir arguments to an argparse parser."""
    parser.add_argument("input", help="Input file (.h5ad, .h5, .csv, .loom, or 10x mtx dir)")
    parser.add_argument("-o", "--output", default=default_output,
                        help="Output .h5ad path" +
                             (f" (default: {default_output})" if default_output else ""))
    parser.add_argument("--figdir", default="figures",
                        help="Directory for saved figures (default: figures)")
    return parser


def summarize(adata):
    """Return a short human-readable summary string of an AnnData object."""
    lines = [f"{adata.n_obs} cells x {adata.n_vars} genes"]
    if len(adata.obs.columns):
        lines.append("obs: " + ", ".join(adata.obs.columns[:20]))
    if list(adata.obsm.keys()):
        lines.append("obsm: " + ", ".join(adata.obsm.keys()))
    if list(adata.layers.keys()):
        lines.append("layers: " + ", ".join(adata.layers.keys()))
    return "\n".join(lines)
