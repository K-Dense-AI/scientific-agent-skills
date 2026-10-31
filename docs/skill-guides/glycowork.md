[All skill guides](README.md) / glycowork

# glycowork

**Read, compare, quantify and test glycans with one Python package instead of hand-made glycan code.**

Glycans are branched sugar chains written in many competing notations, from IUPAC sequences and WURCS strings to Oxford names, GlyTouCan IDs and mass-spectrometry compositions. The glycowork skill guides an AI research assistant to use the glycowork package for this work: it converts any notation into one canonical form, computes compositions and masses, finds structural motifs, draws figures in the Symbol Nomenclature for Glycans (SNFG), and runs the statistics comparative glycomics needs. The package ships curated data, including about 50,000 glycans with species, tissue and disease labels, protein-glycan binding measurements, and analysis-ready glycomics, glycoproteomics and lectin-array datasets.

## Questions this skill can help you explore

- **What is this glycan, and is it the same as that one?** Read a structure from any common notation, compare two structures, and keep uncertain linkages explicit.
- **Which glycans could explain this mass?** Go from an observed m/z to candidate compositions and known structures, taking derivatization, reducing-end labels and adducts into account.
- **Which glycans or motifs differ between my sample groups?** Test released-glycan, site-specific glycoproteomics or lectin-array data with compositional statistics and motif-level summaries.
- **Where does this glycan occur in nature?** Look up curated species, tissue and disease annotations and protein-glycan binding data.

## What you bring

Provide glycan sequences, compositions, GlyTouCan IDs or m/z values, or an abundance table with glycans in rows and samples in columns. Exports of common glycomics and glycoproteomics software (for example Skyline, LaCyTools, GlycoWorkbench, FragPipe, pGlyco3 or Byonic) can be read directly. For group comparisons, say which samples belong to which group and whether samples are paired.

## How it works

1. **Read every glycan into one form.** Convert each notation into canonical IUPAC-condensed sequences or compositions, so that the same glycan written two ways is recognized as one.
2. **Describe the structures.** Compute compositions and masses, and annotate each glycan with known motifs such as core fucose, bisecting GlcNAc or sialyl Lewis X.
3. **Analyze abundances.** Normalize compositional data, impute missing values, and test glycans, motifs or glycosites between groups with effect sizes and multiple-testing control.
4. **Place results in context.** Draw structures in SNFG, build biosynthetic networks, and link glycans to curated species, tissue, disease and binding data.

## What you get

| Output | What it helps you do |
| --- | --- |
| Canonical sequences and compositions | Merge and compare glycans reported in different notations. |
| Masses, ion m/z values and composition matches | Assign glycans to mass-spectrometry signals. |
| Motif annotations and statistical result tables | Find which structural features change between conditions. |
| SNFG drawings and annotated figures | Communicate structures and results in publication-ready form. |

## Example request

> Use the glycowork skill to analyze my N-glycomics table of tumor and normal tissue. Convert the Oxford names to full structures, test which glycans and motifs differ between the groups, and draw the significant glycans next to a volcano plot.

*This is an illustrative request, not a reported research result.*

## Interpreting the results

**A composition is not a structure.** A mass or composition fixes which monosaccharides are present, not how they are linked; glycowork lists the known structures a composition can stand for, and the experiment decides between them. Glycan abundances are relative shares within a sample, so differences are read as changes in proportion. Motif results summarize every glycan carrying a feature, which makes them more robust than single-glycan results when many related structures shift together.

## Get started

The skill requires Python 3.11 or later and the glycowork package from PyPI (`pip install glycowork`), with optional extras for machine learning and chemical structures. The curated datasets ship with the package, so no network access or credentials are needed after installation.

[Setup and technical instructions](../../skills/glycowork/SKILL.md)
