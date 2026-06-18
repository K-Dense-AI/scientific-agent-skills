---
name: pyopenms
description: Complete mass spectrometry analysis platform. Use for proteomics and metabolomics workflows—feature detection, peptide/protein identification, label-free and isobaric quantification, adduct/accurate-mass annotation, and complex LC-MS/MS pipelines. Supports extensive file formats and algorithms. For simple spectral comparison and small-molecule library matching use matchms.
license: 3 clause BSD license
allowed-tools: Read Write Edit Bash
compatibility: Requires Python 3.9+ and uv. Examples and scripts target pyOpenMS 3.5.0.
metadata: {"version": "2.0", "skill-author": "K-Dense Inc."}
---

# PyOpenMS

## Overview

PyOpenMS provides Python bindings to the OpenMS library for computational mass
spectrometry, enabling analysis of proteomics and metabolomics data. Use it to
read/write MS file formats, process raw spectra, detect and quantify features,
identify peptides and proteins, and run end-to-end LC-MS/MS pipelines.

**This skill ships ready-to-run scripts in `scripts/`** covering the most common
high-level workflows. Prefer running a script over writing new code—each is a
parameterized CLI tool that handles loading, processing, and export. Drop into the
Python API (and the `references/`) only when no script fits.

## Installation

```bash
uv pip install pyopenms
```

Verify (note: `__version__` works, but the bundled binary prints a one-line
memory-status notice on import that is harmless):

```python
import pyopenms as ms
print(ms.__version__)  # 3.5.0
```

## Scripts (start here)

Run with `python scripts/<name>.py --help` for full options. All accept standard
MS file formats and write featureXML/consensusXML/CSV/mzTab/PNG as appropriate.

### Inspect & convert
| Script | What it does |
|--------|--------------|
| `inspect_ms_data.py` | Summarize any mzML/mzXML/featureXML/consensusXML/idXML (counts, RT/m/z ranges, TIC, metadata); optional per-spectrum CSV. |
| `convert_format.py` | Convert between mzML/mzXML/MGF with optional MS-level, RT, and intensity filtering. |
| `process_spectra.py` | Configurable signal-processing chain: smoothing (Gauss/SGolay), centroiding (PeakPickerHiRes), normalization, S/N and intensity thresholds. |

### Feature detection & quantification
| Script | What it does |
|--------|--------------|
| `detect_features_metabo.py` | Untargeted metabolomics feature finding: MassTraceDetection → ElutionPeakDetection → FeatureFindingMetabo. |
| `detect_features_centroided.py` | Peptide/centroided feature detection via FeatureFinderAlgorithmPicked. |
| `align_link_quantify.py` | Multi-sample pipeline: detect (or load) features → RT alignment → consensus linking → quant matrix CSV. |
| `consensus_to_matrix.py` | consensusXML → wide intensity matrix + metadata, with optional median/quantile normalization and long format. |

### Annotation
| Script | What it does |
|--------|--------------|
| `detect_adducts.py` | Group adducts/charge variants of the same neutral mass (MetaboliteFeatureDeconvolution). |
| `accurate_mass_search.py` | Annotate features against HMDB by accurate mass (AccurateMassSearchEngine → mzTab/CSV). |
| `export_gnps_sirius.py` | Export GNPS FBMN inputs (MGF + quant table) or a SIRIUS `.ms` file. |

### Identification
| Script | What it does |
|--------|--------------|
| `process_identifications.py` | Re-index against FASTA, estimate FDR/q-values, filter (FDR/length/best-per-spectrum), export idXML + CSV. |

### Chemistry
| Script | What it does |
|--------|--------------|
| `mass_calculator.py` | Monoisotopic/average mass, charged m/z, formula, and isotope pattern for peptides or empirical formulas. |
| `digest_protein.py` | In-silico protease digestion of FASTA/sequence → theoretical peptides with masses and m/z. |
| `theoretical_spectrum.py` | Generate annotated theoretical fragment spectra (b/y/a/c/x/z, losses) for a peptide. |

### Targeted & visualization
| Script | What it does |
|--------|--------------|
| `extract_chromatograms.py` | Build TIC/BPC and XIC traces for target m/z (CSV + optional plot). |
| `plot_ms_data.py` | Quick plots: single spectrum, TIC, 2D feature map, MS1 signal map. |

