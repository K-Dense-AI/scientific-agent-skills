<!-- Source: https://github.com/SuperiorByteWorks-LLC/agent-project | License: Apache-2.0 | Author: Clayton Young / Superior Byte Works, LLC (Boreal Bytes) -->

# Radar Chart

> **Back to [Style Guide](../mermaid_style_guide.md)** — Read the style guide first for emoji, color, and accessibility rules.

**Syntax keyword:** `radar-beta`
**Mermaid version:** v11.6.0+
**Best for:** Multi-dimensional comparisons, skill assessments, performance profiles, competitive analysis
**When NOT to use:** Time series data (use [XY Chart](xy_chart.md)), simple proportions (use [Pie](pie.md))

> **Accessibility:** Mermaid 12.0.0 emits `accTitle`/`accDescr` for this type. Keep a visible description and verify older destination renderers.

---

## Exemplar Diagram

_Radar chart comparing two engineering candidates across six core competency areas, showing complementary strengths:_

```mermaid
radar-beta
    accTitle: Radar Example
    accDescr: Illustrative radar diagram; the surrounding text describes its data and relationships.
    title Team Skill Assessment
    axis sys["System Design"], algo["Algorithms"], comms["Communication"], team["Teamwork"], ops["DevOps"], acq["Domain Knowledge"]
    curve candidate_a["Candidate A"]{4, 3, 5, 5, 2, 3}
    curve candidate_b["Candidate B"]{2, 5, 3, 3, 5, 4}
    max 5
    graticule polygon
    ticks 5
    showLegend true
```

---

## Tips

- Define axes with `axis id["Label"]` — use short labels (1–2 words)
- Define curves with `curve id["Label"]{val1, val2, ...}` matching axis order
- `max` sets the displayed radial limit; it does not normalize data. Convert unlike units to a justified common scale before plotting, declare direction (higher/lower is better), and provide the exact data table
- `graticule` options: `circle` (default) or `polygon`
- `ticks` controls the number of concentric rings (default 5)
- `showLegend true` adds a legend for multiple curves
- Keep to **5–8 axes** and **2–4 curves** for readability
- **Always** pair with a Markdown text description above for screen readers

---

## Template

_Description of what dimensions are being compared across which entities:_

```mermaid
radar-beta
    accTitle: Radar Example
    accDescr: Illustrative radar diagram; the surrounding text describes its data and relationships.
    title Your Radar Title
    axis dim1["Dimension 1"], dim2["Dimension 2"], dim3["Dimension 3"], dim4["Dimension 4"], dim5["Dimension 5"]
    curve series_a["Series A"]{3, 4, 2, 5, 3}
    curve series_b["Series B"]{5, 2, 4, 3, 4}
    max 5
    showLegend true
```


## Verified reference

Syntax examples reviewed against [official Mermaid documentation](https://mermaid.js.org/syntax/radar.html) and rendered with Mermaid 12.0.0 (2026-10-01). Check the destination version; appearance and accessibility are not guaranteed by a successful parse.
