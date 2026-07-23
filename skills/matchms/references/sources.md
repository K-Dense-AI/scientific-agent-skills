# Sources and Verification Record

This skill was refreshed on **2026-07-23** against matchms **0.33.1**.

## Version and Packaging

- [matchms on PyPI](https://pypi.org/project/matchms/) — 0.33.1, released
  2026-06-08; Python `>=3.10,<3.15`; release history and package metadata.
- [matchms 0.33.1 release](https://github.com/matchms/matchms/releases/tag/0.33.1)
  — Python 3.14 support and maintenance changes.
- [matchms repository](https://github.com/matchms/matchms) — source,
  `pyproject.toml`, tests, examples, and current README.
- [matchms releases](https://github.com/matchms/matchms/releases) — complete
  upstream release history.

The 0.33.1 wheel was installed in an isolated uv environment and its public
objects were inspected with `inspect.signature`. Runnable examples in this skill
were checked against that environment.

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

Read the Docs "latest" and the installed 0.33.1 source were treated as
authoritative for class names, signatures, return values, and deprecations.

## User Guides

- [matchms user documentation](https://matchms.github.io/matchms-docs/intro.html)
- [Filtering tutorial](https://matchms.github.io/matchms-docs/notebooks/matchms_filtering_tutorial.html)
- [Building an MS/MS analysis pipeline](https://matchms.github.io/matchms-docs/notebooks/matchms_tutorial_01_building_analysis_pipeline.html)
- [User-guide repository](https://github.com/matchms/matchms-docs)
- [Latest recorded guide revision](https://github.com/matchms/matchms-docs/commit/796f156c58d25adfb7e1528fcb24eb8c40c143a5)
  — 2024-06-13.

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

The current PyPI project description lists compatible or complementary tools:

- [MS2DeepScore](https://github.com/matchms/ms2deepscore)
- [Spec2Vec](https://github.com/iomega/spec2vec)
- [matchmsextras](https://github.com/matchms/matchmsextras)
- [MS2Query](https://github.com/iomega/ms2query)
- [SimMS](https://github.com/PangeAI/SimMS)
- [matchms organization](https://github.com/matchms)

Check each project's current compatibility matrix before combining environments;
matchms 0.33.1 uses NumPy 2 and Python 3.10-3.14.

## Research Queries

Focused web searches and extracts covered:

- current matchms stable version, Python support, dependencies, and release
  history;
- breaking changes and deprecated/removed APIs since 2023;
- current core, filtering, I/O, similarity, Pipeline, Scores, and networking
  documentation;
- current upstream tutorials and their last revision;
- primary publications for matchms, modified cosine/molecular networking,
  BLINK, Flash Entropy, and Spec2Vec.

No research JSON artifacts were committed to the repository.
