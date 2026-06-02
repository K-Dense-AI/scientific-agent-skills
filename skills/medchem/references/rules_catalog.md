# Medchem Rules and Filters Catalog

Catalog of medicinal chemistry rules, alert sets, and filters in **medchem 2.0.5**.

## Table of Contents

1. [Drug-Likeness Rules](#drug-likeness-rules)
2. [Lead-Likeness Rules](#lead-likeness-rules)
3. [Fragment Rules](#fragment-rules)
4. [CNS and Target-Class Rules](#cns-and-target-class-rules)
5. [Structural Alert Filters](#structural-alert-filters)
6. [Named Catalogs](#named-catalogs)
7. [Complexity Metrics](#complexity-metrics)
8. [Chemical Group Collections](#chemical-group-collections)
9. [Filter Selection Guidelines](#filter-selection-guidelines)

---

## Drug-Likeness Rules

### Rule of Five (Lipinski)

**Reference:** Lipinski et al., *Adv Drug Deliv Rev* (1997) 23:3–25

**Criteria:** MW ≤ 500, LogP ≤ 5, HBD ≤ 5, HBA ≤ 10

```python
mc.rules.basic_rules.rule_of_five(mol)
# or
mc.rules.RuleFilters(rule_list=["rule_of_five"])
```

### Rule of Five Beyond

**Reference:** Doak et al., (2015) — compounds beyond Ro5 for large binding sites

**Criteria:** MW ≤ 1000, LogP ∈ [-2, 10], HBD ≤ 6, HBA ≤ 15, TPSA ≤ 250, rotatable bonds ≤ 20

```python
mc.rules.basic_rules.rule_of_five_beyond(mol)
```

### Rule of Veber

**Reference:** Veber et al., *J Med Chem* (2002) 45:2615–2623

**Criteria:** Rotatable bonds ≤ 10, TPSA ≤ 140 Ų

```python
mc.rules.basic_rules.rule_of_veber(mol)
```

### REOS (Rapid Elimination Of Swill)

**Reference:** Walters & Murcko, *Adv Drug Deliv Rev* (2002) 54:255–271

**Criteria:** MW 200–500, LogP −5 to 5, HBD 0–5, HBA 0–10

```python
mc.rules.basic_rules.rule_of_reos(mol)
```

### Egan, Ghose, Pfizer, GSK, Xu

Additional literature filters available as `rule_of_egan`, `rule_of_ghose`, `rule_of_pfizer_3_75`, `rule_of_gsk_4_400`, `rule_of_xu`.

### Rule of Druglike (Soft)

Combined soft drug-likeness criteria:

```python
mc.rules.basic_rules.rule_of_druglike_soft(mol)
```

---

## Lead-Likeness Rules

### Rule of Oprea

**Reference:** Oprea et al., *J Chem Inf Comput Sci* (2001) 41:1308–1315

**Criteria:** MW 200–350, LogP −2 to 4, rotatable bonds ≤ 7, rings ≤ 4

```python
mc.rules.basic_rules.rule_of_oprea(mol)
```

### Rule of Leadlike (Soft)

**Criteria:** MW 250–450, LogP −3 to 4, rotatable bonds ≤ 10

```python
mc.rules.basic_rules.rule_of_leadlike_soft(mol)
```

---

## Fragment Rules

### Rule of Three

**Reference:** Congreve et al., *Drug Discov Today* (2003) 8:876–877

**Criteria:** MW ≤ 300, LogP ≤ 3, HBD ≤ 3, HBA ≤ 3, rotatable bonds ≤ 3, PSA ≤ 60 Ų

```python
mc.rules.basic_rules.rule_of_three(mol)
```

Also available: `rule_of_three_extended`, `rule_of_two`, `rule_of_four`.

---

## CNS and Target-Class Rules

### Rule of CNS

**Criteria:** MW ≤ 450, LogP −1 to 5, HBD ≤ 2, TPSA ≤ 90 Ų

```python
mc.rules.basic_rules.rule_of_cns(mol)
```

### Rule of Respiratory

Target-class filter for respiratory drugs:

```python
mc.rules.basic_rules.rule_of_respiratory(mol)
```

### Generative Design Rules

For ML-generated molecules:

```python
mc.rules.basic_rules.rule_of_generative_design(mol)
mc.rules.basic_rules.rule_of_generative_design_strict(mol)
```

---

## Structural Alert Filters

### PAINS (Pan Assay INterference compoundS)

**Reference:** Baell & Holloway, *J Med Chem* (2010) 53:2719–2740

Apply via named catalog — not a `basic_rules` function:

```python
mc.functional.alert_filter(mols, alerts=["pains"], n_jobs=-1)
# or query: NOT HASALERT("pains")
```

Sub-catalogs: `pains_a`, `pains_b`, `pains_c`.

### Common Alerts Filters

ChEMBL-curated rule sets (Glaxo, Dundee, BMS, MLSMR, etc.):

```python
alert_filter = mc.structural.CommonAlertsFilters()
df = alert_filter(mols=mol_list, n_jobs=-1)
# status: exclude | flag | annotations | ok
```

### NIBR Filters

Novartis screening-deck curation ([Schuffenhauer et al., 2020](https://dx.doi.org/10.1021/acs.jmedchem.0c01332)):

```python
nibr_filter = mc.structural.NIBRFilters()
df = nibr_filter(mols=mol_list, n_jobs=-1)
# severity >= 10 → excluded by default
```

Or via functional API with `max_severity=10`.

### Lilly Demerits (optional)

Requires `mamba install lilly-medchem-rules`. 275 structural patterns; default exclusion at >160 demerits:

```python
mc.functional.lilly_demerit_filter(mols, max_demerits=160, n_jobs=-1)
```

---

## Named Catalogs

Available via `mc.catalogs.list_named_catalogs()` and `NamedCatalogs` static methods:

| Catalog | Purpose |
|---------|---------|
| `pains`, `pains_a/b/c` | PAINS substructure filters |
| `brenk` | Unwanted functional groups |
| `nih` | NIH screening filters |
| `zinc` | ZINC structural filters |
| `glaxo`, `dundee`, `bms` | Pharma-derived alert sets |
| `mlsmr`, `inpharmatica`, `lint` | Additional screening sets |
| `nibr` | NIBR catalog (substructure) |
| `bredt` | Bredt rule violations (unstable structures) |
| `tox`, `toxicophore`, `carcinogen` | Toxicity patterns |
| `reactive_unstable_toxic` | Reactive/unstable groups |
| `unstable_graph` | Unstable molecular graphs |

```python
cat = mc.catalogs.NamedCatalogs.brenk()
passes = mc.functional.catalog_filter(mols, catalogs=[cat], n_jobs=-1)
```

---

## Complexity Metrics

Compared to ZINC-15 percentile thresholds via `ComplexityFilter` or `complexity_filter()`:

| Metric | Description |
|--------|-------------|
| `bertz` | Bertz molecular complexity |
| `sas` | Synthetic accessibility score |
| `qed` | Quantitative Estimate of Drug-likeness |
| `clogp` | Calculated LogP |
| `whitlock` | Whitlock CT (rings, unsaturation, heteroatoms, chirality) |
| `barone` | Barone complexity |
| `smcm` | Synthetic complexity metric |
| `twc` | Total walk count |

```python
mc.functional.complexity_filter(mols, complexity_metric="bertz", limit="99", n_jobs=-1)
```

`limit="99"` keeps compounds below the 99th percentile on ZINC-15.

---

## Chemical Group Collections

Browse with `mc.groups.list_default_chemical_groups()`:

| Group | Application |
|-------|-------------|
| `privileged_scaffolds` | Common drug scaffolds |
| `common_warhead_covalent_inhibitors` | Covalent warhead patterns |
| `electrophilic_warheads_for_kinases` | Kinase covalent motifs |
| `rings_in_drugs` | Ring systems in approved drugs |
| `phase_2_hetereocyclic_rings` | Phase 2 heterocycles |
| `common_monomer_repeating_units` | Polymer/repeating units |
| `emerging_perfluoroalkyls` | PFAS-related patterns |

```python
group = mc.groups.ChemicalGroup(groups=["privileged_scaffolds"])
group.has_match(mol)
```

Custom groups: provide a CSV via `groups_db` with columns `smiles`/`smarts`, `name`, `group`.

---

## Filter Selection Guidelines

### Initial Screening (HTS deck)

```python
qf = mc.query.QueryFilter('MATCHRULE("rule_of_five") AND NOT HASALERT("pains")')
mask = qf(mols=mol_list, n_jobs=-1)
```

### Hit-to-Lead

```python
rules = mc.rules.RuleFilters(rule_list=["rule_of_oprea"])(mols, n_jobs=-1)
nibr = mc.structural.NIBRFilters()(mols, n_jobs=-1)
```

### Lead Optimization

```python
rules = mc.rules.RuleFilters(rule_list=["rule_of_druglike_soft"])(mols, n_jobs=-1)
alerts = mc.structural.CommonAlertsFilters()(mols, n_jobs=-1)
complexity = mc.functional.complexity_filter(mols, complexity_metric="bertz", limit="95", n_jobs=-1)
```

### CNS Targets

```python
qf = mc.query.QueryFilter('MATCHRULE("rule_of_cns") AND HASPROP("tpsa", <=, 90)')
mask = qf(mols, n_jobs=-1)
```

### Fragment-Based Discovery

```python
rules = mc.rules.RuleFilters(rule_list=["rule_of_three"])(mols, n_jobs=-1)
complexity = mc.functional.complexity_filter(mols, complexity_metric="bertz", limit="90", n_jobs=-1)
```

---

## Important Considerations

**Filters are guidelines, not absolutes:**
- ~10% of marketed oral drugs violate Ro5
- Natural products and prodrugs often fail standard rules
- Passing filters does not guarantee clinical success

**Combine with ML when appropriate:**

```python
rules_df = mc.rules.RuleFilters(rule_list=["rule_of_five"])(mols, n_jobs=-1)
filtered_mols = [m for m, ok in zip(mols, rules_df["pass_all"]) if ok]
# score filtered_mols with downstream ML model
```

---

## References

1. Lipinski CA et al. *Adv Drug Deliv Rev* (1997) 23:3–25
2. Veber DF et al. *J Med Chem* (2002) 45:2615–2623
3. Oprea TI et al. *J Chem Inf Comput Sci* (2001) 41:1308–1315
4. Congreve M et al. *Drug Discov Today* (2003) 8:876–877
5. Baell JB & Holloway GA. *J Med Chem* (2010) 53:2719–2740
6. Walters WP & Murcko MA. *Adv Drug Deliv Rev* (2002) 54:255–271
7. Schuffenhauer A et al. *J Med Chem* (2020) — NIBR screening deck
8. Doak BC et al. (2015) — Beyond Rule of Five
