# Sentinel-2 L2A on Planetary Computer: data details

What the extraction script assumes, and what to check when you write your own loader.
Facts below were checked on the `sentinel-2-l2a` collection of Microsoft Planetary Computer
on 2026-09-21 unless marked otherwise.

## Collection and assets

- STAC API: `https://planetarycomputer.microsoft.com/api/stac/v1`, collection `sentinel-2-l2a`.
- Reading assets needs signed URLs: open the client with
  `modifier=planetary_computer.sign_inplace`. No account or key is needed. Signed URLs expire
  after a limited time, so a long job should search again (or re-sign items) rather than reuse
  items signed hours earlier.
- Useful item properties: `s2:mgrs_tile`, `s2:processing_baseline`, `eo:cloud_cover`,
  `datetime`, `platform`.
- The band assets carry no `raster:bands` scale or offset. Load them with
  `stackstac.stack(..., rescale=False)` and convert digital numbers (DN) yourself.

| Resolution | Assets |
|---|---|
| 10 m | `B02` blue, `B03` green, `B04` red, `B08` NIR |
| 20 m | `B05`, `B06`, `B07` red edge, `B8A` narrow NIR, `B11`, `B12` SWIR, `SCL` |
| 60 m | `B01` aerosol, `B09` water vapour |

`stackstac` resamples every asset to the requested resolution with nearest neighbour by
default, which is the right choice for `SCL` (a class map must never be interpolated).

## Digital numbers to reflectance

```text
reflectance = (DN + BOA_ADD_OFFSET) / 10000
BOA_ADD_OFFSET = -1000 for processing baseline >= 04.00 (from 25 January 2022), else 0
DN = 0 is no-data
```

A June 2024 scene in the Gharb plain (Morocco) had baseline `05.10`; a June 2021 scene of the
same area had `03.00`. A multi-year series therefore mixes both conventions. Forgetting the offset
compresses NDVI: with true reflectances red 0.05 and NIR 0.30, NDVI is 0.71, but on raw
offset DN (1500, 4000) it comes out as 0.45. Time series that cross January 2022 then show a
fake step.

`to_reflectance()` in `scripts/s2_parcel_timeseries.py` applies this per scene and raises when
the baseline is missing rather than guessing.

## Overlapping tiles

Sentinel-2 L2A is delivered per 110 km MGRS tile, and neighbouring tiles overlap. A parcel in
an overlap receives every acquisition twice (for example tiles `30STD` and `29SQU` around
34.61 N, 6.01 W: 24 items in June 2024 instead of 12). Keep one tile.

A cross-check on two parcels over June 2024 gave NDVI differences between the two tiles of
0.0017 on average (maximum 0.0067) for the same acquisitions. The choice of tile matters much
less than keeping only one. Mixing tiles doubles some dates and adds reprojection noise.

## Scene Classification Layer (SCL)

| Class | Meaning | Keep as clear? |
|---|---|---|
| 0 | no data | no |
| 1 | saturated or defective | no |
| 2 | dark area pixels (often topographic or cloud shadow) | no |
| 3 | cloud shadows | no |
| 4 | vegetation | yes |
| 5 | not vegetated (bare soil) | yes |
| 6 | water | no for crops (flooded rice: reconsider) |
| 7 | unclassified | no by default |
| 8, 9 | cloud medium and high probability | no |
| 10 | thin cirrus | no |
| 11 | snow or ice | no |

Keeping 4 and 5 is conservative: it removes some valid pixels (class 7 is often clear) but
lets almost no cloud through. For crops, keeping 5 is essential: before emergence and after
harvest a parcel is bare soil, and dropping class 5 would erase the start and end of the season.

SCL misses thin clouds and haze. Symptoms are single-date NDVI drops of a whole parcel.
A robust follow-up is a temporal outlier filter (for example, drop a date whose NDVI falls more
than 0.15 below both neighbours) or a smoother (Savitzky-Golay, Whittaker) on the clear series.

## Per-parcel keep rule

A (parcel, date) is kept when the clear pixels are at least `--min-clear` (default 0.6) of the
parcel's valid pixels. A parcel mean over a few clear pixels in a mostly cloudy parcel is
dominated by cloud edges and adjacency effects. Lower the threshold for small parcels only
after checking the resulting series.

## Memory and speed

- Load only the parcels' bounding box (padded by two pixels), never the whole tile.
- Load scenes in chunks along time (`--time-chunk`); a season of 5 bands over a few km² fits in
  a few hundred MB per chunk.
- Rasterise parcels once, on the grid of the first chunk: every chunk shares the same grid
  because bounds, resolution and CRS are fixed. Use the cube's `transform` attribute rather than
  rebuilding one from the coordinates; `stackstac` labels pixels by their top-left corner by
  default, so a transform built as if they were centres is shifted by half a pixel.
- The public API occasionally drops a request; wrap the search in a few retries.
