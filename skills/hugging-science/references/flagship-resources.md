# Flagship resources by domain

Sensible "if in doubt, start here" picks per scientific domain. These are the resources users most often want when they describe a task in plain language. Always confirm with the live catalog (`fetch_catalog.py topic <slug>`) before final recommendation — the catalog evolves and there may be something newer.

The catalog is a discovery index; author cards, released code and live service metadata determine the usable interface. Reviewed 2026-10-01; no pretrained inference was run.

## Biology / Genomics

**DNA foundation models**
- `arcinstitute/evo2_40b` — 40B DNA language model trained using the 8.8T-base OpenGenome2 corpus. Uses native Evo2/Vortex; current Hub provider mapping is empty. Arc documents NVIDIA hosting and multi-H100 local execution.
- `arcinstitute/evo2_7b` — 7B DNA language model, not an instruction-tuned chat variant. Native runtime supports BF16 without Transformer Engine; hardware feasibility depends on context and batch size.

**Protein language models**
- `facebook/esm2_t33_650M_UR50D` — 650M masked protein language model for embeddings or task-specific scoring. Its encoder alone does not output folded coordinates; folding requires a suitable model/head. Current HF provider mapping exposes fill-mask.
- Smaller ESM2 variants (`*_t30_150M_*`, `*_t12_35M_*`) for laptop/CPU use.

**Single-cell / transcriptomics**
- `arcinstitute/Stack-Large` (STACK) — single-cell foundation model with in-context learning across cell types.
- `Merck/TEDDY` — single-cell model/code repository trained on approximately 116 million cells; 116M describes training cells, not parameter count. Use its AnnData preprocessing and model classes.

**Antibodies**
- `opig/OAS` — Observed Antibody Space; inspect its paired/default configs and metadata before selecting a bounded subset.

**Bioacoustics / ecology**
- `EarthSpeciesProject/NatureLM-audio` — audio-language model for animal vocalizations; follow its dedicated loader and preprocessing.
- `EarthSpeciesProject/esp-aves2-sl-beats-all` — bioacoustic encoder requiring the AVEX library; verify the selected checkpoint's training and input contract.

**Genomic corpora**
- `arcinstitute/opengenome2` — curated prokaryotic + eukaryotic sequences for foundation-model pretraining.

## Chemistry / Drug discovery

- `SandboxAQ/AQAffinity` — gated drug-target affinity resource. Public metadata exists; card/artifact access requires accepted terms, so execution was not verified.
- **SAIR dataset** — protein-ligand structural/affinity resource (see SandboxAQ catalog entry). Its card was not accessible anonymously during review; verify source provenance, labels and terms before treating counts or structures as experimental ground truth.
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

- `hugging-science/breast-cancer-detector-2` — community breast ultrasound image-classification checkpoint. Catalog membership is not clinical validation; check cohort, patient splits, labels and intended use before benchmarking.
- Pathology + radiology foundation models — fetch `topic medicine`. Many are gated; check the model card for access requirements.

## Mathematics / Scientific reasoning

- **Kimina-Prover** family — large theorem-proving models. Read the selected model card and verify a live provider mapping; availability is not implied by parameter count. Validate generated proofs with the exact Lean/mathlib environment.
- `topic scientific-reasoning` for LLM-as-scientific-assistant work, paper QA, multi-step reasoning evals.

## Astronomy

- Galaxy survey datasets (e.g., `hugging-science/mmu_legacysurvey_dr10_south_21`) — HATS/Parquet release with image-array fields; inspect its schema and HATS reader requirements rather than assuming FITS files.
- Astronomical foundation models — fetch `topic astronomy`.

## Cross-domain interactive demos (Spaces)

- `hugging-science/BoltzGen_Demo` — protein/peptide/nanobody binder design (source contract reviewed; runtime returned 503).
- `hugging-science/dataset-quest` — discover and submit scientific datasets.
- `hugging-science/science-release-map` — visualize who's publishing AI4Science resources.

## How to use this list

1. User describes a task → match to a domain row above.
2. Fetch the live topic file with `fetch_catalog.py topic <slug>` and confirm the recommended resource still exists / is current.
3. Read the resource's HF card for input format, license, access requirements.
4. Follow `using-datasets.md` / `using-models.md` / `using-spaces.md` for the actual code.
5. If a related blog post is listed in the catalog, cite it when explaining methodology.

If nothing in this cheatsheet fits, run `fetch_catalog.py search "<keyword>"` against the full index. The catalog has hundreds of entries this file doesn't enumerate.

Primary cards: [Evo2](https://github.com/ArcInstitute/evo2), [TEDDY](https://huggingface.co/Merck/TEDDY), [STACK](https://huggingface.co/arcinstitute/Stack-Large), [AVEX checkpoint](https://huggingface.co/EarthSpeciesProject/esp-aves2-sl-beats-all), [Legacy Survey release](https://huggingface.co/datasets/hugging-science/mmu_legacysurvey_dr10_south_21).
