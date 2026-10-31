# Primer-design validation record

## Documentation/API refresh, 2026-10-01

Python 3.13.3, primer3-py 2.3.1, libprimer3 2.6.1 and local BLAST+ 2.17.0 were
rechecked. The isolated suite passed **93 tests without skips**, including seven
real BLAST integration cases. Native additions verify alternative target semantics,
temperature/free-energy consistency, rejection of finite but physically invalid
Tm, and the reverse-reference coordinate transform under both search engines.
`uv run skills-ref validate skills/primer-design` and scoped `git diff --check`
passed. All four documented demonstration commands ran in a fresh environment:
three primer pairs, completed thermodynamics, and scoped clean product searches
with both exhaustive and heuristic engines.

BLAST executables were `/opt/homebrew/bin/blastn` and
`/opt/homebrew/bin/makeblastdb`; retain that directory on PATH to exercise these
integration tests. Tests use small synthetic sequences and no network search.
No Primer-BLAST job was submitted or biological assay performed. The public
interface, Primer3 reference/API, current package metadata, and primary references
were reviewed; the former NEB Taq PDF link returned a not-found page and was replaced
with a current NEB Q5 study. Publisher MIQE full-text extraction was limited;
official indexed text and its PubMed abstract were available. Repository-wide
validation and the current security scan are coordinated by the collection owner.

No optional `docs/images/primer-design.png` exists, so no image was generated.

## Original validation, 2026-09-30

Validated on 2026-09-30 with Python 3.13.3, primer3-py 2.3.1,
libprimer3 release 2.6.1, and NCBI BLAST+ 2.17.0 on macOS. These results
establish software behavior on synthetic inputs, not biological assay performance.

## Executed checks

| Check | Result |
| --- | --- |
| `uv sync` | Passed |
| `uv run skills-ref validate skills/primer-design` | Passed |
| `uv run --with pytest python -m pytest tests/_meta -q` | 11 passed; 4,212 subtests passed |
| `python tests/run_all.py --isolated primer-design` | 86 passed; no skipped tests in this environment |
| Documented design, thermodynamics, exhaustive-screen, and BLAST-screen examples | Executed successfully on the bundled synthetic template |
| `git diff --check` | Passed |
| Repository security scanner, failing at HIGH severity | Passed; 0 CRITICAL, 0 HIGH, 2 LOW findings reviewed below |

The isolated suite includes six integration tests that execute real BLAST+ tools.
Those six skip explicitly when `blastn` or `makeblastdb` is absent; a passing
Python-only run must not be represented as BLAST integration evidence.

Coverage includes actual Primer3 design and numerical thermodynamics; explicit
chemistry and Tm models; quality scores; fixed primers; exon-junction coordinate
semantics; exclusions and BED masking; reverse orientation; tail concatenation
and product reconstruction; unsupported long oligos; both directional 3-prime
interactions; F/R, R/F, F/F and R/R products; circular origin crossing; mismatch
positions and ambiguous reference bases; multiplex cross-pair products and search
deduplication; resource caps; tool failures; and protection against overwriting
input files, including linked paths.

## Agent workflow evaluations

Prompts, grader assertions, and raw synthetic inputs are retained in
[evals.json](evals.json) and [fixtures/](fixtures/). Each case was run once with the
skill and once without it. Grading combined artifact inspection with independent
sequence/coordinate, thermodynamic, product-inventory, and source-hash checks.

| Case | With skill | Without skill | What was verified |
| --- | --- | --- | --- |
| Existing pair with same-primer off-target products | 5/5 assertions | 5/5 assertions | Intended 154-bp product and both unexpected F/F products, numerical thermodynamics, provenance, and redesign recommendation |
| Tailed design with BED exclusions | 6/6 assertions | 6/6 assertions | Three valid flanking pairs, correct strands and masks, exact 48-base tails, core Tm, unresolved 68-nt full-oligo structures, scoped specificity, and reproducibility |

The first case is a workflow smoke test, **not a blinded efficacy comparison**:
the skill-assisted executor read the evaluation definition, which exposed an
expected-output hint about the same-primer products. Fresh executors for the
second case received only the prompt and named input fixtures; expected outputs
and grader assertions were withheld. Future executors must follow that separation.

Both configurations passed both cases. This small evaluation does **not** establish
improved task success, time savings, or token savings from the skill. Overall agent
wall times and token counts were not reliably measured and are not reported. The
baseline's second report additionally quantified isolated-tail self-association;
the skill-assisted report identified the self-complementary tail and correctly
left complete-oligo structure assessment unresolved.

## Security review

The final `scan_pr_skills.py` run returned two LOW findings:

- `LLM_UNAUTHORIZED_TOOL_USE`: informational absence of optional `allowed-tools`.
  The skill is portable across agent hosts, documents its executables and
  dependencies, and invokes local BLAST tools with argument lists rather than a
  shell. The scanner identified no injection vector.
- `LLM_RESOURCE_ABUSE`: the exhaustive scan can consume substantial resources if
  a caller deliberately raises its bounds. Existing comparison, hit, product,
  panel, subprocess-output, and timeout limits stop incomplete work from being
  reported as a complete search. The reference-memory and genome-scale limits
  are documented. The scan recommended no required action.

An earlier critical behavioral finding was verified against the scanner and AST:
its substring detector interpreted an ordinary identifier containing `exec` as
dynamic execution. Renaming that local identifier removed the false positive;
there are no `eval`, `exec`, or shell-based process calls in the skill scripts.

## Remaining validation boundaries

- All sequence fixtures are synthetic; no primers were ordered or experimentally
  validated. No human-genome sensitivity or scalability benchmark was performed.
- BLAST discovery remains heuristic even when its integration tests pass. The
  exhaustive engine is complete only within its stated bounded, ungapped model.
- NCBI Primer-BLAST is documented as an external workflow; no live submission or
  undocumented API integration was tested.
- Specialized probe, degenerate, bisulfite, modified-base, and allele-specific
  workflows have explicit guidance and limits. They are not automated or
  empirically validated by the ordinary-DNA CLI suite.
- Full oligos longer than 60 nt remain explicitly unresolved in the bundled
  thermodynamic workflow; no truncation is used to manufacture a result.
