# DiffDock v1.1.3 inference contract

Reviewed 2026-09-30 against released `inference.py`, its YAML, and current main
(commit `85c49b60d3e0b0182a59ee43a34a6d7036981284`, same inference file).
This covers user-complex inference, not `evaluate` or training.

## Configuration wins over command line

`main()` loads YAML **after** argparse and overwrites matching argument values.
Therefore `--config default_inference_args.yaml --samples_per_complex 20` still
uses the YAML value 10. Edit a copied YAML for any key present there. YAML accepts
unknown keys without validating that inference uses them; acceptance is not support.

The bundled `assets/custom_inference_config.yaml` retains the released numerical
sampling defaults, contains only consumed inference settings, and explicitly uses
`old_confidence_model`, the actual parser/model-construction name.

| Option | Released effective default with default YAML | Meaning |
| --- | --- | --- |
| `model_dir` | `./workdir/v1.1/score_model` | Score model parameters/checkpoint |
| `confidence_model_dir` | `./workdir/v1.1/confidence_model` | Confidence model parameters/checkpoint |
| `ckpt` | `best_ema_inference_epoch_model.pt` | Score weights |
| `confidence_ckpt` | `best_model_epoch75.pt` | Confidence weights; parser alone instead defaults to `best_model.pt` |
| `old_score_model` | false | Architecture switch, requiring compatible weights; not a model downloader |
| `old_confidence_model` | true | Confidence architecture switch |
| `samples_per_complex` | 10 | Pose candidates per pair |
| `batch_size` | 10 | Samples processed together within a complex; complexes iterate one at a time |
| `inference_steps` | 20 | Construct the diffusion time schedule |
| `actual_steps` | 19 | Number of sampling steps executed; keep consistent with schedule |
| `no_final_step_noise` | true | Omit last-step stochastic noise |
| `initial_noise_std_proportion` | 1.4601642460337794 | Initial translation noise setting |
| `choose_residue` | false | Alternative initial positioning near sampled residue |
| `save_visualisation` | false | Additional reverse-process PDB trajectory; pose SDFs always written |
| `out_dir` | `results/user_inference` | Run-specific output directory |
| `loglevel` | WARNING | `-l`, `--log`, or `--loglevel`; INFO includes successful-run summary |

Temperature defaults (copy full precision from the asset): translation/rotation/
torsion `temp_sampling` approximately 1.170/2.064/7.044, `temp_psi` 0.727/0.902/0.595,
`temp_sigma_data` 0.930/0.746/0.694. Psi is a sampler weighting parameter, **not a
protein psi dihedral**. These coupled settings are empirically tuned. Increasing one
does not establish monotonic diversity or accuracy; no validated flexible/rigid presets
are supplied. More candidates can improve search coverage, without guaranteeing success.

## Input options

- `protein_ligand_csv`: columns `complex_name,protein_path,ligand_description,protein_sequence`.
  Overrides single-complex inputs. Upstream fills blank names with `complex_<index>`;
  the helper intentionally requires explicit safe unique names to avoid collisions.
- Single pair: `complex_name`, `protein_path` or `protein_sequence`, and
  `ligand_description`. Always use the full latter name; README's `--ligand` works
  only as argparse's currently unambiguous abbreviation, not a registered alias.
- Protein paths and ligand file paths resolve relative to **process CWD**, not CSV location.
- Ligands: SMILES attempted first, then `.sdf`, `.mol2`, `.pdb`, `.pdbqt` readers.
  Only the first SDF record is used. Input file conformers are removed and regenerated;
  a supplied pose is not a starting-pose restraint. Preserve stereochemistry and IDs.

## Options that do not work as formerly documented

`--esm_embeddings_path`, `--chain_cutoff`, `--split`, `--tqdm`, `--ode`, `--no_random`,
`--no_model`, `--resample_rdkit`, and `--limit_failures` are not inference parser options.
Some belong to evaluation/training. The released default YAML contains historical
keys (`old_filtering_model`, `sigma_schedule`, `inf_sched_alpha/beta`, `no_random`,
`no_random_pocket`, `resample_rdkit`, `ode`, `different_schedules`, `limit_failures`,
`no_model`) which this inference path does not consume. Inference hard-codes the
`expbeta` schedule. Do not present unused YAML values as operational controls.

The parser also exposes `gnina_*` fields, but `main()` never passes them into the
sampler's GNINA branch; use a separate verified GNINA invocation for refinement.
Do not disable the confidence model: output writing indexes its scores.

`datasets/esm_embedding_preparation.py` has `--dataset`, `--data_dir`, `--out_file`,
not `--protein_ligand_csv`; it prepares FASTA (PDBBind) or sequence dictionaries
(MOAD), not a `.pt` embedding tensor. Arbitrary user-complex inference generates
ESM2 embeddings internally and has no public CLI embedding-cache flag.

## Sources

- [Released inference parser, YAML merge, outputs](https://github.com/gcorso/DiffDock/blob/v1.1.3/inference.py)
- [Released default settings](https://github.com/gcorso/DiffDock/blob/v1.1.3/default_inference_args.yaml)
- [Input processing and ESM truncation](https://github.com/gcorso/DiffDock/blob/v1.1.3/utils/inference_utils.py)
- [Dataset sequence preparation](https://github.com/gcorso/DiffDock/blob/v1.1.3/datasets/esm_embedding_preparation.py)
