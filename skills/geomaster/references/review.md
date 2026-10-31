# Review scope and sources

Reviewed 2026-10-01. This skill contains broad geospatial references, not one package.
Every preexisting reference was read. Invalid scientific shortcuts were corrected
or replaced with bounded workflows; useful API fragments were retained where verified.

## Evidence boundaries

- The isolated Python 3.13 suite passed 43 tests. Synthetic checks cover masked
  indices/calibration, terrain with known planes, raster output metadata, classification
  masks/labels/CRS, refusal to overwrite existing files, and corrected local recipes.
- Public STAC GET searches at Planetary Computer, Earth Search and CDSE each returned
  two Sentinel-2 L2A items plus next-page links. Separate PySTAC Client searches followed
  pagination and bounded results to three items per catalog, checking collection/cloud
  filters. These are metadata tests, not imagery or authenticated download tests.
- A local ODC-STAC 0.5.3 load preserved raw DN values despite asset scale/offset metadata;
  callers must calibrate explicitly once. Real local COG, GeoParquet and Zarr 2 round trips,
  Dask raster/vector, Fiona, PyKrige, ESDA, MovingPandas, OSMnx and watershed checks passed.
- Desktop QGIS/ArcPy/GRASS/SAGA, native GDAL, R/Julia/Java/Go/Rust, GPUs and real-scene
  ML/physical calibration were not executed. Their examples are illustrative and
  use referenced current interfaces; source review is not runtime validation.
- No authenticated Earth Engine/CDS/Google/Mapbox/OpenWeather calls, service mutations,
  cloud exports, training jobs, commercial image orders or pretrained weights were used.

## Upstream contracts checked

| Surface | Source and result |
|---|---|
| Core GIS | [GeoPandas](https://geopandas.org/en/stable/docs/reference.html), [PyProj](https://pyproj4.github.io/pyproj/stable/api/transformer.html), [Rasterio masks](https://rasterio.readthedocs.io/en/stable/topics/masks.html): axis order, CRS transforms, nodata and array dimensions |
| Raster/COG | [GDAL COG](https://gdal.org/en/stable/drivers/raster/cog.html), [viewshed](https://gdal.org/en/stable/programs/gdal_viewshed.html): actual driver layout, projected coordinates and nodata limitation |
| STAC | [PySTAC Client](https://pystac-client.readthedocs.io/en/latest/api.html), [CDSE](https://documentation.dataspace.copernicus.eu/APIs/STAC.html), [Earth Search](https://element84.com/earth-search/): bounded iterator, pages, collection and asset names |
| Planetary Computer | [SDK signing source](https://github.com/microsoft/planetary-computer-sdk-for-python/blob/main/planetary_computer/sas.py): account/container SAS endpoint, expiry and item modifier |
| Sentinel/Landsat | [S2 SR](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED), [Landsat L2](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2), [normalizedDifference](https://developers.google.com/earth-engine/apidocs/ee-image-normalizeddifference), [SAR](https://developers.google.com/earth-engine/guides/sentinel1): QA, reflectance scales, thermal products, negative values and power/dB |
| Climate APIs | [CDS](https://cds.climate.copernicus.eu/how-to-api): PAT configuration, current API URL and data_format request |
| Other HTTP APIs | [Google](https://developers.google.com/maps/documentation/geocoding/guides-v3/requests-geocoding), [Mapbox](https://docs.mapbox.com/api/search/geocoding/), [OpenWeather](https://openweathermap.org/api/current), [Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API): current routes, query keys, response status/shape and traversal limits |
| OSM services | [OSMnx](https://osmnx.readthedocs.io/en/stable/user-reference.html), [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/), [tile policy](https://operations.osmfoundation.org/policies/tiles/): 2.x names, free-flow times and service use boundaries |
| Cloud arrays | [ODC](https://odc-stac.readthedocs.io/en/latest/_api/odc.stac.load.html), [Rioxarray](https://corteva.github.io/rioxarray/stable/rioxarray.html), [Xarray Zarr](https://docs.xarray.dev/en/stable/generated/xarray.Dataset.to_zarr.html), [Dask-GeoPandas](https://dask-geopandas.readthedocs.io/en/stable/docs/reference/api/dask_geopandas.GeoDataFrame.spatial_shuffle.html): chunks, spatial shuffle, explicit store format |
| Specialist local APIs | [MovingPandas](https://movingpandas.readthedocs.io/en/main/api/trajectorysplitter.html), [PyKrige](https://geostat-framework.readthedocs.io/projects/pykrige/en/stable/generated/pykrige.ok.OrdinaryKriging.html), [SciPy MILP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html): current constructors, variance and integer constraints |
| ML/GPU | [group splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html), [SHAP](https://shap.readthedocs.io/en/latest/generated/shap.plots.beeswarm.html), [cuSpatial](https://docs.rapids.ai/api/cuspatial/stable/api_docs/spatial/), [PyTorch AMP](https://docs.pytorch.org/docs/stable/amp.html): output types, holdouts and current namespaces |
| Native GIS | [QGIS](https://docs.qgis.org/4.2/en/docs/pyqgis_developer_cookbook/plugins/plugins.html), [ArcGIS viewshed](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/spatial-analyst/viewshed.html), [GRASS](https://grass.osgeo.org/grass-stable/manuals/r.watershed.html), [SAGA](https://saga-gis.sourceforge.io/saga_tool_doc/9.12.1/ta_morphometry_0.html): actual processing contracts |
| Languages | [sf](https://r-spatial.github.io/sf/reference/geos_unary.html), [terra](https://rspatial.github.io/terra/reference/extract.html), [ArchGDAL](https://yeesian.com/ArchGDAL.jl/latest/geometries/), [GeoStats](https://juliaearth.github.io/GeoStatsDocs/stable/interpolation/), [orb](https://pkg.go.dev/github.com/paulmach/orb/geo), [GeoRust](https://docs.rs/geo/latest/geo/), [Turf](https://turfjs.org/docs/api/interpolate): corrected method names, units and ownership boundaries |

The executed core stack included GeoPandas 1.2.0, Shapely 2.1.2, PyProj 3.8.0,
Rasterio 1.5.2, Rioxarray 0.23.0, Xarray 2026.9.0, Dask 2026.8.0,
Dask-GeoPandas 0.5.0, scikit-learn 1.9.1, OSMnx 2.1.1, PySTAC Client 0.9.0,
Planetary Computer 1.0.0, ODC-STAC 0.5.3, PyArrow 25.0.1, Zarr 3.4.0,
MovingPandas 0.23.0, PyKrige 1.7.3, ESDA 2.10.0 and rio-cogeo 7.0.3.
Upstream warnings concerned Rioxarray affine multiplication deprecation and the
absent optional Stone Soup smoother; the tested MovingPandas operations do not use it.

The core environment intentionally excludes heavy GPU/desktop/specialist stacks.
A package being importable or a synthetic check passing does not validate real-world
scientific accuracy, field transfer, calibration or service availability.
