# Project Scaffold

Use a structured project layout when starting or cleaning up scientific analyses.

## Recommended Layout

```text
project/
├── README.md
├── data/
│   ├── raw/
│   ├── external/
│   └── processed/
├── metadata/
│   ├── analysis_plan.md
│   ├── decision_log.md
│   └── provenance.tsv
├── notebooks/
├── scripts/
├── results/
│   ├── figures/
│   └── tables/
├── reports/
├── logs/
└── env/
```

## Provenance TSV

Use columns:

```text
date_utc	artifact	source	accession_or_url	sha256	notes
```

Record every downloaded file, generated table, generated figure, model checkpoint, and manually curated metadata file.

## Analysis Plan

Include:

- research question
- datasets and inclusion/exclusion rules
- sample-label source
- primary comparisons
- QC gates
- statistical methods
- multiple-testing correction
- sensitivity analyses
- deliverables
- known limitations

## Decision Log

Record irreversible or interpretation-shaping choices:

- dataset inclusion/exclusion
- threshold choices
- method changes
- normalization/model choices
- failed checks and response
- deviations from the original plan

## Scaffolding Script

Run:

```bash
python3 scripts/init_science_project.py ./project --title "Project title"
```

Use `--dry-run` first if the destination already exists or contains valuable files.
