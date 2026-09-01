# Verdict taxonomy

Every verify-citations script emits the same verdict strings so reports,
filters, and downstream tooling can switch on them directly.

## The verdicts

| Verdict | Emitted by | Meaning | Recommended action |
|---|---|---|---|
| `verified` | verify_references | The entry resolved against a provider record and the stated metadata (title similarity >= 0.85, year within 1, first-author surname match) agrees with it. | None. |
| `metadata-mismatch` | verify_references | The entry resolved to a real work, but stated details disagree with the canonical record. | Read the mismatch reasons; fix the manuscript or confirm the intended source. |
| `retracted` | verify_references, check_retractions | Crossref `update-to`/`updated-by` or OpenAlex `is_retracted` marks the work as retracted/withdrawn. | Remove the citation; cite the retraction notice if the fact of retraction matters. |
| `not-found` | verify_references | The entry carried a checkable identifier or title, and every provider returned no record above the match threshold. | Hand-verify. For mainstream-looking papers this is the strongest hallucination signal; for theses/datasets/grey literature it can be a false negative of the providers. |
| `unresolved` | both | A network or API error (HTTP status, timeout) prevented checking. | Retry later; `--pause` up if rate-limited. |
| `skipped` | verify_references | The entry had no DOI/arXiv/PMID and its title was too short/absent to search. | Add an identifier, or check manually (books, websites, software). |

## Precedence

A single entry receives exactly one verdict, chosen in this order:

1. `retracted` -- a retraction overrides everything else (a retracted paper
   that matches perfectly is still removed).
2. `metadata-mismatch` -- the work is real but misdescribed.
3. `verified`.
4. `not-found` / `unresolved` / `skipped` when checking could not complete.

## Thresholds and their knobs

- **Title similarity threshold: 0.85** (Dice coefficient over normalized
  token sets, with a containment bonus for subtitles). Passed via
  `compare_metadata(..., title_threshold=...)`.
- **Year tolerance: 1** -- catches the common off-by-one (online vs print
  year) without silently accepting wrong decades.
- **First-author surname**: compared on the normalized surname only; initial
  differences and name-order variants do not trigger mismatches.

## False-positive and false-negative profile

- `not-found` false positives: grey literature, non-English titles that were
  transliterated, very short titles colliding below threshold.
- `verified` false negatives: Crossref records with sparse metadata (no
  author list) will skip that comparison rather than fail it.
- `metadata-mismatch` high precision: it requires an actual resolution, so
  the comparison is against a canonical record, not a guess.
