# Workflows

Complete worked examples for common materials research tasks. Each one is
self-contained and meant to be a starting point you can adapt rather than
copy-paste verbatim.

---

## Battery cathode screening

The goal here is to find thermodynamically stable Li-transition-metal oxides
that might work as cathode materials. We screen a few TM chemistries at once and
rank by stability and band gap (you want the cathode to be semiconducting, not
metallic, so Li ions can intercalate without short-circuiting).

```python
import pandas as pd
import matplotlib.pyplot as plt
from mp_api.client import MPRester

transition_metals = ["Mn", "Co", "Ni", "Fe"]
all_candidates = []

with MPRester() as mpr:
    for tm in transition_metals:
        results = mpr.materials.summary.search(
            chemsys=f"Li-{tm}-O",
            energy_above_hull=(0, 0.05),   # stable + near-stable
            fields=["material_id", "formula_pretty", "band_gap",
                    "formation_energy_per_atom", "energy_above_hull",
                    "nsites", "volume", "density"]
        )
        for r in results:
            all_candidates.append({
                "mp_id":     r.material_id,
                "formula":   r.formula_pretty,
                "tm":        tm,
                "Eg_eV":     r.band_gap,
                "Ef_eV_at":  r.formation_energy_per_atom,
                "Ehull_eV_at": r.energy_above_hull,
                "nsites":    r.nsites,
                "density":   r.density,
            })

df = pd.DataFrame(all_candidates)

# exclude metals — a metallic cathode short-circuits the cell
df = df[df["Eg_eV"] > 0.1]
df = df.sort_values("Ehull_eV_at")

print(f"Candidates after filtering: {len(df)}")
print(df.head(20).to_string(index=False))

# quick scatter to see the landscape
fig, ax = plt.subplots(figsize=(8, 5))
for tm, group in df.groupby("tm"):
    ax.scatter(group["Eg_eV"], group["Ef_eV_at"], label=tm, alpha=0.7, s=40)
ax.set_xlabel("Band gap (eV)")
ax.set_ylabel("Formation energy (eV/atom)")
ax.legend(title="TM")
ax.set_title("Li-TM-O cathode candidates")
plt.tight_layout()
plt.savefig("cathode_screening.png", dpi=300)
```

---

## Solar absorber search

Direct-gap semiconductors in the 1.0–1.8 eV range are optimal for single-junction
solar cells by the Shockley–Queisser limit. Si sits at 1.1 eV (indirect, so less
than ideal), GaAs at 1.4 eV (direct, near-perfect). The question is what else is
out there.

```python
import pandas as pd
from mp_api.client import MPRester

with MPRester() as mpr:
    results = mpr.materials.summary.search(
        band_gap=(1.0, 1.8),
        is_stable=True,
        is_metal=False,
        is_gap_direct=True,          # thin-film absorbers need direct gaps
        nelements=(2, 4),            # keep it synthesizable
        fields=["material_id", "formula_pretty", "band_gap",
                "formation_energy_per_atom", "nelements",
                "nsites", "theoretical", "crystal_system", "density"]
    )

df = pd.DataFrame([{
    "mp_id":       r.material_id,
    "formula":     r.formula_pretty,
    "Eg_eV":       round(r.band_gap, 3),
    "Ef_eV_at":    round(r.formation_energy_per_atom, 3),
    "n_elem":      r.nelements,
    "n_sites":     r.nsites,
    "theory_only": r.theoretical,
    "crystal":     r.crystal_system,
    "density":     round(r.density, 2),
} for r in results])

# prioritize compounds that have actually been made
exp_only = df[~df["theory_only"]].sort_values("Eg_eV")
print(f"Experimentally known candidates: {len(exp_only)}")
print(exp_only.to_string(index=False))

df.to_csv("solar_absorber_candidates.csv", index=False)
```

GaAs (mp-2715) and CdTe (mp-406) should both show up here, which is a reasonable
sanity check that the query is working.

---

## Phase diagram and stability assessment

This is the standard way to figure out whether a composition is thermodynamically
stable and what it would decompose into if it's not.

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter

# download everything in the Li-Mn-O system
with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys(["Li", "Mn", "O"])

print(f"Loaded {len(entries)} entries")

pd_obj = PhaseDiagram(entries)

# check a specific entry
with MPRester() as mpr:
    target = mpr.get_entry_by_material_id("mp-757979")   # LiMnO2

e_hull = pd_obj.get_e_above_hull(target)
decomp  = pd_obj.get_decomposition(target.composition)

