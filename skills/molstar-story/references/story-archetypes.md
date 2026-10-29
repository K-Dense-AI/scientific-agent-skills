# Story Archetypes And Question Coverage

Use archetypes to decompose the scientific question before choosing structures or
writing scenes. An archetype is a question/evidence contract, not a visual
template. Most useful Stories combine several archetypes; do not create a new
asset directory merely because the protein family or biological example changes.

Choose a provisional composition from the user's question, let retrieval revise
it, and freeze the final composition together with the evidence plan. A template
is only a maintained implementation starting point for recurring scene logic.

## Core Archetypes

| Archetype | Question it must answer | Required evidence and upstream analysis | Claim spine | Stop or expose a gap when |
|---|---|---|---|---|
| `ligand-binding` | Where and in what experimentally supported pose does the ligand bind? | Exact receptor/assembly/ligand identity and chemistry; bound coordinates or density; contacts, complete-residue pocket, relevant distances and covalent links | ligand identity -> pose/occupancy -> local contacts -> bounded pocket interpretation | Ligand identity, pose, chain, covalency, or density support is unresolved; contacts alone are being used as affinity or energetic evidence |
| `state-comparison` | Which frozen states are comparable and what differs after a declared mapping/alignment? | State semantics, construct/partner census, residue correspondence, alignment selection/transform, RMSD and sensitivity | comparable endpoints -> common frame -> conserved versus different regions | Equivalent entities/residues or defensible state labels cannot be established |
| `conformational-change` | Where is the endpoint difference, how large is it, and which functional geometry does it alter? | One or more comparable states; per-residue/domain displacement, angles, axes, pore radius or cavity geometry as appropriate | localized displacement -> changed functional geometry -> claim boundary | Only a visual overlay exists, or endpoint vectors are being described as a physical path, dynamics, or population shift |
| `interface` | Which assemblies and surfaces contact, and how are the partners geometrically accommodated? | Biological assembly and partner identity; interface residues, contacts, buried surface area or hotspot evidence when needed | partner occupancy -> interface geometry -> discriminating contacts -> bounded recognition claim | The displayed contact is a crystal mate, chain identity is unresolved, or geometry is being used as affinity/necessity evidence |
| `mutation-impact` | What does a variant change locally or functionally relative to WT? | Exact variant and numbering; WT environment; mutant structure/model or justified local analysis; functional, conservation, contact or stability evidence needed by the claim | site context -> WT role -> changed geometry/evidence -> functional boundary | Only the residue is highlighted, the mutant state is absent, or a pathogenic/resistance mechanism is inferred from location alone |
| `mechanism` | Does a traceable chain connect the initiating state or perturbation to the functional consequence? | A directed edge ledger; retrieved, reported or computed evidence for every material edge; functional/perturbation evidence for causal or necessary claims | initiating event -> intermediate structural change(s) -> functional geometry/partner consequence -> bounded conclusion | Any material edge is unsupported, or structural endpoints are being promoted from compatibility to causality or necessity |
| `allostery` | What evidence connects a distal site to a functional site? | Multiple states or perturbations plus network, coupling, dynamics, mutational or functional evidence appropriate to the claim | distal event -> supported propagation/coupling -> functional-site response | A drawn path or endpoint correlation is the only propagation evidence |
| `density-validation` | Does experimental density support the modeled feature and its claimed identity? | Exact map/model relation, map preprocessing and threshold, local density views, validation metrics and threshold sensitivity | global map context -> local support -> alternative/uncertain interpretation -> boundary | Map identity, fitted model, contour convention or local support is missing |
| `family-comparison` | What is conserved and what differs across homologs, paralogs or members? | Identity/orthology, sequence and structural correspondence, comparable assemblies/states, conservation or pocket annotations | common fold/motif -> aligned conserved feature -> divergent feature -> functional boundary | Non-equivalent states or positions are compared as family differences |
| `trajectory-summary` | Which analyzed dynamic states dominate and what motion or population result is supported? | Frozen trajectory and method; clustering/PCA/RMSF/distributions/populations; representative frames chosen upstream | starting ensemble -> dominant states -> measured motion/population -> interpretation | Raw frames are treated as analysis, or interpolated Story scenes are presented as the trajectory |
| `assembly` | How is a large molecular system organized and where is the decision-relevant subcomplex? | Biological assembly, stoichiometry, chain/entity map and relevant subcomplex/interface evidence | whole assembly -> named modules -> target interface/center -> orientation/decision | Assembly identity or stoichiometry is unresolved, or the viewer cannot map colors to named entities |
| `quality-review` | Which regions or claims pass, fail, or remain uncertain? | Accepted validation criteria; clashes/outliers, ligand geometry, map fit, confidence/PAE or other relevant metrics; explicit decision rule | global quality -> localized issue -> corroborating/counter evidence -> accept/reject/rework boundary | The threshold/denominator is undefined, or prediction confidence is presented as experimental validation |

Use public MolViewSpec selectors, annotations, primitives, volume surfaces,
camera/focus and representations only after the upstream evidence named above is
frozen. The visual capability never substitutes for the missing analysis.

## Common Compositions

The following routes cover the recurring scene classes without creating a
protein-family template for each one.

