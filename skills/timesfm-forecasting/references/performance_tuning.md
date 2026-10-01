# Tune the actual workload

Start with `per_core_batch_size=1`, a context such as 512 and a horizon rounded
to 128. Record wall time and peak resident/device memory for representative
lengths before increasing batch size. No table can guarantee a batch size from
VRAM alone: contexts, horizon, copies, backend, compiler and concurrent work matter.

The 2.5 `torch_compile` loader option defaults True. Use False for first-load
smokes; separately benchmark whether compilation pays off for repeated calls.
`model.compile(ForecastConfig(...))` is still needed with either setting.
The continuous quantile head supports <=1,024 horizon. Symmetric flip averaging
adds a second decode pass. Reduce context only after evaluating its accuracy cost.

For CUDA float32 matmul, `torch.set_float32_matmul_precision("high")` can trade
internal precision for speed on supported hardware; it is not a universal
accuracy-preserving setting and does not make CPU/MPS use CUDA. Use
`torch.cuda.get_device_properties(0).total_memory`, not `.total_mem`.

Process many series in outer chunks if input/output arrays are large; persist
outputs as you go instead of retaining every array. Passing a copied list avoids
2.5's in-place padding-list growth. `gc.collect()` or `torch.cuda.empty_cache()`
does not free live model tensors or fix an oversized workload. After OOM,
reduce the actual context/batch/horizon allocation and rerun the representative
smoke, then reassess forecast quality.

Backend details: [TimesFM torch source](https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm/timesfm_2p5/timesfm_2p5_torch.py),
[PyTorch precision API](https://docs.pytorch.org/docs/stable/generated/torch.set_float32_matmul_precision.html).
