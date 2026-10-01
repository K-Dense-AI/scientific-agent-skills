# Compensation, transforms, and gates

## Event sources are different representations

FlowKit `Sample` uses FlowIO preprocessing by default: gain, logarithmic FCS
encoding, and time scaling are applied when loading. Consequently,
`sample.get_events(source="raw")` is **before compensation/transforms**, not
necessarily the values encoded in the FCS DATA segment. Reserve
`preprocess=False` for explicitly investigating encoding; it changes the
coordinate system and may make an existing strategy inappropriate.

`source="comp"` requires compensation to have been applied to the Sample;
`source="xform"` requires transformation. The default event source is `xform`,
so specify the source instead of relying on it. Gating a Sample through a
`GatingStrategy` processes its own event arrays; do not assume that it also
populates the Sample's `comp` or `xform` arrays.

## Compensation

Construct `fk.Matrix(spill_data_or_file, detectors, fluorochromes=None)` using
detector/PnN names in the matrix's order. Inputs can be a NumPy matrix, an FCS
spillover keyword string, or supported spillover text. Marker/PnS labels are
annotations and do not replace detector identity. Confirm that all detectors
are present, the matrix is finite and nonsingular, and the fluorescence panel
matches the controls. An identity matrix means no cross-channel spillover; it
is not a fallback for a missing matrix.

For GatingML export in 1.3.2, supply nonempty `fluorochromes` labels as well.
Omitting them leaves empty labels in the exported XML, which fails GatingML
schema validation on re-import even though in-memory gating works. Use the
panel's actual fluorochrome names in matrix order and verify the round-trip.

For a programmatic strategy, register it with
`strategy.add_comp_matrix("spill", matrix)` and set
`compensation_ref="spill"` on the relevant `Dimension`s. The special reference
`"FCS"` uses spillover metadata from each sample; check that every sample has
the intended metadata before using it. The default dimension reference is
`"uncompensated"`. Merely registering a matrix does not apply it to all gates.

For direct fluorescence summaries, use `sample.apply_compensation(matrix)`
and explicitly read `source="comp"`. This starts from that Sample's raw event
array. It cannot detect that the FCS itself was exported already compensated;
verify export provenance to avoid compensating such data a second time.

Classical spillover compensation is not a general replacement for spectral
unmixing. Confirm how spectral-instrument data were unmixed and exported.

## Transform and threshold coordinates

`LogicleTransform(param_t, param_w, param_m, param_a)` handles signed
fluorescence. Match parameters to the acquisition and analysis definition;
the values in the quick start are illustrative. FlowJo's
`WSPBiexTransform` is a distinct transform; substituting logicle or an
arbitrary arcsinh cofactor can change imported gate membership.

Register transforms with `strategy.add_transform(id, transform)` and reference
that ID on each dimension needing it. Gate vertices/bounds must be in the
coordinates of that dimension. If a scientifically justified threshold is on
the untransformed compensated scale, transform that threshold with the same
object used for the data, as the quick start does. Do not transform imported
workspace gates again; the workspace parser handles their coordinates.

## Hierarchy and visual checks

Top-level gates have path `("root",)`. A child of `Cells` has path
`("root", "Cells")`; the gate's own name is excluded from its path. Rectangle
lower bounds are inclusive and upper bounds exclusive. Missing bounds are
unbounded. Polygon boundaries and events near thresholds require particular
care when comparing software implementations.

Get Boolean event masks using
`session.get_gate_membership(sample_id, gate_name, gate_path=path)`. Masks
retain the original sample's event order and cover the entire sample. Their
sum should match the reported count, and child masks should be subsets of
their parents. Boolean/overlapping gates need not sum to the parent count;
mutually exclusive quadrants should be checked as a partition when applicable.

`session.plot_gate(sample_id, gate_name, gate_path=path)` returns a Bokeh plot.
Save it with `bokeh.plotting.save`, using `bokeh.resources.INLINE` when the
HTML must work offline. Inspect events and gate boundaries in matching
coordinates; plotting uses subsampling for large samples, while analysis
uses full event arrays. Plotting is not evidence that controls support a gate.

## Primary sources

- [Sample API](https://flowkit.readthedocs.io/en/latest/sample.html)
- [Matrix API](https://flowkit.readthedocs.io/en/latest/matrix.html)
- [Dimension API](https://flowkit.readthedocs.io/en/latest/dimension.html)
- [GatingStrategy API](https://flowkit.readthedocs.io/en/latest/gating_strategy.html)
