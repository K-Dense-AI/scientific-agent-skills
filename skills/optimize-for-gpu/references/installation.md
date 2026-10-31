# Installation

Per-library install commands, CUDA version selection, and environment setup.

Use `uv add` in standalone examples to match this repository's convention. If the user's project
already uses another package manager, follow that project rather than rewriting its tooling.

Maintained RAPIDS examples target **26.08**, the current published stable line at review on
2026-10-01; 26.10 is nightly. Use the [release-specific platform matrix](https://docs.nvidia.com/datascience/platform-support/#rapids-26-08)
and [installation selector](https://docs.nvidia.com/datascience/install/): Python 3.11-3.14,
Linux x86_64/aarch64 with glibc >=2.28, or supported Linux under WSL2. Native macOS is not
supported. The 26.08 matrix lists CUDA 12.2-12.9 with driver 535+ and Volta+, or CUDA
13.0-13.3 with driver 580+ and Turing+. Confirm the exact GPU and toolkit combination;
a newer driver alone does not supply all compiler/runtime components.

26.08 requires **NumPy >=2 and CuPy >=14**; cuDF now targets **pandas 3**.
Do not combine these pins with cuxfilter 26.06 or cuSpatial 25.04: each legacy stack needs its
own environment. Choose **one** CUDA wheel family throughout an environment, never both.
Current maintained wheels, including cuGraph and nx-cugraph, are published on PyPI;
the optional NVIDIA index remains in commands for upstream consistency. cuSpatial still
needs that index. Commands are illustrative and were not installed on CUDA hardware in this review.

WSL2 has additional limits: the installation guide documents single-GPU support and no GDS.
Warp is a separate package with a CPU-only macOS wheel; that does not enable CUDA or Metal on macOS.

```bash
# CuPy (choose the right CUDA version; CuPy 14+ supports CUDA 12/13 only)
uv add "cupy-cuda12x==14.2.*"          # For CUDA 12.x
uv add "cupy-cuda13x==14.2.*"          # For CUDA 13.x

# Numba-CUDA compatibility path (maintenance mode; installs numba automatically)
uv add "numba-cuda[cu12]==0.30.*"      # use [cu13] for CUDA 13
# For new kernel projects, evaluate Numba-CUDA-MLIR and its migration guide first.

# Warp (simulation, spatial computing, differentiable programming)
uv add "warp-lang==1.17.*"              # CUDA 12 runtime included; CUDA 13 builds are on GitHub Releases only

# cuDF (RAPIDS)
uv add --extra-index-url=https://pypi.nvidia.com "cudf-cu12==26.8.*"
# For cudf.pandas accelerator mode, that's all you need
# Load it with: python -m cudf.pandas your_script.py

# cuML (RAPIDS machine learning)
uv add --extra-index-url=https://pypi.nvidia.com "cuml-cu12==26.8.*"
# For cuml.accel accelerator mode (zero-change sklearn acceleration):
# Load it with: python -m cuml.accel your_script.py

# cuGraph (RAPIDS graph analytics)
uv add --extra-index-url=https://pypi.nvidia.com "cugraph-cu12==26.8.*"    # Core cuGraph
uv add --extra-index-url=https://pypi.nvidia.com "nx-cugraph-cu12==26.8.*" # NetworkX backend
# For nx-cugraph zero-change NetworkX acceleration:
# NX_CUGRAPH_AUTOCONFIG=True python your_script.py

# KvikIO (high-performance GPU file IO)
uv add --extra-index-url=https://pypi.nvidia.com "kvikio-cu12==26.8.*"
# Optional: uv add "zarr==3.*"   # For Zarr GPU backend support

# cuxfilter (separate legacy environment) — SUNSET: 26.06 is the final release
uv add --extra-index-url=https://pypi.nvidia.com "cuxfilter-cu12==26.6.*"
# Depends on cuDF — installs it automatically

# cuCIM (RAPIDS image processing — scikit-image on GPU)
uv add --extra-index-url=https://pypi.nvidia.com "cucim-cu12==26.8.*"

# cuVS (RAPIDS vector search)
uv add --extra-index-url=https://pypi.nvidia.com "cuvs-cu12==26.8.*"

# cuSpatial (geospatial) — ARCHIVED: frozen at 25.04, pins cudf-cu12==25.4.*
# Install only in a dedicated environment; NVIDIA index required
uv add --extra-index-url=https://pypi.nvidia.com "cuspatial-cu12==25.4.*"

# RAFT (low-level GPU primitives)
uv add --extra-index-url=https://pypi.nvidia.com "pylibraft-cu12==26.8.*"   # Core primitives
uv add --extra-index-url=https://pypi.nvidia.com "raft-dask-cu12==26.8.*"   # Multi-GPU support (optional)
```

To check CUDA availability after installation:

```python
# CuPy
import cupy as cp
print(cp.cuda.runtime.getDeviceCount())  # Should be >= 1

# Numba
from numba import cuda
print(cuda.is_available())               # Should be True
print(cuda.detect())                     # Shows GPU details

# cuDF
import cudf
print(cudf.Series([1, 2, 3]))           # Should print a GPU series

# cuML
import cuml
print(cuml.__version__)                  # Should print version

# cuGraph
import cugraph
print(cugraph.__version__)               # Should print version

# Warp
import warp as wp
wp.init()                                # Should print device info

# KvikIO
import kvikio
import kvikio.cufile_driver
print(kvikio.cufile_driver.get("is_gds_available"))  # Capability, not proof every I/O used GDS

# cuxfilter
import cuxfilter
print(cuxfilter.__version__)             # Should print version

# cuCIM
from cucim.skimage.filters import gaussian
import cupy as cp
print(gaussian(cp.zeros((8, 8), dtype=cp.float32), sigma=1).shape)

# cuVS
from cuvs.neighbors import cagra
import cupy as cp
dataset = cp.random.rand(1000, 128, dtype=cp.float32)
index = cagra.build(cagra.IndexParams(), dataset)
print("cuVS working")                    # Should print confirmation

# cuSpatial
import cuspatial
from shapely.geometry import Point
gs = cuspatial.GeoSeries([Point(0, 0)])
print("cuSpatial working")              # Should print confirmation

# RAFT (pylibraft)
from pylibraft.common import DeviceResources
handle = DeviceResources()
handle.sync()
print("pylibraft is working")
```
