# Available Molfeat 1.0 representations

Use this as a checked starting catalog, not a claim that every historical model-store
entry runs on the current release. Consult the [1.0 calculators](https://github.com/datamol-io/molfeat/tree/1.0.0/molfeat/calc)
and [pretrained adapters](https://github.com/datamol-io/molfeat/tree/1.0.0/molfeat/trans/pretrained).

## Fingerprints

All names below are accepted by `FPCalculator`. The local CPU probe ran each family
except external MAP4. Defaults refer to `FPCalculator`, not `FPVecTransformer`.

| Name | Default width | Interpretation / settings |
| --- | ---: | --- |
| `ecfp`, `fcfp` | 2048 | Radius 2; ECFP atom invariants versus FCFP feature invariants; chirality off by default |
| `ecfp-count`, `fcfp-count` | 2048 | Folded count vectors |
| `rdkit`, `rdkit-count` | 2048 | Path fingerprints |
| `atompair`, `atompair-count` | 2048 | Topological distances by default (`use2D=True`); not inherently 3D |
| `topological`, `topological-count` | 2048 | Topological torsions, default four atoms |
| `maccs` | 167 | 166 keys plus unused bit zero |
| `avalon`, `avalon-count` | 512 | Avalon substructure fingerprint |
| `pattern`, `layered` | 2048 | RDKit pattern / layered fingerprint |
| `secfp` | 2048 | Folded molecular shingles using RDKit's MHFP encoder |
| `erg` | 315 | Reduced-graph features; not simply a binary bit vector |
| `estate` | 79 | E-State atom-type counts |
| `map4` | 2048 | External `map4.MAP4Calculator` required; not installed by Molfeat extras |

For current supported parameters call `FPCalculator.default_parameters(name)`.
MAP4's standalone package has its own defaults; do not transfer them to Molfeat.
Its external backend was source-reviewed but not installed or exercised.

## Descriptors and pharmacophores

| Factory name | Concrete calculator | Requirements / contract |
| --- | --- | --- |
| `desc2D` | `RDKitDescriptors2D` | Named 2D features; 223 in the tested RDKit build, not a stable count |
| `desc3D` | `RDKitDescriptors3D` | Conformer coordinates required; inspect `columns` and `len(calc)` |
| `mordred` | `MordredDescriptors` | `molfeat[mordred]` installs mordredcommunity; default `ignore_3D=True`; descriptor count and finite values depend on configuration |
| `cats2D` | `CATS(use_3d_distances=False)` | 21 pair types × 9 default bins = 189 values |
| `cats3D` | `CATS(use_3d_distances=True)` | Conformer needed; 21 × 6 default bins = 126 values |
| `pharm2D` | `Pharmacophore2D` | `factory="default"`, `"cats"`, `"gobbi"`, or `"pmapper"`; default folded length 2048 |
| `pharm3D` | `Pharmacophore3D` | Conformers/pmapper; raw output in 1.0 is a sorted 1D integer array |
| `usr`, `usrcat` | `USRDescriptors` | 12 / 60 shape values; conformer required |
| `electroshape` | `ElectroShapeDescriptors` | 15 values; conformer and declared charge model |
| `scaffoldkeys`, `skeys`, `scaffkeys` | `ScaffoldKeyCalculator` | 42 scaffold descriptors |

Import `CATS` from `molfeat.calc`; `CATSCalculator(mode="2D")` is not the API.
Use `max_dist`, `bins`, `scale`, and `use_3d_distances`. Extra keywords to CATS can
be silently ignored, making a mistaken `mode="3D"` scientifically dangerous.
`gobbi2D`, `pmapper2D`, `rdkit2D`, and `cats2D_pharm` are not factory aliases.
For Gobbi use `Pharmacophore2D(factory="gobbi")`.

Atom/bond feature calculators live in `molfeat.calc.atom` and `molfeat.calc.bond`.
They return graph-related feature structures, not fixed-length molecular fingerprints.
Use `molfeat[pyg]` and the maintained graph transformers for PyTorch Geometric;
`atom-onehot` and `bond-default` are not `get_calculator` names.

## Pretrained models and licensing

- `PretrainedHFTransformer`: ChemBERTa, ChemGPT, MolT5 and other registered Hugging
  Face models. Query exact current card names instead of assuming availability.
  The publisher's ChemBERTa-77M-MLM config has hidden size **384**, not 768;
  pooling and concatenated layers determine the final width.
- `FCDTransformer`: ChemNet embeddings via `molfeat[fcd]`. An embedding alone is
  not a Fréchet distance; distribution comparisons need a separate statistical step.
- `CheMeleonTransformer`: maintained small-molecule graph adapter, checkpoint fetched
  from the authors; documented width 2048. No additional Chemprop runtime is needed.
- `MolJEPATransformer`: requires transformer/PyG extras, pinned remote code, and explicit
  noncommercial-license acceptance. Check upstream terms before loading.

DGL/DGLLife GIN and legacy Graphormer adapters were **removed in 1.0**. Their old cards
are historical metadata. Do not try `molfeat[dgl]`, `molfeat[graphormer]`, or instantiate
the pretrained base class with one of their names. Protein adapters are also removed.

Pretrained and optional-backend inference was not executed during this review.
Sources: [foundation-model guide](https://github.com/datamol-io/molfeat/blob/1.0.0/docs/foundation_models.md),
[ChemBERTa publisher config](https://huggingface.co/DeepChem/ChemBERTa-77M-MLM/blob/main/config.json),
[MAP4 upstream source](https://github.com/reymond-group/map4/blob/master/map4/map4.py).
