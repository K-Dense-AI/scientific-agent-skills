# Group statistics and decoding

Checked against MNE-Python 1.13.2 and scikit-learn 1.9. The statistics blocks build a small
synthetic group (a P3-like effect plus independent noise per participant) on the sensor
layout of one recording, so they run offline; replace `X` with one row per participant.

## Principles

- **The participant is the unit of inference.** Reduce each participant to one value (or one
  waveform) per condition, then test across participants. Pooling trials across people
  inflates the degrees of freedom.
- Within-subject effects: one-sample tests on condition differences. Between groups:
  independent-sample tests. Several factors or trial-level predictors: mixed-effects models
  (statsmodels, R `lme4`) on the tidy tables from `scripts/erp_analysis.py --single-trial`.
- Fix the analysis window, channels, and cluster-forming threshold before looking.

## Cluster-based permutation tests

One channel or ROI over time. `X` has shape `(n_subjects, n_times)`:

```python
import mne
import numpy as np
from scipy import stats

target = mne.read_evokeds("sub-01_task-oddball_ave.fif", condition="target")
standard = mne.read_evokeds("sub-01_task-oddball_ave.fif", condition="standard")
difference = mne.combine_evoked([target, standard], weights=[1, -1])
times = difference.times
rng = np.random.default_rng(0)
n_subjects = 16
effect = 3.0 * np.exp(-0.5 * ((times - 0.35) / 0.05) ** 2)            # µV, P3-like difference
X = effect + rng.normal(0.0, 3.0, size=(n_subjects, times.size))      # one row per subject

t_threshold = stats.t.ppf(1 - 0.05 / 2, df=n_subjects - 1)            # two-tailed p < .05
t_obs, clusters, cluster_p, H0 = mne.stats.permutation_cluster_1samp_test(
    X, threshold=t_threshold, n_permutations=1024, tail=0, seed=0, out_type="mask"
)
for mask, p in zip(clusters, cluster_p):
    if p < 0.05:
        print(f"cluster {times[mask][0]:.3f}-{times[mask][-1]:.3f} s, p = {p:.3f}")
```

Channels × time. `X` has shape `(n_subjects, n_times, n_channels)`, and the adjacency
matrix comes from the channel positions:

```python
eeg_difference = difference.copy().pick("eeg")
adjacency, ch_names = mne.channels.find_ch_adjacency(eeg_difference.info, ch_type="eeg")
topography = eeg_difference.copy().crop(0.3, 0.4).data.mean(axis=1)
signal = np.outer(effect, topography / np.abs(topography).max())     # (n_times, n_channels)
X_st = signal + rng.normal(0.0, 3.0, size=(n_subjects, *signal.shape))
t_obs, clusters, cluster_p, H0 = mne.stats.spatio_temporal_cluster_1samp_test(
    X_st, adjacency=adjacency, threshold=t_threshold, n_permutations=1024, seed=0
)
for (time_idx, channel_idx), p in zip(clusters, cluster_p):
    if p < 0.05:
        channels = sorted({ch_names[i] for i in channel_idx})
        print(f"{times[time_idx.min()]:.3f}-{times[time_idx.max()]:.3f} s, "
              f"{len(channels)} channels, p = {p:.3f}")
```

- What the test licenses (Maris & Oostenveld, 2007): "the conditions differ somewhere in the
  tested data", with family-wise error control. A cluster's extent does **not** establish
  the onset, offset, or location of the effect (Sassenhagen & Draschkow, 2019).
- The cluster-forming `threshold` is arbitrary but must be fixed in advance.
  `threshold=dict(start=0, step=0.2)` runs TFCE instead (slower, no single threshold).
- With `n` subjects there are `2**n` sign flips; when `n_permutations >= 2**n` MNE runs the
  exact test. Report `n_permutations` and the seed.
- Restricting the tested window and channels a priori buys sensitivity.
- Between groups or conditions of independent observations:
  `mne.stats.permutation_cluster_test([X_a, X_b])` and `spatio_temporal_cluster_test`
  (F statistics; use `tail=1`).
- Mass-univariate alternatives: `mne.stats.fdr_correction(p_values)` and
  `mne.stats.bonferroni_correction(p_values)`.

