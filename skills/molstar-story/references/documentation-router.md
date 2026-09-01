# Official Documentation Router

Use this index to retrieve the smallest authoritative source needed for the
current Story. Do not preload or copy the whole manual into the task context.

## Version Boundary

The maintained builder pins:

- MolViewStories commit `6edd08a0be4663a3431ae4f9d394e97a0908fd09`;
- MolViewStories CLI `1.0.0-dev10`;
- Mol* `5.8.0`.

At the time this router was written, that MolViewStories commit was also upstream
`HEAD`, but always verify live state before claiming it is current:

```bash
git ls-remote https://github.com/molstar/mol-view-stories.git HEAD
git -C path/to/mol-view-stories rev-parse HEAD
cat path/to/mol-view-stories/cli/deno.json
```

Use current web docs to understand capabilities, then verify exact syntax against
the pinned checkout used for the build. The pages `reference-api` and
`reference-advanced` explicitly label themselves work in progress; prefer the
MolViewSpec tree/schema, focused pages, and working pinned examples when they
conflict.

## Route By Need

| Need | Official page | Pinned source or example to inspect |
|---|---|---|
| Story folder layout, settings, scenes, CLI formats | <https://molstar.org/mol-view-stories/cli.html> | `docs/cli.qmd`, `cli/README.md`, `cli/main.ts` |
| Story UI authoring and preview | <https://molstar.org/mol-view-stories/getting-started.html> and <https://molstar.org/mol-view-stories/core-features.html> | `docs/getting-started.qmd`, `docs/core-features.qmd` |
| Complete public MVS node hierarchy | <https://molstar.org/mol-view-stories/molviewspec/> and <https://molstar.org/mol-view-spec-docs/> | `docs/molviewspec/index.qmd`; Mol* `src/extensions/mvs/tree/mvs/mvs-tree.ts` and `mvs-builder.ts` |
| Chains, residues, atoms, auth vs label numbering, unions | <https://molstar.org/mol-view-stories/molviewspec/selectors.html> | `docs/molviewspec/selectors.qmd`, `cli/examples/learning-mvs-features/scenes/component-*` |
| External or mmCIF annotations for color/component/label/tooltip | <https://molstar.org/mol-view-stories/molviewspec/annotations.html> | `docs/molviewspec/annotations.qmd`, `cli/examples/learning-mvs-features/scenes/annotations*` |
| Camera, focus, canvas, shared comparison views | <https://molstar.org/mol-view-stories/molviewspec/camera.html> | `docs/molviewspec/camera.qmd`, `cli/examples/learning-mvs-features/scenes/camera` |
| Arrows, distances, axes, shapes, text | <https://molstar.org/mol-view-stories/molviewspec/primitives.html> | `cli/examples/learning-mvs-features/scenes/primitives/primitives.js`, `cli/examples/motm-01/scenes/scene5/scene5.js` |
| Density or cryo-EM/X-ray maps | <https://molstar.org/mol-view-stories/molviewspec/volumes.html> | `docs/molviewspec/volumes.qmd`, `cli/examples/learning-mvs-features/scenes/volumes*` |
| Animation or interpolation | <https://molstar.org/mol-view-stories/molviewspec/animations.html> | `docs/molviewspec/animations.qmd`, `cli/examples/learning-mvs-features/scenes/animations` |
| Multiple structures and frozen rigid transforms | <https://molstar.org/mol-view-stories/molviewspec/examples.html> | `cli/examples/alphafind/scenes/structural-alignment/`, `cli/examples/cyp3a4/story.js` |
| Full scientific Story example | <https://molstar.org/mol-view-stories/example-stories/making-of-cyp3a4.html> | `cli/examples/cyp3a4/` |
| `.mvstory`, HTML, MVSJ/MVSX, self-hosted behavior | <https://molstar.org/mol-view-stories/webapp-cloud-storage.html> | `@mol-view-stories/lib/src/story-manager.ts`, `html-template.ts` |
| Runtime/build failures | <https://molstar.org/mol-view-stories/faq-troubleshooting.html> | `docs/faq-troubleshooting.qmd`, CLI error plus `cli/deno.lock` |
| Mol* core architecture or an undocumented MVS behavior | <https://github.com/molstar/molstar> | Use DeepWiki for `molstar/molstar`, then verify the named source path in the matching Mol* version |

If the MolViewStories repository is unavailable through DeepWiki, query its
official current web docs and pinned Git checkout directly rather than
substituting an ungrounded summary.

## Capability Boundary

MolViewSpec can declaratively load structures and volumes; choose models and
assemblies; select components; render and color representations; apply opacity,
labels, tooltips, cameras, focus, and canvas settings; apply a supplied rigid
transform; consume annotations; and draw primitives.

It does not establish residue correspondence, choose a scientifically valid
alignment core, compute RMSD, contacts, per-residue displacement, pocket
membership, state causality, map thresholds, or statistical conclusions. Compute
those upstream and bind their frozen outputs.

## Query Procedure

When a needed capability is absent or uncertain:

1. Open the focused official page in the table.
2. Search the pinned checkout for the exact public builder method and one working
   example; inspect its YAML/JS together.
3. For Mol* core questions, ask DeepWiki about `molstar/molstar` and require exact
   public paths/type names, then verify against Mol* `5.8.0`.
4. Prefer public MolViewSpec nodes. Do not use private viewer state transforms as
   a shortcut.
5. If the pin lacks the needed public capability, report the limitation before
   proposing a runtime upgrade. Do not silently change the pin or backend.
