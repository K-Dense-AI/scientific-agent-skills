---
name: glycowork
description: Glycan data science with the glycowork Python package. Use for any code that touches glycans, oligosaccharides, polysaccharides or glycoconjugates, including parsing and converting glycan notations (IUPAC-condensed/extended, WURCS, GlycoCT, GlyTouCan IDs, Oxford, LinearCode, GLYCAM, KCF, SMILES), compositions and masses, m/z to composition to structure, motif and epitope search (Lewis, sialyl, core fucose, LacNAc, blood groups), SNFG drawing, differential glycomics, glycoproteomics and lectin-array statistics, glycan databases with species/tissue/disease labels, protein-glycan binding data, biosynthetic networks, and glycan machine learning. Use it instead of writing custom glycan parsers, monosaccharide dictionaries, mass tables or string matching.
license: MIT
compatibility: Python 3.11+ with the glycowork package from PyPI (pip install glycowork; optional extras glycowork[ml] and glycowork[chem]). Tested with glycowork 1.10.1. Datasets ship with the package, so no network access or credentials are needed after installation.
metadata:
  version: "1.0"
  skill-author: Daniel Bojar
  tested-package-version: "1.10.1"
---

# glycowork

`glycowork` is the Python package for glycan data science (Bojar Lab, University of Gothenburg; docs at https://bojarlab.github.io/glycowork/). It treats every glycan as a directed graph, reads essentially every glycan notation, ships curated data (about 50,000 glycans with species/tissue/disease labels, more than 790,000 protein-glycan binding measurements, 70+ analysis-ready glycomics datasets) and does the statistics comparative glycomics needs in one call.

**The one rule:** if a task involves glycan sequences, compositions, masses, motifs or glycomics data, do it with glycowork. Do not write your own parser, regex over glycan strings, monosaccharide abbreviation dictionary, residue mass table, SNFG drawing code or motif matcher. These are the places hand-rolled code silently goes wrong (branch ordering, linkage ambiguity, modifications, sialic acid variants, permethylation, reducing-end chemistry), and glycowork already handles them.

## Install

```bash
pip install glycowork            # core: parsing, motifs, drawing, stats, networks, data
pip install "glycowork[ml]"      # + pretrained models (LectinOracle, SweetNet, NSequonPred)
pip install "glycowork[chem]"    # + RDKit-based chemistry (3D, molecular properties)
```

Requires Python 3.11+. Data ships with the package; no downloads or API keys. Every example below was run against glycowork 1.10.1.

## Ground rules

1. **Canonicalize on the way in.** Pass any glycan string through `canonicalize_iupac` (structures) or `canonicalize_composition` (compositions) before doing anything else. Mixed notations in one list are fine. GlyTouCan IDs go through `glytoucan_to_glycan`.
2. **IUPAC-condensed is the internal language.** Example: `Neu5Ac(a2-3)Gal(b1-4)[Fuc(a1-3)]GlcNAc(b1-2)Man`. The string runs from the non-reducing end to the reducing end (root last), branches sit in `[]`, linkages in `()`. Uncertainty is native: `?` for unknown anomer/position, `b1-3/4` for alternatives, and wildcard residues `Hex`, `HexNAc`, `dHex`, `Sia`, `HexA`, `Pen`.
3. **Never compare or search glycans as strings.** The same glycan can be written with branches in different orders. Use `compare_glycans` for identity and `subgraph_isomorphism`, `annotate_dataset` or `get_match` for motifs.
4. **Never sum residue masses by hand.** `glycan_to_mass` and `composition_to_mass` handle monoisotopic/average, permethylated/peracetylated, adducts and reducing-end labels.
5. **Abundance tables:** glycans in the first column, one column per sample. Groups are given as column names or indices (`group1`, `group2`). The bundled datasets already carry their groups and pairing, so analysis functions run on them with no extra arguments.
6. **Draw with `GlycoDraw`.** It produces SNFG figures from any sequence or composition; save with `filepath='x.svg'` (or `.pdf`, `.png`).

## Which function

| Task | Function (module) |
|---|---|
| Any notation to IUPAC-condensed | `canonicalize_iupac` (`glycowork.motif.processing`) |
| Parse/normalize a composition (`H5N4F1A2`, `Hex5HexNAc4...`, dict, vendor formats) | `canonicalize_composition` (`motif.processing`) |
| GlyTouCan ID to sequence (and back with `revert=True`) | `glytoucan_to_glycan` (`motif.processing`) |
| N/O/lipid/free class of a glycan | `get_class` (`motif.processing`) |
| Structure to composition / mass | `glycan_to_composition`, `glycan_to_mass` (`motif.tokenization`) |
| Composition to mass | `composition_to_mass` (`motif.tokenization`) |
| m/z to composition to candidate structures | `mz_to_composition`, `compositions_to_structures` (`motif.tokenization`) |
| Glycan to SMILES and back | `glycan_to_smiles`, `smiles_to_iupac` (`motif.smiles`) |
| Graph representation | `glycan_to_nxGraph`, `graph_to_string` (`motif.graph`) |
| Are two glycans identical | `compare_glycans` (`motif.graph`) |
| Does a glycan contain a motif (with wildcards, terminal/internal position) | `subgraph_isomorphism` (`motif.graph`) |
| Regular expressions over glycans | `get_match`, `motif_to_regex` (`motif.regex`) |
| Annotate glycans with named motifs, terminal epitopes, k-saccharides | `annotate_dataset`, `annotate_glycan`, `get_terminal_structures`, `get_k_saccharides` (`motif.annotate`) |
| Motif abundances per sample | `quantify_motifs` (`motif.annotate`) |
| Differential expression (sequences or motifs) and volcano plot | `get_differential_expression`, `get_volcano` (`motif.analysis`) |
| Multi-group, time series, diversity, PCA, heatmap, ROC | `get_glycanova`, `get_time_series`, `get_biodiversity`, `get_pca`, `get_heatmap`, `get_roc` (`motif.analysis`) |
| Lectin arrays, site-specific glycoproteomics | `get_lectin_array`, `get_glycoshift_per_site` (`motif.analysis`) |
| SNFG drawing, grids, drawings inside Excel | `GlycoDraw`, `plot_glycans_grid`, `plot_glycans_excel` (`motif.draw`) |
| Biosynthetic network, differential biosynthesis | `construct_network`, `plot_network`, `get_differential_biosynthesis` (`network.biosynthesis`) |
| Glycan database, binding data, bundled datasets | `df_glycan`, `glycan_binding`, `glycomics_data_loader`, `lectin_array_data_loader`, `glycoproteomics_data_loader`, `motif_list` (`glycan_data.loader`) |
| Predict lectin binding from a protein sequence | `prep_model('LectinOracle_flex', 1, trained=True)` + `get_lectin_preds` (`ml`, needs `[ml]`) |

Every function has a docstring with per-parameter comments; `help(fn)` is reliable. The API reference is at https://bojarlab.github.io/glycowork/ (pages `motif.html`, `glycan_data.html`, `network.html`, `ml.html`, `examples.html`).

## Examples

Mixed notations to one canonical form:

```python
from glycowork.motif.processing import canonicalize_iupac, canonicalize_composition
canonicalize_iupac("Ma3(Ma6)Mb4GNb4GN;N")   # LinearCode
canonicalize_iupac("F(3)XA2")               # Oxford
canonicalize_iupac("WURCS=2.0/3,3,2/[a2122h-1b_1-5_2*NCC/3=O][a1122h-1b_1-5][a1122h-1a_1-5]/1-2-3/a4-b1_b3-c1")
canonicalize_composition("H5N4F1A2")        # {'Hex': 5, 'HexNAc': 4, 'dHex': 1, 'Neu5Ac': 2}
```

Compositions and masses, including m/z annotation:

```python
from glycowork.motif.tokenization import glycan_to_composition, glycan_to_mass, composition_to_mass, mz_to_composition, compositions_to_structures
glycan_to_composition("Neu5Ac(a2-3)Gal(b1-4)GlcNAc")
glycan_to_mass("Neu5Ac(a2-3)Gal(b1-4)GlcNAc", sample_prep='permethylated')
composition_to_mass("Hex3HexNAc4")
mz_to_composition(1315.48, max_charge=-2, glycan_class='N')   # sign of max_charge = ion mode
compositions_to_structures([{'Hex': 3, 'HexNAc': 4}], glycan_class='N')
```

Structure identity and motif search:

```python
from glycowork.motif.graph import compare_glycans, subgraph_isomorphism
compare_glycans("Man(a1-3)[Man(a1-6)]Man", "Man(a1-6)[Man(a1-3)]Man")   # True: same glycan, different branch order
glycan = "Neu5Ac(a2-3)Gal(b1-4)[Fuc(a1-3)]GlcNAc(b1-6)[Gal(b1-3)]GalNAc"
subgraph_isomorphism(glycan, "Fuc(a1-?)[Gal(b1-?)]GlcNAc")                            # Lewis A/X anywhere
subgraph_isomorphism(glycan, "Neu5Ac(a2-3)Gal", termini_list=['terminal', 'flexible']) # terminal a2-3 sialylation
subgraph_isomorphism(glycan, "Hex", count=True)                                        # wildcard count
```

Motif annotation of a list of glycans (any notation is accepted):

```python
from glycowork.motif.annotate import annotate_dataset, get_terminal_structures
annotate_dataset(["Neu5Ac(a2-3)Gal(b1-4)[Fuc(a1-3)]GlcNAc", "F(3)XA2"], feature_set=['known', 'terminal'], condense=True)
get_terminal_structures("Man(a1-3)[Man(a1-6)]Man(b1-4)GlcNAc(b1-4)[Fuc(a1-6)]GlcNAc")
```

A full differential glycomics analysis on a bundled dataset, then SNFG output:

```python
from glycowork.glycan_data.loader import glycomics_data_loader
from glycowork.motif.analysis import get_differential_expression, get_volcano
df = glycomics_data_loader.human_skin_O_PMC5871710_SCC   # groups and pairing travel with the data
res = get_differential_expression(df)                    # own data: get_differential_expression(df, group1=[...], group2=[...], paired=False)
motif_res = get_differential_expression(df, motifs=True) # same test on motif level
get_volcano(res, annotate_volcano=True)                  # significant points are labeled with drawn structures
from glycowork import GlycoDraw
GlycoDraw("Neu5Ac(a2-3)Gal(b1-3)[Neu5Ac(a2-6)]GalNAc", highlight_motif="Neu5Ac(a2-6)GalNAc", filepath="disialyl_T.svg")
```

Querying the bundled database:

```python
from glycowork.glycan_data.loader import df_glycan, glycomics_data_loader
hits = df_glycan.meta_filter(Order='Perissodactyla').glyco_filter('Sia(a2-3)Gal')   # taxonomy filter, then motif filter
print(len(hits), hits.glycans[:3])
print(glycomics_data_loader.filter(glycan_class='O', source_type=['primary tissue', 'body fluid']))
```

`df_glycan` columns: `glycan`, taxonomy (`Species` ... `Domain`), `glytoucan_id`, `glycan_type`, `disease_*`, `tissue_*`, `Composition`. `glycan_binding` has one row per protein, one column per glycan, plus `target` and `protein`.

Biosynthetic network with inferred intermediates:

```python
from glycowork.network.biosynthesis import construct_network, plot_network
glycans = ["Gal(b1-4)Glc-ol", "GlcNAc(b1-3)Gal(b1-4)Glc-ol", "GlcNAc6S(b1-3)Gal(b1-4)Glc-ol", "Gal(b1-4)GlcNAc(b1-3)Gal(b1-4)Glc-ol",
           "Fuc(a1-2)Gal(b1-4)Glc-ol", "Neu5Ac(a2-3)Gal(b1-4)GlcNAc(b1-3)[Gal(b1-3)GlcNAc(b1-6)]Gal(b1-4)Glc-ol"]
net = construct_network(glycans)   # unmeasured intermediates are inferred, edges are labeled with reactions
print(net.number_of_nodes(), net.number_of_edges())   # 14 nodes, 19 reactions from 6 measured glycans
plot_network(net, draw_glycans=True)
```

## Gotchas

- Reducing-end aglycones that matter biologically survive canonicalization (`GalNAc1Ser`, `GlcNAc1Asn`, `Glc1Cer`, `Glc-ol` for alditols); spacers and linkers from glycan arrays (`-Sp8`, `-OCH2CH2NH2`) are stripped.
- Compositions are not structures: `canonicalize_iupac` passes `H5N4F1A2` through unchanged (and raises on vendor table formats such as Byonic/pGlyco compositions). Route compositions through `canonicalize_composition`, and use `is_composition` (`motif.processing`) when input could be either.
- Glycan graphs are cached internally: copy a graph before mutating it.
- `mz_to_composition` needs the ion mode via the sign of `max_charge` and a `glycan_class`; pass `modification` (`reduced`, `2AA`, `2AB`, `procainamide`) and `sample_prep` (`permethylated`, `peracetylated`) when they apply.
- For Oxford-style N-glycan names (`A2G2S2`, `FA2`, `M5`), `canonicalize_iupac` expands them to full structures; do not maintain a lookup table.
- Plots return matplotlib figures and display in Jupyter; set `filepath=` to save (SVG/PDF keep the SNFG drawings vectorial).

## Citation

Thomes L, Burkholz R, Bojar D. glycowork: A Python package for glycan data science and machine learning. Glycobiology 31(10):1240-1244 (2021). doi:10.1093/glycob/cwab067
