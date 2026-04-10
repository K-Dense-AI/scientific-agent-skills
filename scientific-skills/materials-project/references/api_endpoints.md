# API Endpoints

This covers the `mp-api` v2 client in enough depth to do real work with it.
Most people only ever touch `mpr.materials.summary` — which is fine, it covers
90% of use cases — but the specialized endpoints are worth knowing about when
you need elasticity, phonons, or surface data.

---

## Setting up the client

```python
from mp_api.client import MPRester

# If MP_API_KEY is set in your environment, this just works
with MPRester() as mpr:
    ...

# Or pass the key directly — fine for scripts, bad for shared code
with MPRester("your_api_key_here") as mpr:
    ...
```

The `with` block isn't just convention — it closes the underlying HTTP session
cleanly when you're done. If you're doing a lot of work in a notebook, you can
keep the session open longer:

```python
mpr = MPRester()
# ... lots of queries ...
mpr.session.close()
```

But the context manager is cleaner and harder to forget.

---

## `mpr.materials.summary` — your first stop for everything

The summary endpoint aggregates the most-used properties from all other
endpoints into one place. If you're doing screening, this is usually all you need.

### Fields worth knowing

| Field | Type | Notes |
|---|---|---|
| `material_id` | str | The canonical MP identifier, e.g. `"mp-149"` |
| `formula_pretty` | str | Reduced formula like `"Fe2O3"` |
| `chemsys` | str | Hyphen-separated chemical system, e.g. `"Fe-O"` |
| `nelements` | int | Number of distinct elements |
| `nsites` | int | Number of sites in the primitive unit cell |
| `volume` | float | Unit cell volume in Å³ |
| `density` | float | Mass density in g/cm³ |
| `density_atomic` | float | Number density in atoms/Å³ |
| `crystal_system` | str | `"cubic"`, `"tetragonal"`, `"hexagonal"`, etc. |
| `spacegroup_number` | int | International Tables number (1–230) |
| `spacegroup_symbol` | str | Hermann–Mauguin symbol like `"Fm-3m"` |
| `band_gap` | float | DFT band gap in eV; 0.0 for metals |
| `is_gap_direct` | bool | Whether the gap is direct (same k-point for VBM and CBM) |
| `is_metal` | bool | True when band_gap == 0 |
| `formation_energy_per_atom` | float | DFT formation energy in eV/atom |
| `energy_above_hull` | float | Distance above convex hull in eV/atom; 0 = on hull |
| `is_stable` | bool | True when energy_above_hull == 0 |
| `ordering` | str | Magnetic ground state: `"FM"`, `"AFM"`, `"FiM"`, `"NM"` |
| `total_magnetization` | float | Total magnetic moment in μ_B per formula unit |
| `total_magnetization_normalized_vol` | float | Magnetization per Å³ |
| `num_magnetic_sites` | int | Count of sites with nonzero moment |
| `theoretical` | bool | True if the structure has no ICSD match (not experimentally observed) |
| `database_IDs` | dict | Cross-references to ICSD, COD, etc. |
| `deprecated` | bool | Don't use deprecated entries — they've been superseded |

### Range queries

For any numeric field, pass a `(min, max)` tuple. Either side can be `None`
for an open bound:

```python
with MPRester() as mpr:
    results = mpr.materials.summary.search(
        band_gap=(1.0, 2.0),          # 1.0 ≤ band_gap ≤ 2.0 eV
        energy_above_hull=(0, 0.1),   # within 100 meV/atom of hull
        nsites=(None, 30),            # up to 30 atoms in the cell
        fields=["material_id", "formula_pretty", "band_gap",
                "energy_above_hull"]
    )
```

### `formula` vs `chemsys` — pick the right one

These behave differently and the distinction matters:

```python
# formula: exact reduced stoichiometry, all polymorphs
mpr.materials.summary.search(formula="LiFePO4")

# chemsys: ALL materials containing exactly these elements
# (and all sub-systems — so Li-Fe-P-O includes Li oxides, Fe phosphates, etc.)
mpr.materials.summary.search(chemsys="Li-Fe-P-O")

# wildcard: Li + any one other element + O
mpr.materials.summary.search(chemsys="Li-*-O")
```

If you want strictly ternaries from a chemsys search, filter with `nelements=3`.

### Check available fields at runtime

The API evolves. If you're not sure what's queryable:

```python
with MPRester() as mpr:
    print(mpr.materials.summary.available_fields)
```

---

## `mpr.materials.thermo` — thermodynamic entries for phase diagrams

This is what you use when you need `ComputedEntry` objects for phase diagram
construction rather than just summary numbers.

```python
with MPRester() as mpr:
    # Returns a list of ComputedEntry objects
    entries = mpr.get_entries_in_chemsys(["Li", "Fe", "O"])
```

The convenience method `get_entries_in_chemsys()` is the cleanest way to get
everything you need for a `PhaseDiagram`. The raw endpoint has more options:

```python
with MPRester() as mpr:
    docs = mpr.materials.thermo.search(
        material_ids=["mp-19770", "mp-804"],
        fields=["material_id", "thermo_type", "energy_per_atom",
                "formation_energy_per_atom", "energy_above_hull"]
    )
```

