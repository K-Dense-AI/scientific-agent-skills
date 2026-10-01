"""Native tiny-array checks for the documented Zarr 3.4 workflow."""
from __future__ import annotations

import functools
from pathlib import Path
import re
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

zarr = pytest.importorskip("zarr", minversion="3.4.0")
np = pytest.importorskip("numpy")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "zarr-python"


@pytest.mark.parametrize("document", [
    "SKILL.md", "references/chunking_and_compression.md", "references/storage_backends.md",
    "references/integration.md", "references/performance_and_patterns.md", "references/v3_migration.md",
])
def test_documented_local_examples(document, tmp_path, monkeypatch):
    """Execute the actual contextual examples, including CLI migration in order."""
    monkeypatch.chdir(tmp_path)
    namespace = {"__name__": "__example__"}
    for index, (language, code) in enumerate(re.findall(r"```(python|bash)\n(.*?)```", (SKILL_ROOT / document).read_text(), re.S)):
        if "# Illustrative remote:" in code:
            continue
        if language == "python":
            exec(compile(code, f"{document}:block-{index}", "exec"), namespace)
        elif document.endswith("v3_migration.md"):
            cli = Path(sys.executable).with_name("zarr")
            assert cli.exists(), "Install zarr[cli] for the documented migration workflow"
            for command in code.strip().splitlines():
                args = command.split()
                assert args[0] == "zarr"
                subprocess.run([str(cli), *args[1:]], check=True, capture_output=True, text=True)


@pytest.mark.parametrize("format", [2, 3])
def test_lossless_dtype_fill_nan_and_indexing(format):
    values = np.array([[0, -1, np.nan, np.inf], [3, 4, -np.inf, 7]], dtype="f4")
    arr = zarr.create_array(None, data=values, chunks=(1, 2), zarr_format=format)
    np.testing.assert_array_equal(arr[:], values)
    assert arr.dtype == values.dtype
    np.testing.assert_array_equal(arr.vindex[[0, 1], [0, 3]], [0, 7])
    np.testing.assert_array_equal(arr.oindex[[0, 1], [0, 3]], [[0, np.inf], [3, 7]])
    with pytest.raises(zarr.errors.NegativeStepError):
        _ = arr[::-1]


def test_rectilinear_is_opt_in_and_uniform_input_stays_rectilinear():
    with zarr.config.set({"array.rectilinear_chunks": False}):
        with pytest.raises(ValueError, match="experimental"):
            zarr.create_array(None, shape=(4,), dtype="i4", chunks=((2, 2),))
    with zarr.config.set({"array.rectilinear_chunks": True}):
        arr = zarr.create_array(None, shape=(4,), dtype="i4", chunks=((2, 2),))
        assert arr.metadata.chunk_grid.to_dict()["name"] == "rectilinear"
        arr[:] = [1, 2, 3, 4]
        np.testing.assert_array_equal(arr[:], [1, 2, 3, 4])


def test_default_codec_and_stored_size_are_current():
    from zarr.codecs import ZstdCodec
    arr = zarr.create_array(None, data=np.arange(12, dtype="i4"), chunks=(4,))
    assert isinstance(arr.compressors[0], ZstdCodec)
    assert arr.nbytes == 48
    assert isinstance(arr.nbytes_stored(), int) and arr.nbytes_stored() > 0
    with pytest.raises(TypeError):
        zarr.create_array(None, shape=(4,), dtype="i4", compressors="default")


def test_creation_readonly_and_resize_boundary(tmp_path):
    path = tmp_path / "data.zarr"
    arr = zarr.create_array(path, data=np.arange(8), chunks=(4,))
    with pytest.raises(zarr.errors.ContainsArrayError):
        zarr.create_array(path, shape=(8,), dtype="i8")
    read = zarr.open_array(path, mode="r")
    with pytest.raises(ValueError, match="read.only"):
        read[0] = 9
    arr.resize((5,))
    arr.resize((8,))
    # Boundary chunk survives shrinking; do not assume trailing values are erased.
    np.testing.assert_array_equal(arr[:], np.arange(8))
    with pytest.raises(ValueError):
        zarr.create_array(None, shape=(2,), dtype="i4", data=np.arange(2))


def test_missing_chunk_policy_is_not_a_completeness_check(tmp_path):
    path = tmp_path / "required.zarr"
    arr = zarr.create_array(path, shape=(8,), dtype="i4", chunks=(4,),
                            config={"write_empty_chunks": True})
    arr[:] = np.arange(8)
    (path / "c" / "1").unlink()
    permissive = zarr.open_array(path, mode="r")
    np.testing.assert_array_equal(permissive[4:], np.zeros(4))
    ignored = zarr.open_array(path, mode="r", config={"read_missing_chunks": False})
    np.testing.assert_array_equal(ignored[4:], np.zeros(4))
    with zarr.config.set({"array.read_missing_chunks": False}):
        strict = zarr.open_array(path, mode="r")
        with pytest.raises(zarr.errors.ChunkNotFoundError):
            _ = strict[:]