## Decoding over time (MVPA)

```python
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from mne.decoding import (
    GeneralizingEstimator, LinearModel, SlidingEstimator, cross_val_multiscore, get_coef,
)

epochs = mne.read_epochs("sub-01_task-oddball_epo.fif").pick("eeg")
X_trials = epochs.get_data()                                          # (n_epochs, n_ch, n_times)
y = (epochs.events[:, 2] == epochs.event_id["target"]).astype(int)

classifier = make_pipeline(
    StandardScaler(), LogisticRegression(solver="liblinear", class_weight="balanced")
)
decoder = SlidingEstimator(classifier, scoring="roc_auc", n_jobs=None)
scores = cross_val_multiscore(decoder, X_trials, y, cv=5).mean(axis=0)  # (n_times,)
print(f"peak AUC {scores.max():.2f} at {epochs.times[scores.argmax()]:.3f} s")

generalizer = GeneralizingEstimator(classifier, scoring="roc_auc", n_jobs=None)
matrix = cross_val_multiscore(generalizer, X_trials[:, :, ::5], y, cv=3).mean(axis=0)
print(matrix.shape)                                                    # train x test times
```

- Everything that learns from data (scaling, PCA, feature selection) goes **inside** the
  pipeline so cross-validation refits it per fold. Scaling or selecting on all trials first
  leaks test information.
- Trials close in time are not independent. With blocked designs or slow drifts use
  `GroupKFold`/blocked splits so neighbouring trials do not straddle folds.
- `roc_auc` (chance 0.5) is robust to class imbalance; plain accuracy is not.
- Interpret **patterns**, not weights (Haufe et al., 2014). Wrap the classifier in
  `LinearModel` and read the patterns back in sensor space:

```python
pattern_model = make_pipeline(StandardScaler(), LinearModel(LogisticRegression(solver="liblinear")))
pattern_decoder = SlidingEstimator(pattern_model, scoring="roc_auc", n_jobs=None)
pattern_decoder.fit(X_trials, y)
patterns = get_coef(pattern_decoder, "patterns_", inverse_transform=True)
evoked_patterns = mne.EvokedArray(patterns, epochs.info, tmin=epochs.times[0])
fig = evoked_patterns.plot_topomap(times=[0.1, 0.35], show=False)
```

- Group level: one score time course per participant, then a one-sample test against chance
  (for example `permutation_cluster_1samp_test(scores - 0.5)`).

## Oscillatory decoding with CSP

Common spatial patterns suit class differences in band power, such as motor imagery. This
block downloads PhysioNet EEGBCI (subject 1, left vs right hand imagery; about 8 MB):

```python
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import ShuffleSplit, cross_val_score
from mne.decoding import CSP

files = mne.datasets.eegbci.load_data(subjects=[1], runs=[4, 8, 12], update_path=False)
mi_raw = mne.concatenate_raws([mne.io.read_raw_edf(f, preload=True) for f in files])
mne.datasets.eegbci.standardize(mi_raw)                 # 'Fc5.' -> 'FC5'
mi_raw.set_montage("colin27_1005")
mi_raw.filter(7.0, 30.0, picks="eeg")
events, _ = mne.events_from_annotations(mi_raw, event_id=dict(T1=1, T2=2))
mi_epochs = mne.Epochs(mi_raw, events, dict(left=1, right=2), tmin=1.0, tmax=2.0,
                       baseline=None, picks="eeg", preload=True)
labels = mi_epochs.events[:, 2]
csp_lda = make_pipeline(CSP(n_components=4, log=True), LinearDiscriminantAnalysis())
cv = ShuffleSplit(n_splits=10, test_size=0.2, random_state=42)
accuracy = cross_val_score(csp_lda, mi_epochs.get_data(copy=False), labels, cv=cv)
print(f"CSP+LDA accuracy {accuracy.mean():.2f} (chance 0.5)")
```

CSP, SPoC, SSD, and XdawnTransformer can be saved and reloaded natively since 1.12. Decode
from 1 s after cue onward to avoid evoked responses to the cue itself. `update_path=False`
matters for agents: without it the fetcher may stop at an interactive `input()` prompt
asking whether to store the dataset path in the MNE config.