---

## `mpr.materials.electronic_structure` — DOS and band structures

For electronic structure you'll mostly use the convenience methods, which
return proper pymatgen objects:

```python
with MPRester() as mpr:
    dos = mpr.get_dos_by_material_id("mp-2715")    # returns CompleteDos
    bs  = mpr.get_bandstructure_by_material_id("mp-2715")  # BandStructureSymmLine
    bs_uniform = mpr.get_bandstructure_by_material_id(
        "mp-2715", line_mode=False     # uniform k-mesh, for DOS consistency checks
    )
```

Not all materials have electronic structure data computed — it's the more
expensive calculations. If the call returns `None`, the data doesn't exist for
that entry. Worth checking before your code assumes it got something back.

---

## `mpr.materials.elasticity` — mechanical properties

Coverage is partial (elasticity is expensive to compute) but the data quality
is good where it exists.

```python
with MPRester() as mpr:
    docs = mpr.materials.elasticity.search(
        material_ids=["mp-149"],
        fields=["material_id", "bulk_modulus", "shear_modulus",
                "universal_anisotropy", "homogeneous_poisson",
                "elastic_tensor"]
    )

if docs:
    e = docs[0]
    # bulk_modulus and shear_modulus have .voigt, .reuss, .vrh attributes
    print(f"K_VRH = {e.bulk_modulus.vrh:.1f} GPa")
    print(f"G_VRH = {e.shear_modulus.vrh:.1f} GPa")
    print(f"Poisson = {e.homogeneous_poisson:.3f}")
    print(f"Anisotropy index = {e.universal_anisotropy:.4f}")
```

The `elastic_tensor` field gives you the full 6×6 Voigt tensor in GPa if you
need to do your own analysis beyond the derived quantities.

---

## `mpr.materials.magnetism` — magnetic properties

```python
with MPRester() as mpr:
    docs = mpr.materials.magnetism.search(
        material_ids=["mp-19770"],
        fields=["material_id", "ordering", "total_magnetization",
                "magmoms", "exchange_symmetry"]
    )
```

`magmoms` gives you site-resolved magnetic moments. `exchange_symmetry` is
relevant for materials where the magnetic unit cell differs from the structural one.

---

## `mpr.materials.dielectric` — optical and dielectric response

```python
with MPRester() as mpr:
    docs = mpr.materials.dielectric.search(
        material_ids=["mp-2715"],
        fields=["material_id", "n", "e_total", "e_ionic", "e_electronic"]
    )
```

`n` is the refractive index. `e_total` is the static dielectric tensor;
`e_ionic` and `e_electronic` are the ionic and electronic contributions.
These are directional properties (tensors), so you'll usually want to average
the diagonal for an isotropic estimate.

---

## `mpr.materials.phonon` — lattice dynamics

Phonon calculations are among the most computationally expensive in the database
so coverage is limited, but it's growing.

```python
with MPRester() as mpr:
    docs = mpr.materials.phonon.search(
        material_ids=["mp-149"],
        fields=["material_id", "ph_dos", "ph_bs", "last_updated"]
    )
```

Returns pymatgen `PhononDos` and `PhononBandStructureSymmLine` objects. Useful
for checking dynamical stability (imaginary modes mean the structure is unstable)
and computing thermodynamic quantities like entropy and heat capacity.

---

## `mpr.materials.surface_properties` — surface energies

```python
with MPRester() as mpr:
    docs = mpr.materials.surface_properties.search(
        material_ids=["mp-149"],
        fields=["material_id", "weighted_surface_energy",
                "surfaces", "shape_factor"]
    )
```

`weighted_surface_energy` is in J/m² and represents the Wulff-weighted average
across all computed facets. `surfaces` is a list of documents, each with Miller
indices, surface energy, and work function for that specific termination.

---

## `mpr.materials.oxidation_states` — valence prediction

```python
with MPRester() as mpr:
    docs = mpr.materials.oxidation_states.search(
        formula="Fe2O3",
        fields=["material_id", "possible_species",
                "possible_valences", "method"]
    )
```

Useful when you need to decorate a structure with oxidation states for
bond valence analysis or preparing inputs for some DFT codes.

---

## Batch queries — the right way to do bulk lookups

If you have a list of MP IDs and need properties for all of them, do it in
one call:

```python
with MPRester() as mpr:
    docs = mpr.materials.summary.search(
        material_ids=["mp-149", "mp-804", "mp-22862", "mp-2715"],
        fields=["material_id", "formula_pretty", "band_gap",
                "formation_energy_per_atom"]
    )
```

This is dramatically faster than calling `get_structure_by_material_id()` in a
loop and won't hit rate limits on even moderately large lists (hundreds of IDs).

---

## Counting results before downloading

Sometimes you just want to know how many entries match before committing to
pulling all the data:

```python
with MPRester() as mpr:
    count = mpr.materials.summary.count(formula="TiO2")
    print(f"TiO2 polymorphs in the database: {count}")
```

Also handy for checking whether a query is narrowed down enough before
running it for real.