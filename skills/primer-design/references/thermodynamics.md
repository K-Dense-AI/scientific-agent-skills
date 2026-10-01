# Thermodynamic calculations and interpretation

Documentation checked: 2026-09-30 against primer3-py 2.3.1 documentation.
Use the version recorded by the actual run to describe tested behavior.

## Record the physical assumptions

Nearest-neighbor predictions use sequence context and specified solution
conditions. They do not make an oligo's Tm an invariant property. The unified DNA
parameter framework is described by
[SantaLucia (1998)](https://pubmed.ncbi.nlm.nih.gov/9465037/); mixed monovalent and
magnesium effects require appropriate correction, as studied by
[Owczarzy et al. (2008)](https://pubmed.ncbi.nlm.nih.gov/18422348/).

| Input | primer3-py unit | Reporting requirement |
| --- | --- | --- |
| Monovalent cations (`mv_conc`) | mM | State measured, manufacturer-supplied, or assumed value |
| Divalent cations (`dv_conc`) | mM | Record the supplied magnesium/cation value |
| dNTPs (`dntp_conc`) | mM | State concentration convention; avoid silently mixing total and per-nucleotide amounts |
| Oligo concentration (`dna_conc`) | nM | Use the model's concentration convention consistently |
| Free-energy evaluation (`temp_c`) | °C | Store with every ΔG comparison |
| DMSO, when modeled | percent | Tm correction is not a complete reaction model |
| Formamide, when modeled | mol/L | Do not enter a percentage as molarity |

These parameter units are documented in the
[primer3-py quickstart](https://libnano.github.io/primer3-py/quickstart.html).
For proprietary mixes with undisclosed composition, label chosen values as
assumptions and compare plausible conditions if necessary. Never back-fill exact
chemistry from the name of a kit.

## Calculate several distinct quantities

Use the snake_case APIs: `calc_tm`, `calc_hairpin`, `calc_homodimer`,
`calc_heterodimer`, and `calc_end_stability`. The end-stability calculation is
directional; examine both oligo orders when either primer's 3′ end matters.
Do not reverse-complement an oligo before passing synthesized sequences to the
structure routines. [API definitions](https://libnano.github.io/primer3-py/api/bindings.html).

For each oligo record its annealing-core Tm, GC fraction, and length, then review
hairpin and self-dimer results for the full ordered sequence. For each interacting
pair record heterodimer and both directional 3′-end assessments. Preserve predicted
structure alignments when available so the location of terminal complementarity
can be inspected.

`ThermoResult.dg` and `.dh` use **cal/mol**; `.ds` uses **cal/(mol·K)**; `.tm` uses
°C. Divide energy by 1000 before displaying kcal/mol. Store `structure_found`:
missing structures and zero-valued fields are not interchangeable evidence.
[ThermoResult documentation](https://libnano.github.io/primer3-py/api/thermoanalysis.html).

## Keep screening thresholds in context

- A low difference between primer Tm values supports compatible conditions but says
  nothing about reference specificity or amplification efficiency.
- A predicted favorable dimer ΔG does not by itself show that the polymerase can
  extend that alignment. Inspect 3′ placement as well as thermodynamic stability.
- Compare energies only at matched temperatures, concentrations, and model settings.
  Comparing one program's default ΔG with another's numeric cutoff is unreliable.
- A candidate close to a chosen limit deserves sensitivity analysis, not unwarranted
  numerical precision. Report useful decimals while retaining raw output.

Thresholds are selection criteria chosen for a particular assay. They are not
universal scientific pass/fail constants. Retain the assumptions, threshold
definition, observed value, and reason for any override.

Predicted Tm is not an automatic annealing temperature. Follow the selected
polymerase's current instructions and validate an appropriate condition range.
Even manufacturer protocols differ; for example, NEB's
[Taq guidance](https://www.neb.com/en/protocols/taq-5x-master-mix-pcr-guidelines?pdf=true)
and [Phusion Flash guidance](https://www.neb.com/en/protocols/guidelines-for-pcr-optimization-with-phusion-flash-high-fidelity-pcr-master-mix?pdf=true)
use different temperature recommendations.

## Model and implementation boundaries

The documented `calc_tm` nearest-neighbor path applies up to its configured length
limit, normally 60 bases; longer sequences switch to an approximation. Structure
routines also have length limits. The bundled checker constrains ordinary oligos
instead of silently using unsupported long-tail calculations. Check runtime errors
and emitted limits rather than inferring successful analysis from a partial table.
[primer3-py API](https://libnano.github.io/primer3-py/api/bindings.html).

Do not substitute ambiguity symbols, RNA, inosine, or modified bases into an ACGT
DNA model and call the result validated. Modified chemistries require appropriate
parameters; for example, LNA substitutions affect both stability and
sequence-dependent mismatch discrimination.
[LNA thermodynamics study](https://pubmed.ncbi.nlm.nih.gov/21928795/).

For tailed primers, model the core's initial template interaction separately from
full-oligo structures. For degenerate mixtures, a single “consensus Tm” hides the
different species and effective concentrations. For multiplex panels, include
cross-pair interactions and disclose any capped enumeration.

## Reproducibility and implementation checks

Record Python, primer3-py, and underlying libprimer3 versions, full sequence inputs,
all chemistry/model settings, warnings, and raw results. Test that:

1. Tm changes appropriately when chemistry inputs change; values were not replaced
   by a fixed rule based only on GC count.
2. Displayed energy units match raw values and conversions.
3. Swapping oligos preserves symmetric dimer comparisons while directional end
   results retain their correct orientation.
4. An invalid or unsupported sequence is reported as unassessed, never silently
   shortened, stripped of modifications, or replaced with an arbitrary base.
5. Tails are included in full-oligo interaction analysis and excluded from the
   initial binding-core Tm and ordinary reference search.
