# Sources and Version Snapshot

Reviewed 2026-10-01 using official documentation, release source, current PyPI metadata, native synthetic fixtures, and fresh extraction for blocked publisher pages. Science remains a historical snapshot because both retrieval routes failed. ACS is an explicitly dated legacy page, not a current journal rule. No submission, authentication, or publication API is called by these network-free tools.

## Tested direct package snapshot

- **Matplotlib 3.11.2**, Python >=3.11 [MPL-PYPI].
- **Seaborn 0.13.2**, Python >=3.8 [SEABORN-PYPI].
- **Plotly 7.1.0**, Python >=3.8 [PLOTLY-PYPI].
- **Kaleido 1.4.0**, Python >=3.8; compatible Chrome/Chromium required [KALEIDO-PYPI].
- **Pillow 12.3.0**, Python >=3.10 [PIL-PYPI].
- **pypdf 6.19.0**, Python >=3.9 [PYPDF-PYPI].

Native tests use Python 3.13, synthetic data, and local Matplotlib/Pillow/pypdf outputs. Plotly HTML and Kaleido exports are checked separately; the isolated baseline manifest does not install optional Kaleido. These direct pins are not a transitive lock. GUI, TeX/PGF, optional Cairo, color-managed printing, authenticated journal submission, and arbitrary external-asset rendering are not established by these checks.

## Matplotlib

