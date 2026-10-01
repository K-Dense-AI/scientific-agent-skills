# Complexity, entropy, fractals, and RQA

Checked **2026-10-01** against NeuroKit2 0.2.13 stable runtime/source,
the official Complexity API, and the NeuroKit2 complexity comparison paper.

## Return convention changed from older examples

Most stable 0.2.13 complexity functions return:

```python
value, info = function(signal, ...)
```

Examples:

```python
sampen, sampen_info = nk.entropy_sample(
    signal, delay=1, dimension=2, tolerance="sd"
)
dfa, dfa_info = nk.fractal_dfa(signal)
hfd, hfd_info = nk.fractal_higuchi(signal, k_max=10)
lyapunov, lyapunov_info = nk.complexity_lyapunov(signal)
fi, fi_info = nk.fisher_information(signal)
```

Do not treat the tuple as a scalar. The current public name is
`fisher_information()`; `information_fisher()` is not exported.

Exceptions exist: for example, `mutual_information()` returns a float. Check the
stable signature and persist runtime type/schema.

## `complexity()` is a selected panel

```python
features, details = nk.complexity(
    signal,
    which="makowski2022",
    delay=1,
    dimension=2,
    tolerance="sd",
)
```

The default does not compute “all complexity measures.” The pinned 0.2.13 probe
returned a one-row DataFrame with 15 columns:

```text
AttEn, BubbEn, CWPEn, Hjorth, LL,
MFDFA_Asymmetry, MFDFA_Delta, MFDFA_Fluctuation,
MFDFA_Increment, MFDFA_Max, MFDFA_Mean,
MFDFA_Peak, MFDFA_Width, MSPEn, SVDEn
```

The accompanying dict had method-specific details. This panel reflects a published
empirical comparison and implementation choices; it is not a universal optimum for
every signal, endpoint, or population.

## Parameter selection

Phase-space/entropy estimates depend on:

- delay (`tau`);
- embedding dimension (`m`);
- tolerance/radius (`r`);
- scale/coarse-graining;
- symbolization/binning;
- detrending/integration/order;
- sampling rate and bandwidth; and
- usable length and stationarity.

Stable utilities also return metadata:

```python
delay, delay_info = nk.complexity_delay(
    signal, delay_max=100, method="fraser1986", show=False
)
dimension, dimension_info = nk.complexity_dimension(
    signal, delay=delay, dimension_max=10, method="afnn", show=False
)
tolerance, tolerance_info = nk.complexity_tolerance(
    signal,
    method="maxApEn",
    delay=delay,
    dimension=dimension,
    show=False,
)
```

Optimization can return no solution or raise when search bounds are inadequate. Do not
silently replace failure with an arbitrary default. Predefine the algorithm/search
range, report failures, and test sensitivity.

`tolerance="sd"` commonly maps to a fraction of standard deviation, but amplitude
normalization, outliers, and signal length alter it. One conventional parameter set is
not method validation.

## Major stable families

### Entropy

Available functions include approximate, sample, fuzzy, permutation, spectral,
multiscale, dispersion, symbolic-dynamic, SVD, Shannon, Rényi, Tsallis, and other
variants.

Pinned probes confirmed `(value, info)` for:

- `entropy_approximate()`;
- `entropy_sample()`;
- `entropy_multiscale()`;
- `entropy_permutation()`; and
- `entropy_spectral()`.

Some values are corrected/normalized by default (for example corrected permutation
entropy). Record every parameter and logarithm base. Entropy values from different
algorithms/normalizations are not interchangeable.

### Fractals

Stable functions include Katz, Higuchi, Petrosian, Sevcik, NLD, PSD slope, Hurst,
correlation dimension, DFA/MFDFA, density, line length, and tMF.

`fractal_dfa()` returns `(float, info)` for monofractal mode and can return a
DataFrame-like multifractal summary. Report scales, overlap, integration, detrending
order, q values, and fit diagnostics. Do not interpret alpha values without checking
which regime and preprocessing generated them.

### Lyapunov and RQA

```python
lle, lle_info = nk.complexity_lyapunov(
    signal,
    delay=1,
    dimension=2,
    method="rosenstein1993",
    separation="auto",
)
rqa, rqa_info = nk.complexity_rqa(
    signal,
    dimension=3,
    delay=1,
    tolerance="sd",
    method="python",
)
```

The pinned RQA DataFrame had fields such as `RecurrenceRate`, `Determinism`,
`Laminarity`, `TrappingTime`, line-length/entropy, divergence, and vertical/white-line
statistics. `rqa_info` included full recurrence and distance matrices, which scale
quadratically in signal length. Bound input length and memory.

A positive estimated Lyapunov exponent does not by itself prove deterministic chaos.
RQA results depend strongly on embedding, tolerance, norm, Theiler window, line
thresholds, nonstationarity, and sample size.

## Signal preparation

1. Preserve raw signal and physical unit.
2. Apply modality-specific artifact/missing-data policy first.
3. Define the analysis window and usable length.
4. Decide detrending, filtering, resampling, and standardization before viewing group
   effects.
5. Check stationarity or segment according to the estimand.
6. Compute prespecified measures and diagnostics.
7. Compare with surrogates/nulls and parameter sensitivity.

Do not apply blanket z-scoring: amplitude-sensitive measures may change, while scale
invariant measures may not. Report both rationale and implementation.

## Length and comparability

There is no universal minimum sample count across complexity measures. Required length
grows with embedding dimension, delay, scale count, tolerance, and estimator. Multiscale
entropy loses points at each coarse-graining scale; RQA and correlation dimension can
be computationally and statistically unstable on short data.

- Use equal-duration/beat-count windows for direct comparisons unless a validated
  correction is used.
- Quantify estimate reliability with simulation/resampling.
- Avoid comparing measures computed at different sample rates or bandwidths without
  explicit validation.
- Return missing/unsupported rather than a numerically convenient but invalid value.

## Interpretation

High entropy can mean noise, not useful complexity. “Healthy complexity,” “complexity
loss,” consciousness, disease, stress, and aging claims require a prespecified theory,
validated acquisition/preprocessing, appropriate controls, and independent evidence.

Do not use these measures for diagnosis, anesthesia/consciousness monitoring, seizure
detection, prognosis, or medical-device validation based on this toolbox alone.

## Reproducible report

Record:

- NeuroKit2 version and function return schema;
- signal type/unit/rate/bandwidth/window/length;
- exclusions, interpolation, filtering, detrending, resampling, normalization;
- algorithm, delay, dimension, tolerance, scales/bins/q/order;
- optimization method/search space and failures;
- fit/convergence diagnostics and runtime warnings;
- surrogate/null and sensitivity results; and
- multiplicity control and participant-level statistical design.

## Sources checked 2026-10-01

- [Official Complexity API](https://neuropsychology.github.io/NeuroKit/functions/complexity.html)
- [Stable v0.2.13 complexity source](https://github.com/neuropsychology/NeuroKit/tree/v0.2.13/neurokit2/complexity)
- [Makowski et al. (2022), empirical comparison using NeuroKit2](https://doi.org/10.3390/e24081036)
- [Richman & Moorman (2000), sample entropy](https://doi.org/10.1152/ajpheart.2000.278.6.H2039)
- [Peng et al. (1995), DFA](https://doi.org/10.1063/1.166141)
- [Costa et al. (2005), multiscale entropy](https://doi.org/10.1103/PhysRevE.71.021906)
