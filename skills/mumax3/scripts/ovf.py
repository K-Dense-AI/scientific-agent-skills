"""Read MuMax3 OVF 2.0 files (binary 4, binary 8 or text) into numpy arrays.

The returned array has shape ``(nz, ny, nx, ncomp)``: OVF stores data with x
varying fastest, then y, then z.

Usage as a library::

    from ovf import read_ovf
    m = read_ovf("run.out/m000010.ovf")      # (nz, ny, nx, 3)

Usage from the command line (prints shape, mesh and component means)::

    python ovf.py run.out/m000010.ovf
"""

import argparse
import sys

import numpy as np

_CHECK_4 = 1234567.0
_CHECK_8 = 123456789012345.0


def read_ovf(path):
    """Return the data of an OVF 2.0 file as an array of shape (nz, ny, nx, ncomp)."""
    data, _ = read_ovf_with_header(path)
    return data


def read_ovf_with_header(path):
    """Return ``(data, header)``; ``header`` maps lower-case keys to strings."""
    header = {}
    with open(path, "rb") as f:
        while True:
            raw = f.readline()
            if not raw:
                raise ValueError(f"{path}: no '# Begin: Data' line found")
            line = raw.decode("latin-1").strip()
            if line.lower().startswith("# begin: data"):
                kind = line.split()[-1].lower()
                break
            if line.startswith("#") and ":" in line:
                key, value = line[1:].split(":", 1)
                header[key.strip().lower()] = value.strip()

        try:
            nx, ny, nz = (int(header[k]) for k in ("xnodes", "ynodes", "znodes"))
        except KeyError as err:
            raise ValueError(f"{path}: missing {err.args[0]} in header") from None
        ncomp = int(header.get("valuedim", 3))
        n = nx * ny * nz * ncomp

        if kind == "4":
            check = np.frombuffer(f.read(4), "<f4")[0]
            if check != np.float32(_CHECK_4):
                raise ValueError(f"{path}: bad binary-4 check value {check}")
            data = np.frombuffer(f.read(4 * n), "<f4")
        elif kind == "8":
            check = np.frombuffer(f.read(8), "<f8")[0]
            if check != _CHECK_8:
                raise ValueError(f"{path}: bad binary-8 check value {check}")
            data = np.frombuffer(f.read(8 * n), "<f8")
        elif kind == "text":
            text = f.read().decode("latin-1").split("#", 1)[0]
            data = np.array(text.split(), dtype=float)
        else:
            raise ValueError(f"{path}: unsupported data format {kind!r}")

    if data.size < n:
        raise ValueError(f"{path}: expected {n} values, found {data.size}")
    return data[:n].reshape(nz, ny, nx, ncomp), header


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarise a MuMax3 OVF 2.0 file.")
    parser.add_argument("path", help="OVF file, e.g. run.out/m000000.ovf")
    args = parser.parse_args(argv)

    data, header = read_ovf_with_header(args.path)
    nz, ny, nx, ncomp = data.shape
    print(f"shape (nz, ny, nx, ncomp): {data.shape}")
    print(f"cell size: {header.get('xstepsize')} x {header.get('ystepsize')} x "
          f"{header.get('zstepsize')} {header.get('meshunit', '')}".rstrip())
    means = ", ".join(f"{v:.6g}" for v in data.reshape(-1, ncomp).mean(axis=0))
    print(f"component means: {means}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
