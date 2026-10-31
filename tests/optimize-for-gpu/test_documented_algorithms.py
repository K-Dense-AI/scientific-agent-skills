"""CPU regressions for pure packing and buffer-lifetime logic in GPU examples.

These fakes do not validate CUDA, KvikIO, or cuVS execution. They exercise the
actual documented functions against CPU reference data and asynchronous hazards.
"""
from pathlib import Path
import ast
import re
import textwrap
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "optimize-for-gpu"


def documented_function(reference, name, namespace):
    source = (SKILL_ROOT / "references" / reference).read_text()
    for block in re.findall(r"```python\n(.*?)```", source, re.S):
        try:
            tree = ast.parse(textwrap.dedent(block))
        except SyntaxError:  # Notebook magics are not standalone Python.
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(SKILL_ROOT / "references" / reference), "exec"), namespace)
                return namespace[name]
    raise AssertionError(f"Missing documented function {name}")


@pytest.mark.parametrize("size", [0, 1, 31, 32, 33, 63, 1003])
def test_bitset_inclusion_and_padding(size):
    pack = documented_function("cuvs.md", "pack_allowed_mask", {"np": np})
    allowed = np.random.default_rng(42).integers(0, 2, size=size).astype(bool)
    words = pack(allowed)
    assert words.dtype == np.dtype("uint32")
    decoded = [(int(word) >> bit) & 1 for word in words for bit in range(32)]
    assert decoded[:size] == allowed.tolist()
    assert not any(decoded[size:])
    assert len(words) == (size + 31) // 32


def test_bitset_rejects_two_dimensional_mask():
    pack = documented_function("cuvs.md", "pack_allowed_mask", {"np": np})
    with pytest.raises(ValueError):
        pack(np.ones((2, 3), dtype=bool))


class Stream:
    def __init__(self):
        self.pending = []
        self.results = []

    def synchronize(self):
        self.results.extend(array.copy() for array in self.pending)
        self.pending.clear()


class Reader:
    def __init__(self, data, stream, short_read=False):
        self.data = data
        self.stream = stream
        self.futures = []
        self.short_read = short_read

    def __enter__(self):
        return self

    def __exit__(self, *_):
        assert all(future.consumed for future in self.futures)
        assert not self.stream.pending

    def pread(self, buf, file_offset=0):
        assert not any(np.shares_memory(buf, pending) for pending in self.stream.pending), "I/O overwrote a buffer with unfinished GPU consumers"
        future = SimpleNamespace(consumed=False)

        def get():
            assert not future.consumed, "An I/O future was consumed twice"
            future.consumed = True
            start = file_offset // 4
            buf[:] = self.data[start:start + len(buf)]
            return buf.nbytes - int(self.short_read)

        future.get = get
        self.futures.append(future)
        return future


def pipeline(tmp_path, count, short_read=False):
    data = np.arange(count, dtype=np.float32)
    path = tmp_path / "data.bin"
    path.write_bytes(data.tobytes())
    stream = Stream()
    reader = Reader(data, stream, short_read)
    cp = SimpleNamespace(empty=np.empty, empty_like=np.empty_like, float32=np.float32,
                         cuda=SimpleNamespace(get_current_stream=lambda: stream))
    kvikio = SimpleNamespace(CuFile=lambda *_: reader)
    run = documented_function("kvikio.md", "process_float32_chunks",
                              {"Path": Path, "cp": cp, "kvikio": kvikio})
    return run, path, data, stream, reader


@pytest.mark.parametrize("count,chunk", [(0, 4), (1, 4), (4, 4), (5, 4), (13, 4), (33, 1)])
def test_pipeline_all_chunks_and_async_buffer_lifetime(tmp_path, count, chunk):
    run, path, data, stream, reader = pipeline(tmp_path, count)
    run(path, chunk, stream.pending.append)
    result = np.concatenate(stream.results) if stream.results else np.array([], dtype=np.float32)
    np.testing.assert_array_equal(result, data)
    assert len(reader.futures) == (count + chunk - 1) // chunk


def test_pipeline_drains_io_on_callback_failure(tmp_path):
    run, path, _, stream, reader = pipeline(tmp_path, 13)

    def fail(buf):
        stream.pending.append(buf)
        raise RuntimeError("consumer failed")

    with pytest.raises(RuntimeError, match="consumer failed"):
        run(path, 4, fail)
    assert len(reader.futures) == 2
    assert all(future.consumed for future in reader.futures)


def test_pipeline_rejects_partial_float(tmp_path):
    run, path, _, stream, _ = pipeline(tmp_path, 2)
    path.write_bytes(b"12345")
    with pytest.raises(ValueError, match="complete float32"):
        run(path, 4, stream.pending.append)


def test_pipeline_detects_short_read(tmp_path):
    run, path, _, stream, _ = pipeline(tmp_path, 5, short_read=True)
    with pytest.raises(EOFError, match="Short read"):
        run(path, 4, stream.pending.append)


def test_pipeline_rejects_nonpositive_chunk(tmp_path):
    run, path, _, stream, _ = pipeline(tmp_path, 5)
    with pytest.raises(ValueError, match="positive"):
        run(path, 0, stream.pending.append)
