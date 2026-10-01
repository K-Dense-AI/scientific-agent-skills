# Sources and Verification Record

This skill was refreshed on **2026-10-01** against the current stable release,
matchms **0.33.1**. Public PyPI metadata, current official API pages, the released
wheel/source, and live public services were checked separately.

## Version and Packaging

- [matchms on PyPI](https://pypi.org/project/matchms/) — 0.33.1, released
  2026-06-08; Python `>=3.10,<3.15`; release history and package metadata.
- [matchms 0.33.1 release](https://github.com/matchms/matchms/releases/tag/0.33.1)
  — Python 3.14 support and maintenance changes.
- [matchms repository](https://github.com/matchms/matchms) — source,
  `pyproject.toml`, tests, examples, and current README.
- [matchms releases](https://github.com/matchms/matchms/releases) — complete
  upstream release history.

The 0.33.1 wheel was installed in isolated uv environments on macOS ARM64 with
Python 3.13.3. Public objects in core, I/O, filtering, similarity, Pipeline,
Fingerprints, and networking were inspected with `inspect.signature`; decorated
writer signatures and return/side-effect semantics were checked in source.
The project environment was not given scientific dependencies.

## Release Notes Used for Migration

- [0.27.0](https://github.com/matchms/matchms/releases/tag/0.27.0) — on-demand
  losses, removal of `add_losses`, and `spectrums` to `spectra` renaming.
- [0.30.0](https://github.com/matchms/matchms/releases/tag/0.30.0) — NumPy 2
  baseline and Python 3.13 support.
- [0.31.0](https://github.com/matchms/matchms/releases/tag/0.31.0) —
  `FlashSimilarity`, `BlinkCosine`, min-max intensity scaling, and new filters.
- [0.32.0](https://github.com/matchms/matchms/releases/tag/0.32.0) —
  `ModifiedCosineGreedy` rename and `ModifiedCosineHungarian`.
- [0.33.0](https://github.com/matchms/matchms/releases/tag/0.33.0) —
  `CosineLinear` and preparation for the future 1.0 API.
- [0.33.1](https://github.com/matchms/matchms/releases/tag/0.33.1) — current
  verified release.

## Current API Documentation

- [Documentation home](https://matchms.readthedocs.io/)
- [Core package, Pipeline, Spectrum, and Scores](https://matchms.readthedocs.io/en/latest/api/matchms.html)
- [Spectrum](https://matchms.readthedocs.io/en/latest/api/matchms.Spectrum.html)
- [Filtering](https://matchms.readthedocs.io/en/latest/api/matchms.filtering.html)
- [Importing](https://matchms.readthedocs.io/en/latest/api/matchms.importing.html)
- [Exporting](https://matchms.readthedocs.io/en/latest/api/matchms.exporting.html)
- [Similarity](https://matchms.readthedocs.io/en/latest/api/matchms.similarity.html)
- [Networking](https://matchms.readthedocs.io/en/latest/api/matchms.networking.html)

Read the Docs pages identify 0.33.1, but individual cached source pages can be
older. The installed released source resolves disagreements, including several
docstring/implementation differences reproduced below.

## User Guides

- [matchms user documentation](https://matchms.github.io/matchms-docs/intro.html)
- [Filtering tutorial](https://matchms.github.io/matchms-docs/notebooks/matchms_filtering_tutorial.html)
- [Building an MS/MS analysis pipeline](https://matchms.github.io/matchms-docs/notebooks/matchms_tutorial_01_building_analysis_pipeline.html)
- [User-guide repository](https://github.com/matchms/matchms-docs)
- [Latest recorded guide revision](https://github.com/matchms/matchms-docs/commit/796f156c58d25adfb7e1528fcb24eb8c40c143a5)
  — 2024-06-13; still the newest guide commit on the review date.

The tutorials are useful for workflow concepts but predate releases 0.27-0.33.
In particular, the pipeline tutorial still uses `ModifiedCosine`. Current API
docs and release notes supersede tutorial symbol names.

## Primary Scientific References

- [Huber et al., 2020 — matchms: processing and similarity evaluation of mass
  spectrometry data](https://joss.theoj.org/papers/10.21105/joss.02411),
  *Journal of Open Source Software* 5(52), 2411,
  DOI `10.21105/joss.02411`.
- [Watrous et al., 2012 — Mass spectral molecular networking of living
  microbial colonies](https://www.pnas.org/doi/10.1073/pnas.1203689109),
  *PNAS* 109, E1743-E1752, DOI `10.1073/pnas.1203689109`.
- [Harwood et al., 2023 — BLINK enables ultrafast tandem mass spectrometry
  cosine similarity scoring](https://pmc.ncbi.nlm.nih.gov/articles/PMC10439109),
  *Scientific Reports* 13, 13462, DOI `10.1038/s41598-023-40496-9`.
- [Li & Fiehn, 2023 — Flash entropy search to query all mass spectral libraries
  in real time](https://pubmed.ncbi.nlm.nih.gov/37735567),
  *Nature Methods* 20, 1475-1478,
  DOI `10.1038/s41592-023-02012-9`.
- [Huber et al., 2021 — Spec2Vec: Improved mass spectral similarity scoring
  through learning of structural relationships](https://pmc.ncbi.nlm.nih.gov/articles/PMC7909622/),
  *PLoS Computational Biology* 17, e1008724,
  DOI `10.1371/journal.pcbi.1008724`.

These papers motivate methods and interpretation. The matchms implementation
and its exact defaults remain defined by the 0.33.1 API/source.

## Ecosystem References

The upstream ecosystem lists complementary tools; they were not runtime-tested
as part of this matchms refresh:

- [MS2DeepScore](https://github.com/matchms/ms2deepscore)
- [Spec2Vec](https://github.com/iomega/spec2vec)
- [matchmsextras](https://github.com/matchms/matchmsextras)
- [MS2Query](https://github.com/iomega/ms2query)
- [SimMS](https://github.com/PangeAI/SimMS)
- [matchms organization](https://github.com/matchms)

Check each project's current compatibility matrix before combining environments;
matchms 0.33.1 uses NumPy 2 and Python 3.10-3.14.

## Released-Source Findings

- [Spectrum and metadata construction](https://github.com/matchms/matchms/blob/0.33.1/matchms/Spectrum.py):
  `metadata_harmonization=False` still harmonizes keys; `plot_against` returns
  `(figure, axis)`.
- [SpectrumProcessor](https://github.com/matchms/matchms/blob/0.33.1/matchms/filtering/SpectrumProcessor.py):
  direct single-spectrum processing can mutate input, while list processing
  clones inputs without a report; registered filters are reordered.
- [Scores calculation](https://github.com/matchms/matchms/blob/0.33.1/matchms/Scores.py):
  coordinate-only computation requires a left/inner join and fewer than half of
  all coordinates; 1-by-1 always calls `pair`.
- [CosineLinear](https://github.com/matchms/matchms/blob/0.33.1/matchms/similarity/CosineLinear.py):
  close peaks are merged before matching.
- [FlashSimilarity](https://github.com/matchms/matchms/blob/0.33.1/matchms/similarity/FlashSimilarity.py):
  sparse output still allocates a dense matrix. Entropy with `neutral_loss`
  adds fragment and loss terms and gave a self-score near 2 in both pair/matrix
  tests; the skill explicitly excludes that combination as a normalized score.
- [Metadata export mappings](https://github.com/matchms/matchms/blob/0.33.1/matchms/data/export_key_conversions.csv):
  MassBank-style precursor keys did not return to `precursor_mz` on reimport.
- [mzSpecLib writer](https://github.com/matchms/matchms/blob/0.33.1/matchms/exporting/save_as_mzspeclib.py):
  direct text output rounds intensities to two decimals and assumes collision
  energy text is expressed in eV.

## Endpoint Verification

- [USI helper source](https://github.com/matchms/matchms/blob/0.33.1/matchms/importing/load_from_usi.py)
  and [GNPS API documentation](https://ccms-ucsd.github.io/GNPSDocumentation/api/):
  public GET `/json/?usi1=<USI>` on `https://metabolomics-usi.gnps2.org`, no
  authentication or pagination, one JSON spectrum. Live retrieval of the two
  documented USIs produced 317 and 119 peaks. The first raw response included
  `precursor_charge` and `splash`, which matchms discards. Both were successfully
  loaded with matchms, identically normalized, and cosine-scored; this was an
  execution check, not a compound-identification validation.
- [Name-annotation filter source](https://github.com/matchms/matchms/blob/0.33.1/matchms/filtering/metadata_processing/derive_annotation_from_compound_name.py)
  and [PubChemPy name-search documentation](https://docs.pubchempy.org/en/latest/guide/searching.html):
  public name lookup via PubChemPy, optional local CSV cache, neutral-parent-mass
  gate, no credential. A live caffeine lookup at 0.001 Da tolerance returned
  the expected reference InChIKey. This does not establish identity for unknown
  spectra or ambiguity-free annotation for arbitrary names.

## Execution Coverage and Limits

- `uv run skills-ref validate skills/matchms`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python tests/run_all.py --isolated matchms`:
  117 tests passed, including the original 58 and 59 API/CLI regressions.
- Small synthetic smoke checks passed for mzML/mzXML MS-level selection,
  precursor and peak arrays; Pipeline/YAML; five network export formats;
  Fingerprints bridging and three structure metrics; binned and metadata
  scoring; mirror-plot export; and all ten bundled CLI metrics.
- MGF/MSP/JSON roundtrips covered matchms, GNPS, NIST, and RIKEN metadata styles;
  separate regression cases record MassBank precursor loss. Score JSON
  serialization/reloading was exercised. No untrusted pickle was opened.
- Flash pair and serial matrix paths were checked. Large-library performance,
  multiprocessing scaling, ANN recall, acquisition-specific thresholds,
  downstream mzSpecLib conformance, every repair heuristic, and other operating
  systems/Python versions were not experimentally validated. Broader snippets
  are workflow templates requiring representative local validation.
- The ordinary project-environment pytest invocation skipped both modules
  because scientific dependencies are intentionally absent; the isolated run
  above is the executable validation.

No downloaded scientific datasets or research JSON artifacts are shipped.
