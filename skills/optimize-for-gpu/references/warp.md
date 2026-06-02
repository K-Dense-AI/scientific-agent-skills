# NVIDIA Warp Reference — GPU Simulation & Spatial Computing

NVIDIA Warp is a Python framework for writing high-performance simulation and graphics code. It JIT-compiles Python functions decorated with `@wp.kernel` into efficient C++/CUDA code that runs on CPU or GPU. Warp is designed specifically for spatial computing — physics simulation, robotics, geometry processing, and differentiable programming — with rich built-in types (vectors, matrices, quaternions, transforms) and spatial primitives (meshes, volumes, hash grids, BVH).

Unlike Numba CUDA (which gives you raw thread/block control) or CuPy (which replaces NumPy ops), Warp provides a higher-level programming model with built-in support for differentiable simulation, spatial queries, and tile-based cooperative operations.

## Table of Contents

1. [Installation](#installation)
2. [When to Use Warp vs Other Libraries](#when-to-use-warp-vs-other-libraries)
3. [Kernels and Launch](#kernels-and-launch)
4. [Arrays](#arrays)
5. [Data Types](#data-types)
6. [Spatial Computing Primitives](#spatial-computing-primitives)
7. [Tile-Based Programming](#tile-based-programming)
8. [Differentiability](#differentiability)
9. [Streams, Events, and CUDA Graphs](#streams-events-and-cuda-graphs)
10. [Random Number Generation](#random-number-generation)
11. [Interoperability](#interoperability)
12. [Performance Optimization](#performance-optimization)
13. [Common Patterns](#common-patterns)
14. [Common Pitfalls](#common-pitfalls)

---

## Installation

```bash
uv add warp-lang              # CUDA 12 runtime (most common)
# uv add warp-lang[examples]  # Includes USD and example dependencies
```

Requires CUDA driver >= 525.60.13 (Linux) or 528.33 (Windows).

Verify installation:

```python
import warp as wp
wp.init()
# Prints device info, CUDA version, kernel cache location
```

---

## When to Use Warp vs Other Libraries

| Use Case | Best Choice | Why |
|----------|------------|-----|
| Physics simulation (particles, cloth, fluids) | **Warp** | Built-in spatial primitives, differentiable, simulation-oriented |
| Geometry processing (meshes, ray casting, SDFs) | **Warp** | Native mesh/volume/BVH types, spatial queries |
| Differentiable simulation for ML training | **Warp** | Automatic forward/backward AD, PyTorch/JAX integration |
| Robotics (kinematics, dynamics, control) | **Warp** | Transforms, quaternions, spatial vectors built-in |
| NumPy array math (FFT, linear algebra, sorting) | **CuPy** | Drop-in NumPy replacement, wraps cuBLAS/cuFFT |
| Custom CUDA kernels with raw thread control | **Numba** | Direct CUDA programming model, shared memory |
| Data wrangling / ETL on tabular data | **cuDF** | pandas API on GPU |
| ML training (sklearn-style) | **cuML** | scikit-learn API on GPU |

Warp and Numba both compile Python to CUDA, but serve different niches:
- **Warp** excels at simulation/spatial workloads with its rich type system (vec3, quat, transform, mesh, volume) and automatic differentiation
- **Numba** excels at raw CUDA programming where you need explicit thread/block control, shared memory management, and atomic operations on arbitrary data

---

## Kernels and Launch

### Defining Kernels

```python
import warp as wp

@wp.kernel
def compute_forces(positions: wp.array(dtype=wp.vec3),
                   velocities: wp.array(dtype=wp.vec3),
                   forces: wp.array(dtype=wp.vec3),
                   dt: float):
    tid = wp.tid()

    pos = positions[tid]
    vel = velocities[tid]

    # Gravity
    force = wp.vec3(0.0, -9.81, 0.0)

    forces[tid] = force
```

### Launching Kernels

```python
# 1D launch
wp.launch(kernel=compute_forces,
          dim=num_particles,
          inputs=[positions, velocities, forces, 0.01],
          device="cuda")

# 2D launch (e.g., image processing)
wp.launch(kernel=compute_image, dim=(1024, 1024), inputs=[img], device="cuda")

# 3D launch
wp.launch(kernel=compute_field, dim=(nx, ny, nz), inputs=[field], device="cuda")
```

Inside 2D/3D kernels, retrieve indices with:

```python
i, j = wp.tid()       # 2D
i, j, k = wp.tid()    # 3D
```

### User Functions

```python
@wp.func
def spring_force(x0: wp.vec3, x1: wp.vec3, rest_length: float, stiffness: float):
    delta = x1 - x0
    length = wp.length(delta)
    direction = delta / length
    return stiffness * (length - rest_length) * direction
```

Functions can be called from kernels, support overloading, and can return multiple values.

### User Structs

```python
@wp.struct
class Particle:
    pos: wp.vec3
    vel: wp.vec3
    mass: float
    active: int
```

---

## Arrays

Warp arrays are typed, device-aware containers (1D to 4D):

```python
# Allocate
positions = wp.zeros(n, dtype=wp.vec3, device="cuda")
grid = wp.empty(shape=(nx, ny, nz), dtype=float, device="cuda")

# From NumPy
import numpy as np
data = np.random.rand(1000, 3).astype(np.float32)
wp_data = wp.from_numpy(data, dtype=wp.vec3, device="cuda")

# Back to NumPy (synchronizes GPU automatically)
np_data = wp_data.numpy()

# Array math operators
c = 2.0 * a + b   # Element-wise, GPU-accelerated
c *= 10.0          # In-place
```

Type aliases for kernel signatures: `wp.array2d`, `wp.array3d`, `wp.array4d`.

---

## Data Types

### Scalars
`bool`, `int8`, `uint8`, `int16`, `uint16`, `int32` (alias: `int`), `uint32`, `int64`, `uint64`, `float16`, `float32` (alias: `float`), `float64`

### Vectors
`vec2`, `vec3`, `vec4` — float32 by default. Variants for every scalar type: `vec3f`, `vec3d`, `vec3h`, `vec3i`, etc.

```python
v = wp.vec3(1.0, 2.0, 3.0)
length = wp.length(v)
normalized = wp.normalize(v)
d = wp.dot(a, b)
c = wp.cross(a, b)
```

### Matrices
`mat22`, `mat33`, `mat44` — row-major. Variants: `mat33f`, `mat33d`, `mat33h`.

```python
m = wp.mat33(1.0, 0.0, 0.0,
             0.0, 1.0, 0.0,
             0.0, 0.0, 1.0)
inv = wp.inverse(m)
det = wp.determinant(m)
result = m * v  # Matrix-vector multiply
```

### Quaternions
`quat` (i, j, k, w layout where w is real part)

```python
q = wp.quat_from_axis_angle(wp.vec3(0.0, 1.0, 0.0), 3.14159 / 2.0)
rotated = wp.quat_rotate(q, wp.vec3(1.0, 0.0, 0.0))
q_combined = wp.mul(q1, q2)  # Compose rotations
```

### Transforms
`transform` — 7D (position vec3 + quaternion)

```python
t = wp.transform(wp.vec3(1.0, 2.0, 3.0), wp.quat_identity())
world_point = wp.transform_point(t, local_point)
world_dir = wp.transform_vector(t, local_dir)
```

### Spatial Vectors and Matrices
`spatial_vector` (6D), `spatial_matrix` (6x6) — for rigid body dynamics.

---

## Spatial Computing Primitives

### Meshes (`wp.Mesh`)

Triangle mesh with BVH for fast ray casting and closest-point queries:

```python
# Create mesh from vertices and triangle indices
mesh = wp.Mesh(points=vertices,     # wp.array(dtype=wp.vec3)
               indices=triangles)   # wp.array(dtype=int), flattened (v0,v1,v2,...)

# Query in kernel
@wp.kernel
def raycast(mesh_id: wp.uint64, origins: wp.array(dtype=wp.vec3),
            directions: wp.array(dtype=wp.vec3), hits: wp.array(dtype=float)):
    tid = wp.tid()
    query = wp.mesh_query_ray(mesh_id, origins[tid], directions[tid], 1000.0)
    if query.result:
        hits[tid] = query.t  # Hit distance

wp.launch(raycast, dim=n, inputs=[mesh.id, origins, dirs, hits])

# Update vertex positions (topology stays fixed)
mesh.points = new_positions
mesh.refit()  # Rebuild BVH
```

### Hash Grids (`wp.HashGrid`)

Spatial hashing for particle neighbor queries (DEM, SPH):

```python
grid = wp.HashGrid(dim_x=128, dim_y=128, dim_z=128, device="cuda")
grid.build(points=particle_positions, radius=search_radius)

@wp.kernel
def find_neighbors(grid_id: wp.uint64, positions: wp.array(dtype=wp.vec3)):
    tid = wp.tid()
    pos = positions[tid]

    query = wp.hash_grid_query(grid_id, pos, search_radius)
    index = int(0)
    while wp.hash_grid_query_next(query, index):
        neighbor_pos = positions[index]
        dist = wp.length(pos - neighbor_pos)
        if dist < search_radius:
            # Process neighbor
            ...
```

### Volumes (`wp.Volume`)

Sparse volumetric grids based on NanoVDB (SDFs, velocity fields, smoke):

```python
# Load from NanoVDB file
volume = wp.Volume.load_from_nvdb("field.nvdb")

# Create from NumPy (dense → sparse)
volume = wp.Volume.load_from_numpy(numpy_3d_array, bg_value=0.0)

# Sample in kernel
@wp.kernel
def sample_sdf(volume_id: wp.uint64, points: wp.array(dtype=wp.vec3),
               distances: wp.array(dtype=float)):
    tid = wp.tid()
    # Trilinear interpolation in world space
    uvw = wp.volume_world_to_index(volume_id, points[tid])
    distances[tid] = wp.volume_sample(volume_id, uvw, wp.Volume.LINEAR)
```

### BVH (`wp.Bvh`)

Bounding volume hierarchy for ray and AABB intersection queries:

```python
bvh = wp.Bvh(lowers=box_mins, uppers=box_maxs)

# Ray query
query = wp.bvh_query_ray(bvh.id, ray_origin, ray_dir)
# AABB overlap query
query = wp.bvh_query_aabb(bvh.id, aabb_min, aabb_max)
```

### Marching Cubes

Isosurface extraction from 3D scalar fields:

```python
mc = wp.MarchingCubes(nx=128, ny=128, nz=128, device="cuda")
mc.surface(field=sdf_array, threshold=0.0)

vertices = mc.verts    # wp.array(dtype=wp.vec3)
triangles = mc.indices # wp.array(dtype=int)
```

---

## Tile-Based Programming

Warp's tile API enables cooperative block-level operations (similar to Triton), using shared memory and Tensor Cores:

```python
TILE_M = wp.constant(16)
TILE_N = wp.constant(16)
TILE_K = wp.constant(16)
TILE_THREADS = 64

@wp.kernel
def tile_gemm(A: wp.array2d(dtype=float), B: wp.array2d(dtype=float),
              C: wp.array2d(dtype=float)):
    i, j = wp.tid()

    sum = wp.tile_zeros(shape=(TILE_M, TILE_N), dtype=wp.float32)
    count = int(A.shape[1] / TILE_K)

    for k in range(count):
        a = wp.tile_load(A, shape=(TILE_M, TILE_K), offset=(i * TILE_M, k * TILE_K))
        b = wp.tile_load(B, shape=(TILE_K, TILE_N), offset=(k * TILE_K, j * TILE_N))
        wp.tile_matmul(a, b, sum)

    wp.tile_store(C, sum, offset=(i * TILE_M, j * TILE_N))

wp.launch_tiled(tile_gemm, dim=(M // TILE_M, N // TILE_N),
                inputs=[A, B, C], block_dim=TILE_THREADS)
```

Key tile operations:
- **Construction**: `tile_zeros`, `tile_ones`, `tile_load`, `tile_from_thread`
- **Math**: `tile_matmul`, `tile_fft`, `tile_ifft`, `tile_cholesky`, `tile_cholesky_solve`
- **Reductions**: `tile_sum`, `tile_min`, `tile_max`, `tile_reduce`
- **IO**: `tile_load`, `tile_store`, `tile_atomic_add`
- **Arithmetic**: `+`, `-`, `*`, `/` operators on tiles
- **Spatial queries**: `tile_bvh_query_aabb`, `tile_mesh_query_aabb`

SIMT↔Tile bridging: `wp.tile(scalar_value)` creates a tile from per-thread values; `wp.untile(tile)` extracts per-thread values back.

---

## Differentiability

Warp generates forward and backward (adjoint) kernels automatically, enabling gradient-based optimization and ML integration:

```python
# Arrays participating in gradients need requires_grad=True
a = wp.zeros(1024, dtype=wp.vec3, device="cuda", requires_grad=True)

# Record forward pass
tape = wp.Tape()
with tape:
    wp.launch(kernel=compute1, inputs=[a, b], device="cuda")
    wp.launch(kernel=compute2, inputs=[c, d], device="cuda")
    wp.launch(kernel=loss_fn, inputs=[d, loss], device="cuda")

# Backward pass
tape.backward(loss)

# Access gradients
grad_a = tape.gradients[a]
```

Key features:
- Automatic adjoint code generation for all kernels
- `wp.Tape` records and replays computation graphs
- Integrates with PyTorch autograd and JAX JIT
- Custom gradient functions via `@wp.func_grad`
- Jacobian computation support

---

## Streams, Events, and CUDA Graphs

```python
# Streams for concurrent execution
stream1 = wp.Stream("cuda:0")
stream2 = wp.Stream("cuda:0")
wp.launch(kernel1, ..., stream=stream1)
wp.launch(kernel2, ..., stream=stream2)

# CUDA Graph capture (eliminates Python launch overhead)
with wp.ScopedCapture() as capture:
    wp.launch(kernel1, ...)
    wp.launch(kernel2, ...)
    wp.launch(kernel3, ...)

# Replay graph many times with near-zero CPU overhead
for _ in range(1000):
    wp.capture_launch(capture.graph)
```

---

## Random Number Generation

Uses PCG (Permuted Congruential Generator) — initialize per-thread:

```python
@wp.kernel
def monte_carlo(samples: wp.array(dtype=wp.vec3), seed: int):
    tid = wp.tid()
    rng = wp.rand_init(seed, tid)  # Unique sequence per thread

    x = wp.randf(rng)  # [0, 1)
    y = wp.randf(rng)
    z = wp.randf(rng)
    samples[tid] = wp.vec3(x, y, z)
```

Use different seeds between launches to avoid correlated sequences.

---

## Interoperability

### NumPy (zero-copy on CPU)
```python
np_array = warp_array.numpy()          # GPU → CPU copy, CPU → zero-copy view
wp_array = wp.from_numpy(np_array, dtype=wp.vec3, device="cuda")
```

### PyTorch (zero-copy, autograd support)
```python
torch_tensor = wp.to_torch(warp_array)      # Zero-copy
warp_array = wp.from_torch(torch_tensor)     # Zero-copy
# Gradient arrays are converted between Warp tape and PyTorch autograd
```

### CuPy/Numba (zero-copy via CUDA Array Interface)
```python
# CuPy arrays can be passed directly to Warp kernels
# Warp arrays expose __cuda_array_interface__
cupy_arr = cp.asarray(warp_array)  # Zero-copy
```

### JAX (zero-copy via DLPack)
```python
jax_array = wp.to_jax(warp_array)
warp_array = wp.from_jax(jax_array)
# @warp.jax_experimental.jax_kernel() for JAX primitive integration
```

### DLPack (universal zero-copy)
```python
# Import from any DLPack framework
warp_array = wp.from_dlpack(external_array)
# Export
external = framework.from_dlpack(warp_array)
```

---

## Performance Optimization

### 1. Use CUDA Graphs for Repeated Launches

If you launch the same sequence of kernels many times (simulation loop), CUDA graph capture eliminates Python overhead:

```python
with wp.ScopedCapture() as capture:
    for _ in range(substeps):
        wp.launch(integrate, ...)
        wp.launch(collide, ...)

for frame in range(num_frames):
    wp.capture_launch(capture.graph)
```

### 2. Minimize Host-Device Transfers

Keep data on GPU. Use `wp.array` on device, avoid `.numpy()` in inner loops.

### 3. Use Tile Operations for Reductions and GEMM

Tile-based reductions are 50x+ faster than per-thread atomics. Use `wp.tile()` + `wp.tile_sum()` + `wp.tile_atomic_add()` instead of `wp.atomic_add()`.

### 4. Prefer float32 Over float64

GPU float32 throughput is 2x-32x higher than float64.

### 5. Kernel Caching

Warp caches compiled kernels between runs. First launch compiles (can take seconds); subsequent runs load from cache in milliseconds.

### 6. Object Lifetime

Keep Python references to spatial primitives (Mesh, HashGrid, Volume, BVH) alive while their `.id` is in use. Garbage collection of the Python object while a kernel holds the ID causes undefined behavior.

---

## Common Patterns

### Particle Simulation

```python
@wp.kernel
def integrate_particles(positions: wp.array(dtype=wp.vec3),
                        velocities: wp.array(dtype=wp.vec3),
                        forces: wp.array(dtype=wp.vec3),
                        dt: float):
    tid = wp.tid()
    vel = velocities[tid] + forces[tid] * dt
    pos = positions[tid] + vel * dt

    velocities[tid] = vel
    positions[tid] = pos
```

### Mesh Ray Casting

```python
@wp.kernel
def cast_rays(mesh_id: wp.uint64,
              ray_origins: wp.array(dtype=wp.vec3),
              ray_dirs: wp.array(dtype=wp.vec3),
              hit_points: wp.array(dtype=wp.vec3)):
    tid = wp.tid()
    query = wp.mesh_query_ray(mesh_id, ray_origins[tid], ray_dirs[tid], 1e6)
    if query.result:
        hit_points[tid] = ray_origins[tid] + ray_dirs[tid] * query.t
```

### Differentiable Simulation with PyTorch

```python
import torch
import warp as wp

# Warp kernel for simulation
@wp.kernel
def simulate(state: wp.array(dtype=wp.vec3), params: wp.array(dtype=float),
             output: wp.array(dtype=wp.vec3)):
    tid = wp.tid()
    # ... physics computation ...

# PyTorch training loop
optimizer = torch.optim.Adam([torch_params], lr=1e-3)

for epoch in range(100):
    wp_params = wp.from_torch(torch_params)
    tape = wp.Tape()
    with tape:
        wp.launch(simulate, dim=n, inputs=[state, wp_params, output])
        wp.launch(loss_kernel, dim=1, inputs=[output, target, loss])

    tape.backward(loss)
    grad = wp.to_torch(tape.gradients[wp_params])
    torch_params.grad = grad
    optimizer.step()
```

### SPH Fluid with Hash Grid

```python
grid = wp.HashGrid(128, 128, 128, device="cuda")

@wp.kernel
def compute_density(grid_id: wp.uint64, positions: wp.array(dtype=wp.vec3),
                    densities: wp.array(dtype=float), radius: float):
    tid = wp.tid()
    pos = positions[tid]
    density = float(0.0)

    query = wp.hash_grid_query(grid_id, pos, radius)
    index = int(0)
    while wp.hash_grid_query_next(query, index):
        dist = wp.length(pos - positions[index])
        if dist < radius:
            # SPH kernel
            q = dist / radius
            density += (1.0 - q) * (1.0 - q) * (1.0 - q)

    densities[tid] = density

# Each timestep:
grid.build(points=positions, radius=h)
wp.launch(compute_density, dim=n, inputs=[grid.id, positions, densities, h])
```

---

## Common Pitfalls

1. **Forgetting type annotations** — All kernel parameters must be typed. Warp infers types from annotations, not runtime values.

2. **Using Python data structures in kernels** — No lists, dicts, or sets. Use `wp.array`, `wp.vec3`, `@wp.struct`.

3. **Calling `wp.tid()` in user functions** — `wp.tid()` only works in kernels. Pass the thread index as a parameter to `@wp.func` functions.

4. **Object lifetime issues** — Spatial primitives (Mesh, HashGrid, Volume, BVH) must stay alive (referenced in Python) while their `.id` is used in kernels. Letting the Python object get garbage-collected causes crashes.

5. **Expecting in-place ops to be differentiable** — Warp's autodiff doesn't support in-place array modifications. Write to separate output arrays for gradient computation.

6. **Not using `requires_grad=True`** — Arrays participating in gradient computation must be created with `requires_grad=True`.

7. **Launching with wrong device** — Arrays and kernel launch must be on the same device. Use `device="cuda"` consistently.

8. **First-launch compilation time** — The first kernel launch triggers JIT compilation (can take seconds). Subsequent runs use the cache. Don't benchmark the first run.

9. **Using tuples instead of Warp types** — `(1.0, 2.0, 3.0)` is invalid in kernel scope. Use `wp.vec3(1.0, 2.0, 3.0)`.

10. **Block size on CPU** — Tile operations on CPU use `block_dim=1`, which changes behavior. Design cross-device kernels to be independent of block size.
