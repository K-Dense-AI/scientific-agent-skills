import importlib.util
from pathlib import Path

import pytest
import skill_contract

np = pytest.importorskip("numpy", reason="mumax3 needs numpy")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "mumax3"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

spec = importlib.util.spec_from_file_location("mumax3_ovf", SKILL_ROOT / "scripts" / "ovf.py")
ovf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ovf)

NX, NY, NZ = 4, 3, 2


def reference():
    """Values that encode their own position: v = 1000*z + 100*y + 10*x + c."""
    z, y, x, c = np.meshgrid(np.arange(NZ), np.arange(NY), np.arange(NX), np.arange(3), indexing="ij")
    return (1000 * z + 100 * y + 10 * x + c).astype(float)


def write_ovf(path, kind, data, check=None):
    header = (
        "# OOMMF OVF 2.0\n# Segment count: 1\n# Begin: Segment\n# Begin: Header\n"
        "# Title: m\n# meshtype: rectangular\n# meshunit: m\n"
        f"# xnodes: {NX}\n# ynodes: {NY}\n# znodes: {NZ}\n"
        "# xstepsize: 4e-09\n# ystepsize: 4e-09\n# zstepsize: 1e-08\n"
        "# valuedim: 3\n# End: Header\n"
    )
    flat = data.reshape(-1)
    with open(path, "wb") as f:
        if kind == "4":
            f.write((header + "# Begin: Data Binary 4\n").encode())
            f.write(np.array([check or 1234567.0], "<f4").tobytes() + flat.astype("<f4").tobytes())
        elif kind == "8":
            f.write((header + "# Begin: Data Binary 8\n").encode())
            f.write(np.array([check or 123456789012345.0], "<f8").tobytes() + flat.astype("<f8").tobytes())
        else:
            f.write((header + "# Begin: Data Text\n").encode())
            f.write(("\n".join(" ".join(f"{v:g}" for v in row) for row in data.reshape(-1, 3)) + "\n").encode())
        f.write(b"# End: Data\n# End: Segment\n")


@pytest.mark.parametrize("kind", ["4", "8", "text"])
def test_read_ovf_layout_is_z_y_x_component(tmp_path, kind):
    path = tmp_path / f"m_{kind}.ovf"
    write_ovf(path, kind, reference())
    data = ovf.read_ovf(path)
    assert data.shape == (NZ, NY, NX, 3)
    np.testing.assert_array_equal(data, reference())
    # spot-check the x-fastest ordering explicitly
    assert data[1, 2, 3, 1] == 1000 + 200 + 30 + 1


def test_header_is_returned(tmp_path):
    path = tmp_path / "m.ovf"
    write_ovf(path, "4", reference())
    _, header = ovf.read_ovf_with_header(path)
    assert header["xnodes"] == str(NX)
    assert float(header["zstepsize"]) == pytest.approx(1e-8)


@pytest.mark.parametrize("kind", ["4", "8"])
def test_bad_check_value_is_rejected(tmp_path, kind):
    path = tmp_path / "bad.ovf"
    write_ovf(path, kind, reference(), check=1.0)
    with pytest.raises(ValueError, match="check value"):
        ovf.read_ovf(path)


def test_truncated_file_is_rejected(tmp_path):
    path = tmp_path / "short.ovf"
    write_ovf(path, "4", reference())
    path.write_bytes(path.read_bytes()[:-200])
    with pytest.raises(ValueError):
        ovf.read_ovf(path)


def test_cli_summary(tmp_path, capsys):
    path = tmp_path / "m.ovf"
    write_ovf(path, "4", reference())
    assert ovf.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert f"({NZ}, {NY}, {NX}, 3)" in out