print(f"\nLiMnO2 — energy above hull: {e_hull:.4f} eV/atom")

if e_hull < 0.025:
    print("Within 25 meV/atom — likely synthesizable")
elif e_hull < 0.1:
    print("Metastable range — might be accessible with the right synthesis")
else:
    print("Probably unstable. Predicted to decompose into:")
    for entry, frac in decomp.items():
        print(f"  {entry.composition.reduced_formula}: {frac:.3f}")

# save a plot
plotter = PDPlotter(pd_obj)
plotter.get_plot(show_unstable=0.05).savefig("LiMnO_phase_diagram.png", dpi=300)
```

---

## Electronic structure analysis for a set of materials

When you need band gaps, VBM/CBM positions, and DOS plots for a batch of materials,
here's a pattern that collects the numbers into a summary DataFrame while also
saving the individual figures:

```python
import pandas as pd
import matplotlib.pyplot as plt
from mp_api.client import MPRester
from pymatgen.electronic_structure.plotter import DosPlotter, BSPlotter

mp_ids = ["mp-149", "mp-2715", "mp-22862", "mp-804"]
labels = ["Si", "GaAs", "TiO2-rutile", "LiFePO4"]

records = []

with MPRester() as mpr:
    for mp_id, label in zip(mp_ids, labels):
        bs  = mpr.get_bandstructure_by_material_id(mp_id)
        dos = mpr.get_dos_by_material_id(mp_id)

        # can be None if the calculation doesn't exist for that entry
        if bs is None or dos is None:
            print(f"Skipping {label} — electronic structure not available")
            continue

        bg  = bs.get_band_gap()
        vbm = bs.get_vbm()
        cbm = bs.get_cbm()

        records.append({
            "material":  label,
            "mp_id":     mp_id,
            "Eg_eV":     round(bg["energy"], 3),
            "direct":    bg["direct"],
            "transition": bg["transition"],
            "VBM_eV":    round(vbm["energy"], 3),
            "CBM_eV":    round(cbm["energy"], 3),
        })

        # DOS figure
        dp = DosPlotter()
        dp.add_dos("Total", dos)
        dp.add_dos_dict(dos.get_element_dos())
        dp.get_plot(xlim=(-6, 6)).savefig(f"dos_{label}.png", dpi=150)
        plt.close()

        # band structure figure
        bp = BSPlotter(bs)
        bp.get_plot(zero_to_efermi=True, vbm_cbm_marker=True).savefig(
            f"bs_{label}.png", dpi=150)
        plt.close()

df = pd.DataFrame(records)
print(df.to_string(index=False))
df.to_csv("electronic_structure_summary.csv", index=False)
```

---

## Thermoelectric material screening

Good thermoelectrics need a narrow band gap (for sufficient carrier concentration),
a complex crystal structure (for low lattice thermal conductivity), and decent
thermodynamic stability. This query gets you a starting pool to work from:

```python
import pandas as pd
from mp_api.client import MPRester

with MPRester() as mpr:
    results = mpr.materials.summary.search(
        band_gap=(0.05, 1.5),
        energy_above_hull=(0, 0.05),
        is_metal=False,
        nsites=(4, 50),        # complex unit cells tend to scatter phonons more
        nelements=(2, 5),
        fields=["material_id", "formula_pretty", "band_gap",
                "formation_energy_per_atom", "energy_above_hull",
                "nsites", "nelements", "density", "crystal_system",
                "spacegroup_number"]
    )

df = pd.DataFrame([{
    "mp_id":      r.material_id,
    "formula":    r.formula_pretty,
    "Eg_eV":      round(r.band_gap, 3),
    "Ef_eV_at":   round(r.formation_energy_per_atom, 3),
    "Ehull_eV_at": round(r.energy_above_hull, 4),
    "n_sites":    r.nsites,
    "n_elem":     r.nelements,
    "density":    round(r.density, 2),
    "crystal":    r.crystal_system,
    "spg":        r.spacegroup_number,
} for r in results])

# sort by unit cell complexity as a rough proxy for low κ_lattice
df = df.sort_values("n_sites", ascending=False)
print(f"Candidates: {len(df)}")
print(df.head(25).to_string(index=False))
df.to_csv("thermoelectric_candidates.csv", index=False)
```

Known good thermoelectrics like Bi₂Te₃ and PbTe should appear. If they don't,
your `band_gap` or `nsites` range might be cutting them out.

---

## Supercell and defect preparation

A common pre-step before defect calculations or MD simulations:

```python
from mp_api.client import MPRester
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

