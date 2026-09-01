# Story Authoring And Acceptance

## Artifact Roles

Keep these roles distinct:

| Role | Typical artifact | Meaning |
|---|---|---|
| Authoritative input | PDB, mmCIF, map, analysis table | Source evidence; never superseded by the Story |
| Derived spatial evidence | aligned coordinates, annotations, metrics JSON/TSV | Reproducible analysis bound into scenes |
| Editable Story | source tree and `.mvstory` | Trusted JavaScript, narrative, scenes, metadata, assets |
| Read-only viewer state | `.mvsx` or `.mvsj` | Executed MolViewSpec snapshots |
| Interactive delivery | `*_file_openable.html` or self-hosted viewer | Reviewer-facing scene sequence |

Expose conflicts rather than silently making the Story agree with the prose.

## Plan Scenes Around Questions

A useful Story normally moves from context to discriminating evidence and then a
decision, but the question determines the actual sequence. Examples:

- ligand review: assembly context -> pocket enclosure -> chemical zones ->
  decision-driving residues -> next action;
- conformational comparison: provenance -> state A -> state B/ligand -> aligned
  overlay -> localized displacement -> decision;
- interface review: assembly identity -> interface overview -> hotspot/contact
  geometry -> counterexample or failure -> decision;
- density review: model/map identity -> global fit -> local disputed region ->
  threshold sensitivity -> claim boundary.

One scene answers one bounded question. Prefer one Story with purposeful scenes
over many simultaneous canvases. For a large candidate set, select
decision-relevant representatives upstream (best, near-pass, trade-off, anomaly,
failure, counterexample) and account for lineage/fanout; do not use random
sampling merely to reduce viewer load.

Every scene description should contain a question, observation, interpretation,
and decision or boundary. State visual encodings once. Text that only says
"cartoon is blue and ligand is sticks" is not a scientific scene.

Assign each major scene a claim ID, trace every claim to retrieved, reported, or
computed evidence IDs, and bundle the claim/evidence ledger with the trusted
Story source. Label unsupported scenes as context, hypothesis, or unresolved.

Before authoring, apply the composition and coverage rules in
`story-archetypes.md`. For a mechanism Story, verify that the sequence follows a
directed evidence chain rather than merely placing interesting structures in a
biological order. An unsupported edge remains visible as a gap.

Pass an information-density gate for each proposed scene. Keep it only if it
introduces discriminating evidence, performs a decision-relevant comparison, or
closes/bounds a material question. Merge pure orientation or style-change scenes
with the next evidence scene unless orientation itself establishes identity,
assembly, numbering, provenance, or another decision-critical fact. Information
density does not mean visual clutter or multiple unrelated claims in one view.

## Keep View Changes Continuous

Treat camera movement and representation replacement as part of the argument,
not decoration. Keep the camera up vector and viewing direction stable across
adjacent scenes, and avoid changing camera scale, structure identity, and dense
representations all at once. For a comparison sequence, prefer one overview
camera and one shared detail camera over repeated overview-to-extreme-close-up
round trips.

Keep representations that recur across adjacent scenes in the same builder call
order with explicit, stable `ref` values. This is a continuity tool, not a demand
for identical complete state trees. An opacity node at zero still leaves the
coordinates and representation in the snapshot and may still incur parsing,
representation, transparent-pass, sorting, or draw work. Keep a small recurring
visual at zero opacity when a verified transition benefits; omit or pre-filter
an expensive inactive structure when responsiveness matters more. Inspect the
actual transition rather than treating topology identity as acceptance.

Prefer opaque primary evidence. Use fractional opacity only when seeing through
or comparing overlapping objects answers the current question, and normally
limit full-structure translucency to one deliberate overlay scene. A faint
ghost that persists through every scene is neither free context nor a substitute
for a well-framed camera.

Use a short explicit camera duration (the maintained templates use 250 ms) and
inspect at least one midpoint rather than only settled endpoints. Mol* 5.8.0
advances camera interpolation on capped animation-loop `properTime`; under low
frame-rate software WebGL, a longer nominal duration can stretch into many
seconds of wall time rather than making the transition feel smoother.

Write `linger_duration_ms` and `transition_duration_ms` explicitly on every
inline scene. The pinned MolViewStories CLI reports `scene_defaults` but does not
apply it to inline scenes, so the maintained builder rejects that misleading
configuration. These transitions interpolate viewer states; they do not show a
physical molecular pathway.

For browser acceptance, do not infer convergence from a fixed sleep. For an
explicit camera, compare the live camera snapshot with the selected target and
wait until position, target, and up-vector error is below tolerance. For a
focus-derived camera without an explicit target snapshot, require repeated
stable camera samples instead. In both cases require Mol* not to be busy. A
screenshot taken at the nominal transition duration can still be an
intermediate frame on software WebGL.

Camera convergence is necessary but not sufficient: Mol* representation work
can continue after the camera and `isBusy` signal appear settled. Require stable
successive canvas digests after a short render grace period, and capture the
last proven-stable frame. A visible task-progress overlay or changing canvas is
an acceptance failure even when the target camera has converged.

## Budget Delivery Assets And Rendering

