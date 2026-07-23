# Practical Workflows (matchms 0.33.1)

These patterns use the current 0.33.1 API. Adapt tolerances and quality filters
to the instrument, acquisition method, and scientific question.

## 1. Standard Query/Reference Preprocessing

Apply the same peak processing to both collections. Metadata enrichment can
differ when a reference library contains known structures and queries do not.

```python
from matchms import SpectrumProcessor
from matchms.filtering import (
    default_filters,
    normalize_intensities,
    require_minimum_number_of_peaks,
    require_precursor_mz,
    select_by_mz,
    select_by_relative_intensity,
)
from matchms.importing import load_spectra


def preprocess(path):
    raw = [default_filters(spectrum) for spectrum in load_spectra(path)]
    processor = SpectrumProcessor(
        [
            (require_precursor_mz, {"minimum_accepted_mz": 50.0}),
            normalize_intensities,
            (select_by_mz, {"mz_from": 20.0, "mz_to": 1500.0}),
            (select_by_relative_intensity, {"intensity_from": 0.01}),
            (require_minimum_number_of_peaks, {"n_required": 5}),
        ]
    )
    cleaned, _ = processor.process_spectra(
        raw,
        progress_bar=False,
        create_report=False,
    )
    return cleaned, ["default_filters", *processor.processing_steps]


queries, query_steps = preprocess("queries.mgf")
references, reference_steps = preprocess("library.msp")
assert query_steps == reference_steps
```

`SpectrumProcessor` may reorder built-in filters. Persist the final
`processing_steps`, not only the requested list. Run the aggregate
`default_filters` before the processor; if passed as one callable, it is treated
as a custom filter and placed after registered filters.

## 2. Run the Bundled Library Search

The bundled CLI is the fastest route to a reproducible CSV:

```bash
uv run python scripts/library_search.py \
  queries.mgf library.msp hits.csv \
  --metric modified \
  --tolerance 0.02 \
  --top-k 10 \
  --min-score 0.6 \
  --min-matches 5
```

The script:

- applies the same configurable peak filters to both inputs;
- supports cosine, exact/greedy modified cosine, neutral-loss, BLINK, and Flash
  modes;
- handles both scalar and structured matchms score records;
- records identifiers, precursor m/z, rank, score, and matched peaks;
- refuses pickle inputs;
- refuses to overwrite output unless `--force`; and
- stops before an unexpectedly large pairwise matrix unless `--max-pairs` is
  explicitly raised.

Use `--help` before batch use.

## 3. Programmatic Spectral-Library Search

```python
from matchms import calculate_scores
from matchms.similarity import ModifiedCosineGreedy

metric = ModifiedCosineGreedy(tolerance=0.02)
scores = calculate_scores(
    references=references,
    queries=queries,
    similarity_function=metric,
)

score_name = "ModifiedCosineGreedy_score"
matches_name = "ModifiedCosineGreedy_matches"
rows = []

for query_index, query in enumerate(queries):
    ranked = scores.scores_by_query(query, name=score_name, sort=True)
    for rank, (reference, value) in enumerate(ranked[:10], start=1):
        rows.append(
            {
                "query_index": query_index,
                "query_id": query.get("spectrum_id", query.get("id")),
                "reference_id": reference.get(
                    "spectrum_id",
                    reference.get("compound_name"),
                ),
                "rank": rank,
                "score": float(value[score_name]),
                "matches": int(value[matches_name]),
            }
        )
```

Filter on both score and matched peaks only after examining their distributions.
Do not label arbitrary cutoffs as universal high/medium/low confidence.

## 4. Efficient Precursor-Gated Search

For identity-oriented search, a precursor gate can reduce expensive spectral
calculations:

```python
from matchms import calculate_scores
from matchms.similarity import ModifiedCosineGreedy, PrecursorMzMatch

scores = calculate_scores(
    references,
    queries,
    PrecursorMzMatch(tolerance=10, tolerance_type="ppm"),
    array_type="sparse",
)
scores.filter_by_range(
    name="PrecursorMzMatch",
    low=0.5,
    above_operator=">=",
)
scores.calculate(
    ModifiedCosineGreedy(tolerance=0.02),
    array_type="sparse",
    join_type="left",
)
```