### Common script recipes

```bash
# Inspect a file
python scripts/inspect_ms_data.py sample.mzML --spectra-csv spectra.csv

# Untargeted metabolomics: features for one sample
python scripts/detect_features_metabo.py sample.mzML --out-csv features.csv

# Full multi-sample quantification study
python scripts/align_link_quantify.py s1.mzML s2.mzML s3.mzML --out-prefix study
python scripts/consensus_to_matrix.py study.consensusXML --out quant.csv --normalize median

# Peptide chemistry
python scripts/mass_calculator.py --peptide "PEPTIDEM(Oxidation)K" --charges 1 2 3 --isotopes 5
python scripts/digest_protein.py proteins.fasta --enzyme Trypsin --missed 2 --out peptides.csv

# Identification post-processing
python scripts/process_identifications.py search.idXML --fasta db.fasta --fdr 0.01 --out filtered.idXML --csv hits.csv
```

## Key 3.5.0 API notes

These changed from older OpenMS releases—older tutorials and code will break:

- **Feature finding**: `FeatureFinder("centroided")` was **removed**. Use
  `FeatureFinderAlgorithmPicked` (proteomics/centroided) or the
  `MassTraceDetection → ElutionPeakDetection → FeatureFindingMetabo` pipeline
  (metabolomics). See `detect_features_*.py`.
- **idXML I/O**: `IdXMLFile().load/store` require a `ms.PeptideIdentificationList()`
  for peptide IDs (a plain Python `list` raises "can not handle type"). Protein IDs
  remain a plain list.
- **Adduct decharging**: the class is `MetaboliteFeatureDeconvolution`, and adducts
  use `Elements:Charge:Probability` syntax (e.g. `H:+:0.4`, `H-2O-1:0:0.05`)—not
  bracket notation like `[M+H]+`.
- **DataFrame columns**: `FeatureMap.get_df()` uses lowercase `rt`/`mz` (not `RT`).
  `ConsensusMap` provides `get_intensity_df()` and `get_metadata_df()`.
- **Bundled data caveat**: the pip wheel ships `HMDBMappingFile.tsv` but not
  `HMDB2StructMapping.tsv`; `accurate_mass_search.py` detects this and explains how
  to supply it.

## Core data structures

- **MSExperiment** – collection of spectra and chromatograms
- **MSSpectrum / MSChromatogram** – a single spectrum / chromatographic trace
- **Feature / FeatureMap** – a detected LC-MS peak / collection of features
- **ConsensusMap** – features linked across samples (the quant table)
- **PeptideIdentification / ProteinIdentification** – search results
- **AASequence / EmpiricalFormula** – sequence and formula chemistry

**For details**: see `references/data_structures.md`.

## Parameter management

Most algorithms expose an OpenMS `Param` object:

```python
algo = ms.FeatureFindingMetabo()
p = algo.getDefaults()
for key in p.keys():
    print(key.decode(), "=", p.getValue(key), "|", p.getDescription(key))
p.setValue("charge_lower_bound", 1)
algo.setParameters(p)
```

## Export to pandas

```python
fm = ms.FeatureMap(); ms.FeatureXMLFile().load("features.featureXML", fm)
df = fm.get_df()             # columns include lowercase rt, mz, intensity, charge, quality

cm = ms.ConsensusMap(); ms.ConsensusXMLFile().load("study.consensusXML", cm)
intensities = cm.get_intensity_df()   # features x samples
metadata = cm.get_metadata_df()       # rt, mz, charge, quality, ...
```

## Integration with other tools

Pandas (DataFrames), NumPy (peak arrays), scikit-learn (ML), Matplotlib/Seaborn
(plots), and downstream tools via export: GNPS (FBMN), SIRIUS, and mzTab.

## Resources

- Official docs (3.5.0): https://pyopenms.readthedocs.io/en/release-3.5.0/
- OpenMS: https://www.openms.org
- GitHub: https://github.com/OpenMS/OpenMS

## References

- `references/file_io.md` – file format handling
- `references/signal_processing.md` – signal processing algorithms
- `references/feature_detection.md` – feature detection and linking
- `references/identification.md` – peptide and protein identification
- `references/metabolomics.md` – metabolomics-specific workflows
- `references/data_structures.md` – core objects and data structures
