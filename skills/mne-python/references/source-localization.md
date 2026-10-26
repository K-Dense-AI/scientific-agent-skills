# Source estimation

Checked against MNE-Python 1.13.2. The template workflow below follows MNE's "EEG forward
operator with a template MRI" tutorial. `fetch_fsaverage()` downloads the fsaverage subject
on first use (about 760 MB unpacked).

## When it is justified

Source estimates turn sensor data into estimated cortical activity, but their spatial
precision depends on the head model. **Without the participant's own MRI and digitized
electrode positions, locations can be off by several centimetres**: report template-based
EEG sources as coarse regional estimates, never as precise loci. Minimum-norm solutions
(dSPM, sLORETA, eLORETA) are distributed and smooth; the peak vertex is not "the" generator.

## EEG with the fsaverage template

```python
import mne
import numpy as np

fs_dir = mne.datasets.fetch_fsaverage()          # pathlib.Path to .../fsaverage
subjects_dir = fs_dir.parent
src = fs_dir / "bem" / "fsaverage-ico-5-src.fif"
bem = fs_dir / "bem" / "fsaverage-5120-5120-5120-bem-sol.fif"

raw = mne.io.read_raw("sub-01_task-oddball_desc-clean_eeg.fif", preload=True)
raw.set_montage("fsaverage_1005", match_case=False)   # 1.13: electrodes on the fsaverage scalp
raw.set_eeg_reference("average", projection=True)     # inverse modelling needs the projector

fwd = mne.make_forward_solution(
    raw.info, trans="fsaverage", src=src, bem=bem, eeg=True, meg=False, mindist=5.0
)
print(fwd)
```

- `trans="fsaverage"` uses MNE's built-in head-to-MRI transform for the template.
- The average reference must be present as a **projector** (`projection=True`); an already
  applied average reference also works if the data are re-referenced the same way. Mixing
  references between the covariance, the evoked data, and the inverse is an error.
- Individual anatomy: FreeSurfer `recon-all`, BEM surfaces (`mne.bem.make_watershed_bem` or
  `mne.bem.make_flash_bem`), a three-layer BEM for EEG (`mne.make_bem_model` with
  conductivities `(0.3, 0.006, 0.3)`), and a coregistration `-trans.fif` from `mne coreg`
  or `mne.coreg.Coregistration`. MEG can use a single-layer BEM.

## Noise covariance and inverse operator

```python
events, event_id = mne.events_from_annotations(raw)
epochs = mne.Epochs(raw, events, event_id, tmin=-0.2, tmax=0.8, baseline=(None, 0),
                    reject=dict(eeg=100e-6), preload=True)
noise_cov = mne.compute_covariance(epochs, tmax=0.0, method=["shrunk", "empirical"], rank=None)
evoked = epochs["target"].average()

inverse = mne.minimum_norm.make_inverse_operator(
    evoked.info, fwd, noise_cov, loose=0.2, depth=0.8
)
snr = 3.0
stc = mne.minimum_norm.apply_inverse(evoked, inverse, lambda2=1.0 / snr**2, method="dSPM")
vertex, peak_time = stc.get_peak(hemi="lh")
print(stc, f"left-hemisphere peak at {peak_time:.3f} s")
```

- Estimate the noise covariance from the pre-stimulus baseline (`tmax=0.0`) of the **same**
  epochs, with regularization (`"shrunk"` is a good default; passing a list picks the best
  by cross-validated likelihood). With few samples per channel it is poorly conditioned;
  1.11 added `on_few_samples` to warn or raise. In 1.13 pass the epochs positionally: the
  `epochs=` keyword is deprecated in favour of `inst=`.
- `lambda2 = 1 / SNR**2`: SNR 3 for averaged responses, 1 for single trials or raw data.
- `loose=0.2` constrains orientations near the cortical normal; `depth=0.8` counteracts the
  bias towards superficial sources.
- `method`: `"MNE"` (current estimate), `"dSPM"` and `"sLORETA"` (noise-normalized
  statistics, unitless), `"eLORETA"` (exact low-resolution; slower). Do not compare
  magnitudes across methods.
- The rank of an average-referenced EEG covariance is `n_channels - 1`; `rank=None` lets MNE
  estimate it. Interpolated channels reduce the rank further.

## Regions of interest

```python
labels = mne.read_labels_from_annot("fsaverage", parc="aparc", subjects_dir=subjects_dir)
labels = [label for label in labels if not label.name.startswith("unknown")]  # medial wall
label_ts = mne.extract_label_time_course(stc, labels, fwd["src"], mode="mean_flip")
print(label_ts.shape)                                  # (n_labels, n_times)
```

Reading parcellations needs `nibabel`. The `unknown` labels cover the medial wall, which
has no vertices in the source space; drop them or pass `allow_empty=True`.
`mode="mean_flip"` flips sign-inconsistent sources before averaging; with dSPM (positive
by construction) `mode="mean"` is equivalent. Label time courses feed ROI statistics and
connectivity. Three-dimensional plotting (`stc.plot()`, `mne.viz.plot_alignment()`) needs
PyVista and a display; the matplotlib 3D backend is deprecated as of 1.13.

## Check the head model

Look at the alignment of electrodes, scalp, and brain before trusting a forward model:
`mne.viz.plot_alignment(raw.info, trans="fsaverage", subject="fsaverage",
subjects_dir=subjects_dir, eeg=["original", "projected"], surfaces=["head", "brain"])`.
Electrodes floating above or sunk into the scalp mean the montage units or the transform
are wrong.
