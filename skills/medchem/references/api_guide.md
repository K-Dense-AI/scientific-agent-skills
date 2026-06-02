# Medchem API Reference

Reference for **medchem 2.0.5**. Official docs: https://medchem-docs.datamol.io/stable/api/

## Module: medchem.rules

### Class: RuleFilters

Filter molecules by multiple medicinal chemistry rules. Returns a **pandas DataFrame**.

**Constructor:**

```python
RuleFilters(rule_list: List[Union[str, Callable]], rule_list_names: Optional[List[str]] = None)
```

**Call signature:**

```python
__call__(
    mols: Sequence[Union[str, Mol]],
    n_jobs: int = -1,
    progress: bool = False,
    progress_leave: bool = False,
    scheduler: str = "auto",
    keep_props: bool = False,
    fail_if_invalid: bool = True,
) -> pd.DataFrame
```

**Return columns:** `mol`, `pass_all`, `pass_any`, plus one boolean column per rule. With `keep_props=True`, descriptor columns (`mw`, `clogp`, `tpsa`, etc.) are included.

**Class methods:**

```python
RuleFilters.list_available_rules_names()  # list of 22 rule names
RuleFilters.list_available_rules()        # rules with property metadata
```

**Example:**

```python
rfilter = mc.rules.RuleFilters(rule_list=["rule_of_five", "rule_of_cns"])
df = rfilter(mols=mol_list, n_jobs=-1, progress=True)
passing = df[df["pass_all"]]
```

### Module: medchem.rules.basic_rules

Individual rule functions for single molecules. Each returns `bool` (True = passes).

| Function | Description |
|----------|-------------|
| `rule_of_five(mol)` | Lipinski Rule of Five |
| `rule_of_five_beyond(mol)` | Beyond Ro5 (large binding sites) |
| `rule_of_four(mol)` | Rule of Four |
| `rule_of_three(mol)` | Fragment library Rule of Three |
| `rule_of_three_extended(mol)` | Extended Ro3 |
| `rule_of_two(mol)` | Rule of Two |
| `rule_of_ghose(mol)` | Ghose filter |
| `rule_of_veber(mol)` | Veber oral bioavailability |
| `rule_of_reos(mol)` | REOS filter |
| `rule_of_chemaxon_druglikeness(mol)` | ChemAxon drug-likeness |
| `rule_of_egan(mol)` | Egan permeability |
| `rule_of_pfizer_3_75(mol)` | Pfizer 3/75 filter |
| `rule_of_gsk_4_400(mol)` | GSK 4/400 filter |
| `rule_of_oprea(mol)` | Oprea lead-like |
| `rule_of_xu(mol)` | Xu filter |
| `rule_of_cns(mol)` | CNS drug-likeness |
| `rule_of_respiratory(mol)` | Respiratory drug-likeness |
| `rule_of_zinc(mol)` | ZINC-like |
| `rule_of_leadlike_soft(mol)` | Soft lead-like |
| `rule_of_druglike_soft(mol)` | Soft drug-like |
| `rule_of_generative_design(mol)` | Generative design space |
| `rule_of_generative_design_strict(mol)` | Strict generative design |

### Descriptor helpers

```python
mc.rules.list_descriptors()  # property names for query language
```

---

## Module: medchem.structural

### Class: CommonAlertsFilters

ChEMBL-derived structural alert filter sets (Glaxo, Dundee, BMS, etc.).

```python
CommonAlertsFilters()
```

**Returns DataFrame columns:** `mol`, `pass_filter`, `status`, `reasons`

- `status`: one of `"exclude"`, `"flag"`, `"annotations"`, `"ok"`
- `pass_filter`: bool — True if compound passes

**Methods:**

```python
list_default_available_alerts()  # DataFrame of alert definitions
__call__(mols, n_jobs=-1, progress=False, ...) -> pd.DataFrame
```

### Class: NIBRFilters

