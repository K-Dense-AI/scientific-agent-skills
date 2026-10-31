# Confidence, scientific scope and validation

Reviewed against DiffDock v1.1.3 source/README and the DiffDock-L paper on 2026-09-30.

## Meaning of a score

DiffDock's confidence model ranks candidate poses for a protein-ligand pair. It does
not output a calibrated binding probability, dissociation constant, selectivity,
residence time or ADMET endpoint. Even if confidence correlates with binding in a
particular dataset, that does not establish an affinity model.

The upstream FAQ gives rough top-pose bands `c > 0`, `-1.5 < c < 0`, `c < -1.5`;
it does not define equality. The helper assigns zero to Moderate and -1.5 to Low.
These conventions and thresholds are not guarantees of pose correctness. Filename
values have only two decimal places; preserve upstream rank and original artifacts.
Nonfinite or missing scores are Unknown, not zero or Low.

Comparison across different ligands and receptor conformations is difficult and not
calibrated. `analyze_results.py --best` is a convenience for inspection, not a ranking
of compounds by potency. Low confidence does not prove a ligand cannot bind. Multiple
similar sampled poses are not independent replicates; consensus can repeat model bias.

## Applicability

The trained/tested problem is small-molecule docking to proteins. Success at parsing a
peptide, nucleotide, macrocycle, metal-containing compound or very large ligand does
not demonstrate reliable modeling. There is no universal molecular-weight or residue
count rule that makes such inputs supported. Covalent binding and accurate coordination
chemistry require appropriate specialist methods. DiffDock does not perform a fully
flexible receptor search; separate conformations provide separate hypotheses.

The original DiffDock and DiffDock-L have different training/evaluation settings.
DiffDock-L adds data and generalization strategies including Binding MOAD and van der
Mers augmentation; record the checkpoint and assess similarity/leakage against its
training data before describing performance on a new benchmark. Do not label all new
proteins or membrane proteins categorically supported/unsupported without evidence.

## Validation workflow

1. Check intended ligand molecular graph, charge, tautomer and stereochemistry. The
   upstream file-input route removes existing conformers and generates a new one.
2. Reconcile input IDs with output ranks and failed/skipped counts. Avoid reused output
   directories. Both a silent skip and a stale output can masquerade as success.
3. Check atom/bond identity, stereochemistry, bond lengths/angles, aromatic planarity,
   internal strain and receptor clashes using independent tools such as PoseBusters.
   These checks establish plausibility constraints, not experimental correctness.
4. Visually review candidate pockets, biologically relevant chains, conserved waters,
   cofactors and metal coordination. Do not remove meaningful components blindly.
5. For any refinement, keep raw and refined structures and the mapping between them.
   Relax in the actual downstream force field with appropriate ligand parameters;
   revalidate afterwards. Rescoring does not repair an invalid pose automatically.
6. If a reference pose is available, align receptors consistently and compare ligand
   atoms with a chemically valid symmetry mapping. A low RMSD does not replace
   stereochemical/clash validation. Without a reference, do not report pose accuracy.
7. Assess affinity with a separately validated model or protocol when needed. GNINA,
   MM/GBSA and free-energy methods have different assumptions and error sources; no
   universal accuracy ordering or mandatory rescoring workflow applies to every system.
8. Report uncertainty and validate experimentally where warranted.

## Upstream implementation limits

- PDB inference still generates ESM2 embeddings. Per-chain tokenization truncates at
  1022 residues; inspect long-chain targets for mismatched embedding/graph lengths.
- Sequence folding calls CUDA regardless of CPU fallback elsewhere and adds folding
  uncertainty. A plausible fold need not be the ligand-bound conformation.
- The inference loop can skip individual complexes. Exit status is insufficient.
- The `batch_size` is for samples within each complex, not concurrent protein pairs.
- The supported inference CLI offers neither a pocket-selection flag nor a precomputed
  ESM-embedding flag. Changing chain selection changes the prepared input itself.

## Sources

- [Upstream confidence FAQ and scope](https://github.com/gcorso/DiffDock/blob/v1.1.3/README.md)
- [Input preparation and ESM2/ESMFold implementation](https://github.com/gcorso/DiffDock/blob/v1.1.3/utils/inference_utils.py)
- [DiffDock-L paper](https://arxiv.org/abs/2402.18396)
- [Original DiffDock paper](https://arxiv.org/abs/2210.01776)
- [PoseBusters documentation](https://posebusters.readthedocs.io/en/latest/)