@pytest.mark.parametrize("format", [2, 3])
def test_consolidation_can_hide_new_children(format):
    store = zarr.storage.MemoryStore()
    root = zarr.open_group(store, mode="w-", zarr_format=format)
    root.create_array("before", data=np.arange(4), chunks=(2,))
    zarr.consolidate_metadata(store)
    root.create_array("after", data=np.arange(3), chunks=(3,))
    cached = zarr.open_group(store, mode="r", use_consolidated=True)
    fresh = zarr.open_group(store, mode="r", use_consolidated=False)
    assert "after" not in cached and "after" in fresh
    np.testing.assert_array_equal(fresh["after"][:], np.arange(3))


def test_metadata_migration_does_not_copy_payloads(tmp_path):
    from zarr.metadata.migrate_v3 import migrate_v2_to_v3
    source = zarr.storage.LocalStore(tmp_path / "source")
    dest = zarr.storage.LocalStore(tmp_path / "metadata-only")
    values = np.arange(1, 9, dtype="i4")
    zarr.create_array(source, data=values, chunks=(4,), zarr_format=2, compressors=None)
    migrate_v2_to_v3(input_store=source, output_store=dest)
    actual = zarr.open_array(dest, mode="r", zarr_format=3)
    np.testing.assert_array_equal(actual[:], np.zeros_like(values))
    assert not np.array_equal(actual[:], values)
    np.testing.assert_array_equal(zarr.open_array(source, mode="r")[:], values)


def test_copy_preserves_fill_and_attributes_without_aliasing():
    source = zarr.create_array(None, data=np.arange(12, dtype="i4"), chunks=(4,),
                               fill_value=-99, attributes={"units": "counts", "meta": {"ids": ["a"]}})
    dest = zarr.from_array(None, data=source)
    assert dest.fill_value == -99 and dest.chunks == source.chunks
    np.testing.assert_array_equal(dest[:], source[:])
    dest.attrs["meta"]["ids"].append("b")
    assert source.attrs["meta"]["ids"] == ["a"]


@pytest.mark.parametrize("format, expected_zero_missing", [(2, True), (3, False)])
def test_xarray_fill_semantics(format, expected_zero_missing):
    xr = pytest.importorskip("xarray")
    store = zarr.storage.MemoryStore()
    root = zarr.open_group(store, mode="w-", zarr_format=format)
    kwargs = {"dimension_names": ("sample",)} if format == 3 else {"attributes": {"_ARRAY_DIMENSIONS": ["sample"]}}
    root.create_array("value", data=np.array([0, 1], dtype="i4"), chunks=(2,), fill_value=0, **kwargs)
    with xr.open_zarr(store, consolidated=False) as ds:
        assert bool(np.isnan(ds.value.values[0])) == expected_zero_missing
        assert ds.value.values[1] == 1


@pytest.mark.parametrize("sharded", [False, True])
def test_http_array_read_on_loopback(tmp_path, sharded):
    """Real GET/HEAD/range requests validate the adapter without an external service."""
    values = np.arange(24, dtype="i4")
    zarr.create_array(tmp_path / "served.zarr", data=values, chunks=(4,),
                      shards=(12,) if sharded else None)
    requests = []
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            request_range = self.headers.get("Range")
            requests.append((self.path, request_range))
            if request_range is None:
                return super().do_GET()
            path = Path(self.translate_path(self.path))
            if not path.is_file():
                return self.send_error(404)
            data = path.read_bytes()
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", request_range)
            assert match is not None
            low, high = match.groups()
            if not low:
                start, stop = max(0, len(data) - int(high)), len(data)
            else:
                start, stop = int(low), min(len(data), int(high) + 1) if high else len(data)
            self.send_response(206)
            self.send_header("Content-Length", str(stop - start))
            self.send_header("Content-Range", f"bytes {start}-{stop - 1}/{len(data)}")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(data[start:stop])

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(tmp_path)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/served.zarr"
        read = zarr.open_array(url, mode="r")
        np.testing.assert_array_equal(read[2:5], values[2:5])
        if sharded:
            assert any(byte_range for _, byte_range in requests)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_provider_option_constructors_without_cloud_requests():
    pytest.importorskip("s3fs")
    pytest.importorskip("gcsfs")
    from zarr.storage import FsspecStore
    s3 = FsspecStore.from_url("s3://example-bucket/prefix", storage_options={"anon": True}, read_only=True)
    gs = FsspecStore.from_url("gs://example-bucket/prefix", storage_options={"token": "anon", "project": "example"}, read_only=True)
    assert s3.path == "example-bucket/prefix" and s3.read_only
    assert gs.path == "example-bucket/prefix" and gs.read_only
    assert s3.fs.asynchronous and gs.fs.asynchronous
