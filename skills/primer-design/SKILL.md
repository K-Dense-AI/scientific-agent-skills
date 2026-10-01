---
name: primer-design
description: Designs and audits PCR and RT-qPCR primers with Primer3, explicit thermodynamic conditions, reference-based off-target amplification searches, and traceable sequence coordinates. Use for designing primer pairs, checking existing primers, exon-junction or isoform-specific assays, variant masking, cloning tails, multiplex compatibility, and interpreting Primer-BLAST results. Includes bounded local in-silico PCR and BLAST screening; distinguishes computational candidates from experimentally validated assays.
license: MIT
compatibility: Requires Python 3.11+ and primer3-py 2.3.1 for design and thermodynamics. Local exhaustive screening uses the standard library; BLAST screening additionally needs blastn and makeblastdb on PATH. Network access is needed only for installation, reference retrieval, or external Primer-BLAST.
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
  last-reviewed: "2026-10-01"
---

# Primer design and specificity

Produce candidate oligos in 5-prime-to-3-prime orientation, with the exact template,
chemistry, intended products, and search scope behind each conclusion. Calculate
sequence-dependent quantities with the supplied tools. A familiar gene name, good
Primer3 penalty, or a single BLAST alignment cannot establish primer specificity.

## Choose the workflow

| Request | Start here |
| --- | --- |
| New genomic PCR or RT-qPCR pair | Define the assay and reference; design; assess thermodynamics; screen products. |
| Check an existing pair | Prepare pair TSV; assess both full oligos and annealing cores; screen with explicit intended coordinates. |
| Exon junction, transcript isoform, allele discrimination | Read [design-workflows.md](references/design-workflows.md); supply sequence annotation before imposing constraints. |
| Cloning/adaptor-tailed primers | Design annealing cores, append declared 5-prime tails, reassess full oligos, reconstruct the final product. |
| Multiplex panel | Enable `--multiplex` in both thermodynamics and specificity tools to assess oligo interactions and cross-pair products. |
| Degenerate, bisulfite, probe, or modified-base assay | Use the specialized workflow in [design-workflows.md](references/design-workflows.md); the bundled ordinary-DNA model is insufficient. |

The local tooling supports paired primers with unambiguous ACGT cores. Advanced assay
types have substantive design and validation guidance, but are not silently reduced
to ordinary PCR. This skill designs assays; expression normalization, experimental
diagnostic validation, and guide-RNA design are separate tasks.

## Establish the assay contract

Obtain what changes the result; use explicit provisional assumptions for an exploratory
design, and identify them in the report:

- **Purpose and template:** genomic DNA, cDNA, plasmid, or another defined substrate;
  target organism, accession **with version**, assembly/transcript release, strand,
  desired isoforms, and product-size range. Name wanted and unwanted templates.
- **Sequence evidence:** local FASTA plus source/retrieval date and its SHA-256 hash.
  A locus excerpt uses local coordinates; record its mapping to the full reference.
  Include relevant paralogs, pseudogenes, alternate contigs, transcript isoforms,
  vector backbone, and host sequence in the appropriate screen.
- **Reaction conditions:** polymerase/buffer, monovalent salt, total divalent salt,
  total dNTP, and oligo concentrations. Primer3 uses mM for salts/dNTP and nM for DNA.
  Record the initial reaction concentration separately from Primer3's effective
  annealing-oligo concentration parameter. Engine defaults are assumptions.
- **Constraints:** target interval, allowed/excluded binding regions, junctions,
  variant exclusions and their source, fixed primers, tails, or multiplex membership.
  Do not guess exon boundaries or silently substitute another assembly.
- **Definition of an acceptable result:** relevant off-target references, amplicon
  lengths, mismatch search limits, controls, and experimental validation appropriate
  to the assay. There is no universal thermodynamic cutoff that validates all PCRs.

Use [input-contract.md](references/input-contract.md) for file schemas and coordinate
examples. Copy [assay-report-template.md](assets/assay-report-template.md) into the
analysis directory to collect evidence. Reference retrieval may be manual or through
an established sequence API; preserve accession/version and verify the returned
sequence. The supplied scripts use local files and do not submit sequences online.

## Install and verify

Set `SKILL_DIR` to this skill's actual installed directory. Work in a separate analysis
directory so environments, reference databases, and results do not enter the skill.

```bash
uv venv --python 3.13 .venv-primer
uv pip install --python .venv-primer/bin/python -r "$SKILL_DIR/assets/requirements.txt"
.venv-primer/bin/python "$SKILL_DIR/scripts/design_primers.py" --help
```

Use the environment's `Scripts/python.exe` on Windows. The design/thermodynamic
examples target primer3-py **2.3.1**, tested with Python **3.13**. For the optional
BLAST engine, install NCBI BLAST+ from its official distribution and check:

```bash
blastn -version
makeblastdb -version
```

Local integration checks also exercise BLAST+ 2.17.0; other releases require checking
their output and search behavior before claiming equivalent coverage.