| Scenario | Default composition | Typical closing question |
|---|---|---|
| Small-molecule binding, agonist/antagonist/inhibitor, selectivity, covalent or fragment binding | `ligand-binding` + optional `state-comparison` + `mechanism` | What pose and local rearrangement are supported, and how far can mechanism be claimed? |
| Apo/holo, active/inactive, open/closed or catalytic-state comparison | `state-comparison` + `conformational-change` | Where and by how much do defensibly comparable endpoints differ? |
| Enzyme catalytic sequence | `ligand-binding` + `state-comparison` + `mechanism` | How do substrate/cofactor geometry and catalytic residues differ across supported states? |
| Protein-protein recognition, receptor-transducer or dimer interface | `interface` + optional `state-comparison` | Which partner geometry and contacts are supported? |
| Disease, engineered or resistance variant | `mutation-impact` + the affected `ligand-binding`, `interface` or `mechanism` route | What changes beyond merely locating the variant? |
| Allosteric regulation | `allostery` + `state-comparison` + `mechanism` | Which propagation edges are supported and which remain hypothetical? |
| Ion-channel gating or transporter alternating access | `state-comparison` + `conformational-change` + `mechanism` | Which gate/pore/cavity geometry changes, and what transport implication is bounded? |
| Cryo-EM or crystallographic density interpretation | `density-validation` + `quality-review` | Does the map support the ligand, side chain, loop or alternative conformation? |
| Same-protein multi-state or multi-ligand comparison | repeated `state-comparison` plus the relevant functional archetype | Which features are common, state-specific or ligand-specific? |
| Homolog, paralog or protein-family comparison | `family-comparison` + optional `ligand-binding` | Which mapped motifs/pocket residues are conserved or divergent? |
| Antibody-antigen, epitope/paratope and escape | `interface` + optional `mutation-impact` + `family-comparison` | Which epitope is recognized and what evidence supports escape? |
| Protein-DNA/RNA recognition or RNP center | `interface` + optional `mechanism` | Which base/backbone contacts and recognition geometry are supported? |
| Ribosome, proteasome, spliceosome, capsid or other large complex | `assembly` + targeted `interface` or `mechanism` | How does the named subcomplex connect to the functional center? |
| Motor, ATPase, helicase or domain mechanics | `state-comparison` + `conformational-change` + `mechanism` | How does nucleotide/state-dependent domain geometry connect to the mechanical output? |
| Zymogen maturation, cleavage or precursor processing | `state-comparison` + `mutation-impact` + `mechanism` | What structural feature forms or becomes accessible after processing? |
| Phosphorylation, glycosylation or another PTM | `mutation-impact` as site-perturbation + affected `interface`, `assembly` or `mechanism` | What local interaction, shielding or accessibility consequence is actually supported? |
| Drug-resistance mechanism | `ligand-binding` + `mutation-impact` + `state-comparison` | Does the variant alter supported drug compatibility without overclaiming affinity? |
| Molecular-dynamics result | `trajectory-summary` + `conformational-change` | Which analyzed states/populations and motions, rather than raw frames, answer the question? |
| AlphaFold or other predicted-structure interpretation | `quality-review` + optional `family-comparison` or `interface` | Which regions/interfaces are supported by confidence evidence and which are uncertain? |
| Model acceptance and structural QC | `quality-review` + optional `density-validation` | Which specific claims pass, fail or require rework under the declared criteria? |

Examples of composition rather than templating:

- GPCR activation = `ligand-binding` + `state-comparison` +
  `conformational-change` + `interface` + `mechanism`.
- Drug resistance = `ligand-binding` + `mutation-impact` +
  `state-comparison`.
- Antibody escape = `interface` + `mutation-impact` +
  `family-comparison` when several antibodies or variants are compared.

## Freeze Question Coverage Before Scenes

Write a compact coverage plan before Story code. It should enumerate every
material branch of the user's question and every mechanism edge:

```yaml
archetypes: [ligand-binding, state-comparison, conformational-change, interface, mechanism]
subquestions:
  - id: Q1
    question: Where is the ligand and what supports its pose?
    status: answered       # answered | bounded | unresolved | not-applicable
    evidence_ids: [E5, E8]
    claim_ids: [C3]
  - id: Q2
    question: Why is the receptor displacement relevant to downstream binding?
    status: bounded
    evidence_ids: [E10, E11]
    claim_ids: [C7]
mechanism_edges:
  - id: M2
    from: intracellular-cavity-opening
    to: transducer-tail-occupancy
    status: evidenced      # evidenced | gap | not-applicable
    evidence_ids: [E10, E11]
    strongest_allowed_wording: geometrically accommodates
```

The final conclusion must answer or explicitly bound every subquestion. A gap is
an accepted scientific outcome when recorded; it is not permission to omit the
question from the Story.

## Pass The Information-Density Gate

A scene earns its place only when it does at least one of the following:

1. introduces evidence needed to orient or discriminate a claim;
2. performs a comparison that changes the interpretation or decision;
3. closes a question branch or makes a material claim boundary/gap inspectable.

Merge a scene that merely repeats the prior view, changes style without adding
evidence, or contains only an orientation sentence. Context is legitimate when
identity, assembly, numbering, provenance or the common coordinate frame is
decision-critical. Do not maximize atom count, labels, or claims per scene:
information density means each scene advances the argument, not visual clutter.

Before acceptance, verify:

- every user-facing question branch is `answered`, `bounded`, `unresolved`, or
  `not-applicable` with a reason;
- every material mechanism edge is evidenced or shown as a gap;
- every scene advances at least one coverage item and every major claim is
  inspectable in at least one scene;
- causal terms such as *causes*, *drives*, *enables*, *required* or *necessary*
  do not exceed the strongest evidence type;
- the conclusion closes the coverage plan rather than summarizing only the
  easiest endpoint comparison.
