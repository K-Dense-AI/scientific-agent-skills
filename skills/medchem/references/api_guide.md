# Medchem API Reference

Reference for **medchem 2.1.1**, checked 2026-10-01 against current documentation and installed release source. Requires Python 3.11+. Official API: https://medchem-docs.datamol.io/stable/api/medchem.rules.html

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
CommonAlertsFilters(alerts_set=["BMS", "Dundee", "Glaxo"], alerts_db_path=None)
```

The source defaults to **BMS only**, despite an older constructor docstring saying BMS+Dundee+Glaxo. Select sets explicitly.

**Returns DataFrame columns:** `mol`, `pass_filter`, `status`, `reasons`

- `status`: `"exclude"` or `"ok"` in the current common-alert implementation
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

- `severity`: sum of flag scores; any explicit exclusion alert yields 10.
- `status`: `"exclude"`, `"flag"`, `"annotations"`, or `"ok"`.
- Class `pass_filter` rejects explicit exclusions only. Combine it with `severity < 10` to also reject accumulated flags. For prevalidated molecules, `functional.nibr_filter(max_severity=10)` supplies the severity cutoff. The functional wrapper checks severity only and can admit invalid inputs (reported by the class with severity zero); never use it as a parse-validity check.

### Lilly demerits (optional)

Requires native tools installed with `medchem install-lilly` (C++/make/zlib/Ruby, source download and build; WSL on Windows). This native installation/execution was not exercised locally. Access via:

```python
mc.functional.lilly_demerit_filter(mols, max_demerits=160, n_jobs=-1)
# or
from medchem.structural.lilly_demerits import LillyDemeritsFilters
```

---

## Module: medchem.functional

High-level boolean-mask API. **True = passes** (no alert / passes all rules). `return_idx=True` returns indices instead of the default NumPy mask. `alert_filter` uses the names from `CommonAlertsFilters.list_default_available_alerts()`; it does not validate unknown names, which can silently create an empty alert set. For `brenk` and `pains_a`, use `catalog_filter`. Its string interface deliberately rejects `nibr` and `bredt`; use `nibr_filter` and `bredt_filter` respectively. Raw NIBR catalog matching ignores severity and includes annotations.

| Function | Description |
|----------|-------------|
| `rules_filter(mols, rules, n_jobs=None, ...)` | Apply rule list |
| `nibr_filter(mols, max_severity=10, n_jobs=None, ...)` | NIBR filter |
| `alert_filter(mols, alerts, alerts_db=None, n_jobs=1, ...)` | Common-alert collection names, case-insensitive |
| `catalog_filter(mols, catalogs, n_jobs=-1, ...)` | Named catalogs or RDKit FilterCatalog objects |
| `complexity_filter(mols, complexity_metric="bertz", limit="99", ...)` | Complexity threshold |
| `lilly_demerit_filter(mols, max_demerits=160, ...)` | Lilly demerits (optional) |
| `chemical_group_filter(mols, chemical_group, ...)` | Exclude group matches |
| `bredt_filter(mols, ...)` | Bredt instability filter |
| `macrocycle_filter(mols, ...)` | Macrocycle filter |
| `protecting_groups_filter(mols, ...)` | Protecting group filter |
| `ring_infraction_filter(mols, ...)` | Ring infraction filter |
| `symmetry_filter(mols, ...)` | Symmetry filter |

---

In 2.1.1, `bredt_filter` kekulizes supplied RDKit objects in place, changing later aromatic substructure/PAINS matches. Preserve the shared input molecules by copying them:

```python
from rdkit import Chem
passes_bredt = mc.functional.bredt_filter([Chem.Mol(mol) for mol in mol_list], n_jobs=1)
```

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
merge_catalogs(*catalogs)
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
get_matches(mol, use_smiles=True, exact_match=False, terminal_only=False) -> pd.DataFrame  # None for invalid input
filter(names, fuzzy=False) -> ChemicalGroup  # narrows pattern names in place
get_catalog(exact_match=True) -> FilterCatalog
list_groups() -> list
list_hierarchy_groups() -> list
```

