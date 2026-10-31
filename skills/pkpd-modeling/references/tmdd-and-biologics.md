# TMDD and biologics: analyte mapping before fitting

## Mechanistic state and units

A basic full TMDD model represents free drug L, free target R and complex LR:

```
dL/dt  = input - kel*L - kon*L*R + koff*LR
dR/dt  = ksyn - kdeg*R - kon*L*R + koff*LR
dLR/dt = kon*L*R - (koff+kint)*LR
```

These equations assume compatible molar concentrations and binding stoichiometry. A mass dose
and molar target cannot be combined without molecular-weight conversion. Full TMDD still assumes
a structural system, compartments, turnover and observation mapping; it is not assumption-free.
Binding constants have different units, so ratios such as kon/kel do not directly diagnose stiffness.
Assess solver/tolerance behavior. The helper uses adaptive LSODA integration.

`_models.simulate_tmdd()` supports IV input only and returns free drug, free target, complex and
total drug separately. Match each assay to the state it actually measures. Ligand-binding assays
can measure free, total or other operational fractions depending on reagents and conditions;
there is no universal rule that they report total drug.

## Approximations and identification

Equilibrium uses `Kd=koff/kon`; quasi-steady state uses `Kss=(koff+kint)/kon` under a timescale
approximation. Those assumptions must hold over the intended concentration range. Constant-target,
irreversible-binding and Michaelis-Menten reductions discard additional information. Choose based
on available observations and model purpose, not a mandatory hierarchy.

Drug-only observations often poorly identify binding, internalization and target turnover separately.
Measure target/complex where feasible, fix independently supported parameters with uncertainty,
and inspect sensitivity rank and profiles. A low residual error does not validate binding kinetics.
Dose-normalized profiles failing to overlap suggest nonlinear disposition, not TMDD uniquely;
apparent overlap within a noisy limited range does not prove target saturation.

Pharmpy 2.2.0 API `set_tmdd(model, type=...)` accepts full, ib, cr, crib, qss, wagner and mmapp.
`dv_types` maps drug, drug_tot, target, target_tot and complex to integer observation IDs. Assign
its returned model and inspect the resulting observation equations. The QSS transformation was
executed locally; no TMDD clinical estimation engine was run.
[Pharmpy TMDD API](https://pharmpy.github.io/latest/api/pharmpy.modeling.set_tmdd.html).

## Broader biologic considerations

FcRn recycling, proteolysis, target binding, subcutaneous absorption and immunogenicity can affect
antibody PK. Neither a fixed half-life range nor a blanket lack of renal/organ effects establishes
plausibility for a specific engineered molecule or disease population. Evaluate the molecule and
population, including protein loss and inflammation when relevant.

ADA may alter clearance, neutralization and assay behavior. Use timing, titre, drug tolerance and
missingness, not only a baseline binary flag; apparent ADA/exposure associations can be bidirectional.
For ADCs, distinguish conjugated antibody, total antibody and unconjugated payload, accounting for
drug-to-antibody distribution and analyte-specific efficacy/safety relevance. A concentration
ratio alone does not identify deconjugation. Bispecific/ternary-complex systems can show hook
effects; a monotone Emax or ordinary binary TMDD model need not represent them.
