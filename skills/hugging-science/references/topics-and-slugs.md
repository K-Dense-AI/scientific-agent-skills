# Topic slugs and entry schema

The Hugging Science catalog organizes scientific resources across **17 topics**. Each has a markdown file at `https://huggingscience.co/topics/<slug>.md`. Slugs are lowercase and hyphenated.

## Topic slugs and what each covers

| Slug | What's in here |
|---|---|
| `astronomy` | Galaxy/stellar surveys, cosmology, exoplanets, telescope imagery, foundation models for astronomical data |
| `benchmark` | Cross-domain evaluation suites — useful when comparing methods or running standard tests |
| `biology` | Protein/DNA/single-cell data and models, antibodies, bioacoustics, microbiome — broad biology umbrella |
| `biotechnology` | Synthetic biology, fermentation, applied genetic engineering data |
| `chemistry` | Molecules, reactions, drug discovery, SMILES corpora, DFT data, ligand-protein interactions |
| `climate` | Weather forecasting, climate models, atmospheric data, storm/flood prediction |
| `conservation` | Wildlife monitoring, biodiversity, camera-trap and bioacoustic models |
| `earth-science` | Remote sensing, satellite imagery, geospatial foundation models |
| `ecology` | Species distribution, ecosystem dynamics, biogeography (overlaps with conservation/biology) |
| `energy` | Battery materials, fusion plasma, grid simulation, renewables modeling |
| `engineering` | CAD, mechanical/structural simulation, robotics datasets |
| `genomics` | DNA language models, variant effect, single-cell, phylogenetics (overlaps heavily with biology) |
| `materials-science` | Crystal structures, band gaps, catalysts, perovskites, alloys, materials foundation models |
| `mathematics` | Theorem proving, formal math, mathematical reasoning datasets |
| `medicine` | Pathology, radiology, clinical NLP, drug-disease, EHR (overlaps with biology/chemistry) |
| `physics` | PDE solvers, fluid/plasma simulation, particle physics, physics-informed ML |
| `scientific-reasoning` | LLMs for scientific QA, paper understanding, multi-step scientific reasoning |

## Cross-domain reality

Most real tasks span multiple slugs. Pull all relevant ones rather than guessing:

- "Drug discovery" → `chemistry`, `biology`, `medicine`
- "Protein structure prediction" → `biology`, `chemistry`
- "Weather forecasting model" → `climate`, `earth-science`, `physics`
- "Single-cell foundation model" → `biology`, `genomics`, `medicine`
- "Battery electrolyte design" → `materials-science`, `chemistry`, `energy`
- "Bioacoustic species ID" → `biology`, `ecology`, `conservation`

When in doubt, fall back to `python scripts/fetch_catalog.py search "<keyword>"` against the full catalog.

## Entry schema

Each catalog entry is an H3 block with bulleted metadata followed by a description. Three flavors:

### Datasets
```
### org/dataset-name
- **Type**: <category, e.g. "Genomics", "Pathology", "PDE Simulation">
- **Tags**: <comma-separated topic tags>
- **HuggingFace**: https://huggingface.co/datasets/org/dataset-name

<one-line description>
```

### Models
```
### Model Display Name
- **Type**: <category, e.g. "Protein Language Model", "Materials Foundation Model">
- **Tags**: <comma-separated topic tags>
- **HuggingFace**: https://huggingface.co/org/model-id

<one-line description>
```

### Blog posts
```
### Post Title
- **Author**: <username>
- **Date**: <YYYY-MM-DD>
- **Tags**: <comma-separated>
- **Link**: <URL — usually huggingface.co/blog/...>

<one-line description>
```

## Endpoints

- `https://huggingscience.co/llms.txt` — compact site index
- `https://huggingscience.co/llms-full.txt` — every entry, every domain (this is the file to fetch when you want to grep across the whole catalog)
- `https://huggingscience.co/topics/<slug>.md` — one domain
- `https://huggingscience.co/feed.xml` — RSS for new entries

The `fetch_catalog.py` script wraps these and adds parsing, filtering, and JSON output. Prefer the script for structured access; use raw `WebFetch`/`curl` only if the script fails.
