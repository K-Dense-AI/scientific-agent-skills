# Examples and validation scope

Run all commands from the skill root in the isolated TimesFM environment.
Choose output directories outside the shipped skill tree. Plots require
Matplotlib; GIF generation also requires Pillow.

```bash
python examples/global-temperature/run_forecast.py --output-dir /tmp/timesfm-temperature
python examples/global-temperature/visualize_forecast.py --output-dir /tmp/timesfm-temperature
python examples/global-temperature/generate_animation_data.py --output-dir /tmp/timesfm-temperature
python examples/global-temperature/generate_gif.py --output-dir /tmp/timesfm-temperature
python examples/global-temperature/generate_html.py --output-dir /tmp/timesfm-temperature
python examples/anomaly-detection/detect_anomalies.py --output-dir /tmp/timesfm-anomalies
python examples/covariates-forecasting/demo_covariates.py --output-dir /tmp/timesfm-covariates
```

Global-temperature and anomaly scripts download/use the pinned 2.5 checkpoint
and run preflight. The bundled temperature-shaped values have unverified
provenance; they are illustrative input, not a current NASA/NOAA data release.
Retired generated results were removed instead of relabeling incorrect bands.
The corrected schema rejects legacy results in plot/animation tools.

The covariate demo generates 108 synthetic rows (3 stores x 36 weeks) and plots
known generator components. It does not execute pretrained forecasting or
establish that adding covariates improves a model. Its 24-point context supports
the `xreg + timesfm` example; `timesfm + xreg` requires a longer history (>32).

## Checks before reporting a result

- Check model/package/revision, cadence, target units and forecast origins.
- Retain positions for missing timestamps/values; fit transformations per origin.
- Check all forecast values are finite, output dimensions match, and quantiles
  are ordered. For 2.5 point=q[...,5], while 3.0 point=q[...,4].
- Report nominal interval level correctly: q10-q90 is 80%, q20-q80 is 60%.
- Evaluate against held-out actuals and naive baselines; report coverage **and**
  width by horizon, not only mean accuracy.
- Qualify illustrative retrospective screens and synthetic injected events;
  observed flags do not validate alarm severity or clinical/climate meaning.
- Plot every band's extent and align each successive forecast with its own
  historical cutoff. A final forecast is only a retrospective reference layer.

## Executed checks for this refresh

The repository suite covers strict CSV/date handling, missingness, quantile
indices/shapes, system checks, native 2.5 preprocessing/compile/XReg with a
controlled lightweight decoder, tiny random 2.5 native transformer/decode, and
tiny random 3.0 native save/load/inference.
Example plots and animations are tested with clearly synthetic model outputs.
These verify API mechanics and file/visual alignment, not pretrained accuracy,
calibration, cloud availability or GPU/MLX performance. Checkpoint-load snippets
remain illustrative until run against the real weights for the user's data.

From the repository root:

```bash
uv run skills-ref validate skills/timesfm-forecasting
python tests/run_all.py --isolated timesfm-forecasting
```