Keep authoritative coordinates unchanged upstream. For the interactive package,
derive and record the smallest presentation subset that preserves every scene
selector and claim: exact models, biological-assembly instances, chains,
ligands, partners, relevant solvent/ions, and maps. Remove duplicate crystal
copies, bulk waters, detergents, lipids, glycans, or fusion partners only when no
scene or claim consumes them. Record the subset rule, source hash, output hash,
and retained atom/entity counts so performance pruning cannot silently change
the evidence.

Use the renderer budget in this order:

1. prune unused coordinate and map content;
2. render only the decision-relevant representation for the scene;
3. prefer cartoon/backbone and sticks over broad transparent surfaces;
4. use lightweight illustrative coloring/flat lighting and outline;
5. enable SSAO, bloom, shadow, depth-of-field, or dense transparency only when
   they answer the question and pass interaction/settle-time acceptance.

When lag is reported, compare the accepted artifact before and after on the same
browser path and viewport. Record atom/asset size, HTML size, per-scene stable
canvas wait, and a rotate/zoom interaction. Do not infer responsiveness from a
successful build or from a static screenshot.

## Preserve Scientific Meaning

- Load exact accepted local assets and verify model, assembly, chain, ligand/CCD,
  residue numbering, insertion codes, and altloc policy.
- Compute alignment and measurements upstream. Bake aligned coordinates or bind
  the frozen rigid transform; never let browser code choose the evidence.
- Apply a mobile-state transform to its complete complex, including ligand,
  cofactors, and partners.
- Report the alignment selection, matched atom count, RMSD, transform, and
  source/derived hashes. Similar scalar scores do not establish structural
  equivalence.
- Keep paired states in a common camera and coordinate frame when judging
  apparent displacement. State hidden chains or atoms.
- Use carbon color for state, route, or chemical-zone identity while retaining
  element colors for N/O/S/halogens. Uniform whole-object color is appropriate
  for deliberate state identity, not ligand chemistry by default.
- Select complete heavy-atom residues and retain surrounding cartoon context.
  Split dense pockets into meaningful zones rather than showing every contact
  stick simultaneously.
- Put already-computed distances, axes, displacement vectors, and labels into
  primitives. A rendered line does not validate the underlying atom mapping or
  measurement.
- A transition is interpolation between snapshots, not a molecular trajectory.
  Avoid it or label the limitation when that distinction matters.

## Use Public MolViewSpec Surfaces

Prefer public builder nodes: `download`, `parse`, `modelStructure` or
`assemblyStructure`, `transform`, `component`, `representation`, `color`,
`opacity`, `label`, `tooltip`, `focus`, `camera`, `canvas`, `primitives`, and the
volume/annotation nodes documented for the pinned version.

Do not reach for private Mol* `StateTransforms` or viewer internals when a public
MolViewSpec node expresses the view. Route unfamiliar capabilities through
`documentation-router.md` and verify the current public example or schema before
coding.

## Package Deliberately

### File-openable HTML: routine default

The maintained wrapper builds an HTML file with embedded MVS data and embedded,
version-pinned Mol* runtime. Test that exact file through ordinary `file://` with
network access blocked. A filename or HTTP-served success does not prove offline
operation.

Routine output also retains `.mvstory` and `build_manifest.json`; it omits MVSX,
self-hosted ZIP, and HTTP viewer. Reuse the pinned checkout and persistent
`DENO_DIR` cache across builds.

### Full package: explicit only

Use `--full-package` when the contract requires MVSX or self-hosting. The
self-hosted viewer loads `data.mvsx` by URL and should be served over HTTP.
Opening its `index.html` by `file://` is a known CORS failure mode. The wrapper's
separate file-openable HTML remains the double-click/offline entry point.

The upstream default `StoryManager.toHTML()` normally references versioned CDN
assets. A single file is not offline unless runtime and Story data are actually
embedded and the network-blocked file check passes.

Publishing to a remote Story service is optional and externally mutating. Do not
upload, create accounts, or make a published URL the sole review surface without
explicit authorization.

## Accept At The Right Depth

For routine rebinding of an already-qualified template/runtime/transport:

1. reconcile question coverage, mechanism edges, identities, selectors,
   measurements, transforms, and conclusions;
2. open the initial and decision scenes plus one scene per distinct binding rule
   or geometry;
3. verify nonblank WebGL, focus, colors, one rotate/zoom/pick, and no unexpected
   requests or runtime errors.

Run all scenes and desktop+narrow inspection when a template, runtime, transport,
selector family, primitive, volume, alignment method, or layout changes, or when
a real defect appears. If editable import or HTTP self-hosting is advertised,
qualify that advertised path too.

`check_story.py` records offline transport, visible scene navigation, screenshots,
canvas variation, WebGL, requests, and runtime errors. It cannot prove that the
correct atoms are displayed, that a measurement is valid, or that the narrative
claim follows. Manual evidence reconciliation remains mandatory.

## Optional Downstream Embedding

Another deliverable may embed the file-openable HTML in a titled responsive
iframe and link the authoritative coordinates, metrics, and `.mvstory`. Use only
relative local URLs inside the portability root. Keep the Story independently
openable; the parent page is navigation, not a second scientific truth source.
