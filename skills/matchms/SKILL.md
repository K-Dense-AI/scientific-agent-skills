---
name: matchms
description: Process, clean, compare, and search tandem mass spectra with matchms. Use for MS/MS file I/O, metadata harmonization, peak filtering, spectral similarity, library matching, score matrices, and molecular-similarity networks. Use pyopenms instead for LC-MS feature detection or proteomics pipelines.
allowed-tools: Read Write Edit Bash
license: Apache-2.0
compatibility: Requires Python >=3.10,<3.15, uv, and matchms 0.33.1. Local file workflows need no credentials; metabolomics-USI loading requires network access.
metadata:
  version: "2.0"
  skill-author: K-Dense Inc.
---

# Matchms

## Purpose and Scope

Matchms is a Python package for importing, cleaning, processing, and comparing
tandem mass spectra. This skill targets **matchms 0.33.1**, released 2026-06-08,
and corrects several breaking API changes that older tutorials do not reflect.

Use matchms for:

- MS/MS library search and query-versus-reference scoring
- Metadata harmonization, adduct/precursor handling, and peak filtering
- Cosine, modified-cosine, neutral-loss, approximate, and entropy scoring
- Structured score matrices, top-hit extraction, and spectral networks
- MGF, MSP, mzML, mzXML, JSON, mzSpecLib, and metabolomics-USI workflows

Do not use matchms as a replacement for:

- LC-MS feature detection, chromatographic alignment, peptide identification, or
  protein quantification — use pyopenms
- Vendor raw-file conversion — convert to mzML/mzXML first
- A validated compound-identification protocol — similarity is evidence, not
  proof of identity

## Install the Verified Release

Create or activate an environment, then install the release used by this skill:

```bash
uv pip install "matchms==0.33.1"
```

Verify the runtime:

```bash
uv run python -c "import matchms; print(matchms.__version__)"
```

Matchms 0.33.1 supports Python 3.10-3.14 and installs RDKit as a regular
dependency. The old `matchms[chemistry]` extra is not part of the current
package metadata.

## Operating Workflow

1. **Inspect the inputs.** Record format, spectrum count, MS level, precursor
   coverage, ion mode, peak counts, and identifier fields.
2. **Load with metadata harmonization enabled** unless preserving source keys is
   a deliberate requirement.
3. **Apply the same peak-processing steps** to query and reference spectra.
   Keep metadata enrichment separate when reference annotations are richer.
4. **Drop invalid spectra explicitly.** Many `require_*` filters return `None`.
5. **Choose the score from the scientific question**, not from convenience.
   Modified and neutral-loss scores require valid `precursor_mz`.
6. **Estimate `len(references) * len(queries)` before scoring.** A sparse result
   container does not automatically avoid computing every requested pair.
7. **Report score settings and evidence.** Include tolerance, preprocessing,
   score name, number of matched peaks when available, and candidate metadata.
8. **Validate top hits visually and chemically.** Use mirror plots, precursor
   agreement, ion/adduct compatibility, and orthogonal evidence.

## Current API Guardrails

These points prevent the most common failures from pre-0.33 examples:

- Use `ModifiedCosineGreedy` or `ModifiedCosineHungarian`; `ModifiedCosine` was
  removed in 0.32.0.
- Do not call `add_losses()`. It was removed in 0.27.0; use
  `spectrum.losses`, `spectrum.compute_losses(...)`, or
  `NeutralLossesCosine` directly.
- `SpectrumProcessor` is not callable. Use `process_spectrum()` or
  `process_spectra()`.
- `process_spectra()` returns `(processed_spectra, processing_report)`.
- `Scores.scores` is a `StackedSparseArray`, often with separate structured
  fields such as `CosineGreedy_score` and `CosineGreedy_matches`.
- `scores_by_query()` returns `(reference_spectrum, score_record)` pairs, not
  reference indices.
- Prefer `spectra` in parameter names. The legacy spelling `spectrums` is
  deprecated.
- Never load pickle files from an untrusted source; unpickling can execute code.

See `references/migration.md` for a complete old-to-current mapping.

## Quick Start: Clean and Search a Library

```python
from matchms import SpectrumProcessor, calculate_scores
from matchms.filtering import (
    default_filters,
    normalize_intensities,
    require_minimum_number_of_peaks,
    select_by_relative_intensity,
)
from matchms.importing import load_spectra
from matchms.similarity import ModifiedCosineGreedy


def load_and_process(path):
    spectra = [default_filters(spectrum) for spectrum in load_spectra(path)]
    processor = SpectrumProcessor(
        [
            normalize_intensities,
            (select_by_relative_intensity, {"intensity_from": 0.01}),
            (require_minimum_number_of_peaks, {"n_required": 5}),
        ]
    )
    processed, _ = processor.process_spectra(
        spectra,
        progress_bar=False,
        create_report=False,
    )
    return processed


references = load_and_process("library.msp")
queries = load_and_process("queries.mgf")

metric = ModifiedCosineGreedy(tolerance=0.02)
scores = calculate_scores(
    references=references,
    queries=queries,
    similarity_function=metric,
)

score_name = "ModifiedCosineGreedy_score"
matches_name = "ModifiedCosineGreedy_matches"
for query in queries:
    ranked = scores.scores_by_query(query, name=score_name, sort=True)
    for reference, values in ranked[:5]:
        print(
            query.get("spectrum_id", query.get("id")),
            reference.get("compound_name", reference.get("spectrum_id")),
            float(values[score_name]),
            int(values[matches_name]),
        )
```