- **[MPL-PYPI]** [matplotlib on PyPI](https://pypi.org/project/matplotlib/) — current package version and release history.
- **[MPL-RELEASE]** [Matplotlib release notes](https://matplotlib.org/stable/release/release_notes.html) — 3.11 release/API changes.
- **[MPL-SAVE]** [`matplotlib.figure.Figure.savefig`](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html) — 3.11.2 signature; format inference, DPI, metadata, bounding boxes, transparency, backends, Pillow kwargs.
- **[MPL-BACKENDS]** [Backends](https://matplotlib.org/stable/users/explain/figure/backends.html) — interactive versus static renderers; PDF/PS/SVG/PGF/Cairo formats.
- **[MPL-STYLE]** [Customizing Matplotlib with style sheets and rcParams](https://matplotlib.org/stable/users/explain/customizing.html) — `rc_context`, style composition, save settings, PDF/PS/SVG font types.
- **[MPL-LAYOUT]** [Constrained layout guide](https://matplotlib.org/stable/users/explain/axes/constrainedlayout_guide.html) — `layout="constrained"`, colorbars, subfigures, GridSpec, interaction with `tight_layout`.
- **[MPL-GRIDSPEC]** [`matplotlib.gridspec`](https://matplotlib.org/stable/api/gridspec_api.html) — current grid layout API.
- **[MPL-NORM]** [Colormap normalization](https://matplotlib.org/stable/users/explain/colors/colormapnorms.html) — `Normalize`, `LogNorm`, `CenteredNorm`, `SymLogNorm`, `PowerNorm`, `BoundaryNorm`, `TwoSlopeNorm`.
- **[MPL-CMAP]** [Choosing colormaps](https://matplotlib.org/stable/users/explain/colors/colormaps.html) — data classes and perceived lightness.

## Seaborn

- **[SEABORN-PYPI]** [seaborn on PyPI](https://pypi.org/project/seaborn/) — 0.13.2 package metadata and release history.
- **[SEABORN-ERROR]** [Statistical estimation and error bars](https://seaborn.pydata.org/tutorial/error_bars.html) — current `errorbar` methods, callable intervals, bootstrapping, `seed`, and `n_boot`.
- **[SEABORN-FAQ]** [Frequently asked questions](https://seaborn.pydata.org/faq.html) — axes-level versus figure-level functions, Matplotlib object-oriented integration, DPI/SVG notes.
- **[SEABORN-PALETTE]** [Choosing color palettes](https://seaborn.pydata.org/tutorial/color_palettes.html) — qualitative, sequential, and diverging palette APIs.
- **[SEABORN-THEME]** [`seaborn.set_theme`](https://seaborn.pydata.org/generated/seaborn.set_theme.html) — style, context, palette, font, scale, and rc parameters.

## Plotly and Kaleido

- **[PLOTLY-PYPI]** [plotly on PyPI](https://pypi.org/project/plotly/) — 7.1.0 package metadata.
- **[PLOTLY-STATIC]** [Static image export in Python](https://plotly.com/python/static-image-export/) — Kaleido/Chrome setup, formats, `write_image`, `write_images`, dimensions/scale, WebGL rasterization, offline assets, defaults, EPS/Orca/engine deprecations; page dated 2026.
- **[PLOTLY-HTML]** [Interactive HTML export](https://plotly.com/python/interactive-html-export/) — `write_html`, `to_html`, `include_plotlyjs`, `full_html`; page dated 2026.
- **[PLOTLY-CHANGES]** [Static image generation changes in Plotly.py 6.1](https://plotly.com/python/static-image-generation-changes/) — Kaleido v1 migration and deprecations.
- **[KALEIDO]** [Plotly Kaleido repository](https://github.com/plotly/Kaleido) — Chrome requirement, v1 migration, direct APIs, and offline/page behavior.
- **[KALEIDO-PYPI]** [kaleido on PyPI](https://pypi.org/project/kaleido/) — 1.4.0 package metadata.

- **[PLOTLY-7]** [Plotly 7.0 release](https://github.com/plotly/plotly.py/releases/tag/v7.0.0) — removal of Orca, Kaleido v0, and `engine`; MathJax 2 removal and Share Chart button.
- **[KALEIDO-14]** [Kaleido 1.4 release](https://github.com/plotly/Kaleido/releases/tag/v1.4.0) — MathJax default moves to v3.

## Accessibility and color

- **[WCAG22]** [Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/) — W3C Recommendation; normative SC 1.1.1, 1.4.1, 1.4.3, 1.4.5, and 1.4.11.
- **[WCAG-NONTEXT]** [Understanding SC 1.4.11: Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) — informative chart/graph examples and testing principles; not itself normative.
- **[WCAG-COLOR]** [Understanding SC 1.4.1: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) — informative non-color cue guidance.
- **[COLORBREWER]** [ColorBrewer 2.0](https://colorbrewer2.org/) — Cynthia Brewer, Mark Harrower, and Penn State; scheme type, data-class count, colorblind/print/photocopy filters, and exports.
- **[TOL-HOME]** [Paul Tol’s Notes](https://sronpersonalpages.nl/~pault/) — canonical site; page states the move from SRON on 2026-07-07.
- **[TOL]** [Paul Tol, “Colour Schemes”](https://sronpersonalpages.nl/~pault/data/colourschemes.pdf) — SRON/EPS/TN/09-002, issue 3.2, 2021-08-18; exact sRGB palettes, intended uses, color-vision checks, and grayscale analysis.
- **[WONG]** [Bang Wong, “Color blindness”](https://www.nature.com/articles/nmeth.1618) — Nature Methods 8, 441 (2011); source commonly used for the eight-color palette.

## Publishers and journals

Most publisher content was verified 2026-10-01. Nature final submission and Cell Press needed fresh extraction after direct access failed. Science initial/revised pages remained blocked; their 2026-07-23 values are explicitly historical. ACS is a legacy source updated 2006-01-21. Dates label access separately from publication dates.

- **[NATURE-FINAL]** [`Nature` final submission](https://www.nature.com/nature/for-authors/final-submission) — flagship final files, dimensions, fonts, formats, raster resolution, RGB/CMYK, Extended Data distinctions.
- **[NATURE-FIG]** [`Nature` research figure specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications) — graphs, accessibility, RGB, 300/450 dpi discussion, editable Type 42 text, export.
- **[SCIENCE-INITIAL]** [`Science` initial manuscript instructions](https://www.science.org/content/page/instructions-preparing-initial-manuscript) — historical snapshot: initial figure embedding, 300 dpi, widths, fonts, color/contrast, source data.
- **[SCIENCE-REVISED]** [`Science` revised manuscript instructions](https://www.science.org/content/page/instructions-preparing-revised-manuscript) — historical snapshot: separate files, formats, minimum resolution, dimensions, no upsampling.
- **[CELL-FIG]** [Cell Press figure guidelines](https://www.cell.com/information-for-authors/figure-guidelines) — initial versus final stages, formats, widths, file size, DPI, RGB, fonts, image integrity, AI-assisted image policy.
- **[PLOS-FIG]** [PLOS Computational Biology figures](https://journals.plos.org/ploscompbiol/s/figures) — provisional-accept waiver, TIFF/EPS, dimensions, 300-600 dpi, RGB/grayscale, file size, image integrity, 2026-04-01 blot/gel requirement.
- **[ELSEVIER-FORMAT]** [Elsevier artwork formats checklist](https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-formats-checklist) — general formats, RGB preference, separate files, journal override.
- **[ELSEVIER-SIZE]** [Elsevier artwork sizing](https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-sizing) — general widths, 300/500/1,000 dpi, typography, and explicit journal variability.
- **[IEEE-SIZE]** [IEEE Resolution and Size](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/) — modified 2025-02-25; PS/EPS/PDF, >300/>600 dpi, 88.9/182 mm.
- **[BMC-BIOINFO]** [BMC Bioinformatics: preparing your manuscript](https://link.springer.com/journal/12859/submission-guidelines) — journal-specific formats, 85/170 mm, approximately 300 dpi, 10 MB, embedded fonts.
- **[ACS-GRAPHICS]** [ACS Preparing Manuscript Graphics](https://pubsapp.acs.org/paragonplus/submission/general/graphics_prep.html) — legacy dimensions/typography, page updated 2006-01-21; target-journal rules govern.

## Optional inspection backends

- **[PIL-PYPI]** [Pillow on PyPI](https://pypi.org/project/Pillow/) — 12.3.0 package metadata; released 2026-07-01.
- **[PYPDF-PYPI]** [pypdf on PyPI](https://pypi.org/project/pypdf/) — 6.19.0 package metadata.

- **[PIL-IMAGE]** [Pillow Image API](https://pillow.readthedocs.io/en/stable/reference/Image.html) — lazy open, verify versus decoding, channel conversion, pixel limits.
- **[PIL-TIFF]** [Pillow TIFF format](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#tiff) — LZW compression, DPI, ICC, multiple frames.
- **[PYPDF-PAGE]** [pypdf PageObject](https://pypdf.readthedocs.io/en/stable/modules/PageObject.html) — `user_unit`, `rotation`, `mediabox`, and `cropbox`; page coordinates alone are not physical size.
- **[SEABORN-LINE]** [seaborn.lineplot](https://seaborn.pydata.org/generated/seaborn.lineplot.html) — `units` with `estimator=None` for individual trajectories; missing rows can be dropped before line construction, so use explicit Matplotlib gaps for missing observations.

Native checks verify technical behavior, not truth of data, inferential calibration, full-file accessibility, or publisher acceptance. The PDF inspector reports only first-page declared font resources; it does not traverse nested XObjects or all pages. Source artifacts and smoke outputs stay outside the shipped skill.
