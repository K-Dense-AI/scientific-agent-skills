# Candidate RELSA zones from a score density

The [primary foRcast paper](https://doi.org/10.3389/fphys.2026.1869563) explores local minima
of a Gaussian KDE over longitudinal RELSA scores. These valleys describe the **sampled score
distribution**. They do not establish transitions between normal welfare and distress.
The legacy output names `normal`, `attention`, `danger` are descriptive labels only.

## Kernel, bandwidth and implementation differences

`bw_nrd0()` uses R's rule `0.9 * min(sd, IQR/1.349) * n^(-1/5)` with the zero-spread fallback.
The [official R density documentation](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/density.html)
uses a Gaussian default, 512 grid points and an extent of three bandwidths beyond the data.
R performs an FFT-based approximation and its `old.coords` compatibility option changes
historical behavior. The Python helper evaluates SciPy's Gaussian KDE directly, with an
analytic Gaussian for constant samples. It matches the bandwidth convention, not bitwise
R density output or the paper's exact thresholds. SciPy's named `silverman` bandwidth factor
is a different convention and must not be substituted silently.

Input scores must be nonnegative. Missing scores are omitted. Fewer than two finite scores
cannot define a KDE. Constant samples produce no usable interior threshold. A bandwidth must
be finite and positive. `n_thresholds` is a maximum count, not a demand to invent boundaries.
The default `min_zone_fraction=0.02` removes minima isolating fewer than 2% of observations;
this is a local heuristic, not a published or welfare-validated cutoff. Set it to zero to
inspect raw minima. Zone assignment includes equality in the higher zone; threshold JSON
preserves full precision so its decisions agree with CSV labels.

The paper gives sepsis thresholds 0.337/0.643 in Results/Figure 3 but 0.337/0.647 in the
abstract. These are historical model-specific observations, not transferable clinical limits.
Earlier skill notes included full-cohort reproduction and bandwidth-sweep numbers; those
analyses are not repeated by this refresh and are not presented as current execution evidence.

## Population and sampling are part of the model

Use a development population that represents the intended comparison: endpoint animals,
survivors and controls where scientifically appropriate. Explain exclusions, baseline-row
inclusion, measurement cadence, variable panel and reference scale. More frequent observations
and longer-lived animals contribute more KDE mass. Endpoint-related truncation changes that
mixture; 239 measurements from seven animals are not 239 independent animals.

Sensitivity analyses should vary bandwidth, sampling/aggregation and baseline inclusion;
assess threshold stability with animal-level resampling or held-out cohorts. Pool only
measurements sharing one calibration and measurement interpretation. Select thresholds on
development data and freeze them before evaluation. Candidate zones cannot be tuned until
held-out endpoint classification looks favorable.

## Runnable synthetic workflow

After the scoring command in `SKILL.md`, run from the skill directory:

```bash
python scripts/kde_thresholds.py relsa_scores.csv --n-thresholds 2 \
  --plot zones.png --json zones.json --label-out zoned.csv

for f in 0.8 0.9 1.0 1.1 1.2; do
  python - "$f" <<'PY'
import sys, pandas as pd
sys.path.insert(0, "scripts")
from kde_thresholds import find_thresholds, bw_nrd0
v = pd.read_csv("relsa_scores.csv")["relsa"].dropna()
bw = bw_nrd0(v.to_numpy()) * float(sys.argv[1])
print(sys.argv[1], [round(t, 3) for t in find_thresholds(v, bandwidth=bw).thresholds])
PY
done
```

An empty result is legitimate. Do not keep shrinking bandwidth until minima appear. A
stable minimum still needs independent welfare relevance; a bimodal sampling mixture alone
can create it. The official R `relsa_levels` path was source-reviewed but not executed here, so it is
not a tested fallback. Animal-level RELSA maxima used in the original
paper's clustering are a different quantity from all-time-point KDE inputs.

## Welfare and regulatory interpretation

The [European Commission severity assessment framework](https://environment.ec.europa.eu/topics/chemicals/animals-science_en)
addresses prospective classification, monitoring during procedures and actual experienced
severity. The [Directive](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32010L0063)
uses non-recovery, mild, moderate and severe categories with procedure-specific assessment.
No reviewed official guidance maps a RELSA value or KDE zone directly to these categories.
A KDE output cannot replace the approved humane endpoint criteria or assessment by responsible
personnel. No low score, empty threshold list or reassuring forecast establishes permission
to wait when observed welfare signs require action. Record that distinction in reports.
