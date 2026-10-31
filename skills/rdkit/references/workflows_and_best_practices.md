# RDKit Workflows and Best Practices

Worked workflows (drug-likeness analysis, similarity screening, substructure filtering)
followed by error handling, performance optimization, version-sensitive behavior, thread
safety, and memory management.

## Common Workflows

### Drug-likeness Analysis

```python
from rdkit import Chem
from rdkit.Chem import Descriptors

def analyze_druglikeness(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    # Calculate Lipinski descriptors
    results = {
        'MW': Descriptors.MolWt(mol),
        'LogP': Descriptors.MolLogP(mol),
        'HBD': Descriptors.NumHDonors(mol),
        'HBA': Descriptors.NumHAcceptors(mol),
        'TPSA': Descriptors.TPSA(mol),
        'RotBonds': Descriptors.NumRotatableBonds(mol)
    }

    # Check Lipinski's Rule of Five
    results['Lipinski'] = (
        results['MW'] <= 500 and
        results['LogP'] <= 5 and
        results['HBD'] <= 5 and
        results['HBA'] <= 10
    )

    return results
```

### Similarity Screening

```python
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator
from rdkit import DataStructs

def similarity_screen(query_smiles, database_smiles, threshold=0.7):
    query_mol = Chem.MolFromSmiles(query_smiles)
    if query_mol is None:
        return []

    morgan_gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    query_fp = morgan_gen.GetFingerprint(query_mol)

    hits = []
    for idx, smiles in enumerate(database_smiles):
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            fp = morgan_gen.GetFingerprint(mol)
            sim = DataStructs.TanimotoSimilarity(query_fp, fp)
            if sim >= threshold:
                hits.append((idx, smiles, sim))

    return sorted(hits, key=lambda x: x[2], reverse=True)
```

### Substructure Filtering

```python
from rdkit import Chem

def filter_by_substructure(smiles_list, pattern_smarts):
    query = Chem.MolFromSmarts(pattern_smarts)
    if query is None or query.GetNumAtoms() == 0:
        raise ValueError("Invalid or empty SMARTS")

    hits = []
    for smiles in smiles_list:
        mol = Chem.MolFromSmiles(smiles)
        if mol and mol.HasSubstructMatch(query):
            hits.append(smiles)

    return hits
```

## Best Practices

### Error Handling

Always check for `None` when parsing molecules:

```python
mol = Chem.MolFromSmiles(smiles)
if mol is None:
    print(f"Failed to parse: {smiles}")
    continue
```

### Performance Optimization

**Use safe storage formats:**

```python
import base64
import json
from pathlib import Path
from rdkit import Chem

# Portable exchange formats such as SMILES and SDF are safest for shared data.
# For local caches, RDKit's binary molecule representation avoids generic pickle.
payload = [base64.b64encode(mol.ToBinary()).decode("ascii") for mol in mols]
Path("molecules.rdmol.json").write_text(json.dumps(payload))

cached = json.loads(Path("molecules.rdmol.json").read_text())
mols = [Chem.Mol(base64.b64decode(item)) for item in cached]
```

Do not load Python pickle files from untrusted sources. Pickle deserialization can execute arbitrary code; prefer SMILES/SDF for interchange and RDKit binary payloads for trusted local caches.

**Use bulk operations:**

```python
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator

# Calculate fingerprints for all molecules at once
morgan_gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
fps = [morgan_gen.GetFingerprint(mol) for mol in mols]

# Use bulk similarity calculations
similarities = DataStructs.BulkTanimotoSimilarity(fps[0], fps[1:])
```

### Version-Sensitive Behavior

Pin RDKit versions when exact molecular identifiers or numeric features are part of a persisted dataset, model feature pipeline, or regulated report. Recent releases changed or documented behavior in several Python-facing areas:

