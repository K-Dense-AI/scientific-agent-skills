# Illustrative temperature-shaped forecast

The small bundled CSV has no recorded retrieval/revision provenance. It is
retained as illustrative numerical input, not as verified NASA GISTEMP or NOAA
observations. No claim about 2025 climate, a cooling trend or an anomalous
September is justified from this example. Use a cited versioned authoritative
data release for scientific analysis.

The scripts now use the Apache-licensed 2.5 checkpoint with package 3.0.2 and
correct deciles: mean at index 0, q10..q90 at 1..9, nominal 80%/60% bands.
Old generated CSV/JSON/PNG/GIF/HTML outputs were removed. New output requires
explicit regeneration; no pretrained inference was executed in this refresh.

From the skill root, after installing dependencies and checking resources:

```bash
python examples/global-temperature/run_forecast.py --output-dir /tmp/timesfm-demo
python examples/global-temperature/visualize_forecast.py --output-dir /tmp/timesfm-demo
python examples/global-temperature/generate_animation_data.py --output-dir /tmp/timesfm-demo
python examples/global-temperature/generate_gif.py --output-dir /tmp/timesfm-demo
python examples/global-temperature/generate_html.py --output-dir /tmp/timesfm-demo
```

Animations forecast from each prefix only. All-history/final-forecast background
layers are labeled retrospective references and are never model inputs. Band
axes use all steps, avoiding clipping wider early forecasts. New-schema checks
reject old unvalidated animation/forecast JSON rather than silently relabel it.
The HTML embeds data but loads pinned Chart.js from a CDN, so it needs network
access and is not a self-contained offline artifact. Its interpolation is linear
to avoid suggesting extra forecast structure between monthly observations.
