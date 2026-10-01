# Identification and confidence (pyOpenMS 3.6.0)

## Search engines and provenance

OpenMS TOPP adapters and their engine executables are separate from the Python
wheel. Use a supported installed adapter's `--help` and versioned parameter file;
do not invent `ms.CometAdapter` or assume a search engine is bundled. This skill
postprocesses precomputed idXML. Comet, Mascot, MSGF+, X! Tandem and MSFragger
searches, rescoring, protein inference accuracy and proprietary engines were not
executed in this audit.

Record raw data/conversion, target+decoy FASTA checksum and decoy strategy,
enzyme/specificity/missed cleavages, fixed versus variable modifications,
precursor/fragment tolerance values **and units**, charge/isotope hypotheses,
search-engine version and rescoring. `SearchParameters` records settings; merely
setting it does not run a database search. Use `digestion_enzyme`,
`fixed_modifications`, `variable_modifications`, `precursor_mass_tolerance`,
`precursor_mass_tolerance_ppm`, `fragment_mass_tolerance` and
`fragment_mass_tolerance_ppm`, not invented `enzyme`/`modifications` attributes.

## Local idXML processing

```python
import pyopenms as ms
proteins, peptides = ms.IdXMLFile().load("search.idXML")
for pid in peptides:
    print(pid.getIdentifier(), pid.getScoreType(), pid.isHigherScoreBetter())
    for hit in pid.getHits():
        print(hit.getSequence().toString(), hit.getCharge(), hit.getScore())
        if hit.metaValueExists("target_decoy"):
            print(hit.getMetaValue("target_decoy"))
ms.IdXMLFile().store("copy.idXML", proteins, peptides)
```

`PeptideIdentificationList` is the mutable ID container; protein runs remain a
Python list. In 3.6, string accessors return `str`; do not blindly `.decode()`.
`getIdentifier()` links peptide IDs to a protein/search run; it is not the engine
name. Read `getScoreType()` and `isHigherScoreBetter()` rather than inferring
score meaning from filenames or a substring such as Comet.

```bash
python scripts/process_identifications.py search.idXML --fasta target_decoy.fasta --decoy-prefix DECOY_ --fdr 0.01 --out filtered.idXML --csv hits.csv
```

This file-dependent recipe was exercised on a tiny constructed target/decoy
FASTA and idXML, not a real search. Re-index using exactly the database used for
searching. The prefix is configurable; the CLI uses prefix matching, not suffix
matching. `PeptideIndexing.run` returns status plus updated output containers;
non-success status is an error. Missing decoys are an error, not a warning.

## FDR assumptions

`filter_psm_qvalues` checks finite original scores, valid target/decoy annotations,
one search run/score type/direction, and both target and decoy **top** hits. This
prevents the native no-decoy behavior from producing misleading zero q-values.
`FalseDiscoveryRate` sorts and retains the first hit by default, estimates q-values,
removes decoys by default, sets score type `q-value` and lower-is-better, and puts
the q-value in **`hit.getScore()`**. It is not generally a `q-value` meta-value.
The helper explicitly sets `no_qvalues=false`, `use_all_hits=false`, and
`add_decoy_peptides=false`; record all other defaults with the result.

A 1% PSM threshold is neither a per-hit probability nor 1% protein FDR. Unique
peptide, protein and protein-group error control are separate. Tiny fixtures test
API behavior and safeguards only; they cannot establish statistical calibration.
Do not repeatedly estimate FDR from already transformed scores. Post-FDR length
filters change the reported population and do not establish an independently
controlled subgroup FDR. Mixed runs require an explicit pooling/stratification
plan rather than silently accepting incomparable scores.

## Feature annotation and protein inference

`IDMapper.annotate(feature_map, peptides, proteins)` maps IDs onto features using
m/z/RT tolerances, charge and hull assumptions; it does not infer proteins.
`BasicProteinInferenceAlgorithm.run(peptides, proteins)` aggregates evidence and
returns updated protein runs in 3.6. Protein hits are not a protein group simply
because multiple hits occur in one run. Inspect `getProteinGroups()` and
`getIndistinguishableProteins()` where appropriate and perform separately
validated protein/group-level confidence estimation. This workflow is
illustrative here, not a validated protein-inference pipeline.

## Chemistry

The bundled digestion, mass and theoretical-spectrum scripts have synthetic
native regression tests. The spectrum generator requires an `MSSpectrum`, not a
Python list:

```python
seq = ms.AASequence.fromString("PEPTIDEM(Oxidation)K")
fragments = ms.MSSpectrum()
ms.TheoreticalSpectrumGenerator().getSpectrum(fragments, seq, 1, 2)
```

Fragment charge bounds are positive magnitudes; sequence modifications alter
mass. Theoretical intensities do not predict instrument spectra. An arbitrary
similarity cutoff such as 0.7 is not validated spectral-library identification.
Decoy construction also needs deliberate enzyme/modification/duplicate handling;
`DecoyGenerator.reverseProtein` accepts an `AASequence`, not a `FASTAEntry`.

Sources: [FDR release implementation](https://github.com/OpenMS/OpenMS/blob/5d5cbff4053b281763a1a79bf69e81c27967cfdf/src/openms/source/ANALYSIS/ID/FalseDiscoveryRate.cpp),
[OpenMS FDR API](https://openms.de/documentation/classOpenMS_1_1FalseDiscoveryRate.html)
and installed 3.6.0 binding signatures. Use the implementation to resolve stale or
internally inconsistent formula descriptions in generated API documentation.
