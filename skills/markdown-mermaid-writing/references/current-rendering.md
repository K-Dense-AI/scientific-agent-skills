# Current rendering and validation

Reviewed 2026-10-01 with Mermaid **12.0.0**, Mermaid CLI **12.0.0**, and
`@mermaid-js/mermaid-zenuml` **1.0.1** in Chromium. Local success is not evidence
that a hosted Markdown renderer uses these versions.

## Check the destination first

GitHub's [diagram guide](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)
documents a fenced `mermaid` block containing `info` to show the installed version.
Run that probe in the intended preview; do not assume every GitHub surface, editor,
notebook, or static-site generator has identical support. A Markdown fence labels
source code; CommonMark itself does not execute Mermaid.

The bundled guides cover 23 diagram types and one composition pattern collection.
They are illustrative syntax examples, not current application/provider API contracts.
The [`-beta` keywords](https://mermaid.js.org/intro/) used here still render in 12.0.0;
experimental types can change. Prefer a supported simpler diagram or export an SVG/PNG
with meaningful alt text when a destination cannot render the chosen syntax.

## Version and configuration changes

[Mermaid 12 release notes](https://github.com/mermaid-js/mermaid/releases/tag/mermaid%4012.0.0)
describe an ES2024 build (Node 22.12+; Safari 17.4+), bundled ELK layout, and new
default appearance for several diagram types. CLI 12 requires **Node 22.13+**.
Retest layout, wrapping, arrow direction, and contrast when upgrading.

For a deliberately classic local rendering, save `mermaid-config.json`:

```json
{
  "layout": "dagre",
  "theme": "default",
  "look": "classic",
  "securityLevel": "strict"
}
```

Use top-level `layout`; `flowchart.defaultRenderer`, `class.defaultRenderer`, and
`state.defaultRenderer` no longer choose an engine. Use top-level `htmlLabels`
when needed, not the deprecated `flowchart.htmlLabels` field. These options are
host-controlled in many integrations; a file cannot override every host setting.

[`%%{init: ...}%%` directives are deprecated](https://mermaid.js.org/config/directives.html)
since 10.5. Prefer a `config` mapping in Mermaid's diagram frontmatter or the
host's initialization settings. This is separate from the outer Markdown file's
frontmatter. Custom `style` and `classDef` rules are valid for types that implement
them; neither guarantees readable dark-mode colors. Do not disable strict security
just to make a diagram render.

## Local CLI export

The [official CLI](https://github.com/mermaid-js/mermaid-cli) supports SVG, PNG, PDF,
and Markdown conversion. In a disposable preview directory:

```bash
npm install --save-dev --save-exact @mermaid-js/mermaid-cli@12.0.0
npx mmdc --version
npx mmdc -i diagram.mmd -o diagram.svg -c mermaid-config.json
npx mmdc -i diagram.mmd -o diagram-dark.png -t dark -b transparent
npx mmdc -i report-source.md -o report-rendered.md
```

Put the Mermaid body, without Markdown fences, in `diagram.mmd`. Keep
`report-source.md`: Markdown conversion writes a separate document containing image
links and adjacent numbered SVGs. Preserve the lockfile for reproducible dependency
versions. Inspect both the exported file and the final document at its intended size.

Puppeteer needs a compatible Chrome/Chromium. Installation may download one. To use
an existing supported browser, set `PUPPETEER_SKIP_DOWNLOAD=true` when installing,
then supply its executable using `PUPPETEER_EXECUTABLE_PATH` or a Puppeteer JSON file
via `-p`. Local verification used an installed Chrome rather than downloading another
browser. Browser availability and fonts remain environment-specific.

## Browser embedding and parse contract

[Mermaid's current API](https://mermaid.js.org/config/usage.html) uses promises.
`parse()` validates syntax; it does not validate scientific meaning or layout.
A successful parse returns an object containing `diagramType`, not boolean `true`.
With `{suppressErrors: true}`, invalid input returns `false`; otherwise it throws.

Example HTML for a page you control (requires CDN access):

```html
<!doctype html>
<html lang="en">
<body>
  <pre class="mermaid">
flowchart LR
    accTitle: Analysis Workflow
    accDescr: Input data pass through quality checks before analysis.
    input["Input data"] --> qc["Quality checks"] --> analysis["Analysis"]
  </pre>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@12.0.0/dist/mermaid.esm.min.mjs';
    mermaid.initialize({startOnLoad: false, securityLevel: 'strict'});
    await document.fonts.ready;
    await mermaid.run({querySelector: '.mermaid'});
  </script>
</body>
</html>
```

For programmatic output, `await mermaid.render(uniqueId, source)` returns
`{svg, bindFunctions}`. Insert the SVG into the intended container, then call
`bindFunctions?.(container)` if the diagram uses supported interactions. Use a unique
ID per rendered diagram. `mermaid.init` is deprecated; use `run` for DOM scanning.
Do not treat arbitrary HTML from another source as trusted output.

ZenUML requires a separately registered module in a custom browser integration:
`await mermaid.registerExternalDiagrams([zenuml])` after importing the compatible
plugin. CLI 12 registers it itself. The two bundled ZenUML examples rendered with
plugin 1.0.1; this does not establish support in GitHub or every editor.

## Accessibility: inspect the output, not only parsing

Current checks inserted distinct `accTitle` and `accDescr` strings, rendered SVG,
and inspected its `<title>`/`<desc>`. Results apply to the tested versions:

| Types | Result / action |
| --- | --- |
| Flowchart, sequence, class, state, ER, gantt, pie, git graph, journey, requirement | Both SVG metadata fields emitted |
| Quadrant, XY, architecture, packet, radar, treemap | Both emitted in 12.0.0; older host versions require checking |
| Block, kanban, mindmap, Sankey | Do not insert those annotations; use a visible description and export alt text |
| Timeline | Input accepted, but tested SVG omitted both metadata fields; provide a text alternative |
| C4 | Tested SVG omitted the accessible title; retain a visible description and inspect export metadata |
| ZenUML | Plugin-specific; use a visible text alternative and inspect the output |

See [official accessibility syntax](https://mermaid.js.org/config/accessibility.html).
`accDescr: ...` is single-line; multiline descriptions use `accDescr { ... }`.
A valid annotation does not prove screen-reader usability in an embedded host.
Keep a concise visible explanation and a data table when exact values matter.

## Scientific review before delivery

- Distinguish workflow order, statistical association, and causation in arrow labels.
  An inferred or proposed connection must not look like an established result.
- Preserve units, denominators, uncertainty, and data provenance. Radar `max` controls
  the axis bound; it does not normalize unlike measures. A shared Y-axis requires
  commensurate units. Use plotting tools for error bars, scatter data, or exact geometry.
- Check totals and relationships: Sankey internal flows should balance when the modeled
  quantity is conserved; pie/treemap values must form meaningful nonnegative parts;
  ER cardinalities and identifying relationships must match actual constraints.
- Gantt `crit` is a manual tag, not a computed critical path. Journey diagrams assign
  one score to each task row, shared by its listed actors. Diagram rendering does not
  verify a scientific or engineering claim.
- Label example/synthetic values prominently, and remove placeholders before delivery.
  A citation must actually support its claim; never cite a paper as evidence for invented
  measurements or unexecuted software results.
