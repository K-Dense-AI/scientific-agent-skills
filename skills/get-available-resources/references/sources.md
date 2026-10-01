# Official Sources and Verification

Reviewed **2026-10-01**. This ledger covers all bundled commands, parsers,
planning assumptions, and reference guidance. Living documentation is not a
claim that every host, driver, or scheduler configuration was exercised.

## Python and psutil

- [psutil 7.2.2 reference](https://psutil.readthedocs.io/stable/index.html) and
  [release source](https://github.com/giampaolo/psutil/tree/release-7.2.2) verify
  `cpu_count(logical=...)`, `Process.cpu_affinity()`, `virtual_memory()`,
  `swap_memory()`, disk semantics, and `psutil.Error` failures. The optional
  tested package remains **7.2.2**, matching the current
  [PyPI release metadata](https://pypi.org/pypi/psutil/json). Development/latest
  documentation can describe a newer version; it does not change this pin.
- [Python os reference](https://docs.python.org/3/library/os.html) verifies
  CPU affinity, `statvfs`, `sysconf`, and CPU-count overrides introduced in
  Python 3.13. The calling-thread/process count is not a cgroup quota detector.
- [CPython 3.14.8 shutil source](https://github.com/python/cpython/blob/v3.14.8/Lib/shutil.py)
  confirms POSIX `disk_usage().free` uses `f_bavail`, not `f_bfree`. Both are
  read separately by the detector when available.
- [Python 3.14.8 concurrent.futures documentation source](https://github.com/python/cpython/blob/v3.14.8/Doc/library/concurrent.futures.rst)
  confirms process-aware defaults, the Windows ProcessPoolExecutor ceiling
  of 61, and the changed process start method.
- [Python 3.14.8 multiprocessing documentation source](https://github.com/python/cpython/blob/v3.14.8/Doc/library/multiprocessing.rst)
  confirms the forkserver/spawn defaults and `os.process_cpu_count()` pool
  default. These are executor-specific constraints; the generic planner does
  not launch an executor or promise that every worker count fits every API.

## Linux, containers, and disk

- [Kernel procfs documentation](https://docs.kernel.org/filesystems/proc.html)
  verifies `MemAvailable`, CPU topology/affinity fields, and the mountinfo
  root/mountpoint fields used to locate a cgroup2 mount.
- [Kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
  verifies `cpu.max`, `cpuset.cpus.effective`, `memory.current`, `memory.high`,
  `memory.max`, hierarchical limits, and namespace-relative membership.
  Hidden ancestors cannot be measured from a restricted mount. `memory.high`
  remains a pressure boundary; remaining capacity is not a reservation.
- [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)
  verifies default unconstrained configuration, quota/period, cpusets, memory,
  and why host-visible swap is not necessarily container-usable swap.
- [OCI Runtime Specification 1.3.0 Linux configuration](https://github.com/opencontainers/runtime-spec/blob/v1.3.0/config-linux.md)
  verifies CPU/memory/device controls independently of container markers.

## NVIDIA

- [nvidia-smi manual](https://docs.nvidia.com/deploy/nvidia-smi/index.html)
  verifies selective `--query-gpu` and `--format=csv,noheader,nounits` queries,
  unsupported `N/A` values, unstable indices, and output compatibility limits.
  The detector requests index/name/memory/driver/compute capability and retries
  without compute capability on a command error. No NVIDIA hardware was
  available for a driver-specific `--help-query-gpu` check in this review.
- [Container Toolkit configuration](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html)
  verifies `NVIDIA_VISIBLE_DEVICES` and driver-capability semantics. These are
  container-start configuration inputs; their presence in a running process
  does not prove kernel device isolation.
- [CUDA visibility](https://docs.nvidia.com/deploy/topics/topic_5_2_1.html) and
  [CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/latest/why-cuda-compatibility.html)
  distinguish application enumeration from management visibility and runtime
  compatibility.
- [MIG device enumeration](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/mig-device-names.html)
  explains why physical management GPU counts are not framework-device counts.

## AMD

- [AMD SMI CLI reference](https://rocm.docs.amd.com/projects/amdsmi/en/latest/how-to/amdsmi-cli-tool.html)
  currently identifies **27.0.0**. It verifies `static --asic --vram --json`,
  unavailable fields, and APU/partition differences. The narrower query avoids
  collecting every static field, including unrelated board and topology data.
- [AMD SMI command source](https://github.com/ROCm/amdsmi/blob/a044536b8d690a9ae5962a93e7596d9eec2030b7/amdsmi_cli/amdsmi_commands.py)
  verifies nested JSON `vram.size: {value, unit}`.
  [The matching C++ implementation](https://github.com/ROCm/amdsmi/blob/a044536b8d690a9ae5962a93e7596d9eec2030b7/src/amd_smi/amd_smi.cc)
  divides byte totals by 1024 squared despite labeling the result `MB`.
  The parser preserves that binary conversion. This pinned source check does
  not establish every installed AMD SMI release's output shape.
- [ROCm SMI CLI reference](https://rocm.docs.amd.com/projects/rocm_smi_lib/en/latest/how-to/use-python.html)
  and [official CLI source](https://github.com/ROCm/rocm_smi_lib/blob/master/python_smi_tools/rocm_smi.py)
  verify the retained `--showproductname --showmeminfo vram --json` fallback
  and flat byte-valued memory fields.
- [ROCm environment variables](https://rocm.docs.amd.com/en/latest/reference/environment-variables/index.html)
  verifies visibility-variable scopes and recommends `ROCR_VISIBLE_DEVICES`
  on Linux and `HIP_VISIBLE_DEVICES` on Windows. The detector does not claim
  to cover every isolation variable or runtime. The old separate GPU-isolation
  URL was inaccessible; the current environment reference and container
  documentation support the bounded guidance retained here.

## Apple, Windows, and Slurm

- [Apple system capabilities](https://developer.apple.com/documentation/kernel/1387446-sysctlbyname/determining_system_capabilities)
  was read through its official documentation JSON representation; it verifies
  `hw.logicalcpu`/`hw.physicalcpu` and performance-level semantics.
  [Archived sysctl manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/sysctl.3.html)
  cross-checks memory reporting.
- [Apple DTS system_profiler discussion](https://developer.apple.com/forums/thread/688443)
  explains integrated/SoC memory interpretation. The fixed `sysctl -n` and
  `system_profiler SPDisplaysDataType -json` probes were executed locally on
  macOS during this review. Intel/AMD display-vendor handling is synthetic,
  and no Metal framework workload was executed.
- [Windows processor groups](https://learn.microsoft.com/en-us/windows/win32/procthread/processor-groups),
  [GetLogicalProcessorInformation](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformation),
  and [GetLogicalProcessorInformationEx](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformationex)
  distinguish topology, group-limited observations, and Windows 11/Server 2022
  defaults spanning groups. Windows behavior was covered by mocks only.
- [Slurm sbatch](https://slurm.schedmd.com/sbatch.html),
  [srun](https://slurm.schedmd.com/srun.html), and
  [CPU management](https://slurm.schedmd.com/cpu_management.html) verify every
  allowlisted allocation variable, compressed task lists, the current
  `SLURM_NODEID` index, memory units/scope, and site-dependent enforcement.
  Scheduler tests are synthetic; no Slurm allocation or accounting call was
  executed. Job/step and heterogeneous-component scope must still be checked
  in the workload's actual environment.

## Verification boundary

The network-free suite exercises Linux cgroup hierarchy/delegated mounts,
Slurm heterogeneous node counts, macOS/Windows probes, legacy/current AMD
parsers, NVIDIA CSV, malformed snapshots, private output, and infeasible
memory plans. All four CLI helpers were exercised on redacted local snapshots.
No stress tests, large allocations, write-capacity probes, device changes,
framework accelerator execution, or scheduler submissions were performed.