with MPRester() as mpr:
    structure = mpr.get_structure_by_material_id("mp-149")   # Si

# always use the conventional cell for supercell expansions
# the primitive cell produces lopsided supercells
sga = SpacegroupAnalyzer(structure)
conv = sga.get_conventional_standard_structure()
print(f"Conventional: {conv.formula}, {len(conv)} sites")

# 2×2×2 supercell — 64 atoms for Si
supercell = conv.copy()
supercell.make_supercell([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
print(f"Supercell: {supercell.formula}, {len(supercell)} sites")

# vacancy at site 0
vacancy = supercell.copy()
vacancy.remove_sites([0])
vacancy.to(filename="POSCAR_Si_vacancy")

# substitutional defect: replace site 0 with Ge
sub = supercell.copy()
sub[0] = "Ge"
print(f"Ge substitution: {sub.formula}")
sub.to(filename="POSCAR_Ge_sub")
```

One thing that catches people: `make_supercell()` modifies the structure in
place. The `copy()` calls above are important — without them you'd be building
on top of a structure you've already modified.

---

## Polymorph analysis

How many distinct crystal structures exist for a given composition, and which
are structurally equivalent (e.g. the same phase submitted to the database
twice)?

```python
from mp_api.client import MPRester
from pymatgen.analysis.structure_matcher import StructureMatcher

formula = "TiO2"

with MPRester() as mpr:
    results = mpr.materials.summary.search(
        formula=formula,
        fields=["material_id", "formula_pretty", "energy_above_hull",
                "spacegroup_symbol", "band_gap"]
    )
    structures = {
        r.material_id: mpr.get_structure_by_material_id(r.material_id)
        for r in results
    }

# print the landscape first
for r in sorted(results, key=lambda x: x.energy_above_hull):
    print(f"  {r.material_id:12s}  {r.spacegroup_symbol:10s}  "
          f"Ehull={r.energy_above_hull:.4f} eV/at  Eg={r.band_gap:.2f} eV")

# group into structurally equivalent sets
sm = StructureMatcher()
ids = list(structures.keys())
already_seen = set()
groups = []

for id1 in ids:
    if id1 in already_seen:
        continue
    group = [id1]
    for id2 in ids:
        if id2 != id1 and id2 not in already_seen:
            if sm.fit(structures[id1], structures[id2]):
                group.append(id2)
                already_seen.add(id2)
    already_seen.add(id1)
    groups.append(group)

print(f"\n{len(groups)} structurally distinct {formula} polymorphs:")
for i, g in enumerate(groups):
    print(f"  Group {i+1}: {', '.join(g)}")
```

Rutile, anatase, and brookite are the three well-known TiO2 polymorphs —
they should all show up as separate groups.

---

## Using MP data alongside local DFT calculations

This is what you do when you've run your own VASP calculation and want to
know where your material sits on the phase diagram:

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.core import Composition

# your local result — total DFT energy and composition
my_formula   = "Li2MnO3"
my_energy_per_atom = -6.312   # replace with your actual value (eV/atom)
my_comp      = Composition(my_formula)
my_entry     = ComputedEntry(
    composition=my_comp,
    energy=my_energy_per_atom * my_comp.num_atoms,
    entry_id="local-calc"
)

# download MP reference entries for the same chemical system
elements = [str(el) for el in my_comp.elements]
with MPRester() as mpr:
    mp_entries = mpr.get_entries_in_chemsys(elements)

# build the phase diagram including your entry
all_entries = mp_entries + [my_entry]
pd_obj      = PhaseDiagram(all_entries)

e_hull = pd_obj.get_e_above_hull(my_entry)
decomp = pd_obj.get_decomposition(my_entry.composition)

print(f"{my_formula}: {e_hull:.4f} eV/atom above hull")

if e_hull < 0.025:
    print("Likely stable — sits on or very near the convex hull")
else:
    print("Predicted to decompose into:")
    for entry, frac in decomp.items():
        print(f"  {entry.composition.reduced_formula}: {frac:.3f}")
```

One caveat worth knowing: mixing your own DFT energies with MP energies only
makes sense if you used compatible settings (same functional, pseudopotentials,
k-mesh density, etc.). MP uses PBE with specific VASP settings — if your
calculation used a different setup, the energy comparisons won't be meaningful.
The `MaterialsProjectCompatibility` energy correction scheme exists for
exactly this reason if you need to handle corrections properly.