This pattern calculates the second metric on retained coordinates. It is
inappropriate when the scientific goal is broad analog discovery across
precursor shifts or adducts.

## 5. Reproducible `Pipeline` Workflow

`Pipeline` combines import, ordered filtering, sparse score gating, and score
calculation. A workflow can also be written to YAML.

```python
from matchms import Pipeline
from matchms.Pipeline import create_workflow

common_filters = [
    "make_charge_int",
    "add_compound_name",
    "derive_adduct_from_name",
    "derive_formula_from_name",
    "clean_compound_name",
    "interpret_pepmass",
    "add_precursor_mz",
    "derive_ionmode",
    "correct_charge",
    ["require_precursor_mz", {"minimum_accepted_mz": 50.0}],
    "normalize_intensities",
    ["select_by_relative_intensity", {"intensity_from": 0.01}],
    ["require_minimum_number_of_peaks", {"n_required": 5}],
]

workflow = create_workflow(
    yaml_file_name=None,
    query_filters=common_filters,
    reference_filters=common_filters,
    score_computations=[
        ["precursormzmatch", {"tolerance": 10, "tolerance_type": "ppm"}],
        ["filter_by_range", {"name": "PrecursorMzMatch", "low": 0.5}],
        ["modifiedcosinegreedy", {"tolerance": 0.02}],
        [
            "filter_by_range",
            {"name": "ModifiedCosineGreedy_score", "low": 0.6},
        ],
    ],
)

pipeline = Pipeline(
    workflow,
    progress_bar=False,
    logging_level="WARNING",
    logging_file="matchms-pipeline.log",
)
pipeline.run(
    query_files="queries.mgf",
    reference_files="library.msp",
    cleaned_query_file="queries-cleaned.mgf",
    cleaned_reference_file="library-cleaned.msp",
    create_report=False,
)
scores = pipeline.scores
```

Notes:

- `create_workflow()` expects matchms filter callables/names and score class
  names lowercased in `score_computations`.
- The first score should establish the coordinate set when later metrics should
  be candidate-gated.
- `filter_by_range` mutates the retained coordinates.
- `Pipeline.run()` stores final scores on `pipeline.scores`.
- Output and YAML paths must not already exist.
- For all-vs-all scoring, omit `reference_files`; Pipeline then sets symmetric
  mode.

To persist and reload a workflow:

```python
from matchms import Pipeline
from matchms.Pipeline import create_workflow
from matchms.yaml_file_functions import load_workflow_from_yaml_file

create_workflow(
    yaml_file_name="workflow.yaml",
    query_filters=common_filters,
    reference_filters=common_filters,
    score_computations=[["cosinegreedy", {"tolerance": 0.02}]],
)

workflow = load_workflow_from_yaml_file("workflow.yaml")
Pipeline(workflow).run("queries.mgf", "library.msp")
```

Treat YAML as configuration, not as a substitute for recording software and
input versions.

## 6. All-vs-All Comparison

```python
from matchms import calculate_scores
from matchms.similarity import CosineGreedy

scores = calculate_scores(
    references=spectra,
    queries=spectra,
    similarity_function=CosineGreedy(tolerance=0.02),
    array_type="sparse",
    is_symmetric=True,
)
```

`is_symmetric=True` avoids redundant calculation for symmetric methods. The
logical pair count still grows quadratically. Estimate size before launching:

```python
n = len(spectra)
unique_pairs_with_diagonal = n * (n + 1) // 2
```

For large collections, consider:

- precursor/metadata candidate masks;
- `BlinkCosine` or matrix-oriented `FlashSimilarity`;
- batched query subsets;
- sparse score thresholds; and
- approximate-neighbor indexing with validated recall.

Do not densify a large result with `to_array()` merely to find top hits.

## 7. Fast Matrix Scoring

### Flash entropy

```python
from matchms import calculate_scores
from matchms.similarity import FlashSimilarity

scores = calculate_scores(
    references,
    queries,
    FlashSimilarity(
        score_type="spectral_entropy",
        matching_mode="fragment",
        tolerance=0.02,
        noise_cutoff=0.01,
    ),
)
```

### Fast modified-cosine-like mode

```python
scores = calculate_scores(
    references,
    queries,
    FlashSimilarity(
        score_type="cosine",
        matching_mode="hybrid",
        tolerance=0.02,
    ),
)
```