Group collections contain substructure patterns, not whole-molecule classifications: `amino_acids` includes side-chain fragments that can match ethanol. Some collections contain unparseable SMILES patterns (observed for `electrophilic_warheads_for_kinases`); inspect `group.dataframe` and validate `mol`/`mol_smarts` before choosing a representation or curating a custom database.

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
`bertz`, `sas`, `qed`, `clogp`, `whitlock`, `barone`, `smcm`, `twc`, `spacialscore`.
The default ZINC-15 table supports the first eight; `spacialscore` requires a custom threshold CSV.
`limit` must be a provided table label: `median`, `90`, `99`, `999`, or `max` for ZINC-15; `999` is 99.9%. Thresholds depend on molecular-weight bins. The implementation uses `score < threshold` for every metric, including QED, and treats a NaN score as a pass. Validate finiteness separately when needed.

**Direct metric functions:**

```python
mc.complexity.WhitlockCT(mol)
mc.complexity.BaroneCT(mol)
mc.complexity.SMCM(mol)
mc.complexity.TWC(mol)
mc.complexity.SPS(mol)  # normalized SpacialScore
```

For batch filtering, use `mc.functional.complexity_filter()`.

---

## Module: medchem.constraints

### Class: Constraints

Scaffold-based substructure matching with per-atom constraint functions — **not** simple property-range filters.

```python
Constraints(core: Mol, constraint_fns: Dict[str, Callable], prop_name: str = "query")
constraints(mol)  # -> bool
constraints.get_matches(mol)  # tuple of matching atom-index tuples
```

A constraint is active only when a core atom has `prop_name` set to a key in `constraint_fns`. Each function receives **one extracted side-chain molecule** and returns a boolean. See the executable example in `SKILL.md`; a three-argument lambda on an unannotated core never applies the intended check. Use `RuleFilters` or the query language for MW/LogP/TPSA bounds.

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
| Functional-group name | `HASGROUP("Primary amines")` |
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

`HASGROUP` accepts exact map keys from `mc.groups.get_functional_group_map()`, not collection names from `list_default_chemical_groups()`. Some aliases from `list_functional_group_names()` (for example `primary_amine`) are missing from the map in 2.1.1 and raise `KeyError`; use a map key such as `Primary amines`. `HASSUPERSTRUCTURE("CCO")` tests whether the input molecule is contained in the query molecule. Invalid inputs should be separated before evaluating queries.

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
alerts_df = mc.structural.CommonAlertsFilters(alerts_set=["BMS", "Dundee", "Glaxo"])(mols=mol_list, n_jobs=-1)

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
df["mol"] = df["smiles"].apply(
    lambda value: dm.to_mol(value) if isinstance(value, str) and value.strip() else None
)
invalid = df[df["mol"].isna()].copy()
df = df[df["mol"].notna()].reset_index(drop=True)
# Keep invalid separately with original source IDs; these are parse failures.

results = mc.rules.RuleFilters(rule_list=["rule_of_five", "rule_of_cns"])(
    mols=df["mol"].tolist(), n_jobs=-1
)
df = pd.concat([df, results.drop(columns=["mol"])], axis=1)
filtered = df[df["pass_all"]]
```


Upstream NIBR 2.1.1 also converts the catalog special-molecule flag with `bool(text)`; a nonempty `"0"` therefore becomes true. Treat `special_mol` as unreliable metadata until the raw catalog entry is checked, rather than evidence of a peptide or glycoside.

## Upstream verification sources

- [Release 2.1.1](https://github.com/datamol-io/medchem/releases/tag/2.1.1) and [2.1 migration](https://medchem-docs.datamol.io/stable/migration.html)
- [Structural APIs](https://medchem-docs.datamol.io/stable/api/medchem.structural.html), [functional APIs](https://medchem-docs.datamol.io/stable/api/medchem.functional.html), [catalog APIs](https://medchem-docs.datamol.io/stable/api/medchem.catalogs.html)
- [Groups](https://medchem-docs.datamol.io/stable/api/medchem.groups.html), [complexity](https://medchem-docs.datamol.io/stable/api/medchem.complexity.html), [constraints](https://medchem-docs.datamol.io/stable/api/medchem.constraints.html), [queries](https://medchem-docs.datamol.io/stable/api/medchem.query.html)
- [Versioned source](https://github.com/datamol-io/medchem/tree/2.1.1/medchem) resolves docstring discrepancies. No remote service endpoints, authentication, or pagination are used by these local APIs. Native Lilly filtering remains an unexecuted optional integration.