Read [sources.md](references/sources.md) when updating dependencies or API assumptions.
The scripts record engine versions and effective settings in their JSON reports.

## 1. Design candidates

For an initial functional demonstration, use the bundled synthetic sequence. It is
nonbiological example input, not an experimentally validated assay:

```bash
.venv-primer/bin/python "$SKILL_DIR/scripts/design_primers.py" \
  --template "$SKILL_DIR/assets/demo-template.fasta" \
  --preset qpcr --config "$SKILL_DIR/assets/qpcr-config.json" \
  --output design.json --pairs-out pairs.tsv --expected-out expected.tsv
```

For actual work, substitute the reviewed target FASTA and constraints. A multi-record
FASTA requires `--record` with its exact ID. The `pcr` preset requests 100–1000 bp;
`qpcr` requests 70–200 bp. Override these starting ranges in the configuration.
The example overrides its range to 90–180 bp and includes a specific target interval.
Multiple `SEQUENCE_TARGET` intervals are alternatives: Primer3 flanks at least one.
To require coverage of every interval, supply one enclosing target and verify the
returned product; separate assays require separate design runs.

The tool:

- Passes validated `sequence_args` and `global_args` to Primer3. Unsupported or
  misspelled tags fail rather than silently changing the task.
- Converts ambiguous template positions to `N` and forbids ambiguous primer bases.
  It does not interpret lowercase sequence as a repeat mask; use explicit exclusions.
- Optionally imports `--mask-bed` exclusions in **the supplied template's coordinates**.
  Use BED intervals for variant/repeat masking only after validating the reference
  mapping; it does not infer allele frequencies or convert arbitrary VCFs.
- Verifies returned forward and reverse sequences against the template and checks
  product lengths. Primer3's right-primer position is converted into a half-open
  binding interval; the reverse primer is already in ordering orientation.
- Optionally appends `--forward-tail` and `--reverse-tail` to cores. The design score
  and core Tm do not include those tails; step 2 checks complete oligos.

Inspect `engine_explanations` when no candidates are found. Change a biologically
justified constraint and rerun; do not silently relax all constraints or return an
invented sequence. Preserve previous reports when comparing parameter choices.

`expected.tsv` describes intended products **on the design template**. If screening
another reference, map these coordinates to its exact record IDs and orientation.
A cDNA product cannot be relabeled as a genomic interval across introns.

## 2. Assess thermodynamics

Use the **same chemistry as the design**. The following explicit values match the
bundled design defaults; replace them together when the actual conditions differ:

```bash
.venv-primer/bin/python "$SKILL_DIR/scripts/check_thermodynamics.py" \
  --pairs pairs.tsv --mv-conc 50 --dv-conc 1.5 --dntp-conc 0.6 \
  --dna-conc 50 --temp-c 37 --output thermodynamics.json
```

The report contains core Tm, core and full-oligo hairpins/homodimers, full-oligo
heterodimers, self 3-prime end stability, and both directional inter-oligo 3-prime
end-stability calculations. Delta-G and
delta-H are reported in kcal/mol; delta-S in cal/(mol K). `--temp-c` controls the
temperature for delta-G, **not** a recommended PCR annealing temperature.

If design used different Tm/salt models, also set `--tm-method` and
`--salt-corrections-method` to match; see the mapping in the input contract.

For a panel, add `--multiplex` to examine all unordered oligo combinations, including
forward/forward and reverse/reverse between different pairs. Distinguish a panel to
be combined from alternative candidates that will be tested separately.

Read [thermodynamics.md](references/thermodynamics.md) before interpreting these
values. Full oligos longer than 60 bases are reported as unresolved; they are never
silently truncated. Modified bases and degenerate mixtures require a suitable model.
Thermodynamic predictions support ranking and experimental planning, not a blanket
claim of primer quality.
Nonfinite Tm or a Tm at/below absolute zero is rejected as a calculation/input
failure; such a result must not be ranked as an ordinary low-Tm primer.

## 3. Screen amplification products

Read [specificity.md](references/specificity.md) before making a specificity claim.
Search each primer on both strands and pair inward-facing binding sites. A binding
hit alone is not an amplicon; absence of a reported hit is not proof of absence.

### Exhaustive bounded local search

```bash
.venv-primer/bin/python "$SKILL_DIR/scripts/screen_specificity.py" \
  --pairs pairs.tsv --reference "$SKILL_DIR/assets/demo-template.fasta" \
  --expected expected.tsv --engine exhaustive \
  --min-product 40 --max-product 1000 --max-mismatches 2 \
  --three-prime-bases 5 --max-three-prime-mismatches 0 \
  --output specificity.json
```

This enumerates full-length, ungapped binding sites in a **bounded local reference**
and checks F/R, R/F, F/F, and R/R products for each pair. Reference ambiguity is
treated conservatively as unresolved sequence; it cannot establish a clean result.
The mismatch limits are a search model, not a validated polymerase discrimination
rule. Tight 3-prime thresholds can exclude amplifiable mismatched sites; broaden
the search when evaluating that uncertainty.

