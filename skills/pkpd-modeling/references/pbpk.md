# PBPK: context of use and verification

PBPK links physiology, drug properties and mechanistic disposition. System parameters can be
fixed, population-distributed, calibrated or uncertain; they are not inherently known. Use it when
the intended extrapolation benefits from mechanisms such as enzyme/transporter DDI, absorption,
organ function, maturation or tissue distribution. Population PK and PBPK can complement each
other; neither is automatically superior for every in-range or out-of-range question.

## Platforms

PK-Sim/MoBi in Open Systems Pharmacology Suite 12 Update 3 (PK-Sim/MoBi 12.3) provide an open
platform with an R interface. Vendor suites include Simcyp and GastroPlus. Select according to
required mechanisms, population/model availability, qualification evidence and reproducibility;
no platform name alone establishes regulatory acceptance. The current `ospsuite` 12.3.2 release
notes should be checked for matching runtime and platform requirements before installation.
[OSP releases](https://github.com/Open-Systems-Pharmacology/Suite/releases),
[OSPSuite-R news](https://github.com/Open-Systems-Pharmacology/OSPSuite-R/blob/main/NEWS.md).
These platforms and interfaces were documentation-reviewed, not run in this refresh.

## Construction checks

1. Specify blood/plasma basis, unbound fractions, amount/concentration units, organ volumes/flows,
   partition model and elimination routes. Do not mix plasma fu and whole-blood clearance without
   the blood/plasma conversion.
2. For perfusion-limited distribution, use a consistent partition basis in
   `Vt*dCt/dt=Qt*(Ca-Ct/Kt)`. Permeability-limited systems need separate vascular/extravascular
   states and transfer terms; a tissue name alone does not choose the correct approximation.
3. Scale intrinsic clearance with traceable protein/cell abundance and organ-size inputs.
   Well-stirred hepatic blood clearance is `Qh*fu_b*CLint/(Qh+fu_b*CLint)` under its assumptions.
4. Distinguish measured, predicted, fixed and fitted parameters. Tissue partition methods and
   empirical IVIVE scaling factors are modeling choices, not direct observations.
5. Check mass balance, numerical tolerance, dose/input events and sensitivity to uncertain binding,
   fm, Ki, CLint, permeability and physiological inputs.

## Credibility for the intended decision

Separate calibration data from verification evidence where feasible. Evaluate relevant routes,
doses, temporal profiles and challenging conditions; agreement with one AUC does not validate a
mechanism. For DDI, interrogate both perpetrator and substrate components and alternatives.
Predicted tissue exposure can remain uncertain despite agreement with plasma concentrations.

There is no universal twofold acceptance rule. Prespecify context-appropriate criteria and quantify
parameter, structural and population uncertainty. An organ-impairment prediction does not
automatically replace a clinical study. Explain why verification supports the specific extrapolation.
[ICH M15 FDA guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/m15-general-principles-model-informed-drug-development)
and [ICH M12](https://www.ema.europa.eu/en/scientific-guidelines/ich-m12-drug-interaction-studies)
provide relevant decision frameworks.

Archive the model, software/library versions, population definition, calibration/verification data,
parameter sources, sensitivity design and simulation seeds. The bundled one-to-three-compartment
models are empirical PK, not PBPK implementations.
