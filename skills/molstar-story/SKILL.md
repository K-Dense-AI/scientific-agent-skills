---
name: molstar-story
description: >-
  Builds evidence-backed interactive Mol* Story/MolViewStories artifacts for
  structural-mechanism questions. Use when ligand pockets, conformational
  states, interfaces, mutations, density, or multi-structure results must be
  organized into a traceable scene sequence with scientific claim boundaries
  and browser acceptance. Do not use for ordinary HTML indexes, generic
  structure retrieval, or PyMOL-specific sessions.
license: MIT
compatibility: >-
  Analysis requires Python 3.10+ and NumPy. Story builds require Deno and the
  pinned MolViewStories checkout; browser acceptance requires Playwright,
  Chromium, and Pillow. Network access is normally needed for evidence
  retrieval and the first pinned-runtime build.
metadata:
  version: "1.0"
  skill-author: Molaison
---

# Mol* Story

Produce an ordered scientific argument that a reviewer can inspect, rotate, and
revisit. The complete workflow is question -> retrieval -> evidence selection
-> analysis -> claims -> Story. Mol* is the final representation engine, not the
search or analysis engine and not a substitute for source evidence.

## Establish The Question

First determine whether the user supplied authoritative frozen evidence or only
a scientific question, protein, phenomenon, or example structure. A PDB ID is
often a retrieval result, not a required input. Do not ask for structures when
the target identity and suitable evidence can be found from authoritative
sources.

Before authoring scenes, freeze:

- the scientific question and the decision the Story must support;
- a provisional composition of question archetypes and a coverage plan for all
  material subquestions and mechanism edges;
- exact coordinate files, models, assemblies, chains, ligands, residue-numbering
  convention, and any construct or partner differences;
- authoritative upstream measurements and unresolved claims;
- the portability root and required output form.

If equivalent residues, biological assemblies, or state labels cannot be
established, stop with that blocker instead of creating a visually persuasive
but scientifically ambiguous overlay.

Read [references/story-archetypes.md](references/story-archetypes.md) after
resolving the question. Archetypes are evidence contracts, not protein-family
templates. Let retrieval revise the provisional composition, then freeze the
final coverage plan before Story code.

## Retrieve And Select Evidence

When protein identity, structures, state labels, reported results, or supporting
maps are not already authoritative and frozen, read
[references/evidence-retrieval.md](references/evidence-retrieval.md). Resolve the
entity, search the relevant primary and domain sources, and write a candidate
structure matrix before choosing comparison objects.

Selection reasoning belongs to this skill. Do not take the first search result
or silently optimize only resolution. Compare identity, species, construct,
mutation, coverage, assembly, partners, ligand and state semantics, method, and
quality against the scientific question. If the requested apo/holo or other pair
is not scientifically comparable, report that result and reframe the Story
around the strongest available evidence rather than forcing the requested
template.

Keep retrieved facts, publication-reported analyses, and locally computed
analyses distinct. Record source URLs or identifiers, retrieval time, local
artifacts, unresolved fields, exclusion reasons, and a claim/evidence ledger.
For a mechanism question, also record each directed mechanism edge and mark it
as evidenced, gap, or not applicable. Do not omit an unsupported edge merely
because the available endpoint structures make the earlier part of the story
easy to visualize.

## Route Only The Needed Detail

Read [references/story-authoring.md](references/story-authoring.md) for scene,
visual-semantic, packaging, and acceptance rules. For an API or capability that
is not already familiar, use
[references/documentation-router.md](references/documentation-router.md) to open
only the relevant current official page and pinned source/example.

For paired or multi-state comparisons, especially GPCR activation or
apo/ligand-bound questions, also read
[references/state-comparison.md](references/state-comparison.md).

Choose the smallest maintained starting point that fits:

| Review need | Starting point |
|---|---|
| Ligand pose, pocket, or chemical zones | Copy `assets/ligand-pocket-story/` |
| Apo/holo, active/inactive, or other aligned states | Copy `assets/state-comparison-story/` and run `scripts/analyze_pair.py` when its explicit PDB/same-numbering contract fits |
| Interface, mutation, annotation, density, or custom geometry | Route to the official selector, annotation, volume, or primitive docs and author only the necessary scenes |

Do not force a template onto a question it cannot answer. Do not create a new
template until the same scene logic has a verified recurring consumer.

## Compute Evidence Upstream