Use `--circular RECORD_ID` for a circular molecule. Wrapped products use canonical
start coordinates and unwrapped ends greater than the reference length; only
products spanning at most one molecule are considered. Caps on comparisons, hits,
and products prevent unbounded work; hitting a cap makes the result incomplete.

### BLAST-assisted local search

```bash
.venv-primer/bin/python "$SKILL_DIR/scripts/screen_specificity.py" \
  --pairs pairs.tsv --reference "$SKILL_DIR/assets/demo-template.fasta" \
  --expected expected.tsv --engine blast \
  --min-product 40 --max-product 1000 --max-mismatches 2 \
  --three-prime-bases 5 --max-three-prime-mismatches 0 \
  --output specificity-blast.json
```

The script builds a temporary local BLAST database, runs short-query alignment,
rechecks complete primer-length candidate sites, and records commands and versions.
It checks configured hit limits and tool failures. BLAST discovery is heuristic:
successful execution and unsaturated limits do not establish exhaustive coverage.
The reference is loaded in memory; plan memory and search bounds for large genomes.
The small example verifies execution, not human-genome sensitivity or scalability.

For broader public-reference screening, follow the official NCBI Primer-BLAST
workflow in [specificity.md](references/specificity.md), choosing the organism,
database, intended templates, maximum product length, and mismatch policy deliberately.
Submitting a sequence sends it to NCBI; keep local-only work local. Primer-BLAST
is not a documented REST API implemented by these scripts.

### Interpret the result

- `potential_off_target`: inspect every unexpected product, including its orientation,
  length, mismatch positions, and reference identity; redesign or justify its relevance.
- `intended_target_not_found`: resolve mapping, reference, sequence, and search problems
  before drawing specificity conclusions.
- `no_expected_target`: results are a product inventory, without a target-specific
  conclusion. Supply all intended product intervals for the assay.
- `incomplete`: reference uncertainty, resource limits, or failed computation leaves
  the conclusion unresolved. Inspect the reported reason and repeat appropriately.
- `no_off_target_found_within_search_scope`: state the exact reference and search
  model. Check the report's exhaustive/heuristic flags; this is not empirical validation.

For a multiplex reaction, add `--multiplex` to the specificity command as well as
the thermodynamics command. The specificity tool then searches every cross-pair
oligo combination, retaining the original oligo identities and tails. It treats
cross-pair products as unintended; intentionally shared-primer designs require
explicit standalone combinations with reviewed expected products. The
`--max-panel-combinations` cap defaults to 10,000 and is checked before expansion.
Thermodynamic `--multiplex` checks structures; specificity `--multiplex` checks
reference products. Both are necessary for this panel assessment.

## 4. Validate the assay and deliver evidence

Select candidates using assay purpose, coverage, specificity evidence, and chemistry,
not just the lowest Primer3 penalty. Preserve multiple candidates when uncertainty
remains. Follow [design-workflows.md](references/design-workflows.md) for the relevant
experimental checks: expected product identity/size, negative and no-template controls,
genomic contamination controls for RT-qPCR, and efficiency/dynamic-range assessment
when quantification is intended. A single melt peak alone does not prove identity.

Deliver the completed [report template](assets/assay-report-template.md), pair TSV,
design/thermodynamic/specificity JSON, and source manifest. Include:

1. Exact ordering sequences, separated annealing cores and tails, primer lengths,
   intended product coordinates/size, and any relevant transcript/junction mapping.
2. Chemistry and model settings; engine versions; reference accession/release, source,
   retrieval date, and file hashes; explicit exclusions and rationale.
3. Intended and potential unintended products; uncertainty from unknown bases,
   incomplete references, heuristic searches, caps, and unsupported assay chemistry.
4. Experimental evidence actually obtained, outstanding validation, and the reason
   for each recommended candidate. Label untested candidates accurately.

## Validation and limits of this implementation

The repository suite at `tests/primer-design/` exercises actual Primer3 calculations,
orientation and coordinate reconstruction, masking, tails, concentration handling,
off-target product geometry, mismatch/ambiguity behavior, failure states, and local
BLAST integration when its executables are installed. Synthetic fixtures establish
software behavior; they do not validate a biological assay or prove genome-wide recall.

Tools return 0 when their computation completes, 1 for a completed design with no
candidates or incomplete long-oligo thermodynamics, and 2 for invalid input or tool
failure. Read the JSON scientific status even after exit 0: finding an off-target is
a successfully completed calculation. See the input contract for screen-specific exits.

## Citing Scientific Agent Skills

If used in published work, cite the upstream methods in [sources.md](references/sources.md)
and [Scientific Agent Skills](https://arxiv.org/abs/2609.00065). Report the software
versions and assay-specific settings required to reproduce the actual analysis.
