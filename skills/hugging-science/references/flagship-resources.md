# Flagship resources by domain

Sensible "if in doubt, start here" picks per scientific domain. These are the resources users most often want when they describe a task in plain language. Always confirm with the live catalog (`fetch_catalog.py topic <slug>`) before final recommendation — the catalog evolves and there may be something newer.

The catalog is the source of truth. Treat this file as a fast cheatsheet, not a directory.

## Biology / Genomics

**DNA foundation models**
- `arcinstitute/evo2_40b` — 40B-param DNA LM, 9.3T nucleotide pretraining; zero-shot variant effect prediction, sequence generation. Huge — use Inference Providers or a Space.
- `arcinstitute/evo2_7b` — 7B instruction-tuned variant; runs on a single 24 GB GPU.

**Protein language models**
- `facebook/esm2_t33_650M_UR50D` — 650M ESM2; standard for embeddings, structure prediction, mutation scoring. Strong default.
- Smaller ESM2 variants (`*_t30_150M_*`, `*_t12_35M_*`) for laptop/CPU use.

**Single-cell / transcriptomics**
- `arcinstitute/Stack-Large` (STACK) — single-cell foundation model with in-context learning across cell types.
- `Merck/TEDDY` — 116M single-cell foundation models for genomics + drug discovery.

**Antibodies**
- `opig/OAS` — Observed Antibody Space, ~1B antibody sequences. The standard antibody ML dataset.

**Bioacoustics / ecology**
- `EarthSpeciesProject/NatureLM-audio` — first audio-LM for animal vocalizations.
- `EarthSpeciesProject/esp-aves2-sl-beats-all` — self-supervised bioacoustic encoder.

**Genomic corpora**
- `arcinstitute/opengenome2` — curated prokaryotic + eukaryotic sequences for foundation-model pretraining.

## Chemistry / Drug discovery

- `SandboxAQ/AQAffinity` — drug-target affinity prediction.
- **SAIR dataset** — 1M+ protein-ligand co-structures (see SandboxAQ blog post in catalog).
- For SMILES/molecular tasks: check the catalog `chemistry` topic for current best — molecular foundation models change frequently.

## Materials science

- **LeMaterial** — large open materials database (see catalog blog post 2024-12-10).
- Crystal structure foundation models, perovskite datasets — fetch `topic materials-science` for the live list. Many ship `pymatgen.Structure` objects rather than tensors.

## Physics

- PDE-solver datasets (`topic physics --filter datasets`) — magnetohydrodynamics, fluid dynamics, plasma.
- Physics-Informed Neural Networks (PINN) — methodology covered in catalog blog posts.

## Climate / Earth science / Weather

- Weather-foundation-model entries under `topic climate` — these are often huge multi-modal models with structured atmospheric inputs (geopotential, temperature on multiple pressure levels).
- Satellite imagery / remote sensing models under `topic earth-science`.

## Medicine / Pathology

- `hugging-science/breast-cancer-detector-2` — image classification baseline from the org itself.
- Pathology + radiology foundation models — fetch `topic medicine`. Many are gated; check the model card for access requirements.

## Mathematics / Scientific reasoning

- **Kimina-Prover** family — large theorem-proving models. Likely needs Inference Providers.
- `topic scientific-reasoning` for LLM-as-scientific-assistant work, paper QA, multi-step reasoning evals.

## Astronomy

- Galaxy survey datasets (e.g., `hugging-science/mmu_legacysurvey_dr10_south_21`) — image-heavy, FITS format, may need `astropy`.
- Astronomical foundation models — fetch `topic astronomy`.

## Cross-domain interactive demos (Spaces)

- `hugging-science/boltzgen-demo` — protein/peptide/nanobody binder design (the marquee demo).
- `hugging-science/dataset-quest` — discover and submit scientific datasets.
- `hugging-science/science-release-heatmap` — visualize who's publishing AI4Science resources.

## How to use this list

1. User describes a task → match to a domain row above.
2. Fetch the live topic file with `fetch_catalog.py topic <slug>` and confirm the recommended resource still exists / is current.
3. Read the resource's HF card for input format, license, access requirements.
4. Follow `using-datasets.md` / `using-models.md` / `using-spaces.md` for the actual code.
5. If a related blog post is listed in the catalog, cite it when explaining methodology.

If nothing in this cheatsheet fits, run `fetch_catalog.py search "<keyword>"` against the full index. The catalog has hundreds of entries this file doesn't enumerate.
