# Mol* Story mechanism showcases

These examples were generated with the `molstar-story` skill in this pull
request. Each GIF cycles through settled, browser-accepted Story scenes; it is
a compact review preview, **not** an interpolation of atomic coordinates or a
molecular trajectory.

## Rhodopsin: retinal pocket to transducin-tail accommodation

![Rhodopsin mechanism Story](assets/molstar-story-showcases/rhodopsin-mechanism.gif)

- **Evidence:** dark retinal-bound [7ZBC](https://www.rcsb.org/structure/7ZBC),
  ligand-free active [3CAP](https://www.rcsb.org/structure/3CAP), and the
  GαCT-bound active complex [3DQB](https://www.rcsb.org/structure/3DQB).
- **Computed result:** after a 129-Cα receptor-core fit, E247 and T251 differ by
  9.534 and 7.335 Å. The observed GαCT pose has no heavy-atom pair below 2.0 Å
  in 3DQB, whereas substituting the aligned dark receptor produces 99 such
  pairs across eight receptor residues.
- **Bounded conclusion:** the active-like intracellular cavity geometrically
  accommodates the observed GαCT pose; the unchanged dark endpoint does not.
  The structures do not prove that retinal alone causes the path or that the
  measured displacement is sufficient for full G-protein activation.

## Adenylate kinase: AP5A and LID/NMP closure

![Adenylate kinase closure Story](assets/molstar-story-showcases/adenylate-kinase-closure.gif)

- **Evidence:** unligated open [4AKE](https://www.rcsb.org/structure/4AKE) and
  AP5A-bound closed [1AKE](https://www.rcsb.org/structure/1AKE), the same
  unmutated 214-residue *E. coli* adenylate kinase sequence.
- **Computed result:** a 133-Cα core fit gives 1.551 Å RMSD. LID mean
  displacement is 13.623 Å (T149: 23.955 Å); NMP mean displacement is 9.505 Å
  (A55: 18.464 Å). Fixing the observed AP5 pose against the open endpoint
  produces 16 heavy-atom overlaps below 2.0 Å, versus none in the closed
  endpoint under the same altloc rule.
- **Bounded conclusion:** the closed endpoint accommodates the observed AP5
  pose, while the unchanged open endpoint cannot retain it. The pair does not
  establish a physical closure pathway, catalytic rate, or free-energy gain.

## Hemoglobin: oxygen-site geometry to the T/R switch

![Hemoglobin allostery Story](assets/molstar-story-showcases/hemoglobin-allostery.gif)

- **Evidence:** human HbA deoxy-T [2HHB](https://www.rcsb.org/structure/2HHB)
  and the biological oxy-R tetramer from
  [1HHO](https://www.rcsb.org/structure/1HHO).
- **Computed result:** fitting the α1β1 dimer over 287 Cα atoms gives 0.936 Å
  RMSD; the partner α2β2 dimer differs by a 13.005° relative rotation. The
  α-heme Fe-to-porphyrin-N-plane distance changes from 0.448 Å (deoxy) to
  0.121 Å (oxy), and β2 His97 changes its α1 switch-neighborhood geometry.
- **Bounded conclusion:** local heme, quaternary, and α1β2-switch differences
  form a traceable T/R endpoint evidence chain. Two structures cannot derive a
  Hill coefficient, T/R populations, cooperative free energy, or causal order.

## Acceptance

All 17 scenes across the three Stories passed offline `file://` checks with
WebGL2, live camera convergence, stable post-representation canvas digests,
rotate/zoom/pick interaction, and no console, page, failed-request, or external
network errors. Decision-bearing scenes were also inspected manually. The
Stories use pruned presentation coordinates, opaque decision-relevant views,
and the lightweight illustrative rendering defaults described by the skill.