`SpectrumProcessor` automatically orders built-in filters according to matchms's
filter order. The aggregate `default_filters` callable is not in that registry,
so run it first as above or expand its nine component filters. Inspect
`processor.processing_steps` and preserve it with results.

## Pair Scoring

Similarity classes expose `pair()` for one reference/query pair. Cosine-family
results are structured NumPy scalars:

```python
from matchms.similarity import CosineGreedy

result = CosineGreedy(tolerance=0.02).pair(reference, query)
similarity = float(result["score"])
matched_peaks = int(result["matches"])
```

Use `calculate_scores()` for matrix-oriented methods such as
`FlashSimilarity`; its single-pair path is supported but intentionally not the
optimized path.

## Choose a Similarity Method

- `CosineGreedy` — standard peak cosine with greedy peak assignment.
- `CosineHungarian` — exact assignment; slower, useful for benchmarks.
- `CosineLinear` — current linear-scaling cosine implementation.
- `ModifiedCosineGreedy` — permits precursor-delta-shifted matches; common for
  analog search.
- `ModifiedCosineHungarian` — exact modified-cosine assignment.
- `NeutralLossesCosine` — compares losses computed from precursor and fragments.
- `BlinkCosine` — fast BLINK-style cosine approximation for larger matrices.
- `FlashSimilarity` — optimized matrix scoring using spectral entropy or cosine
  with fragment, neutral-loss, or hybrid matching.
- `BinnedEmbeddingSimilarity` — binned spectral vectors and optional approximate
  nearest-neighbor indexing.
- `PrecursorMzMatch`, `ParentMassMatch`, `MetadataMatch` — candidate masks or
  metadata constraints, not rich spectral scores.
- `FingerprintSimilarity` — molecular-structure similarity; it is not spectral
  similarity and requires fingerprints prepared from valid structures.

Read `references/similarity.md` before choosing a fast method, combining scores,
or interpreting structured outputs.

## Large Comparisons

For all-vs-all scoring of one collection, set `is_symmetric=True`:

```python
scores = calculate_scores(
    references=spectra,
    queries=spectra,
    similarity_function=CosineGreedy(tolerance=0.02),
    array_type="sparse",
    is_symmetric=True,
)
```

For a precursor-gated search, compute and filter `PrecursorMzMatch` first, then
calculate the spectral metric only on retained coordinates through `Pipeline`
or `Scores.calculate(...)`. See `references/workflows.md`.

Do not choose a universal "identification threshold." Score distributions
depend on preprocessing, mass accuracy, collision conditions, library quality,
and metric. At minimum, retain both score and matched-peak count for
cosine-family methods.

## Bundled Library-Search CLI

`scripts/library_search.py` provides a reproducible query-versus-library search
with current score extraction, pair-count limits, preprocessing, and CSV output:

```bash
uv run python scripts/library_search.py \
  queries.mgf library.msp hits.csv \
  --metric modified \
  --tolerance 0.02 \
  --top-k 10 \
  --min-score 0.6 \
  --min-matches 5
```

Run `--help` for fast metrics, preprocessing options, identifier fields,
overwrite control, and the explicit large-matrix override.

## Spectrum Objects and Visualization

```python
import numpy as np
from matchms import Spectrum

spectrum = Spectrum(
    mz=np.array([100.0, 150.0, 200.0]),
    intensities=np.array([0.2, 1.0, 0.4]),
    metadata={"spectrum_id": "query-1", "precursor_mz": 250.5},
)

print(spectrum.peaks.mz)
print(spectrum.get("precursor_mz"))
losses = spectrum.compute_losses(loss_mz_from=5.0, loss_mz_to=200.0)
spectrum.plot()
spectrum.plot_against(reference_spectrum)
```

## References

Read only the reference needed for the task:

- `references/importing_exporting.md` — formats, return types, generic I/O,
  mzSpecLib, score serialization, and pickle safety
- `references/filtering.md` — current filter catalog, clone/`None` semantics,
  default filters, ordering, and `SpectrumProcessor`
- `references/similarity.md` — all current similarity classes, outputs,
  candidate masking, performance, and interpretation
- `references/workflows.md` — library search, sparse gating, `Pipeline`, networks,
  plotting, and provenance
- `references/migration.md` — breaking changes and deprecated APIs
- `references/sources.md` — authoritative docs, release notes, user guides, and
  scientific publications used for this refresh

## Non-Negotiable Checks

- Never compare raw queries against differently processed references.
- Never use modified or neutral-loss scoring without valid precursor metadata.
- Never assume a `Scores` value is a plain float; inspect `score_names`.
- Never treat a high similarity score alone as confirmed identification.
- Never deserialize untrusted pickle data.
- Never launch an unbounded all-pairs comparison without estimating pair count.