- **Canonical SMILES and stereo:** 2026.03 changed canonical double-bond handling to avoid stereo corruption, so some stereo-containing SMILES may differ from older releases.
- **Descriptors and hashes:** preserve exact feature names and representation rules with the installed version; a successful rerun does not prove cross-version feature equivalence.
- **Drawing:** legacy `rdkit.Chem.Draw` canvas modules and functions such as `MolToImageFile`, `MolToMPL`, and `MolToQPixmap` were removed; use `Draw.MolToFile`, `Draw.MolToImage`, or `rdMolDraw2D`.
- **MolStandardize:** use `rdkit.Chem.MolStandardize.rdMolStandardize`; the older Python MolStandardize implementation was removed.
- **Similarity maps:** `GetSimilarityMapFromWeights()`, `GetSimilarityMapForFingerprint()`, and `GetSimilarityMapForModel()` now require an `rdMolDraw2D` drawing object.

### Thread Safety

Use independent molecule/query objects per worker. Never share a supplier across
threads; recursive SMARTS, calculated properties, and concurrent MolToSmiles on
the same Mol have specific caveats. Most Python bindings do not gain parallelism
from Python threads; prefer APIs exposing `numThreads` or separate processes.
`MultithreadedSDMolSupplier` may reorder records: capture `GetLastRecordId()` at
each iteration, not a filtered-list index. See the RDKit Book thread-safety section.

### Memory Management

For large datasets:

```python
# Use ForwardSDMolSupplier to avoid loading entire file
with open('large.sdf', 'rb') as f:
    suppl = Chem.ForwardSDMolSupplier(f)
    for mol in suppl:
        # Process one molecule at a time
        pass

# Use MultithreadedSDMolSupplier for parallel processing
suppl = Chem.MultithreadedSDMolSupplier('large.sdf', numWriterThreads=4)
```

## Identity and deliberate standardization

This small example is executed by the regression suite:

```python
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize as standardize

def canonical(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or mol.GetNumAtoms() == 0:
        raise ValueError("Invalid or empty molecule")
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)

assert canonical('OCC') == canonical('CCO')
assert canonical('C[C@H](O)F') != canonical('C[C@@H](O)F')
assert canonical('CC(=O)O') != canonical('CC(=O)[O-]')
assert canonical('CC=O') != canonical('C=CO')

original = Chem.MolFromSmiles('CC(=O)[O-].[Na+]')
cleaned = standardize.Cleanup(original)
assert len(Chem.GetMolFrags(cleaned)) == 2  # Cleanup does NOT strip salts
parent = standardize.FragmentParent(cleaned)
neutral = standardize.Uncharger().uncharge(parent)
assert Chem.MolToSmiles(neutral) == 'CC(=O)O'
```

Fragment selection, neutralization, and tautomer canonicalization are separate
policy decisions; retain original IDs/structures and each transformation. They
can erase experimental distinctions such as salt form, isotope labeling or stereo.
`Reionize` is rule-based charge placement, not pKa/pH speciation. `Uncharger` cannot
neutralize every ion (e.g. quaternary ammonium). `TautomerEnumerator().Enumerate`
returns a result with `status`; ensure it is `TautomerEnumeratorStatus.Completed`
before treating enumeration as complete. Its canonical tautomer is a scoring-rule
representative, not a measured population maximum. Default tautomer transforms
may remove stereo at affected centers/bonds.

Record fingerprint family, radius (Morgan radius 2 is ECFP4-like), length,
chirality, atom/bond invariants, bit versus count representation, count-simulation
settings and RDKit version. Equal-length fingerprints from different pipelines
are not interchangeable. Save `generator.GetInfoString()` where available.
Specified stereo, unspecified stereo and a racemate are different data meanings;
`useChirality=True` cannot recover information absent from the source.

Even enabling chirality cannot make a folded fingerprint an identity key. In
2026.03.6, `C[C@H](F)Cl` and `C[C@@H](F)Cl` have identical 2048-bit atom-pair
fingerprints with `includeChirality=True`, despite different sparse count
fingerprints. Increasing length changes collisions, not the identity guarantee.

Plain isomeric SMILES also omits enhanced stereo-group relationships. Preserve
these with CXSMILES or an appropriate SDF representation. The bundled text
outputs include enhanced stereo groups, but omit other CX annotations and are
not a lossless archive of every input property. Fingerprint chirality flags do
not encode a complete sample-level interpretation of stereo groups.