Flash outputs a scalar `FlashSimilarity` field without a matched-peak count.
Validate ranking agreement against a transparent baseline on representative
data.

## 8. Mirror-Plot Validation

```python
from pathlib import Path

output = Path("top-hit-mirror.png")
axis = query.plot_against(reference, figsize=(10, 6), dpi=200)
axis.figure.savefig(output, bbox_inches="tight")
```

Inspect:

- unshifted and shifted matched peaks;
- precursor and adduct agreement;
- whether the score is driven by one dominant fragment;
- unexplained high-intensity peaks; and
- collision-energy/acquisition differences.

## 9. Spectral Similarity Network

Networks require an all-vs-all `Scores` object and a unique identifier on each
spectrum:

```python
from matchms import calculate_scores
from matchms.networking import SimilarityNetwork
from matchms.similarity import ModifiedCosineGreedy

scores = calculate_scores(
    spectra,
    spectra,
    ModifiedCosineGreedy(tolerance=0.02),
    array_type="sparse",
    is_symmetric=True,
)

network = SimilarityNetwork(
    identifier_key="spectrum_id",
    top_n=20,
    max_links=10,
    score_cutoff=0.7,
    link_method="mutual",
    keep_unconnected_nodes=True,
)
network.create_network(
    scores,
    score_name="ModifiedCosineGreedy_score",
)
network.export_to_file("spectral-network.graphml", graph_format="graphml")
```

Supported export formats include GraphML, GEXF, GML, Cytoscape JSON, and JSON.
`top_n` must be at least `max_links`. Equal scores near the strict link limit
can make tie selection order-dependent; use deterministic identifiers and
document parameters.

Network components are hypotheses about spectral relatedness, not proof of
shared structure or biosynthetic origin.

## 10. Structure Versus Spectrum Similarity

Use separate labels and outputs:

- spectral similarity compares measured peak patterns;
- fingerprint similarity compares known molecular structures;
- correlation between the two can be analyzed only where reliable structures
  are available.

Do not include a query's true structure in candidate ranking when evaluating a
spectral identification method; that leaks the answer.

## 11. USI-Based Reproducible Pair

```python
from matchms.importing import load_from_usi
from matchms.similarity import CosineGreedy

reference = load_from_usi(
    "mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00000424840"
)
query = load_from_usi(
    "mzspec:MSV000086109:BD5_dil2x_BD5_01_57213:scan:760"
)
result = CosineGreedy(tolerance=0.02).pair(reference, query)
```

Record resolver, retrieval date, and returned metadata. A USI is stable
provenance, but resolver availability and returned annotations can change.

## 12. Provenance Record

At minimum, save:

```python
import json
import platform

import matchms

provenance = {
    "matchms_version": matchms.__version__,
    "python_version": platform.python_version(),
    "query_files": ["queries.mgf"],
    "reference_files": ["library.msp"],
    "metadata_harmonization": True,
    "processing_steps": query_steps,
    "similarity": {
        "class": "ModifiedCosineGreedy",
        "tolerance_da": 0.02,
    },
    "selection": {
        "top_k": 10,
        "minimum_score": 0.6,
        "minimum_matches": 5,
    },
}

with open("provenance.json", "w", encoding="utf-8") as handle:
    json.dump(provenance, handle, indent=2, default=str)
```

Also retain input checksums, library release/date, acquisition information,
code/configuration, and any manual curation decisions.

## Failure Modes

- **No modified-cosine results:** check precursor m/z after harmonization and
  filtering.
- **Unexpected `TypeError` from `SpectrumProcessor`:** call
  `process_spectrum()`/`process_spectra()`; the processor is not callable.
- **Cannot format a score as float:** extract a named field from the structured
  score record.
- **Top-hit value treated as an index:** `scores_by_query()` returns a Spectrum.
- **Huge memory use:** avoid dense conversion; gate candidates and estimate pair
  count.
- **No network edges:** verify identifier fields, score layer name, threshold,
  and that the scores are all-vs-all.
- **Fingerprint warnings:** migrate from `add_fingerprint()` to `Fingerprints`
  and bridge to the current `FingerprintSimilarity` only when required.
- **Output already exists:** matchms intentionally refuses overwrite in generic
  writers and pipeline outputs; choose a new path or remove only after explicit
  confirmation.
