# Histolab core API map

The skill targets published Histolab 0.7.0. Read the per-topic reference for
executable examples and scientific limitations; placeholder WSI paths require
user data. Upstream [API index](https://histolab.readthedocs.io/en/latest/py-modindex.html)
currently labels itself 0.6.0, so use the linked 0.7.0 source for release-specific
behavior.

| Capability | Public API | Key contract |
| --- | --- | --- |
| Slide inspection | `histolab.slide.Slide` | `levels` is a list; `level_dimensions(level)` is a method |
| Tissue detection | `histolab.masks.TissueMask`, `BiggestTissueBoxMask`, `BinaryMask` | Boolean mask; custom filters are positional |
| Tiling | `histolab.tiler.RandomTiler`, `GridTiler`, `ScoreTiler` | Mask passed to methods; preview returns Pillow image |
| Ranking | `histolab.scorer.NucleiScorer`, `CellularityScorer` | Stain-derived area heuristics, not cell counts or diagnosis |
| Filters | `histolab.filters.image_filters.Compose` and filter classes | Preserve Pillow/NumPy type transitions |
| Normalization | `histolab.stain_normalizer.MacenkoStainNormalizer`, `ReinhardStainNormalizer` | `fit(target)` then `transform(source)` |
| Spatial provenance | `histolab.types.CoordinatePair`, `Tile.coords` | Four level-0 pixel coordinates |

The slide-management reference covers native OpenSlide, exact MPP backend
requirements and small versus remote sample data. The tissue-mask reference
provides ROI conversion and pen-mask examples. The tile-extraction reference
covers strategy choice, CSV schema and concentric multi-resolution patches.
The filters reference covers type-correct compositions and stain normalization.
The visualization reference provides aligned mask overlays, mosaics and score
plots. The typical-workflows reference combines these APIs into extraction runs.
