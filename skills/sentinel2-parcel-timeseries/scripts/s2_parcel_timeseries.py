#!/usr/bin/env python3
"""Per-parcel Sentinel-2 L2A time series from Microsoft Planetary Computer.

For every parcel polygon and every acquisition date, the script keeps only the
pixels the Scene Classification Layer (SCL) marks as clear, drops the date for
that parcel when too few of its pixels are clear, and writes one row per
(parcel, date) with surface-reflectance statistics and NDVI.

It handles three traps that silently corrupt Sentinel-2 time series:

* overlapping MGRS tiles: the same acquisition is served once per tile, so an
  area on a tile edge gets every date twice. One tile is kept (``--tile`` or
  the most frequent one).
* the processing-baseline offset: from baseline 04.00 (25 January 2022) L2A
  digital numbers carry a +1000 offset. Reflectance is (DN - 1000) / 10000 for
  those scenes and DN / 10000 before. Computing NDVI on raw DN biases it.
* no-data: DN 0 is no-data, not zero reflectance.

Only the command-line entry point needs network access and the geospatial
stack; the pure functions (``to_reflectance``, ``clear_mask``, ``ndvi``,
``choose_tile``, ``one_item_per_date``, ``parcel_stats``) need only NumPy.

Example
-------
    python s2_parcel_timeseries.py parcels.geojson --id-column parcel_id \\
        --start 2024-04-01 --end 2024-09-30 --out parcel_timeseries.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from typing import Iterable, Mapping, Sequence

import numpy as np

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-2-l2a"

#: SCL classes kept as clear: 4 vegetation, 5 not vegetated (bare soil).
CLEAR_SCL = (4, 5)

SCL_CLASSES = {
    0: "no data",
    1: "saturated or defective",
    2: "dark area pixels",
    3: "cloud shadows",
    4: "vegetation",
    5: "not vegetated",
    6: "water",
    7: "unclassified",
    8: "cloud medium probability",
    9: "cloud high probability",
    10: "thin cirrus",
    11: "snow or ice",
}

DEFAULT_ASSETS = ("B02", "B03", "B04", "B08", "B11")


# ----------------------------------------------------------------- pure helpers
def baseline_offset(baseline: str | None) -> float:
    """DN offset added by the processing baseline: 1000 from 04.00, else 0.

    A missing baseline raises instead of guessing, because a wrong guess biases
    every reflectance and index computed afterwards.
    """
    if baseline is None or str(baseline).strip() == "":
        raise ValueError("processing baseline unknown: cannot decide the +1000 offset")
    major, _, minor = str(baseline).partition(".")
    return 1000.0 if (int(major), int(minor or 0)) >= (4, 0) else 0.0


def to_reflectance(dn: np.ndarray, baseline: str | None) -> np.ndarray:
    """Convert L2A digital numbers to surface reflectance (0 to 1).

    DN 0 and NaN become NaN (no-data). Values are clipped to [0, 1] after the
    offset is removed, since dark targets can fall slightly below the offset.
    """
    dn = np.asarray(dn, dtype="float64")
    out = (dn - baseline_offset(baseline)) / 10000.0
    out[~np.isfinite(dn) | (dn == 0)] = np.nan
    return np.clip(out, 0.0, 1.0)


def clear_mask(scl: np.ndarray, classes: Iterable[int] = CLEAR_SCL) -> np.ndarray:
    """Boolean mask of pixels whose SCL class is in ``classes`` (NaN is not clear)."""
    scl = np.asarray(scl, dtype="float64")
    return np.isfinite(scl) & np.isin(scl, list(classes))


def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDVI from reflectances; NaN where the denominator is zero or missing."""
    red = np.asarray(red, dtype="float64")
    nir = np.asarray(nir, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (nir - red) / (nir + red)
    out[~np.isfinite(out)] = np.nan
    return out


def choose_tile(items: Sequence, tile: str | None = None) -> tuple[str, list]:
    """Keep the items of one MGRS tile: ``tile`` if given, else the most frequent.

    Ties are broken alphabetically so the choice is reproducible.
    """
    tiles = Counter(item.properties.get("s2:mgrs_tile") for item in items)
    if not tiles:
        raise ValueError("no Sentinel-2 items to choose a tile from")
    if tile is None:
        best = max(tiles.values())
        tile = sorted(t for t, n in tiles.items() if n == best)[0]
    kept = [item for item in items if item.properties.get("s2:mgrs_tile") == tile]
    if not kept:
        raise ValueError(f"tile {tile} not found; available: {dict(tiles)}")
    return tile, kept


def one_item_per_date(items: Sequence) -> list:
    """One item per acquisition day, keeping the lowest cloud cover, sorted by date."""
    best: dict[str, object] = {}
    for item in items:
        day = str(item.properties["datetime"])[:10]
        cloud = item.properties.get("eo:cloud_cover", 100.0)
        if day not in best or cloud < best[day].properties.get("eo:cloud_cover", 100.0):
            best[day] = item
    return [best[day] for day in sorted(best)]


def parcel_stats(
    labels: np.ndarray,
    parcel_ids: Sequence,
    reflectance: Mapping[str, np.ndarray],
    scl: np.ndarray,
    dates: Sequence[str],
    min_clear: float = 0.6,
    clear_classes: Iterable[int] = CLEAR_SCL,
) -> list[dict]:
    """Per-parcel, per-date statistics over clear pixels.

    Parameters
    ----------
    labels : (y, x) int array, 0 outside parcels, k+1 inside ``parcel_ids[k]``.
    reflectance : band name -> (t, y, x) reflectance arrays.
    scl : (t, y, x) SCL classes.
    min_clear : a (parcel, date) is kept only if at least this fraction of the
        parcel's valid pixels is clear.

    Returns one dict per kept (parcel, date) with ``n_pixels``, ``n_clear``,
    ``clear_fraction``, ``<band>_mean`` and, when B04 and B08 are present,
    ``ndvi_mean``, ``ndvi_median`` and ``ndvi_std``.
    """
    clear_classes = tuple(clear_classes)
    rows = []
    has_ndvi = "B04" in reflectance and "B08" in reflectance
    for t, day in enumerate(dates):
        clear_t = clear_mask(scl[t], clear_classes)
        valid_t = np.isfinite(np.asarray(scl[t], dtype="float64")) & (np.asarray(scl[t]) != 0)
        vi = ndvi(reflectance["B04"][t], reflectance["B08"][t]) if has_ndvi else None
        for k, pid in enumerate(parcel_ids):
            inside = labels == k + 1
            n_valid = int((inside & valid_t).sum())
            use = inside & clear_t
            n_clear = int(use.sum())
            if n_valid == 0 or n_clear / n_valid < min_clear:
                continue
            row = {"parcel_id": pid, "date": day, "n_pixels": int(inside.sum()),
                   "n_clear": n_clear, "clear_fraction": round(n_clear / n_valid, 4)}
            for band, arr in reflectance.items():
                row[f"{band}_mean"] = float(np.nanmean(arr[t][use]))
            if vi is not None:
                v = vi[use]
                row["ndvi_mean"] = float(np.nanmean(v))
                row["ndvi_median"] = float(np.nanmedian(v))
                row["ndvi_std"] = float(np.nanstd(v))
            rows.append(row)
    return rows


# ------------------------------------------------------------ network section
def search_items(bbox, start: str, end: str, max_cloud: float, retries: int = 5):
    """STAC search with retries (the public API occasionally drops requests)."""
    import planetary_computer
    import pystac_client

    for attempt in range(retries):
        try:
            catalog = pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
            search = catalog.search(collections=[COLLECTION], bbox=list(bbox),
                                    datetime=f"{start}/{end}",
                                    query={"eo:cloud_cover": {"lt": max_cloud}})
            return list(search.items())
        except Exception as error:  # network errors differ by transport; retry all
            if attempt == retries - 1:
                raise
            print(f"STAC search failed ({error!s:.80}); retry {attempt + 1}/{retries}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return []


def extract(parcels_path: str, id_column: str, start: str, end: str,
            assets: Sequence[str] = DEFAULT_ASSETS, max_cloud: float = 80.0,
            min_clear: float = 0.6, tile: str | None = None, resolution: float = 10.0,
            time_chunk: int = 8, pixel_out: str | None = None):
    """Run the full extraction and return a pandas DataFrame (one row per parcel and date).

    With ``pixel_out``, also saves every parcel pixel's series to a compressed
    NumPy archive: ``X`` (pixels, dates, bands) reflectance with NaN where the
    pixel is not clear, ``parcel_id`` per pixel, ``dates`` and ``bands``.
    """
    import geopandas as gpd
    import pandas as pd
    import stackstac
    from rasterio.features import rasterize

    parcels = gpd.read_file(parcels_path)
    if id_column not in parcels.columns:
        raise SystemExit(f"column {id_column!r} not in {list(parcels.columns)}")
    if parcels.crs is None:
        parcels = parcels.set_crs(4326)
    utm = parcels.estimate_utm_crs()
    parcels_utm = parcels.to_crs(utm)
    ids = list(parcels[id_column])

    items = search_items(parcels.to_crs(4326).total_bounds, start, end, max_cloud)
    if not items:
        raise SystemExit("no Sentinel-2 scene found for this area and period")
    tile, items = choose_tile(items, tile)
    items = one_item_per_date(items)
    print(f"{len(items)} scenes on tile {tile} ({start} to {end})", file=sys.stderr)

    xmin, ymin, xmax, ymax = parcels_utm.total_bounds
    pad = 2 * resolution
    bounds = (xmin - pad, ymin - pad, xmax + pad, ymax + pad)
    bands = [a for a in assets if a != "SCL"] + ["SCL"]

    rows = []
    labels = None
    pixel_blocks, all_dates = [], []
    for i in range(0, len(items), time_chunk):
        chunk = items[i:i + time_chunk]
        cube = stackstac.stack(chunk, assets=bands, epsg=utm.to_epsg(), resolution=resolution,
                               bounds=bounds, dtype="float64", fill_value=np.nan,
                               rescale=False).compute()
        if labels is None:
            shapes = [(geom, k + 1) for k, geom in enumerate(parcels_utm.geometry)]
            labels = rasterize(shapes, out_shape=(cube.sizes["y"], cube.sizes["x"]),
                               transform=cube.attrs["transform"], fill=0, dtype="int32")
        dates = [str(t)[:10] for t in cube["time"].values]
        # read the baseline from the cube itself so it always matches the time order
        # (stackstac drops the time dimension of a coordinate that is constant)
        if "s2:processing_baseline" in cube.coords:
            coord = cube["s2:processing_baseline"]
            values = coord.values if "time" in coord.dims else [coord.values.item()] * cube.sizes["time"]
            baselines = [str(b) for b in values]
        else:
            baselines = [item.properties.get("s2:processing_baseline") for item in chunk]
        reflectance = {}
        for band in bands[:-1]:
            dn = cube.sel(band=band).values
            reflectance[band] = np.stack([to_reflectance(dn[t], baselines[t]) for t in range(len(chunk))])
        scl = cube.sel(band="SCL").values
        rows += parcel_stats(labels, ids, reflectance, scl, dates, min_clear)
        if pixel_out:
            inside = labels > 0
            block = np.stack([reflectance[b][:, inside] for b in bands[:-1]], axis=-1)  # (t, pix, band)
            block[~clear_mask(scl[:, inside])] = np.nan
            pixel_blocks.append(block.transpose(1, 0, 2))
            all_dates += dates

    missing = [pid for k, pid in enumerate(ids) if not (labels == k + 1).any()]
    if missing:
        print(f"warning: parcels smaller than one pixel, no data: {missing}", file=sys.stderr)
    if pixel_out:
        inside = labels > 0
        np.savez_compressed(pixel_out, X=np.concatenate(pixel_blocks, axis=1).astype("float32"),
                            parcel_id=np.asarray(ids, dtype=object)[labels[inside] - 1].astype(str),
                            dates=np.array(all_dates), bands=np.array(bands[:-1]))
        print(f"{int(inside.sum())} parcel pixels x {len(all_dates)} dates -> {pixel_out}", file=sys.stderr)
    table = pd.DataFrame(rows)
    if not table.empty:
        table.insert(2, "tile", tile)
    return table


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Per-parcel Sentinel-2 L2A time series (Planetary Computer, SCL cloud mask, "
                    "baseline offset handled).")
    parser.add_argument("parcels", help="parcel polygons: GeoJSON, KML, GeoPackage or shapefile")
    parser.add_argument("--id-column", required=True, help="column holding the parcel identifier")
    parser.add_argument("--start", required=True, help="first date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="last date, YYYY-MM-DD")
    parser.add_argument("--assets", nargs="+", default=list(DEFAULT_ASSETS),
                        help="Sentinel-2 bands to extract (SCL is always added)")
    parser.add_argument("--max-cloud", type=float, default=80.0,
                        help="scene-level cloud cover filter in percent (default 80)")
    parser.add_argument("--min-clear", type=float, default=0.6,
                        help="minimum clear fraction of a parcel to keep a date (default 0.6)")
    parser.add_argument("--tile", help="MGRS tile to keep, e.g. 30STD (default: most frequent)")
    parser.add_argument("--resolution", type=float, default=10.0, help="output pixel size in metres")
    parser.add_argument("--time-chunk", type=int, default=8,
                        help="scenes loaded at once; lower it when memory is short")
    parser.add_argument("--out", required=True, help="output CSV, one row per parcel and date")
    parser.add_argument("--pixel-out", help="optional .npz with every parcel pixel's clear series")
    args = parser.parse_args(argv)

    table = extract(args.parcels, args.id_column, args.start, args.end, args.assets,
                    args.max_cloud, args.min_clear, args.tile, args.resolution, args.time_chunk,
                    args.pixel_out)
    table.to_csv(args.out, index=False)
    print(f"{len(table)} rows ({table['parcel_id'].nunique() if len(table) else 0} parcels) -> {args.out}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