Novartis screening-deck curation filters ([Schuffenhauer et al., J. Med. Chem. 2020](https://dx.doi.org/10.1021/acs.jmedchem.0c01332)).

```python
NIBRFilters()
```

**Returns DataFrame columns:** `mol`, `pass_filter`, `status`, `severity`, `reasons`, `n_covalent_motif`, `special_mol`

- `severity`: 0 = clean; 1–9 = flags; ≥10 = excluded by default

### Lilly demerits (optional)

Requires `mamba install lilly-medchem-rules`. Access via:

```python
mc.functional.lilly_demerit_filter(mols, max_demerits=160, n_jobs=-1)
# or
from medchem.structural.lilly_demerits import LillyDemeritsFilters
```

---

## Module: medchem.functional

High-level boolean-mask API. **True = passes** (no alert / passes all rules).

| Function | Description |
|----------|-------------|
| `rules_filter(mols, rules, n_jobs=None, ...)` | Apply rule list |
| `nibr_filter(mols, max_severity=10, n_jobs=None, ...)` | NIBR filter |
| `alert_filter(mols, alerts, alerts_db=None, n_jobs=1, ...)` | Named alert catalogs |
| `catalog_filter(mols, catalogs, n_jobs=-1, ...)` | RDKit FilterCatalog list |
| `complexity_filter(mols, complexity_metric="bertz", limit="99", ...)` | Complexity threshold |
| `lilly_demerit_filter(mols, max_demerits=160, ...)` | Lilly demerits (optional) |
| `chemical_group_filter(mols, chemical_group, ...)` | Exclude group matches |
| `catalog_filter(mols, catalogs, ...)` | Custom catalog list |
| `bredt_filter(mols, ...)` | Bredt instability filter |
| `macrocycle_filter(mols, ...)` | Macrocycle filter |
| `protecting_groups_filter(mols, ...)` | Protecting group filter |
| `ring_infraction_filter(mols, ...)` | Ring infraction filter |
| `symmetry_filter(mols, ...)` | Symmetry filter |

---

## Module: medchem.catalogs

### NamedCatalogs

Static methods returning RDKit `FilterCatalog` objects:

```python
mc.catalogs.list_named_catalogs()
# tox, pains, pains_a, pains_b, pains_c, nih, zinc, brenk, dundee, bms,
# glaxo, schembl, mlsmr, inpharmatica, lint, nibr, bredt, toxicophore, ...

mc.catalogs.NamedCatalogs.pains()
mc.catalogs.NamedCatalogs.brenk()
mc.catalogs.NamedCatalogs.nibr()
mc.catalogs.NamedCatalogs.bredt()
```

**Helpers:**

```python
catalog_from_smarts(smarts_list)
merge_catalogs(catalogs)
list_named_catalogs()
```

---

## Module: medchem.groups

### ChemicalGroup

Detect functional groups from the global-chem curated library.

```python
ChemicalGroup(groups=None, n_jobs=None, groups_db=None)
```

**Methods:**

```python
has_match(mol, exact_match=False, terminal_only=False) -> bool
get_matches(mol, use_smiles=True, exact_match=False, terminal_only=False) -> dict
filter(mols) -> list[Mol]
get_catalog() -> FilterCatalog
list_groups() -> list
list_hierarchy_groups() -> list
```

**Listing helpers:**

```python
mc.groups.list_default_chemical_groups(hierarchy=False)
mc.groups.list_functional_group_names(unique=True)
mc.groups.get_functional_group_map()  # name → SMARTS
```

---

## Module: medchem.complexity

### Class: ComplexityFilter

Compare a metric to ZINC-15 percentile thresholds. Operates on **single molecules**.

```python
ComplexityFilter(
    limit="99",
    complexity_metric="bertz",
    threshold_stats_file="zinc_15_available",
)
cf(mol)  # -> bool
```

**Available metrics** (`ComplexityFilter.list_default_available_filters()`):
`bertz`, `sas`, `qed`, `clogp`, `whitlock`, `barone`, `smcm`, `twc`

**Direct metric functions:**

```python
mc.complexity.WhitlockCT(mol)
mc.complexity.BaroneCT(mol)
mc.complexity.SMCM(mol)
mc.complexity.TWC(mol)
```

For batch filtering, use `mc.functional.complexity_filter()`.

---

## Module: medchem.constraints

### Class: Constraints

Scaffold-based substructure matching with per-atom constraint functions — **not** simple property-range filters.

```python
Constraints(core: Mol, constraint_fns: Dict[str, Callable], prop_name: str = "query")
constraints(mol)  # -> bool or match details
```

Use `RuleFilters` or the query language for MW/LogP/TPSA bounds.

---

## Module: medchem.query

### Class: QueryFilter

Parse and evaluate the medchem query language.

```python
QueryFilter(query: str, grammar: Optional[str] = None, parser: str = "lalr")
qf(mols, n_jobs=-1, progress=True, scheduler="processes") -> list[bool]
```

**Grammar constructs:**

| Construct | Example |
|-----------|---------|
| Rule match | `MATCHRULE("rule_of_five")` |
| Alert catalog | `HASALERT("pains")` |
| Property compare | `HASPROP("mw", <, 500)` |
| Chemical group | `HASGROUP("privileged_scaffolds")` |
| Substructure | `HASSUBSTRUCTURE("c1ccccc1")` |
| Superstructure | `HASSUPERSTRUCTURE("CCO")` |
| Boolean | `true`, `false` |
| Logic | `AND`, `OR`, `NOT` |

**Example queries:**

```python
'MATCHRULE("rule_of_five") AND NOT HASALERT("pains")'
'MATCHRULE("rule_of_cns") AND HASPROP("tpsa", <=, 90)'
'NOT HASALERT("brenk") AND HASPROP("mw", >=, 200)'
```

### Class: QueryOperator

Holds available properties, catalogs, rules, and functional groups used by the parser.

---

## Common Patterns

### Parallel processing

```python
df = mc.rules.RuleFilters(rule_list=["rule_of_five"])(mols=mol_list, n_jobs=-1, progress=True)
mask = mc.functional.nibr_filter(mols=mol_list, n_jobs=-1)
```

### Combining filters

```python
rules_df = mc.rules.RuleFilters(rule_list=["rule_of_five"])(mols=mol_list, n_jobs=-1)
alerts_df = mc.structural.CommonAlertsFilters()(mols=mol_list, n_jobs=-1)

passing = [
    mol for i, mol in enumerate(mol_list)
    if rules_df.iloc[i]["pass_all"] and alerts_df.iloc[i]["pass_filter"]
]
```

### Working with DataFrames

```python
import pandas as pd
import datamol as dm
import medchem as mc

df = pd.read_csv("molecules.csv")
df["mol"] = df["smiles"].apply(dm.to_mol)

results = mc.rules.RuleFilters(rule_list=["rule_of_five", "rule_of_cns"])(
    mols=df["mol"].tolist(), n_jobs=-1
)
df = pd.concat([df, results.drop(columns=["mol"])], axis=1)
filtered = df[df["pass_all"]]
```
