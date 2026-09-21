# Parcel geometry: checks before extracting anything

Most wrong parcel time series come from wrong polygons, not from the satellite. Check the
outlines before interpreting a single curve.

## Reading the polygons

```python
import geopandas as gpd

parcels = gpd.read_file("parcels.geojson")      # also .gpkg, .shp, .kml
if parcels.crs is None:
    parcels = parcels.set_crs(4326)              # KML and most GeoJSON are WGS 84
parcels_utm = parcels.to_crs(parcels.estimate_utm_crs())   # metres, for areas and buffers
```

- Keep a stable identifier column and join field labels on it, never on row order.
- KML exported from Google Earth may contain folders, points or reference polygons (study area,
  pivot outlines) besides the parcels. Filter by geometry type and by name before use.
- Fix invalid geometries with `parcels_utm.geometry.make_valid()` and drop empty ones.

## Area check

Compare the polygon area with the declared parcel area:

```python
parcels_utm["area_ha"] = parcels_utm.area / 10_000
parcels_utm["ratio"] = parcels_utm["area_ha"] / parcels_utm["declared_ha"]
print(parcels_utm.loc[(parcels_utm["ratio"] < 0.8) | (parcels_utm["ratio"] > 1.25),
                      ["parcel_id", "area_ha", "declared_ha", "ratio"]])
```

A polygon several times larger than the declared area includes neighbouring fields, roads or
fallow land. Its mean NDVI mixes crops, and a winter-crop profile inside a summer-maize parcel
is a typical sign. Redraw such parcels on recent imagery before modelling.

The pixel count reported by the extraction script gives the same check from the raster side:
at 10 m, one hectare is 100 pixels.

## Edge pixels

A 10 m pixel on the parcel boundary mixes the crop with roads, ditches or the neighbouring field.
For parcels of a few hectares or more, shrink the polygons before rasterising:

```python
parcels_utm["geometry"] = parcels_utm.buffer(-10)      # one pixel inwards
parcels_utm = parcels_utm[~parcels_utm.is_empty]
```

Skip the inward buffer for small parcels (under about 1 ha), where it removes most pixels.

## Vegetation masks can empty a parcel

Filtering pixels by an NDVI threshold ("keep vegetation pixels") before modelling removes bare
soil, but on a sparse, late or failed crop it can remove every pixel of a parcel, which then
silently disappears from the data set. Log, per parcel, the pixel count before and after any
mask. If a parcel falls below a minimum, keep all its pixels and flag it rather than dropping it,
because the parcels most affected by a disease are often the ones with the lowest NDVI.

## Parcels smaller than a pixel

`rasterio.features.rasterize` assigns a pixel to a polygon only when the pixel centre falls
inside it. A narrow or very small polygon can get zero pixels; the extraction script prints
these parcels. Use `all_touched=True` only for such small parcels, knowing that it adds mixed
edge pixels.