MolViewSpec declares what to load and render. Compute alignment, residue mapping,
RMSD, per-residue displacement, contacts, pocket membership, confidence
summaries, density thresholds, and other scientific metrics before Story build.
Then bind their frozen values, selectors, transforms, annotations, or primitive
coordinates into the source.

For a rigid alignment, record the reference/mobile identity, atom selection,
matched count, RMSD, transform, and hashes. Transform the whole mobile complex,
including its ligand and partners, into the reference frame; never move only the
receptor while leaving bound objects behind.

## Author The Argument

Use one scene per bounded review question. Each description must state:

1. the question;
2. the frozen observation or measurement;
3. the structural interpretation;
4. the decision, next action, or claim boundary.

Assign each major scene a claim ID and trace that claim to one or more retrieved,
reported, or computed evidence IDs. Bundle the ledger with the trusted Story
source. A scene without supporting evidence must be labeled as context,
hypothesis, or unresolved rather than presented as a result.

Apply the question-coverage and information-density gates in
`story-archetypes.md`: every material subquestion must be answered or explicitly
bounded, every mechanism edge must be evidenced or exposed as a gap, and every
scene must advance evidence, comparison, decision, or a material boundary. More
scenes do not make an incomplete argument complete.

Keep state colors, residue-numbering semantics, camera, and omissions stable
across comparisons. Preserve heteroatom element colors for chemistry while using
carbon color for state or residue identity. Show selected residues as complete
heavy-atom residues with fold context, not floating side chains.

Treat responsiveness as part of scientific usability. Build delivery coordinates
from only the models, chains, ligands, partners, maps, and solvent that a scene
actually consumes, while retaining the authoritative full inputs and recording
the extraction rule and hashes. Do not use several translucent whole structures
as the default context: opacity does not remove parse, representation, sorting,
or draw cost. Prefer an opaque decision-relevant view and reserve a dual-state
overlay for the scene that actually asks a comparison question.

Use a lightweight illustrative default for ordinary protein Stories: clear
cartoons/sticks, flat lighting or illustrative coloring, and outline when it
improves separation. Leave SSAO, bloom, shadow, depth-of-field, and dense
transparent surfaces off unless the question requires them and the accepted
viewer remains responsive.

Transitions and arrows can explain two observed endpoints but do not establish a
physical pathway or causality. Say so whenever a viewer could infer motion from
an interpolation or displacement vector.

## Build

Treat Story JavaScript as trusted executable input. Replace every `REPLACE_`
marker, add the exact local assets, and build with the maintained wrapper:

```bash
python3 scripts/build_molstar_story.py path/to/story_source path/to/story \
  --mol-view-stories-repo path/to/pinned/mol-view-stories \
  --deno path/to/deno --deno-dir path/to/persistent-deno-cache \
  --name state_comparison
```

The wrapper accepts only its pinned MolViewStories commit and Mol* version. Its
routine output is an editable `.mvstory`, directly file-openable single HTML,
and provenance manifest. Use `--full-package` only when MVSX or an HTTP-served
self-hosted viewer is actually required.

If Deno, Playwright, NumPy, or the pinned checkout is missing, install the named
dependency explicitly and record the resulting version; do not silently change
the runtime, pin, or analysis method.

## Accept The Story

A successful build is not a scientific or browser acceptance result.

1. Reconcile source identity, candidate selection, claim/evidence links,
   mechanism-edge and question coverage, selectors, transforms, measurements,
   text, and omissions against the frozen evidence.
2. Run the file-openable Story offline and capture the prescribed scenes. The
   checker waits for the selected scene's live camera to converge and for the
   rendered canvas to remain stable after representation work; do not replace
   those criteria with a larger fixed sleep:

   ```bash
   python3 scripts/check_story.py path/to/story_file_openable.html \
     --output-dir path/to/qa/story --expected-scenes N \
     --scene-settle-ms 12000 --chromium-software-webgl
   ```

3. Inspect the initial and decision scenes plus every distinct selector,
   transform, geometry, or chemistry rule. Inspect all scenes when qualifying a
   new template, runtime, transport, or scene type.
4. Confirm nonblank WebGL, correct identity/focus/colors, and at least one
   rotate/zoom/pick interaction. Record initial and per-scene settle time when a
   user reports lag or when several structures, transparent surfaces, maps, or
   large assemblies are present. The checker proves transport and rendering
   observables, not that the selected atoms or scientific interpretation are
   correct.
5. Report the Story's actual conclusion, quantitative evidence, caveats, runtime
   versions, and acceptance status; do not substitute artifact paths for the
   result.
