# Model selection and ignition interpretation

## Match the observable

A maximum in dT/dt, a maximum in OH mole fraction, an OH* chemiluminescence onset,
a fixed temperature rise, and a pressure-based delay are different observables. The
helper implements only the global maximum dT/dt, guarded by a specified temperature
rise. Tracked species are exported to support inspection; their maxima do not silently
replace the configured definition. OH and excited OH* are distinct species and may
not both exist in the mechanism.

Two-stage ignition may have an early weak heat-release peak and a later stronger one.
The global-maximum definition selects the strongest heating peak in the modeled horizon.
If the user needs first-stage delay, define and validate a separate event detector and
report both. Extending the horizon can change which peak is largest; the automatic
longer-horizon run checks this possibility but cannot prove no later event exists.

## Numerical diagnosis

An interior derivative maximum can still be sampled coarsely. Inspect peak width,
compare the finer output grid, and increase samples until the uncertainty is adequate
for the intended comparison. Internal solver tolerance and output sampling are distinct:
a tightly integrated trajectory can yield a poorly located derivative on a coarse output
grid. The tighter-solver run also halves the allowed internal time step; its comparison
therefore tests those controls together.

Unreached temperature rise means only that the threshold was not observed in this model
and horizon. It does not establish nonflammability, an infinite physical delay, or a
lower bound under a different ignition definition. Review conditions and extend the
horizon when scientifically justified.

Species thermochemistry extrapolation can produce smooth numerical trajectories. Check
the reported thermodynamic temperature interval and the mechanism's original kinetic
validation sources. Small mass, energy, and element residuals do not detect a poor
reaction mechanism, missing pathways, incorrect third-body efficiencies, or a wrong
composition basis.

## Model boundaries

The helper assumes initially 1 m3, closed adiabatic walls, ideal-gas behavior, homogeneous
composition, and no reacting surfaces. Homogeneous ignition time is independent of
this arbitrary initial volume in the modeled system; extensive energies and mass scale
with it. Constant-pressure volume expansion is allowed, so its conserved energy is
enthalpy. Constant-volume pressure rises, so comparison with a nominal constant-pressure
experiment requires a different reactor setting.

Shock tubes, rapid compression machines, and engines may need measured volume histories,
heat transfer, facility effects, or nonideal equations of state. Those are physics changes,
not tolerance adjustments. Use the appropriate upstream reactor class or customized model
and verify the additional terms before interpreting agreement with an experiment.
