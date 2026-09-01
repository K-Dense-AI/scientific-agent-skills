# State Comparison And GPCR Stories

Use this route when the question is where two states differ, by how much, and
whether ligand or partner context makes that difference interpretable.

## Freeze Comparable States

Confirm before alignment:

- same protein identity or an explicit residue correspondence;
- construct differences, mutations, truncations, fusion proteins, missing loops,
  resolution/confidence, biological assembly, and bound partners;
- state labels supported by the source record rather than inferred from ligand
  name alone;
- residue-numbering convention used in text and selectors;
- exact ligand identity, occupancy/altloc policy, and whether it is covalent.

An apo/holo or inactive/active pair is observational evidence. It does not by
itself prove that the ligand caused every structural difference; constructs,
crystal contacts, partners, mutations, and ensemble selection can also differ.

## Align For The Question

Map equivalent residues first. Align a declared stable core that preserves the
motion being measured; aligning on the moving region can erase the signal.
Record every included range, atom type, mismatch, missing residue, matched count,
RMSD, and transform.

For GPCR activation, a reasonable starting hypothesis is a well-resolved
transmembrane-bundle core while excluding fusion partners, long loops, termini,
and the cytoplasmic portions whose movement is the question. This is not a
universal fixed range: use GPCRdb/UniProt mapping and the actual structures to
choose and disclose the core. Repeat with a plausible alternate core when the
conclusion depends materially on that choice.

Apply the fitted transform to the complete mobile complex. Keep its ligand,
G-protein/nanobody, cofactors, and receptor in one frame.

For PDB inputs with matching author residue numbers, `analyze_pair.py` provides a
literal deterministic path:

```bash
python3 scripts/analyze_pair.py reference.pdb mobile.pdb \
  --reference-chain A --mobile-chain A \
  --align-range 36:63 --align-range 72:98 \
  --align-range 108:139 --align-range 151:173 \
  --segments-tsv gpcr_segments.tsv \
  --mobile-ligand-resname RET \
  --output-dir derived/state-comparison
```

The script writes `reference.pdb`, `mobile_aligned.pdb`,
`comparison_metrics.json`, `per_residue_displacement.tsv`, and optional
`ligand_contacts.tsv`. It matches Cα atoms by author residue number/insertion
code, so do not use it when renumbering or nontrivial sequence alignment is
required; prepare an explicit mapping with an appropriate structure tool instead.

## Quantify Global And Local Change

At minimum report:

- core alignment RMSD and matched Cα count;
- per-residue Cα displacement after that alignment;
- segment-level count, mean, median, maximum, and the residue at the maximum;
- the largest decision-relevant residue/segment changes, not only the global
  maximum (which may be a missing or flexible loop boundary);
- source and derived coordinate hashes.

For GPCRs, inspect only metrics supported by the mapping and question:

- cytoplasmic TM6 outward displacement and/or helix-axis change;
- TM7/NPxxY and helix-8 rearrangement;
- DRY/ionic-lock or other receptor-specific microswitch distances;
- orthosteric-pocket contraction/expansion and ligand contact changes;
- intracellular partner occupancy and contacts.

Name the exact residue pair or segment used for every scalar. Generic labels such
as "TM6 moved 8 Å" are incomplete without alignment core, measurement point,
numbering system, and state direction.

## Build The Story

Copy `assets/state-comparison-story/` and bind the frozen outputs. A useful
sequence is:

1. **Provenance/context:** what structures, constructs, states, chains, and
   partners are being compared?
2. **Reference state:** what spatial features define the baseline?
3. **Mobile/ligand state:** where is the ligand and which local contacts or
   partners distinguish this state?
4. **Aligned overlay:** what is globally conserved under one declared core fit?
5. **Localized displacement:** where are the largest relevant movements, with
   arrows/labels carrying frozen Å values?
6. **Decision:** what mechanism or next experiment is supported, and what remains
   confounded or unproven?

That is a comparison-first route, not a fixed mechanism order. When the user is
trying to understand an ordered mechanism and the evidence chain supports it,
follow the directed reading order instead. For example: whole receptor -> pocket
orientation -> ligand reveal with its computed contact shell -> intracellular
endpoint difference -> key mapped displacements -> observed partner insertion ->
counterfactual incompatibility and boundary. Merge a separate conclusion scene
into the last discriminating view when it would only repeat the same geometry.

Use a common camera for state and overlay scenes. Draw displacement vectors from
reference to aligned mobile coordinates, but describe them as endpoint
differences, not a physical trajectory. If an animation is used, repeat that
boundary in the scene text.

Keep adjacent camera orientations stable. The maintained template uses one
overview camera for provenance/reference and one shared detail camera for
ligand, overlay, motion, and decision scenes, with short camera interpolation.
Keep small recurring representation nodes under stable refs when that prevents a
verified delete/rebuild jump, but do not carry every full receptor as a
translucent ghost through every scene. Prefer an opaque primary receptor, use the
camera to retain orientation, and reserve two whole-state cartoons for the
aligned-overlay question. Do not use an instantaneous scene switch to imply a
conformational jump, and do not smooth structural coordinates between endpoints
unless a real trajectory is the evidence.

Use complete-residue sticks for microswitches and pocket residues. For ligands,
retain element colors with a semantic carbon override. Avoid an all-residue
rainbow displacement view unless a quantitative legend and scale make it
readable; a small annotated set plus the TSV is usually more informative.

## Decision Boundary

A good final scene distinguishes:

- **observed:** coordinates, aligned displacements, contacts, partners;
- **interpretation:** a state-associated rearrangement consistent with a known
  mechanism;
- **not established:** causal ligand pathway, thermodynamics, kinetics, or the
  ensemble distribution from two frozen structures;
- **next action:** additional structures, simulations, mutagenesis, functional
  assays, or an alternate alignment sensitivity check.
